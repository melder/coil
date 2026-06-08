import os
import math
import logging
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq
import hood

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_nearest_atm_options(ticker: str, risk_free_rate: float = 0.045):
    """
    Method 1 & 2: Sweeps the four contracts closest to the current symbol price
    for the nearest expiration using the robust hood wrapper.
    """
    current_price = hood.get_price(ticker)
    if not current_price:
        logging.error(f"Could not fetch price for {ticker}")
        return None

    expirations = hood.get_expirations(ticker)
    if not expirations:
        logging.error(f"Could not fetch expirations for {ticker}")
        return None

    # Get the nearest future expiration
    today = hood.today_datetime_utc().strftime('%Y-%m-%d')
    valid_exps = [d for d in expirations if d >= today]
    if not valid_exps:
        logging.warning(f"No future expirations found for {ticker}")
        return None

    nearest_exp = valid_exps[0]

    # Calculate Precise Time to Expiration (DTE in years) using market hours
    time_to_exp_years = hood.get_dte_years(nearest_exp)
    logging.info(f"{ticker} @ {current_price:.2f} | Nearest Exp: {nearest_exp} | DTE: {time_to_exp_years*365.25:.4f} days")

    calls = hood.get_options_by_expiration(ticker, nearest_exp, option_type='call')
    puts = hood.get_options_by_expiration(ticker, nearest_exp, option_type='put')

    if not calls or not puts:
        logging.error(f"Failed to fetch option chain for {ticker} @ {nearest_exp}")
        return None

    def parse_options(opt_list):
        parsed = []
        for o in opt_list:
            strike = float(o['strike_price'])
            opt_type = o['type']
            bid = float(o['bid_price'] or 0.0)
            ask = float(o['ask_price'] or 0.0)
            mark = float(o['adjusted_mark_price'] or 0.0)
            rh_iv = float(o['implied_volatility'] or 0.0)

            spread = ask - bid
            spread_score = (spread / mark * 100) if mark > 0 else 0.0

            custom_iv = np.nan
            if mark > 0:
                custom_iv = calculate_custom_iv(current_price, strike, time_to_exp_years, risk_free_rate, mark, opt_type)

            parsed.append({
                'strike': strike,
                'type': opt_type,
                'bid': bid,
                'ask': ask,
                'mark': mark,
                'spread_score': spread_score,
                'rh_iv': rh_iv,
                'custom_iv': custom_iv
            })
        return sorted(parsed, key=lambda x: x['strike'])

    sorted_calls = parse_options(calls)
    sorted_puts = parse_options(puts)

    def find_nearest_two(sorted_opts):
        below, above = None, None
        for i, opt in enumerate(sorted_opts):
            if opt['strike'] >= current_price:
                above = opt
                if i > 0:
                    below = sorted_opts[i-1]
                break
        return below, above

    call_below, call_above = find_nearest_two(sorted_calls)
    put_below, put_above = find_nearest_two(sorted_puts)

    contracts = {
        'call_below': call_below,
        'call_above': call_above,
        'put_below': put_below,
        'put_above': put_above
    }

    agg_stats = aggregate_ivs(contracts)

    return {
        'ticker': ticker,
        'current_price': current_price,
        'expiration': nearest_exp,
        'dte_years': time_to_exp_years,
        'risk_free_rate': risk_free_rate,
        'contracts': contracts,
        'aggregated_iv': agg_stats
    }

def bs_price(S, K, T, r, sigma, option_type='call'):
    """Standard Black-Scholes formula for pricing European options."""
    if T <= 0 or sigma <= 0:
        return max(0.0, S - K) if option_type == 'call' else max(0.0, K - S)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == 'call':
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

def calculate_custom_iv(S, K, T, r, market_price, option_type='call'):
    """Reverse-engineered IV from Market Price using Brent's method."""
    if market_price <= 0:
        return np.nan
    def objective(sigma):
        return bs_price(S, K, T, r, sigma, option_type) - market_price
    try:
        return brentq(objective, 1e-4, 5.0)
    except (ValueError, RuntimeError):
        return np.nan

def aggregate_ivs(contracts):
    """Aggregates IV (Median/Average) from the 4 contracts."""
    custom_ivs = []
    rh_ivs = []
    for label, opt in contracts.items():
        if not opt:
            continue
        if 'custom_iv' in opt and not np.isnan(opt['custom_iv']):
            custom_ivs.append(opt['custom_iv'])
        if 'rh_iv' in opt and opt['rh_iv'] > 0:
            rh_ivs.append(opt['rh_iv'])
    stats = {}
    if custom_ivs:
        stats['custom_median'] = float(np.median(custom_ivs))
        stats['custom_average'] = float(np.mean(custom_ivs))
    else:
        stats['custom_median'] = np.nan
        stats['custom_average'] = np.nan
    if rh_ivs:
        stats['rh_median'] = float(np.median(rh_ivs))
        stats['rh_average'] = float(np.mean(rh_ivs))
    else:
        stats['rh_median'] = np.nan
        stats['rh_average'] = np.nan
    return stats

if __name__ == "__main__":
    try:
        hood.login()
        test_ticker = "ADBE"
        result = get_nearest_atm_options(test_ticker)
        if result:
            print(f"\n--- {test_ticker} ATM Options Summary ---")
            print(f"Price: ${result['current_price']:.2f} | Exp: {result['expiration']} (DTE: {result['dte_years']*365.25:.4f} days)\n")
            for label, opt in result['contracts'].items():
                if not opt: continue
                print(f"[{label.upper():10}] Strike: {opt['strike']:6.1f} | Mark: {opt['mark']:6.2f} | Bid/Ask: {opt['bid']:.2f}/{opt['ask']:.2f} (Spread Score: {opt['spread_score']:5.1f}%)")
                print(f"             Robinhood IV: {opt['rh_iv']:.4f} | Custom IV: {opt['custom_iv']:.4f}\n")
            agg_stats = result['aggregated_iv']
            print("--- Aggregated IV Results ---")
            print(f"Custom IV Median (Primary) : {agg_stats['custom_median']:.4f}")
            print(f"Custom IV Average (Dangling): {agg_stats['custom_average']:.4f}")
    except Exception as e:
        print(f"Error: {e}")
