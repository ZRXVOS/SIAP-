#!/usr/bin/env python3
"""
GemaScreener - Stock Screening Tool untuk IHSG
Deteksi pergerakan bandar dan anomali volume

Usage:
    python main.py                          # Jalankan rules 4,5,6,7 (default)
    python main.py --all                    # Jalankan rules 4,5,6,7
    python main.py --rules 4,5,6,7          # Jalankan rules tertentu
    python main.py --rumus 4                # Jalankan rumus 4 saja
    python main.py --rumus 5                # Jalankan rumus 5 saja
    python main.py --rumus 6                # Jalankan rumus 6 saja
    python main.py --rumus 7                # Jalankan rumus 7 saja
    python main.py --all --auto             # Auto-schedule setiap 5 menit
    python main.py --all --no-telegram      # Tanpa kirim ke Telegram
    python main.py --test                   # Test koneksi Telegram

Rules:
    4: RSI-2 Mean Reversion (Larry Connors)
    5: Dual MA Crossover (Golden Cross)
    6: Bollinger Band Mean Reversion
    7: Breakout with Volume
"""

import argparse
import sys
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from tabulate import tabulate

from config import Colors, RUMUS_NAMES, SCHEDULE_INTERVAL
from watchlist import get_watchlist_with_suffix, TOTAL_STOCKS
from data_fetcher import (
    fetch_stock_data, fetch_intraday_data,
    format_number, format_price, format_percent
)
from rules import (
    check_rule1, RULE1_NAME,
    check_rule2, RULE2_NAME,
    check_rule3, RULE3_NAME,
    check_rule4, RULE4_NAME,
    check_rule5, RULE5_NAME,
    check_rule6, RULE6_NAME,
    check_rule7, RULE7_NAME
)
from telegram_alert import (
    send_screening_alert, send_combined_alert,
    send_start_notification, test_telegram_connection
)


