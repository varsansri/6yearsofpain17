"""
POI ENGINE — the keystone (Idea 1, 2, 4, 6).

A *persistent* map of Points of Interest, marked across 4H / 1H / 15m, where each POI
carries TWO measured scores (Idea 6 — the measurement layer):

  • structural_score (0-10) — buyer/seller structural validity: how many timeframes see
    this level + how hard price was rejected from it. (multi-TF alignment = Idea 1)
  • crowd_score      (0-10) — how FOCAL it is: round numbers, prior session/day/week
    highs & lows, equal highs/lows. Pure Python → the AI cannot fake it.

From the pair we derive a reaction_type:
  CLEAN  (structural↑ crowd↑) — clean reaction expected, highest conviction
  QUIET  (structural↑ crowd↓) — real level nobody watches → reacts late/softly
  FIGHT  (structural↓ crowd↑) — focal trap → liquidity grab / fight, NOT a tidy bounce
  IGNORE (structural↓ crowd↓) — discard

Everything here is DETERMINISTIC and built only from data up to the current M5 index
(no look-ahead). The map is rebuilt each clock hour and "armed" (price-near flag)
re-checked every candle. Buyer/seller language only — sellers defend resistance above,
buyers defend support below.
"""
from datetime import timedelta

import config
import data_loader


# ── side language (LIVE — relative to current price) ──────────────────────────
# A level's role flips as price crosses it: a former resistance price closed ABOVE
# becomes support (sellers who defended it lost; buyers now defend it), and vice versa.
def _live_side(level_price: float, price: float) -> str:
    return "resistance" if level_price >= price else "support"


# ── swing detection (no future leak — a swing needs K confirmed candles each side) ──
def _swings(candles: list, k: int) -> list:
    """Return confirmed swing highs/lows from a candle list (oldest→newest).
    The last k candles are NEVER swings (can't be confirmed yet) — so no look-ahead."""
    out = []
    n = len(candles)
    for i in range(k, n - k):
        hi = candles[i]["high"]
        lo = candles[i]["low"]
        left  = candles[i - k:i]
        right = candles[i + 1:i + 1 + k]
        if all(hi >= c["high"] for c in left) and all(hi > c["high"] for c in right):
            # rejection strength: how far price fell away from the high afterwards
            drop = hi - min(c["low"] for c in right)
            out.append({"price": hi, "kind": "swing_high", "strength": drop})
        if all(lo <= c["low"] for c in left) and all(lo < c["low"] for c in right):
            rise = max(c["high"] for c in right) - lo
            out.append({"price": lo, "kind": "swing_low", "strength": rise})
    return out


# ── focal references: prior session/day/week H-L (pure crowd attention) ─────────
def _period_levels(m5_window: list, current_ts) -> list:
    """Prior DAY and prior WEEK highs/lows from closed periods only (no leak)."""
    levels = []
    if not m5_window:
        return levels
    cur_day = current_ts.date()
    # group by calendar day
    by_day = {}
    for c in m5_window:
        d = c["timestamp"].date()
        if d >= cur_day:        # skip today (still in progress) → no leak
            continue
        b = by_day.setdefault(d, {"hi": c["high"], "lo": c["low"]})
        b["hi"] = max(b["hi"], c["high"])
        b["lo"] = min(b["lo"], c["low"])
    if not by_day:
        return levels
    days = sorted(by_day)
    # prior day
    pd = by_day[days[-1]]
    levels.append({"price": pd["hi"], "kind": "day_high"})
    levels.append({"price": pd["lo"], "kind": "day_low"})
    # prior week (last up-to-7 closed days)
    wk = days[-7:]
    wk_hi = max(by_day[d]["hi"] for d in wk)
    wk_lo = min(by_day[d]["lo"] for d in wk)
    levels.append({"price": wk_hi, "kind": "week_high"})
    levels.append({"price": wk_lo, "kind": "week_low"})
    return levels


# ── crowd attention score (0-10) — round numbers + focal period levels ──────────
def _nearest_round(price: float):
    """Closest psychological level + how focal it is (bigger base = more focal)."""
    best = None
    for base in config.POI_ROUND_BASES:
        lvl = round(price / base) * base
        dist = abs(price - lvl)
        # focal weight: thousands matter most
        weight = base / config.POI_ROUND_BASES[0]
        score = max(0.0, 1 - dist / base) * weight
        if best is None or score > best[2]:
            best = (lvl, dist, score)
    return best  # (level, distance, raw_score)


def _crowd_score(price: float, period_levels: list) -> float:
    score = 0.0
    # round-number focality (0-6)
    lvl, dist, raw = _nearest_round(price)
    score += min(6.0, raw * 6.0)
    # proximity to a prior session/day/week extreme (0-4, the more important the level the more)
    weights = {"week_high": 4, "week_low": 4, "day_high": 3, "day_low": 3}
    for pl in period_levels:
        if abs(price - pl["price"]) <= config.POI_CLUSTER_PTS:
            score = max(score, score + weights.get(pl["kind"], 2) * 0.6)
    return round(min(10.0, score), 1)


# ── clustering: merge near-equal levels across timeframes ───────────────────────
def _cluster(raw_levels: list) -> list:
    """raw_levels: [{price, kind, tf, strength?}] → merged POIs with timeframe sets."""
    raw = sorted(raw_levels, key=lambda x: x["price"])
    clusters = []
    for lv in raw:
        if clusters and abs(lv["price"] - clusters[-1]["_anchor"]) <= config.POI_CLUSTER_PTS:
            c = clusters[-1]
            c["_prices"].append(lv["price"])
            c["timeframes"].add(lv["tf"])
            c["kinds"].add(lv["kind"])
            c["strength"] = max(c["strength"], lv.get("strength", 0))
            c["_anchor"] = sum(c["_prices"]) / len(c["_prices"])
        else:
            clusters.append({
                "_anchor": lv["price"], "_prices": [lv["price"]],
                "timeframes": {lv["tf"]}, "kinds": {lv["kind"]},
                "strength": lv.get("strength", 0),
            })
    return clusters


