import pandas as pd
import numpy as np

def calculate_gkyz_rv(df: pd.DataFrame, lambda_decay: float = 0.9) -> float:
    """
    Calculates the Garman-Klass-Yang-Zhang (GKYZ) Realized Volatility estimator.
    Applies a reversed EWMA-like weighting where older data is weighted higher
    than recent data to "punish" recent range expansion.

    Expects a DataFrame with columns: ['Open', 'Close', 'Low', 'High']
    and expects len(df) == 14 (13 weeks + 1 previous close).
    """
    if len(df) < 2:
        return np.nan

    # GKYZ Formula components:
    # variance = (ln(Open_i / Close_{i-1}))^2
    #          + 0.5 * (ln(High_i / Low_i))^2
    #          - (2 * ln(2) - 1) * (ln(Close_i / Open_i))^2

    # 1. Calculate the components for each week
    # Note: shift(1) gets the previous row's value
    prev_close = df['Close'].shift(1)

    # We drop the first row since it doesn't have a previous close
    df_calc = df.copy().dropna()
    prev_close = prev_close.dropna()

    o = df_calc['Open']
    c = df_calc['Close']
    h = df_calc['High']
    l = df_calc['Low']

    # Overnight jump variance
    overnight_var = np.log(o / prev_close)**2

    # Intraday (intra-week) variance
    intra_var = 0.5 * np.log(h / l)**2 - (2 * np.log(2) - 1) * np.log(c / o)**2

    # Combined GKYZ variance per period
    period_var = overnight_var + intra_var

    # 2. Apply reverse EWMA weighting
    n = len(period_var)

    # Standard EWMA weights give higher weight to recent data: lambda^i where i is steps back
    # We want reverse EWMA: higher weight to older data.
    # If index 0 is the oldest (13 weeks ago) and index n-1 is the newest (this week)
    # Standard EWMA: weights = [lambda^(n-1), lambda^(n-2), ..., lambda^0]
    # Reverse EWMA: weights = [lambda^0, lambda^1, ..., lambda^(n-1)]

    powers = np.arange(n)
    weights = lambda_decay ** powers

    # Normalize weights so they sum to 1
    weights = weights / np.sum(weights)

    # 3. Calculate weighted variance
    # The GKYZ estimator is typically an annualized variance, but here we are working
    # with weekly data. We'll leave it as a weekly variance measure first, then annualize.

    weighted_var = np.sum(period_var * weights)

    # Annualize (assuming 52 weeks in a year)
    annualized_var = weighted_var * 52

    # Return Realized Volatility (std dev)
    rv = np.sqrt(annualized_var)

    return rv

if __name__ == "__main__":
    # Test script
    # Generate some dummy data representing 14 weeks
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=14, freq='W')
    base_price = 100

    # Scenario 1: Expanding volatility (recent weeks have higher ranges)
    # Older weeks: tight range
    close1 = base_price + np.random.normal(0, 1, 7).cumsum()
    open1 = close1 - np.random.normal(0, 0.5, 7)
    high1 = np.maximum(open1, close1) + np.random.uniform(0, 1, 7)
    low1 = np.minimum(open1, close1) - np.random.uniform(0, 1, 7)

    # Newer weeks: expanding range
    close2 = close1[-1] + np.random.normal(0, 5, 7).cumsum()
    open2 = close2 - np.random.normal(0, 2, 7)
    high2 = np.maximum(open2, close2) + np.random.uniform(2, 5, 7)
    low2 = np.minimum(open2, close2) - np.random.uniform(2, 5, 7)

    df_expanding = pd.DataFrame({
        'Open': np.concatenate([open1, open2]),
        'High': np.concatenate([high1, high2]),
        'Low': np.concatenate([low1, low2]),
        'Close': np.concatenate([close1, close2])
    }, index=dates)

    # Scenario 2: Contracting volatility (older weeks have higher ranges)
    df_contracting = pd.DataFrame({
        'Open': np.concatenate([open2, open1]),
        'High': np.concatenate([high2, high1]),
        'Low': np.concatenate([low2, low1]),
        'Close': np.concatenate([close2, close1])
    }, index=dates)

    # Scenario 3: Flat volatility
    close3 = base_price + np.random.normal(0, 2, 14).cumsum()
    open3 = close3 - np.random.normal(0, 1, 14)
    high3 = np.maximum(open3, close3) + np.random.uniform(0.5, 2, 14)
    low3 = np.minimum(open3, close3) - np.random.uniform(0.5, 2, 14)

    df_flat = pd.DataFrame({
        'Open': open3, 'High': high3, 'Low': low3, 'Close': close3
    }, index=dates)

    print("--- Reverse-Weighted GKYZ RV Tests ---")
    print("This 'punishes' recent expansion by weighting older data heavier.")
    print(f"Expanding Volatility : {calculate_gkyz_rv(df_expanding):.4f}")
    print(f"Contracting Volatility: {calculate_gkyz_rv(df_contracting):.4f}")
    print(f"Flat Volatility      : {calculate_gkyz_rv(df_flat):.4f}")
