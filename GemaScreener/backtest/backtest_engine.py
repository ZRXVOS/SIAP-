"""
GemaScreener Backtest Engine
Core engine untuk simulasi trading
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_manager import get_stock_data, get_all_tickers
from indicators import calculate_all_indicators
from rules.rule1_konsisten import check_rule1
from rules.rule2_breakout import check_rule2
from rules.rule3_reversal import check_rule3


@dataclass
class Trade:
    """Represents a single trade"""
    ticker: str
    entry_date: str
    entry_price: float
    exit_date: str = None
    exit_price: float = None
    shares: int = 0
    position_value: float = 0
    exit_reason: str = None
    pnl: float = 0
    pnl_percent: float = 0
    holding_days: int = 0
    rule: int = 0


@dataclass
class BacktestConfig:
    """Backtest configuration"""
    initial_capital: float = 100_000_000  # Rp 100 juta
    position_size_pct: float = 0.30       # 30% per trade
    max_positions: int = 1                 # Max 1 posisi bersamaan
    take_profit_pct: float = 0.10         # TP +10%
    stop_loss_pct: float = 0.05           # SL -5%
    max_holding_days: int = 5             # Max hold 5 hari
    commission_pct: float = 0.0015        # 0.15% komisi (beli + jual)
    rules: List[int] = field(default_factory=lambda: [1, 2, 3])


class BacktestEngine:
    """Main backtest engine"""

    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
        self.signals: List[Dict] = []
        self.current_position: Optional[Trade] = None

    def _check_signal(self, df: pd.DataFrame, ticker: str, date_idx: int) -> Optional[int]:
        """
        Check if there's a signal on given date

        Args:
            df: DataFrame with indicators
            ticker: Stock ticker
            date_idx: Index of the date to check

        Returns:
            Rule number (1, 2, or 3) if signal, None otherwise
        """
        if date_idx < 15:  # Need enough history
            return None

        # Get data up to this date (simulate not having future data)
        df_subset = df.iloc[:date_idx + 1].copy()

        for rule_num in self.config.rules:
            try:
                if rule_num == 1:
                    result = check_rule1(df_subset, ticker)
                elif rule_num == 2:
                    result = check_rule2(df_subset, None, ticker)
                elif rule_num == 3:
                    result = check_rule3(df_subset, ticker)
                else:
                    continue

                if result.get('passed', False):
                    return rule_num
            except:
                pass

        return None

    def _calculate_shares(self, price: float, capital: float) -> int:
        """Calculate number of shares to buy (lot = 100)"""
        position_value = capital * self.config.position_size_pct
        shares = int(position_value / price / 100) * 100  # Round to lot
        return max(shares, 100)  # Minimum 1 lot

    def _check_exit_conditions(self, trade: Trade, current_high: float,
                                current_low: float, current_close: float,
                                days_held: int) -> Tuple[bool, str, float]:
        """
        Check if exit conditions are met

        Returns:
            (should_exit, reason, exit_price)
        """
        entry_price = trade.entry_price

        # Calculate TP and SL prices
        tp_price = entry_price * (1 + self.config.take_profit_pct)
        sl_price = entry_price * (1 - self.config.stop_loss_pct)

        # Check Take Profit (use high)
        if current_high >= tp_price:
            return True, "TAKE_PROFIT", tp_price

        # Check Stop Loss (use low)
        if current_low <= sl_price:
            return True, "STOP_LOSS", sl_price

        # Check Max Holding Days
        if days_held >= self.config.max_holding_days:
            return True, "TIME_EXIT", current_close

        return False, None, None

    def run(self, start_date: str = None, end_date: str = None,
            tickers: List[str] = None, show_progress: bool = True) -> Dict:
        """
        Run backtest

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            tickers: List of tickers to test (default: all in database)
            show_progress: Show progress bar

        Returns:
            Dictionary with backtest results
        """
        self.trades = []
        self.equity_curve = []
        self.signals = []
        self.current_position = None

        if tickers is None:
            tickers = get_all_tickers()

        if not tickers:
            print("No tickers found in database. Run data_manager.py --download-all first.")
            return {}

        # Initialize
        capital = self.config.initial_capital
        equity = capital

        print(f"\n{'='*60}")
        print(f"🔄 RUNNING BACKTEST")
        print(f"{'='*60}")
        print(f"Initial Capital: Rp {capital:,.0f}")
        print(f"Position Size: {self.config.position_size_pct*100:.0f}%")
        print(f"Take Profit: +{self.config.take_profit_pct*100:.0f}%")
        print(f"Stop Loss: -{self.config.stop_loss_pct*100:.0f}%")
        print(f"Max Hold: {self.config.max_holding_days} days")
        print(f"Rules: {self.config.rules}")
        print(f"Tickers: {len(tickers)}")
        print(f"{'='*60}\n")

        # Get all data and calculate indicators
        all_data = {}
        total_tickers = len(tickers)

        print("Loading data...")
        for i, ticker in enumerate(tickers):
            if show_progress:
                print(f"\r[{i+1}/{total_tickers}] Loading {ticker}...", end="", flush=True)

            df = get_stock_data(ticker, start_date, end_date)

            if df is not None and len(df) > 50:
                try:
                    # Rename columns for indicator calculation
                    df = df.rename(columns={
                        'open': 'Open', 'high': 'High', 'low': 'Low',
                        'close': 'Close', 'volume': 'Volume'
                    })
                    df = calculate_all_indicators(df)
                    all_data[ticker] = df
                except Exception as e:
                    pass

        print(f"\n\nLoaded {len(all_data)} stocks with sufficient data\n")

        if not all_data:
            print("No valid data found.")
            return {}

        # Get date range
        all_dates = set()
        for ticker, df in all_data.items():
            all_dates.update(df['date'].dt.strftime('%Y-%m-%d').tolist())

        all_dates = sorted(list(all_dates))

        if start_date:
            all_dates = [d for d in all_dates if d >= start_date]
        if end_date:
            all_dates = [d for d in all_dates if d <= end_date]

        print(f"Backtesting from {all_dates[0]} to {all_dates[-1]}")
        print(f"Total trading days: {len(all_dates)}\n")

        # Main backtest loop
        for day_idx, current_date in enumerate(all_dates):
            if show_progress and day_idx % 50 == 0:
                print(f"\r[{day_idx}/{len(all_dates)}] Processing {current_date}...", end="", flush=True)

            # Check if we have an open position
            if self.current_position:
                trade = self.current_position
                ticker = trade.ticker

                if ticker in all_data:
                    df = all_data[ticker]
                    date_mask = df['date'].dt.strftime('%Y-%m-%d') == current_date

                    if date_mask.any():
                        row = df[date_mask].iloc[0]
                        days_held = (datetime.strptime(current_date, '%Y-%m-%d') -
                                     datetime.strptime(trade.entry_date, '%Y-%m-%d')).days

                        should_exit, reason, exit_price = self._check_exit_conditions(
                            trade, row['High'], row['Low'], row['Close'], days_held
                        )

                        if should_exit:
                            # Close position
                            trade.exit_date = current_date
                            trade.exit_price = exit_price
                            trade.exit_reason = reason
                            trade.holding_days = days_held

                            # Calculate P&L
                            gross_pnl = (exit_price - trade.entry_price) * trade.shares
                            commission = (trade.entry_price + exit_price) * trade.shares * self.config.commission_pct
                            trade.pnl = gross_pnl - commission
                            trade.pnl_percent = ((exit_price / trade.entry_price) - 1) * 100

                            # Update capital
                            capital += trade.position_value + trade.pnl

                            self.trades.append(trade)
                            self.current_position = None

            # Look for new entry (only if no position)
            if self.current_position is None:
                for ticker, df in all_data.items():
                    date_mask = df['date'].dt.strftime('%Y-%m-%d') == current_date

                    if not date_mask.any():
                        continue

                    date_idx = df[date_mask].index[0]

                    # Check for signal on previous day's close
                    if date_idx > 0:
                        signal_rule = self._check_signal(df, ticker, date_idx - 1)

                        if signal_rule:
                            # Entry at today's open
                            row = df.iloc[date_idx]
                            entry_price = row['Open']

                            if entry_price > 0:
                                shares = self._calculate_shares(entry_price, capital)
                                position_value = shares * entry_price

                                if position_value <= capital:
                                    # Open position
                                    trade = Trade(
                                        ticker=ticker,
                                        entry_date=current_date,
                                        entry_price=entry_price,
                                        shares=shares,
                                        position_value=position_value,
                                        rule=signal_rule
                                    )

                                    capital -= position_value
                                    self.current_position = trade

                                    self.signals.append({
                                        'date': current_date,
                                        'ticker': ticker,
                                        'rule': signal_rule,
                                        'price': entry_price
                                    })

                                    break  # Only one position at a time

            # Record equity
            current_equity = capital
            if self.current_position:
                # Add unrealized P&L
                ticker = self.current_position.ticker
                if ticker in all_data:
                    df = all_data[ticker]
                    date_mask = df['date'].dt.strftime('%Y-%m-%d') == current_date
                    if date_mask.any():
                        current_price = df[date_mask].iloc[0]['Close']
                        unrealized_pnl = (current_price - self.current_position.entry_price) * self.current_position.shares
                        current_equity = capital + self.current_position.position_value + unrealized_pnl

            self.equity_curve.append({
                'date': current_date,
                'equity': current_equity,
                'capital': capital,
                'in_position': self.current_position is not None
            })

        print(f"\n\n{'='*60}")
        print(f"✅ BACKTEST COMPLETE")
        print(f"{'='*60}\n")

        # Close any remaining position at last price
        if self.current_position:
            trade = self.current_position
            ticker = trade.ticker

            if ticker in all_data:
                df = all_data[ticker]
                last_row = df.iloc[-1]
                trade.exit_date = all_dates[-1]
                trade.exit_price = last_row['Close']
                trade.exit_reason = "END_OF_BACKTEST"

                gross_pnl = (trade.exit_price - trade.entry_price) * trade.shares
                commission = (trade.entry_price + trade.exit_price) * trade.shares * self.config.commission_pct
                trade.pnl = gross_pnl - commission
                trade.pnl_percent = ((trade.exit_price / trade.entry_price) - 1) * 100

                self.trades.append(trade)

        return self._compile_results()

    def _compile_results(self) -> Dict:
        """Compile backtest results"""
        if not self.trades:
            return {
                'total_trades': 0,
                'message': 'No trades executed'
            }

        # Convert to DataFrame for analysis
        trades_df = pd.DataFrame([{
            'ticker': t.ticker,
            'entry_date': t.entry_date,
            'entry_price': t.entry_price,
            'exit_date': t.exit_date,
            'exit_price': t.exit_price,
            'shares': t.shares,
            'position_value': t.position_value,
            'pnl': t.pnl,
            'pnl_percent': t.pnl_percent,
            'exit_reason': t.exit_reason,
            'holding_days': t.holding_days,
            'rule': t.rule
        } for t in self.trades])

        equity_df = pd.DataFrame(self.equity_curve)

        # Calculate metrics
        total_pnl = trades_df['pnl'].sum()
        win_trades = trades_df[trades_df['pnl'] > 0]
        loss_trades = trades_df[trades_df['pnl'] <= 0]

        gross_profit = win_trades['pnl'].sum() if len(win_trades) > 0 else 0
        gross_loss = abs(loss_trades['pnl'].sum()) if len(loss_trades) > 0 else 0

        results = {
            'config': {
                'initial_capital': self.config.initial_capital,
                'position_size_pct': self.config.position_size_pct,
                'take_profit_pct': self.config.take_profit_pct,
                'stop_loss_pct': self.config.stop_loss_pct,
                'max_holding_days': self.config.max_holding_days,
                'rules': self.config.rules
            },
            'summary': {
                'initial_capital': self.config.initial_capital,
                'final_equity': equity_df['equity'].iloc[-1] if len(equity_df) > 0 else self.config.initial_capital,
                'total_pnl': total_pnl,
                'total_pnl_pct': (total_pnl / self.config.initial_capital) * 100,
                'total_trades': len(self.trades),
                'winning_trades': len(win_trades),
                'losing_trades': len(loss_trades),
                'win_rate': (len(win_trades) / len(self.trades)) * 100 if self.trades else 0,
                'gross_profit': gross_profit,
                'gross_loss': gross_loss,
                'profit_factor': gross_profit / gross_loss if gross_loss > 0 else float('inf'),
                'avg_win': win_trades['pnl'].mean() if len(win_trades) > 0 else 0,
                'avg_loss': loss_trades['pnl'].mean() if len(loss_trades) > 0 else 0,
                'avg_win_pct': win_trades['pnl_percent'].mean() if len(win_trades) > 0 else 0,
                'avg_loss_pct': loss_trades['pnl_percent'].mean() if len(loss_trades) > 0 else 0,
                'largest_win': trades_df['pnl'].max(),
                'largest_loss': trades_df['pnl'].min(),
                'avg_holding_days': trades_df['holding_days'].mean()
            },
            'by_exit_reason': trades_df.groupby('exit_reason').agg({
                'pnl': ['count', 'sum', 'mean']
            }).to_dict(),
            'by_rule': trades_df.groupby('rule').agg({
                'pnl': ['count', 'sum', 'mean']
            }).to_dict(),
            'trades': trades_df.to_dict('records'),
            'equity_curve': equity_df.to_dict('records'),
            'max_drawdown': self._calculate_max_drawdown(equity_df)
        }

        return results

    def _calculate_max_drawdown(self, equity_df: pd.DataFrame) -> Dict:
        """Calculate maximum drawdown"""
        if equity_df.empty:
            return {'max_drawdown_pct': 0, 'max_drawdown_value': 0}

        equity = equity_df['equity'].values
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak * 100

        max_dd_idx = np.argmax(drawdown)
        max_dd_pct = drawdown[max_dd_idx]
        max_dd_value = peak[max_dd_idx] - equity[max_dd_idx]

        return {
            'max_drawdown_pct': max_dd_pct,
            'max_drawdown_value': max_dd_value
        }
