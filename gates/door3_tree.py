"""
DOOR 3 — POSSIBILITY TREE
Agents:
  M5 Sniper  — builds full possibility tree from M5 context
  M15 Scout  — reads M15 momentum and confirms/challenges branches
Both run in parallel. Python synthesises their outputs — no extra Gemini call.
"""

import claude_client
import display
import config
import flow_layer
from prompts import candle_block, context_block, m15_block


def run(m5: dict, m1_list: list, recent_candles: list,
        d2_analysis: dict, state: dict, presession: dict,
        m15_candles: list = None, required_conviction: float = 7,
        poi_ctx: str = "") -> dict:

    display.door_header(3, "POSSIBILITY TREE — M5 SNIPER + M15 SCOUT")

    m15_candles = m15_candles or []

    # ── Shared context ────────────────────────────────────────────────────────
    d2_summary = (
        f"- Attacker   : {d2_analysis.get('q1_attacker', '?')}\n"
        f"- Winner     : {d2_analysis.get('q2_winner', '?')}\n"
        f"- Absorption : {d2_analysis.get('q3_absorption', '?')}\n"
        f"- Trap       : {d2_analysis.get('q4_trap', '?')}\n"
        f"- Intention  : {d2_analysis.get('q5_intention', '?')}\n"
        f"- Buyers now : {d2_analysis.get('q6_buyers_now', '?')}\n"
        f"- Sellers now: {d2_analysis.get('q7_sellers_now', '?')}\n"
        f"- M1 verdict : {d2_analysis.get('m1_verdict', 'N/A')} — {d2_analysis.get('m1_reason', '')}\n"
    )

    mandate = presession.get("q11_direction_mandate", "N/A")
    mind_changer = presession.get("q10_mind_changer", "N/A")
    active_trade = (
        "YES — direction: " + state["active_trade"]["direction"]
        if state.get("active_trade") else "None"
    )

    # ── Agent 3 — M5 Sniper: build possibility tree ───────────────────────────
    m5_prompt = f"""
H1 Commander mandate: {mandate}
Pre-session mind-changer: {mind_changer}
Active trade: {active_trade}

{context_block(recent_candles)}

CURRENT CANDLE:
{candle_block(m5)}

DOOR 2 CANDLE ANALYSIS:
{d2_summary}
{(chr(10) + poi_ctx + chr(10)) if poi_ctx else ""}
You are the M5 SNIPER. Build the possibility tree from M5 structure only.
Anchor your branches to the POINTS OF INTEREST above — that is where buyers/sellers will
react. Respect the reaction guide: a CLEAN poi favors a clean bounce/rejection branch; a
FIGHT poi favors a liquidity-grab / trap branch, not a tidy reaction.
Minimum 3 branches, maximum 4. Always include a counter-intuitive branch.
Do NOT use pattern names. Think ONLY in buyer/seller behavior with exact prices.

After building the tree, assess if an entry opportunity exists RIGHT NOW.
Entry exists when: one branch is dominant, price is at a POI, conviction ≥ 7/10.

Return ONLY this JSON:
{{
  "branches": [
    {{
      "name": "branch name in buyer/seller terms",
      "direction": "bullish|bearish|sideways",
      "buyer_seller_story": "full buyer/seller narrative with exact prices",
      "confirm": "exact price action that confirms this branch",
      "invalidate": "exact price or candle close that kills this branch",
      "target": "price target if this branch plays out"
    }}
  ],
  "dominant_branch": "which branch is currently most likely and WHY with price evidence",
  "branches_remaining": 0,
  "entry_signal": {{
    "exists": false,
    "direction": null,
    "entry_level": null,
    "sl_level": null,
    "tp_level": null,
    "poi_description": "describe the POI level",
    "conviction": 0,
    "reasoning": "buyer/seller reasoning for this entry"
  }}
}}
"""

    # ── Agent 2 — M15 Scout: momentum confirmation ────────────────────────────
    m15_prompt = f"""
H1 Commander mandate: {mandate}
Active trade: {active_trade}

{m15_block(m15_candles)}

You are the M15 SCOUT. Read ONLY the M15 candles above.
Your job: assess momentum state on M15, confirm or challenge the H1 mandate,
and identify if M15 is approaching, at, or leaving a key battle zone.

Return ONLY this JSON:
{{
  "m15_control": "buyers|sellers|neutral",
  "m15_energy": "expanding|compressing|exhausting|waiting",
  "m15_direction": "bullish|bearish|sideways",
  "m15_nearest_level": "price of the nearest M15 battle level with evidence",
  "m15_confirms_h1": true,
  "m15_conflict": false,
  "m15_note": "one sentence: what is M15 telling us right now with specific prices"
}}
"""

    # ── Run both in parallel ──────────────────────────────────────────────────
    parallel_results = claude_client.ask_parallel([
        ("m5_sniper",  m5_prompt,  "Door 3 — M5 Sniper Tree"),
        ("m15_scout",  m15_prompt, "Door 3 — M15 Scout"),
    ])

    tree_result = parallel_results["m5_sniper"]
    m15_result  = parallel_results["m15_scout"]

    # ── Python synthesis — adjust conviction based on M15 alignment ───────────
    entry = tree_result.get("entry_signal", {})
    m15_dir = m15_result.get("m15_direction", "sideways")
    m15_conflict = m15_result.get("m15_conflict", False)
    m15_confirms = m15_result.get("m15_confirms_h1", True)

    if entry.get("exists"):
        entry_dir = (entry.get("direction") or "").lower()
        conviction = float(entry.get("conviction", 0))

        if m15_dir == "sideways":
            conviction = max(0, conviction - 0.5)
            entry["conviction_note"] = "M15 neutral — conviction trimmed -0.5"
        elif (entry_dir in ("long", "bullish") and m15_dir == "bearish") or \
             (entry_dir in ("short", "bearish") and m15_dir == "bullish"):
            conviction = max(0, conviction - 1.5)
            entry["conviction_note"] = f"M15 CONFLICT ({m15_dir}) — conviction trimmed -1.5"
            m15_conflict = True
        else:
            entry["conviction_note"] = f"M15 aligned ({m15_dir}) — conviction unchanged"

        entry["conviction"] = round(conviction, 1)

        # ── Order-flow conviction modifier (ADDITIVE — runs after the M15 step) ──
        if config.ORDERFLOW_ENABLED:
            flow = flow_layer.normalize(d2_analysis.get("flow", {}))
            dir_norm = "LONG" if entry_dir in ("long", "bullish", "buy") else \
                       ("SHORT" if entry_dir in ("short", "bearish", "sell") else "")
            mod = flow_layer.conviction_modifier(flow, dir_norm)
            if mod:
                conviction = max(0, conviction + mod)
                entry["flow_note"] = (f"Flow {flow['verdict']} ({flow['bias']}, "
                                      f"str {flow['strength']:.0f}) → conviction {mod:+.1f}")
            entry["flow_norm"] = flow
            entry["conviction"] = round(conviction, 1)

        if conviction < required_conviction:
            entry["exists"] = False

    tree_result["entry_signal"] = entry
    tree_result["m15_read"] = m15_result

    # ── Display ───────────────────────────────────────────────────────────────
    display.show_tree(tree_result.get("branches", []))

    dominant = tree_result.get("dominant_branch", "")
    if dominant:
        print(f"\n  Dominant: {dominant}")

    remaining = tree_result.get("branches_remaining", 99)
    print(f"\n  Branches remaining: {remaining}")
    print(f"  M15: {m15_result.get('m15_direction','?').upper()} | "
          f"{m15_result.get('m15_energy','?')} | "
          f"{m15_result.get('m15_note','')}")

    sig = tree_result.get("entry_signal", {})
    if sig.get("exists") and not state.get("active_trade"):
        display.block(
            f"ENTRY SIGNAL — {sig.get('direction')} | "
            f"Entry:{sig.get('entry_level')} SL:{sig.get('sl_level')} TP:{sig.get('tp_level')} "
            f"Conviction:{sig.get('conviction')}/10 | {sig.get('conviction_note','')}"
            + (f" | {sig.get('flow_note','')}" if sig.get('flow_note') else ""),
            "PASS"
        )
    else:
        display.block("No entry signal — continuing to watch", "INFO")

    return tree_result
