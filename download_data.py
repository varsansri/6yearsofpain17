"""
Download BTCUSDT candle data from Binance public API.
Uses only Python stdlib — no pip needed.

Usage:
  python download_data.py                        # last 30 days of M5
  python download_data.py --days 7               # last 7 days
  python download_data.py --start 2025-06-17     # from specific date to today
  python download_data.py --m1                   # also download M1 data
"""

import urllib.request
import json
import csv
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

SYMBOL   = "BTCUSDT"
BASE_URL = "https://api.binance.com/api/v3/klines"
LIMIT    = 1000  # max per request


def fetch(interval: str, start_ms: int, end_ms: int) -> list:
    url = (f"{BASE_URL}?symbol={SYMBOL}&interval={interval}"
           f"&startTime={start_ms}&endTime={end_ms}&limit={LIMIT}")
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())


def download(interval: str, days: int, filename: str):
    Path("data").mkdir(exist_ok=True)
    out = Path("data") / filename

    now_ms  = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = now_ms - days * 24 * 60 * 60 * 1000

    all_candles = []
    cursor = start_ms
    print(f"\nDownloading {interval} data ({days} days)...")

    while cursor < now_ms:
        try:
            batch = fetch(interval, cursor, now_ms)
        except Exception as e:
            print(f"  Error fetching batch: {e}. Retrying in 5s...")
            time.sleep(5)
            continue

        if not batch:
            break

        all_candles.extend(batch)
        cursor = batch[-1][0] + 1  # next batch starts after last candle

        first = datetime.fromtimestamp(batch[0][0] / 1000)
        last  = datetime.fromtimestamp(batch[-1][0] / 1000)
        print(f"  {len(all_candles)} candles... {first.strftime('%Y-%m-%d')} → {last.strftime('%Y-%m-%d %H:%M')}")

        if len(batch) < LIMIT:
            break
        time.sleep(0.3)

    with open(out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for c in all_candles:
            ts = datetime.fromtimestamp(c[0] / 1000).strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([ts, c[1], c[2], c[3], c[4], c[5]])

    print(f"  Saved {len(all_candles)} candles → {out}")
    return len(all_candles)


def main():
    args = sys.argv[1:]
    days = 30
    get_m1 = "--m1" in args

    if "--start" in args:
        i = args.index("--start")
        start_date = datetime.strptime(args[i + 1], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days = (now - start_date).days + 1
        print(f"Start date: {args[i+1]}  ({days} days of data)")
    elif "--days" in args:
        i = args.index("--days")
        days = int(args[i + 1])

    download("5m", days, "m5.csv")
    if get_m1:
        download("1m", days, "m1.csv")
    print("\nDone. Run: python main.py")


if __name__ == "__main__":
    main()
