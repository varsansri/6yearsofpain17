"""
DOOR 6 — TRADE LOG
4 post-mortem questions. Writes to LEDGER.md including position size.
"""

from pathlib import Path
import claude_client
import display
from prompts import context_block

LEDGER = "LEDGER.md"


def _ensure_ledger():
    p = Path(LEDGER)
    if not p.exists():
        p.write_text(
            "# TRADE LEDGER\n\n"
            "| ID | Date | Dir | Entry | SL | TP | R:R | Size% | Result | Pips | Max Fav | Max Against |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        )


def run(trade: dict, result: str, exit_candle: str,
        recent_candles: list) -> dict:

    display.door_header(6, "TRADE LOG — POST-MORTEM")

    prompt = f"""
{context_block(recent_candles[-10:])}

COMPLETED TRADE:
ID: {trade.get('id')}
Direction: {trade['direction']}
Entry: {trade['entry']} | SL: {trade['sl']} | TP: {trade['tp']} | R:R: {trade.get('rr')}:1
Position size: {trade.get('size', 'N/A')}
Result: {result}
Exit price: {trade.get('exit_price')}
Pips: {trade.get('result_pips', 0):+.1f}
Max favorable: {trade.get('max_fav', 0):.1f}pts
Max against: {trade.get('max_against', 0):.1f}pts
Exit candle: {exit_candle}
Original branch: {trade.get('dominant_branch', '?')}
Inversion point: {trade.get('inversion_point', '?')}
M1 verdict at entry: {trade.get('m1_verdict', 'N/A')}
Bull rating at entry: {trade.get('bull_rating', 'N/A')}/10
Bear rating at entry: {trade.get('bear_rating', 'N/A')}/10
Order flow at entry: {trade.get('flow_verdict', 'N/A')} | bias {trade.get('flow_bias', 'n/a')} | strength {trade.get('flow_strength', 0)}

Write a post-mortem. Buyer/seller terms only. No patterns.

Return ONLY this JSON:
{{
  "q1_branch_result": "What was the branch? Who proved it right or wrong, at which exact level, and how?",
  "q2_why_won_lost": "Why did this trade WIN or LOSE? Full buyer/seller narrative — who was strong, weak, trapped?",
  "q3_inversion_hit": "Did the inversion point get hit before trade closed? What happened at that level?",
  "q4_different": "What would you do differently? One specific change to entry, SL, TP, or branch — and why in buyer/seller terms."
}}
"""

    post = claude_client.ask(prompt, label="Door 6 — Log")

    print()
    for k, v in post.items():
        if k.startswith("q"):
            print(f"  [{k.upper()}]")
            print(f"  {v}")
            print()

    # Write to ledger
    _ensure_ledger()
    entry_date = str(trade.get("entry_candle", "?"))[:10]
    pips = trade.get("result_pips", 0)
    size_pct = f"{trade.get('size', 0) * 100:.0f}%" if trade.get("size") else "N/A"

    row = (
        f"| {trade.get('id')} | {entry_date} | {trade['direction']} "
        f"| {trade['entry']} | {trade['sl']} | {trade['tp']} | {trade.get('rr')}:1 "
        f"| {size_pct} | {result} | {pips:+.1f} "
        f"| {trade.get('max_fav', 0):.1f} | {trade.get('max_against', 0):.1f} |\n"
    )
    with open(LEDGER, "a") as f:
        f.write(row)
        f.write(f"\n**Trade {trade.get('id')} Post-Mortem** ({result}):\n")
        for k, v in post.items():
            if k.startswith("q"):
                f.write(f"- {k}: {v}\n")
        f.write("\n---\n\n")

    display.block(f"Trade {trade.get('id')} logged to LEDGER.md", "PASS")
    post["logged"] = True
    return post
