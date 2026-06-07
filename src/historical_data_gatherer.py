import os
import time
import logging
import pandas as pd
from typing import Optional
from dotenv import load_dotenv

# We have alpha_vantage and polygon-api-client in pyproject.toml
from polygon import RESTClient

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
load_dotenv()

class HistoricalDataGatherer:
    def __init__(self):
        api_key = os.environ.get("POLYGON_API_KEY")
        if not api_key:
            logging.warning("POLYGON_API_KEY not found in .env. Initialization may fail if making live calls.")
        # The client handles the missing key gracefully until a call is made
        self.polygon_client = RESTClient(api_key=api_key)

    def fetch_weekly_data(self, ticker: str, weeks: int = 13) -> Optional[pd.DataFrame]:
        """
        Fetches 'weeks' number of weekly OHLC data for a given ticker.
        Standardizes output to a pandas DataFrame with columns: [Open, Close, Low, High, Volume]
        and Date as index.
        """
        try:

            logging.info(f"Fetching Polygon data for {ticker}...")
            # Polygon aggs endpoint: 
            # We fetch daily and resample to weekly, or fetch weekly directly.
            # Polygon supports multiplier=1, timespan='week'
            
            # Since we need exactly 'weeks' of data ending recently, and Polygon requires
            # date ranges, we calculate a safe lookback window (e.g., weeks * 2 to account for holidays)
            end_date = pd.Timestamp.now().strftime('%Y-%m-%d')
            start_date = (pd.Timestamp.now() - pd.Timedelta(weeks=weeks*2)).strftime('%Y-%m-%d')
            
            aggs = []
            for a in self.polygon_client.list_aggs(
                ticker, 
                multiplier=1, 
                timespan="week", 
                from_=start_date, 
                to=end_date,
                limit=50000
            ):
                aggs.append(a)
                
            if not aggs:
                logging.warning(f"No data returned from Polygon for {ticker}")
                return None
                
            df = pd.DataFrame(aggs)
            # Polygon uses ms timestamps
            df['Date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('Date', inplace=True)
            
            # Map Polygon's format to our standard
            df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
            
            # Enforce the required columns
            std_df = df[['Open', 'Close', 'Low', 'High', 'Volume']].copy()
            
            # Return exactly the requested number of weeks (tail)
            return std_df.tail(weeks)
            
        except Exception as e:
            logging.error(f"Polygon fetch failed for {ticker}: {e}")
            return None

if __name__ == "__main__":
    # Smoke test stub.
    gatherer = HistoricalDataGatherer()
    df = gatherer.fetch_weekly_data("TSLA")
    if df is not None:
        print(df.head())
