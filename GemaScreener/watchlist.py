"""
GemaScreener Watchlist - EXPANDED VERSION
Daftar saham: 400-500 saham dari berbagai sektor IDX
Update: Januari 2026
"""

# ============================================
# LQ45 (45 Saham Paling Liquid)
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
# IDX80 (Saham di luar LQ45)
# ============================================
IDX80_OTHERS = [
    "ARTO", "AUTO", "BBYB", "BDMN", "BJBR",
    "BJTM", "BNLI", "BRIS", "BSDE", "BTPN",
    "CTRA", "ERAA", "GJTL", "HMSP", "INDY",
    "JPFA", "JSMR", "LSIP", "MNCN", "PNBN",
    "PWON", "SCMA", "SIDO", "SMRA", "SRTG",
    "TKIM", "TSPC", "WIKA", "WOOD", "WTON"
]

# ============================================
# BANKING (All Listed Banks)
# ============================================
BANKING = [
    # Big Banks (already in LQ45)
    "BBCA", "BBRI", "BMRI", "BBNI", "BBTN",
    # Medium Banks
    "BRIS", "BTPN", "BNLI", "BDMN", "PNBN",
    "BJBR", "BJTM", "MEGA", "NISP", "BTPS",
    # Small Banks
    "ARTO", "BBYB", "AGRO", "BGTG", "BBSI",
    "BMAS", "BVIC", "MCOR", "NOBU", "SDRA",
    "BINA", "BKSW", "BNBA", "BNII", "BSWD",
    "BTPN", "DNAR", "INPC", "NAGA", "PNBS",
    "AGRS", "AMAR", "BABP", "BANK", "BBKP",
    "BBMD", "BCIC", "BEKS", "BHAT", "BINA"
]

# ============================================
# PROPERTY & REAL ESTATE
# ============================================
PROPERTY = [
    # Big Property
    "BSDE", "CTRA", "PWON", "SMRA", "LPKR",
    "DILD", "KIJA", "PPRO", "ASRI", "APLN",
    # Medium Property
    "PANI", "DMAS", "BEST", "BKSL", "CTRP",
    "GWSA", "JRPT", "MDLN", "MKPI", "MTSM",
    "NIRO", "OMRE", "PLIN", "POLL", "PUDP",
    "RBMS", "RDTX", "RODA", "SMDM", "TARA",
    # Small Property
    "BCIP", "BIKA", "BIPP", "COWL", "DART",
    "DUTI", "ELTY", "EMDE", "FORZ", "FMII",
    "GAMA", "GPRA", "LCGP", "LPCK", "LPGI",
    "MMLP", "MTLA", "MYRX", "NZIA", "PAMG",
    "POSA", "PRDA", "REAL", "RISE", "ROCK",
    "SATU", "SSIA", "URBN"
]

# ============================================
# CONSTRUCTION & INFRASTRUCTURE
# ============================================
CONSTRUCTION = [
    # Big Construction
    "WIKA", "WSKT", "PTPP", "ADHI", "JSMR",
    # Medium Construction
    "TOTL", "NRCA", "ACST", "DGIK", "IDPR",
    "MTRA", "PBSA", "SSIA", "WEGE", "TOPS",
    # Small Construction
    "BUKK", "CSIS", "IBST", "JKON", "META",
    "MYRX", "NUSA", "OASA", "PPRE", "PSAB",
    "PTDU", "SKRN", "SMKL", "SPTO", "TGRA"
]