def print_header():
    """Print header aplikasi"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}")
    print(r"   ____                      ____                                 ")
    print(r"  / ___| ___ _ __ ___   __ _/ ___|  ___ _ __ ___  ___ _ __   ___ _ __ ")
    print(r" | |  _ / _ \ '_ ` _ \ / _` \___ \ / __| '__/ _ \/ _ \ '_ \ / _ \ '__|")
    print(r" | |_| |  __/ | | | | | (_| |___) | (__| | |  __/  __/ | | |  __/ |   ")
    print(r"  \____|\___|_| |_| |_|\__,_|____/ \___|_|  \___|\___|_| |_|\___|_|   ")
    print(f"{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.YELLOW}  Stock Screening Tool untuk IHSG - By Gema{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}\n")


def print_rule_header(rule_num: int):
    """Print header untuk setiap rumus"""
    rule_name = RUMUS_NAMES.get(rule_num, f"Rule {rule_num}")
    emojis = {1: "🔥", 2: "🚀", 3: "🔄", 4: "📉", 5: "📈", 6: "📊", 7: "💥"}
    emoji = emojis.get(rule_num, "📌")

    print(f"\n{Colors.YELLOW}{'─'*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{emoji} RULE {rule_num}: {rule_name}{Colors.ENDC}")
    print(f"{Colors.YELLOW}{'─'*60}{Colors.ENDC}\n")


def run_screening(rules: List[int], use_telegram: bool = True,
                  show_progress: bool = True) -> Dict[int, List[Dict[str, Any]]]:
    """
    Jalankan screening untuk rumus yang dipilih

    Args:
        rules: List nomor rumus yang akan dijalankan [1, 2, 3]
        use_telegram: Kirim hasil ke Telegram
        show_progress: Tampilkan progress bar

    Returns:
        Dictionary {rule_num: [results]}
    """
    all_results = {}
    tickers = get_watchlist_with_suffix()
    total = len(tickers)

    print(f"{Colors.CYAN}📊 Total saham: {total}{Colors.ENDC}")
    print(f"{Colors.CYAN}📋 Rules: {rules}{Colors.ENDC}")
    print(f"{Colors.CYAN}📱 Telegram: {'Ya' if use_telegram else 'Tidak'}{Colors.ENDC}")
    print()

    # Fetch data untuk semua saham
    print(f"{Colors.YELLOW}Mengambil data dari Yahoo Finance...{Colors.ENDC}\n")

    stock_data = {}
    intraday_data = {}

    for i, ticker in enumerate(tickers, 1):
        progress = f"[{i}/{total}]"
        print(f"\r{progress} Fetching {ticker}...", end="", flush=True)

        # Fetch daily data
        df = fetch_stock_data(ticker, period="3mo")
        if df is not None and not df.empty:
            stock_data[ticker] = df

        # Fetch intraday jika rule 2 dipilih
        if 2 in rules:
            df_intraday = fetch_intraday_data(ticker, interval="5m")
            if df_intraday is not None and not df_intraday.empty:
                intraday_data[ticker] = df_intraday

        time.sleep(0.5)  # Rate limit

    print(f"\n\n{Colors.GREEN}✅ Data fetched: {len(stock_data)} saham{Colors.ENDC}\n")

    # Jalankan screening untuk setiap rule
    for rule_num in rules:
        print_rule_header(rule_num)

        results = []

        for ticker, df in stock_data.items():
            try:
                if rule_num == 1:
                    result = check_rule1(df, ticker)
                elif rule_num == 2:
                    df_intraday = intraday_data.get(ticker)
                    result = check_rule2(df, df_intraday, ticker)
                elif rule_num == 3:
                    result = check_rule3(df, ticker)
                elif rule_num == 4:
                    passed, details = check_rule4(df)
                    result = {'ticker': ticker, 'passed': passed, 'details': details, 'signals': [details.get('reason', '')]}
                elif rule_num == 5:
                    passed, details = check_rule5(df)
                    result = {'ticker': ticker, 'passed': passed, 'details': details, 'signals': [details.get('reason', '')]}
                elif rule_num == 6:
                    passed, details = check_rule6(df)
                    result = {'ticker': ticker, 'passed': passed, 'details': details, 'signals': [details.get('reason', '')]}
                elif rule_num == 7:
                    passed, details = check_rule7(df)
                    result = {'ticker': ticker, 'passed': passed, 'details': details, 'signals': [details.get('reason', '')]}
                else:
                    continue

                results.append(result)

            except Exception as e:
                print(f"{Colors.RED}Error processing {ticker}: {e}{Colors.ENDC}")

        # Filter passed results
        passed = [r for r in results if r.get('passed', False)]

        # Display results
        if passed:
            print(f"{Colors.GREEN}✅ Ditemukan {len(passed)} saham:{Colors.ENDC}\n")
            display_results_table(passed, rule_num)

            # Send to Telegram
            if use_telegram:
                if send_screening_alert(results, rule_num):
                    print(f"\n{Colors.GREEN}📱 Alert sent to Telegram{Colors.ENDC}")
        else:
            print(f"{Colors.YELLOW}❌ Tidak ada saham yang memenuhi kriteria{Colors.ENDC}")

        all_results[rule_num] = results

    return all_results


def display_results_table(results: List[Dict[str, Any]], rule_num: int):
    """Display hasil dalam format tabel"""
    table_data = []

    for r in results:
        ticker = r['ticker'].replace('.JK', '')
        details = r.get('details', {})

        close = details.get('close', 0)
        value = details.get('value', 0)
        rsi = details.get('rsi', 0)

        # Change percentage
        prev_close = details.get('prev_close', 0)
        if prev_close and close:
            change = ((close - prev_close) / prev_close) * 100
            change_str = f"{change:+.1f}%"
        else:
            change_str = "N/A"

        # Get top 2 signals
        signals = r.get('signals', [])[:2]
        signal_str = ", ".join(signals) if signals else "-"

        table_data.append([
            ticker,
            format_price(close),
            change_str,
            format_number(value),
            f"{rsi:.1f}" if rsi else "N/A",
            signal_str[:40] + "..." if len(signal_str) > 40 else signal_str
        ])

    headers = ["Saham", "Close", "Change", "Value", "RSI", "Signals"]
    print(tabulate(table_data, headers=headers, tablefmt="pretty"))


def run_auto_mode(rules: List[int], use_telegram: bool = True):
    """
    Jalankan screening dalam mode auto (scheduled)

    Args:
        rules: List nomor rumus
        use_telegram: Kirim ke Telegram
    """
    print(f"\n{Colors.BOLD}{Colors.GREEN}🔄 AUTO MODE ACTIVATED{Colors.ENDC}")
    print(f"{Colors.CYAN}Interval: {SCHEDULE_INTERVAL} detik ({SCHEDULE_INTERVAL//60} menit){Colors.ENDC}")
    print(f"{Colors.YELLOW}Tekan Ctrl+C untuk berhenti{Colors.ENDC}\n")

    if use_telegram:
        send_start_notification()

    iteration = 0

    try:
        while True:
            iteration += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
            print(f"{Colors.BOLD}📡 Iteration #{iteration} - {timestamp}{Colors.ENDC}")
            print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")

            # Run screening
            all_results = run_screening(rules, use_telegram)

            # Send combined alert if multiple rules
            if use_telegram and len(rules) > 1:
                send_combined_alert(all_results)

            # Wait for next iteration
            print(f"\n{Colors.YELLOW}⏳ Waiting {SCHEDULE_INTERVAL} seconds...{Colors.ENDC}")
            print(f"{Colors.YELLOW}   Next scan at: {datetime.now().strftime('%H:%M:%S')}{Colors.ENDC}")

            time.sleep(SCHEDULE_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n\n{Colors.RED}🛑 Auto mode stopped by user{Colors.ENDC}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="GemaScreener - Stock Screening Tool untuk IHSG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --all                  Jalankan semua rumus
  python main.py --rumus 1              Jalankan rumus 1 (9 Hari Konsisten)
  python main.py --rumus 2              Jalankan rumus 2 (Breakout Kuat)
  python main.py --rumus 3              Jalankan rumus 3 (Reversal/Hammer)
  python main.py --all --auto           Auto-schedule setiap 5 menit
  python main.py --all --no-telegram    Tanpa kirim ke Telegram
  python main.py --test                 Test koneksi Telegram
        """
    )

    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Jalankan semua rumus (4, 5, 6, 7)'
    )

    parser.add_argument(
        '--rumus', '-r',
        type=int,
        choices=[1, 2, 3, 4, 5, 6, 7],
        help='Jalankan rumus tertentu (1-7)'
    )

    parser.add_argument(
        '--rules',
        type=str,
        help='Jalankan beberapa rumus, pisahkan dengan koma (contoh: 4,5,6,7)'
    )

    parser.add_argument(
        '--auto',
        action='store_true',
        help='Mode auto-schedule (setiap 5 menit)'
    )

    parser.add_argument(
        '--no-telegram',
        action='store_true',
        help='Tidak kirim alert ke Telegram'
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='Test koneksi Telegram'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='Tampilkan daftar saham watchlist'
    )

    args = parser.parse_args()

    # Print header
    print_header()

    # Test mode
    if args.test:
        print(f"{Colors.YELLOW}Testing Telegram connection...{Colors.ENDC}")
        if test_telegram_connection():
            print(f"{Colors.GREEN}✅ Connection successful!{Colors.ENDC}")
        else:
            print(f"{Colors.RED}❌ Connection failed!{Colors.ENDC}")
        return

    # List watchlist
    if args.list:
        from watchlist import ALL_WATCHLIST, LQ45, LAYER2_AGRESIF
        print(f"Total saham: {TOTAL_STOCKS}")
        print(f"LQ45: {len(LQ45)}")
        print(f"Layer 2 Agresif: {len(LAYER2_AGRESIF)}")
        print(f"\nDaftar saham:")
        for i, stock in enumerate(ALL_WATCHLIST, 1):
            print(f"  {i:3}. {stock}")
        return

    # Determine rules to run
    if args.all:
        rules = [4, 5, 6, 7]  # Default ke rules yang sudah di-optimize
    elif args.rules:
        # Parse comma-separated rules
        rules = [int(r.strip()) for r in args.rules.split(',')]
    elif args.rumus:
        rules = [args.rumus]
    else:
        # Default: jalankan rules 4, 5, 6, 7
        rules = [4, 5, 6, 7]

    use_telegram = not args.no_telegram

    # Run screening
    if args.auto:
        run_auto_mode(rules, use_telegram)
    else:
        run_screening(rules, use_telegram)

    print(f"\n{Colors.GREEN}✅ Screening selesai!{Colors.ENDC}\n")


if __name__ == "__main__":
    main()
