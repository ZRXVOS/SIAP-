#!/usr/bin/env python3
"""
GemaScreener Backtest Runner
Main entry point untuk menjalankan backtest

Usage:
    python run_backtest.py --rule 1 --period 1y
    python run_backtest.py --all --period 3y
    python run_backtest.py --rule 1 --period 1y --export-excel
    python run_backtest.py --rule 1 --period 1y --telegram
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from config import Colors
from data_manager import get_database_status, DB_PATH
from backtest.backtest_engine import BacktestEngine, BacktestConfig
from backtest.report_generator import (
    generate_report,
    generate_telegram_report,
    print_console_report
)


def parse_period(period_str: str) -> tuple:
    """
    Parse period string to start and end date

    Args:
        period_str: Period string (3m, 6m, 1y, 2y, 3y)

    Returns:
        (start_date, end_date) as strings
    """
    end_date = datetime.now()

    period_map = {
        '3m': timedelta(days=90),
        '6m': timedelta(days=180),
        '1y': timedelta(days=365),
        '2y': timedelta(days=730),
        '3y': timedelta(days=1095),
        '5y': timedelta(days=1825)
    }

    if period_str in period_map:
        start_date = end_date - period_map[period_str]
    else:
        # Try to parse as date
        try:
            start_date = datetime.strptime(period_str, '%Y-%m-%d')
        except:
            start_date = end_date - timedelta(days=365)  # Default 1 year

    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')


def print_header():
    """Print header"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}")
    print(r"   ____                      ____             _    _            _   ")
    print(r"  / ___| ___ _ __ ___   __ _| __ )  __ _  ___| | _| |_ ___  ___| |_ ")
    print(r" | |  _ / _ \ '_ ` _ \ / _` |  _ \ / _` |/ __| |/ / __/ _ \/ __| __|")
    print(r" | |_| |  __/ | | | | | (_| | |_) | (_| | (__|   <| ||  __/\__ \ |_ ")
    print(r"  \____|\___|_| |_| |_|\__,_|____/ \__,_|\___|_|\_\\__\___||___/\__|")
    print(f"{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.YELLOW}  Stock Backtesting Tool untuk IHSG{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}\n")


def main():
    parser = argparse.ArgumentParser(
        description="GemaScreener Backtest Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_backtest.py --rule 1 --period 1y
    python run_backtest.py --all --period 3y
    python run_backtest.py --rule 2 --period 6m --export-excel
    python run_backtest.py --all --period 1y --telegram
    python run_backtest.py --rule 1 --start 2023-01-01 --end 2024-12-31
    python run_backtest.py --all --period 1y --mode strict

Trading Plan Default:
    - Take Profit: +10%
    - Stop Loss: -5%
    - Max Hold: 5 days
    - Position Size: 30%

Signal Detection Modes:
    - relaxed (default): Easier thresholds for more signals
        * Rule 1: 3 consecutive days instead of 9
        * Rule 2: 3%+ gain instead of 8%
        * Rule 3: 30% shadow ratio instead of 50%
    - strict: Original rules exactly as defined
        """
    )

    # Rule selection
    parser.add_argument('--rule', '-r', type=int, choices=[1, 2, 3],
                        help='Run backtest untuk rule tertentu (1, 2, atau 3)')
    parser.add_argument('--all', '-a', action='store_true',
                        help='Run backtest untuk semua rules')

    # Period
    parser.add_argument('--period', '-p', type=str, default='1y',
                        choices=['3m', '6m', '1y', '2y', '3y', '5y'],
                        help='Periode backtest (default: 1y)')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')

    # Trading parameters
    parser.add_argument('--capital', type=float, default=100_000_000,
                        help='Modal awal (default: 100000000)')
    parser.add_argument('--position-size', type=float, default=0.30,
                        help='Ukuran posisi sebagai fraction (default: 0.30 = 30%%)')
    parser.add_argument('--take-profit', type=float, default=0.10,
                        help='Take profit percentage (default: 0.10 = 10%%)')
    parser.add_argument('--stop-loss', type=float, default=0.05,
                        help='Stop loss percentage (default: 0.05 = 5%%)')
    parser.add_argument('--max-hold', type=int, default=5,
                        help='Max holding days (default: 5)')
    parser.add_argument('--mode', type=str, default='relaxed',
                        choices=['relaxed', 'strict'],
                        help='Signal detection mode (default: relaxed)')

    # Output options
    parser.add_argument('--export-excel', '-e', action='store_true',
                        help='Export hasil ke Excel')
    parser.add_argument('--telegram', '-t', action='store_true',
                        help='Kirim hasil ke Telegram')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Minimal output')

    args = parser.parse_args()

    # Print header
    if not args.quiet:
        print_header()

    # Check database
    if not DB_PATH.exists():
        print(f"{Colors.RED}❌ Database tidak ditemukan!{Colors.ENDC}")
        print(f"Jalankan terlebih dahulu: python data_manager.py --download-all --period 3y")
        return 1

    status = get_database_status()
    if status['stock_count'] == 0:
        print(f"{Colors.RED}❌ Database kosong!{Colors.ENDC}")
        print(f"Jalankan terlebih dahulu: python data_manager.py --download-all --period 3y")
        return 1

    # Determine rules
    if args.all:
        rules = [1, 2, 3]
    elif args.rule:
        rules = [args.rule]
    else:
        print("Pilih --rule atau --all")
        parser.print_help()
        return 1

    # Determine date range
    if args.start and args.end:
        start_date = args.start
        end_date = args.end
    else:
        start_date, end_date = parse_period(args.period)

    # Create config
    config = BacktestConfig(
        initial_capital=args.capital,
        position_size_pct=args.position_size,
        max_positions=1,
        take_profit_pct=args.take_profit,
        stop_loss_pct=args.stop_loss,
        max_holding_days=args.max_hold,
        rules=rules,
        mode=args.mode
    )

    # Print config
    if not args.quiet:
        print(f"{Colors.CYAN}📋 Backtest Configuration:{Colors.ENDC}")
        print(f"   Rules: {rules}")
        print(f"   Period: {start_date} to {end_date}")
        print(f"   Capital: Rp {config.initial_capital:,.0f}")
        print(f"   Position: {config.position_size_pct*100:.0f}%")
        print(f"   TP/SL: +{config.take_profit_pct*100:.0f}% / -{config.stop_loss_pct*100:.0f}%")
        print(f"   Max Hold: {config.max_holding_days} days")
        print(f"   Mode: {config.mode}")
        print()

    # Run backtest
    engine = BacktestEngine(config)
    results = engine.run(
        start_date=start_date,
        end_date=end_date,
        show_progress=not args.quiet
    )

    if not results or results.get('summary', {}).get('total_trades', 0) == 0:
        print(f"{Colors.YELLOW}⚠️ Tidak ada trade yang dieksekusi dalam periode ini.{Colors.ENDC}")
        print("Kemungkinan penyebab:")
        print("  - Tidak ada signal yang match dengan rules")
        print("  - Data tidak cukup untuk periode tersebut")
        print("  - Coba periode yang lebih panjang")
        return 0

    # Print results
    if not args.quiet:
        print_console_report(results)

    # Export to Excel
    if args.export_excel:
        filepath = generate_report(results)
        if filepath:
            print(f"{Colors.GREEN}📊 Excel report: {filepath}{Colors.ENDC}")

    # Send to Telegram
    if args.telegram:
        generate_telegram_report(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