# ============================================
# MINING (Coal, Metal, Oil & Gas)
# ============================================
MINING = [
    # Coal
    "ADRO", "PTBA", "ITMG", "HRUM", "BYAN",
    "INDY", "BUMI", "DSSA", "MBMA", "GEMS",
    "MYOH", "PTRO", "ARII", "BORN", "BSSR",
    "DEWA", "DOID", "FIRE", "GTBO", "KKGI",
    "PKPK", "PSAB", "SMMT", "SMRU", "TOBA",
    # Metal & Mineral
    "ANTM", "INCO", "TINS", "MDKA", "NCKL",
    "ADMR", "AADI", "CITA", "ZINC", "IFSH",
    "MITI", "NICL", "PSAB", "PURE", "RAJA",
    "SMRU", "SQMI", "TRAM", "ZINC",
    # Oil & Gas
    "MEDC", "PGAS", "ELSA", "ENRG", "ESSA",
    "HITS", "RUIS", "BULL", "APEX", "BIPI",
    "GTPC"
]

# ============================================
# CONSUMER GOODS (Food, Beverage, Tobacco)
# ============================================
CONSUMER = [
    # Food & Beverage
    "ICBP", "INDF", "MYOR", "ULTJ", "GOOD",
    "CLEO", "HOKI", "KEJU", "CAMP", "ADES",
    "AISA", "ALTO", "CEKA", "DLTA", "DMND",
    "FOOD", "MLBI", "PANI", "PCAR", "ROTI",
    "SKBM", "SKLT", "STTP", "TBLA",
    # Tobacco
    "GGRM", "HMSP", "WIIM", "RMBA",
    # Household & Personal Care
    "UNVR", "KINO", "TCID", "MRAT", "MBTO",
    "KPAS", "KICI", "LMPI", "CINT", "ENZO"
]

# ============================================
# RETAIL & TRADE
# ============================================
RETAIL = [
    # Modern Retail
    "AMRT", "ACES", "MAPI", "ERAA", "LPPF",
    "RALS", "HERO", "CSAP", "MIDI", "MPPA",
    # Automotive Retail
    "AUTO", "SMSM", "GJTL", "BRAM", "BOLT",
    "DRMA", "GDYR", "IMAS", "INDS", "LPIN",
    "MASA", "NIPS", "PRAS", "PTSN", "SMSM",
    # E-commerce & Tech Retail
    "BUKA", "GOTO", "MSIN", "KIOS"
]

# ============================================
# PLANTATION (Palm Oil, Rubber, etc)
# ============================================
PLANTATION = [
    "LSIP", "SIMP", "SGRO", "SSMS", "DSNG",
    "AALI", "ANJT", "BISI", "BWPT", "CPRO",
    "GZCO", "JAWA", "MAGP", "PALM", "PGUN",
    "PSGO", "SMAR", "TBLA", "UNSP"
]

# ============================================
# HEALTHCARE & PHARMACEUTICAL
# ============================================
HEALTHCARE = [
    # Pharmaceutical
    "KLBF", "SIDO", "TSPC", "DVLA", "PYFA",
    "KAEF", "INAF", "PEHA", "MERK", "SCPI",
    "SQBB", "SOHO",
    # Hospital & Healthcare
    "MIKA", "SILO", "HEAL", "PRDA", "SRAJ",
    "SAME", "PRIM", "BMHS"
]

# ============================================
# TELCO & TECHNOLOGY
# ============================================
TECHNOLOGY = [
    # Telecommunication
    "TLKM", "EXCL", "ISAT", "FREN", "LINK",
    "CENT", "WIFI", "SUPR",
    # IT & Technology
    "DCII", "MTDL", "MLPT", "ATIC", "DNET",
    "LUCK", "GLVA", "VIVA", "ZYRX",
    # Tower & Infrastructure
    "TBIG", "TOWR", "GHON", "IBST"
]

# ============================================
# MEDIA & ENTERTAINMENT
# ============================================
MEDIA = [
    "EMTK", "MNCN", "SCMA", "BMTR", "KPIG",
    "FILM", "MDIA", "JTPE", "TMPO", "VIVA",
    "LPLI", "ABBA", "BLTZ"
]

