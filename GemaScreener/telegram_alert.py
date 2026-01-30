"""
GemaScreener Telegram Alert
Mengirim notifikasi hasil screening ke Telegram
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, RUMUS_NAMES


def send_telegram_message(message: str, parse_mode: str = "HTML") -> bool:
    """
    Kirim pesan ke Telegram

    Args:
        message: Pesan yang akan dikirim
        parse_mode: HTML atau Markdown

    Returns:
        True jika berhasil, False jika gagal
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False


def format_screening_alert(results: List[Dict[str, Any]], rule_num: int, max_display: int = 10) -> str:
    """
    Format hasil screening menjadi pesan Telegram

    Args:
        results: List hasil screening yang passed
        rule_num: Nomor rumus (1, 2, atau 3)
        max_display: Maksimal saham yang ditampilkan (default 10)

    Returns:
        String pesan yang diformat
    """
    if not results:
        return ""

    passed = [r for r in results if r.get('passed', False)]

    if not passed:
        return ""

    # Sort by value (highest first) untuk menampilkan yang paling liquid
    passed_sorted = sorted(passed, key=lambda x: x.get('details', {}).get('value', 0), reverse=True)

    # Header
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rule_name = RUMUS_NAMES.get(rule_num, f"Rule {rule_num}")

    message = f"<b>🚨 GEMA SCREENER ALERT</b>\n"
    message += f"<b>Rule {rule_num}: {rule_name}</b>\n"
    message += f"<code>{timestamp}</code>\n"
    message += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    # Limit results untuk Telegram (max 10)
    display_results = passed_sorted[:max_display]

    # Results
    for i, r in enumerate(display_results, 1):
        ticker = r['ticker'].replace('.JK', '')
        details = r.get('details', {})

        # Emoji based on rule
        emoji = "🔥" if rule_num == 1 else ("🚀" if rule_num == 2 else "🔄")

        message += f"{emoji} <b>{ticker}</b>\n"

        # Price and change
        close = details.get('close', 0)
        prev_close = details.get('prev_close', 0)
        if close and prev_close:
            change = ((close - prev_close) / prev_close) * 100
            change_emoji = "📈" if change > 0 else "📉"
            message += f"   {change_emoji} Rp {close:,.0f} ({change:+.1f}%)\n"
        elif close:
            message += f"   💰 Rp {close:,.0f}\n"

        # Value
        value = details.get('value', 0)
        if value:
            message += f"   📊 Value: {value/1e9:.2f}B\n"

        # RSI (simplified)
        rsi = details.get('rsi', 0)
        if rsi and not (rsi != rsi):  # Check for NaN
            rsi_emoji = "🔴" if rsi > 70 else ("🟢" if rsi < 30 else "⚪")
            message += f"   {rsi_emoji} RSI: {rsi:.1f}\n"

        message += "\n"

    # Footer dengan info jika ada lebih banyak
    message += f"━━━━━━━━━━━━━━━━━━━━\n"
    if len(passed) > max_display:
        others = len(passed) - max_display
        other_tickers = [r['ticker'].replace('.JK', '') for r in passed_sorted[max_display:max_display+10]]
        message += f"<i>+{others} lainnya: {', '.join(other_tickers[:10])}</i>\n"
    message += f"<b>Total: {len(passed)} saham terdeteksi</b>\n"
    message += f"<i>⚠️ Bukan rekomendasi investasi</i>"

    return message


def send_screening_alert(results: List[Dict[str, Any]], rule_num: int) -> bool:
    """
    Kirim alert hasil screening ke Telegram

    Args:
        results: List hasil screening
        rule_num: Nomor rumus

    Returns:
        True jika berhasil
    """
    message = format_screening_alert(results, rule_num)

    if not message:
        return False

    return send_telegram_message(message)


def send_combined_alert(all_results: Dict[int, List[Dict[str, Any]]]) -> bool:
    """
    Kirim alert gabungan dari semua rumus

    Args:
        all_results: Dictionary {rule_num: [results]}

    Returns:
        True jika berhasil
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    message = f"<b>🔔 GEMA SCREENER - DAILY SCAN</b>\n"
    message += f"<code>{timestamp}</code>\n"
    message += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    total_found = 0

    for rule_num in [1, 2, 3]:
        results = all_results.get(rule_num, [])
        passed = [r for r in results if r.get('passed', False)]

        rule_name = RUMUS_NAMES.get(rule_num, f"Rule {rule_num}")
        emoji = "🔥" if rule_num == 1 else ("🚀" if rule_num == 2 else "🔄")

        message += f"{emoji} <b>Rule {rule_num}: {rule_name}</b>\n"

        if passed:
            total_found += len(passed)
            tickers = [r['ticker'].replace('.JK', '') for r in passed[:5]]
            message += f"   ✅ {len(passed)} saham: {', '.join(tickers)}"
            if len(passed) > 5:
                message += f" (+{len(passed)-5} lainnya)"
            message += "\n\n"
        else:
            message += f"   ❌ Tidak ada\n\n"

    message += f"━━━━━━━━━━━━━━━━━━━━\n"
    message += f"<b>Total: {total_found} saham terdeteksi</b>\n"
    message += f"<i>⚠️ Bukan rekomendasi investasi</i>"

    return send_telegram_message(message)


def send_error_alert(error_message: str) -> bool:
    """Kirim alert error ke Telegram"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    message = f"⚠️ <b>GEMA SCREENER ERROR</b>\n"
    message += f"<code>{timestamp}</code>\n\n"
    message += f"<code>{error_message}</code>"

    return send_telegram_message(message)


def send_start_notification() -> bool:
    """Kirim notifikasi bahwa screening dimulai"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    message = f"🟢 <b>GEMA SCREENER STARTED</b>\n"
    message += f"<code>{timestamp}</code>\n\n"
    message += f"Screening saham IHSG dimulai..."

    return send_telegram_message(message)


def test_telegram_connection() -> bool:
    """Test koneksi ke Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        if data.get('ok'):
            bot_name = data['result']['username']
            print(f"✅ Telegram connected: @{bot_name}")
            return True
        else:
            print("❌ Telegram connection failed")
            return False

    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False


if __name__ == "__main__":
    # Test koneksi
    print("Testing Telegram connection...")
    if test_telegram_connection():
        # Kirim test message
        test_msg = "🔔 Test dari GemaScreener!\nKoneksi berhasil."
        if send_telegram_message(test_msg):
            print("✅ Test message sent!")
        else:
            print("❌ Failed to send test message")
