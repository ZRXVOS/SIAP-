#!/usr/bin/env python3
"""
GemaScreener Scheduler
Advanced scheduler dengan fitur tambahan

Features:
- Schedule pada waktu tertentu (market hours)
- Multiple interval options
- Logging ke file
- Error recovery
"""

import schedule
import time
import sys
import logging
from datetime import datetime, time as dt_time
from typing import List, Callable

from config import SCHEDULE_INTERVAL, Colors
from main import run_screening
from telegram_alert import send_error_alert, send_telegram_message


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gema_screener.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def is_market_hours() -> bool:
    """
    Cek apakah sekarang jam market IHSG
    Market IHSG: 09:00 - 16:00 WIB (Senin-Jumat)
    """
    now = datetime.now()

    # Cek hari (0 = Senin, 6 = Minggu)
    if now.weekday() >= 5:  # Weekend
        return False

    # Cek jam
    market_open = dt_time(9, 0)
    market_close = dt_time(16, 0)
    current_time = now.time()

    return market_open <= current_time <= market_close


def scheduled_job(rules: List[int] = [1, 2, 3], use_telegram: bool = True,
                  only_market_hours: bool = True):
    """
    Job yang akan dijalankan secara scheduled

    Args:
        rules: List rumus yang dijalankan
        use_telegram: Kirim ke Telegram
        only_market_hours: Hanya jalankan saat market buka
    """
    # Cek market hours jika diaktifkan
    if only_market_hours and not is_market_hours():
        logger.info("Skipping - Outside market hours")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Starting scheduled screening at {timestamp}")

    try:
        run_screening(rules, use_telegram, show_progress=True)
        logger.info("Screening completed successfully")

    except Exception as e:
        error_msg = f"Screening error: {str(e)}"
        logger.error(error_msg)

        if use_telegram:
            send_error_alert(error_msg)


def run_scheduler(rules: List[int] = [1, 2, 3],
                  interval_minutes: int = 5,
                  use_telegram: bool = True,
                  only_market_hours: bool = True):
    """
    Jalankan scheduler

    Args:
        rules: List rumus
        interval_minutes: Interval dalam menit
        use_telegram: Kirim ke Telegram
        only_market_hours: Hanya saat market buka
    """
    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}  GEMA SCREENER - SCHEDULER MODE{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.ENDC}")

    print(f"\n{Colors.CYAN}Configuration:{Colors.ENDC}")
    print(f"  - Rules: {rules}")
    print(f"  - Interval: {interval_minutes} minutes")
    print(f"  - Telegram: {'Yes' if use_telegram else 'No'}")
    print(f"  - Market hours only: {'Yes' if only_market_hours else 'No'}")

    if only_market_hours:
        print(f"\n{Colors.YELLOW}⏰ Market Hours: 09:00 - 16:00 WIB (Mon-Fri){Colors.ENDC}")

    print(f"\n{Colors.YELLOW}Press Ctrl+C to stop{Colors.ENDC}\n")

    # Send start notification
    if use_telegram:
        msg = f"🟢 GemaScreener Scheduler Started\n"
        msg += f"Interval: {interval_minutes} min\n"
        msg += f"Rules: {rules}\n"
        msg += f"Market hours only: {'Yes' if only_market_hours else 'No'}"
        send_telegram_message(msg)

    # Schedule job
    schedule.every(interval_minutes).minutes.do(
        scheduled_job,
        rules=rules,
        use_telegram=use_telegram,
        only_market_hours=only_market_hours
    )

    # Run immediately first
    logger.info("Running initial screening...")
    scheduled_job(rules, use_telegram, only_market_hours)

    # Main loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Scheduler stopped by user{Colors.ENDC}")
        logger.info("Scheduler stopped by user")

        if use_telegram:
            send_telegram_message("🔴 GemaScreener Scheduler Stopped")


def run_at_specific_times(rules: List[int] = [1, 2, 3],
                          times: List[str] = ["09:15", "12:00", "15:30"],
                          use_telegram: bool = True):
    """
    Jalankan screening pada waktu tertentu

    Args:
        rules: List rumus
        times: List waktu dalam format "HH:MM"
        use_telegram: Kirim ke Telegram
    """
    print(f"\n{Colors.BOLD}Scheduled times: {times}{Colors.ENDC}")

    for t in times:
        schedule.every().day.at(t).do(
            scheduled_job,
            rules=rules,
            use_telegram=use_telegram,
            only_market_hours=False
        )

    if use_telegram:
        msg = f"🟢 GemaScreener Scheduled\nTimes: {', '.join(times)}"
        send_telegram_message(msg)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Scheduler stopped{Colors.ENDC}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GemaScreener Scheduler")

    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=5,
        help='Interval dalam menit (default: 5)'
    )

    parser.add_argument(
        '--rules', '-r',
        type=int,
        nargs='+',
        default=[1, 2, 3],
        help='Rules yang dijalankan (default: 1 2 3)'
    )

    parser.add_argument(
        '--no-telegram',
        action='store_true',
        help='Tanpa Telegram'
    )

    parser.add_argument(
        '--all-hours',
        action='store_true',
        help='Jalankan di luar market hours juga'
    )

    parser.add_argument(
        '--times',
        nargs='+',
        help='Jalankan pada waktu tertentu (contoh: 09:15 12:00 15:30)'
    )

    args = parser.parse_args()

    if args.times:
        run_at_specific_times(
            rules=args.rules,
            times=args.times,
            use_telegram=not args.no_telegram
        )
    else:
        run_scheduler(
            rules=args.rules,
            interval_minutes=args.interval,
            use_telegram=not args.no_telegram,
            only_market_hours=not args.all_hours
        )
