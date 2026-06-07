import os
import time
import logging
import pandas as pd
from pathlib import Path
from option_symbol_fetcher import fetch_cboe_symbols
from historical_data_gatherer import HistoricalDataGatherer
# We need to catch specific Polygon exceptions for retries if we can,
# but a general exception catch is safer given the RESTClient behavior.

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Best practice data directories
DATA_DIR = Path("data/raw")

def build_intermediary_dataset(free_tier: bool = True, max_retries: int = 3):
    """
    Fetches the CBOE weekly universe and iteratively downloads 13-week OHLC data.
    Saves each ticker to its own CSV to allow resuming on failure.
    Includes rate limiting and retry logic for API resilience.
    """
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Fetch Universe
    symbols = fetch_cboe_symbols("weeklies")
    if not symbols:
        logging.error("Failed to fetch symbol universe. Exiting.")
        return

    total_symbols = len(symbols)
    logging.info(f"Starting data gather for {total_symbols} symbols (Free Tier: {free_tier})...")

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
            logging.info(f"[{i+1}/{total_symbols}] Skipping {ticker} - already exists.")
            skip_count += 1
            continue

        logging.info(f"[{i+1}/{total_symbols}] Fetching {ticker}...")

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
                    wait_time = 60 # wait a full minute if we hit a hard 429
                    logging.warning(f"  -> Rate limit hit (429). Retrying in {wait_time}s... ({retries}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    # Generic 4xx/5xx or network error
                    wait_time = 5 * retries # Simple backoff
                    logging.warning(f"  -> Error fetching {ticker}: {e}. Retrying in {wait_time}s... ({retries}/{max_retries})")
                    if retries > max_retries:
                        logging.error(f"  -> Max retries reached for {ticker}. Skipping.")
                    else:
                        time.sleep(wait_time)

        if df is not None and not df.empty:
            df.to_csv(file_path)
            success_count += 1
        else:
            if retries <= max_retries: # Only log if it wasn't already logged as a max retry failure
                 logging.warning(f"[{i+1}/{total_symbols}] No data returned for {ticker}.")
            error_count += 1

        # Rate Limiting (proactive)
        if free_tier and i < total_symbols - 1:
            # Polygon free tier is 5 requests / minute -> 1 request every 12 seconds.
            # We sleep 12.5 to be safe.
            logging.debug(f"  -> Free tier active. Sleeping 12.5s before next request...")
            time.sleep(12.5)

    logging.info(f"Finished. Success: {success_count}, Skipped: {skip_count}, Errors: {error_count}")

if __name__ == "__main__":
    build_intermediary_dataset(free_tier=True)
