"""
GemaScreener Watchlist
Daftar saham: LQ45 + Layer 2 Agresif + Top 100 Market Cap
Total: ~130 saham
"""

# ============================================
# LQ45 (45 Saham Paling Liquid)
# Update: Januari 2025
# ============================================
LQ45 = [
    "ACES", "ADRO", "AKRA", "AMMN", "AMRT",
    "ANTM", "ASII", "BBCA", "BBNI", "BBRI",
    "BBTN", "BFIN", "BMRI", "BRPT", "BUKA",
    "CPIN", "EMTK", "ESSA", "EXCL", "GGRM",
    "GOTO", "HRUM", "ICBP", "INCO", "INDF",
    "INKP", "INTP", "ISAT", "ITMG", "KLBF",
    "MAPI", "MDKA", "MEDC", "MIKA", "PGAS",
    "PGEO", "PTBA", "SMGR", "TBIG", "TINS",
    "TLKM", "TOWR", "TPIA", "UNTR", "UNVR"
]

# ============================================
# LAYER 2 AGRESIF (Saham Volatil, Sering Digoreng)
# Karakteristik: Volatilitas tinggi, Market Cap 1T-20T
# ============================================
LAYER2_AGRESIF = [
    # Banking Layer 2
    "BRIS", "ARTO", "BBYB", "AGRO", "BGTG",
    "BBSI", "BMAS", "BTPS", "BVIC", "MCOR",
    "NISP", "NOBU", "PNBN", "SDRA",

    # Property & Construction (Volatile)
    "PANI", "PWON", "SMRA", "BSDE", "CTRA",
    "LPKR", "DILD", "KIJA", "PPRO", "WIKA",
    "WSKT", "PTPP", "ADHI", "TOTL", "NRCA",

    # Mining Layer 2
    "MBMA", "NCKL", "INDY", "BUMI", "DSSA",
    "PTRO", "MYOH", "GEMS", "BYAN",

    # Consumer & Retail (Agresif)
    "AVIA", "KEJU", "CAMP", "CLEO", "GOOD",
    "HOKI", "KINO", "MYOR", "SIDO", "ULTJ",

    # Tech & Telco Layer 2
    "DCII", "MTDL", "FREN", "LINK",

    # Misc High Volatility
    "TARA", "PNGO", "CBDK", "FILM", "KPIG",
    "MSIN", "PANR", "SCMA", "MNCN", "BMTR",
    "SILO", "HEAL", "PRDA", "SRAJ", "SAME"
]

# ============================================
# TOP 100 MARKET CAP (Yang belum masuk di atas)
# ============================================
TOP_MARKET_CAP_OTHERS = [
    # Big Caps yang belum masuk LQ45
    "BREN", "CUAN", "DNET", "PNLF", "SRTG",
    "TMAS", "BNLI", "BTPN", "MEGA", "BDMN",

    # Consumer Goods
    "HMSP", "MLBI", "DLTA", "TCID", "UNTR",

    # Industrial
    "AUTO", "SMSM", "BOLT", "IMPC", "TKIM",

    # Plantation
    "LSIP", "SIMP", "SGRO", "SSMS", "DSNG",

    # Healthcare
    "KLBF", "SIDO", "TSPC", "DVLA", "PYFA",

    # Cement & Building Materials
    "WTON", "SMBR", "ARNA", "MARK", "CAKK",

    # Others
    "JSMR", "META", "ERAA", "DMAS", "BJTM",
    "BJBR", "SMMA", "LPGI", "ABMM", "FIRE",
    "SGER", "TAPG", "ADMR", "AADI", "GJTL"
]

# ============================================
# COMBINED WATCHLIST (Tanpa duplikat)
# ============================================
def get_all_watchlist():
    """Gabungkan semua watchlist tanpa duplikat"""
    all_stocks = set()
    all_stocks.update(LQ45)
    all_stocks.update(LAYER2_AGRESIF)
    all_stocks.update(TOP_MARKET_CAP_OTHERS)
    return sorted(list(all_stocks))

def get_watchlist_with_suffix():
    """Return watchlist dengan suffix .JK untuk Yahoo Finance"""
    return [f"{stock}.JK" for stock in get_all_watchlist()]

def get_lq45_with_suffix():
    """Return LQ45 dengan suffix .JK"""
    return [f"{stock}.JK" for stock in LQ45]

def get_layer2_with_suffix():
    """Return Layer 2 Agresif dengan suffix .JK"""
    return [f"{stock}.JK" for stock in LAYER2_AGRESIF]

# ============================================
# STATISTICS
# ============================================
ALL_WATCHLIST = get_all_watchlist()
TOTAL_STOCKS = len(ALL_WATCHLIST)

if __name__ == "__main__":
    print(f"=" * 50)
    print(f"GEMA SCREENER WATCHLIST")
    print(f"=" * 50)
    print(f"LQ45           : {len(LQ45)} saham")
    print(f"Layer 2 Agresif: {len(LAYER2_AGRESIF)} saham")
    print(f"Top Market Cap : {len(TOP_MARKET_CAP_OTHERS)} saham")
    print(f"-" * 50)
    print(f"TOTAL (unique) : {TOTAL_STOCKS} saham")
    print(f"=" * 50)
    print(f"\nDaftar Saham:")
    for i, stock in enumerate(ALL_WATCHLIST, 1):
        print(f"{i:3}. {stock}")
