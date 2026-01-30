"""
GemaScreener Configuration
Konfigurasi untuk Telegram Bot dan pengaturan lainnya
"""

# ============================================
# TELEGRAM CONFIGURATION
# ============================================
TELEGRAM_BOT_TOKEN = "8579079685:AAF6t_Ra1I5xFPbb1Kb_vmB35lkWEFr_oxY"
TELEGRAM_CHAT_ID = "698017480"

# ============================================
# SCREENING SETTINGS
# ============================================
# Interval auto-scheduler (dalam detik)
SCHEDULE_INTERVAL = 300  # 5 menit = 300 detik

# Delay antara request ke Yahoo Finance (hindari rate limit)
REQUEST_DELAY = 1  # detik

# Timeout untuk request
REQUEST_TIMEOUT = 30  # detik

# ============================================
# FILTER SETTINGS (Default dari rumus)
# ============================================
# Price range filter
MIN_PRICE = 70
MAX_PRICE = 1600

# Value filters (dalam Rupiah)
MIN_VALUE_1B = 1_000_000_000      # 1 Milyar
MIN_VALUE_2B = 2_000_000_000      # 2 Milyar
MIN_VALUE_5B = 5_000_000_000      # 5 Milyar
MIN_VALUE_500M = 500_000_000     # 500 Juta
MIN_SMA_VALUE_2B = 2_000_000_000  # SMA Value > 2B

# ============================================
# INDICATOR SETTINGS
# ============================================
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

STOCH_K_PERIOD = 14
STOCH_D_PERIOD = 3
STOCH_SMOOTH = 3
STOCH_OVERBOUGHT = 80
STOCH_OVERSOLD = 20

SMA_SHORT = 20
SMA_MEDIUM = 50
SMA_LONG = 200

ATR_PERIOD = 14
CMF_PERIOD = 20
BOLLINGER_PERIOD = 20

# ============================================
# DISPLAY SETTINGS
# ============================================
# Warna untuk terminal (ANSI codes)
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# ============================================
# RUMUS NAMES
# ============================================
RUMUS_NAMES = {
    1: "9 Hari Konsisten Naik",
    2: "Breakout Kuat + Momentum",
    3: "Reversal / Hammer Pattern",
    4: "RSI-2 Mean Reversion",
    5: "Dual MA Crossover",
    6: "Bollinger Mean Reversion",
    7: "Breakout Volume"
}
