import yfinance as yf
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def fetch_pilot_data(ticker_symbol: str):
    """
    Fetches 13 weeks of weekly OHLC data for a given ticker.
    """
    logging.info(f"Fetching 13 weeks of data for {ticker_symbol}...")
    
    # We fetch slightly more than 13 weeks to ensure we have enough after potential alignment
    # interval='1wk' gives us weekly candles
    try:
        data = yf.download(ticker_symbol, period="4mo", interval="1wk", progress=False)
        
        if data.empty:
            logging.error(f"No data found for {ticker_symbol}")
            return None

        # Clean up yfinance MultiIndex columns if present
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # We only want the last 13 weeks
        pilot_data = data.tail(13).copy()
        
        # Ensure we have OHLC
        cols = ['Open', 'High', 'Low', 'Close']
        if not all(c in pilot_data.columns for c in cols):
            logging.error(f"Missing OHLC columns. Found: {list(pilot_data.columns)}")
            return None
            
        return pilot_data[cols]

    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        return None

if __name__ == "__main__":
    ticker = "TSLA"
    df = fetch_pilot_data(ticker)
    if df is not None:
        print(f"\nLast 13 Weekly Candles for {ticker}:")
        print(df)
        print(f"\nShape: {df.shape}")
