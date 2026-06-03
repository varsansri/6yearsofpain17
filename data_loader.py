import csv
from datetime import datetime, timedelta
from pathlib import Path


def _parse_ts(val: str):
    val = val.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            pass
    try:
        ts = int(val)
        return datetime.utcfromtimestamp(ts / 1000 if ts > 1e10 else ts)
    except ValueError:
        pass
    raise ValueError(f"Cannot parse timestamp: {val}")


def _read_csv(path: str) -> list:
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        headers = [h.strip().lower().replace(" ", "_") for h in reader.fieldnames]

        ts_col = next((h for h in headers if "time" in h or "date" in h or h == "ts"), None)
        if ts_col is None:
            ts_col = headers[0]

        for raw in reader:
            row = {k.strip().lower().replace(" ", "_"): v for k, v in raw.items()}
            if ts_col != "timestamp":
                row["timestamp"] = row.pop(ts_col, row.get(ts_col))
            row["timestamp"] = _parse_ts(row["timestamp"])
            row["open"]   = float(row["open"])
            row["high"]   = float(row["high"])
            row["low"]    = float(row["low"])
            row["close"]  = float(row["close"])
            row["volume"] = float(row.get("volume", row.get("vol", 0)) or 0)
            rows.append(row)

    rows.sort(key=lambda r: r["timestamp"])
    return rows


def load_data(data_dir: str = "data"):
    p = Path(data_dir)
    m5_path = p / "m5.csv"

    if not m5_path.exists():
        raise FileNotFoundError(
            f"M5 data not found at {m5_path}\n"
            "Place your M5 CSV at data/m5.csv\n"
            "Format: timestamp,open,high,low,close,volume"
        )

    m5 = _read_csv(str(m5_path))
    m1 = _read_csv(str(p / "m1.csv")) if (p / "m1.csv").exists() else None
    h1 = _read_csv(str(p / "h1.csv")) if (p / "h1.csv").exists() else None
    h4 = _read_csv(str(p / "h4.csv")) if (p / "h4.csv").exists() else None

    print(f"Loaded M5 : {len(m5)} candles  ({m5[0]['timestamp']} → {m5[-1]['timestamp']})")
    if m1: print(f"Loaded M1 : {len(m1)} candles")
    if h1: print(f"Loaded H1 : {len(h1)} candles")
    if h4: print(f"Loaded H4 : {len(h4)} candles")

    return m5, m1, h1, h4


# ── NEW: M15 aggregation from M5 (no CSV needed) ─────────────────────────────

