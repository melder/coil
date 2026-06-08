import pandas as pd
import numpy as np

def calculate_gkyz_rv(df: pd.DataFrame, lambda_decay: float = 0.9, reverse_ewma: bool = True) -> float:
    """
    Calculates the Garman-Klass-Yang-Zhang (GKYZ) Realized Volatility estimator.

    By default (reverse_ewma=True), it applies a reversed EWMA-like weighting where
    older data is weighted higher than recent data. This measures volatility relative
    to its longer-term regime by emphasizing older observations.

    Expects a DataFrame with columns: ['Open', 'Close', 'Low', 'High']
    and expects len(df) == 14 (13 weeks + 1 previous close).
    """
    if len(df) < 2:
        return np.nan

    # 1. Safer alignment by keeping it in the DataFrame
    df = df.copy()
    df['prev_close'] = df['Close'].shift(1)

    # We drop the first row since it doesn't have a previous close
    df_calc = df.dropna(subset=['prev_close']).copy()

    o = df_calc['Open']
    c = df_calc['Close']
    h = df_calc['High']
    l = df_calc['Low']
    prev_close = df_calc['prev_close']

    # Overnight jump variance
    overnight_var = np.log(o / prev_close)**2

    # Intraday (intra-week) variance
    intra_var = 0.5 * np.log(h / l)**2 - (2 * np.log(2) - 1) * np.log(c / o)**2

    # Combined GKYZ variance per period
    period_var = overnight_var + intra_var

    # 2. Apply weighting
    n = len(period_var)
    powers = np.arange(n)

    if reverse_ewma:
        # Emphasize older observations (index 0 is oldest)
        weights = lambda_decay ** powers
    else:
        # Standard EWMA: Emphasize recent observations
        weights = lambda_decay ** powers[::-1]

    # Normalize weights so they sum to 1
    weights = weights / np.sum(weights)

    # 3. Calculate weighted variance
    weighted_var = np.sum(period_var * weights)

    # Annualize (assuming 52 weeks in a year)
    annualized_var = weighted_var * 52

    # Return Realized Volatility (std dev)
    rv = np.sqrt(annualized_var)

    return rv

if __name__ == "__main__":
    import os

    # Test script using real AMZN data
    file_path = 'data/raw/AMZN.csv'

    if os.path.exists(file_path):
        df_real = pd.read_csv(file_path)

        print("--- Realized Volatility Weighting Tests (AMZN) ---")

        # 1. Reverse-Weighted (Our Method): Emphasizes longer-term regime.
        rv_reverse = calculate_gkyz_rv(df_real, lambda_decay=0.9, reverse_ewma=True)

        # 2. Equal Weight (Baseline): All weeks weighted evenly.
        rv_equal = calculate_gkyz_rv(df_real, lambda_decay=1.0)

        # 3. Standard EWMA: Emphasizes recent observations.
        rv_standard = calculate_gkyz_rv(df_real, lambda_decay=0.9, reverse_ewma=False)

        print(f"RV Reverse EWMA (Emphasizes OLD data)  : {rv_reverse:.4f}")
        print(f"RV Equal Weight (Baseline)             : {rv_equal:.4f}")
        print(f"RV Standard EWMA (Emphasizes NEW data) : {rv_standard:.4f}\n")

    else:
        print(f"Please provide {file_path} to run the test.")
