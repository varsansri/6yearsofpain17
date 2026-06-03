"""
DOOR 4 — TRADE ENTRY GATE
Gates (in order):
  1. Hard code checks (automatic blocks)
  2. H1 Commander direction veto (from presession mandate)
  3. M1 verdict gate (from d2 m1_verdict)
  4. Bull Agent + Bear Agent run in PARALLEL
  5. 14-rule checklist + 10 thinking questions
  6. Half-Kelly position sizing on confirmed entry
"""

import claude_client
import display
import config
import flow_layer
from prompts import candle_block, context_block


# ── Hard code checks ──────────────────────────────────────────────────────────

def _code_checks(signal: dict, state: dict, m5: dict) -> tuple[bool, list]:
    msgs = []
    blocked = False

    checks = [
        (state.get("daily_trades", 0) >= config.MAX_DAILY_TRADES,
         f"Daily trade limit reached ({state.get('daily_trades')}/{config.MAX_DAILY_TRADES})"),
        (state.get("total_trades", 0) >= config.MAX_TOTAL_TRADES,
         f"Total trade limit reached ({state.get('total_trades')}/{config.MAX_TOTAL_TRADES})"),
        (state.get("active_trade") is not None, "Already in a trade"),
        (state.get("session_halted"), "Session is HALTED"),
        (state.get("daily_loss_limit_hit"), "Daily loss limit reached"),
    ]

    entry = signal.get("entry_level")
    sl    = signal.get("sl_level")
    tp    = signal.get("tp_level")
    direction = signal.get("direction")

    if entry and sl and tp:
        sl_dist  = abs(entry - sl) / config.PIP_SIZE
        poi_dist = abs(entry - m5["close"]) / config.PIP_SIZE
        if sl_dist < config.MIN_SL_PIPS:
            checks.append((True, f"SL too close: {sl_dist:.1f}p (min {config.MIN_SL_PIPS}p)"))
        if poi_dist > config.MAX_POI_PIPS:
            checks.append((True, f"POI too far: {poi_dist:.1f}p (max {config.MAX_POI_PIPS}p)"))
        rr = (tp - entry) / max(entry - sl, 0.0001) if direction == "LONG" \
             else (entry - tp) / max(sl - entry, 0.0001)
        if rr < config.MIN_RR:
            checks.append((True, f"R:R too low: {rr:.2f}:1 (min {config.MIN_RR}:1)"))

    for fail_cond, msg in checks:
        if fail_cond:
            msgs.append(("BLOCK", msg))
            blocked = True

    return blocked, msgs


# ── H1 Commander direction veto ───────────────────────────────────────────────

def _h1_veto(signal: dict, presession: dict) -> tuple[bool, str]:
    """Block if trade direction directly contradicts H1 Commander mandate."""
    mandate = presession.get("q11_direction_mandate", "").upper()
    direction = (signal.get("direction") or "").upper()
    if direction == "LONG" and "BEARISH" in mandate and "BULLISH" not in mandate:
        return True, f"H1 Commander mandate is BEARISH — LONG entry vetoed. Flip price: {mandate}"
    if direction == "SHORT" and "BULLISH" in mandate and "BEARISH" not in mandate:
        return True, f"H1 Commander mandate is BULLISH — SHORT entry vetoed. Flip price: {mandate}"
    return False, ""


# ── Half-Kelly position sizing ────────────────────────────────────────────────

def _kelly_size(trade_history: list, rr: float) -> float:
    """
    Half-Kelly position size as fraction of capital [MIN, MAX].
    f* = 0.5 × (b×p - q) / b   where b=R:R, p=win_rate, q=1-p
    """
    if not trade_history:
        return config.DEFAULT_POSITION_SIZE

    wins  = sum(1 for t in trade_history if t.get("result_pips", 0) > 0)
    total = len(trade_history)
    if total == 0 or rr <= 0:
        return config.DEFAULT_POSITION_SIZE

    p = wins / total
    q = 1 - p
    b = rr
    kelly = (b * p - q) / b
    half_kelly = kelly * 0.5

    return max(config.MIN_POSITION_SIZE,
               min(config.MAX_POSITION_SIZE, round(half_kelly, 2)))


