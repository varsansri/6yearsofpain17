"""
DOOR 0 — BOOTSTRAP / OVERALL MAP (Ideas 1, 2, 3, 4, 5)

Runs BEFORE the session and at each new cycle. Two jobs:

1. Re-anchor the OVERALL IDEOLOGY so the system never drifts into pattern-recognition
   or its own structure (Idea 5). Structure → POI → aligned buyer/seller reading.

2. WARM START (Idea 3): never enter a session blind. Gather the previous period's data
   (higher-TF structure + the dual-scored POI map) and run the DIRECTION story engine
   (the Cartographer) — the gather→narrow→story process the vision wanted for Direction,
   not just Entry (Idea 2 gap). Produces a "cycle map": overall control, the POIs that
   matter this cycle, and 2-4 possible stories (the funnel seed). Carried forward in state.

Agent: Cartographer (strategic, reads H4/H1 + POI map). Deterministic gather, one AI call.
"""

import claude_client
import display
import poi_engine
from prompts import h1_block


IDEOLOGY = (
    "OVERALL IDEOLOGY (re-anchor every cycle):\n"
    "  1. STRUCTURE first, then POINTS OF INTEREST, then aligned candle-by-candle reading.\n"
    "  2. Top-down: higher timeframe lays the map; lower timeframe only executes against it.\n"
    "  3. Think ONLY in buyers vs sellers — never patterns, indicators, or 'the trend'.\n"
    "  4. POIs are reaction zones, dual-scored (structural validity + crowd attention).\n"
    "  5. Gather data → narrow the story space in stages → only act when narrowed enough.\n"
)


def run(m5_data: list, idx: int, poi_map: list, state: dict) -> dict:
    display.door_header(0, "BOOTSTRAP — OVERALL MAP (CARTOGRAPHER)")
    print(IDEOLOGY)

    price = m5_data[idx]["close"]
    h4c, h1c = __import__("data_loader").get_h1_context(m5_data, idx, n=12)
    htf_ctx = h1_block(h4c, h1c)
    poi_ctx = poi_engine.map_block(poi_map, price, top=10)

    prev = state.get("cycle_map", {})
    prev_line = ""
    if prev:
        prev_line = (f"\nPREVIOUS CYCLE MAP (carry forward — confirm or revise it):\n"
                     f"  control: {prev.get('overall_control','?')}\n"
                     f"  direction: {prev.get('direction','?')}\n"
                     f"  watch: {prev.get('what_to_watch','?')}\n")

    prompt = f"""
{IDEOLOGY}
{htf_ctx}

{poi_ctx}
{prev_line}
You are the CARTOGRAPHER. Draw the overall map for THIS cycle from the higher timeframes
and the POI map above. Do not trade. Lay out the picture the session will navigate by.

Return ONLY this JSON:
{{
  "overall_control": "Who controls the macro battle right now — buyers or sellers? Exact H4/H1 price evidence.",
  "direction": "BULLISH | BEARISH | NEUTRAL",
  "key_pois": [
    "POI price + why it matters THIS cycle (its reaction type + who defends it)",
    "second POI ...",
    "third POI ..."
  ],
  "stories": [
    {{"name": "story 1 name", "story": "buyer/seller narrative with prices", "confirm": "exact price action that confirms", "invalidate": "exact price that kills it"}},
    {{"name": "story 2 name", "story": "...", "confirm": "...", "invalidate": "..."}},
    {{"name": "counter-intuitive story", "story": "the path most are NOT watching", "confirm": "...", "invalidate": "..."}}
  ],
  "what_to_watch": "The single thing that will tip which story wins — with the exact price."
}}
"""

    cmap = claude_client.ask_agent("cartographer", prompt, label="Door 0 — Cartographer")

    # Display
    print(f"\n  Overall control : {cmap.get('overall_control','?')}")
    print(f"  Direction       : {cmap.get('direction','?')}")
    print(f"  Watch           : {cmap.get('what_to_watch','?')}")
    print("\n  KEY POIs this cycle:")
    for kp in cmap.get("key_pois", []):
        print(f"    • {kp}")
    print("\n  POSSIBLE STORIES (the funnel seed):")
    for s in cmap.get("stories", []):
        print(f"    [{s.get('name','?')}] {str(s.get('story',''))[:160]}")
        print(f"        confirm: {str(s.get('confirm',''))[:100]} | invalidate: {str(s.get('invalidate',''))[:100]}")

    state["cycle_map"] = cmap
    display.block("Door 0 — cycle map drawn, warm seed established", "PASS")
    return cmap


def summary(cmap: dict) -> str:
    """Concise cycle-map context line to seed Door 1 / Door 3 (so they aren't blind)."""
    if not cmap:
        return ""
    stories = " || ".join(s.get("name", "?") for s in cmap.get("stories", []))
    return (
        "CYCLE MAP (from Door 0 Cartographer — the overall plan to align with):\n"
        f"  control: {cmap.get('overall_control','?')}\n"
        f"  direction: {cmap.get('direction','?')} | watch: {cmap.get('what_to_watch','?')}\n"
        f"  live stories: {stories}"
    )
