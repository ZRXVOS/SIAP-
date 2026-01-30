"""
Rule 7: Breakout with Volume Confirmation
==========================================
Filosofi: Breakout yang valid harus disertai volume tinggi

ENTRY CONDITIONS:
1. Close > High[20]              - 20-day breakout
2. Volume > SMA(20,Vol) * 2      - Volume spike 2x
3. Close > Open                  - Bullish candle
4. ATR expanding (optional)      - Volatility expansion

EXIT CONDITIONS:
1. Take Profit: +10%             - Target hit
2. Stop Loss: -5%                - Risk limit
3. Close < SMA(10)               - Short-term support break

EXPECTED PERFORMANCE:
- Win Rate: ~45%
- Risk:Reward: 1:2 or 1:3
- Avg Holding: 5-15 days
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple


def sma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average"""
    return series.rolling(window=period, min_periods=period).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    high = df['high'] if 'high' in df.columns else df['High']
    low = df['low'] if 'low' in df.columns else df['Low']
    close = df['close'] if 'close' in df.columns else df['Close']

    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_val = tr.rolling(window=period, min_periods=period).mean()

    return atr_val


def check_rule7(df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
    """
    Check if stock passes Rule 7: Breakout with Volume Confirmation

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with columns: Open, High, Low, Close, Volume

    Returns:
    --------
    Tuple[bool, Dict]: (passed, details)
    """
    details = {
        'rule': 7,
        'rule_name': 'Breakout Volume',
        'passed': False,
        'close': 0,
        'high_20': 0,
        'volume_ratio': 0,
        'is_bullish': False,
        'breakout_pct': 0,
        'reason': ''
    }

    # Need at least 25 days of data
    if len(df) < 25:
        details['reason'] = 'Insufficient data (need 25 days)'
        return False, details

    # Standardize column names
    df_copy = df.copy()
    df_copy.columns = [col.lower() for col in df_copy.columns]

    required = ['open', 'high', 'low', 'close', 'volume']
    for col in required:
        if col not in df_copy.columns:
            details['reason'] = f'Missing column: {col}'
            return False, details

    # Get data
    open_price = df_copy['open']
    high = df_copy['high']
    low = df_copy['low']
    close = df_copy['close']
    volume = df_copy['volume']

    # Calculate indicators
    # 20-day high (excluding today)
    high_20 = high.shift(1).rolling(window=20, min_periods=20).max()
    sma_20_vol = sma(volume, 20)

    # Get latest values
    latest_close = close.iloc[-1]
    latest_open = open_price.iloc[-1]
    latest_high_20 = high_20.iloc[-1]
    latest_volume = volume.iloc[-1]
    latest_sma_20_vol = sma_20_vol.iloc[-1]

    # Volume ratio
    volume_ratio = latest_volume / latest_sma_20_vol if latest_sma_20_vol > 0 else 0

    # Is bullish candle (close > open)
    is_bullish = latest_close > latest_open

    # Breakout percentage
    breakout_pct = ((latest_close - latest_high_20) / latest_high_20 * 100) if latest_high_20 > 0 else 0

    # Update details
    details['close'] = round(latest_close, 2)
    details['high_20'] = round(latest_high_20, 2)
    details['volume_ratio'] = round(volume_ratio, 2)
    details['is_bullish'] = is_bullish
    details['breakout_pct'] = round(breakout_pct, 2)

    # Condition 1: Close > 20-day High (breakout)
    if latest_close <= latest_high_20:
        details['reason'] = f'Close {latest_close:.0f} <= High20 {latest_high_20:.0f} (no breakout)'
        return False, details

    # Condition 2: Volume spike (at least 2x average)
    min_volume_ratio = 2.0
    if volume_ratio < min_volume_ratio:
        details['reason'] = f'Volume ratio {volume_ratio:.2f} < {min_volume_ratio}x (need volume spike)'
        return False, details

    # Condition 3: Bullish candle (close > open)
    if not is_bullish:
        details['reason'] = 'Bearish candle (Close < Open)'
        return False, details

    # Condition 4: Breakout must be significant (at least 1%)
    min_breakout_pct = 1.0
    if breakout_pct < min_breakout_pct:
        details['reason'] = f'Breakout only {breakout_pct:.2f}% (need at least {min_breakout_pct}%)'
        return False, details

    # All conditions passed
    details['passed'] = True
    details['reason'] = f'Breakout +{breakout_pct:.1f}%, Vol {volume_ratio:.1f}x'

    return True, details


def check_exit_rule7(df: pd.DataFrame, entry_price: float) -> Tuple[bool, str, Dict]:
    """
    Check exit conditions for Rule 7

    EXIT CONDITIONS:
    1. Take Profit: +10%
    2. Stop Loss: -5%
    3. Close < SMA(10)
    """
    details = {
        'close': 0,
        'sma_10': 0,
        'pnl_pct': 0,
        'exit_reason': None
    }

    if len(df) < 10:
        return False, None, details

    df_copy = df.copy()
    df_copy.columns = [col.lower() for col in df_copy.columns]

    close = df_copy['close']
    sma_10 = sma(close, 10)

    latest_close = close.iloc[-1]
    latest_sma_10 = sma_10.iloc[-1]

    pnl_pct = ((latest_close - entry_price) / entry_price) * 100

    details['close'] = round(latest_close, 2)
    details['sma_10'] = round(latest_sma_10, 2)
    details['pnl_pct'] = round(pnl_pct, 2)

    # Exit 1: Take Profit +10%
    if pnl_pct >= 10:
        details['exit_reason'] = 'TAKE_PROFIT'
        return True, 'TAKE_PROFIT', details

    # Exit 2: Stop Loss -5%
    if pnl_pct <= -5:
        details['exit_reason'] = 'STOP_LOSS'
        return True, 'STOP_LOSS', details

    # Exit 3: Close below SMA(10) - momentum loss
    if latest_close < latest_sma_10:
        details['exit_reason'] = 'MOMENTUM_LOSS'
        return True, 'MOMENTUM_LOSS', details

    return False, None, details


def scan_stocks(stock_data: Dict[str, pd.DataFrame]) -> list:
    """
    Scan multiple stocks for Rule 7 signals

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
            passed, details = check_rule7(df)
            if passed:
                results.append({
                    'ticker': ticker,
                    **details
                })
        except Exception as e:
            continue

    # Sort by volume ratio (higher = stronger breakout)
    results.sort(key=lambda x: x.get('volume_ratio', 0), reverse=True)

    return results


if __name__ == "__main__":
    print("Rule 7: Breakout with Volume Confirmation")
    print("=" * 50)
    print("Entry: Close > High20 AND Volume > 2x AND Bullish")
    print("Exit: TP +10% OR SL -5% OR Close < SMA(10)")
    print("=" * 50)