# ── structural score (0-10) — multi-TF alignment + rejection strength ───────────
def _structural_score(cluster: dict) -> float:
    tf_count = len(cluster["timeframes"])
    base = {1: 4.0, 2: 7.0, 3: 9.0}.get(tf_count, 9.5 if tf_count > 3 else 4.0)
    # rejection strength bonus (normalised, capped)
    bonus = min(1.0, cluster["strength"] / 400.0)
    return round(min(10.0, base + bonus), 1)


def _reaction_type(structural: float, crowd: float) -> str:
    hi, lo = config.POI_HIGH_SCORE, config.POI_LOW_SCORE
    s_hi, c_hi = structural >= hi, crowd >= hi
    s_lo, c_lo = structural < lo, crowd < lo
    if s_hi and c_hi:           return "CLEAN"
    if s_hi and (c_lo or not c_hi): return "QUIET"
    if (s_lo or not s_hi) and c_hi: return "FIGHT"
    return "IGNORE"


# ── build the full POI map at the current index (no leak) ───────────────────────
def build_map(m5_data: list, idx: int) -> list:
    """Construct the POI map as of m5_data[idx]. Deterministic, look-ahead free."""
    if not m5_data or idx < 0:
        return []
    current_ts = m5_data[idx]["timestamp"]

    # bounded lookback window of M5 (keeps cost O(window), not O(all history))
    win_start = current_ts - timedelta(days=config.POI_LOOKBACK_DAYS)
    lo = idx
    while lo > 0 and m5_data[lo - 1]["timestamp"] >= win_start:
        lo -= 1
    # we still pass the global idx to the no-leak getters; window only bounds period levels
    m5_window = m5_data[lo:idx + 1]

    # gather swings from each timeframe (no-leak: _agg_tail builds backward from idx,
    # the most recent candle is in-progress). Pull deep history so 4H is well represented.
    raw = []
    tfs = (
        ("4H",  data_loader._agg_tail(m5_data, idx, n=40,  hours=4)),
        ("1H",  data_loader._agg_tail(m5_data, idx, n=90,  hours=1)),
        ("15m", data_loader._agg_tail(m5_data, idx, n=120, minutes=15)),
    )
    for tf, candles in tfs:
        for sw in _swings(candles, config.POI_SWING_K):
            raw.append({**sw, "tf": tf})

    if not raw:
        return []

    period_levels = _period_levels(m5_window, current_ts)

    cur_price = m5_data[idx]["close"]
    pois = []
    for c in _cluster(raw):
        lvl = round(c["_anchor"], 1)
        structural = _structural_score(c)
        crowd = _crowd_score(lvl, period_levels)
        rtype = _reaction_type(structural, crowd)
        if rtype == "IGNORE":
            continue
        pois.append({
            "price": lvl,
            "origin": sorted(c["kinds"])[0],         # how it formed (swing_high/low)
            "side": _live_side(lvl, cur_price),       # live role vs current price
            "timeframes": sorted(c["timeframes"]),
            "structural_score": structural,
            "crowd_score": crowd,
            "reaction_type": rtype,
            "tested_count": 0,
            "armed": False,
            "distance_pts": None,
        })
    # strongest first (structural + crowd)
    pois.sort(key=lambda p: p["structural_score"] + p["crowd_score"], reverse=True)
    return pois


# ── arm POIs near the current price (cheap, every candle) ───────────────────────
def arm(poi_map: list, price: float) -> list:
    """Flag POIs within the arm band as 'armed' and set live distance. Returns armed list."""
    armed = []
    band = config.POI_ARM_BAND_PTS
    for p in poi_map:
        d = abs(price - p["price"])
        p["distance_pts"] = round(d, 1)
        p["side"] = _live_side(p["price"], price)   # role flips as price crosses it
        p["armed"] = d <= band
        if p["armed"]:
            armed.append(p)
    armed.sort(key=lambda p: p["distance_pts"])
    return armed


def mark_tested(poi_map: list, candle: dict):
    """If the candle wicked through a POI price, increment its tested_count."""
    for p in poi_map:
        if candle["low"] <= p["price"] <= candle["high"]:
            p["tested_count"] += 1


# ── prompt block — armed POIs in buyer/seller language ──────────────────────────
def poi_block(armed: list, price: float) -> str:
    if not armed:
        return "POINTS OF INTEREST: none armed (price not near a mapped level)."
    lines = ["POINTS OF INTEREST (armed — price is near these reaction zones):"]
    for p in armed[:6]:
        above = "above" if p["price"] >= price else "below"
        lines.append(
            f"  • {p['price']} ({p['side']}, {above}, {p['distance_pts']:.0f}pts away) "
            f"| {p['reaction_type']} | structural {p['structural_score']}/10, "
            f"crowd {p['crowd_score']}/10 | seen on {','.join(p['timeframes'])}"
            f"{' | tested '+str(p['tested_count'])+'x' if p['tested_count'] else ''}"
        )
    lines.append(
        "  Reaction guide: CLEAN=expect a clean reaction · QUIET=real but unwatched, soft/late · "
        "FIGHT=focal trap, expect a liquidity fight not a tidy bounce."
    )
    return "\n".join(lines)
