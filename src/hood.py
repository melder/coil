"""
Wrapper module for interacting with the Robinhood options API, handling
session authentication, market hours lookups, and DTE calculations.
"""

import logging
import os
from datetime import datetime

import dateutil.parser
import pyotp
import pytz
import robin_stocks.robinhood as rh
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
load_dotenv()

_MIC = "XNYS"  # NYSE market code
_TIMEZONE = pytz.timezone("US/Eastern")


class HoodError(Exception):
    """Catchall exception for hood API failures"""


def login():
    """
    Logs into Robinhood using environment variables.
    Optionally uses RH_2FA_SECRET for TOTP and RH_PICKLE_NAME for session
    caching.
    """
    username = os.environ.get("RH_USERNAME")
    password = os.environ.get("RH_PASSWORD")
    mfa_secret = os.environ.get("RH_2FA_SECRET")
    pickle_name = os.environ.get("RH_PICKLE_NAME", "coil_ranker_session")

    if not username or not password:
        logging.error("RH_USERNAME and RH_PASSWORD not found in environment.")
        raise HoodError("Missing Robinhood credentials.")

    login_kwargs = {
        "username": username,
        "password": password,
        "pickle_name": pickle_name,
    }

    if mfa_secret:
        totp = pyotp.TOTP(mfa_secret).now()
        login_kwargs["mfa_code"] = totp
        logging.info("Using 2FA for Robinhood login.")

    rh.login(**login_kwargs)
    logging.info("Successfully logged into Robinhood API.")


def get_price(ticker):
    try:
        res = rh.stocks.get_latest_price(ticker)
        if res:
            return float(res[0])
        return None
    except Exception as e:
        logging.error("Failed to get price for %s: %s", ticker, e)
        return None


def get_expirations(ticker):
    try:
        res = rh.options.get_chains(ticker).get("expiration_dates")
        if res:
            return sorted(res)
        return None
    except Exception as e:
        logging.error("Failed to get expirations for %s: %s", ticker, e)
        return []


def get_options_by_expiration(ticker, expr, option_type=None):
    try:
        kwargs = {"optionType": option_type} if option_type else {}
        return rh.options.find_options_by_expiration(ticker, expr, **kwargs)
    except (AttributeError, TypeError) as err:
        # LAZY LOGGING: Unified exception signature handling for parsing flaws
        logging.error(
            "Unexpected err=%r, type=%s. Failed to get option chain data for %s",
            err,
            type(err),
            ticker,
        )
        return []


def get_market_hours(iso_date):
    try:
        return rh.markets.get_market_hours(_MIC, iso_date)
    except Exception as e:
        logging.error("Failed to get market hours for %s: %s", iso_date, e)
        return None


def is_market_open_on(iso_date):
    hours = get_market_hours(iso_date)
    return hours.get("is_open", False) if hours else False


def market_closes_at(iso_date):
    if is_market_open_on(iso_date):
        hours = get_market_hours(iso_date)
        if hours and hours.get("closes_at"):
            return dateutil.parser.isoparse(hours["closes_at"])
    return None


def today_datetime_utc():
    now = datetime.utcnow()
    return now.replace(tzinfo=pytz.UTC)


def absolute_seconds_until_expr(iso_date):
    """
    Calculates exact absolute seconds between right now and the precise
    market closing time on the given expiration date.
    """
    close_dt = market_closes_at(iso_date)

    if not close_dt:
        # Fallback if the endpoint fails or says the market is closed (e.g. holiday anomaly)
        # We default to 4:00 PM EST
        fallback_str = f"{iso_date} 16:00:00"
        fallback_dt = datetime.strptime(fallback_str, "%Y-%m-%d %H:%M:%S")
        local_dt = _TIMEZONE.localize(fallback_dt)
        close_dt = local_dt.astimezone(pytz.UTC)
        logging.warning(
            "Market hours missing for %s, defaulting to 16:00 EST (%s)",
            iso_date,
            close_dt,
        )

    seconds = (close_dt - today_datetime_utc()).total_seconds()
    return max(0.0, seconds)


def get_dte_years(iso_date):
    """
    Returns precise Time to Expiration in Years based on absolute market
    seconds.
    """
    seconds = absolute_seconds_until_expr(iso_date)
    return max(0.0001, seconds / (365.25 * 24 * 3600))
