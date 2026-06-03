"""
DOOR 2 — CANDLE ADVANCE
Agents:
  M5 Sniper  — reads M5 structure, answers q1-q9
  M1 Trigger — reads M1 sub-candles, enriches absorption/trap + timing verdict
Both run in parallel. Results merged into same output structure.
"""

from datetime import datetime
import claude_client
import display
import flow_layer
from prompts import candle_block, context_block, m1_block
import config


def code_checks(m5: dict, state: dict) -> tuple[bool, list]:
    """Hard code checks. Returns (blocked, messages). AI cannot override."""
    messages = []
    blocked = False

    last_ts = state.get("last_timestamp")
    def _ts(v):
        return datetime.fromisoformat(str(v)) if isinstance(v, str) else v
    if last_ts and _ts(m5["timestamp"]) <= _ts(last_ts):
        messages.append(("BLOCK", f"Timestamp not advancing: {m5['timestamp']} ≤ {last_ts}"))
        blocked = True

    if state.get("session_halted"):
        messages.append(("HALT", "Session is HALTED (kill switch active)."))
        blocked = True

    current_day = str(m5["timestamp"])[:10]
    prev_day = state.get("current_day")
    if prev_day and current_day != prev_day:
        daily = state.get("daily_trades", 0)
        if daily < 3:
            messages.append(("WARN", f"Day {prev_day} ended with only {daily} trades (min 3)."))

    return blocked, messages


