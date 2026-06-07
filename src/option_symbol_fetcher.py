import logging
import pandas as pd
import requests
from io import StringIO
from typing import Any

# Configure logging for the prototype
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

_CBOE_URLS = {
    "all": "https://www.cboe.com/us/options/symboldir/?download=csv",
    "weeklies": "https://www.cboe.com/us/options/symboldir/weeklys_options/?download=csv",
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.166 Safari/537.36"
}

def fetch_cboe_symbols(symbol_type: str = "all") -> list[dict[str, Any]]:
    """
    Fetches optionable symbols from CBOE.
    Returns a list of dicts: [{'ticker': 'AAPL', 'name': 'Apple Inc.'}, ...]
    """
    url = _CBOE_URLS.get(symbol_type)
    if not url:
        logging.error(f"Invalid symbol type: {symbol_type}. Use: {list(_CBOE_URLS.keys())}")
        return []

    logging.info(f"Fetching {symbol_type} from CBOE...")
    
    try:
        response = requests.get(url, timeout=30, headers=_HEADERS)
        response.raise_for_status()

        # Simple CSV read
        df = pd.read_csv(StringIO(response.text))
        
        # Normalize headers (CBOE often has leading/trailing spaces)
        df.columns = df.columns.str.strip()
        
        if df.empty:
            logging.warning("CBOE returned empty data.")
            return []

        # Header normalization/check
        # CBOE CSVs usually have 'Stock Symbol' and 'Company Name'
        target_col = "Stock Symbol"
        if target_col not in df.columns:
            logging.error(f"Required column '{target_col}' not found. Found: {list(df.columns)}")
            return []

        symbols = []
        for _, row in df.iterrows():
            ticker = str(row.get(target_col, "")).strip()
            if not ticker or pd.isna(row.get(target_col)):
                continue
                
            symbols.append({
                "ticker": ticker,
                "name": str(row.get("Company Name", "")).strip(),
                "type": symbol_type
            })

        logging.info(f"Successfully fetched {len(symbols)} symbols.")
        return symbols

    except Exception as e:
        logging.error(f"Failed to fetch CBOE symbols: {e}")
        return []

if __name__ == "__main__":
    # Quick sanity check for all types
    for t in ["weeklies", "all"]:
        symbols = fetch_cboe_symbols(t)
        print(f"Type: {t:12} | Count: {len(symbols):4} | Samples: {[s['ticker'] for s in symbols[:3]]}")
