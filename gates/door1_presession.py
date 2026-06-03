"""
DOOR 1 — PRE-SESSION
Agent: H1 Commander (strategic layer)
Reads H4 + H1 only — no M5 noise.
12 questions: context (4), possibilities (4), self-awareness (4)
Run ONCE at the start of each session/day.
"""

import claude_client
import display
from prompts import h1_block


def run(h4_candles: list, h1_candles: list) -> dict:
    display.door_header(1, "PRE-SESSION — H1 COMMANDER (12 QUESTIONS)")

    context = h1_block(h4_candles, h1_candles)

    prompt = f"""
{context}

You are the H1 COMMANDER. You read ONLY H4 and H1 data.
Your job is to set the strategic mandate for the session before any M5 candle is seen.
Answer these 12 questions to establish context, bias, and possible paths.

Return ONLY this JSON:
{{
  "q1_buyers_yesterday": "What specifically did BUYERS do on H4/H1 yesterday? Which exact price levels did they defend, attack, or lose? What was their final position?",
  "q2_sellers_yesterday": "What specifically did SELLERS do on H4/H1 yesterday? Which exact price levels did they defend, attack, or lose? What was their final position?",
  "q3_current_control": "Who controls RIGHT NOW at the H1 level? Give specific evidence — H1 bodies, wicks, closes at specific prices.",
  "q4_battle_levels": "List 2-4 key H4/H1 battle levels. For each: exact price, who won the battle there, and what immediately followed that win.",
  "q5_possible_paths": ["H4/H1 path 1 — full story with prices", "H4/H1 path 2 — full story with prices", "H4/H1 path 3 — full story with prices"],
  "q6_confirm_invalidate": [
    {{"path": "path name", "confirm": "exact H1 candle action that confirms this path", "invalidate": "exact H1 price/close that kills this path"}},
    {{"path": "path name", "confirm": "...", "invalidate": "..."}}
  ],
  "q7_matching_path": "Which path matches what buyers/sellers have been ACTUALLY doing on H4/H1 most recently? Cite specific candles and prices.",
  "q8_counter_intuitive_path": "What is the H4/H1 path most people are NOT watching? What exact price action would trigger it?",
  "q9_bias": "What H4/H1 bias do you currently have? Are you favoring evidence that supports one side? Be brutally honest.",
  "q10_mind_changer": "What EXACT H1 candle close or H4 price level would completely change your current view?",
  "q11_direction_mandate": "State your direction mandate clearly: BULLISH / BEARISH / NEUTRAL at the H4/H1 level, and the exact price that would flip it.",
  "q12_h1_blind_spot": "What are you NOT seeing clearly enough in the H4/H1 data? Which candle or zone deserves more attention and why?"
}}
"""

    result = claude_client.ask_agent("h1_commander", prompt, label="Door 1 — H1 Commander")

    display.show_answers({k: v for k, v in result.items() if k.startswith("q")})
    display.block("Door 1 PASSED — H1 Commander mandate established", "PASS")
    return result
