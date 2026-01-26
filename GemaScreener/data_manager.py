#!/usr/bin/env python3
"""
GemaScreener Data Manager
Download dan manage data historis ke SQLite database
"""

import sqlite3
import pandas as pd
import yfinance as yf
import argparse
import time
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from pathlib import Path

from config import REQUEST_DELAY, Colors
from watchlist import get_watchlist_with_suffix, get_all_watchlist, TOTAL_STOCKS


# Database path
DB_PATH = Path(__file__).parent / "data" / "gema_screener.db"


def get_connection() -> sqlite3.Connection:
    """Get SQLite database connection"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database tables"""
    conn = get_connection()
    cursor = conn.cursor()

    # Table: stocks (master data)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            ticker TEXT PRIMARY KEY,
            name TEXT,
            sector TEXT,
            last_update TEXT
        )
    ''')

    # Table: daily_prices (OHLCV data)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            adj_close REAL,
            UNIQUE(ticker, date)
        )
    ''')

    # Table: metadata
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # Create indexes for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_prices_ticker ON daily_prices(ticker)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_prices_date ON daily_prices(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_prices_ticker_date ON daily_prices(ticker, date)')

    conn.commit()
    conn.close()
    print(f"{Colors.GREEN}✅ Database initialized{Colors.ENDC}")


