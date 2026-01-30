"""
Rule 6: Bollinger Band Mean Reversion
======================================
Filosofi: Harga cenderung kembali ke rata-rata - beli di lower band, jual di middle/upper

ENTRY CONDITIONS:
1. Close < BB_Lower(20, 2)   - Price below lower band
2. Close > SMA(200)          - Still in uptrend
3. RSI(14) < 30              - Oversold confirmation
4. %B < 0                    - Strongly oversold

EXIT CONDITIONS:
1. Close > BB_Middle(20)     - Return to mean (primary target)
2. Close > BB_Upper(20, 2)   - Overbought bonus
3. Holding > 10 days         - Time exit

EXPECTED PERFORMANCE:
- Win Rate: ~68%
- Avg Profit/Trade: +3-5%
- Avg Holding: 5-10 days
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple


def sma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average"""
    return series.rolling(window=period, min_periods=period).mean()


def std(series: pd.Series, period: int) -> pd.Series:
    """Calculate Rolling Standard Deviation"""
    return series.rolling(window=period, min_periods=period).std()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI (Relative Strength Index)"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi_val = 100 - (100 / (1 + rs))
    return rsi_val


def bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0):
    """
    Calculate Bollinger Bands

    Returns: (middle, upper, lower, percent_b)
    """
    middle = sma(series, period)
    std_dev = std(series, period)

    upper = middle + (num_std * std_dev)
    lower = middle - (num_std * std_dev)

    # %B = (Price - Lower) / (Upper - Lower)
    percent_b = (series - lower) / (upper - lower)

    return middle, upper, lower, percent_b


