"""
GemaScreener Report Generator
Generate Excel and Telegram reports for backtest results
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, RUMUS_NAMES

try:
    import requests
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False


def generate_report(results: Dict, output_dir: str = None, filename: str = None) -> str:
    """
    Generate Excel report from backtest results

    Args:
        results: Backtest results dictionary
        output_dir: Output directory (default: data/reports)
        filename: Output filename (default: backtest_YYYYMMDD_HHMMSS.xlsx)

    Returns:
        Path to generated file
    """
    if not EXCEL_AVAILABLE:
        print("openpyxl not installed. Run: pip install openpyxl")
        return None

    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data" / "reports"

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backtest_{timestamp}.xlsx"

    filepath = output_dir / filename

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # Sheet 1: Summary
        summary_data = []
        summary = results.get('summary', {})
        config = results.get('config', {})
        drawdown = results.get('max_drawdown', {})

        summary_data.append(['BACKTEST SUMMARY', ''])
        summary_data.append(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        summary_data.append(['', ''])
        summary_data.append(['CONFIGURATION', ''])
        summary_data.append(['Initial Capital', f"Rp {config.get('initial_capital', 0):,.0f}"])
        summary_data.append(['Position Size', f"{config.get('position_size_pct', 0)*100:.0f}%"])
        summary_data.append(['Take Profit', f"+{config.get('take_profit_pct', 0)*100:.0f}%"])
        summary_data.append(['Stop Loss', f"-{config.get('stop_loss_pct', 0)*100:.0f}%"])
        summary_data.append(['Max Hold Days', config.get('max_holding_days', 0)])
        summary_data.append(['Rules', str(config.get('rules', []))])
        summary_data.append(['', ''])
        summary_data.append(['PERFORMANCE', ''])
        summary_data.append(['Final Equity', f"Rp {summary.get('final_equity', 0):,.0f}"])
        summary_data.append(['Total P&L', f"Rp {summary.get('total_pnl', 0):+,.0f}"])
        summary_data.append(['Total Return', f"{summary.get('total_pnl_pct', 0):+.2f}%"])
        summary_data.append(['', ''])
        summary_data.append(['TRADE STATISTICS', ''])
        summary_data.append(['Total Trades', summary.get('total_trades', 0)])
        summary_data.append(['Winning Trades', summary.get('winning_trades', 0)])
        summary_data.append(['Losing Trades', summary.get('losing_trades', 0)])
        summary_data.append(['Win Rate', f"{summary.get('win_rate', 0):.2f}%"])
        summary_data.append(['Profit Factor', f"{summary.get('profit_factor', 0):.2f}"])
        summary_data.append(['', ''])
        summary_data.append(['RISK METRICS', ''])
        summary_data.append(['Max Drawdown', f"{drawdown.get('max_drawdown_pct', 0):.2f}%"])
        summary_data.append(['Max DD Value', f"Rp {drawdown.get('max_drawdown_value', 0):,.0f}"])
        summary_data.append(['Avg Win', f"Rp {summary.get('avg_win', 0):,.0f}"])
        summary_data.append(['Avg Loss', f"Rp {summary.get('avg_loss', 0):,.0f}"])
        summary_data.append(['Avg Holding Days', f"{summary.get('avg_holding_days', 0):.1f}"])

        summary_df = pd.DataFrame(summary_data, columns=['Metric', 'Value'])
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

        # Sheet 2: All Trades
        trades = results.get('trades', [])
        if trades:
            trades_df = pd.DataFrame(trades)
            trades_df.to_excel(writer, sheet_name='All Trades', index=False)

        # Sheet 3: Equity Curve
        equity_curve = results.get('equity_curve', [])
        if equity_curve:
            equity_df = pd.DataFrame(equity_curve)
            equity_df.to_excel(writer, sheet_name='Equity Curve', index=False)

        # Sheet 4: By Rule
        if trades:
            trades_df = pd.DataFrame(trades)
            by_rule = trades_df.groupby('rule').agg({
                'pnl': ['count', 'sum', 'mean'],
                'pnl_percent': 'mean'
            }).round(2)
            by_rule.columns = ['Trades', 'Total P&L', 'Avg P&L', 'Avg P&L %']
            by_rule.to_excel(writer, sheet_name='By Rule')

        # Sheet 5: By Exit Reason
        if trades:
            by_exit = trades_df.groupby('exit_reason').agg({
                'pnl': ['count', 'sum', 'mean'],
                'pnl_percent': 'mean'
            }).round(2)
            by_exit.columns = ['Trades', 'Total P&L', 'Avg P&L', 'Avg P&L %']
            by_exit.to_excel(writer, sheet_name='By Exit Reason')

    print(f"✅ Report saved: {filepath}")
    return str(filepath)


def generate_telegram_report(results: Dict) -> bool:
    """
    Send backtest report to Telegram

    Args:
        results: Backtest results dictionary

    Returns:
        True if sent successfully
    """
    if not TELEGRAM_AVAILABLE:
        print("requests not installed")
        return False

    summary = results.get('summary', {})
    config = results.get('config', {})
    drawdown = results.get('max_drawdown', {})

    # Format rules
    rules_str = ", ".join([RUMUS_NAMES.get(r, f"Rule {r}") for r in config.get('rules', [])])

    # Build message
    message = f"<b>📊 GEMA SCREENER BACKTEST REPORT</b>\n"
    message += f"<code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
    message += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    # Config
    message += f"<b>⚙️ Configuration</b>\n"
    message += f"   Modal: Rp {config.get('initial_capital', 0):,.0f}\n"
    message += f"   TP: +{config.get('take_profit_pct', 0)*100:.0f}% | SL: -{config.get('stop_loss_pct', 0)*100:.0f}%\n"
    message += f"   Rules: {rules_str}\n\n"

    # Performance
    total_pnl = summary.get('total_pnl', 0)
    pnl_emoji = "📈" if total_pnl > 0 else "📉"

    message += f"<b>💰 Performance</b>\n"
    message += f"   {pnl_emoji} P&L: Rp {total_pnl:+,.0f} ({summary.get('total_pnl_pct', 0):+.2f}%)\n"
    message += f"   Final: Rp {summary.get('final_equity', 0):,.0f}\n\n"

    # Trade stats
    message += f"<b>📋 Trade Statistics</b>\n"
    message += f"   Total: {summary.get('total_trades', 0)} trades\n"
    message += f"   Win Rate: {summary.get('win_rate', 0):.1f}%\n"
    message += f"   Profit Factor: {summary.get('profit_factor', 0):.2f}\n\n"

    # Risk
    message += f"<b>⚠️ Risk</b>\n"
    message += f"   Max Drawdown: {drawdown.get('max_drawdown_pct', 0):.2f}%\n"
    message += f"   Avg Hold: {summary.get('avg_holding_days', 0):.1f} days\n\n"

    # Top trades
    trades = results.get('trades', [])
    if trades:
        trades_df = pd.DataFrame(trades)
        top_wins = trades_df.nlargest(3, 'pnl')

        message += f"<b>🏆 Top 3 Trades</b>\n"
        for _, t in top_wins.iterrows():
            ticker = t['ticker'].replace('.JK', '')
            message += f"   {ticker}: Rp {t['pnl']:+,.0f} ({t['pnl_percent']:+.1f}%)\n"

    message += f"\n━━━━━━━━━━━━━━━━━━━━\n"
    message += f"<i>⚠️ Hasil backtest tidak menjamin hasil di masa depan</i>"

    # Send to Telegram
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        print("✅ Report sent to Telegram")
        return True
    except Exception as e:
        print(f"❌ Failed to send Telegram: {e}")
        return False


def print_console_report(results: Dict):
    """Print formatted report to console"""
    summary = results.get('summary', {})
    config = results.get('config', {})
    drawdown = results.get('max_drawdown', {})

    print("\n" + "="*70)
    print(" "*20 + "GEMA SCREENER BACKTEST REPORT")
    print("="*70)

    print("\n📌 CONFIGURATION")
    print("-"*50)
    print(f"   Initial Capital  : Rp {config.get('initial_capital', 0):>15,.0f}")
    print(f"   Position Size    : {config.get('position_size_pct', 0)*100:>15.0f}%")
    print(f"   Take Profit      : {'+' + str(config.get('take_profit_pct', 0)*100) + '%':>15}")
    print(f"   Stop Loss        : {'-' + str(config.get('stop_loss_pct', 0)*100) + '%':>15}")
    print(f"   Max Hold         : {config.get('max_holding_days', 0):>15} days")
    print(f"   Rules            : {str(config.get('rules', [])):>15}")

    print("\n💰 PERFORMANCE")
    print("-"*50)
    print(f"   Final Equity     : Rp {summary.get('final_equity', 0):>15,.0f}")
    print(f"   Total P&L        : Rp {summary.get('total_pnl', 0):>+15,.0f}")
    print(f"   Total Return     : {summary.get('total_pnl_pct', 0):>+15.2f}%")

    print("\n📊 TRADE STATISTICS")
    print("-"*50)
    print(f"   Total Trades     : {summary.get('total_trades', 0):>15}")
    print(f"   Winning Trades   : {summary.get('winning_trades', 0):>15} ({summary.get('win_rate', 0):.1f}%)")
    print(f"   Losing Trades    : {summary.get('losing_trades', 0):>15}")
    print(f"   Profit Factor    : {summary.get('profit_factor', 0):>15.2f}")

    print("\n💵 PROFIT/LOSS DETAILS")
    print("-"*50)
    print(f"   Gross Profit     : Rp {summary.get('gross_profit', 0):>15,.0f}")
    print(f"   Gross Loss       : Rp {summary.get('gross_loss', 0):>15,.0f}")
    print(f"   Avg Win          : Rp {summary.get('avg_win', 0):>+15,.0f} ({summary.get('avg_win_pct', 0):+.2f}%)")
    print(f"   Avg Loss         : Rp {summary.get('avg_loss', 0):>+15,.0f} ({summary.get('avg_loss_pct', 0):+.2f}%)")
    print(f"   Largest Win      : Rp {summary.get('largest_win', 0):>+15,.0f}")
    print(f"   Largest Loss     : Rp {summary.get('largest_loss', 0):>+15,.0f}")

    print("\n⚠️ RISK METRICS")
    print("-"*50)
    print(f"   Max Drawdown     : {drawdown.get('max_drawdown_pct', 0):>15.2f}%")
    print(f"   Max DD Value     : Rp {drawdown.get('max_drawdown_value', 0):>15,.0f}")
    print(f"   Avg Hold Days    : {summary.get('avg_holding_days', 0):>15.1f}")

    # By Exit Reason
    trades = results.get('trades', [])
    if trades:
        print("\n📋 BY EXIT REASON")
        print("-"*50)
        trades_df = pd.DataFrame(trades)
        by_exit = trades_df.groupby('exit_reason').agg({
            'pnl': ['count', 'sum']
        })
        for reason in by_exit.index:
            count = by_exit.loc[reason, ('pnl', 'count')]
            total = by_exit.loc[reason, ('pnl', 'sum')]
            print(f"   {reason:15} : {count:>5} trades, Rp {total:>+12,.0f}")

        # By Rule
        print("\n📋 BY RULE")
        print("-"*50)
        by_rule = trades_df.groupby('rule').agg({
            'pnl': ['count', 'sum']
        })
        for rule in by_rule.index:
            count = by_rule.loc[rule, ('pnl', 'count')]
            total = by_rule.loc[rule, ('pnl', 'sum')]
            rule_name = RUMUS_NAMES.get(rule, f"Rule {rule}")
            print(f"   Rule {rule} ({rule_name[:20]:20}) : {count:>5} trades, Rp {total:>+12,.0f}")

    print("\n" + "="*70)
    print(" "*15 + "⚠️ Hasil backtest tidak menjamin hasil di masa depan")
    print("="*70 + "\n")
