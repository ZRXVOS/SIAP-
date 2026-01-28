"""
ForexScreener Backtest Runner
Jalankan: python run_backtest.py --rules 4,5,6,7 --period 3y
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import RULE_NAMES, FOREX_PAIRS, DEFAULT_PAIRS
from data_manager import download_forex_data, get_forex_data, get_all_pairs, get_database_status, DB_PATH
from backtest.backtest_engine import ForexBacktestEngine, BacktestConfig


def print_banner():
    print(f"\033[96m{'='*60}\033[0m")
    print(f"\033[1m\033[92m")
    print(f"   ForexScreener Backtest")
    print(f"   Forex Backtesting Tool")
    print(f"\033[0m")
    print(f"\033[96m{'='*60}\033[0m")


def print_results(results):
    """Print backtest results"""
    if not results or results.get('total_trades', 0) == 0:
        print("\nNo trades executed.")
        if 'debug_signals' in results:
            signals = results.get('debug_signals', [])
            print(f"Signals found: {len(signals)}")
            for s in signals[:10]:
                print(f"  {s['date']} | {s['pair']} | Rule {s['rule']} | {s['price']:.4f} | {s['detail']}")
        return

    cfg = results['config']
    summary = results['summary']
    dd = results['max_drawdown']

    print(f"\n{'='*60}")
    print(f"CONFIGURATION")
    print(f"{'='*60}")
    print(f"Initial Capital : ${cfg['initial_capital']:,.2f}")
    print(f"Leverage        : 1:{cfg['leverage']}")
    print(f"Position Size   : {cfg['position_size_pct']*100:.0f}%")
    print(f"Take Profit     : +{cfg['take_profit_pct']*100:.1f}%")
    print(f"Stop Loss       : -{cfg['stop_loss_pct']*100:.1f}%")
    print(f"Max Hold        : {cfg['max_holding_days']} days")
    print(f"Rules           : {cfg['rules']}")

    print(f"\n{'='*60}")
    print(f"PERFORMANCE")
    print(f"{'='*60}")
    print(f"Final Equity  : ${summary['final_equity']:,.2f}")
    print(f"Total P&L     : ${summary['total_pnl']:,.2f}")
    print(f"Total Return  : {summary['total_pnl_pct']:+.2f}%")

    print(f"\n{'='*60}")
    print(f"TRADE STATISTICS")
    print(f"{'='*60}")
    print(f"Total Trades    : {summary['total_trades']}")
    print(f"Winning Trades  : {summary['winning_trades']}")
    print(f"Losing Trades   : {summary['losing_trades']}")
    print(f"Win Rate        : {summary['win_rate']:.1f}%")
    print(f"Profit Factor   : {summary['profit_factor']:.2f}")

    print(f"\n{'='*60}")
    print(f"PROFIT/LOSS DETAILS")
    print(f"{'='*60}")
    print(f"Gross Profit  : ${summary['gross_profit']:,.2f}")
    print(f"Gross Loss    : ${summary['gross_loss']:,.2f}")
    print(f"Avg Win       : ${summary['avg_win']:,.2f} ({summary['avg_win_pct']:+.2f}%)")
    print(f"Avg Loss      : ${summary['avg_loss']:,.2f} ({summary['avg_loss_pct']:+.2f}%)")
    print(f"Largest Win   : ${summary['largest_win']:,.2f}")
    print(f"Largest Loss  : ${summary['largest_loss']:,.2f}")

    print(f"\n{'='*60}")
    print(f"RISK METRICS")
    print(f"{'='*60}")
    print(f"Max Drawdown    : {dd['max_drawdown_pct']:.2f}%")
    print(f"Max DD Value    : ${dd['max_drawdown_value']:,.2f}")
    print(f"Avg Hold Days   : {summary['avg_holding_days']:.1f}")

    # Exit Reason Breakdown
    import pandas as pd
    trades_df = pd.DataFrame(results['trades'])

    print(f"\n{'='*60}")
    print(f"BY EXIT REASON")
    print(f"{'='*60}")

    exit_groups = trades_df.groupby('exit_reason')
    for reason, group in exit_groups:
        count = len(group)
        total_pnl = group['pnl'].sum()
        print(f"  {reason}: {count} trades, ${total_pnl:,.2f}")

    # By Rule
    print(f"\n{'='*60}")
    print(f"BY RULE")
    print(f"{'='*60}")

    rule_groups = trades_df.groupby('rule')
    for rule_num, group in rule_groups:
        count = len(group)
        total_pnl = group['pnl'].sum()
        win_count = len(group[group['pnl'] > 0])
        wr = win_count / count * 100 if count > 0 else 0
        rule_name = RULE_NAMES.get(rule_num, f"Rule {rule_num}")
        print(f"  Rule {rule_num} ({rule_name})")
        print(f"    Trades: {count}, WR: {wr:.1f}%, P&L: ${total_pnl:,.2f}")

    # By Pair
    print(f"\n{'='*60}")
    print(f"BY PAIR")
    print(f"{'='*60}")

    pair_groups = trades_df.groupby('pair')
    for pair_name, group in pair_groups:
        count = len(group)
        total_pnl = group['pnl'].sum()
        win_count = len(group[group['pnl'] > 0])
        wr = win_count / count * 100 if count > 0 else 0
        print(f"  {pair_name}: {count} trades, WR: {wr:.1f}%, P&L: ${total_pnl:,.2f}")


def main():
    parser = argparse.ArgumentParser(description="ForexScreener Backtest")
    parser.add_argument("--rules", type=str, default="4,5,6,7", help="Rules to test (e.g., 4,5,6,7)")
    parser.add_argument("--period", type=str, default="3y", help="Period: 1y, 2y, 3y, 5y")
    parser.add_argument("--pairs", type=str, default=None, help="Pairs (e.g., XAUUSD,EURUSD)")
    parser.add_argument("--capital", type=float, default=10_000, help="Initial capital in USD")
    parser.add_argument("--leverage", type=int, default=20, help="Leverage (e.g., 20 for 1:20)")
    parser.add_argument("--take-profit", type=float, default=0.10, help="Take profit %%")
    parser.add_argument("--stop-loss", type=float, default=0.05, help="Stop loss %%")
    parser.add_argument("--max-hold", type=int, default=5, help="Max holding days")
    parser.add_argument("--position-size", type=float, default=0.30, help="Position size %%")
    parser.add_argument("--mode", choices=['relaxed', 'strict'], default='relaxed')
    parser.add_argument("--download", action="store_true", help="Force re-download data")

    args = parser.parse_args()

    print_banner()

    # Parse rules
    rules = [int(r) for r in args.rules.split(",")]

    # Parse pairs
    if args.pairs:
        pairs = args.pairs.split(",")
    else:
        pairs = DEFAULT_PAIRS

    # Check database or download
    if args.download or not os.path.exists(DB_PATH):
        print(f"\nDownloading forex data...")
        if not download_forex_data(pairs, args.period):
            print("Failed to download data.")
            return
    else:
        status = get_database_status()
        if status:
            print(f"\nDatabase found: {DB_PATH}")
            for pair, info in status.items():
                print(f"  {pair}: {info['rows']} days ({info['start']} to {info['end']})")
        else:
            print(f"\nNo data found. Downloading...")
            if not download_forex_data(pairs, args.period):
                print("Failed to download data.")
                return

    # Load data
    print(f"\nLoading data for {len(pairs)} pairs...")
    pairs_data = {}
    for pair_name in pairs:
        df = get_forex_data(pair_name)
        if df is not None and len(df) > 50:
            pairs_data[pair_name] = df
            print(f"  {pair_name}: {len(df)} days")
        else:
            print(f"  {pair_name}: SKIP (no data)")

    if not pairs_data:
        print("\nNo data loaded. Try: python run_backtest.py --download")
        return

    # Setup config
    config = BacktestConfig(
        initial_capital=args.capital,
        position_size_pct=args.position_size,
        leverage=args.leverage,
        take_profit_pct=args.take_profit,
        stop_loss_pct=args.stop_loss,
        max_holding_days=args.max_hold,
        rules=rules,
        mode=args.mode
    )

    # Run backtest
    engine = ForexBacktestEngine(config)
    results = engine.run(pairs_data)

    # Print results
    print_results(results)


if __name__ == "__main__":
    main()
