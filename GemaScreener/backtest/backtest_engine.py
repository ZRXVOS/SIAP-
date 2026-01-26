"""
GemaScreener Backtest Engine
Core engine untuk simulasi trading - FIXED VERSION
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
from indicators import calculate_all_indicators, sma, rsi, stochastic, atr, cmf


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
    signal_details: str = ""


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
    # Mode: 'strict' = original rules, 'relaxed' = easier to match
    mode: str = 'relaxed'


class BacktestEngine:
    """Main backtest engine"""

    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
        self.signals: List[Dict] = []
        self.current_position: Optional[Trade] = None
        self.debug_signals = []

    def _check_rule1_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        Rule 1: Konsisten Naik
        Relaxed: 3+ hari HIGH > 2% dari prev CLOSE
        Strict: 9 hari
        """
        min_days = 3 if self.config.mode == 'relaxed' else 9
        threshold = 1.02

        if idx < min_days + 1:
            return False, ""

        consecutive = 0
        for i in range(min_days):
            curr_idx = idx - i
            prev_idx = idx - i - 1

            if prev_idx < 0:
                break

            high = df.iloc[curr_idx]['High']
            prev_close = df.iloc[prev_idx]['Close']

            if prev_close > 0 and high / prev_close > threshold:
                consecutive += 1
            else:
                break

        # Additional filters
        if consecutive >= min_days:
            row = df.iloc[idx]
            volume = row.get('Volume', 0)
            close = row.get('Close', 0)
            value = close * volume if close and volume else 0

            # Volume dan Value filter (relaxed)
            min_value = 500_000_000 if self.config.mode == 'relaxed' else 1_000_000_000

            if value > min_value and 50 < close < 5000:
                return True, f"{consecutive}d konsisten naik"

        return False, ""

    def _check_rule2_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        Rule 2: Breakout Kuat
        Relaxed: Close naik >= 3% + volume spike
        Strict: Close naik >= 8% + banyak kondisi
        """
        if idx < 20:
            return False, ""

        row = df.iloc[idx]
        prev = df.iloc[idx - 1]

        close = row.get('Close', 0)
        prev_close = prev.get('Close', 0)
        volume = row.get('Volume', 0)
        prev_volume = prev.get('Volume', 0)

        if not (close and prev_close and volume and prev_volume):
            return False, ""

        # Price change
        change_pct = (close - prev_close) / prev_close * 100

        # Volume change
        vol_change = volume / prev_volume if prev_volume > 0 else 0

        # Thresholds based on mode
        min_change = 3.0 if self.config.mode == 'relaxed' else 8.0
        min_vol_spike = 1.5 if self.config.mode == 'relaxed' else 2.0

        if change_pct >= min_change and vol_change >= min_vol_spike:
            value = close * volume
            min_value = 1_000_000_000 if self.config.mode == 'relaxed' else 5_000_000_000

            if value > min_value and 50 < close < 5000:
                return True, f"+{change_pct:.1f}% vol {vol_change:.1f}x"

        return False, ""

    def _check_rule3_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        Rule 3: Reversal / Hammer
        Relaxed: Shadow bawah > 3% + bullish close
        Strict: Shadow bawah > 5% + engulfing pattern
        """
        if idx < 10:
            return False, ""

        row = df.iloc[idx]
        prev = df.iloc[idx - 1]

        open_price = row.get('Open', 0)
        high = row.get('High', 0)
        low = row.get('Low', 0)
        close = row.get('Close', 0)
        volume = row.get('Volume', 0)
        prev_close = prev.get('Close', 0)

        if not (open_price and high and low and close and prev_close):
            return False, ""

        # Calculate shadow
        body_bottom = min(open_price, close)
        lower_shadow = body_bottom - low
        total_range = high - low if high > low else 1
        shadow_ratio = lower_shadow / total_range

        # Shadow threshold
        min_shadow_ratio = 0.3 if self.config.mode == 'relaxed' else 0.5

        # Bullish (close > open)
        is_bullish = close > open_price

        # Lower shadow dip below prev close
        dip_pct = (low / prev_close) if prev_close > 0 else 1
        min_dip = 0.97 if self.config.mode == 'relaxed' else 0.95

        if shadow_ratio >= min_shadow_ratio and is_bullish and dip_pct < min_dip:
            value = close * volume
            min_value = 500_000_000 if self.config.mode == 'relaxed' else 2_000_000_000

            if value > min_value and 50 < close < 5000:
                return True, f"Hammer {shadow_ratio:.0%} shadow"

        return False, ""

    def _check_signal(self, df: pd.DataFrame, ticker: str, idx: int) -> Tuple[Optional[int], str]:
        """Check all rules for signal"""
        for rule_num in self.config.rules:
            try:
                if rule_num == 1:
                    passed, detail = self._check_rule1_signal(df, idx)
                elif rule_num == 2:
                    passed, detail = self._check_rule2_signal(df, idx)
                elif rule_num == 3:
                    passed, detail = self._check_rule3_signal(df, idx)
                else:
                    continue

                if passed:
                    return rule_num, detail
            except Exception as e:
                pass

        return None, ""

    def _calculate_shares(self, price: float, capital: float) -> int:
        """Calculate number of shares to buy (lot = 100)"""
        position_value = capital * self.config.position_size_pct
        shares = int(position_value / price / 100) * 100
        return max(shares, 100)

    def _check_exit_conditions(self, trade: Trade, current_high: float,
                                current_low: float, current_close: float,
                                days_held: int) -> Tuple[bool, str, float]:
        """Check if exit conditions are met"""
        entry_price = trade.entry_price

        tp_price = entry_price * (1 + self.config.take_profit_pct)
        sl_price = entry_price * (1 - self.config.stop_loss_pct)

        if current_high >= tp_price:
            return True, "TAKE_PROFIT", tp_price

        if current_low <= sl_price:
            return True, "STOP_LOSS", sl_price

        if days_held >= self.config.max_holding_days:
            return True, "TIME_EXIT", current_close

        return False, None, None

    def run(self, start_date: str = None, end_date: str = None,
            tickers: List[str] = None, show_progress: bool = True) -> Dict:
        """Run backtest"""
        self.trades = []
        self.equity_curve = []
        self.signals = []
        self.debug_signals = []
        self.current_position = None

        if tickers is None:
            tickers = get_all_tickers()

        if not tickers:
            print("No tickers found in database.")
            return {}

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
        print(f"Mode: {self.config.mode}")
        print(f"Tickers: {len(tickers)}")
        print(f"{'='*60}\n")

        # Load and process all data
        all_data = {}
        print("Loading and processing data...")

        for i, ticker in enumerate(tickers):
            if show_progress and i % 20 == 0:
                print(f"\r[{i+1}/{len(tickers)}] Loading {ticker}...", end="", flush=True)

            df = get_stock_data(ticker, start_date, end_date)

            if df is not None and len(df) > 50:
                try:
                    # Rename columns for consistency
                    df = df.rename(columns={
                        'open': 'Open', 'high': 'High', 'low': 'Low',
                        'close': 'Close', 'volume': 'Volume'
                    })

                    # Ensure date column
                    if 'date' in df.columns:
                        df['Date'] = pd.to_datetime(df['date'])

                    all_data[ticker] = df
                except:
                    pass

        print(f"\n\nLoaded {len(all_data)} stocks\n")

        if not all_data:
            return {}

        # Get unified date range
        all_dates = set()
        for ticker, df in all_data.items():
            dates = df['Date'].dt.strftime('%Y-%m-%d').tolist()
            all_dates.update(dates)

        all_dates = sorted(list(all_dates))

        if start_date:
            all_dates = [d for d in all_dates if d >= start_date]
        if end_date:
            all_dates = [d for d in all_dates if d <= end_date]

        print(f"Period: {all_dates[0]} to {all_dates[-1]}")
        print(f"Trading days: {len(all_dates)}\n")
        print("Scanning for signals...")

        signals_found = 0

        # Main loop
        for day_num, current_date in enumerate(all_dates):
            if show_progress and day_num % 100 == 0:
                print(f"\r[{day_num}/{len(all_dates)}] {current_date} | Signals: {signals_found} | Trades: {len(self.trades)}", end="", flush=True)

            # Check exit for open position
            if self.current_position:
                trade = self.current_position
                ticker = trade.ticker

                if ticker in all_data:
                    df = all_data[ticker]
                    mask = df['Date'].dt.strftime('%Y-%m-%d') == current_date

                    if mask.any():
                        row = df[mask].iloc[0]
                        days_held = (datetime.strptime(current_date, '%Y-%m-%d') -
                                    datetime.strptime(trade.entry_date, '%Y-%m-%d')).days

                        should_exit, reason, exit_price = self._check_exit_conditions(
                            trade, row['High'], row['Low'], row['Close'], days_held
                        )

                        if should_exit:
                            trade.exit_date = current_date
                            trade.exit_price = exit_price
                            trade.exit_reason = reason
                            trade.holding_days = days_held

                            gross_pnl = (exit_price - trade.entry_price) * trade.shares
                            commission = (trade.entry_price + exit_price) * trade.shares * self.config.commission_pct
                            trade.pnl = gross_pnl - commission
                            trade.pnl_percent = ((exit_price / trade.entry_price) - 1) * 100

                            capital += trade.position_value + trade.pnl
                            self.trades.append(trade)
                            self.current_position = None

            # Look for entry (if no position)
            if self.current_position is None:
                for ticker, df in all_data.items():
                    mask = df['Date'].dt.strftime('%Y-%m-%d') == current_date

                    if not mask.any():
                        continue

                    idx = df.index[mask][0]
                    df_idx = df.index.get_loc(idx)

                    # Check for signal on THIS day (not previous)
                    rule_num, detail = self._check_signal(df, ticker, df_idx)

                    if rule_num:
                        signals_found += 1
                        row = df.iloc[df_idx]
                        entry_price = row['Close']  # Enter at close

                        if entry_price > 0:
                            shares = self._calculate_shares(entry_price, capital)
                            position_value = shares * entry_price

                            if position_value <= capital * 0.95:  # Keep 5% buffer
                                trade = Trade(
                                    ticker=ticker,
                                    entry_date=current_date,
                                    entry_price=entry_price,
                                    shares=shares,
                                    position_value=position_value,
                                    rule=rule_num,
                                    signal_details=detail
                                )

                                capital -= position_value
                                self.current_position = trade

                                self.debug_signals.append({
                                    'date': current_date,
                                    'ticker': ticker,
                                    'rule': rule_num,
                                    'price': entry_price,
                                    'detail': detail
                                })

                                break

            # Record equity
            current_equity = capital
            if self.current_position:
                ticker = self.current_position.ticker
                if ticker in all_data:
                    df = all_data[ticker]
                    mask = df['Date'].dt.strftime('%Y-%m-%d') == current_date
                    if mask.any():
                        current_price = df[mask].iloc[0]['Close']
                        unrealized = (current_price - self.current_position.entry_price) * self.current_position.shares
                        current_equity = capital + self.current_position.position_value + unrealized

            self.equity_curve.append({
                'date': current_date,
                'equity': current_equity,
                'capital': capital
            })

        print(f"\n\n{'='*60}")
        print(f"✅ BACKTEST COMPLETE")
        print(f"{'='*60}")
        print(f"Signals found: {signals_found}")
        print(f"Trades executed: {len(self.trades)}")

        # Close remaining position
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
        """Compile results"""
        if not self.trades:
            return {
                'total_trades': 0,
                'signals_found': len(self.debug_signals),
                'debug_signals': self.debug_signals[:20],
                'message': 'No trades executed'
            }

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
            'rule': t.rule,
            'signal_details': t.signal_details
        } for t in self.trades])

        equity_df = pd.DataFrame(self.equity_curve)

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
                'rules': self.config.rules,
                'mode': self.config.mode
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
            'trades': trades_df.to_dict('records'),
            'equity_curve': equity_df.to_dict('records'),
            'max_drawdown': self._calculate_max_drawdown(equity_df),
            'debug_signals': self.debug_signals[:20]
        }

        return results

    def _calculate_max_drawdown(self, equity_df: pd.DataFrame) -> Dict:
        """Calculate max drawdown"""
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
