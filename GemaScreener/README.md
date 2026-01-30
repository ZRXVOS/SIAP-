# GemaScreener 🔥

Stock Screening Tool untuk IHSG - Deteksi pergerakan bandar dan anomali volume.

## Features

- **3 Rumus Screening**:
  - Rule 1: 9 Hari Konsisten Naik (deteksi uptrend kuat)
  - Rule 2: Breakout Kuat + Momentum (deteksi saham yang "meledak")
  - Rule 3: Reversal / Hammer Pattern (deteksi reversal dari bottom)

- **Watchlist**: LQ45 + Layer 2 Agresif + Top 100 Market Cap (~130 saham)
- **Output**: Terminal + Telegram Alert
- **Scheduler**: Auto-screening setiap 5 menit

## Installation

```bash
# Clone atau masuk ke folder
cd GemaScreener

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Commands

```bash
# Jalankan SEMUA rumus
python main.py --all

# Jalankan rumus tertentu
python main.py --rumus 1    # 9 Hari Konsisten Naik
python main.py --rumus 2    # Breakout Kuat + Momentum
python main.py --rumus 3    # Reversal / Hammer Pattern

# Tanpa Telegram (terminal only)
python main.py --all --no-telegram

# Test koneksi Telegram
python main.py --test

# Lihat daftar watchlist
python main.py --list
```

### Auto-Schedule Mode

```bash
# Auto-screening setiap 5 menit
python main.py --all --auto

# Menggunakan scheduler.py (lebih advanced)
python scheduler.py --interval 5

# Hanya saat market hours (09:00-16:00 WIB)
python scheduler.py --interval 5

# Jalankan 24/7 (termasuk di luar market hours)
python scheduler.py --interval 5 --all-hours

# Jalankan pada waktu tertentu
python scheduler.py --times 09:15 12:00 15:30
```

## Configuration

Edit `config.py` untuk mengubah:

```python
# Telegram
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"

# Schedule interval (detik)
SCHEDULE_INTERVAL = 300  # 5 menit

# Price filter
MIN_PRICE = 70
MAX_PRICE = 1600
```

## Rumus Detail

### Rule 1: 9 Hari Konsisten Naik
```
- HIGH > 2% dari prev CLOSE selama 9 hari berturut
- Value > 1B
- SMA Value 5 > 2B
- Price range 70-1600
- Close > SMA50 atau SMA200
- Volume naik
```

### Rule 2: Breakout Kuat + Momentum
```
- Close naik >= 8% dari kemarin
- Value > 5B
- Stochastic K > D atau RSI > 70 atau Stoch K > 80
- Volume breakout atau Price breakout
- CMF > 0
- ATR% > 3%
- Gap up (Open >= Prev Close)
```

### Rule 3: Reversal / Hammer Pattern
```
- Shadow bawah panjang (Low < 95% dari prev Close)
- Bullish candle (Close > Open)
- Value > 2B
- Engulfing pattern atau New Low recovery
```

## File Structure

```
GemaScreener/
├── main.py              # Entry point utama
├── config.py            # Konfigurasi
├── watchlist.py         # Daftar saham
├── data_fetcher.py      # Yahoo Finance data
├── indicators.py        # Technical indicators
├── telegram_alert.py    # Telegram notification
├── scheduler.py         # Auto-scheduler
├── rules/
│   ├── __init__.py
│   ├── rule1_konsisten.py
│   ├── rule2_breakout.py
│   └── rule3_reversal.py
└── requirements.txt
```

## Disclaimer

⚠️ **BUKAN REKOMENDASI INVESTASI**

Tool ini hanya untuk membantu screening. Selalu lakukan analisis sendiri sebelum mengambil keputusan investasi. Investasi saham memiliki risiko.

## Author

By Gema - GemaScreener 2024