def download_stock_data(ticker: str, period: str = "3y") -> Optional[pd.DataFrame]:
    """
    Download data untuk satu saham dari Yahoo Finance

    Args:
        ticker: Kode saham (contoh: "BBCA.JK")
        period: Periode (1y, 2y, 3y, 5y, max)

    Returns:
        DataFrame dengan OHLCV data
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, auto_adjust=False)

        if df.empty:
            return None

        df = df.reset_index()
        df['ticker'] = ticker

        # Rename columns
        df = df.rename(columns={
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Adj Close': 'adj_close'
        })

        # Convert date to string
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')

        # Select only needed columns
        df = df[['ticker', 'date', 'open', 'high', 'low', 'close', 'volume', 'adj_close']]

        return df

    except Exception as e:
        print(f"{Colors.RED}Error downloading {ticker}: {e}{Colors.ENDC}")
        return None


def save_to_database(df: pd.DataFrame, ticker: str):
    """Save DataFrame to SQLite database"""
    if df is None or df.empty:
        return

    conn = get_connection()

    # Insert or replace data
    df.to_sql('daily_prices', conn, if_exists='append', index=False,
              method='multi', chunksize=500)

    # Update stocks table
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO stocks (ticker, last_update)
        VALUES (?, ?)
    ''', (ticker, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    conn.commit()
    conn.close()


def download_all_stocks(period: str = "3y", show_progress: bool = True):
    """
    Download data untuk semua saham di watchlist

    Args:
        period: Periode data (1y, 2y, 3y, 5y)
        show_progress: Tampilkan progress
    """
    init_database()

    tickers = get_watchlist_with_suffix()
    total = len(tickers)
    success = 0
    failed = []

    print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}📥 DOWNLOADING HISTORICAL DATA{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"Total saham: {total}")
    print(f"Periode: {period}")
    print(f"Database: {DB_PATH}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}\n")

    start_time = time.time()

    for i, ticker in enumerate(tickers, 1):
        if show_progress:
            print(f"\r[{i}/{total}] Downloading {ticker}...", end="", flush=True)

        df = download_stock_data(ticker, period)

        if df is not None and not df.empty:
            # Delete existing data for this ticker first (to avoid duplicates)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM daily_prices WHERE ticker = ?', (ticker,))
            conn.commit()
            conn.close()

            save_to_database(df, ticker)
            success += 1
        else:
            failed.append(ticker)

        time.sleep(REQUEST_DELAY)

    elapsed = time.time() - start_time

    print(f"\n\n{Colors.GREEN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.GREEN}✅ DOWNLOAD COMPLETE{Colors.ENDC}")
    print(f"{Colors.GREEN}{'='*60}{Colors.ENDC}")
    print(f"Berhasil: {success}/{total} saham")
    print(f"Gagal: {len(failed)} saham")
    print(f"Waktu: {elapsed:.1f} detik")
    print(f"Database: {DB_PATH}")

    if failed:
        print(f"\n{Colors.YELLOW}Saham yang gagal:{Colors.ENDC}")
        for t in failed[:10]:
            print(f"  - {t}")
        if len(failed) > 10:
            print(f"  ... dan {len(failed)-10} lainnya")

    # Update metadata
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO metadata (key, value)
        VALUES ('last_full_download', ?)
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))
    cursor.execute('''
        INSERT OR REPLACE INTO metadata (key, value)
        VALUES ('download_period', ?)
    ''', (period,))
    conn.commit()
    conn.close()


def update_data(show_progress: bool = True):
    """Update data dengan data terbaru (incremental)"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get all tickers in database
    cursor.execute('SELECT DISTINCT ticker FROM daily_prices')
    tickers = [row[0] for row in cursor.fetchall()]
    conn.close()

    if not tickers:
        print(f"{Colors.YELLOW}Database kosong. Jalankan --download-all terlebih dahulu.{Colors.ENDC}")
        return

    total = len(tickers)
    updated = 0

    print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}🔄 UPDATING DATA{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"Total saham: {total}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}\n")

    start_time = time.time()

    for i, ticker in enumerate(tickers, 1):
        if show_progress:
            print(f"\r[{i}/{total}] Updating {ticker}...", end="", flush=True)

        # Get last date in database
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT MAX(date) FROM daily_prices WHERE ticker = ?
        ''', (ticker,))
        last_date = cursor.fetchone()[0]
        conn.close()

        if last_date:
            last_date = datetime.strptime(last_date, '%Y-%m-%d')
            # Download dari last_date + 1 sampai sekarang
            start_date = last_date + timedelta(days=1)

            if start_date.date() >= datetime.now().date():
                continue  # Already up to date

            try:
                stock = yf.Ticker(ticker)
                df = stock.history(start=start_date.strftime('%Y-%m-%d'), auto_adjust=False)

                if not df.empty:
                    df = df.reset_index()
                    df['ticker'] = ticker
                    df = df.rename(columns={
                        'Date': 'date', 'Open': 'open', 'High': 'high',
                        'Low': 'low', 'Close': 'close', 'Volume': 'volume',
                        'Adj Close': 'adj_close'
                    })
                    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                    df = df[['ticker', 'date', 'open', 'high', 'low', 'close', 'volume', 'adj_close']]

                    save_to_database(df, ticker)
                    updated += 1
            except:
                pass

        time.sleep(0.5)

    elapsed = time.time() - start_time

    print(f"\n\n{Colors.GREEN}✅ Update complete: {updated} saham diupdate ({elapsed:.1f}s){Colors.ENDC}")

    # Update metadata
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO metadata (key, value)
        VALUES ('last_update', ?)
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))
    conn.commit()
    conn.close()


def get_stock_data(ticker: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Get stock data from database

    Args:
        ticker: Kode saham (dengan atau tanpa .JK)
        start_date: Tanggal mulai (YYYY-MM-DD)
        end_date: Tanggal akhir (YYYY-MM-DD)

    Returns:
        DataFrame dengan OHLCV data
    """
    if not ticker.endswith('.JK'):
        ticker = f"{ticker}.JK"

    conn = get_connection()

    query = 'SELECT * FROM daily_prices WHERE ticker = ?'
    params = [ticker]

    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)

    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)

    query += ' ORDER BY date'

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])

    return df


def get_all_tickers() -> List[str]:
    """Get list of all tickers in database"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT ticker FROM daily_prices')
    tickers = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tickers


def get_database_status() -> Dict:
    """Get database status info"""
    conn = get_connection()
    cursor = conn.cursor()

    # Count stocks
    cursor.execute('SELECT COUNT(DISTINCT ticker) FROM daily_prices')
    stock_count = cursor.fetchone()[0]

    # Count total rows
    cursor.execute('SELECT COUNT(*) FROM daily_prices')
    row_count = cursor.fetchone()[0]

    # Date range
    cursor.execute('SELECT MIN(date), MAX(date) FROM daily_prices')
    date_range = cursor.fetchone()

    # Last update
    cursor.execute('SELECT value FROM metadata WHERE key = "last_update"')
    result = cursor.fetchone()
    last_update = result[0] if result else None

    # Database size
    db_size = os.path.getsize(DB_PATH) if DB_PATH.exists() else 0

    conn.close()

    return {
        'stock_count': stock_count,
        'row_count': row_count,
        'date_range': date_range,
        'last_update': last_update,
        'db_size': db_size,
        'db_path': str(DB_PATH)
    }


def export_to_csv(ticker: str = None, output_dir: str = None):
    """Export data to CSV"""
    if output_dir is None:
        output_dir = DB_PATH.parent / "csv_export"

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if ticker:
        # Export single ticker
        if not ticker.endswith('.JK'):
            ticker = f"{ticker}.JK"

        df = get_stock_data(ticker)
        if not df.empty:
            filename = output_dir / f"{ticker.replace('.JK', '')}.csv"
            df.to_csv(filename, index=False)
            print(f"{Colors.GREEN}✅ Exported: {filename}{Colors.ENDC}")
        else:
            print(f"{Colors.YELLOW}No data for {ticker}{Colors.ENDC}")
    else:
        # Export all
        tickers = get_all_tickers()
        print(f"Exporting {len(tickers)} saham ke CSV...")

        for t in tickers:
            df = get_stock_data(t)
            if not df.empty:
                filename = output_dir / f"{t.replace('.JK', '')}.csv"
                df.to_csv(filename, index=False)

        print(f"{Colors.GREEN}✅ Exported {len(tickers)} files to {output_dir}{Colors.ENDC}")


def print_status():
    """Print database status"""
    if not DB_PATH.exists():
        print(f"{Colors.YELLOW}Database belum dibuat. Jalankan --download-all terlebih dahulu.{Colors.ENDC}")
        return

    status = get_database_status()

    print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}📊 DATABASE STATUS{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"Database: {status['db_path']}")
    print(f"Size: {status['db_size'] / 1024 / 1024:.2f} MB")
    print(f"Total saham: {status['stock_count']}")
    print(f"Total records: {status['row_count']:,}")
    if status['date_range'][0]:
        print(f"Date range: {status['date_range'][0]} to {status['date_range'][1]}")
    if status['last_update']:
        print(f"Last update: {status['last_update']}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")


def main():
    parser = argparse.ArgumentParser(description="GemaScreener Data Manager")

    parser.add_argument('--download-all', action='store_true',
                        help='Download semua data historis')
    parser.add_argument('--period', type=str, default='3y',
                        choices=['3m', '6m', '1y', '2y', '3y', '5y'],
                        help='Periode data (default: 3y)')
    parser.add_argument('--update', action='store_true',
                        help='Update data dengan data terbaru')
    parser.add_argument('--status', action='store_true',
                        help='Tampilkan status database')
    parser.add_argument('--export-csv', type=str, nargs='?', const='ALL',
                        help='Export ke CSV (ticker atau ALL)')
    parser.add_argument('--init', action='store_true',
                        help='Initialize database')

    args = parser.parse_args()

    if args.init:
        init_database()
    elif args.download_all:
        download_all_stocks(period=args.period)
    elif args.update:
        update_data()
    elif args.status:
        print_status()
    elif args.export_csv:
        if args.export_csv == 'ALL':
            export_to_csv()
        else:
            export_to_csv(args.export_csv)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
