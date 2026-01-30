"""
ForexScreener Backtest Engine
Rules 4, 5, 6, 7 adapted for Forex (menggunakan RULE LAMA yang terbukti terbaik)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Trade:
    """Single trade record"""
    pair: str
    entry_date: str
    entry_price: float
    exit_date: str = None
    exit_price: float = None
    units: float = 0
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
    initial_capital: float = 10_000      # USD $10,000
    position_size_pct: float = 0.30      # 30% per trade
    leverage: int = 20                    # 1:20 leverage
    take_profit_pct: float = 0.10        # TP +10%
    stop_loss_pct: float = 0.05          # SL -5%
    max_holding_days: int = 5            # Max hold 5 days
    spread_cost_pct: float = 0.0003      # 0.03% spread (buy + sell)
    rules: List[int] = field(default_factory=lambda: [4, 5, 6, 7])
    mode: str = 'relaxed'


class ForexBacktestEngine:
    """Forex Backtest Engine"""

    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
        self.current_position: Optional[Trade] = None
        self.debug_signals = []

    # ============================================================
    # ENTRY SIGNALS (RULE LAMA - terbukti terbaik)
    # ============================================================

    def _check_rule4_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        Rule 4: RSI-2 Mean Reversion (Larry Connors)
        Entry: Close > SMA(200) AND RSI(2) < threshold
        """
        if idx < 200:
            return False, ""

        close = df['close']
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=2, min_periods=2).mean()
        avg_loss = loss.rolling(window=2, min_periods=2).mean()

        rs = avg_gain / avg_loss
        rsi_2 = 100 - (100 / (1 + rs))

        sma_200 = close.rolling(window=200, min_periods=200).mean()

        curr_close = close.iloc[idx]
        curr_sma_200 = sma_200.iloc[idx]
        curr_rsi_2 = rsi_2.iloc[idx]

        if pd.isna(curr_rsi_2) or pd.isna(curr_sma_200):
            return False, ""

        rsi_threshold = 10 if self.config.mode == 'relaxed' else 5

        if curr_close > curr_sma_200 and curr_rsi_2 < rsi_threshold:
            return True, f"RSI2={curr_rsi_2:.1f}, >SMA200"

        return False, ""

    def _check_rule5_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        Rule 5: Dual MA Crossover (Golden Cross)
        Entry: SMA(20) crosses above SMA(50) + Volume spike + RSI > 50
        """
        if idx < 52:
            return False, ""

        close = df['close']
        volume = df['volume']

        sma_20 = close.rolling(window=20, min_periods=20).mean()
        sma_50 = close.rolling(window=50, min_periods=50).mean()
        sma_20_vol = volume.rolling(window=20, min_periods=20).mean()

        # RSI(14)
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()
        rs = avg_gain / avg_loss
        rsi_14 = 100 - (100 / (1 + rs))

        curr_sma_20 = sma_20.iloc[idx]
        curr_sma_50 = sma_50.iloc[idx]
        prev_sma_20 = sma_20.iloc[idx - 1]
        prev_sma_50 = sma_50.iloc[idx - 1]
        curr_close = close.iloc[idx]
        curr_volume = volume.iloc[idx]
        curr_sma_20_vol = sma_20_vol.iloc[idx]
        curr_rsi = rsi_14.iloc[idx] if idx >= 14 else 50

        if pd.isna(curr_sma_50) or pd.isna(prev_sma_50):
            return False, ""

        # Golden Cross
        golden_cross = (prev_sma_20 <= prev_sma_50) and (curr_sma_20 > curr_sma_50)

        # Recent cross within 3 days
        recent_cross = False
        if curr_sma_20 > curr_sma_50:
            for i in range(1, min(4, idx)):
                if sma_20.iloc[idx - i] <= sma_50.iloc[idx - i]:
                    recent_cross = True
                    break

        vol_ratio = curr_volume / curr_sma_20_vol if curr_sma_20_vol > 0 else 0

        min_vol_ratio = 1.2 if self.config.mode == 'relaxed' else 1.5
        min_rsi = 45 if self.config.mode == 'relaxed' else 50

        if (golden_cross or recent_cross) and curr_close > curr_sma_20 and vol_ratio >= min_vol_ratio:
            if pd.isna(curr_rsi) or curr_rsi < min_rsi:
                return False, ""

            cross_type = "GoldenX" if golden_cross else "RecentX"
            return True, f"{cross_type}, Vol {vol_ratio:.1f}x, RSI {curr_rsi:.0f}"

        return False, ""

    def _check_rule6_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        Rule 6: Bollinger Band Mean Reversion
        Entry: Close < BB_Lower AND RSI(14) < 30 AND Close > SMA(200)
        """
        if idx < 200:
            return False, ""

        close = df['close']

        sma_20 = close.rolling(window=20, min_periods=20).mean()
        std_20 = close.rolling(window=20, min_periods=20).std()
        bb_lower = sma_20 - (2 * std_20)
        bb_middle = sma_20

        sma_200 = close.rolling(window=200, min_periods=200).mean()

        # RSI(14)
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()
        rs = avg_gain / avg_loss
        rsi_14 = 100 - (100 / (1 + rs))

        curr_close = close.iloc[idx]
        curr_bb_lower = bb_lower.iloc[idx]
        curr_sma_200 = sma_200.iloc[idx]
        curr_rsi_14 = rsi_14.iloc[idx]

        if pd.isna(curr_bb_lower) or pd.isna(curr_sma_200) or pd.isna(curr_rsi_14):
            return False, ""

        rsi_threshold = 35 if self.config.mode == 'relaxed' else 30

        if curr_close < curr_bb_lower and curr_close > curr_sma_200 and curr_rsi_14 < rsi_threshold:
            percent_b = (curr_close - curr_bb_lower) / (bb_middle.iloc[idx] - curr_bb_lower) if bb_middle.iloc[idx] != curr_bb_lower else 0
            return True, f"BB %B={percent_b:.2f}, RSI={curr_rsi_14:.0f}"

        return False, ""

    def _check_rule7_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        Rule 7: Breakout with Volume
        Entry: Close > High(20) AND Volume > 1.5x AND Bullish candle
        """
        if idx < 25:
            return False, ""

        close = df['close']
        high = df['high']
        volume = df['volume']
        open_price = df['open']

        high_20 = high.shift(1).rolling(window=20, min_periods=20).max()
        sma_20_vol = volume.rolling(window=20, min_periods=20).mean()

        curr_close = close.iloc[idx]
        curr_open = open_price.iloc[idx]
        curr_high_20 = high_20.iloc[idx]
        curr_volume = volume.iloc[idx]
        curr_sma_20_vol = sma_20_vol.iloc[idx]

        if pd.isna(curr_high_20) or pd.isna(curr_sma_20_vol):
            return False, ""

        vol_ratio = curr_volume / curr_sma_20_vol if curr_sma_20_vol > 0 else 0
        breakout_pct = ((curr_close - curr_high_20) / curr_high_20 * 100) if curr_high_20 > 0 else 0
        is_bullish = curr_close > curr_open

        min_vol_ratio = 1.5 if self.config.mode == 'relaxed' else 2.0
        min_breakout_pct = 0.5 if self.config.mode == 'relaxed' else 1.0

        if curr_close > curr_high_20 and vol_ratio >= min_vol_ratio and is_bullish and breakout_pct >= min_breakout_pct:
            return True, f"Breakout +{breakout_pct:.1f}%, Vol {vol_ratio:.1f}x"

        return False, ""

    # ============================================================
    # EXIT CONDITIONS (Default TP/SL - RULE LAMA)
    # ============================================================

    def _check_exit(self, df: pd.DataFrame, idx: int, trade: Trade,
                    days_held: int) -> Tuple[bool, str, float]:
        """Check exit conditions - menggunakan default TP/SL seperti RULE LAMA"""
        entry_price = trade.entry_price
        curr_close = df['close'].iloc[idx]
        curr_high = df['high'].iloc[idx]
        curr_low = df['low'].iloc[idx]

        tp_price = entry_price * (1 + self.config.take_profit_pct)
        sl_price = entry_price * (1 - self.config.stop_loss_pct)

        # Take Profit
        if curr_high >= tp_price:
            return True, "TAKE_PROFIT", tp_price

        # Stop Loss
        if curr_low <= sl_price:
            return True, "STOP_LOSS", sl_price

        # Time Exit
        if days_held >= self.config.max_holding_days:
            return True, "TIME_EXIT", curr_close

        return False, None, None

    # ============================================================
    # SIGNAL ROUTER
    # ============================================================

    def _check_signal(self, df: pd.DataFrame, pair: str, idx: int) -> Tuple[Optional[int], str]:
        """Check all rules for signal"""
        for rule_num in self.config.rules:
            try:
                if rule_num == 4:
                    passed, detail = self._check_rule4_signal(df, idx)
                elif rule_num == 5:
                    passed, detail = self._check_rule5_signal(df, idx)
                elif rule_num == 6:
                    passed, detail = self._check_rule6_signal(df, idx)
                elif rule_num == 7:
                    passed, detail = self._check_rule7_signal(df, idx)
                else:
                    continue

                if passed:
                    return rule_num, detail
            except Exception:
                pass

        return None, ""

    # ============================================================
    # POSITION SIZING
    # ============================================================

    def _calculate_units(self, price: float, capital: float) -> float:
        """Calculate units to buy with leverage"""
        position_value = capital * self.config.position_size_pct
        leveraged_value = position_value * self.config.leverage
        units = leveraged_value / price
        return units

    # ============================================================
    # MAIN BACKTEST
    # ============================================================

    def run(self, pairs_data: Dict[str, pd.DataFrame], show_progress: bool = True) -> Dict:
        """Run backtest across all forex pairs"""
        self.trades = []
        self.equity_curve = []
        self.debug_signals = []
        self.current_position = None

        if not pairs_data:
            print("No data to backtest.")
            return {}

        capital = self.config.initial_capital
        equity = capital

        print(f"\n{'='*60}")
        print(f"FOREX BACKTEST ENGINE")
        print(f"{'='*60}")
        print(f"Initial Capital: ${capital:,.2f}")
        print(f"Position Size: {self.config.position_size_pct*100:.0f}%")
        print(f"Leverage: 1:{self.config.leverage}")
        print(f"Take Profit: +{self.config.take_profit_pct*100:.0f}%")
        print(f"Stop Loss: -{self.config.stop_loss_pct*100:.0f}%")
        print(f"Max Hold: {self.config.max_holding_days} days")
        print(f"Rules: {self.config.rules}")
        print(f"Mode: {self.config.mode}")
        print(f"Pairs: {list(pairs_data.keys())}")
        print(f"{'='*60}\n")

        # Rename columns for consistency
        processed_data = {}
        for pair_name, df in pairs_data.items():
            df = df.copy()
            if 'Date' in df.columns:
                df = df.rename(columns={'Date': 'date', 'Open': 'open', 'High': 'high',
                                         'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
            df['date'] = pd.to_datetime(df['date'])
            processed_data[pair_name] = df

        # Get unified date range
        all_dates = set()
        for pair_name, df in processed_data.items():
            dates = df['date'].dt.strftime('%Y-%m-%d').tolist()
            all_dates.update(dates)
        all_dates = sorted(list(all_dates))

        print(f"Period: {all_dates[0]} to {all_dates[-1]}")
        print(f"Trading days: {len(all_dates)}\n")
        print("Scanning for signals...")

        signals_found = 0

        # Main loop
        for day_num, current_date in enumerate(all_dates):
            if show_progress and day_num % 100 == 0:
                print(f"\r  [{day_num}/{len(all_dates)}] {current_date} | Signals: {signals_found} | Trades: {len(self.trades)}", end="", flush=True)

            # Check exit for open position
            if self.current_position:
                trade = self.current_position
                pair_name = trade.pair

                if pair_name in processed_data:
                    df = processed_data[pair_name]
                    mask = df['date'].dt.strftime('%Y-%m-%d') == current_date

                    if mask.any():
                        idx = df.index[mask][0]
                        df_idx = df.index.get_loc(idx)
                        days_held = (datetime.strptime(current_date, '%Y-%m-%d') -
                                    datetime.strptime(trade.entry_date, '%Y-%m-%d')).days

                        should_exit, reason, exit_price = self._check_exit(
                            df, df_idx, trade, days_held
                        )

                        if should_exit:
                            trade.exit_date = current_date
                            trade.exit_price = exit_price
                            trade.exit_reason = reason
                            trade.holding_days = days_held

                            # PnL calculation with leverage
                            price_change_pct = (exit_price - trade.entry_price) / trade.entry_price
                            gross_pnl = trade.position_value * self.config.leverage * price_change_pct
                            spread_cost = trade.position_value * self.config.leverage * self.config.spread_cost_pct * 2
                            trade.pnl = gross_pnl - spread_cost
                            trade.pnl_percent = price_change_pct * 100

                            capital += trade.position_value + trade.pnl
                            self.trades.append(trade)
                            self.current_position = None

            # Look for entry (if no position)
            if self.current_position is None:
                for pair_name, df in processed_data.items():
                    mask = df['date'].dt.strftime('%Y-%m-%d') == current_date

                    if not mask.any():
                        continue

                    idx = df.index[mask][0]
                    df_idx = df.index.get_loc(idx)

                    rule_num, detail = self._check_signal(df, pair_name, df_idx)

                    if rule_num:
                        signals_found += 1
                        row = df.iloc[df_idx]
                        entry_price = row['close']

                        if entry_price > 0:
                            position_value = capital * self.config.position_size_pct

                            if position_value <= capital * 0.95:
                                trade = Trade(
                                    pair=pair_name,
                                    entry_date=current_date,
                                    entry_price=entry_price,
                                    units=self._calculate_units(entry_price, capital),
                                    position_value=position_value,
                                    rule=rule_num,
                                    signal_details=detail
                                )

                                capital -= position_value
                                self.current_position = trade

                                self.debug_signals.append({
                                    'date': current_date,
                                    'pair': pair_name,
                                    'rule': rule_num,
                                    'price': entry_price,
                                    'detail': detail
                                })
                                break

            # Record equity
            current_equity = capital
            if self.current_position:
                pair_name = self.current_position.pair
                if pair_name in processed_data:
                    df = processed_data[pair_name]
                    mask = df['date'].dt.strftime('%Y-%m-%d') == current_date
                    if mask.any():
                        current_price = df[mask].iloc[0]['close']
                        price_change_pct = (current_price - self.current_position.entry_price) / self.current_position.entry_price
                        unrealized = self.current_position.position_value * self.config.leverage * price_change_pct
                        current_equity = capital + self.current_position.position_value + unrealized

            self.equity_curve.append({
                'date': current_date,
                'equity': current_equity,
                'capital': capital
            })

        # Close remaining position
        if self.current_position:
            trade = self.current_position
            pair_name = trade.pair
            if pair_name in processed_data:
                df = processed_data[pair_name]
                last_row = df.iloc[-1]
                trade.exit_date = all_dates[-1]
                trade.exit_price = last_row['close']
                trade.exit_reason = "END_OF_BACKTEST"

                price_change_pct = (trade.exit_price - trade.entry_price) / trade.entry_price
                gross_pnl = trade.position_value * self.config.leverage * price_change_pct
                spread_cost = trade.position_value * self.config.leverage * self.config.spread_cost_pct * 2
                trade.pnl = gross_pnl - spread_cost
                trade.pnl_percent = price_change_pct * 100

                self.trades.append(trade)

        print(f"\n\n{'='*60}")
        print(f"BACKTEST COMPLETE")
        print(f"{'='*60}")
        print(f"Signals found: {signals_found}")
        print(f"Trades executed: {len(self.trades)}")

        return self._compile_results()

    def _compile_results(self) -> Dict:
        """Compile all results"""
        if not self.trades:
            return {
                'total_trades': 0,
                'signals_found': len(self.debug_signals),
                'debug_signals': self.debug_signals[:20],
                'message': 'No trades executed'
            }

        trades_df = pd.DataFrame([{
            'pair': t.pair,
            'entry_date': t.entry_date,
            'entry_price': t.entry_price,
            'exit_date': t.exit_date,
            'exit_price': t.exit_price,
            'units': t.units,
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
                'leverage': self.config.leverage,
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
