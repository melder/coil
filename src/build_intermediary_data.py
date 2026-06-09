import argparse
import logging
import time
from pathlib import Path

import pandas as pd

from historical_data_gatherer import HistoricalDataGatherer

# We need to catch specific Polygon exceptions for retries if we can,
# but a general exception catch is safer given the RESTClient behavior.

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Best practice data directories
DATA_DIR = Path("data/raw")


def build_intermediary_dataset(
    symbol_type: str = "weeklies", free_tier: bool = True, max_retries: int = 3
):
    """
    Reads the option symbol universe from a CSV and iteratively downloads 13-week OHLC data.
    Saves each ticker to its own CSV to allow resuming on failure.
    Includes rate limiting and retry logic for API resilience.
    """
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Read Universe from CSV
    symbols_file = Path(f"data/symbols/{symbol_type}.csv")
    if not symbols_file.exists():
        logging.error(
            "Symbols file not found: %s. Please run option_symbol_fetcher.py first.",
            symbols_file,
        )
        return

    try:
        df_symbols = pd.read_csv(symbols_file)
        symbols = df_symbols.to_dict("records")
    except Exception as e:
        logging.error("Failed to read symbols CSV: %s", e)
        return

    if not symbols:
        logging.error("Symbol universe is empty. Exiting.")
        return

    total_symbols = len(symbols)
    logging.info(
        "Starting data gather for %s symbols (Free Tier: %s)...",
        total_symbols,
        free_tier,
    )

    gatherer = HistoricalDataGatherer()

    # 2. Iterative Download & Save
    success_count = 0
    skip_count = 0
    error_count = 0

    for i, symbol_data in enumerate(symbols):
        ticker = symbol_data["ticker"]
        file_path = DATA_DIR / f"{ticker}.csv"

        # Resiliency: Skip if we already downloaded it
        if file_path.exists():
            logging.info(
                "[%s/%s] Skipping %s - already exists.",
                i + 1,
                total_symbols,
                ticker,
            )
            skip_count += 1
            continue

        logging.info("[%s/%s] Fetching %s...", i + 1, total_symbols, ticker)

        df = None
        retries = 0

        while retries <= max_retries:
            try:
                df = gatherer.fetch_weekly_data(ticker)
                # If we get here without an exception, break the retry loop
                break
            except Exception as e:
                # Polygon RESTClient throws exceptions on 4xx/5xx
                err_str = str(e).lower()
                retries += 1

                # Check if it's explicitly a 429 rate limit
                if "429" in err_str or "too many requests" in err_str:
                    wait_time = 60  # wait a full minute if we hit a hard 429
                    logging.warning(
                        "  -> Rate limit hit (429). Retrying in %ss... (%s/%s)",
                        wait_time,
                        retries,
                        max_retries,
                    )
                    time.sleep(wait_time)
                else:
                    # Generic 4xx/5xx or network error
                    wait_time = 5 * retries  # Simple backoff
                    logging.warning(
                        "  -> Error fetching %s: %s. Retrying in %ss... (%s/%s)",
                        ticker,
                        e,
                        wait_time,
                        retries,
                        max_retries,
                    )
                    if retries > max_retries:
                        logging.error(
                            "  -> Max retries reached for %s. Skipping.", ticker
                        )
                    else:
                        time.sleep(wait_time)

        if df is not None and not df.empty:
            df.to_csv(file_path)
            success_count += 1
        else:
            if (
                retries <= max_retries
            ):  # Only log if it wasn't already logged as a max retry failure
                logging.warning(
                    "[%s/%s] No data returned for %s.",
                    i + 1,
                    total_symbols,
                    ticker,
                )
            error_count += 1

        # Rate Limiting (proactive)
        if free_tier and i < total_symbols - 1:
            # Polygon free tier is 5 requests / minute -> 1 request every 12 seconds.
            # We sleep 12.5 to be safe.
            logging.debug(
                "  -> Free tier active. Sleeping 12.5s before next request..."
            )
            time.sleep(12.5)

    logging.info(
        "Finished. Success: %s, Skipped: %s, Errors: %s",
        success_count,
        skip_count,
        error_count,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build intermediary OHLC data from a fetched symbol list."
    )
    parser.add_argument(
        "--type",
        type=str,
        default="weeklies",
        choices=["weeklies", "all"],
        help="The symbol type to process (from data/symbols/).",
    )
    parser.add_argument(
        "--paid-tier",
        action="store_true",
        help="Disable the free tier rate limit of 5 requests/min.",
    )
    args = parser.parse_args()

    build_intermediary_dataset(symbol_type=args.type, free_tier=not args.paid_tier)
