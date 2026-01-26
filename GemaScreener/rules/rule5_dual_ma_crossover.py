"""
Rule 5: Dual Moving Average Crossover
======================================
Filosofi: Ikuti trend - beli saat MA cepat cross di atas MA lambat

ENTRY CONDITIONS:
1. SMA(20) crosses above SMA(50)  - Golden Cross
2. Close > SMA(20)                - Price confirmation
3. Volume > SMA(20,Vol) * 1.5     - Volume spike 50%

EXIT CONDITIONS:
1. SMA(20) crosses below SMA(50)  - Death Cross
2. Close < SMA(50)                - Breakdown support
3. Stop Loss: -5%                 - Risk management

EXPECTED PERFORMANCE:
- Win Rate: ~55%
- Risk:Reward: 1:2
- Avg Holding: 15-30 days
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple


def sma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average"""
    return series.rolling(window=period, min_periods=period).mean()


def check_rule5(df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
    """
    Check if stock passes Rule 5: Dual MA Crossover (Golden Cross)

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with columns: Open, High, Low, Close, Volume

    Returns:
    --------
    Tuple[bool, Dict]: (passed, details)
    """
    details = {
        'rule': 5,
        'rule_name': 'Dual MA Crossover',
        'passed': False,
        'close': 0,
        'sma_20': 0,
        'sma_50': 0,
        'volume_ratio': 0,
        'cross_type': '',
        'reason': ''
    }

    # Need at least 50 days of data
    if len(df) < 52:
        details['reason'] = 'Insufficient data (need 52 days)'
        return False, details

    # Standardize column names
    df_copy = df.copy()
    df_copy.columns = [col.lower() for col in df_copy.columns]

    required = ['close', 'volume']
    for col in required:
        if col not in df_copy.columns:
            details['reason'] = f'Missing column: {col}'
            return False, details

    # Calculate indicators
    close = df_copy['close']
    volume = df_copy['volume']

    sma_20 = sma(close, 20)
    sma_50 = sma(close, 50)
    sma_20_vol = sma(volume, 20)

    # Get current and previous values
    curr_sma_20 = sma_20.iloc[-1]
    curr_sma_50 = sma_50.iloc[-1]
    prev_sma_20 = sma_20.iloc[-2]
    prev_sma_50 = sma_50.iloc[-2]

    latest_close = close.iloc[-1]
    latest_volume = volume.iloc[-1]
    latest_sma_20_vol = sma_20_vol.iloc[-1]

    # Volume ratio
    volume_ratio = latest_volume / latest_sma_20_vol if latest_sma_20_vol > 0 else 0

    # Update details
    details['close'] = round(latest_close, 2)
    details['sma_20'] = round(curr_sma_20, 2)
    details['sma_50'] = round(curr_sma_50, 2)
    details['volume_ratio'] = round(volume_ratio, 2)

    # Check for Golden Cross (SMA20 crosses above SMA50)
    golden_cross = (prev_sma_20 <= prev_sma_50) and (curr_sma_20 > curr_sma_50)

    # Alternative: Already in bullish alignment (within 3 days of cross)
    bullish_alignment = curr_sma_20 > curr_sma_50

    # Check for recent cross (within last 3 days)
    recent_cross = False
    for i in range(1, min(4, len(df) - 1)):
        prev_20 = sma_20.iloc[-i-1]
        prev_50 = sma_50.iloc[-i-1]
        if prev_20 <= prev_50:
            recent_cross = True
            break

    if golden_cross:
        details['cross_type'] = 'GOLDEN_CROSS_TODAY'
    elif recent_cross and bullish_alignment:
        details['cross_type'] = 'GOLDEN_CROSS_RECENT'
    elif bullish_alignment:
        details['cross_type'] = 'BULLISH_ALIGNMENT'
    else:
        details['cross_type'] = 'NONE'

    # Condition 1: Golden Cross or recent cross with bullish alignment
    if not (golden_cross or (recent_cross and bullish_alignment)):
        details['reason'] = f'No Golden Cross (SMA20={curr_sma_20:.0f}, SMA50={curr_sma_50:.0f})'
        return False, details

    # Condition 2: Price above SMA20
    if latest_close <= curr_sma_20:
        details['reason'] = f'Close {latest_close:.0f} <= SMA20 {curr_sma_20:.0f}'
        return False, details

    # Condition 3: Volume spike (at least 1.5x average)
    min_volume_ratio = 1.5
    if volume_ratio < min_volume_ratio:
        details['reason'] = f'Volume ratio {volume_ratio:.2f} < {min_volume_ratio} (need spike)'
        return False, details

    # All conditions passed
    details['passed'] = True
    details['reason'] = f'{details["cross_type"]}, Vol {volume_ratio:.1f}x'

    return True, details


def check_exit_rule5(df: pd.DataFrame, entry_price: float) -> Tuple[bool, str, Dict]:
    """
    Check exit conditions for Rule 5

    EXIT CONDITIONS:
    1. Death Cross: SMA(20) crosses below SMA(50)
    2. Breakdown: Close < SMA(50)
    3. Stop Loss: -5%
    """
    details = {
        'close': 0,
        'sma_20': 0,
        'sma_50': 0,
        'pnl_pct': 0,
        'exit_reason': None
    }

    if len(df) < 52:
        return False, None, details

    df_copy = df.copy()
    df_copy.columns = [col.lower() for col in df_copy.columns]

    close = df_copy['close']
    sma_20 = sma(close, 20)
    sma_50 = sma(close, 50)

    curr_sma_20 = sma_20.iloc[-1]
    curr_sma_50 = sma_50.iloc[-1]
    prev_sma_20 = sma_20.iloc[-2]
    prev_sma_50 = sma_50.iloc[-2]
    latest_close = close.iloc[-1]

    pnl_pct = ((latest_close - entry_price) / entry_price) * 100

    details['close'] = round(latest_close, 2)
    details['sma_20'] = round(curr_sma_20, 2)
    details['sma_50'] = round(curr_sma_50, 2)
    details['pnl_pct'] = round(pnl_pct, 2)

    # Exit 1: Death Cross
    death_cross = (prev_sma_20 >= prev_sma_50) and (curr_sma_20 < curr_sma_50)
    if death_cross:
        details['exit_reason'] = 'DEATH_CROSS'
        return True, 'DEATH_CROSS', details

    # Exit 2: Close below SMA50
    if latest_close < curr_sma_50:
        details['exit_reason'] = 'BREAKDOWN'
        return True, 'BREAKDOWN', details

    # Exit 3: Stop Loss -5%
    if pnl_pct <= -5:
        details['exit_reason'] = 'STOP_LOSS'
        return True, 'STOP_LOSS', details

    # Exit 4: Take Profit +10% (optional)
    if pnl_pct >= 10:
        details['exit_reason'] = 'TAKE_PROFIT'
        return True, 'TAKE_PROFIT', details

    return False, None, details


def scan_stocks(stock_data: Dict[str, pd.DataFrame]) -> list:
    """
    Scan multiple stocks for Rule 5 signals

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
            passed, details = check_rule5(df)
            if passed:
                results.append({
                    'ticker': ticker,
                    **details
                })
        except Exception as e:
            continue

    # Sort by volume ratio (higher = stronger signal)
    results.sort(key=lambda x: x.get('volume_ratio', 0), reverse=True)

    return results


if __name__ == "__main__":
    print("Rule 5: Dual Moving Average Crossover")
    print("=" * 50)
    print("Entry: SMA(20) cross above SMA(50) + Volume 1.5x")
    print("Exit: Death Cross OR Close < SMA(50) OR SL -5%")
    print("=" * 50)
