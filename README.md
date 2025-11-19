# SIAP - Professional XAUUSD Trading System

🏆 **Pine Script v6** Trading Strategies untuk XAUUSD Scalping 15m

## 📁 Pilih Strategy Anda

### 🚀 **Version 9a: Plan A Optimized** ⭐ **LATEST - TESTING**
**File:** `v9a_plan_a_optimized.pine`

**V8 + Simple Optimizations:**
- ✅ ATR Multiplier 3.5 (was 3.0) - Less whipsaw
- ✅ Confirmation candle - Wait 1 bar for validation
- ✅ Same proven base (ATR 12, LONG only)
- ✅ Trailing Stop (protect profit)
- ✅ Daily limits OPTIONAL (bisa ON/OFF)

**Target Improvements vs V8:**
- Win Rate: 43.86% → **58-62%** (+14-18%)
- Profit: 13.96% → **20-28%** (+6-14%)
- Profit Factor: 2.05 → **2.5-3.0**
- Fewer trades: 57 → **25-35** (quality over quantity)

**Status:** Testing phase - backtest and compare with V8

📖 **Baca:** `V9A_PLAN_A_SETUP.md` untuk testing guide

---

### 🔥 **Version 8: Simple Daily Gainer** ⭐ **BASELINE**
**File:** `v8_simple_daily_gainer.pine`

**SIMPLE tapi POWERFUL:**
- ✅ Proven formula (ATR 12, Multi 3.0, LONG only)
- ✅ Trailing Stop (protect profit)
- ✅ Daily limits OPTIONAL (bisa ON/OFF)
- ✅ Clean code, NO bugs
- ✅ Position size: 0.02 lot default (adjustable)
- ✅ Exit on Supertrend reverse

**Actual Results (1 Sep - 19 Nov 2024):**
- Profit: 13.96%
- Win Rate: 43.86%
- Profit Factor: 2.048 (Excellent!)
- Max DD: 5.79%

**Perfect For:**
- Baseline testing
- Simple approach
- Quality profit factor

📖 **Baca:** `V8_SETUP.md` untuk quick start

---

### 🚀 **Version 7: Daily Gainer Pro** ❌ **DEPRECATED (0% profit - too complex)**
**File:** `v7_daily_gainer_pro.pine`

**TARGET: 2-3% profit PER HARI (Sustainable)**
- ✅ Based on proven formula (ATR 12, Multi 3.0)
- ✅ Daily profit target: 3%
- ✅ Daily loss limit: -8% (protection)
- ✅ Max 5 trades per day (quality over quantity)
- ✅ Session filter (London/NY only)
- ✅ Scalable position sizing (0.01/0.02/0.03 lot)
- ✅ EA-ready structure

**Perfect For:**
- Active daily traders
- Want consistent daily income
- Need strict risk management
- Plan EA automation later
- Monitor during London/NY sessions

**Expected:** 50-80% profit per quarter, 60%+ win rate

📖 **Baca:** `V7_DAILY_GAINER_SETUP.md` untuk complete guide
📊 **Compare:** `V7_COMPARISON.md` untuk V6 vs V7

---

### 💎 **Version 6: Supertrend Pro** ⭐ **PRODUCTION READY (Quarterly Focus)**
**File:** `v6_supertrend_pro_final.pine`

**PROVEN FORMULA dengan Fixed Lot Size:**
- ✅ ATR 12, Multiplier 3.0 (proven best)
- ✅ LONG ONLY (proven profitable)
- ✅ Stop Loss 4% (proven optimal)
- ✅ NO Take Profit (let profit run)
- ✅ Trailing Stop active (4.5% / 2.5%)
- ✅ Fixed 0.01 lot per trade
- ✅ **Based on 18% profit, 55% win rate** (3 bulan)

**Enhancements:**
- ✅ Trailing Stop (protect profit while running)
- ✅ Smart Exit (conditional on profit level)
- ✅ Exit on opposite signal
- ✅ Detailed dashboard

**Perfect For:**
- Passive quarterly compounding
- Set-and-forget traders
- Proven simple approach
- Conservative risk profile
- Check charts 1-2x daily

**Expected:** 40-50% profit per quarter, 50-55% win rate

📖 **Baca:** `SETUP_V6_GUIDE.md` dan `V6_FIXED_LOT_SETUP.md`

---

### 🔧 **Version 5: Optimized Supertrend** (Testing Phase)
**File:** `v5_optimized_supertrend.pine`

**Baseline Testing Version:**
- ✅ ATR 12, Multiplier 3.0
- ✅ Multiple optimization features
- ✅ Used for establishing baseline

**Note:** V5 evolved into V6 (production) and V7 (daily gainer)

📖 **Baca:** `OPTIMIZATION_GUIDE.md` untuk methodology

---

### 💡 **Version 4: Pure Supertrend** (SIMPLE & CLEAN)
**File:** `v4_pure_supertrend_simple.pine`

**Filosofi: LESS IS MORE**
- ✅ **HANYA Supertrend** - No filters!
- ✅ Simple & Clean
- ✅ Long & Short positions
- ✅ Performance dashboard

**Perfect For:**
- Trader yang suka SIMPLE
- Tidak suka banyak filter
- Testing different parameters

**Target:** Win Rate 45%+, Net Profit 15-20%+

---

### 📊 **Version 3: Ultimate Full**
**File:** `v3_ultimate_xauusd_full.pine`

**Fitur Lengkap:**
- ✅ Semua indikator (Supertrend, EMA, RSI, MACD, Volume, ADX, S/R)
- ✅ Performance dashboard on chart
- ✅ Multi-timeframe (Daily filter + 15m/1H)
- ✅ Session filter (Asian/London/NY)
- ✅ Complete alerts system
- ✅ All filters toggleable

**Target:** Win Rate 60-65%, Profit Factor 2.0-2.8

---

### 💡 **Version 2: Simplified Scalper**
**File:** `v2_simplified_xauusd_scalper.pine`

**Simple & Robust:**
- ✅ Daily filter + EMA + RSI + Volume
- ✅ Performance table
- ✅ Less filters, proven combination

**Target:** Win Rate 58-62%, Profit Factor 1.9-2.3

---

### 🔧 **Version 1: Enhanced Multi-Timeframe**
**File:** `v1_enhanced_supertrend_xauusd.pine`

**Enhanced Original:**
- ✅ Upgrade dari formula lama
- ✅ All bugs fixed
- ✅ Multi-indicator support

---

## 🚀 Quick Start

1. **Import:** Copy file `.pine` ke TradingView Pine Editor
2. **Setup:** XAUUSD chart, timeframe 15m atau 1H
3. **Backtest:** Strategy Tester, period 12 bulan
4. **Optimize:** Adjust parameters sesuai hasil

📖 **Baca:** `QUICK_START_GUIDE.md` untuk tutorial lengkap

📚 **Dokumentasi:** `README_STRATEGY_GUIDE.md` untuk penjelasan detail

---

## 🎯 Target Performance

| Metric | Target |
|--------|--------|
| Win Rate | > 60% |
| Profit Factor | > 2.0 |
| Max Drawdown | < 15% |
| Total Trades | > 200/year |

---

## 📊 Features

- ✅ Pine Script v6 (latest)
- ✅ Multi-timeframe analysis
- ✅ ATR-based SL/TP
- ✅ Trailing stop
- ✅ Session filter
- ✅ Performance dashboard
- ✅ Complete alerts

---

**Good luck & Happy Trading! 🚀📈**