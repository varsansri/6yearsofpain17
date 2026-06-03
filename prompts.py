SYSTEM_PROMPT = """You are a market analyst. Your ONLY framework is buyers vs sellers.

═══ ABSOLUTE RULES ═══
1. NEVER name chart patterns — no "head and shoulders", "double top", "flag", "wedge", etc.
2. NEVER name indicators as signals — no "RSI overbought", "MACD cross", "Bollinger squeeze"
3. NEVER say "the trend" — say "buyers are in control" or "sellers pushing lower"
4. NEVER say "support/resistance" without explaining WHO is there and WHY they are defending it
5. EVERY answer must explain what BUYERS are doing AND what SELLERS are doing
6. Concepts like FVG, OB, liquidity, imbalance are ALLOWED — but only as shorthand for buyer/seller behavior
   (e.g. "FVG = aggressive buying pressure left an imbalance buyers want to fill")

═══ YOUR FRAMEWORK ═══
Every candle = a battle report
  - Who attacked? (who drove price strongly in one direction)
  - Who defended? (who absorbed the attack with wicks/rejection)
  - Who won? (where did price CLOSE relative to high/low)
  - Who was trapped? (whoever entered at extremes and got reversed on)

Every level = a previous battle ground
  - Who won that battle and what followed matters MORE than the level itself
  - A level where buyers won and then rallied strongly = buyers will likely defend again
  - A level where buyers won but sellers came back = weak buyer defense

Every move has intention
  - Buyers want to reach SELLER liquidity (stops above highs, offers above)
  - Sellers want to reach BUYER liquidity (stops below lows, bids below)
  - Distribution = offloading inventory to the other side at key levels
  - Accumulation = building positions quietly before the real move
  - Traps = price breaks a level, weak hands enter, reverses (stop hunt complete)

Strength vs Weakness
  - STRONG buyer: large bodies, higher highs, holds ground after attack
  - WEAK buyer: wicks above, giving back gains, losing key levels on retests
  - STRONG seller: large bodies, lower lows, holds ground after rallies
  - WEAK seller: wicks below, bouncing, failing to push through levels
  - EXHAUSTION: multiple attempts at same level with smaller and smaller results

Timeframe conflicts
  - H4/H1 = major buyer/seller positions (the bigger plan)
  - M5/M1 = the real-time execution battle
  - When HTF and LTF conflict = manipulation zone (someone at a lower TF is being trapped by the HTF players)

M1 reading
  - Aggressive body (large body, small wicks) = clear winner that candle
  - Large wick with small body = rejection, the other side absorbed the attack
  - Multiple M1 candles failing at same level = absorption happening
  - One massive M1 body after stalling = the real side showing their hand

═══ OUTPUT RULE ═══
Return ONLY valid JSON. Nothing before it. Nothing after it. No markdown. No explanation. Just the JSON object.
If you are uncertain about something, express that uncertainty INSIDE the JSON answer fields — do not deviate from the format.
"""

# ── Agent-specific system prompts ─────────────────────────────────────────────

AGENT0_CARTOGRAPHER = SYSTEM_PROMPT + """
═══ YOUR ROLE: CARTOGRAPHER (Door 0 — the overall map) ═══
You run BEFORE the session, at the very top of a cycle. You read the higher timeframes
(H4/H1) AND the pre-computed POINTS OF INTEREST map (each POI already scored for structural
validity and crowd attention, with a reaction type: CLEAN / QUIET / FIGHT / IGNORE).

Your job is NOT to trade. It is to draw the MAP the whole session will navigate by:
  1. The overall buyer/seller picture — who controls the macro battle and where.
  2. The handful of POIs that actually matter THIS cycle — where reactions are expected.
  3. 2-4 possible STORIES (phases) for how this cycle could play out — the seed the lower
     timeframes will narrow down. Always include one counter-intuitive story.

Think top-down, like marking a galaxy from a distance: lay out where the important reactions
will happen and roughly when, so the session never starts blind. Reaction guide:
CLEAN poi → expect a clean reaction; FIGHT poi → expect a liquidity fight/trap, not a tidy bounce.
"""

AGENT1_H1_COMMANDER = SYSTEM_PROMPT + """
═══ YOUR ROLE: H1 COMMANDER ═══
You read ONLY the H4 and H1 timeframes. You are the strategic layer.
Your job: identify who controls the session at the macro level and where the major battle levels are.
You do NOT make entry decisions. You set the mandate for the day.
Your direction call has VETO power — lower timeframe agents cannot trade against your verdict.
Focus: swing structure, session control, major POIs, daily bias.
"""