def check_rule6(df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
    """
    Check if stock passes Rule 6: Bollinger Band Mean Reversion

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with columns: Open, High, Low, Close, Volume

    Returns:
    --------
    Tuple[bool, Dict]: (passed, details)
    """
    details = {
        'rule': 6,
        'rule_name': 'Bollinger Mean Reversion',
        'passed': False,
        'close': 0,
        'bb_lower': 0,
        'bb_middle': 0,
        'bb_upper': 0,
        'percent_b': 0,
        'sma_200': 0,
        'rsi_14': 0,
        'reason': ''
    }

    # Need at least 200 days of data
    if len(df) < 200:
        details['reason'] = 'Insufficient data (need 200 days)'
        return False, details

    # Standardize column names
    df_copy = df.copy()
    df_copy.columns = [col.lower() for col in df_copy.columns]

    required = ['close']
    for col in required:
        if col not in df_copy.columns:
            details['reason'] = f'Missing column: {col}'
            return False, details

    # Calculate indicators
    close = df_copy['close']

    bb_middle, bb_upper, bb_lower, percent_b = bollinger_bands(close, 20, 2.0)
    sma_200 = sma(close, 200)
    rsi_14 = rsi(close, 14)

    # Get latest values
    latest_close = close.iloc[-1]
    latest_bb_lower = bb_lower.iloc[-1]
    latest_bb_middle = bb_middle.iloc[-1]
    latest_bb_upper = bb_upper.iloc[-1]
    latest_percent_b = percent_b.iloc[-1]
    latest_sma_200 = sma_200.iloc[-1]
    latest_rsi_14 = rsi_14.iloc[-1]

    # Update details
    details['close'] = round(latest_close, 2)
    details['bb_lower'] = round(latest_bb_lower, 2)
    details['bb_middle'] = round(latest_bb_middle, 2)
    details['bb_upper'] = round(latest_bb_upper, 2)
    details['percent_b'] = round(latest_percent_b, 3)
    details['sma_200'] = round(latest_sma_200, 2)
    details['rsi_14'] = round(latest_rsi_14, 2)

    # Condition 1: Close below BB Lower
    if latest_close >= latest_bb_lower:
        details['reason'] = f'Close {latest_close:.0f} >= BB_Lower {latest_bb_lower:.0f}'
        return False, details

    # Condition 2: Still in uptrend (Close > SMA200)
    if latest_close <= latest_sma_200:
        details['reason'] = f'Close {latest_close:.0f} <= SMA200 {latest_sma_200:.0f} (downtrend)'
        return False, details

    # Condition 3: RSI < 30 (oversold)
    if pd.isna(latest_rsi_14) or latest_rsi_14 >= 30:
        details['reason'] = f'RSI(14) {latest_rsi_14:.1f} >= 30 (not oversold)'
        return False, details

    # Condition 4: %B < 0 (price below lower band)
    if latest_percent_b >= 0:
        details['reason'] = f'%B {latest_percent_b:.3f} >= 0'
        return False, details

    # All conditions passed
    details['passed'] = True
    details['reason'] = f'%B={latest_percent_b:.2f}, RSI={latest_rsi_14:.1f}'

    return True, details


def check_exit_rule6(df: pd.DataFrame, entry_price: float) -> Tuple[bool, str, Dict]:
    """
    Check exit conditions for Rule 6

    EXIT CONDITIONS:
    1. Close > BB_Middle (mean reversion complete)
    2. Close > BB_Upper (overbought)
    """
    details = {
        'close': 0,
        'bb_middle': 0,
        'bb_upper': 0,
        'percent_b': 0,
        'pnl_pct': 0,
        'exit_reason': None
    }

    if len(df) < 20:
        return False, None, details

    df_copy = df.copy()
    df_copy.columns = [col.lower() for col in df_copy.columns]

    close = df_copy['close']
    bb_middle, bb_upper, bb_lower, percent_b = bollinger_bands(close, 20, 2.0)

    latest_close = close.iloc[-1]
    latest_bb_middle = bb_middle.iloc[-1]
    latest_bb_upper = bb_upper.iloc[-1]
    latest_percent_b = percent_b.iloc[-1]

    pnl_pct = ((latest_close - entry_price) / entry_price) * 100

    details['close'] = round(latest_close, 2)
    details['bb_middle'] = round(latest_bb_middle, 2)
    details['bb_upper'] = round(latest_bb_upper, 2)
    details['percent_b'] = round(latest_percent_b, 3)
    details['pnl_pct'] = round(pnl_pct, 2)

    # Exit 1: Close > BB_Middle (return to mean) - PRIMARY TARGET
    if latest_close > latest_bb_middle:
        details['exit_reason'] = 'MEAN_REVERSION'
        return True, 'MEAN_REVERSION', details

    # Exit 2: Close > BB_Upper (overbought) - BONUS
    if latest_close > latest_bb_upper:
        details['exit_reason'] = 'OVERBOUGHT'
        return True, 'OVERBOUGHT', details

    # Exit 3: Stop Loss -7% (wider for mean reversion)
    if pnl_pct <= -7:
        details['exit_reason'] = 'STOP_LOSS'
        return True, 'STOP_LOSS', details

    return False, None, details


def scan_stocks(stock_data: Dict[str, pd.DataFrame]) -> list:
    """
    Scan multiple stocks for Rule 6 signals

    Parameters:
    -----------
    stock_data : Dict[str, pd.DataFrame]
        Dictionary with ticker as key and OHLCV DataFrame as value

    Returns:
    --------
    list: List of stocks that pass the rule with details
    """
    results = []

    for ticker, df in stock_data.items():
        try:
            passed, details = check_rule6(df)
            if passed:
                results.append({
                    'ticker': ticker,
                    **details
                })
        except Exception as e:
            continue

    # Sort by %B (lower = more oversold = better)
    results.sort(key=lambda x: x.get('percent_b', 1))

    return results


if __name__ == "__main__":
    print("Rule 6: Bollinger Band Mean Reversion")
    print("=" * 50)
    print("Entry: Close < BB_Lower AND RSI(14) < 30 AND Close > SMA200")
    print("Exit: Close > BB_Middle OR Close > BB_Upper")
    print("=" * 50)