# ============================================
# INDUSTRIAL & MANUFACTURING
# ============================================
INDUSTRIAL = [
    # Cement & Building Materials
    "SMGR", "INTP", "SMBR", "WTON", "WSBP",
    "ARNA", "MARK", "CAKK", "MLIA", "TOTO",
    # Steel & Metal Products
    "ISSP", "KRAS", "BTON", "CTBN", "GDST",
    "INAI", "JKSW", "LION", "LMSH", "NIKL",
    "PICO", "TBMS",
    # Chemical
    "BRPT", "TPIA", "DPNS", "EKAD", "ETWA",
    "FPNI", "INCI", "MDKI", "SRSN", "TALF",
    "TDPM", "UNIC",
    # Pulp & Paper
    "INKP", "TKIM", "ALDO", "FASW", "KDSI",
    "KBRI", "SPMA", "SWAT",
    # Textile & Garment
    "ARGO", "BELL", "CNTX", "ERTX", "ESTI",
    "HDTX", "INDR", "MYTX", "PBRX", "POLY",
    "RICY", "SRIL", "SSTM", "STAR", "TFCO",
    "TRIS", "UNIT",
    # Packaging & Plastics
    "AKPI", "APLI", "BRNA", "FPNI", "IGAR",
    "IMPC", "IPOL", "PBID", "SIAP", "TALF",
    "TRST", "YPAS"
]

# ============================================
# TRANSPORTATION & LOGISTICS
# ============================================
TRANSPORTATION = [
    # Airlines & Aviation
    "GIAA", "CMPP", "SMDR", "SAFE",
    # Shipping & Logistics
    "TMAS", "SMDR", "BBRM", "BLTA", "BULL",
    "ESSA", "HAIS", "HITS", "KARW", "LEAD",
    "MBSS", "MIRA", "NELY", "PTIS", "RIGS",
    "SHIP", "SOCI", "TCPI", "TMAS", "TPMA",
    "WINS", "ZBRA",
    # Land Transport
    "BIRD", "TAXI", "WEHA", "LRNA"
]

# ============================================
# ENERGY & UTILITIES
# ============================================
ENERGY = [
    "PGEO", "PGAS", "AKRA", "POWR", "RAJA",
    "KEEN", "KOPI", "PNGO", "SGER", "BPTR",
    "IPTV", "PETR", "RGAS", "SAFE", "TAMU"
]

# ============================================
# FINANCIAL SERVICES (Non-Bank)
# ============================================
FINANCIAL = [
    # Multi Finance
    "BFIN", "ADMF", "CFIN", "MFIN", "TIFA",
    "VRNA", "WOMF", "HDFA", "BPFI", "DEFI",
    "FINN", "FUJI", "IBFN", "IMJS", "INCF",
    "MGNA", "PNLF", "SMMA", "TRUS",
    # Insurance
    "ASBI", "ASDM", "ASJT", "ASRM", "JMAS",
    "LPGI", "MREI", "PNIN", "AHAP", "AMAG",
    # Investment & Securities
    "KREN", "PADI", "PANS", "TRIM", "YULE"
]

# ============================================
# MISC HIGH VOLATILITY & SPECULATIVE
# ============================================
SPECULATIVE = [
    "TARA", "PNGO", "CBDK", "PANR", "BTEK",
    "BOLA", "BOSS", "CLAY", "DEAL", "DIGI",
    "EDGE", "ELLO", "ENVY", "ESTA", "FLMC",
    "FORU", "GTRA", "HAJJ", "HILL", "HOMI",
    "HOTL", "ICON", "INPS", "ITIC", "JIHD",
    "KJEN", "KONI", "LMAS", "MINA", "NASA",
    "NFCX", "NICK", "OCAP", "OILS", "PACK",
    "PAMG", "PEVE", "PNSE", "POOL", "PORT",
    "PSKT", "RANC", "SAPX", "SBAT", "SHIP",
    "SINI", "SKYB", "SLIS", "SOSS", "SUGI",
    "TAMA", "TAPG", "TAXI", "TELE", "TOPS",
    "TPMA", "UNIQ", "VINS", "WAPO", "WGSH"
]

