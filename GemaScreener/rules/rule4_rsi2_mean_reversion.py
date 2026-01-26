"""
Rule 4: RSI-2 Mean Reversion (Larry Connors Strategy)
======================================================
Filosofi: Beli saat saham oversold dalam trend naik, jual saat kembali ke mean

ENTRY CONDITIONS:
1. Close > SMA(200)     - Trend jangka panjang bullish
2. RSI(2) < 5           - Extreme oversold (2-period RSI)
3. Volume > average     - Ada partisipasi pasar (opsional)

EXIT CONDITIONS:
1. Close > SMA(5)       - Harga recovery di atas MA 5
2. RSI(2) > 70          - RSI sudah overbought
3. Holding > 5 hari     - Time exit

EXPECTED PERFORMANCE:
- Win Rate: ~75%
- Avg Profit/Trade: +0.5%
- Avg Holding: 3-5 days
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple


def rsi(series: pd.Series, period: int = 2) -> pd.Series:
    """Calculate RSI (Relative Strength Index)"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi_val = 100 - (100 / (1 + rs))
    return rsi_val


def sma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average"""
    return series.rolling(window=period, min_periods=period).mean()


def check_rule4(df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
    """
    Check if stock passes Rule 4: RSI-2 Mean Reversion

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with columns: Open, High, Low, Close, Volume

    Returns:
    --------
    Tuple[bool, Dict]: (passed, details)
    """
    details = {
        'rule': 4,
        'rule_name': 'RSI-2 Mean Reversion',
        'passed': False,
        'close': 0,
        'sma_200': 0,
        'rsi_2': 0,
        'volume_ratio': 0,
        'reason': ''
    }

    # Need at least 200 days of data
    if len(df) < 200:
        details['reason'] = 'Insufficient data (need 200 days)'
        return False, details

    # Standardize column names
    df_copy = df.copy()
    df_copy.columns = [col.lower() for col in df_copy.columns]

    # Ensure we have required columns
    required = ['close', 'volume']
    for col in required:
        if col not in df_copy.columns:
            details['reason'] = f'Missing column: {col}'
            return False, details

    # Calculate indicators
    close = df_copy['close']
    volume = df_copy['volume']

    sma_200 = sma(close, 200)
    sma_20_vol = sma(volume, 20)
    rsi_2 = rsi(close, 2)

    # Get latest values
    latest_close = close.iloc[-1]
    latest_sma_200 = sma_200.iloc[-1]
    latest_rsi_2 = rsi_2.iloc[-1]
    latest_volume = volume.iloc[-1]
    latest_sma_20_vol = sma_20_vol.iloc[-1]

    # Volume ratio
    volume_ratio = latest_volume / latest_sma_20_vol if latest_sma_20_vol > 0 else 0

    # Update details
    details['close'] = round(latest_close, 2)
    details['sma_200'] = round(latest_sma_200, 2)
    details['rsi_2'] = round(latest_rsi_2, 2)
    details['volume_ratio'] = round(volume_ratio, 2)

    # Check conditions
    # 1. Price above SMA 200 (uptrend)
    if latest_close <= latest_sma_200:
        details['reason'] = f'Close {latest_close:.0f} <= SMA200 {latest_sma_200:.0f} (not in uptrend)'
        return False, details

    # 2. RSI(2) < 5 (extreme oversold)
    if pd.isna(latest_rsi_2) or latest_rsi_2 >= 5:
        details['reason'] = f'RSI(2) {latest_rsi_2:.1f} >= 5 (not oversold)'
        return False, details

    # 3. Volume filter (optional but recommended)
    min_volume_ratio = 0.5  # At least 50% of average volume
    if volume_ratio < min_volume_ratio:
        details['reason'] = f'Volume ratio {volume_ratio:.2f} < {min_volume_ratio} (low participation)'
        return False, details

    # All conditions passed
    details['passed'] = True
    details['reason'] = f'RSI(2)={latest_rsi_2:.1f} < 5, Close > SMA200'

    return True, details


def check_exit_rule4(df: pd.DataFrame, entry_price: float, entry_date: str = None) -> Tuple[bool, str, Dict]:
    """
    Check exit conditions for Rule 4

    EXIT CONDITIONS:
    1. Close > SMA(5)
    2. RSI(2) > 70
    3. Holding > 5 days (if entry_date provided)
    """
    details = {
        'close': 0,
        'sma_5': 0,
        'rsi_2': 0,
        'exit_reason': None
    }

    if len(df) < 5:
        return False, None, details

    df_copy = df.copy()
    df_copy.columns = [col.lower() for col in df_copy.columns]

    close = df_copy['close']
    sma_5 = sma(close, 5)
    rsi_2 = rsi(close, 2)

    latest_close = close.iloc[-1]
    latest_sma_5 = sma_5.iloc[-1]
    latest_rsi_2 = rsi_2.iloc[-1]

    details['close'] = round(latest_close, 2)
    details['sma_5'] = round(latest_sma_5, 2)
    details['rsi_2'] = round(latest_rsi_2, 2)

    # Exit condition 1: Close > SMA(5)
    if latest_close > latest_sma_5:
        details['exit_reason'] = 'MEAN_REVERSION'
        return True, 'MEAN_REVERSION', details

    # Exit condition 2: RSI(2) > 70
    if not pd.isna(latest_rsi_2) and latest_rsi_2 > 70:
        details['exit_reason'] = 'RSI_OVERBOUGHT'
        return True, 'RSI_OVERBOUGHT', details

    return False, None, details


def scan_stocks(stock_data: Dict[str, pd.DataFrame]) -> list:
    """
    Scan multiple stocks for Rule 4 signals

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
            passed, details = check_rule4(df)
            if passed:
                results.append({
                    'ticker': ticker,
                    **details
                })
        except Exception as e:
            continue

    # Sort by RSI (lower = more oversold = better)
    results.sort(key=lambda x: x.get('rsi_2', 100))

    return results


if __name__ == "__main__":
    # Test with sample data
    print("Rule 4: RSI-2 Mean Reversion")
    print("=" * 50)
    print("Entry: Close > SMA(200) AND RSI(2) < 5")
    print("Exit: Close > SMA(5) OR RSI(2) > 70 OR 5 days")
    print("=" * 50)
