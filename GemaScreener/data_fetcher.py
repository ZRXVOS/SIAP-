"""
GemaScreener Data Fetcher
Mengambil data saham dari Yahoo Finance
"""

import yfinance as yf
import pandas as pd
import time
from typing import Optional, Dict, List
from datetime import datetime, timedelta

from config import REQUEST_DELAY, REQUEST_TIMEOUT
from indicators import calculate_all_indicators, calculate_intraday_indicators


def fetch_stock_data(ticker: str, period: str = "3mo", interval: str = "1d") -> Optional[pd.DataFrame]:
    """
    Mengambil data saham dari Yahoo Finance

    Args:
        ticker: Kode saham (contoh: "BBCA.JK")
        period: Periode data (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval: Interval data (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

    Returns:
        DataFrame dengan kolom: Open, High, Low, Close, Volume, dan indikator
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval, timeout=REQUEST_TIMEOUT)

        if df.empty:
            return None

        # Reset index untuk menjadikan Date sebagai kolom
        df = df.reset_index()

        # Rename kolom jika perlu
        if 'Datetime' in df.columns:
            df = df.rename(columns={'Datetime': 'Date'})

        # Hitung semua indikator
        if interval == "1d":
            df = calculate_all_indicators(df)
        else:
            df = calculate_intraday_indicators(df)

        return df

    except Exception as e:
        print(f"Error fetching {ticker}: {str(e)}")
        return None


def fetch_intraday_data(ticker: str, interval: str = "5m") -> Optional[pd.DataFrame]:
    """
    Mengambil data intraday dari Yahoo Finance

    Args:
        ticker: Kode saham (contoh: "BBCA.JK")
        interval: Interval (1m, 2m, 5m, 15m, 30m, 60m)

    Returns:
        DataFrame dengan data intraday
    """
    try:
        stock = yf.Ticker(ticker)
        # Yahoo Finance hanya menyediakan data intraday untuk 7 hari terakhir
        df = stock.history(period="7d", interval=interval, timeout=REQUEST_TIMEOUT)

        if df.empty:
            return None

        df = df.reset_index()
        if 'Datetime' in df.columns:
            df = df.rename(columns={'Datetime': 'Date'})

        df = calculate_intraday_indicators(df)
        return df

    except Exception as e:
        print(f"Error fetching intraday {ticker}: {str(e)}")
        return None


def fetch_multiple_stocks(tickers: List[str], period: str = "3mo",
                          show_progress: bool = True) -> Dict[str, pd.DataFrame]:
    """
    Mengambil data untuk multiple saham

    Args:
        tickers: List kode saham
        period: Periode data
        show_progress: Tampilkan progress bar

    Returns:
        Dictionary {ticker: DataFrame}
    """
    results = {}
    total = len(tickers)

    for i, ticker in enumerate(tickers, 1):
        if show_progress:
            progress = f"[{i}/{total}]"
            print(f"\r{progress} Fetching {ticker}...", end="", flush=True)

        df = fetch_stock_data(ticker, period=period)

        if df is not None and not df.empty:
            results[ticker] = df

        # Delay untuk menghindari rate limit
        time.sleep(REQUEST_DELAY)

    if show_progress:
        print()  # New line setelah progress

    return results


def get_latest_data(df: pd.DataFrame) -> Optional[pd.Series]:
    """
    Ambil data terbaru (baris terakhir) dari DataFrame

    Args:
        df: DataFrame dengan data saham

    Returns:
        Series dengan data terbaru
    """
    if df is None or df.empty:
        return None

    return df.iloc[-1]


def get_prev_data(df: pd.DataFrame, days_back: int = 1) -> Optional[pd.Series]:
    """
    Ambil data n hari sebelumnya

    Args:
        df: DataFrame dengan data saham
        days_back: Berapa hari ke belakang

    Returns:
        Series dengan data
    """
    if df is None or df.empty or len(df) <= days_back:
        return None

    return df.iloc[-(days_back + 1)]


def format_number(num: float) -> str:
    """Format angka ke format yang mudah dibaca (K, M, B, T)"""
    if num is None or pd.isna(num):
        return "N/A"

    abs_num = abs(num)
    sign = "-" if num < 0 else ""

    if abs_num >= 1_000_000_000_000:
        return f"{sign}{abs_num/1_000_000_000_000:.2f}T"
    elif abs_num >= 1_000_000_000:
        return f"{sign}{abs_num/1_000_000_000:.2f}B"
    elif abs_num >= 1_000_000:
        return f"{sign}{abs_num/1_000_000:.2f}M"
    elif abs_num >= 1_000:
        return f"{sign}{abs_num/1_000:.2f}K"
    else:
        return f"{sign}{abs_num:.2f}"


def format_price(price: float) -> str:
    """Format harga saham"""
    if price is None or pd.isna(price):
        return "N/A"
    return f"{price:,.0f}"


def format_percent(value: float) -> str:
    """Format persentase"""
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:+.2f}%"


if __name__ == "__main__":
    # Test fetch single stock
    print("Testing data fetcher...")
    print("-" * 50)

    ticker = "BBCA.JK"
    print(f"Fetching {ticker}...")

    df = fetch_stock_data(ticker, period="1mo")

    if df is not None:
        print(f"Data shape: {df.shape}")
        print(f"\nLatest data:")
        latest = get_latest_data(df)
        print(f"  Close: {format_price(latest['Close'])}")
        print(f"  Volume: {format_number(latest['Volume'])}")
        print(f"  Value: {format_number(latest['Value'])}")
        print(f"  RSI: {latest['RSI']:.2f}")
        print(f"  SMA50: {format_price(latest['SMA50'])}")
    else:
        print("Failed to fetch data")