# ============================================
# COMBINED WATCHLIST (Tanpa duplikat)
# ============================================
def get_all_watchlist():
    """Gabungkan semua watchlist tanpa duplikat"""
    all_stocks = set()
    all_stocks.update(LQ45)
    all_stocks.update(IDX80_OTHERS)
    all_stocks.update(BANKING)
    all_stocks.update(PROPERTY)
    all_stocks.update(CONSTRUCTION)
    all_stocks.update(MINING)
    all_stocks.update(CONSUMER)
    all_stocks.update(RETAIL)
    all_stocks.update(PLANTATION)
    all_stocks.update(HEALTHCARE)
    all_stocks.update(TECHNOLOGY)
    all_stocks.update(MEDIA)
    all_stocks.update(INDUSTRIAL)
    all_stocks.update(TRANSPORTATION)
    all_stocks.update(ENERGY)
    all_stocks.update(FINANCIAL)
    all_stocks.update(SPECULATIVE)
    return sorted(list(all_stocks))

def get_watchlist_with_suffix():
    """Return watchlist dengan suffix .JK untuk Yahoo Finance"""
    return [f"{stock}.JK" for stock in get_all_watchlist()]

def get_lq45_with_suffix():
    """Return LQ45 dengan suffix .JK"""
    return [f"{stock}.JK" for stock in LQ45]

def get_by_sector(sector: str):
    """Return saham berdasarkan sektor"""
    sectors = {
        'lq45': LQ45,
        'banking': BANKING,
        'property': PROPERTY,
        'construction': CONSTRUCTION,
        'mining': MINING,
        'consumer': CONSUMER,
        'retail': RETAIL,
        'plantation': PLANTATION,
        'healthcare': HEALTHCARE,
        'technology': TECHNOLOGY,
        'media': MEDIA,
        'industrial': INDUSTRIAL,
        'transportation': TRANSPORTATION,
        'energy': ENERGY,
        'financial': FINANCIAL,
        'speculative': SPECULATIVE
    }
    return sectors.get(sector.lower(), [])

def get_by_sector_with_suffix(sector: str):
    """Return saham sektor dengan suffix .JK"""
    return [f"{stock}.JK" for stock in get_by_sector(sector)]

# ============================================
# STATISTICS
# ============================================
ALL_WATCHLIST = get_all_watchlist()
TOTAL_STOCKS = len(ALL_WATCHLIST)

SECTOR_COUNTS = {
    'LQ45': len(LQ45),
    'IDX80 Others': len(IDX80_OTHERS),
    'Banking': len(BANKING),
    'Property': len(PROPERTY),
    'Construction': len(CONSTRUCTION),
    'Mining': len(MINING),
    'Consumer': len(CONSUMER),
    'Retail': len(RETAIL),
    'Plantation': len(PLANTATION),
    'Healthcare': len(HEALTHCARE),
    'Technology': len(TECHNOLOGY),
    'Media': len(MEDIA),
    'Industrial': len(INDUSTRIAL),
    'Transportation': len(TRANSPORTATION),
    'Energy': len(ENERGY),
    'Financial': len(FINANCIAL),
    'Speculative': len(SPECULATIVE)
}

if __name__ == "__main__":
    print(f"=" * 60)
    print(f"GEMA SCREENER WATCHLIST - EXPANDED VERSION")
    print(f"=" * 60)
    print(f"\nSECTOR BREAKDOWN:")
    print(f"-" * 40)
    for sector, count in SECTOR_COUNTS.items():
        print(f"  {sector:20} : {count:3} saham")
    print(f"-" * 40)
    print(f"  {'TOTAL (unique)':20} : {TOTAL_STOCKS:3} saham")
    print(f"=" * 60)
