"""
ForexScreener Configuration
Konfigurasi untuk Forex Backtesting
"""

# ============================================================
# FOREX PAIRS
# ============================================================
# Yahoo Finance ticker format: EURUSD=X, GC=F (gold futures)

FOREX_PAIRS = {
    # Tier 1: Sangat Volatile
    "XAUUSD": {"yahoo": "GC=F", "name": "Gold", "pip_size": 0.01, "spread_pips": 3},
    "GBPJPY": {"yahoo": "GBPJPY=X", "name": "Guppy", "pip_size": 0.01, "spread_pips": 3},

    # Tier 2: Volatile Moderat
    "GBPUSD": {"yahoo": "GBPUSD=X", "name": "Cable", "pip_size": 0.0001, "spread_pips": 2},
    "EURJPY": {"yahoo": "EURJPY=X", "name": "Yuppy", "pip_size": 0.01, "spread_pips": 2},
    "USDJPY": {"yahoo": "USDJPY=X", "name": "Ninja", "pip_size": 0.01, "spread_pips": 1.5},
    "AUDUSD": {"yahoo": "AUDUSD=X", "name": "Aussie", "pip_size": 0.0001, "spread_pips": 2},

    # Tier 3: Stabil
    "EURUSD": {"yahoo": "EURUSD=X", "name": "Fiber", "pip_size": 0.0001, "spread_pips": 1},
    "USDCHF": {"yahoo": "USDCHF=X", "name": "Swissy", "pip_size": 0.0001, "spread_pips": 2},
}

# Default pairs untuk backtest
DEFAULT_PAIRS = ["XAUUSD", "GBPUSD", "EURUSD", "USDJPY", "AUDUSD"]

# ============================================================
# RULE NAMES
# ============================================================
RULE_NAMES = {
    4: "RSI-2 Mean Reversion (Larry Connors)",
    5: "Dual MA Crossover (Golden Cross)",
    6: "Bollinger Band Mean Reversion",
    7: "Breakout with Volume",
}

# ============================================================
# BACKTEST DEFAULTS
# ============================================================
DEFAULT_CAPITAL = 10_000        # USD $10,000
DEFAULT_POSITION_PCT = 0.30     # 30% per trade
DEFAULT_LEVERAGE = 20           # 1:20 leverage (conservative)
DEFAULT_TP = 0.10               # TP +10%
DEFAULT_SL = 0.05               # SL -5%
DEFAULT_MAX_HOLD = 5            # 5 days
DEFAULT_SPREAD_COST = 0.0003    # 0.03% spread cost estimate
