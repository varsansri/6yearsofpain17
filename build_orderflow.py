"""
Build a 5-minute ORDER FLOW dataset from Binance spot aggTrades (FREE tick data).
Aligned to the existing M5 candles: same source (Binance spot BTCUSDT),
same timezone (IST = UTC+5:30), same 5-min boundaries.

aggTrades row: aggId, price, qty, firstId, lastId, timestamp(µs), isBuyerMaker, isBestMatch
  isBuyerMaker = True  -> buyer was maker -> SELLER was the aggressor (market sell)
  isBuyerMaker = False -> buyer was taker -> BUYER  was the aggressor (market buy)

Output: data/orderflow_5m_<date>.csv  (one row per 5-min IST bar)
"""
import csv
from collections import defaultdict
from datetime import datetime, timedelta, timezone

SRC = "/tmp/BTCUSDT-aggTrades-2025-06-17.csv"
OUT = "data/orderflow_5m_2025-06-17.csv"
IST = timedelta(hours=5, minutes=30)
PRICE_BIN = 10.0          # $10 footprint bins
LARGE_BTC = 1.0           # "notable" single-trade size
WHALE_BTC = 5.0           # whale single-trade size

def floor5(dt):
    return dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)

class Bar:
    __slots__ = ("o","h","l","c","vol","qvol","n","bvol","svol","bt","st",
                 "maxt","large_vol","large_n","whale_vol","bins")
    def __init__(self):
        self.o=None; self.h=-1e18; self.l=1e18; self.c=None
        self.vol=0.0; self.qvol=0.0; self.n=0
        self.bvol=0.0; self.svol=0.0; self.bt=0; self.st=0
        self.maxt=0.0; self.large_vol=0.0; self.large_n=0; self.whale_vol=0.0
        self.bins=defaultdict(lambda:[0.0,0.0])  # binprice -> [buyvol, sellvol]

def main():
    bars = {}
    rows = 0
    with open(SRC, newline="") as f:
        for line in f:
            p = line.split(",")
            if len(p) < 7 or not p[0].strip().lstrip("-").isdigit():
                continue
            price = float(p[1]); qty = float(p[2]); ts = int(p[5])
            is_buyer_maker = p[6].strip().lower() == "true"
            # normalise timestamp to seconds
            sec = ts/1e6 if ts > 1e15 else (ts/1e3 if ts > 1e12 else ts)
            dt_ist = datetime.fromtimestamp(sec, tz=timezone.utc).replace(tzinfo=None) + IST
            key = floor5(dt_ist)
            b = bars.get(key)
            if b is None:
                b = bars[key] = Bar()
                b.o = price
            b.c = price
            if price > b.h: b.h = price
            if price < b.l: b.l = price
            b.vol += qty; b.qvol += price*qty; b.n += 1
            buy_aggressor = not is_buyer_maker
            binp = round(int(price / PRICE_BIN) * PRICE_BIN, 1)
            if buy_aggressor:
                b.bvol += qty; b.bt += 1; b.bins[binp][0] += qty
            else:
                b.svol += qty; b.st += 1; b.bins[binp][1] += qty
            if qty > b.maxt: b.maxt = qty
            if qty >= LARGE_BTC: b.large_vol += qty; b.large_n += 1
            if qty >= WHALE_BTC: b.whale_vol += qty
            rows += 1
    print(f"Parsed {rows} aggTrades into {len(bars)} 5m bars")

    cum_delta = 0.0
    out_rows = []
    for key in sorted(bars):
        b = bars[key]
        delta = b.bvol - b.svol
        cum_delta += delta
        rng = max(b.h - b.l, 1e-9)
        body = b.c - b.o
        delta_pct = (delta / b.vol * 100) if b.vol else 0.0
        avg_size = (b.vol / b.n) if b.n else 0.0
        # POC = price bin with most total volume
        poc = max(b.bins.items(), key=lambda kv: kv[1][0]+kv[1][1])
        poc_price, (poc_b, poc_s) = poc
        # footprint: top 3 bins by total volume -> "price:buy:sell"
        top = sorted(b.bins.items(), key=lambda kv: kv[1][0]+kv[1][1], reverse=True)[:3]
        fp = ";".join(f"{int(pr)}:{bs[0]:.2f}:{bs[1]:.2f}" for pr,bs in top)
        # absorption: heavy one-sided aggression but price barely moved
        absorption = abs(delta) > 0.30*b.vol and abs(body) < 0.25*rng
        out_rows.append([
            key.strftime("%Y-%m-%d %H:%M:%S"),
            f"{b.o:.2f}", f"{b.h:.2f}", f"{b.l:.2f}", f"{b.c:.2f}",
            f"{b.vol:.4f}", f"{b.qvol:.2f}", b.n,
            f"{b.bvol:.4f}", f"{b.svol:.4f}", f"{delta:.4f}", f"{cum_delta:.4f}",
            f"{delta_pct:.2f}", b.bt, b.st, f"{avg_size:.5f}",
            f"{b.maxt:.4f}", f"{b.large_vol:.4f}", b.large_n, f"{b.whale_vol:.4f}",
            f"{poc_price:.0f}", f"{poc_b:.4f}", f"{poc_s:.4f}", fp,
            "YES" if absorption else "NO",
        ])

    header = ["timestamp","open","high","low","close","volume","quote_volume",
              "trade_count","buy_vol","sell_vol","delta","cum_delta","delta_pct",
              "buy_trades","sell_trades","avg_trade_size","max_trade",
              "large_vol_1btc","large_trades_1btc","whale_vol_5btc",
              "poc_price","poc_buy_vol","poc_sell_vol","footprint_top3","absorption"]
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(out_rows)
    print(f"Wrote {OUT}: {len(out_rows)} bars")
    print(f"  IST range: {out_rows[0][0]} -> {out_rows[-1][0]}")

if __name__ == "__main__":
    main()
