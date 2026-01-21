"""
GemaScreener - Rule 3: Reversal / Hammer Pattern
Deteksi saham yang menunjukkan pola reversal/hammer

Rumus Original (broker/foreign skipped):
(low / prev close < 0.95 or low / open < 0.95) AND
close > open AND
value > 2b AND
(Engulfing pattern OR New low recovery) AND
sma("value",5) > 2b AND
(price > 70 and price < 1600) AND
(close > sma(50) or close > sma(200)) AND
llv("value",5) > 0.5b
"""

import pandas as pd
from typing import Optional, Dict, Any

from config import (
    MIN_PRICE, MAX_PRICE,
    MIN_VALUE_2B, MIN_SMA_VALUE_2B, MIN_VALUE_500M
)

RULE3_NAME = "Reversal / Hammer Pattern"
RULE3_DESCRIPTION = "Saham dengan pola hammer/reversal + shadow bawah panjang"


def check_rule3(df: pd.DataFrame, ticker: str = "") -> Dict[str, Any]:
    """
    Check Rule 3: Reversal / Hammer Pattern

    Args:
        df: DataFrame dengan data saham (sudah termasuk indikator)
        ticker: Kode saham untuk logging

    Returns:
        Dictionary dengan hasil screening
    """
    result = {
        'passed': False,
        'ticker': ticker,
        'rule': 3,
        'rule_name': RULE3_NAME,
        'details': {},
        'signals': [],
        'failed': []
    }

    # Validasi data
    if df is None or df.empty or len(df) < 15:
        result['failed'].append("Data tidak cukup")
        return result

    # Ambil data terbaru dan sebelumnya
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None

    if prev is None:
        result['failed'].append("Tidak ada data sebelumnya")
        return result

    # Extract values
    open_price = latest.get('Open', 0)
    high = latest.get('High', 0)
    low = latest.get('Low', 0)
    close = latest.get('Close', 0)
    volume = latest.get('Volume', 0)
    value = latest.get('Value', 0)

    prev_open = prev.get('Open', 0)
    prev_high = prev.get('High', 0)
    prev_low = prev.get('Low', 0)
    prev_close = prev.get('Close', 0)

    # Calculate candle body and shadows
    body = abs(close - open_price)
    upper_shadow = high - max(open_price, close)
    lower_shadow = min(open_price, close) - low
    total_range = high - low if high != low else 1

    # Simpan detail
    result['details'] = {
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
        'value': value,
        'prev_close': prev_close,
        'body': body,
        'lower_shadow': lower_shadow,
        'upper_shadow': upper_shadow,
        'shadow_ratio': lower_shadow / total_range if total_range else 0,
        'rsi': latest.get('RSI', 0),
        'sma50': latest.get('SMA50', 0),
        'sma200': latest.get('SMA200', 0)
    }

    conditions_met = []
    conditions_failed = []

    # ============================================
    # CEK KONDISI UTAMA
    # ============================================

    # 1. Shadow bawah panjang (low/prev_close < 0.95 OR low/open < 0.95)
    shadow_condition1 = False
    shadow_condition2 = False

    if prev_close and low:
        ratio1 = low / prev_close
        if ratio1 < 0.95:
            shadow_condition1 = True
            conditions_met.append(f"Low/PrevClose = {ratio1:.3f} (< 0.95)")

    if open_price and low:
        ratio2 = low / open_price
        if ratio2 < 0.95:
            shadow_condition2 = True
            conditions_met.append(f"Low/Open = {ratio2:.3f} (< 0.95)")

    if not shadow_condition1 and not shadow_condition2:
        conditions_failed.append("Shadow bawah tidak cukup panjang")

    # 2. Bullish candle (Close > Open)
    if close and open_price and close > open_price:
        change = ((close - open_price) / open_price) * 100
        conditions_met.append(f"Bullish candle (+{change:.1f}%)")
    else:
        conditions_failed.append("Bearish candle")

    # 3. Value > 2B
    if value and value > MIN_VALUE_2B:
        conditions_met.append(f"Value > 2B ({value/1e9:.2f}B)")
    else:
        conditions_failed.append(f"Value < 2B ({value/1e9:.2f}B)")

    # 4. Engulfing Pattern atau New Low Recovery
    pattern_found = False

    # Engulfing Pattern:
    # low <= prev_low AND high >= prev_high AND close > open AND prev_close < prev_open
    is_engulfing = (
        low and prev_low and low <= prev_low and
        high and prev_high and high >= prev_high and
        close and open_price and close > open_price and
        prev_close and prev_open and prev_close < prev_open
    )

    if is_engulfing:
        pattern_found = True
        conditions_met.append("Bullish Engulfing Pattern")

    # New Low Recovery:
    # prev_low < prev_llv_low_9 AND value > 2B AND close > open
    prev_llv_low_9 = latest.get('Prev_LLV_Low_9', 0)
    is_new_low_recovery = (
        prev_low and prev_llv_low_9 and prev_low < prev_llv_low_9 and
        value and value > MIN_VALUE_2B and
        close and open_price and close > open_price
    )

    if is_new_low_recovery:
        pattern_found = True
        conditions_met.append("New Low Recovery")

    if not pattern_found:
        # Check for simple hammer pattern (lower shadow > 2x body)
        if lower_shadow > 2 * body and body > 0:
            pattern_found = True
            conditions_met.append(f"Hammer Pattern (shadow/body = {lower_shadow/body:.1f})")
        else:
            conditions_failed.append("Tidak ada pattern reversal")

    # 5. SMA Value 5 > 2B
    sma_value_5 = latest.get('SMA_Value_5', 0)
    if sma_value_5 and sma_value_5 > MIN_SMA_VALUE_2B:
        conditions_met.append("SMA Value 5 > 2B")
    else:
        conditions_failed.append("SMA Value 5 < 2B")

    # 6. Price range (70 < price < 1600)
    if close and MIN_PRICE < close < MAX_PRICE:
        conditions_met.append(f"Price OK ({close:.0f})")
    else:
        conditions_failed.append(f"Price di luar range")

    # 7. Close > SMA50 atau Close > SMA200
    sma50 = latest.get('SMA50', 0)
    sma200 = latest.get('SMA200', 0)
    if (close and sma50 and close > sma50) or (close and sma200 and close > sma200):
        conditions_met.append("Close > SMA50/200")
    else:
        conditions_failed.append("Close < SMA50 & SMA200")

    # 8. LLV Value 5 > 0.5B
    llv_value_5 = latest.get('LLV_Value_5', 0)
    if llv_value_5 and llv_value_5 > MIN_VALUE_500M:
        conditions_met.append("LLV Value 5 > 0.5B")
    else:
        conditions_failed.append("LLV Value 5 < 0.5B")

    # ============================================
    # ADDITIONAL QUALITY CHECKS
    # ============================================

    # Lower shadow should be significant (> 30% of total range)
    shadow_ratio = lower_shadow / total_range if total_range > 0 else 0
    if shadow_ratio > 0.3:
        conditions_met.append(f"Shadow ratio {shadow_ratio:.0%}")

    # ============================================
    # EVALUASI HASIL
    # ============================================

    result['signals'] = conditions_met
    result['failed'] = conditions_failed

    # Untuk Rule 3, minimal 6 kondisi harus terpenuhi
    min_conditions = 6

    if len(conditions_met) >= min_conditions:
        result['passed'] = True

    return result


def get_rule3_summary(results: list) -> str:
    """Generate summary text untuk Rule 3"""
    passed = [r for r in results if r['passed']]

    if not passed:
        return "Tidak ada saham yang memenuhi Rule 3 (Reversal/Hammer)"

    summary = f"=== RULE 3: {RULE3_NAME} ===\n"
    summary += f"Total: {len(passed)} saham\n\n"

    for r in passed:
        ticker = r['ticker'].replace('.JK', '')
        details = r['details']

        summary += f"{ticker}\n"
        summary += f"  Close: {details['close']:,.0f}\n"
        summary += f"  Value: {details['value']/1e9:.2f}B\n"
        summary += f"  Shadow Ratio: {details['shadow_ratio']:.0%}\n"

        # Find pattern
        patterns = [s for s in r['signals'] if 'Pattern' in s or 'Recovery' in s or 'Engulfing' in s]
        if patterns:
            summary += f"  Pattern: {patterns[0]}\n"

        summary += f"  RSI: {details['rsi']:.1f}\n\n"

    return summary
