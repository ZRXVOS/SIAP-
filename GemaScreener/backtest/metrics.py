"""
GemaScreener Backtest Metrics
Kalkulasi metrik performa trading
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any


def calculate_metrics(trades: List[Dict], initial_capital: float) -> Dict:
    """
    Calculate comprehensive trading metrics

    Args:
        trades: List of trade dictionaries
        initial_capital: Initial capital

    Returns:
        Dictionary with all metrics
    """
    if not trades:
        return {'error': 'No trades to analyze'}

    df = pd.DataFrame(trades)

    # Basic counts
    total_trades = len(df)
    winning_trades = len(df[df['pnl'] > 0])
    losing_trades = len(df[df['pnl'] <= 0])

    # P&L metrics
    total_pnl = df['pnl'].sum()
    gross_profit = df[df['pnl'] > 0]['pnl'].sum()
    gross_loss = abs(df[df['pnl'] <= 0]['pnl'].sum())

    # Ratios
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

    # Average metrics
    avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
    avg_loss = df[df['pnl'] <= 0]['pnl'].mean() if losing_trades > 0 else 0
    avg_trade = df['pnl'].mean()

    # Percentage metrics
    avg_win_pct = df[df['pnl'] > 0]['pnl_percent'].mean() if winning_trades > 0 else 0
    avg_loss_pct = df[df['pnl'] <= 0]['pnl_percent'].mean() if losing_trades > 0 else 0

    # Best/Worst
    largest_win = df['pnl'].max()
    largest_loss = df['pnl'].min()
    largest_win_pct = df['pnl_percent'].max()
    largest_loss_pct = df['pnl_percent'].min()

    # Holding period
    avg_holding = df['holding_days'].mean()
    max_holding = df['holding_days'].max()
    min_holding = df['holding_days'].min()

    # Consecutive wins/losses
    consecutive_wins = calculate_max_consecutive(df['pnl'] > 0)
    consecutive_losses = calculate_max_consecutive(df['pnl'] <= 0)

    # Risk metrics
    returns = df['pnl_percent'].values
    sharpe_ratio = calculate_sharpe_ratio(returns)
    sortino_ratio = calculate_sortino_ratio(returns)

    # Expectancy
    expectancy = (win_rate/100 * avg_win_pct) + ((1 - win_rate/100) * avg_loss_pct)

    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': round(win_rate, 2),

        'total_pnl': round(total_pnl, 0),
        'total_pnl_pct': round((total_pnl / initial_capital) * 100, 2),
        'gross_profit': round(gross_profit, 0),
        'gross_loss': round(gross_loss, 0),
        'profit_factor': round(profit_factor, 2),

        'avg_win': round(avg_win, 0),
        'avg_loss': round(avg_loss, 0),
        'avg_trade': round(avg_trade, 0),
        'avg_win_pct': round(avg_win_pct, 2),
        'avg_loss_pct': round(avg_loss_pct, 2),

        'largest_win': round(largest_win, 0),
        'largest_loss': round(largest_loss, 0),
        'largest_win_pct': round(largest_win_pct, 2),
        'largest_loss_pct': round(largest_loss_pct, 2),

        'avg_holding_days': round(avg_holding, 1),
        'max_holding_days': max_holding,
        'min_holding_days': min_holding,

        'max_consecutive_wins': consecutive_wins,
        'max_consecutive_losses': consecutive_losses,

        'sharpe_ratio': round(sharpe_ratio, 2),
        'sortino_ratio': round(sortino_ratio, 2),
        'expectancy': round(expectancy, 2)
    }


def calculate_drawdown(equity_curve: List[Dict]) -> Dict:
    """
    Calculate drawdown metrics

    Args:
        equity_curve: List of equity dictionaries with 'equity' key

    Returns:
        Dictionary with drawdown metrics
    """
    if not equity_curve:
        return {'error': 'No equity data'}

    equity = np.array([e['equity'] for e in equity_curve])

    # Calculate running maximum (peak)
    peak = np.maximum.accumulate(equity)

    # Calculate drawdown
    drawdown = (peak - equity)
    drawdown_pct = (peak - equity) / peak * 100

    # Max drawdown
    max_dd_idx = np.argmax(drawdown_pct)
    max_drawdown_pct = drawdown_pct[max_dd_idx]
    max_drawdown_value = drawdown[max_dd_idx]

    # Find drawdown periods
    in_drawdown = drawdown > 0
    drawdown_periods = []
    start_idx = None

    for i, is_dd in enumerate(in_drawdown):
        if is_dd and start_idx is None:
            start_idx = i
        elif not is_dd and start_idx is not None:
            drawdown_periods.append({
                'start': equity_curve[start_idx]['date'],
                'end': equity_curve[i]['date'],
                'duration': i - start_idx,
                'depth_pct': max(drawdown_pct[start_idx:i])
            })
            start_idx = None

    # Average drawdown
    avg_drawdown_pct = np.mean(drawdown_pct[drawdown_pct > 0]) if any(drawdown_pct > 0) else 0

    # Recovery factor
    total_return = (equity[-1] - equity[0]) / equity[0] * 100 if equity[0] > 0 else 0
    recovery_factor = total_return / max_drawdown_pct if max_drawdown_pct > 0 else float('inf')

    return {
        'max_drawdown_pct': round(max_drawdown_pct, 2),
        'max_drawdown_value': round(max_drawdown_value, 0),
        'avg_drawdown_pct': round(avg_drawdown_pct, 2),
        'recovery_factor': round(recovery_factor, 2),
        'num_drawdown_periods': len(drawdown_periods),
        'longest_drawdown_days': max([p['duration'] for p in drawdown_periods]) if drawdown_periods else 0,
        'drawdown_periods': drawdown_periods[:5]  # Top 5 drawdown periods
    }


def calculate_max_consecutive(series: pd.Series) -> int:
    """Calculate maximum consecutive True values"""
    if series.empty:
        return 0

    # Create groups of consecutive values
    groups = (series != series.shift()).cumsum()
    # Count consecutive True values
    consecutive = series.groupby(groups).cumsum()
    return int(consecutive.max())


def calculate_sharpe_ratio(returns: np.array, risk_free_rate: float = 0.05) -> float:
    """
    Calculate Sharpe Ratio

    Args:
        returns: Array of returns (in percentage)
        risk_free_rate: Annual risk-free rate (default 5%)

    Returns:
        Sharpe ratio
    """
    if len(returns) < 2:
        return 0

    # Convert to decimal
    returns_decimal = returns / 100

    # Annualize (assuming ~250 trading days)
    avg_return = np.mean(returns_decimal) * 250
    std_return = np.std(returns_decimal) * np.sqrt(250)

    if std_return == 0:
        return 0

    sharpe = (avg_return - risk_free_rate) / std_return
    return sharpe


def calculate_sortino_ratio(returns: np.array, risk_free_rate: float = 0.05) -> float:
    """
    Calculate Sortino Ratio (only considers downside volatility)

    Args:
        returns: Array of returns (in percentage)
        risk_free_rate: Annual risk-free rate (default 5%)

    Returns:
        Sortino ratio
    """
    if len(returns) < 2:
        return 0

    # Convert to decimal
    returns_decimal = returns / 100

    # Annualize
    avg_return = np.mean(returns_decimal) * 250

    # Downside deviation
    negative_returns = returns_decimal[returns_decimal < 0]
    if len(negative_returns) == 0:
        return float('inf')

    downside_std = np.std(negative_returns) * np.sqrt(250)

    if downside_std == 0:
        return 0

    sortino = (avg_return - risk_free_rate) / downside_std
    return sortino


def calculate_monthly_returns(equity_curve: List[Dict]) -> Dict:
    """
    Calculate monthly returns

    Args:
        equity_curve: List of equity dictionaries

    Returns:
        Dictionary with monthly returns
    """
    if not equity_curve:
        return {}

    df = pd.DataFrame(equity_curve)
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    # Resample to monthly
    monthly = df['equity'].resample('ME').last()

    # Calculate returns
    monthly_returns = monthly.pct_change() * 100

    return {
        'monthly_returns': monthly_returns.dropna().to_dict(),
        'best_month': round(monthly_returns.max(), 2),
        'worst_month': round(monthly_returns.min(), 2),
        'avg_month': round(monthly_returns.mean(), 2),
        'positive_months': int((monthly_returns > 0).sum()),
        'negative_months': int((monthly_returns < 0).sum())
    }


def generate_performance_summary(results: Dict) -> str:
    """
    Generate text summary of performance

    Args:
        results: Backtest results dictionary

    Returns:
        Formatted string summary
    """
    summary = results.get('summary', {})
    drawdown = results.get('max_drawdown', {})

    text = f"""
