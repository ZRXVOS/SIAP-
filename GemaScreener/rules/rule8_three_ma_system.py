"""
Rule 8: Three Moving Average System
====================================
Filosofi: Beli saat pullback dalam trend yang kuat (3 MA sejajar bullish)

ENTRY CONDITIONS:
1. SMA(10) > SMA(20) > SMA(50)   - Bullish alignment
2. Close > SMA(10)               - Price above all MAs
3. Low touches/near SMA(20)      - Pullback to medium MA
4. Close > Open                  - Bullish candle at support

EXIT CONDITIONS:
1. SMA(10) < SMA(20)             - Short-term trend reversal
2. Close < SMA(50)               - Major trend break
3. Trailing Stop: 2x ATR         - Dynamic stop loss

EXPECTED PERFORMANCE:
- Win Rate: ~52%
- Risk:Reward: 1:2
- Avg Holding: 10-20 days
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple


def sma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average"""
    return series.rolling(window=period, min_periods=period).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_val = tr.rolling(window=period, min_periods=period).mean()

    return atr_val


def check_rule8(df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
    """
    Check if stock passes Rule 8: Three Moving Average System

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with columns: Open, High, Low, Close, Volume

    Returns:
    --------
    Tuple[bool, Dict]: (passed, details)
    """
    details = {
        'rule': 8,
        'rule_name': 'Three MA System',
        'passed': False,
        'close': 0,
        'low': 0,
        'sma_10': 0,
        'sma_20': 0,
        'sma_50': 0,
        'pullback_pct': 0,
        'is_aligned': False,
        'is_pullback': False,
        'reason': ''
    }

    # Need at least 55 days of data
    if len(df) < 55:
        details['reason'] = 'Insufficient data (need 55 days)'
        return False, details

    # Standardize column names
    df_copy = df.copy()
    df_copy.columns = [col.lower() for col in df_copy.columns]

    required = ['open', 'high', 'low', 'close']
    for col in required:
        if col not in df_copy.columns:
            details['reason'] = f'Missing column: {col}'
            return False, details

    # Get data
    open_price = df_copy['open']
    high = df_copy['high']
    low = df_copy['low']
    close = df_copy['close']

    # Calculate MAs
    sma_10 = sma(close, 10)
    sma_20 = sma(close, 20)
    sma_50 = sma(close, 50)

    # Get latest values
    latest_close = close.iloc[-1]
    latest_low = low.iloc[-1]
    latest_open = open_price.iloc[-1]
    latest_sma_10 = sma_10.iloc[-1]
    latest_sma_20 = sma_20.iloc[-1]
    latest_sma_50 = sma_50.iloc[-1]

    # Check bullish alignment
    is_aligned = (latest_sma_10 > latest_sma_20) and (latest_sma_20 > latest_sma_50)

    # Check pullback to SMA20 (low within 2% of SMA20)
    pullback_tolerance = 0.02  # 2%
    distance_to_sma20 = abs(latest_low - latest_sma_20) / latest_sma_20
    is_pullback = (latest_low <= latest_sma_20 * (1 + pullback_tolerance)) and \
                  (latest_low >= latest_sma_20 * (1 - pullback_tolerance))

    # Alternative: Low touched SMA20 today or in last 2 days
    for i in range(3):
        idx = -1 - i
        if len(df) > abs(idx):
            day_low = low.iloc[idx]
            day_sma20 = sma_20.iloc[idx]
            if day_low <= day_sma20 * 1.01:  # Within 1% of SMA20
                is_pullback = True
                break

    # Is bullish candle
    is_bullish = latest_close > latest_open

    # Pullback percentage from SMA10
    pullback_pct = ((latest_sma_10 - latest_low) / latest_sma_10 * 100) if latest_sma_10 > 0 else 0

    # Update details
    details['close'] = round(latest_close, 2)
    details['low'] = round(latest_low, 2)
    details['sma_10'] = round(latest_sma_10, 2)
    details['sma_20'] = round(latest_sma_20, 2)
    details['sma_50'] = round(latest_sma_50, 2)
    details['pullback_pct'] = round(pullback_pct, 2)
    details['is_aligned'] = is_aligned
    details['is_pullback'] = is_pullback

    # Condition 1: Bullish alignment (SMA10 > SMA20 > SMA50)
    if not is_aligned:
        details['reason'] = f'Not aligned (10:{latest_sma_10:.0f}, 20:{latest_sma_20:.0f}, 50:{latest_sma_50:.0f})'
        return False, details

    # Condition 2: Price must be above SMA10 (confirmation of recovery)
    if latest_close <= latest_sma_10:
        details['reason'] = f'Close {latest_close:.0f} <= SMA10 {latest_sma_10:.0f}'
        return False, details

    # Condition 3: Pullback to SMA20 area
    if not is_pullback:
        details['reason'] = f'No pullback to SMA20 (Low={latest_low:.0f}, SMA20={latest_sma_20:.0f})'
        return False, details

    # Condition 4: Bullish candle
    if not is_bullish:
        details['reason'] = 'Bearish candle (Close < Open)'
        return False, details

    # All conditions passed
    details['passed'] = True
    details['reason'] = f'Aligned + Pullback {pullback_pct:.1f}%'

    return True, details


def check_exit_rule8(df: pd.DataFrame, entry_price: float) -> Tuple[bool, str, Dict]:
    """
    Check exit conditions for Rule 8

    EXIT CONDITIONS:
    1. SMA(10) < SMA(20) - Short-term trend reversal
    2. Close < SMA(50) - Major trend break
    3. Trailing Stop: 2x ATR
    """
    details = {
        'close': 0,
        'sma_10': 0,
        'sma_20': 0,
        'sma_50': 0,
        'pnl_pct': 0,
        'exit_reason': None
    }

    if len(df) < 55:
        return False, None, details

    df_copy = df.copy()
    df_copy.columns = [col.lower() for col in df_copy.columns]

    close = df_copy['close']
    high = df_copy['high']
    low = df_copy['low']

    sma_10 = sma(close, 10)
    sma_20 = sma(close, 20)
    sma_50 = sma(close, 50)
    atr_14 = atr(high, low, close, 14)

    latest_close = close.iloc[-1]
    latest_sma_10 = sma_10.iloc[-1]
    latest_sma_20 = sma_20.iloc[-1]
    latest_sma_50 = sma_50.iloc[-1]
    latest_atr = atr_14.iloc[-1]

    pnl_pct = ((latest_close - entry_price) / entry_price) * 100

    details['close'] = round(latest_close, 2)
    details['sma_10'] = round(latest_sma_10, 2)
    details['sma_20'] = round(latest_sma_20, 2)
    details['sma_50'] = round(latest_sma_50, 2)
    details['pnl_pct'] = round(pnl_pct, 2)

    # Exit 1: SMA(10) crosses below SMA(20)
    prev_sma_10 = sma_10.iloc[-2]
    prev_sma_20 = sma_20.iloc[-2]
    if (prev_sma_10 >= prev_sma_20) and (latest_sma_10 < latest_sma_20):
        details['exit_reason'] = 'MA_CROSS_DOWN'
        return True, 'MA_CROSS_DOWN', details

    # Exit 2: Close below SMA50
    if latest_close < latest_sma_50:
        details['exit_reason'] = 'BREAKDOWN'
        return True, 'BREAKDOWN', details

    # Exit 3: Trailing Stop (entry - 2x ATR)
    trailing_stop = entry_price - (2 * latest_atr)
    if latest_close < trailing_stop:
        details['exit_reason'] = 'TRAILING_STOP'
        return True, 'TRAILING_STOP', details

    # Exit 4: Take Profit +15%
    if pnl_pct >= 15:
        details['exit_reason'] = 'TAKE_PROFIT'
        return True, 'TAKE_PROFIT', details

    return False, None, details


def scan_stocks(stock_data: Dict[str, pd.DataFrame]) -> list:
    """
    Scan multiple stocks for Rule 8 signals

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
            passed, details = check_rule8(df)
            if passed:
                results.append({
                    'ticker': ticker,
                    **details
                })
        except Exception as e:
            continue

    # Sort by pullback percentage (smaller = better timing)
    results.sort(key=lambda x: x.get('pullback_pct', 100))

    return results


if __name__ == "__main__":
    print("Rule 8: Three Moving Average System")
    print("=" * 50)
    print("Entry: SMA10 > SMA20 > SMA50 + Pullback to SMA20")
    print("Exit: SMA10 < SMA20 OR Close < SMA50 OR Trailing Stop")
    print("=" * 50)
