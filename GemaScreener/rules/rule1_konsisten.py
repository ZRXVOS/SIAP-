"""
GemaScreener - Rule 1: 9 Hari Konsisten Naik
Deteksi saham yang HIGH selalu > 2% dari CLOSE hari sebelumnya selama 9 hari berturut-turut

Rumus Original:
((high / prev close > 1.02) AND ... 9 hari) AND
(current value > 1B) AND
sma("value",5) > 2b AND
(price > 70 and price < 1600) AND
(close > sma(50) or close > sma(200)) AND
llv("value",5) > 0.5b AND
(volume > prev volume)
# Broker/Foreign data di-skip
"""

import pandas as pd
from typing import Optional, Dict, Any

from config import (
    MIN_PRICE, MAX_PRICE,
    MIN_VALUE_1B, MIN_SMA_VALUE_2B, MIN_VALUE_500M
)

RULE1_NAME = "9 Hari Konsisten Naik"
RULE1_DESCRIPTION = "Saham dengan HIGH > 2% dari prev CLOSE selama 9 hari berturut + volume naik"


def check_consecutive_rise(df: pd.DataFrame, days: int = 9, threshold: float = 1.02) -> bool:
    """
    Cek apakah high/prev_close > threshold selama n hari berturut-turut

    Args:
        df: DataFrame dengan data saham
        days: Jumlah hari berturut-turut
        threshold: Threshold (1.02 = 2%)

    Returns:
        True jika kondisi terpenuhi
    """
    if df is None or len(df) < days + 1:
        return False

    # Ambil data untuk n hari terakhir
    for i in range(days):
        idx = -(i + 1)  # -1, -2, ..., -9
        prev_idx = -(i + 2)  # -2, -3, ..., -10

        if abs(prev_idx) > len(df):
            return False

        current_high = df.iloc[idx]['High']
        prev_close = df.iloc[prev_idx]['Close']

        if prev_close == 0 or pd.isna(prev_close):
            return False

        ratio = current_high / prev_close
        if ratio <= threshold:
            return False

    return True


def check_rule1(df: pd.DataFrame, ticker: str = "") -> Dict[str, Any]:
    """
    Check Rule 1: 9 Hari Konsisten Naik

    Args:
        df: DataFrame dengan data saham (sudah termasuk indikator)
        ticker: Kode saham untuk logging

    Returns:
        Dictionary dengan hasil:
        {
            'passed': bool,
            'ticker': str,
            'details': dict dengan data pendukung,
            'signals': list of triggered conditions
        }
    """
    result = {
        'passed': False,
        'ticker': ticker,
        'rule': 1,
        'rule_name': RULE1_NAME,
        'details': {},
        'signals': []
    }

    # Validasi data
    if df is None or df.empty or len(df) < 15:
        result['signals'].append("Data tidak cukup")
        return result

    # Ambil data terbaru
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None

    # Simpan detail untuk display
    result['details'] = {
        'close': latest.get('Close', 0),
        'volume': latest.get('Volume', 0),
        'value': latest.get('Value', 0),
        'sma_value_5': latest.get('SMA_Value_5', 0),
        'sma50': latest.get('SMA50', 0),
        'sma200': latest.get('SMA200', 0),
        'llv_value_5': latest.get('LLV_Value_5', 0),
        'rsi': latest.get('RSI', 0),
        'prev_volume': prev.get('Volume', 0) if prev is not None else 0
    }

    # ============================================
    # CEK SEMUA KONDISI
    # ============================================

    conditions_met = []
    conditions_failed = []

    # 1. 9 Hari Konsisten (high/prev_close > 1.02)
    if check_consecutive_rise(df, days=9, threshold=1.02):
        conditions_met.append("9 hari konsisten naik > 2%")
    else:
        conditions_failed.append("9 hari tidak konsisten")
        # Cek berapa hari yang konsisten
        for days in [7, 5, 3]:
            if check_consecutive_rise(df, days=days, threshold=1.02):
                result['signals'].append(f"{days} hari konsisten naik")
                break

    # 2. Current Value > 1B
    current_value = latest.get('Value', 0)
    if current_value and current_value > MIN_VALUE_1B:
        conditions_met.append(f"Value > 1B ({current_value/1e9:.2f}B)")
    else:
        conditions_failed.append(f"Value < 1B ({current_value/1e9:.2f}B)")

    # 3. SMA Value 5 > 2B
    sma_value_5 = latest.get('SMA_Value_5', 0)
    if sma_value_5 and sma_value_5 > MIN_SMA_VALUE_2B:
        conditions_met.append(f"SMA Value 5 > 2B ({sma_value_5/1e9:.2f}B)")
    else:
        conditions_failed.append(f"SMA Value 5 < 2B")

    # 4. Price range (70 < price < 1600)
    close_price = latest.get('Close', 0)
    if close_price and MIN_PRICE < close_price < MAX_PRICE:
        conditions_met.append(f"Price dalam range ({close_price:.0f})")
    else:
        conditions_failed.append(f"Price di luar range ({close_price:.0f})")

    # 5. Close > SMA50 atau Close > SMA200
    sma50 = latest.get('SMA50', 0)
    sma200 = latest.get('SMA200', 0)
    if (close_price and sma50 and close_price > sma50) or \
       (close_price and sma200 and close_price > sma200):
        conditions_met.append("Close > SMA50/200")
    else:
        conditions_failed.append("Close < SMA50 & SMA200")

    # 6. LLV Value 5 > 0.5B
    llv_value_5 = latest.get('LLV_Value_5', 0)
    if llv_value_5 and llv_value_5 > MIN_VALUE_500M:
        conditions_met.append(f"LLV Value 5 > 0.5B")
    else:
        conditions_failed.append(f"LLV Value 5 < 0.5B")

    # 7. Volume > Prev Volume
    current_volume = latest.get('Volume', 0)
    prev_volume = prev.get('Volume', 0) if prev is not None else 0
    if current_volume and prev_volume and current_volume > prev_volume:
        vol_change = ((current_volume - prev_volume) / prev_volume) * 100
        conditions_met.append(f"Volume naik {vol_change:.1f}%")
    else:
        conditions_failed.append("Volume tidak naik")

    # ============================================
    # EVALUASI HASIL
    # ============================================

    result['signals'] = conditions_met
    result['failed'] = conditions_failed

    # Semua kondisi harus terpenuhi (kecuali broker/foreign yang di-skip)
    # Total 7 kondisi
    if len(conditions_met) >= 7:
        result['passed'] = True

    return result


def get_rule1_summary(results: list) -> str:
    """Generate summary text untuk Rule 1"""
    passed = [r for r in results if r['passed']]

    if not passed:
        return "Tidak ada saham yang memenuhi Rule 1 (9 Hari Konsisten Naik)"

    summary = f"=== RULE 1: {RULE1_NAME} ===\n"
    summary += f"Total: {len(passed)} saham\n\n"

    for r in passed:
        ticker = r['ticker'].replace('.JK', '')
        details = r['details']
        summary += f"{ticker}\n"
        summary += f"  Close: {details['close']:,.0f}\n"
        summary += f"  Value: {details['value']/1e9:.2f}B\n"
        summary += f"  RSI: {details['rsi']:.1f}\n"
        summary += f"  Signals: {', '.join(r['signals'][:3])}\n\n"

    return summary
