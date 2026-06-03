"""
DOOR 8 — SESSION END
Final report + 4 session reflection questions.
"""

import claude_client
import display


def run(state: dict) -> dict:
    display.door_header(8, "SESSION END — FINAL REPORT")

    history = state.get("trade_history", [])
    wins = sum(1 for t in history if t.get("result") == "WIN")
    losses = len(history) - wins
    total_pips = sum(t.get("result_pips", 0) for t in history)
    win_rate = (wins / len(history) * 100) if history else 0

    print(f"""
  ┌── FINAL SESSION REPORT ──────────────────────────────
  │  Total Trades : {len(history)}
  │  Wins         : {wins}
  │  Losses       : {losses}
  │  Win Rate     : {win_rate:.1f}%
  │  Total Pips   : {total_pips:+.1f}
  └──────────────────────────────────────────────────────""")

    trades_detail = "\n".join([
        f"  #{t.get('id')} {t.get('direction')} {t.get('result','?')} {t.get('result_pips',0):+.1f}pts | "
        f"Branch: {str(t.get('dominant_branch','?'))[:80]}"
        for t in history
    ]) or "No trades."

    prompt = f"""
SESSION COMPLETE.
Total trades: {len(history)} | W:{wins} L:{losses} | Win rate:{win_rate:.1f}% | Pips:{total_pips:+.1f}

Trades:
{trades_detail}

Answer 4 session reflection questions. Buyer/seller language only. No patterns.

Return ONLY this JSON:
{{
  "q1_patterns_across_session": "What buyer/seller patterns repeated across the whole session? Who was consistently strong or weak? Where did the market show its hand most clearly?",
  "q2_reliable_branches": "Which types of possibility branches were most reliable? Which kept getting invalidated? What does this tell you about how buyers/sellers were operating?",
  "q3_thinking_failures": "Where did the thinking process FAIL? Were there moments where you misread buyer/seller intentions? What caused it?",
  "q4_changes_next_session": "What specifically changes for the next session? One real adjustment to how you will read buyers/sellers, enter, or manage trades."
}}
"""

    result = claude_client.ask(prompt, label="Door 8 — Session End")

    print()
    for k, v in result.items():
        if k.startswith("q"):
            print(f"  [{k.upper()}]")
            print(f"  {v}")
            print()

    # Append to ledger
    with open("LEDGER.md", "a") as f:
        f.write(f"\n## SESSION FINAL REPORT\n")
        f.write(f"Trades: {len(history)} | W:{wins} L:{losses} | {win_rate:.1f}% | {total_pips:+.1f}pts\n\n")
        for k, v in result.items():
            if k.startswith("q"):
                f.write(f"**{k}**: {v}\n\n")
        f.write("---\n\n")

    display.block("Session complete. Results written to LEDGER.md", "PASS")
    return result