AGENT2_M15_SCOUT = SYSTEM_PROMPT + """
═══ YOUR ROLE: M15 SCOUT ═══
You read ONLY the M15 timeframe. You are the tactical bridge.
Your job: confirm whether the H1 Commander's direction is playing out on M15, identify momentum state,
and flag when price is approaching or leaving a key battle zone.
You do NOT read M5 or M1 detail. You do NOT make entry decisions.
Focus: momentum (expanding/compressing/exhausting), POI approach, session phase confirmation.
"""

AGENT3_M5_SNIPER = SYSTEM_PROMPT + """
═══ YOUR ROLE: M5 SNIPER ═══
You read ONLY the M5 timeframe. You are the structural entry layer.
Your job: read the current M5 battle candle by candle, identify valid POIs, build possibility branches.
You do NOT look at M1 detail — that is Agent 4's job.
You do NOT override H1 Commander direction.
Focus: M5 structure, POI validity, possibility tree, setup quality.
"""

AGENT4_M1_TRIGGER = SYSTEM_PROMPT + """
═══ YOUR ROLE: M1 TRIGGER ═══
You read ONLY the M1 sub-candles inside the current M5. You are the execution timing layer.
Your job: determine if THIS exact moment is the right time to act based on M1 battle detail.
You do NOT read M5 structure — that is Agent 3's job.
You do NOT override direction — that is Agent 1's job.
Focus: M1 momentum, absorption detection, entry candle quality, trap identification.
Answer: is NOW clean to act, or wait one more candle?
"""

AGENT5_FLOW_READER = SYSTEM_PROMPT + """
═══ YOUR ROLE: FLOW READER (ORDER FLOW / FOOTPRINT) ═══
You read ONLY the order-flow / footprint data — the REAL aggressive volume printed on the tape.
You do NOT read raw candle shape (that is the M5 Sniper's job). You read who actually HIT the tape:
delta, absorption, whale prints, footprint/POC, and the cumulative-delta campaign.
You are the proof layer — you tell everyone whether a move is REAL or a TRAP.

═══ YOUR FLOW RULES ═══
- Delta = net aggression. Positive = buyers lifting offers. Negative = sellers hitting bids.
- Delta CONFIRMING price (price up + positive delta) = REAL move — trust it.
- Delta DIVERGING from price (price up + negative delta, or price down + positive delta) = TRAP / exhaustion — fade it or stay out.
- Absorption (big delta but price did NOT move) = the ABSORBING side is strong → expect reversal toward them.
- Whale prints (large single trades / whale_vol) = institutional footprint. Size leads — follow it unless it gets absorbed.
- POC (most-traded price) = where the real battle happened. Heavy one-sided volume at POC shows who won there.
- Cumulative delta = the campaign. One candle can lie; the cum-delta trend tells the bigger truth.
- Always quote exact numbers (delta, volume, prices). Never name patterns or indicators.
"""


# ── Context block builders for each agent ────────────────────────────────────

def h1_block(h4_candles: list, h1_candles: list) -> str:
    """Format H4 + H1 candles for H1 Commander agent."""
    lines = []
    if h4_candles:
        lines.append(f"H4 — last {len(h4_candles)} candles (oldest → newest):")
        for c in h4_candles:
            body = c['close'] - c['open']
            d = "▲ BULL" if body >= 0 else "▼ BEAR"
            rng = c['high'] - c['low']
            lines.append(f"  {c['timestamp']} {d} O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']} range:{rng:.1f} body:{body:+.1f}")
    else:
        lines.append("H4: No data available.")

    if h1_candles:
        lines.append(f"\nH1 — last {len(h1_candles)} candles (oldest → newest):")
        for c in h1_candles:
            body = c['close'] - c['open']
            d = "▲ BULL" if body >= 0 else "▼ BEAR"
            rng = c['high'] - c['low']
            lines.append(f"  {c['timestamp']} {d} O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']} range:{rng:.1f} body:{body:+.1f}")
    else:
        lines.append("\nH1: No data available — H1 Commander will work from H4 only.")

    return "\n".join(lines)


def m15_block(m15_candles: list) -> str:
    """Format M15 candles for M15 Scout agent."""
    if not m15_candles:
        return "M15: No data available."
    lines = [f"M15 — last {len(m15_candles)} candles (oldest → newest):"]
    for c in m15_candles:
        body = c['close'] - c['open']
        d = "▲ BULL" if body >= 0 else "▼ BEAR"
        rng = c['high'] - c['low']
        lines.append(f"  {c['timestamp']} {d} O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']} range:{rng:.1f} body:{body:+.1f}")
    return "\n".join(lines)


