Place your CSV files here:

REQUIRED:
  m5.csv   — 5-minute candles

OPTIONAL (but recommended):
  m1.csv   — 1-minute candles (for deeper M1 sub-candle analysis in Door 2/5)
  h1.csv   — 1-hour candles  (for HTF context in Door 1 pre-session)
  h4.csv   — 4-hour candles  (for HTF context in Door 1 pre-session)

NOTE on H1/H4:
  If h1.csv / h4.csv are absent, main.py aggregates H1 and H4 from m5.csv
  automatically (data_loader.aggregate_to_hours). No download needed.

CURRENT DATASET (this repo):
  Source   : Binance spot BTCUSDT 1m/5m (data.binance.vision)
  Timezone : IST (UTC+5:30) — timestamps are local Indian wall-clock time.
             The Binance UTC open_time was shifted +5:30 when building these.
  Range    : 2025-06-16 11:20:00 -> 2026-05-31 11:15:00 (IST)
  m1.csv was verified to aggregate EXACTLY to m5.csv (0 mismatches / 500 sampled).
  To rebuild m1.csv: download Binance 1m monthly zips, shift UTC->IST, filter
  to the m5 range, write timestamp,open,high,low,close,volume.

CSV FORMAT (any of these column names work):
  timestamp,open,high,low,close,volume
  time,open,high,low,close,vol
  date,open,high,low,close

BINANCE EXAMPLE:
  Download from: https://data.binance.vision/
  Symbol: BTCUSDT, Interval: 5m
  Rename the file to m5.csv

TIMESTAMP FORMATS SUPPORTED:
  2025-09-01 09:00:00
  2025-09-01T09:00:00
  1725177600000  (millisecond unix — pandas handles this)