def run(m5: dict, m1_list: list, recent_candles: list,
        state: dict, presession: dict, tree: list) -> dict:

    display.door_header(2, "CANDLE ADVANCE — M5 SNIPER + M1 TRIGGER + FLOW")
    display.show_candle(m5, m1_list)

    # ── Code checks (unchanged) ───────────────────────────────────────────────
    blocked, messages = code_checks(m5, state)
    for style, msg in messages:
        display.block(msg, style)
    if blocked:
        return {"blocked": True, "messages": messages}

    print()

    # ── Shared context ────────────────────────────────────────────────────────
    presession_summary = "\n".join([
        f"H1 Commander bias    : {presession.get('q9_bias', 'N/A')}",
        f"Direction mandate    : {presession.get('q11_direction_mandate', 'N/A')}",
        f"Expected paths       : {presession.get('q7_matching_path', 'N/A')}",
        f"Mind changer         : {presession.get('q10_mind_changer', 'N/A')}",
    ])

    tree_summary = ""
    if tree:
        tree_summary = "Current possibility tree:\n" + "\n".join(
            [f"  [{b.get('name')}] Confirm:{b.get('confirm')} | Invalidate:{b.get('invalidate')}"
             for b in tree]
        )

    # ── Agent 3 — M5 Sniper prompt ────────────────────────────────────────────
    m5_prompt = f"""
{presession_summary}

{tree_summary}

{context_block(recent_candles)}

CURRENT M5 CANDLE (structure only — no M1 detail, that is another agent's job):
{candle_block(m5)}

You are the M5 SNIPER. Read this M5 candle and its context in pure buyer/seller terms.
Do NOT speculate about M1 sub-candle detail — focus on the M5 body, wicks, and range only.

Return ONLY this JSON:
{{
  "q1_attacker": "Who attacked this M5 candle — buyers or sellers? Evidence from the M5 body size and direction?",
  "q2_winner": "Who WON this M5 candle? Where did price close relative to the high and low? Who has control at the close?",
  "q3_absorption": "From M5 body/wick alone — was there absorption evidence? (Wick into a level, small body, close away from extreme?)",
  "q4_trap": "From M5 structure alone — was there a trap? A break of a level followed by reversal within the same candle?",
  "q5_intention": "What is the M5-level INTENTION? What are buyers/sellers trying to reach from here? Name exact price targets.",
  "q6_buyers_now": "What are BUYERS doing at this M5 close? Strong, weak, defending, retreating, accumulating? Give price evidence.",
  "q7_sellers_now": "What are SELLERS doing at this M5 close? Strong, weak, attacking, distributing, exhausted? Give price evidence.",
  "q8_tree_update": "How does this M5 candle update the possibility tree? Which branches more likely? Which eliminated? Cite prices.",
  "q9_next_scenarios": [
    "Scenario 1: next M5 candle if buyers press higher — what price, what body, what confirms?",
    "Scenario 2: next M5 candle if sellers take control — what price, what body, what confirms?",
    "Scenario 3: next M5 candle if indecision — range, small bodies, what tells you neither side wins?"
  ],
  "blocked": false
}}
"""

    # ── Agent 4 — M1 Trigger prompt ───────────────────────────────────────────
    m1_prompt = f"""
{presession_summary}

{m1_block(m1_list, m5)}

You are the M1 TRIGGER. Read ONLY the M1 sub-candles above.
Your job is to find what the M5 body HIDES — the minute-by-minute battle inside this 5-minute candle.

Return ONLY this JSON:
{{
  "m1_first_mover": "Who attacked FIRST in the M1 candles? What was the first M1 body's direction and size? Did it hold or reverse?",
  "m1_absorption": "Was there M1 absorption? Multiple M1 candles pushing into a level with wicks — then stalling? Who was absorbing whom?",
  "m1_trap": "Was there an M1 trap? A break that failed — weak hands entered then price reversed hard? Name the exact M1 candle and price.",
  "m1_momentum": "Is M1 momentum REAL or FADING? Are bodies getting larger (real) or smaller (fading)? Which side is losing steam?",
  "m1_verdict": "CLEAN / WAIT / ABORT — is this a clean M1 structure for entry, wait for more information, or abort the trade idea? One word only.",
  "m1_reason": "One sentence explaining your M1 verdict with specific prices."
}}
"""

    # ── Agent panel: M5 Sniper + M1 Trigger (Flow Reader runs in main.py background) ──
    calls = [("m5_sniper", m5_prompt, "Door 2 — M5 Sniper")]
    if m1_list:
        calls.append(("m1_trigger", m1_prompt, "Door 2 — M1 Trigger"))

    if len(calls) > 1:
        parallel = claude_client.ask_parallel(calls)
        result = parallel["m5_sniper"]
    else:
        result = claude_client.ask_agent("m5_sniper", m5_prompt, "Door 2 — M5 Sniper")
        parallel = {"m5_sniper": result}

    # M1 Trigger merge (unchanged behavior)
    if "m1_trigger" in parallel:
        m1res = parallel["m1_trigger"]
        result["m1_verdict"]     = (m1res.get("m1_verdict") or "CLEAN").upper().strip()
        result["m1_reason"]      = m1res.get("m1_reason", "")
        result["m1_first_mover"] = m1res.get("m1_first_mover", "")
        result["m1_absorption"]  = m1res.get("m1_absorption", "")
        result["m1_trap"]        = m1res.get("m1_trap", "")
        result["m1_momentum"]    = m1res.get("m1_momentum", "")
    else:
        result["m1_verdict"]     = "CLEAN"
        result["m1_reason"]      = "No M1 sub-candle data for this M5 — not blocking"
        result["m1_first_mover"] = ""
        result["m1_momentum"]    = ""

    # Flow Reader merge (NEW — stored under "flow" for Door 3/4 to reuse)
    result["flow"] = parallel.get("flow_reader", {}) or {}

    # Verdict must be a known token; anything unexpected falls back to non-blocking
    if result["m1_verdict"] not in ("CLEAN", "WAIT", "ABORT"):
        result["m1_verdict"] = "CLEAN"
    result["blocked"] = False

    display.show_answers({k: v for k, v in result.items() if k.startswith("q")})
    print(f"\n  M1 Trigger: {result['m1_verdict']} — {str(result.get('m1_reason',''))[:160]}")
    if result["flow"]:
        fl = result["flow"]
        print(f"  Flow Reader: {fl.get('flow_verdict','N/A')} | bias {fl.get('flow_bias','?')} | "
              f"strength {fl.get('flow_strength','?')} — {str(fl.get('flow_note',''))[:140]}")
    return result
