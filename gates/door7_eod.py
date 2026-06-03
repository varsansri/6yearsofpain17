"""
DOOR 7 — END OF DAY
Kill switch check. 5 reflection questions.
"""

import claude_client
import display
import config


def run(day: str, daily_trades: int, day_history: list, state: dict) -> dict:
    display.door_header(7, f"END OF DAY — {day}")

    # --- KILL SWITCH ---
    consec = state.get("consecutive_losses", 0)
    if consec >= config.KILL_SWITCH_LOSSES:
        display.block(
            f"KILL SWITCH TRIGGERED — {consec} consecutive losses. Session HALTED.",
            "HALT"
        )
        return {"kill_switch": True, "reflections": {}}

    # --- TRADE COUNT CHECK ---
    if daily_trades < 3:
        display.block(
            f"Only {daily_trades} trades today (minimum 3). "
            f"Pass --force to end day anyway, or continue watching.",
            "WARN"
        )

    # Build day summary
    wins = sum(1 for t in day_history if t.get("result") == "WIN")
    losses = len(day_history) - wins
    total_pips = sum(t.get("result_pips", 0) for t in day_history)

    trades_summary = "\n".join([
        f"  Trade {t.get('id')}: {t.get('direction')} {t.get('entry')} → {t.get('exit_price', '?')} "
        f"[{t.get('result', '?')}] {t.get('result_pips', 0):+.1f}pts"
        for t in day_history
    ]) or "  No trades today."

    prompt = f"""
Day: {day}
Trades taken: {daily_trades} (W:{wins} L:{losses})
Total pips: {total_pips:+.1f}
Consecutive losses: {consec}

Trades:
{trades_summary}

Answer 5 end-of-day reflection questions in buyer/seller terms. No patterns.

Return ONLY this JSON:
{{
  "q1_dominant_dynamic": "What was the dominant buyer/seller dynamic TODAY? Who controlled the session and why?",
  "q2_session_control": "Who controlled most of the session — buyers or sellers? What was the key turning point (if any)?",
  "q3_key_battles": "Where were the key battles today? For each: who fought, who won, what followed immediately after?",
  "q4_learned": "What did you learn today about how buyers and sellers are behaving in this market right now?",
  "q5_differently": "What would you do differently tomorrow? One specific change to how you read buyers/sellers or manage entries."
}}
"""

    result = claude_client.ask(prompt, label="Door 7 — EOD")

    print()
    for k, v in result.items():
        print(f"  [{k.upper()}]")
        print(f"  {v}")
        print()

    print(f"  Day summary: {wins}W {losses}L | {total_pips:+.1f}pts")
    display.block(f"Day {day} closed", "PASS")
    result["kill_switch"] = False
    return result
