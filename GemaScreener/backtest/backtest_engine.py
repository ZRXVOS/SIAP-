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

    def _check_rule4_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        Rule 4: RSI-2 Mean Reversion (Larry Connors) - OPTIMIZED
        Entry: Close > SMA(200) AND RSI(2) < 5 (strict threshold)
        Exit: Close > SMA(5) AND RSI(2) > 60, Disaster Stop -20%, Time 20 days
        """
        if idx < 200:
            return False, ""

        # Calculate RSI(2)
        close = df['Close']
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=2, min_periods=2).mean()
        avg_loss = loss.rolling(window=2, min_periods=2).mean()

        rs = avg_gain / avg_loss
        rsi_2 = 100 - (100 / (1 + rs))

        # Calculate SMA(200)
        sma_200 = close.rolling(window=200, min_periods=200).mean()

        # Get current values
        curr_close = close.iloc[idx]
        curr_sma_200 = sma_200.iloc[idx]
        curr_rsi_2 = rsi_2.iloc[idx]

        if pd.isna(curr_rsi_2) or pd.isna(curr_sma_200):
            return False, ""

        # RSI threshold - STRICT: < 5 for higher win rate
        rsi_threshold = 5

        # Entry conditions: Close > SMA(200) AND RSI(2) < 5
        if curr_close > curr_sma_200 and curr_rsi_2 < rsi_threshold:
            row = df.iloc[idx]
            volume = row.get('Volume', 0)
            value = curr_close * volume if volume else 0
            min_value = 500_000_000 if self.config.mode == 'relaxed' else 1_000_000_000

            if value > min_value:
                return True, f"RSI2={curr_rsi_2:.1f}, >SMA200"

        return False, ""

    def _check_rule5_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        Rule 5: Dual MA Crossover - OPTIMIZED
        Entry: Golden Cross + Volume 1.5x + RSI > 50 + ADX > 20
        Exit: TP +15%, SL -8%, Breakdown < SMA50, Time 20 days
        NO Trailing Stop, NO Momentum Loss
        """
        if idx < 52:
            return False, ""

        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']

        sma_20 = close.rolling(window=20, min_periods=20).mean()
        sma_50 = close.rolling(window=50, min_periods=50).mean()
        sma_20_vol = volume.rolling(window=20, min_periods=20).mean()

        # Calculate RSI(14) for momentum filter
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()
        rs = avg_gain / avg_loss
        rsi_14 = 100 - (100 / (1 + rs))

        # Calculate ADX(14) for trend strength
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr_14 = tr.rolling(window=14, min_periods=14).mean()
        plus_di = 100 * (plus_dm.rolling(window=14).mean() / atr_14)
        minus_di = 100 * (minus_dm.rolling(window=14).mean() / atr_14)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=14, min_periods=14).mean()

        # Current and previous values
        curr_sma_20 = sma_20.iloc[idx]
        curr_sma_50 = sma_50.iloc[idx]
        prev_sma_20 = sma_20.iloc[idx - 1]
        prev_sma_50 = sma_50.iloc[idx - 1]
        curr_close = close.iloc[idx]
        curr_volume = volume.iloc[idx]
        curr_sma_20_vol = sma_20_vol.iloc[idx]
        curr_rsi = rsi_14.iloc[idx] if idx >= 14 else 50
        curr_adx = adx.iloc[idx] if idx >= 28 else 25  # Default to 25 if not enough data

        if pd.isna(curr_sma_50) or pd.isna(prev_sma_50):
            return False, ""

        # Check Golden Cross (today or within last 3 days)
        golden_cross = (prev_sma_20 <= prev_sma_50) and (curr_sma_20 > curr_sma_50)

        # Alternative: Recent cross within 3 days
        recent_cross = False
        if curr_sma_20 > curr_sma_50:  # Currently bullish
            for i in range(1, min(4, idx)):
                if sma_20.iloc[idx - i] <= sma_50.iloc[idx - i]:
                    recent_cross = True
                    break

        # Volume ratio
        vol_ratio = curr_volume / curr_sma_20_vol if curr_sma_20_vol > 0 else 0

        # Thresholds - OPTIMIZED
        min_vol_ratio = 1.5  # Volume 1.5x average
        min_rsi = 50         # RSI > 50 for momentum
        min_adx = 20         # ADX > 20 for trend strength

        # Entry: Golden Cross + Volume + RSI > 50 + ADX > 20
        if (golden_cross or recent_cross) and curr_close > curr_sma_20 and vol_ratio >= min_vol_ratio:
            # RSI filter - momentum positive
            if pd.isna(curr_rsi) or curr_rsi < min_rsi:
                return False, ""

            # ADX filter - trend strength
            if pd.isna(curr_adx) or curr_adx < min_adx:
                return False, ""

            row = df.iloc[idx]
            value = curr_close * curr_volume
            min_value = 500_000_000 if self.config.mode == 'relaxed' else 1_000_000_000

            if value > min_value:
                cross_type = "GoldenX" if golden_cross else "RecentX"
                return True, f"{cross_type}, Vol {vol_ratio:.1f}x, RSI {curr_rsi:.0f}, ADX {curr_adx:.0f}"

        return False, ""

    def _check_rule6_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        Rule 6: Bollinger Band Mean Reversion - OPTIMIZED
        Entry: Close < BB_Lower AND %B < 0 AND RSI(14) < 30 AND Close > SMA(200)
        Exit: TP +10% or BB_Middle, Disaster Stop -8%, Time 20 days
        """
        if idx < 200:
            return False, ""

        close = df['Close']

        # Bollinger Bands
        sma_20 = close.rolling(window=20, min_periods=20).mean()
        std_20 = close.rolling(window=20, min_periods=20).std()
        bb_lower = sma_20 - (2 * std_20)
        bb_upper = sma_20 + (2 * std_20)
        bb_middle = sma_20

        # Calculate %B (Bollinger Band position indicator)
        # %B = (Close - BB_Lower) / (BB_Upper - BB_Lower)
        # %B < 0 means price is BELOW lower band
        percent_b = (close - bb_lower) / (bb_upper - bb_lower)

        # SMA 200
        sma_200 = close.rolling(window=200, min_periods=200).mean()

        # RSI(14)
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()
        rs = avg_gain / avg_loss
        rsi_14 = 100 - (100 / (1 + rs))

        # Current values
        curr_close = close.iloc[idx]
        curr_bb_lower = bb_lower.iloc[idx]
        curr_sma_200 = sma_200.iloc[idx]
        curr_rsi_14 = rsi_14.iloc[idx]
        curr_percent_b = percent_b.iloc[idx]

        if pd.isna(curr_bb_lower) or pd.isna(curr_sma_200) or pd.isna(curr_rsi_14):
            return False, ""

        # Thresholds - STRICT
        rsi_threshold = 30  # RSI < 30 for confirmed oversold

        # Entry conditions: Close < BB_Lower AND %B < 0 AND RSI < 30 AND Close > SMA(200)
        if curr_close < curr_bb_lower and curr_percent_b < 0 and curr_close > curr_sma_200 and curr_rsi_14 < rsi_threshold:
            row = df.iloc[idx]
            volume = row.get('Volume', 0)
            value = curr_close * volume if volume else 0
            min_value = 500_000_000 if self.config.mode == 'relaxed' else 1_000_000_000

            if value > min_value:
                return True, f"BB %B={curr_percent_b:.2f}, RSI={curr_rsi_14:.0f}"

        return False, ""

    def _check_rule7_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        Rule 7: Breakout with Volume - OPTIMIZED
        Entry: Close > High(20) AND Volume > 2x AND Breakout >= 2% AND Base Pattern 5 days
        Exit: TP +20%, Support-based Stop Loss, Time 15 days
        """
        if idx < 30:
            return False, ""

        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']
        open_price = df['Open']

        # 20-day high (excluding today)
        high_20 = high.shift(1).rolling(window=20, min_periods=20).max()
        low_20 = low.shift(1).rolling(window=20, min_periods=20).min()
        sma_20_vol = volume.rolling(window=20, min_periods=20).mean()

        # Current values
        curr_close = close.iloc[idx]
        curr_open = open_price.iloc[idx]
        curr_high_20 = high_20.iloc[idx]
        curr_low_20 = low_20.iloc[idx]
        curr_volume = volume.iloc[idx]
        curr_sma_20_vol = sma_20_vol.iloc[idx]

        if pd.isna(curr_high_20) or pd.isna(curr_sma_20_vol):
            return False, ""

        # Volume ratio - STRICT: Volume > 2x average
        vol_ratio = curr_volume / curr_sma_20_vol if curr_sma_20_vol > 0 else 0

        # Breakout percentage - STRICT: >= 2%
        breakout_pct = ((curr_close - curr_high_20) / curr_high_20 * 100) if curr_high_20 > 0 else 0

        # Is bullish candle
        is_bullish = curr_close > curr_open

        # Check Base Pattern: Price range in last 5 days < 10% (consolidation)
        if idx >= 5:
            last_5_high = high.iloc[idx-5:idx].max()
            last_5_low = low.iloc[idx-5:idx].min()
            consolidation_range = ((last_5_high - last_5_low) / last_5_low * 100) if last_5_low > 0 else 100
            has_base = consolidation_range < 10  # Range < 10% = consolidation
        else:
            has_base = False

        # Thresholds - STRICT
        min_vol_ratio = 2.0    # Volume > 2x average
        min_breakout_pct = 2.0  # Breakout >= 2%

        # Entry: Breakout + Volume 2x + Bullish + Breakout 2% + Base Pattern
        if curr_close > curr_high_20 and vol_ratio >= min_vol_ratio and is_bullish and breakout_pct >= min_breakout_pct and has_base:
            value = curr_close * curr_volume
            min_value = 500_000_000 if self.config.mode == 'relaxed' else 1_000_000_000

            if value > min_value:
                return True, f"Breakout +{breakout_pct:.1f}%, Vol {vol_ratio:.1f}x, Base OK"

        return False, ""

    def _check_rule8_signal(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """
        Rule 8: Three MA System (SWING TRADING OPTIMIZED)
        Entry: SMA(10) > SMA(20) > SMA(50) + Pullback to SMA(20) + Bullish + Volume
        Optimized for 3-10 day swing trades
        """
        if idx < 55:
            return False, ""

        close = df['Close']
        low = df['Low']
        open_price = df['Open']
        volume = df['Volume']

        # Calculate MAs
        sma_10 = close.rolling(window=10, min_periods=10).mean()
        sma_20 = close.rolling(window=20, min_periods=20).mean()
        sma_50 = close.rolling(window=50, min_periods=50).mean()
        sma_20_vol = volume.rolling(window=20, min_periods=20).mean()

        # Current values
        curr_close = close.iloc[idx]
        curr_low = low.iloc[idx]
        curr_open = open_price.iloc[idx]
        curr_sma_10 = sma_10.iloc[idx]
        curr_sma_20 = sma_20.iloc[idx]
        curr_sma_50 = sma_50.iloc[idx]
        curr_volume = volume.iloc[idx]
        curr_sma_20_vol = sma_20_vol.iloc[idx]

        if pd.isna(curr_sma_50):
            return False, ""

        # Check bullish alignment
        is_aligned = (curr_sma_10 > curr_sma_20) and (curr_sma_20 > curr_sma_50)

        if not is_aligned:
            return False, ""

        # Check pullback to SMA20 (within 2-3% in last 3 days)
        is_pullback = False
        pullback_tolerance = 0.03 if self.config.mode == 'relaxed' else 0.02

        for i in range(3):
            if idx - i < 0:
                break
            day_low = low.iloc[idx - i]
            day_sma_20 = sma_20.iloc[idx - i]
            if day_low <= day_sma_20 * (1 + pullback_tolerance):
                is_pullback = True
                break

        if not is_pullback:
            return False, ""

        # Close above SMA10 (recovery) and bullish candle
        is_bullish = curr_close > curr_open
        above_sma10 = curr_close > curr_sma_10

        # SWING TRADING: Add volume confirmation on pullback recovery
        vol_ratio = curr_volume / curr_sma_20_vol if curr_sma_20_vol > 0 else 0
        min_vol_ratio = 1.0 if self.config.mode == 'relaxed' else 1.2  # Volume at least average

        if is_bullish and above_sma10 and vol_ratio >= min_vol_ratio:
            row = df.iloc[idx]
            value = curr_close * curr_volume if curr_volume else 0
            min_value = 500_000_000 if self.config.mode == 'relaxed' else 1_000_000_000

            if value > min_value:
                pullback_pct = ((curr_sma_10 - curr_low) / curr_sma_10 * 100) if curr_sma_10 > 0 else 0
                return True, f"3MA Aligned, PB {pullback_pct:.1f}%, Vol {vol_ratio:.1f}x"

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
                elif rule_num == 4:
                    passed, detail = self._check_rule4_signal(df, idx)
                elif rule_num == 5:
                    passed, detail = self._check_rule5_signal(df, idx)
                elif rule_num == 6:
                    passed, detail = self._check_rule6_signal(df, idx)
                elif rule_num == 7:
                    passed, detail = self._check_rule7_signal(df, idx)
                elif rule_num == 8:
                    passed, detail = self._check_rule8_signal(df, idx)
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

    def _check_exit_for_rule(self, df: pd.DataFrame, idx: int, trade: Trade,
                              days_held: int) -> Tuple[bool, str, float]:
        """
        Check exit conditions based on specific rule from journal
        Each rule has its own exit logic as per original research
        """
        rule = trade.rule
        entry_price = trade.entry_price

        close = df['Close']
        high = df['High']
        low = df['Low']

        curr_close = close.iloc[idx]
        curr_high = high.iloc[idx]
        curr_low = low.iloc[idx]

        # ============================================================
        # RULE 1-3: Original rules (use default TP/SL)
        # ============================================================
        if rule in [1, 2, 3]:
            tp_price = entry_price * (1 + self.config.take_profit_pct)
            sl_price = entry_price * (1 - self.config.stop_loss_pct)

            if curr_high >= tp_price:
                return True, "TAKE_PROFIT", tp_price
            if curr_low <= sl_price:
                return True, "STOP_LOSS", sl_price
            if days_held >= self.config.max_holding_days:
                return True, "TIME_EXIT", curr_close

        # ============================================================
        # RULE 4: RSI-2 Mean Reversion (Larry Connors) - OPTIMIZED
        # EXIT: Close > SMA(5) AND RSI(2) > 60 (stronger confirmation)
        # Disaster Stop: -20%, Time: 20 days
        # ============================================================
        elif rule == 4:
            # Calculate SMA(5)
            sma_5 = close.rolling(window=5, min_periods=5).mean()
            curr_sma_5 = sma_5.iloc[idx] if idx >= 5 else None

            # Calculate RSI(2) for exit confirmation
            delta = close.diff()
            gain = delta.where(delta > 0, 0.0)
            loss_series = -delta.where(delta < 0, 0.0)
            avg_gain = gain.rolling(window=2, min_periods=2).mean()
            avg_loss = loss_series.rolling(window=2, min_periods=2).mean()
            rs = avg_gain / avg_loss
            rsi_2 = 100 - (100 / (1 + rs))
            curr_rsi_2 = rsi_2.iloc[idx] if idx >= 2 else 50

            # EXIT 1: Mean Reversion Complete - Close > SMA(5) AND RSI(2) > 60
            if curr_sma_5 is not None and not pd.isna(curr_rsi_2):
                if curr_close > curr_sma_5 and curr_rsi_2 > 60:
                    return True, "MEAN_REVERSION", curr_close

            # EXIT 2: Disaster Stop -20% (black swan protection)
            if curr_close <= entry_price * 0.80:
                return True, "DISASTER_STOP", curr_close

            # EXIT 3: Time exit 20 days (extended from 5)
            if days_held >= 20:
                return True, "TIME_EXIT", curr_close

        # ============================================================
        # RULE 5: Dual MA Crossover - OPTIMIZED
        # EXIT: TP +15%, SL -8%, Breakdown < SMA50, Time 20 days
        # NO Trailing Stop, NO Momentum Loss (removed)
        # ============================================================
        elif rule == 5:
            sma_50 = close.rolling(window=50, min_periods=50).mean()
            curr_sma_50 = sma_50.iloc[idx] if idx >= 50 else None

            # EXIT 1: Take Profit +15%
            if curr_close >= entry_price * 1.15:
                return True, "TAKE_PROFIT", curr_close

            # EXIT 2: Stop Loss -8%
            if curr_close <= entry_price * 0.92:
                return True, "STOP_LOSS", curr_close

            # EXIT 3: Breakdown - Close below SMA50 (major trend break)
            if curr_sma_50 is not None and curr_close < curr_sma_50:
                return True, "BREAKDOWN", curr_close

            # EXIT 4: Time exit 20 days
            if days_held >= 20:
                return True, "TIME_EXIT", curr_close

            # REMOVED: Trailing Stop (was causing -177M loss)
            # REMOVED: Momentum Loss Close < SMA20 (too sensitive)

        # ============================================================
        # RULE 6: Bollinger Band Mean Reversion - OPTIMIZED
        # EXIT: TP +10% OR BB_Middle, Disaster Stop -8%, Time 20 days
        # ============================================================
        elif rule == 6:
            # Calculate Bollinger Bands
            sma_20 = close.rolling(window=20, min_periods=20).mean()
            curr_bb_middle = sma_20.iloc[idx] if idx >= 20 else None

            # EXIT 1: Take Profit +10%
            if curr_close >= entry_price * 1.10:
                return True, "TAKE_PROFIT", curr_close

            # EXIT 2: Mean Reversion Complete - Close > BB Middle
            if curr_bb_middle is not None and curr_close > curr_bb_middle:
                return True, "MEAN_REVERSION", curr_close

            # EXIT 3: Disaster Stop -8% (protection)
            if curr_close <= entry_price * 0.92:
                return True, "DISASTER_STOP", curr_close

            # EXIT 4: Time exit 20 days
            if days_held >= 20:
                return True, "TIME_EXIT", curr_close

        # ============================================================
        # RULE 7: Breakout with Volume - OPTIMIZED
        # EXIT: TP +20%, Support-based Stop Loss (Breakout Level - ATR)
        # ============================================================
        elif rule == 7:
            # Calculate ATR for support-based stop
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_14 = tr.rolling(window=14, min_periods=14).mean()
            curr_atr = atr_14.iloc[idx] if idx >= 14 else entry_price * 0.03

            # Calculate 20-day high (breakout level) at entry
            high_20 = high.shift(1).rolling(window=20, min_periods=20).max()
            entry_idx = idx - days_held
            if entry_idx >= 20:
                breakout_level = high_20.iloc[entry_idx]
            else:
                breakout_level = entry_price * 0.97  # Fallback

            # Support-based Stop Loss: Breakout Level - 1x ATR
            support_stop = breakout_level - curr_atr

            # EXIT 1: Take Profit +20%
            if curr_close >= entry_price * 1.20:
                return True, "TAKE_PROFIT", curr_close

            # EXIT 2: Support-based Stop Loss
            if curr_close <= support_stop:
                return True, "STOP_LOSS", curr_close

            # EXIT 3: Momentum loss - Close < SMA(10)
            sma_10 = close.rolling(window=10, min_periods=10).mean()
            curr_sma_10 = sma_10.iloc[idx] if idx >= 10 else None

            if curr_sma_10 is not None and curr_close < curr_sma_10:
                return True, "MOMENTUM_LOSS", curr_close

            # EXIT 4: Time exit 15 days
            if days_held >= 15:
                return True, "TIME_EXIT", curr_close

        # ============================================================
        # RULE 8: Three MA System (SWING TRADING OPTIMIZED)
        # EXIT: Trailing Stop from High OR Close < SMA10 OR Time Exit 10 days
        # ============================================================
        elif rule == 8:
            sma_10 = close.rolling(window=10, min_periods=10).mean()
            sma_20 = close.rolling(window=20, min_periods=20).mean()
            sma_50 = close.rolling(window=50, min_periods=50).mean()

            curr_sma_10 = sma_10.iloc[idx] if idx >= 10 else None
            curr_sma_20 = sma_20.iloc[idx] if idx >= 20 else None
            curr_sma_50 = sma_50.iloc[idx] if idx >= 50 else None

            # Calculate ATR for trailing stop
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_14 = tr.rolling(window=14, min_periods=14).mean()
            curr_atr = atr_14.iloc[idx] if idx >= 14 else None

            # Calculate highest high since entry for trailing stop
            entry_idx = idx - days_held
            if entry_idx >= 0 and days_held > 0:
                highest_since_entry = high.iloc[entry_idx:idx+1].max()
            else:
                highest_since_entry = entry_price

            # SWING EXIT 1: Take Profit +10% (target hit)
            if curr_close >= entry_price * 1.10:
                return True, "TAKE_PROFIT", curr_close

            # SWING EXIT 2: Trailing Stop from highest (1.5x ATR)
            if curr_atr is not None and days_held >= 2:
                trailing_stop = highest_since_entry - (1.5 * curr_atr)
                if curr_close < trailing_stop and curr_close < highest_since_entry * 0.96:
                    return True, "TRAILING_STOP", curr_close

            # SWING EXIT 3: Close below SMA10 (quick momentum loss)
            if curr_sma_10 is not None and curr_close < curr_sma_10:
                return True, "MOMENTUM_LOSS", curr_close

            # SWING EXIT 4: MA Cross Down (SMA10 < SMA20)
            if curr_sma_10 is not None and curr_sma_20 is not None:
                if curr_sma_10 < curr_sma_20:
                    return True, "MA_CROSS_DOWN", curr_close

            # SWING EXIT 5: Breakdown below SMA50
            if curr_sma_50 is not None and curr_close < curr_sma_50:
                return True, "BREAKDOWN", curr_close

            # SWING EXIT 6: Max hold 10 days (swing trade limit)
            if days_held >= 10:
                return True, "TIME_EXIT", curr_close

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
        print(f"🔄 RUNNING BACKTEST (Rule-Specific Exit)")
        print(f"{'='*60}")
        print(f"Initial Capital: Rp {capital:,.0f}")
        print(f"Position Size: {self.config.position_size_pct*100:.0f}%")
        print(f"Rules: {self.config.rules}")
        print(f"Mode: {self.config.mode}")
        print(f"Tickers: {len(tickers)}")

        # Show rule-specific settings
        for r in self.config.rules:
            if r == 4:
                print(f"\n📌 Rule 4: RSI-2 Mean Reversion")
                print(f"   Entry: RSI(2) < 5, Close > SMA200")
                print(f"   Exit: Close > SMA5 + RSI > 60, Disaster -20%, Time 20d")
            elif r == 5:
                print(f"\n📌 Rule 5: Dual MA Crossover")
                print(f"   Entry: Golden Cross, Vol 1.5x, RSI > 50, ADX > 20")
                print(f"   Exit: TP +15%, SL -8%, Breakdown < SMA50, Time 20d")
            elif r == 6:
                print(f"\n📌 Rule 6: Bollinger Mean Reversion")
                print(f"   Entry: Close < BB_Lower, %B < 0, RSI < 30")
                print(f"   Exit: TP +10% or BB_Middle, Disaster -8%, Time 20d")
            elif r == 7:
                print(f"\n📌 Rule 7: Breakout Volume")
                print(f"   Entry: Breakout 2%+, Vol 2x, Base Pattern")
                print(f"   Exit: TP +20%, Support-based SL, Time 15d")

        print(f"\n{'='*60}\n")

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
                        idx = df.index[mask][0]
                        df_idx = df.index.get_loc(idx)
                        days_held = (datetime.strptime(current_date, '%Y-%m-%d') -
                                    datetime.strptime(trade.entry_date, '%Y-%m-%d')).days

                        # Use rule-specific exit conditions
                        should_exit, reason, exit_price = self._check_exit_for_rule(
                            df, df_idx, trade, days_held
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