def aggregate_to_m15(m5_data: list) -> list:
    """Group M5 candles into M15 candles (3 M5 = 1 M15)."""
    if not m5_data:
        return []
    result = []
    bucket = None
    for c in m5_data:
        ts = c["timestamp"]
        # Floor to nearest 15-minute boundary
        bucket_ts = ts.replace(
            minute=(ts.minute // 15) * 15,
            second=0, microsecond=0
        )
        if bucket is None or bucket["timestamp"] != bucket_ts:
            if bucket:
                result.append(bucket)
            bucket = {
                "timestamp": bucket_ts,
                "open":   c["open"],
                "high":   c["high"],
                "low":    c["low"],
                "close":  c["close"],
                "volume": c["volume"],
            }
        else:
            bucket["high"]   = max(bucket["high"], c["high"])
            bucket["low"]    = min(bucket["low"],  c["low"])
            bucket["close"]  = c["close"]
            bucket["volume"] += c["volume"]
    if bucket:
        result.append(bucket)
    return result


def aggregate_to_hours(m5_data: list, hours: int) -> list:
    """Group M5 candles into N-hour candles (e.g. hours=1 -> H1, hours=4 -> H4).
    Buckets align to the hour-of-day grid so H4 boundaries are 00:00, 04:00, ...
    Note: m5 timestamps are IST (UTC+5:30); buckets follow that same wall clock."""
    if not m5_data:
        return []
    span = hours * 3600
    result = []
    bucket = None
    for c in m5_data:
        ts = c["timestamp"]
        # Floor to the N-hour boundary on the calendar day
        floored_hour = (ts.hour // hours) * hours
        bucket_ts = ts.replace(hour=floored_hour, minute=0, second=0, microsecond=0)
        if bucket is None or bucket["timestamp"] != bucket_ts:
            if bucket:
                result.append(bucket)
            bucket = {
                "timestamp": bucket_ts,
                "open":   c["open"],
                "high":   c["high"],
                "low":    c["low"],
                "close":  c["close"],
                "volume": c["volume"],
            }
        else:
            bucket["high"]   = max(bucket["high"], c["high"])
            bucket["low"]    = min(bucket["low"],  c["low"])
            bucket["close"]  = c["close"]
            bucket["volume"] += c["volume"]
    if bucket:
        result.append(bucket)
    return result


# ── NEW: Dedicated context getters for each agent ────────────────────────────

def get_h1_context(h1_data: list, h4_data: list, current_ts, n: int = 8) -> list:
    """Return last n H1 candles before current_ts for H1 Commander agent."""
    if isinstance(current_ts, str):
        current_ts = _parse_ts(current_ts)
    h1_candles = []
    if h1_data:
        h1_candles = [candle_to_dict(r) for r in h1_data
                      if r["timestamp"] <= current_ts][-n:]
    h4_candles = []
    if h4_data:
        h4_candles = [candle_to_dict(r) for r in h4_data
                      if r["timestamp"] <= current_ts][-5:]
    return h4_candles, h1_candles


def get_m15_context(m15_data: list, current_ts, n: int = 12) -> list:
    """Return last n M15 candles before current_ts for M15 Scout agent."""
    if isinstance(current_ts, str):
        current_ts = _parse_ts(current_ts)
    return [candle_to_dict(r) for r in m15_data
            if r["timestamp"] <= current_ts][-n:]


# ── Existing helpers (untouched) ─────────────────────────────────────────────

def build_m1_index(m1_data: list) -> dict:
    """Bucket M1 candles by their parent M5 (5-min floor) timestamp — built once.
    Avoids an O(N) scan of all M1 rows for every M5 candle during the backtest."""
    index = {}
    if not m1_data:
        return index
    for c in m1_data:
        t = c["timestamp"]
        floor = t.replace(minute=(t.minute // 5) * 5, second=0, microsecond=0)
        index.setdefault(floor, []).append(c)
    for bucket in index.values():
        bucket.sort(key=lambda r: r["timestamp"])
    return index


def get_m1_for_m5(m1_data, m5_ts) -> list:
    """Return the M1 sub-candles inside one M5 window.
    `m1_data` may be either the raw list (linear scan) or a prebuilt index dict
    from build_m1_index() (O(1) lookup, preferred for backtests)."""
    if not m1_data:
        return []
    if isinstance(m5_ts, str):
        m5_ts = _parse_ts(m5_ts)
    if isinstance(m1_data, dict):
        floor = m5_ts.replace(minute=(m5_ts.minute // 5) * 5, second=0, microsecond=0)
        return [candle_to_dict(r) for r in m1_data.get(floor, [])]
    end = m5_ts + timedelta(minutes=5)
    return [r for r in m1_data if m5_ts <= r["timestamp"] < end]


def candle_to_dict(row: dict) -> dict:
    return {
        "timestamp": str(row["timestamp"]),
        "open":   row["open"],
        "high":   row["high"],
        "low":    row["low"],
        "close":  row["close"],
        "volume": row["volume"],
    }


# ── Order Flow / Footprint loaders ───────────────────────────────────────────

_OF_FLOAT = {"open","high","low","close","volume","quote_volume","buy_vol","sell_vol",
             "delta","cum_delta","delta_pct","avg_trade_size","max_trade",
             "large_vol_1btc","whale_vol_5btc","poc_price","poc_buy_vol","poc_sell_vol"}
_OF_INT   = {"trade_count","buy_trades","sell_trades","large_trades_1btc"}


def load_orderflow(data_dir: str = "data") -> list:
    """Load every data/orderflow_5m_*.csv into one timestamp-sorted list.
    Returns None if no order-flow file is present (layer stays disabled)."""
    files = sorted(Path(data_dir).glob("orderflow_5m_*.csv"))
    if not files:
        return None
    rows = []
    for fp in files:
        with open(fp, newline="") as f:
            for raw in csv.DictReader(f):
                row = {}
                for k, v in raw.items():
                    if k == "timestamp":
                        row[k] = _parse_ts(v)
                    elif k in _OF_FLOAT:
                        row[k] = float(v) if v not in (None, "") else 0.0
                    elif k in _OF_INT:
                        row[k] = int(float(v)) if v not in (None, "") else 0
                    else:
                        row[k] = v
                rows.append(row)
    rows.sort(key=lambda r: r["timestamp"])
    print(f"Loaded order flow: {len(rows)} bars from {len(files)} file(s)")
    return rows


def build_orderflow_index(of_data: list) -> dict:
    """Index order-flow bars by their 5-min timestamp for O(1) lookup."""
    index = {}
    if not of_data:
        return index
    for r in of_data:
        index[r["timestamp"]] = r
    return index


def get_orderflow_for_m5(of_index: dict, m5_ts) -> dict:
    """Return the order-flow bar for one M5 timestamp, or None."""
    if not of_index:
        return None
    if isinstance(m5_ts, str):
        m5_ts = _parse_ts(m5_ts)
    floor = m5_ts.replace(minute=(m5_ts.minute // 5) * 5, second=0, microsecond=0)
    return of_index.get(floor)


def get_orderflow_context(of_index: dict, m5_ts, n: int = 6) -> list:
    """Return up to n order-flow bars BEFORE the current M5 timestamp (cum-delta campaign)."""
    if not of_index:
        return []
    if isinstance(m5_ts, str):
        m5_ts = _parse_ts(m5_ts)
    floor = m5_ts.replace(minute=(m5_ts.minute // 5) * 5, second=0, microsecond=0)
    out = []
    for i in range(n, 0, -1):
        key = floor - timedelta(minutes=5 * i)
        if key in of_index:
            out.append(of_index[key])
    return out


def get_htf_context(h4: list, h1: list, current_ts) -> str:
    if isinstance(current_ts, str):
        current_ts = _parse_ts(current_ts)
    lines = []
    if h4:
        recent = [r for r in h4 if r["timestamp"] <= current_ts][-5:]
        if recent:
            lines.append("H4 (last 5 candles):")
            for r in recent:
                d = "▲" if r["close"] >= r["open"] else "▼"
                lines.append(f"  {r['timestamp']} {d} O:{r['open']} H:{r['high']} L:{r['low']} C:{r['close']}")
    if h1:
        recent = [r for r in h1 if r["timestamp"] <= current_ts][-6:]
        if recent:
            lines.append("H1 (last 6 candles):")
            for r in recent:
                d = "▲" if r["close"] >= r["open"] else "▼"
                lines.append(f"  {r['timestamp']} {d} O:{r['open']} H:{r['high']} L:{r['low']} C:{r['close']}")
    return "\n".join(lines) if lines else "No H4/H1 data available."
