"""
GemaScreener - Rule 2: Breakout Kuat + Momentum
Deteksi saham yang breakout dengan momentum kuat

Rumus Original (simplified, broker/foreign skipped):
(close / prev close >= 1.08) AND value > 5b AND
(stoch_k > stoch_d or rsi(14) > 70 or stoch_k > 80) AND
sma("value",5) > 2b AND
(volume breakout OR price breakout) AND
cmf(2) > 0 AND volume > prev volume AND
open >= prev close AND
(atr(1)/close)*100 > 3 AND
(price > 70 and price < 1600) AND
(close > sma(50) or close > sma(200)) AND
llv("value",5) > 0.5b

+ Kondisi 5-menit (jika data tersedia)
"""

import pandas as pd
from typing import Optional, Dict, Any

from config import (
    MIN_PRICE, MAX_PRICE,
    MIN_VALUE_1B, MIN_VALUE_5B, MIN_SMA_VALUE_2B, MIN_VALUE_500M,
    RSI_OVERBOUGHT, STOCH_OVERBOUGHT
)

RULE2_NAME = "Breakout Kuat + Momentum"
RULE2_DESCRIPTION = "Saham naik >= 8% dengan volume breakout + momentum indicators"


def check_rule2(df: pd.DataFrame, df_intraday: pd.DataFrame = None,
                ticker: str = "") -> Dict[str, Any]:
    """
    Check Rule 2: Breakout Kuat + Momentum

    Args:
        df: DataFrame dengan data harian (sudah termasuk indikator)
        df_intraday: DataFrame dengan data 5-menit (optional)
        ticker: Kode saham untuk logging

    Returns:
        Dictionary dengan hasil screening
    """
    result = {
        'passed': False,
        'ticker': ticker,
        'rule': 2,
        'rule_name': RULE2_NAME,
        'details': {},
        'signals': [],
        'failed': []
    }

    # Validasi data
    if df is None or df.empty or len(df) < 25:
        result['failed'].append("Data tidak cukup")
        return result

    # Ambil data terbaru
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None

    if prev is None:
        result['failed'].append("Tidak ada data sebelumnya")
        return result

    # Simpan detail untuk display
    close = latest.get('Close', 0)
    prev_close = prev.get('Close', 0)
    change_pct = ((close - prev_close) / prev_close * 100) if prev_close else 0

    result['details'] = {
        'close': close,
        'prev_close': prev_close,
        'change_pct': change_pct,
        'volume': latest.get('Volume', 0),
        'value': latest.get('Value', 0),
        'rsi': latest.get('RSI', 0),
        'stoch_k': latest.get('Stoch_K', 0),
        'stoch_d': latest.get('Stoch_D', 0),
        'cmf': latest.get('CMF_2', 0),
        'atr_pct': latest.get('ATR_Percent', 0),
        'sma50': latest.get('SMA50', 0),
        'sma200': latest.get('SMA200', 0)
    }

    conditions_met = []
    conditions_failed = []

    # ============================================
    # CEK KONDISI UTAMA
    # ============================================

    # 1. Close naik >= 8% dari prev close
    if prev_close and close:
        ratio = close / prev_close
        if ratio >= 1.08:
            conditions_met.append(f"Naik {change_pct:.1f}%")
        else:
            conditions_failed.append(f"Naik hanya {change_pct:.1f}% (< 8%)")

    # 2. Value > 5B
    value = latest.get('Value', 0)
    if value and value > MIN_VALUE_5B:
        conditions_met.append(f"Value > 5B ({value/1e9:.2f}B)")
    else:
        conditions_failed.append(f"Value < 5B")

    # 3. Momentum indicators (stoch_k > stoch_d OR rsi > 70 OR stoch_k > 80)
    stoch_k = latest.get('Stoch_K', 0)
    stoch_d = latest.get('Stoch_D', 0)
    rsi = latest.get('RSI', 0)

    momentum_ok = False
    momentum_signals = []

    if stoch_k and stoch_d and stoch_k > stoch_d:
        momentum_ok = True
        momentum_signals.append(f"Stoch K({stoch_k:.0f}) > D({stoch_d:.0f})")

    if rsi and rsi > RSI_OVERBOUGHT:
        momentum_ok = True
        momentum_signals.append(f"RSI {rsi:.0f} > 70")

    if stoch_k and stoch_k > STOCH_OVERBOUGHT:
        momentum_ok = True
        momentum_signals.append(f"Stoch K {stoch_k:.0f} > 80")

    if momentum_ok:
        conditions_met.append(f"Momentum: {', '.join(momentum_signals)}")
    else:
        conditions_failed.append("Momentum lemah")

    # 4. SMA Value 5 > 2B
    sma_value_5 = latest.get('SMA_Value_5', 0)
    if sma_value_5 and sma_value_5 > MIN_SMA_VALUE_2B:
        conditions_met.append("SMA Value 5 > 2B")
    else:
        conditions_failed.append("SMA Value 5 < 2B")

    # 5. Volume Breakout atau Price Breakout
    volume = latest.get('Volume', 0)
    prev_volume = prev.get('Volume', 0)
    prev_hhv_volume = latest.get('Prev_HHV_Volume_9', 0)
    prev_hhv_high = latest.get('Prev_HHV_High_20', 0)

    breakout_ok = False
    breakout_signals = []

    # Volume breakout: prev_volume < prev_hhv_volume AND volume > prev_hhv_volume
    if prev_volume and prev_hhv_volume and volume:
        if prev_volume < prev_hhv_volume and volume > prev_hhv_volume:
            breakout_ok = True
            breakout_signals.append("Volume Breakout")

    # Price breakout: prev_close < prev_hhv_high AND close > prev_hhv_high
    if prev_close and prev_hhv_high and close:
        if prev_close < prev_hhv_high and close > prev_hhv_high:
            breakout_ok = True
            breakout_signals.append("Price Breakout")

    if breakout_ok:
        conditions_met.append(f"Breakout: {', '.join(breakout_signals)}")
    else:
        conditions_failed.append("Tidak ada breakout")

    # 6. CMF(2) > 0
    cmf = latest.get('CMF_2', 0)
    if cmf and cmf > 0:
        conditions_met.append(f"CMF > 0 ({cmf:.3f})")
    else:
        conditions_failed.append(f"CMF < 0 ({cmf:.3f})")

    # 7. Volume > Prev Volume
    if volume and prev_volume and volume > prev_volume:
        vol_change = ((volume - prev_volume) / prev_volume) * 100
        conditions_met.append(f"Vol naik {vol_change:.1f}%")
    else:
        conditions_failed.append("Volume tidak naik")

    # 8. Open >= Prev Close (Gap up atau flat open)
    open_price = latest.get('Open', 0)
    if open_price and prev_close and open_price >= prev_close:
        gap_pct = ((open_price - prev_close) / prev_close) * 100
        conditions_met.append(f"Gap up {gap_pct:.1f}%")
    else:
        conditions_failed.append("Gap down")

    # 9. ATR% > 3%
    atr_pct = latest.get('ATR_Percent', 0)
    if atr_pct and atr_pct > 3:
        conditions_met.append(f"ATR {atr_pct:.1f}% > 3%")
    else:
        conditions_failed.append(f"ATR {atr_pct:.1f}% < 3%")

    # 10. Price range (70 < price < 1600)
    if close and MIN_PRICE < close < MAX_PRICE:
        conditions_met.append(f"Price OK ({close:.0f})")
    else:
        conditions_failed.append(f"Price di luar range")

    # 11. Close > SMA50 atau Close > SMA200
    sma50 = latest.get('SMA50', 0)
    sma200 = latest.get('SMA200', 0)
    if (close and sma50 and close > sma50) or (close and sma200 and close > sma200):
        conditions_met.append("Close > SMA50/200")
    else:
        conditions_failed.append("Close < SMA50 & SMA200")

    # 12. LLV Value 5 > 0.5B
    llv_value_5 = latest.get('LLV_Value_5', 0)
    if llv_value_5 and llv_value_5 > MIN_VALUE_500M:
        conditions_met.append("LLV Value 5 > 0.5B")
    else:
        conditions_failed.append("LLV Value 5 < 0.5B")

    # ============================================
    # CEK KONDISI 5-MENIT (jika data tersedia)
    # ============================================
    intraday_met = 0
    intraday_total = 0

    if df_intraday is not None and not df_intraday.empty:
        intraday_latest = df_intraday.iloc[-1]

        # 5min close >= 5min hhv("high",20)
        intraday_total += 1
        close_5m = intraday_latest.get('Close', 0)
        hhv_high_20 = intraday_latest.get('HHV_High_20', 0)
        if close_5m and hhv_high_20 and close_5m >= hhv_high_20:
            intraday_met += 1
            conditions_met.append("5m: Close >= HHV High 20")

        # 5min close > 5min sma("5min close", 20)
        intraday_total += 1
        sma20_5m = intraday_latest.get('Close_SMA20', 0)
        if close_5m and sma20_5m and close_5m > sma20_5m:
            intraday_met += 1
            conditions_met.append("5m: Close > SMA20")

        # 5min close > 5min sma("5min close", 200)
        intraday_total += 1
        sma200_5m = intraday_latest.get('Close_SMA200', 0)
        if close_5m and sma200_5m and close_5m > sma200_5m:
            intraday_met += 1
            conditions_met.append("5m: Close > SMA200")

        # Bollinger condition
        intraday_total += 1
        bb_middle = intraday_latest.get('BB_Middle', 0)
        if bb_middle and close_5m and (bb_middle / close_5m) < 1.05:
            intraday_met += 1
            conditions_met.append("5m: Bollinger OK")

        result['details']['intraday_met'] = intraday_met
        result['details']['intraday_total'] = intraday_total

    # ============================================
    # EVALUASI HASIL
    # ============================================

    result['signals'] = conditions_met
    result['failed'] = conditions_failed

    # Untuk Rule 2, minimal 10 dari 12 kondisi harian harus terpenuhi
    # (lebih relaxed karena kondisi sangat ketat)
    min_conditions = 8

    if len(conditions_met) >= min_conditions:
        result['passed'] = True

    return result


def get_rule2_summary(results: list) -> str:
    """Generate summary text untuk Rule 2"""
    passed = [r for r in results if r['passed']]

    if not passed:
        return "Tidak ada saham yang memenuhi Rule 2 (Breakout Kuat)"

    summary = f"=== RULE 2: {RULE2_NAME} ===\n"
    summary += f"Total: {len(passed)} saham\n\n"

    for r in passed:
        ticker = r['ticker'].replace('.JK', '')
        details = r['details']
        summary += f"{ticker}\n"
        summary += f"  Close: {details['close']:,.0f} ({details['change_pct']:+.1f}%)\n"
        summary += f"  Value: {details['value']/1e9:.2f}B\n"
        summary += f"  RSI: {details['rsi']:.1f}, Stoch: {details['stoch_k']:.0f}\n"
        summary += f"  Signals: {len(r['signals'])} kondisi terpenuhi\n\n"

    return summary