# ── Bull + Bear agent prompts ─────────────────────────────────────────────────

def _bull_prompt(m5, m1_list, recent_candles, signal):
    return f"""
{context_block(recent_candles)}
CURRENT CANDLE: {candle_block(m5, m1_list)}
Proposed signal: {signal.get('direction')} Entry:{signal.get('entry_level')} SL:{signal.get('sl_level')} TP:{signal.get('tp_level')}

You are the BULL AGENT. Argue the STRONGEST possible case for buyers being in control
and why a LONG entry makes sense here. Be honest. Buyer/seller language only.

Return ONLY this JSON:
{{
  "bull_case": "strongest argument for buyers in control right now with specific prices",
  "buyer_strength": 1,
  "key_buyer_evidence": ["price evidence 1", "price evidence 2", "price evidence 3"],
  "bull_invalidated_if": "exact price/action that proves buyers are not in control",
  "rating": 0
}}
rating: 1-10 (1=very weak bull case, 10=overwhelming buyer control)
"""


def _bear_prompt(m5, m1_list, recent_candles, signal):
    return f"""
{context_block(recent_candles)}
CURRENT CANDLE: {candle_block(m5, m1_list)}
Proposed signal: {signal.get('direction')} Entry:{signal.get('entry_level')} SL:{signal.get('sl_level')} TP:{signal.get('tp_level')}

You are the BEAR AGENT. Argue the STRONGEST possible case for sellers being in control
and why this trade should NOT be entered (or why SHORT makes more sense).
Be honest. Buyer/seller language only.

Return ONLY this JSON:
{{
  "bear_case": "strongest argument for sellers in control right now with specific prices",
  "seller_strength": 1,
  "key_seller_evidence": ["price evidence 1", "price evidence 2", "price evidence 3"],
  "bear_invalidated_if": "exact price/action that proves sellers are not in control",
  "rating": 0
}}
rating: 1-10 (1=very weak bear case, 10=overwhelming seller control)
"""


# ── Main run ──────────────────────────────────────────────────────────────────

