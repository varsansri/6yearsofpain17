"""
ORDER FLOW LAYER — additive enhancement for the existing doors.

This module owns ALL the new flow logic so the doors only need a small guarded hook.
It never touches existing behavior; when config.ORDERFLOW_ENABLED is False nothing here runs.

Provides:
  build_prompt(of_current, of_recent)      -> Flow Reader question prompt (Agent 5)
  normalize(flow_raw)                       -> {verdict, bias, strength}
  conviction_modifier(flow, direction)     -> float to add/subtract from conviction
  veto(flow, direction)                     -> (blocked: bool, reason: str)
  exit_signal(flow, direction)              -> (exit: bool, reason: str)
"""
import config
from prompts import orderflow_block


def build_prompt(of_current: dict, of_recent: list = None) -> str:
    """The Flow Reader's own 8 thinking questions."""
    return f"""
{orderflow_block(of_current, of_recent)}

You are the FLOW READER. Read ONLY the order flow above. Decide if the move is REAL or a TRAP,
and who the tape says is actually in control. Buyer/seller + flow language only, with exact numbers.

Return ONLY this JSON:
{{
  "q1_aggressor": "Who is hitting the tape right now — buyers or sellers? Quote the delta and delta%.",
  "q2_confirm_or_diverge": "Does delta CONFIRM the candle's close direction, or DIVERGE from it? If price rose on negative delta (or fell on positive delta), say TRAP and explain.",
  "q3_absorption": "Was aggressive volume ABSORBED (heavy delta but price barely moved)? Who absorbed whom, and who likely wins next?",
  "q4_whale": "Was there whale / large-trade activity? Which side? Are big players accumulating or distributing? Quote whale_vol and largest trade.",
  "q5_poc_footprint": "Where did volume concentrate (POC)? Was the POC buy-heavy or sell-heavy? Is price accepting or rejecting that level?",
  "q6_cum_campaign": "What is cumulative delta doing over the recent bars? Is the underlying campaign bullish or bearish regardless of the last candle?",
  "q7_exhaustion": "Is aggression FADING (delta shrinking while price still moves)? Any exhaustion / reversal warning?",
  "flow_verdict": "ONE token: BUY_FLOW | SELL_FLOW | ABSORPTION_REVERSAL | EXHAUSTION | NEUTRAL",
  "flow_bias": "ONE token: bullish | bearish | neutral",
  "flow_strength": 0,
  "flow_note": "one sentence: what the tape is really telling us right now, with exact numbers"
}}
flow_strength: 1-10 (1 = no real conviction on the tape, 10 = overwhelming one-sided aggression).
"""


def normalize(flow_raw: dict) -> dict:
    """Coerce the agent's flow answer into a clean {verdict, bias, strength} dict."""
    if not flow_raw:
        return {"verdict": "NEUTRAL", "bias": "neutral", "strength": 0.0, "note": ""}
    try:
        strength = float(flow_raw.get("flow_strength", 0) or 0)
    except (TypeError, ValueError):
        strength = 0.0
    return {
        "verdict":  str(flow_raw.get("flow_verdict", "NEUTRAL")).upper().strip(),
        "bias":     str(flow_raw.get("flow_bias", "neutral")).lower().strip(),
        "strength": strength,
        "note":     flow_raw.get("flow_note", ""),
    }


def _aligns(bias: str, direction: str) -> int:
    """+1 if flow bias supports the trade direction, -1 if it opposes, 0 if neutral."""
    d = (direction or "").upper()
    if bias == "bullish":
        return 1 if d == "LONG" else (-1 if d == "SHORT" else 0)
    if bias == "bearish":
        return 1 if d == "SHORT" else (-1 if d == "LONG" else 0)
    return 0


def conviction_modifier(flow: dict, direction: str) -> float:
    """How much the Flow Reader adds to / subtracts from conviction."""
    align = _aligns(flow.get("bias", "neutral"), direction)
    strength = flow.get("strength", 0.0)
    if align > 0:
        return round(min(config.FLOW_BOOST_MAX, max(0.0, (strength - 5) * 0.5)), 2)
    if align < 0:
        return round(-min(config.FLOW_PENALTY_MAX, max(0.0, (strength - 5) * 0.6)), 2)
    return 0.0


def veto(flow: dict, direction: str) -> tuple:
    """Block an entry if the tape strongly opposes it (don't trade into a wall)."""
    if _aligns(flow.get("bias", "neutral"), direction) >= 0:
        return False, ""
    strength = flow.get("strength", 0.0)
    verdict = flow.get("verdict", "NEUTRAL")
    if strength >= config.FLOW_VETO_STRENGTH or verdict in ("ABSORPTION_REVERSAL", "EXHAUSTION"):
        return True, (f"Order flow opposes {direction}: {verdict} "
                      f"(bias {flow.get('bias')}, strength {strength:.0f}) — {flow.get('note','')}")
    return False, ""


def exit_signal(flow: dict, direction: str) -> tuple:
    """For an OPEN trade: exit if the tape has flipped hard against the position."""
    blocked, reason = veto(flow, direction)
    return blocked, (reason.replace("opposes", "flipped against") if blocked else "")
