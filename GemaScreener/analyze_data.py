"""
GemaScreener Data Analyzer
Analisis data 3 tahun untuk menemukan parameter optimal Rule 4, 5, 6, 7
Jalankan: python analyze_data.py
Output: analysis_result.txt
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# Configuration
DB_PATH = "data/gema_screener.db"
OUTPUT_FILE = "analysis_result.txt"

def log(msg, file=None):
    """Print and write to file"""
    print(msg)
    if file:
        file.write(msg + "\n")

def get_stock_data(conn, ticker):
    """Get stock data from database"""
    query = f"SELECT * FROM '{ticker}' ORDER BY date"
    try:
        df = pd.read_sql_query(query, conn)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except:
        return None

def calculate_indicators(df):
    """Calculate all indicators needed for analysis"""
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']

    # RSI(2)
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=2, min_periods=2).mean()
    avg_loss = loss.rolling(window=2, min_periods=2).mean()
    rs = avg_gain / avg_loss
    df['rsi_2'] = 100 - (100 / (1 + rs))

    # RSI(14)
    avg_gain_14 = gain.rolling(window=14, min_periods=14).mean()
    avg_loss_14 = loss.rolling(window=14, min_periods=14).mean()
    rs_14 = avg_gain_14 / avg_loss_14
    df['rsi_14'] = 100 - (100 / (1 + rs_14))

    # SMAs
    df['sma_5'] = close.rolling(window=5).mean()
    df['sma_10'] = close.rolling(window=10).mean()
    df['sma_20'] = close.rolling(window=20).mean()
    df['sma_50'] = close.rolling(window=50).mean()
    df['sma_200'] = close.rolling(window=200).mean()

    # Bollinger Bands
    df['bb_middle'] = df['sma_20']
    std_20 = close.rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (2 * std_20)
    df['bb_lower'] = df['bb_middle'] - (2 * std_20)
    df['percent_b'] = (close - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

    # Volume
    df['vol_sma_20'] = volume.rolling(window=20).mean()
    df['vol_ratio'] = volume / df['vol_sma_20']

    # High 20
    df['high_20'] = high.shift(1).rolling(window=20).max()

    # ATR
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(window=14).mean()

    # ADX
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    atr_14 = df['atr_14']
    plus_di = 100 * (plus_dm.rolling(window=14).mean() / atr_14)
    minus_di = 100 * (minus_dm.rolling(window=14).mean() / atr_14)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df['adx'] = dx.rolling(window=14).mean()

    return df

def simulate_rule4(df, rsi_entry, exit_type, disaster_stop, max_hold):
    """
    Simulate Rule 4: RSI-2 Mean Reversion
    exit_type: 'sma5' or 'sma5_rsi60'
    """
    trades = []
    position = None

    for i in range(200, len(df)):
        row = df.iloc[i]

        # Check exit
        if position:
            days_held = i - position['entry_idx']
            entry_price = position['entry_price']

            # Exit conditions
            exit_reason = None
            exit_price = row['close']

            if exit_type == 'sma5' and row['close'] > row['sma_5']:
                exit_reason = 'MEAN_REVERSION'
            elif exit_type == 'sma5_rsi60' and row['close'] > row['sma_5'] and row['rsi_2'] > 60:
                exit_reason = 'MEAN_REVERSION'
            elif row['close'] <= entry_price * (1 - disaster_stop):
                exit_reason = 'DISASTER_STOP'
            elif days_held >= max_hold:
                exit_reason = 'TIME_EXIT'

            if exit_reason:
                pnl_pct = (exit_price / entry_price - 1) * 100
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                    'days_held': days_held
                })
                position = None

        # Check entry
        if position is None:
            if (row['close'] > row['sma_200'] and
                row['rsi_2'] < rsi_entry and
                row['close'] * row['volume'] > 500_000_000):
                position = {
                    'entry_idx': i,
                    'entry_price': row['close']
                }

    return trades

def simulate_rule5(df, tp_pct, use_sl, sl_pct, use_trailing, max_hold):
    """
    Simulate Rule 5: Dual MA Crossover
    """
    trades = []
    position = None
    highest_price = 0

    for i in range(52, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        # Check exit
        if position:
            days_held = i - position['entry_idx']
            entry_price = position['entry_price']
            highest_price = max(highest_price, row['high'])

            exit_reason = None
            exit_price = row['close']

            # Take Profit
            if row['close'] >= entry_price * (1 + tp_pct):
                exit_reason = 'TAKE_PROFIT'
            # Stop Loss
            elif use_sl and row['close'] <= entry_price * (1 - sl_pct):
                exit_reason = 'STOP_LOSS'
            # Trailing Stop
            elif use_trailing and row['close'] < highest_price * 0.95:
                exit_reason = 'TRAILING_STOP'
            # Breakdown
            elif row['close'] < row['sma_50']:
                exit_reason = 'BREAKDOWN'
            # Time Exit
            elif days_held >= max_hold:
                exit_reason = 'TIME_EXIT'

            if exit_reason:
                pnl_pct = (exit_price / entry_price - 1) * 100
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                    'days_held': days_held
                })
                position = None
                highest_price = 0

        # Check entry (Golden Cross)
        if position is None:
            golden_cross = prev['sma_20'] <= prev['sma_50'] and row['sma_20'] > row['sma_50']
            recent_cross = False
            if row['sma_20'] > row['sma_50']:
                for j in range(1, min(4, i)):
                    if df.iloc[i-j]['sma_20'] <= df.iloc[i-j]['sma_50']:
                        recent_cross = True
                        break

            if ((golden_cross or recent_cross) and
                row['close'] > row['sma_20'] and
                row['vol_ratio'] >= 1.5 and
                row['close'] * row['volume'] > 500_000_000):
                position = {
                    'entry_idx': i,
                    'entry_price': row['close']
                }
                highest_price = row['close']

    return trades

def simulate_rule6(df, tp_pct, disaster_stop, max_hold):
    """
    Simulate Rule 6: Bollinger Band Mean Reversion
    """
    trades = []
    position = None

    for i in range(200, len(df)):
        row = df.iloc[i]

        # Check exit
        if position:
            days_held = i - position['entry_idx']
            entry_price = position['entry_price']

            exit_reason = None
            exit_price = row['close']

            # Take Profit
            if row['close'] >= entry_price * (1 + tp_pct):
                exit_reason = 'TAKE_PROFIT'
            # Mean Reversion
            elif row['close'] > row['bb_middle']:
                exit_reason = 'MEAN_REVERSION'
            # Disaster Stop
            elif disaster_stop > 0 and row['close'] <= entry_price * (1 - disaster_stop):
                exit_reason = 'DISASTER_STOP'
            # Time Exit
            elif days_held >= max_hold:
                exit_reason = 'TIME_EXIT'

            if exit_reason:
                pnl_pct = (exit_price / entry_price - 1) * 100
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                    'days_held': days_held
                })
                position = None

        # Check entry
        if position is None:
            if (row['close'] < row['bb_lower'] and
                row['percent_b'] < 0 and
                row['rsi_14'] < 30 and
                row['close'] > row['sma_200'] and
                row['close'] * row['volume'] > 500_000_000):
                position = {
                    'entry_idx': i,
                    'entry_price': row['close']
                }

    return trades

def simulate_rule7(df, tp_pct, vol_ratio_min, breakout_pct_min, use_momentum_loss, max_hold):
    """
    Simulate Rule 7: Breakout with Volume
    """
    trades = []
    position = None

    for i in range(30, len(df)):
        row = df.iloc[i]

        # Check exit
        if position:
            days_held = i - position['entry_idx']
            entry_price = position['entry_price']
            breakout_level = position['breakout_level']

            exit_reason = None
            exit_price = row['close']

            # Support-based stop
            support_stop = breakout_level - row['atr_14'] if not pd.isna(row['atr_14']) else entry_price * 0.95

            # Take Profit
            if row['close'] >= entry_price * (1 + tp_pct):
                exit_reason = 'TAKE_PROFIT'
            # Support Stop Loss
            elif row['close'] <= support_stop:
                exit_reason = 'STOP_LOSS'
            # Momentum Loss
            elif use_momentum_loss and row['close'] < row['sma_10']:
                exit_reason = 'MOMENTUM_LOSS'
            # Time Exit
            elif days_held >= max_hold:
                exit_reason = 'TIME_EXIT'

            if exit_reason:
                pnl_pct = (exit_price / entry_price - 1) * 100
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                    'days_held': days_held
                })
                position = None

        # Check entry
        if position is None:
            if pd.isna(row['high_20']) or pd.isna(row['vol_ratio']):
                continue

            breakout_pct = (row['close'] - row['high_20']) / row['high_20'] * 100
            is_bullish = row['close'] > row['open']

            if (row['close'] > row['high_20'] and
                row['vol_ratio'] >= vol_ratio_min and
                breakout_pct >= breakout_pct_min and
                is_bullish and
                row['close'] * row['volume'] > 500_000_000):
                position = {
                    'entry_idx': i,
                    'entry_price': row['close'],
                    'breakout_level': row['high_20']
                }

    return trades

def analyze_trades(trades):
    """Analyze trade results"""
    if not trades:
        return None

    df = pd.DataFrame(trades)

    wins = df[df['pnl_pct'] > 0]
    losses = df[df['pnl_pct'] <= 0]

    total_pnl = df['pnl_pct'].sum()
    win_rate = len(wins) / len(df) * 100 if len(df) > 0 else 0

    gross_profit = wins['pnl_pct'].sum() if len(wins) > 0 else 0
    gross_loss = abs(losses['pnl_pct'].sum()) if len(losses) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    # Exit reason breakdown
    exit_breakdown = df.groupby('exit_reason')['pnl_pct'].agg(['count', 'sum', 'mean']).to_dict('index')

    return {
        'total_trades': len(df),
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'profit_factor': profit_factor,
        'avg_pnl': df['pnl_pct'].mean(),
        'avg_hold': df['days_held'].mean(),
        'exit_breakdown': exit_breakdown
    }

def main():
    print("=" * 60)
    print("GEMASCREENER DATA ANALYZER")
    print("=" * 60)

    # Check database
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database tidak ditemukan di {DB_PATH}")
        return

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all tables (tickers)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tickers = [t[0] for t in cursor.fetchall()]
    print(f"Found {len(tickers)} stocks in database")

    # Open output file
    with open(OUTPUT_FILE, 'w') as f:
        log("=" * 70, f)
        log("GEMASCREENER ANALYSIS RESULT", f)
        log(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", f)
        log(f"Stocks analyzed: {len(tickers)}", f)
        log("=" * 70, f)

        # Load all data
        all_data = {}
        print("\nLoading data...")
        for i, ticker in enumerate(tickers):
            if i % 50 == 0:
                print(f"  Loading {i}/{len(tickers)}...")
            df = get_stock_data(conn, ticker)
            if df is not None and len(df) > 200:
                df = calculate_indicators(df)
                all_data[ticker] = df

        print(f"Loaded {len(all_data)} stocks with sufficient data")
        log(f"\nStocks with sufficient data: {len(all_data)}", f)

        # ============================================================
        # RULE 4 ANALYSIS
        # ============================================================
        log("\n" + "=" * 70, f)
        log("RULE 4: RSI-2 MEAN REVERSION", f)
        log("=" * 70, f)

        rule4_results = []

        # Test different parameters
        for rsi_entry in [5, 10, 15]:
            for exit_type in ['sma5', 'sma5_rsi60']:
                for disaster_stop in [0.05, 0.08, 0.10, 0.15, 0.20]:
                    for max_hold in [5, 10, 15, 20]:
                        all_trades = []
                        for ticker, df in all_data.items():
                            trades = simulate_rule4(df, rsi_entry, exit_type, disaster_stop, max_hold)
                            all_trades.extend(trades)

                        if all_trades:
                            result = analyze_trades(all_trades)
                            if result:
                                result['params'] = {
                                    'rsi_entry': rsi_entry,
                                    'exit_type': exit_type,
                                    'disaster_stop': disaster_stop,
                                    'max_hold': max_hold
                                }
                                rule4_results.append(result)

        # Sort by profit factor
        rule4_results.sort(key=lambda x: x['profit_factor'], reverse=True)

        log("\nTOP 5 CONFIGURATIONS:", f)
        for i, r in enumerate(rule4_results[:5]):
            log(f"\n#{i+1}: PF={r['profit_factor']:.2f}, WR={r['win_rate']:.1f}%, PnL={r['total_pnl']:.1f}%", f)
            log(f"    Params: RSI<{r['params']['rsi_entry']}, Exit={r['params']['exit_type']}, " +
                f"Disaster={r['params']['disaster_stop']*100:.0f}%, MaxHold={r['params']['max_hold']}d", f)
            log(f"    Trades: {r['total_trades']}, Avg Hold: {r['avg_hold']:.1f}d", f)
            log(f"    Exit Breakdown:", f)
            for reason, stats in r['exit_breakdown'].items():
                log(f"      {reason}: {int(stats['count'])} trades, {stats['sum']:.1f}% total, {stats['mean']:.2f}% avg", f)

        # ============================================================
        # RULE 5 ANALYSIS
        # ============================================================
        log("\n" + "=" * 70, f)
        log("RULE 5: DUAL MA CROSSOVER", f)
        log("=" * 70, f)

        rule5_results = []

        for tp_pct in [0.08, 0.10, 0.15]:
            for use_sl in [True, False]:
                for sl_pct in [0.05, 0.08] if use_sl else [0]:
                    for use_trailing in [True, False]:
                        for max_hold in [10, 15, 20]:
                            all_trades = []
                            for ticker, df in all_data.items():
                                trades = simulate_rule5(df, tp_pct, use_sl, sl_pct, use_trailing, max_hold)
                                all_trades.extend(trades)

                            if all_trades:
                                result = analyze_trades(all_trades)
                                if result:
                                    result['params'] = {
                                        'tp_pct': tp_pct,
                                        'use_sl': use_sl,
                                        'sl_pct': sl_pct,
                                        'use_trailing': use_trailing,
                                        'max_hold': max_hold
                                    }
                                    rule5_results.append(result)

        rule5_results.sort(key=lambda x: x['profit_factor'], reverse=True)

        log("\nTOP 5 CONFIGURATIONS:", f)
        for i, r in enumerate(rule5_results[:5]):
            log(f"\n#{i+1}: PF={r['profit_factor']:.2f}, WR={r['win_rate']:.1f}%, PnL={r['total_pnl']:.1f}%", f)
            p = r['params']
            sl_str = f"SL={p['sl_pct']*100:.0f}%" if p['use_sl'] else "No SL"
            trail_str = "Trailing" if p['use_trailing'] else "No Trail"
            log(f"    Params: TP={p['tp_pct']*100:.0f}%, {sl_str}, {trail_str}, MaxHold={p['max_hold']}d", f)
            log(f"    Trades: {r['total_trades']}, Avg Hold: {r['avg_hold']:.1f}d", f)
            log(f"    Exit Breakdown:", f)
            for reason, stats in r['exit_breakdown'].items():
                log(f"      {reason}: {int(stats['count'])} trades, {stats['sum']:.1f}% total, {stats['mean']:.2f}% avg", f)

        # ============================================================
        # RULE 6 ANALYSIS
        # ============================================================
        log("\n" + "=" * 70, f)
        log("RULE 6: BOLLINGER BAND MEAN REVERSION", f)
        log("=" * 70, f)

        rule6_results = []

        for tp_pct in [0.08, 0.10, 0.15]:
            for disaster_stop in [0, 0.08, 0.10, 0.15, 0.20]:
                for max_hold in [10, 15, 20]:
                    all_trades = []
                    for ticker, df in all_data.items():
                        trades = simulate_rule6(df, tp_pct, disaster_stop, max_hold)
                        all_trades.extend(trades)

                    if all_trades:
                        result = analyze_trades(all_trades)
                        if result:
                            result['params'] = {
                                'tp_pct': tp_pct,
                                'disaster_stop': disaster_stop,
                                'max_hold': max_hold
                            }
                            rule6_results.append(result)

        rule6_results.sort(key=lambda x: x['profit_factor'], reverse=True)

        log("\nTOP 5 CONFIGURATIONS:", f)
        for i, r in enumerate(rule6_results[:5]):
            log(f"\n#{i+1}: PF={r['profit_factor']:.2f}, WR={r['win_rate']:.1f}%, PnL={r['total_pnl']:.1f}%", f)
            p = r['params']
            ds_str = f"Disaster={p['disaster_stop']*100:.0f}%" if p['disaster_stop'] > 0 else "No Disaster"
            log(f"    Params: TP={p['tp_pct']*100:.0f}%, {ds_str}, MaxHold={p['max_hold']}d", f)
            log(f"    Trades: {r['total_trades']}, Avg Hold: {r['avg_hold']:.1f}d", f)
            log(f"    Exit Breakdown:", f)
            for reason, stats in r['exit_breakdown'].items():
                log(f"      {reason}: {int(stats['count'])} trades, {stats['sum']:.1f}% total, {stats['mean']:.2f}% avg", f)

        # ============================================================
        # RULE 7 ANALYSIS
        # ============================================================
        log("\n" + "=" * 70, f)
        log("RULE 7: BREAKOUT WITH VOLUME", f)
        log("=" * 70, f)

        rule7_results = []

        for tp_pct in [0.10, 0.15, 0.20]:
            for vol_ratio_min in [1.5, 2.0]:
                for breakout_pct_min in [1.0, 2.0]:
                    for use_momentum_loss in [True, False]:
                        for max_hold in [10, 15, 20]:
                            all_trades = []
                            for ticker, df in all_data.items():
                                trades = simulate_rule7(df, tp_pct, vol_ratio_min, breakout_pct_min, use_momentum_loss, max_hold)
                                all_trades.extend(trades)

                            if all_trades:
                                result = analyze_trades(all_trades)
                                if result:
                                    result['params'] = {
                                        'tp_pct': tp_pct,
                                        'vol_ratio_min': vol_ratio_min,
                                        'breakout_pct_min': breakout_pct_min,
                                        'use_momentum_loss': use_momentum_loss,
                                        'max_hold': max_hold
                                    }
                                    rule7_results.append(result)

        rule7_results.sort(key=lambda x: x['profit_factor'], reverse=True)

        log("\nTOP 5 CONFIGURATIONS:", f)
        for i, r in enumerate(rule7_results[:5]):
            log(f"\n#{i+1}: PF={r['profit_factor']:.2f}, WR={r['win_rate']:.1f}%, PnL={r['total_pnl']:.1f}%", f)
            p = r['params']
            mom_str = "MomLoss" if p['use_momentum_loss'] else "No MomLoss"
            log(f"    Params: TP={p['tp_pct']*100:.0f}%, Vol>{p['vol_ratio_min']}x, Breakout>{p['breakout_pct_min']}%, {mom_str}, MaxHold={p['max_hold']}d", f)
            log(f"    Trades: {r['total_trades']}, Avg Hold: {r['avg_hold']:.1f}d", f)
            log(f"    Exit Breakdown:", f)
            for reason, stats in r['exit_breakdown'].items():
                log(f"      {reason}: {int(stats['count'])} trades, {stats['sum']:.1f}% total, {stats['mean']:.2f}% avg", f)

        # ============================================================
        # SUMMARY
        # ============================================================
        log("\n" + "=" * 70, f)
        log("RECOMMENDED OPTIMAL PARAMETERS", f)
        log("=" * 70, f)

        if rule4_results:
            best4 = rule4_results[0]
            log(f"\nRULE 4: RSI<{best4['params']['rsi_entry']}, Exit={best4['params']['exit_type']}, " +
                f"Disaster={best4['params']['disaster_stop']*100:.0f}%, MaxHold={best4['params']['max_hold']}d", f)
            log(f"  -> PF={best4['profit_factor']:.2f}, WR={best4['win_rate']:.1f}%", f)

        if rule5_results:
            best5 = rule5_results[0]
            p = best5['params']
            sl_str = f"SL={p['sl_pct']*100:.0f}%" if p['use_sl'] else "No SL"
            trail_str = "Trailing" if p['use_trailing'] else "No Trail"
            log(f"\nRULE 5: TP={p['tp_pct']*100:.0f}%, {sl_str}, {trail_str}, MaxHold={p['max_hold']}d", f)
            log(f"  -> PF={best5['profit_factor']:.2f}, WR={best5['win_rate']:.1f}%", f)

        if rule6_results:
            best6 = rule6_results[0]
            p = best6['params']
            ds_str = f"Disaster={p['disaster_stop']*100:.0f}%" if p['disaster_stop'] > 0 else "No Disaster"
            log(f"\nRULE 6: TP={p['tp_pct']*100:.0f}%, {ds_str}, MaxHold={p['max_hold']}d", f)
            log(f"  -> PF={best6['profit_factor']:.2f}, WR={best6['win_rate']:.1f}%", f)

        if rule7_results:
            best7 = rule7_results[0]
            p = best7['params']
            mom_str = "MomLoss" if p['use_momentum_loss'] else "No MomLoss"
            log(f"\nRULE 7: TP={p['tp_pct']*100:.0f}%, Vol>{p['vol_ratio_min']}x, Breakout>{p['breakout_pct_min']}%, {mom_str}, MaxHold={p['max_hold']}d", f)
            log(f"  -> PF={best7['profit_factor']:.2f}, WR={best7['win_rate']:.1f}%", f)

        log("\n" + "=" * 70, f)
        log("Analysis complete!", f)

    conn.close()
    print(f"\nResults saved to: {OUTPUT_FILE}")
    print("Please share the contents of this file.")

if __name__ == "__main__":
    main()
