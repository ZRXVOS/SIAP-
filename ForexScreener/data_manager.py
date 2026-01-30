"""
ForexScreener Data Manager
Download dan manage data forex dari Yahoo Finance
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "forex_data.db")

def ensure_data_dir():
    """Pastikan folder data ada"""
    data_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

def download_forex_data(pairs: list = None, period: str = "3y"):
    """Download data forex dari Yahoo Finance"""
    import yfinance as yf
    from config import FOREX_PAIRS, DEFAULT_PAIRS

    if pairs is None:
        pairs = DEFAULT_PAIRS

    ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)

    print(f"\nDownloading {len(pairs)} forex pairs (period: {period})...")
    print("=" * 50)

    success = 0
    failed = 0

    for pair_name in pairs:
        if pair_name not in FOREX_PAIRS:
            print(f"  [{pair_name}] SKIP - tidak dikenal")
            continue

        pair_info = FOREX_PAIRS[pair_name]
        yahoo_ticker = pair_info["yahoo"]

        try:
            print(f"  [{pair_name}] Downloading {yahoo_ticker}...", end=" ")
            ticker = yf.Ticker(yahoo_ticker)
            df = ticker.history(period=period)

            if df is not None and len(df) > 0:
                # Reset index, rename columns
                df = df.reset_index()
                df = df.rename(columns={
                    'Date': 'date',
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                })

                # Keep only needed columns
                df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

                # Save to SQLite
                df.to_sql(pair_name, conn, if_exists='replace', index=False)
                print(f"OK ({len(df)} days)")
                success += 1
            else:
                print(f"EMPTY")
                failed += 1

        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1

    conn.close()

    print(f"\n{'=' * 50}")
    print(f"Success: {success}, Failed: {failed}")
    print(f"Database: {DB_PATH}")
    return success > 0

def get_forex_data(pair_name: str, start_date: str = None, end_date: str = None):
    """Get data forex dari database"""
    if not os.path.exists(DB_PATH):
        return None

    conn = sqlite3.connect(DB_PATH)
    try:
        query = f"SELECT * FROM '{pair_name}' ORDER BY date"
        df = pd.read_sql_query(query, conn)
        df['date'] = pd.to_datetime(df['date'])

        if start_date:
            df = df[df['date'] >= start_date]
        if end_date:
            df = df[df['date'] <= end_date]

        return df
    except:
        return None
    finally:
        conn.close()

def get_all_pairs():
    """Get semua pairs yang ada di database"""
    if not os.path.exists(DB_PATH):
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    pairs = [t[0] for t in cursor.fetchall()]
    conn.close()
    return pairs

def get_database_status():
    """Get status database"""
    if not os.path.exists(DB_PATH):
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    status = {}
    for (table_name,) in tables:
        cursor.execute(f"SELECT COUNT(*), MIN(date), MAX(date) FROM '{table_name}'")
        count, min_date, max_date = cursor.fetchone()
        status[table_name] = {
            'rows': count,
            'start': min_date,
            'end': max_date
        }

    conn.close()
    return status

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Forex Data Manager")
    parser.add_argument("--download", action="store_true", help="Download forex data")
    parser.add_argument("--pairs", type=str, default=None, help="Comma-separated pairs (e.g., XAUUSD,EURUSD)")
    parser.add_argument("--period", type=str, default="3y", help="Period: 1y, 2y, 3y, 5y")
    parser.add_argument("--status", action="store_true", help="Show database status")

    args = parser.parse_args()

    if args.download:
        pairs = args.pairs.split(",") if args.pairs else None
        download_forex_data(pairs, args.period)
    elif args.status:
        status = get_database_status()
        if status:
            print(f"\nDatabase: {DB_PATH}")
            print(f"{'=' * 50}")
            for pair, info in status.items():
                print(f"  {pair}: {info['rows']} days ({info['start']} to {info['end']})")
        else:
            print("Database tidak ditemukan. Jalankan: python data_manager.py --download")
    else:
        parser.print_help()