╔══════════════════════════════════════════════════════════╗
║           GEMA SCREENER BACKTEST REPORT                 ║
╠══════════════════════════════════════════════════════════╣
║  CAPITAL                                                 ║
╠══════════════════════════════════════════════════════════╣
║  Initial Capital    : Rp {summary.get('initial_capital', 0):>15,.0f}        ║
║  Final Equity       : Rp {summary.get('final_equity', 0):>15,.0f}        ║
║  Total P&L          : Rp {summary.get('total_pnl', 0):>+15,.0f}        ║
║  Total Return       :    {summary.get('total_pnl_pct', 0):>+14.2f}%        ║
╠══════════════════════════════════════════════════════════╣
║  TRADE STATISTICS                                        ║
╠══════════════════════════════════════════════════════════╣
║  Total Trades       : {summary.get('total_trades', 0):>10}                    ║
║  Winning Trades     : {summary.get('winning_trades', 0):>10} ({summary.get('win_rate', 0):.1f}%)            ║
║  Losing Trades      : {summary.get('losing_trades', 0):>10}                    ║
║  Avg Holding Days   : {summary.get('avg_holding_days', 0):>10.1f}                    ║
╠══════════════════════════════════════════════════════════╣
║  PROFIT/LOSS                                             ║
╠══════════════════════════════════════════════════════════╣
║  Gross Profit       : Rp {summary.get('gross_profit', 0):>15,.0f}        ║
║  Gross Loss         : Rp {summary.get('gross_loss', 0):>15,.0f}        ║
║  Profit Factor      : {summary.get('profit_factor', 0):>10.2f}                    ║
║  Avg Win            : Rp {summary.get('avg_win', 0):>+15,.0f}        ║
║  Avg Loss           : Rp {summary.get('avg_loss', 0):>+15,.0f}        ║
║  Largest Win        : Rp {summary.get('largest_win', 0):>+15,.0f}        ║
║  Largest Loss       : Rp {summary.get('largest_loss', 0):>+15,.0f}        ║
╠══════════════════════════════════════════════════════════╣
║  RISK METRICS                                            ║
╠══════════════════════════════════════════════════════════╣
║  Max Drawdown       :    {drawdown.get('max_drawdown_pct', 0):>14.2f}%        ║
║  Max DD Value       : Rp {drawdown.get('max_drawdown_value', 0):>15,.0f}        ║
╚══════════════════════════════════════════════════════════╝
"""
    return text