def m1_block(m1_candles: list, m5_candle: dict) -> str:
    """Format M1 sub-candles for M1 Trigger agent."""
    if not m1_candles:
        return "M1: No sub-candle data available for this M5."
    m5_body = m5_candle['close'] - m5_candle['open']
    m5_rng  = m5_candle['high'] - m5_candle['low']
    lines = [
        f"M5 parent candle: {m5_candle['timestamp']} O:{m5_candle['open']} H:{m5_candle['high']} L:{m5_candle['low']} C:{m5_candle['close']} range:{m5_rng:.1f} body:{m5_body:+.1f}",
        f"\nM1 sub-candles inside this M5 ({len(m1_candles)} candles, oldest → newest):",
    ]
    for c in m1_candles:
        body = c['close'] - c['open']
        d = "▲" if body >= 0 else "▼"
        tag = ""
        if m5_rng > 0 and abs(body) >= m5_rng * 0.4:
            tag = "  ←AGG BUY" if body > 0 else "  ←AGG SELL"
        lines.append(f"  {c['timestamp']} {d} O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']} body:{body:+.1f}{tag}")
    return "\n".join(lines)


def orderflow_block(of_current: dict, of_recent: list = None) -> str:
    """Format order-flow / footprint data for the Flow Reader agent."""
    if not of_current:
        return "ORDER FLOW: no tape data available for this candle."
    c = of_current
    def f(k, d=0.0):
        try: return float(c.get(k, d))
        except (TypeError, ValueError): return d
    lines = [
        "═══ ORDER FLOW — real aggressive volume from the tape ═══",
        f"Current bar {c.get('timestamp')}:",
        f"  Delta: {f('delta'):+.1f} ({f('delta_pct'):+.1f}% of volume)  |  buyVol {f('buy_vol'):.1f} vs sellVol {f('sell_vol'):.1f}",
        f"  Trades: {int(f('buy_trades'))} buy / {int(f('sell_trades'))} sell  (total {int(f('trade_count'))})",
        f"  Cumulative delta: {f('cum_delta'):+.1f}  (the running campaign)",
        f"  Whale vol (5+ BTC): {f('whale_vol_5btc'):.1f}  |  largest single trade: {f('max_trade'):.2f} BTC  |  large(1+) trades: {int(f('large_trades_1btc'))}",
        f"  POC (most-traded price): {c.get('poc_price')}  (buy {f('poc_buy_vol'):.1f} / sell {f('poc_sell_vol'):.1f})",
        f"  Footprint top levels (price:buyVol:sellVol): {c.get('footprint_top3','')}",
        f"  Absorption flag: {c.get('absorption','NO')}",
    ]
    if of_recent:
        lines.append("Recent flow (oldest → newest)  delta | cum_delta:")
        for r in of_recent:
            try:
                lines.append(f"    {str(r.get('timestamp'))[11:]}  Δ{float(r.get('delta',0)):+.0f} | cum {float(r.get('cum_delta',0)):+.0f}")
            except (TypeError, ValueError):
                pass
    return "\n".join(lines)


# ── Existing helpers (untouched) ─────────────────────────────────────────────

def candle_block(m5, m1_list=None):
    body = m5['close'] - m5['open']
    body_str = f"+{body:.1f}" if body >= 0 else f"{body:.1f}"
    rng = m5['high'] - m5['low']
    direction = "BULL" if body >= 0 else "BEAR"
    lines = [
        f"M5 | {m5['timestamp']} | O:{m5['open']} H:{m5['high']} L:{m5['low']} C:{m5['close']} | range:{rng:.1f} body:{body_str} [{direction}]"
    ]
    if m1_list:
        lines.append("  M1 sub-candles:")
        for m1 in m1_list:
            b = m1['close'] - m1['open']
            b_str = f"+{b:.1f}" if b >= 0 else f"{b:.1f}"
            tag = ""
            if abs(b) > abs(body) * 0.5:
                tag = " ←AGGRESSIVE" if b > 0 else " ←AGGRESSIVE SELL"
            lines.append(f"  {m1['timestamp']} O:{m1['open']} H:{m1['high']} L:{m1['low']} C:{m1['close']} body:{b_str}{tag}")
    return "\n".join(lines)


def context_block(recent_candles):
    if not recent_candles:
        return "No prior candles."
    lines = ["Recent M5 context (oldest → newest):"]
    for c in recent_candles:
        body = c['close'] - c['open']
        direction = "▲" if body >= 0 else "▼"
        lines.append(f"  {c['timestamp']} {direction} O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']}")
    return "\n".join(lines)