def run(m5: dict, m1_list: list, recent_candles: list,
        signal: dict, d2_analysis: dict, d3_result: dict,
        state: dict, presession: dict, required_conviction: float = 7) -> dict:

    display.door_header(4, "TRADE ENTRY GATE — 5-AGENT CONSENSUS")

    # Gate 1: Hard code checks
    blocked, msgs = _code_checks(signal, state, m5)
    for style, msg in msgs:
        display.block(msg, style)
    if blocked:
        display.block("Entry BLOCKED by code checks", "BLOCK")
        return {"enter": False, "blocked": True, "messages": msgs}

    # Gate 2: H1 Commander veto
    vetoed, veto_reason = _h1_veto(signal, presession)
    if vetoed:
        display.block(f"H1 COMMANDER VETO — {veto_reason}", "BLOCK")
        return {"enter": False, "blocked": True, "veto_reason": veto_reason}

    # Gate 2.5: ORDER-FLOW VETO (additive) — never enter into a wall of opposing aggression
    flow = {}
    flow_confirms = True
    if config.ORDERFLOW_ENABLED:
        flow = flow_layer.normalize(d2_analysis.get("flow", {}))
        f_blocked, f_reason = flow_layer.veto(flow, signal.get("direction"))
        if f_blocked:
            display.block(f"FLOW VETO — {f_reason}", "BLOCK")
            return {"enter": False, "blocked": True, "flow_veto": f_reason}
        # confirms = flow not opposing (opposing already vetoed above)
        flow_confirms = flow_layer._aligns(flow.get("bias", "neutral"),
                                           signal.get("direction")) >= 0

    # Gate 3: M1 verdict gate
    m1_verdict = d2_analysis.get("m1_verdict", "WAIT")
    if m1_verdict == "ABORT":
        reason = d2_analysis.get("m1_reason", "M1 Trigger signalled ABORT")
        display.block(f"M1 TRIGGER ABORT — {reason}", "BLOCK")
        return {"enter": False, "blocked": True, "m1_abort": reason}

    if m1_verdict == "WAIT":
        display.block(f"M1 Trigger: WAIT — {d2_analysis.get('m1_reason', '')}", "WARN")

    # Gate 4: Bull + Bear agents in parallel
    print("\n  ▶ Running Bull Agent + Bear Agent in parallel...")
    bull_data, bear_data = _run_debate_parallel(m5, m1_list, recent_candles, signal)

    print(f"\n  Bull rating: {bull_data.get('rating')}/10 — {str(bull_data.get('bull_case',''))[:150]}")
    print(f"  Bear rating: {bear_data.get('rating')}/10 — {str(bear_data.get('bear_case',''))[:150]}")

    # Gate 5: 14-rule checklist + 10 thinking questions
    entry_val = signal.get("entry_level")
    sl_val    = signal.get("sl_level")
    tp_val    = signal.get("tp_level")
    direction = signal.get("direction")

    if direction == "LONG":
        rr_calc = round((tp_val - entry_val) / max(entry_val - sl_val, 0.0001), 2)
    else:
        rr_calc = round((entry_val - tp_val) / max(sl_val - entry_val, 0.0001), 2)

    # Pre-verify items already gated by earlier Python checks:
    # - h1_h4_aligned: Gate 2 veto already blocks mandate-direction mismatch
    # - m1_trigger_not_abort: Gate 3 already blocked ABORT; CLEAN/WAIT are fine
    # - trades_today_ok / total_trades_ok: Gate 1 hard code already checked limits
    h1_mandate = presession.get('q11_direction_mandate', 'N/A')
    m1_pass = m1_verdict in ("CLEAN", "WAIT")
    daily_ok  = state.get("daily_trades", 0) < config.MAX_DAILY_TRADES
    total_ok  = state.get("total_trades", 0) < config.MAX_TOTAL_TRADES

    # Order-flow context line for the gate prompt (raw Flow Reader read from Door 2)
    _fl = d2_analysis.get("flow", {}) or {}
    flow_line = (f"ORDER FLOW: {_fl.get('flow_verdict','N/A')} | bias {_fl.get('flow_bias','?')} | "
                 f"strength {_fl.get('flow_strength','?')} — {str(_fl.get('flow_note',''))[:180]}"
                 if config.ORDERFLOW_ENABLED and _fl else "ORDER FLOW: not available")

    gate_prompt = f"""
{context_block(recent_candles)}
CURRENT CANDLE: {candle_block(m5, m1_list)}

PROPOSED TRADE:
Direction: {direction} | Entry: {entry_val} | SL: {sl_val} | TP: {tp_val} | R:R: {rr_calc}:1
Conviction so far: {signal.get('conviction')}/10
M1 Verdict: {m1_verdict} — {d2_analysis.get('m1_reason', '')}
M15 Read: {d3_result.get('m15_read', {}).get('m15_note', 'N/A')}
H1 Mandate: {h1_mandate}
{flow_line}

BULL AGENT (rating {bull_data.get('rating')}/10): {str(bull_data.get('bull_case',''))[:250]}
BEAR AGENT (rating {bear_data.get('rating')}/10): {str(bear_data.get('bear_case',''))[:250]}

CANDLE ANALYSIS: {d2_analysis.get('q5_intention', '')}
DOMINANT BRANCH: {d3_result.get('dominant_branch', '')}
M15 Momentum: {d3_result.get('m15_read', {}).get('m15_direction','?')} | {d3_result.get('m15_read', {}).get('m15_energy','?')}

Complete the 14-rule checklist then answer the 10 entry thinking questions.
NOTE: Items marked PRE-VERIFIED are already confirmed by earlier Python gates — do NOT change them.

Return ONLY this JSON:
{{
  "checklist": {{
    "three_checkpoints_hit": {{"pass": false, "note": "Key battle level + M5 confirmation at entry + momentum aligned?"}},
    "options_remaining_2_or_less": {{"pass": false, "note": "Possibility tree narrowed to ≤ 2 viable branches?"}},
    "movie_test_clear": {{"pass": false, "note": "Would the buyer/seller story be instantly obvious to anyone watching?"}},
    "poi_not_midway": {{"pass": false, "note": "Entry at true boundary — NOT in the middle of a range?"}},
    "poi_distance_ok": {{"pass": false, "note": "Price within 0-8pts of exact POI entry level?"}},
    "rr_minimum_1_5": {{"pass": false, "note": "R:R ≥ 1.5:1?"}},
    "trades_today_ok": {{"pass": true, "note": "PRE-VERIFIED: daily={state.get('daily_trades',0)}/{config.MAX_DAILY_TRADES} — keep pass=true"}},
    "total_trades_ok": {{"pass": true, "note": "PRE-VERIFIED: total={state.get('total_trades',0)}/{config.MAX_TOTAL_TRADES} — keep pass=true"}},
    "not_fresh_untested_level": {{"pass": false, "note": "Level tested at least once before?"}},
    "conviction_7_plus": {{"pass": false, "note": "Conviction ≥ {required_conviction}/10 after Bull and Bear arguments?"}},
    "h1_h4_aligned": {{"pass": true, "note": "PRE-VERIFIED: H1 Commander mandate ({h1_mandate[:60]}) cleared Gate 2 veto — keep pass=true"}},
    "m1_trigger_not_abort": {{"pass": {str(m1_pass).lower()}, "note": "PRE-VERIFIED: M1 verdict is {m1_verdict} — keep as shown"}},
    "order_flow_confirms": {{"pass": {str(flow_confirms).lower()}, "note": "PRE-VERIFIED: tape not opposing {direction} (opposing flow already vetoed) — keep as shown"}},
    "not_news_blackout": {{"pass": true, "note": "No news event imminent in next 30 minutes?"}},
    "first_candle_plan_defined": {{"pass": false, "note": "Clear plan if first candle moves 30+ pts against?"}},
    "m15_not_opposing": {{"pass": false, "note": "M15 momentum not actively opposing the trade direction?"}}
  }},
  "q1_dominant_branch": "Which branch justifies this trade? Quote the branch and its confirm condition.",
  "q2_inversion_point": "Exact price/candle that proves this trade WRONG before SL is hit?",
  "q3_branches_2_or_less": "Are ≤ 2 branches remaining? Name them and why others are eliminated.",
  "q4_battle_level": "Does entry sit at a previous battle level? Who won that battle? What followed?",
  "q5_sl_liquidity": "What buyer/seller liquidity does the SL protect? Whose stops are there?",
  "q6_tp_liquidity": "What liquidity is TP targeting? Which trapped traders is price hunting?",
  "q7_trap_possibility": "Could this be a trap? Evidence for and against.",
  "q8_opposite_side": "What are the opposing side doing RIGHT NOW? Strong, weak, retreating, building?",
  "q9_level_history": "Has this level been tested this session? First test vs retested?",
  "q10_minimum_confirmation": "Minimum price action needed to enter. What triggers entry vs keeps you out?",
  "final_conviction": 0,
  "enter": false,
  "no_entry_reason": "if enter=false, why does this trade not pass"
}}

Set enter=true ONLY if ALL checklist items pass=true AND final_conviction >= {required_conviction}.
"""

    result = claude_client.ask_agent("m5_sniper", gate_prompt, label="Door 4 — Entry Gate")

    # Enforce pre-verified items — AI must not override these
    checklist = result.get("checklist", {})
    conv_ok = float(result.get("final_conviction", 0) or 0) >= required_conviction
    for pre_key, pre_val in [
        ("h1_h4_aligned",       True),
        ("m1_trigger_not_abort", m1_pass),
        ("trades_today_ok",      daily_ok),
        ("total_trades_ok",      total_ok),
        ("not_news_blackout",    True),
        ("order_flow_confirms",  flow_confirms),
        ("conviction_7_plus",    conv_ok),
    ]:
        if pre_key in checklist and isinstance(checklist[pre_key], dict):
            checklist[pre_key]["pass"] = pre_val
    result["checklist"] = checklist

    # Display checklist
    checklist = result.get("checklist", {})
    all_pass = True
    print("\n  14-RULE CHECKLIST:")
    for rule, data in checklist.items():
        if isinstance(data, dict):
            passed = data.get("pass", False)
            note   = data.get("note", "")
        else:
            passed = bool(data)
            note   = ""
        icon = "✓" if passed else "✗"
        if not passed:
            all_pass = False
        print(f"  {icon} {rule.replace('_', ' ').upper()}")
        if not passed:
            print(f"      → {note[:120]}")

    # Display thinking questions
    q_names = ["dominant_branch", "inversion_point", "branches_2_or_less",
               "battle_level", "sl_liquidity", "tp_liquidity",
               "trap_possibility", "opposite_side", "level_history",
               "minimum_confirmation"]
    print("\n  10 ENTRY THINKING QUESTIONS:")
    for i, name in enumerate(q_names, 1):
        val = result.get(f"q{i}_{name}", "")
        if val:
            print(f"\n  Q{i}: {str(val)[:250]}")

    conviction = result.get("final_conviction", 0)
    enter = result.get("enter", False)
    print(f"\n  Final conviction: {conviction}/10")

    if enter and all_pass:
        # Half-Kelly position size
        size = _kelly_size(state.get("trade_history", []), rr_calc)

        trade = {
            "id":               state.get("total_trades", 0) + 1,
            "direction":        direction,
            "entry":            entry_val,
            "sl":               sl_val,
            "tp":               tp_val,
            "rr":               rr_calc,
            "conviction":       conviction,
            "size":             size,
            "entry_candle":     m5["timestamp"],
            "inversion_point":  result.get("q2_inversion_point", ""),
            "dominant_branch":  result.get("q1_dominant_branch", ""),
            "first_candle_plan":result.get("q10_minimum_confirmation", ""),
            "m1_verdict":       m1_verdict,
            "bull_rating":      bull_data.get("rating", 0),
            "bear_rating":      bear_data.get("rating", 0),
            "flow_verdict":     flow.get("verdict", "N/A") if flow else "N/A",
            "flow_bias":        flow.get("bias", "n/a") if flow else "n/a",
            "flow_strength":    flow.get("strength", 0) if flow else 0,
            "max_fav":          0.0,
            "max_against":      0.0,
            "is_first_candle":  True,
        }
        display.show_trade_setup(trade)
        print(f"\n  Position Size (Half-Kelly): {size * 100:.0f}% of capital")
        display.block(f"TRADE ENTERED — {direction} {entry_val} | Size: {size*100:.0f}%", "PASS")
        result["trade"] = trade
        result["enter"] = True
    else:
        reason = result.get("no_entry_reason", "Checklist or conviction failed")
        display.block(f"Entry REJECTED — {str(reason)[:150]}", "BLOCK")
        result["enter"] = False

    return result


def _run_debate_parallel(m5, m1_list, recent_candles, signal):
    """Run Bull and Bear agents in parallel using threads directly."""
    import threading

    bull_result = [None]
    bear_result = [None]

    def run_bull():
        bull_result[0] = claude_client.ask_agent(
            "default", _bull_prompt(m5, m1_list, recent_candles, signal), "Door 4 — Bull"
        )

    def run_bear():
        bear_result[0] = claude_client.ask_agent(
            "default", _bear_prompt(m5, m1_list, recent_candles, signal), "Door 4 — Bear"
        )

    t1 = threading.Thread(target=run_bull)
    t2 = threading.Thread(target=run_bear)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    return bull_result[0] or {}, bear_result[0] or {}
