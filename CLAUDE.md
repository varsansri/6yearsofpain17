# 6YEARSOFPAIN — Project Context for Claude

## What This Is
Candle-by-candle BTC trading backtester. Gemini 2.5 Flash is the brain.
Door 0 + 8-door gate system. No patterns. Pure buyers vs sellers language.
GitHub (public): https://github.com/varsansri/6yearsofpain17 · phone backup: /sdcard/6yearsofpain17_backup/

## Current State (as of 2026-06-03)
- **6-agent** system + 3 analytical engines (Direction, POI, Entry) + stage funnel
- Gemini Flash via Google account auth (GOOGLE_GENAI_USE_GCA=1)
- Target: 30 trades total, 24/day max · conviction floor 6 (flow on)
- M1 data: available and active (M1 Trigger enabled)
- H1/H4/M15: built backward from M5 with NO future leak (in-progress candle only up to now)
- Order Flow: active for 2025-06-17 (288 bars, Binance spot aggTrades IST), 5-min only
- POI engine + stage funnel + Door 0 warm-start all live (behind config switches)

## ⭐ THE VISION (founder's, captured in IDEAS.md — read it)
The project is really **3 gather→narrow→story engines + execution**, not just an entry machine:
1. **DIRECTION** (Door 0 Cartographer + Door 1) — overall picture from higher TFs.
2. **POI** (poi_engine.py) — THE keystone. Dual-scored reaction zones. POI matters most.
3. **ENTRY** (Doors 2-4 + stage funnel + order flow) — 15m→5m→1m execution.
Core rules: structure first → POI → aligned candle reading; top-down; buyer/seller language
ONLY (no patterns/indicators/"trend"); narrow the story space in stages, act only when narrowed;
measure quality with numbers but give the AI room to say "unclear" instead of faking (Idea 5).
IDEAS.md holds Ideas 1-6 verbatim incl. the dual-score measurement layer (Idea 6).

## BUILD HISTORY — 2026-06-03 (this session's major work)
Diagnosis: the project had drifted — Direction was a once/day text dump, POI barely existed,
~90% of engineering was in Entry, higher-TF reads leaked the future. Fixed in 4 steps:
1. **Future-candle leak** → `data_loader._agg_tail` builds higher-TF context BACKWARD from the
   current M5 idx; most recent candle is in-progress (close==current M5 close). Verified no leak.
2. **POI engine** (`poi_engine.py`) → persistent dual-scored map (structural + crowd → CLEAN/
   QUIET/FIGHT/IGNORE), no-leak swings, side flips live, armed near price. Injected into D1/3/4.
3. **Door 0 + warm-start** (`gates/door0_bootstrap.py`, Cartographer agent) → draws the cycle
   map (control/direction/key_pois/stories/what_to_watch), seeds D1/3/4; run.sh resumes warm
   (no candle-0 reset). Gives Direction its own story engine.
4. **Stage funnel** (`stage_funnel.py`) → hour = 4×15-min; narrow 1→3; Door 4 entry only in
   stage 4 (Door 5 management every candle).
All additive behind switches (POI_ENABLED, STAGE_FUNNEL_ENABLED, ORDERFLOW_ENABLED).
Each shipped as its own git commit + phone backup. Verification run from candle 272 still pending.

## CRITICAL BUG — FIXED 2026-06-03
Door 4 checklist item `h1_h4_aligned` used to ALWAYS FAIL (no h1/h4 data),
blocking every trade entry. **Fixed** in `gates/door4_entry.py`:

Pre-verified items (computed in Python, enforced after AI call so Gemini cannot override):
- `h1_h4_aligned` → True (Gate 2 H1 Commander veto already enforces direction)
- `m1_trigger_not_abort` → CLEAN/WAIT pass (Gate 3 already blocks ABORT)
- `trades_today_ok` / `total_trades_ok` → from Gate 1 hard limits
- `not_news_blackout` → True (no news feed)
- `order_flow_confirms` → PRE-VERIFIED (opposing flow already vetoed at Gate 2.5)

## 6-Agent Architecture
| Agent | Timeframe | Role | Where Used |
|-------|-----------|------|-----------|
| Cartographer | H4+H1+POI | Draws cycle map, warm-start, Direction story engine | Door 0 |
| H1 Commander | H4 + H1 | Strategic mandate, veto power | Door 1 |
| M15 Scout | M15 | Tactical momentum, conviction trim | Door 3 |
| M5 Sniper | M5 | Structure, setup, entry signal, stage-aware tree | Door 2, 3, 4 |
| M1 Trigger | M1 | Execution timing, sub-candle reads | Door 2, 4, 5 |
| Flow Reader | Order Flow | Real intent: delta, absorption, whale, POC | Background thread |
(+ Bull & Bear debate agents inside Door 4, using the `default` system prompt.)

## CRITICAL BUG — FIXED 2026-06-03
Door 4 checklist item `h1_h4_aligned` used to ALWAYS FAIL (no h1/h4 data),
blocking every trade entry. **Fixed** in `gates/door4_entry.py`:

Pre-verified items (computed in Python, enforced after AI call so Gemini cannot override):
- `h1_h4_aligned` → True (Gate 2 H1 Commander veto already enforces direction)
- `m1_trigger_not_abort` → CLEAN/WAIT pass (Gate 3 already blocks ABORT)
- `trades_today_ok` / `total_trades_ok` → from Gate 1 hard limits
- `not_news_blackout` → True (no news feed)
- `order_flow_confirms` → PRE-VERIFIED (opposing flow already vetoed at Gate 2.5)

## 5-Agent Architecture
| Agent | Timeframe | Role | Where Used |
|-------|-----------|------|-----------|
| H1 Commander | H4 + H1 | Strategic mandate, veto power | Door 1 |
| M15 Scout | M15 | Tactical momentum, conviction trim | Door 3 |
| M5 Sniper | M5 | Structure, setup, entry signal | Door 2, 3, 4 |
| M1 Trigger | M1 | Execution timing, sub-candle reads | Door 2, 4, 5 |
| Flow Reader | Order Flow | Real intent: delta, absorption, whale, POC | Background thread |

## Order Flow Layer (ADDITIVE — 2026-06-03)
Everything behind `config.ORDERFLOW_ENABLED`. Off = byte-for-byte original behavior.

### What Flow Reader sees (per M5 candle)
delta, cum_delta, buy/sell vol+trades, whale_vol_5btc, max_trade, poc_price,
footprint_top3, absorption flag — 25 columns from Binance spot aggTrades IST.

### Flow hooks per door
- **Door 2**: Flow Reader starts as background thread at candle TOP (before Door 2 runs)
- **Door 3**: flow conviction modifier after M15 trim (±2.5 max boost/penalty)
- **Door 4**: Gate 2.5 flow veto (blocks into walls) + `order_flow_confirms` checklist
- **Door 5**: flow exit_signal — forces early exit if tape flips hard against trade
- **Door 6**: logs flow_verdict, flow_bias, flow_strength to LEDGER.md post-mortem

### Flow threading fix (2026-06-03)
Flow Reader used to run inside Door 2's `ask_parallel()` — blocked everything for 90s.
**Fixed**: Flow Reader now starts in a dedicated `_FlowPool(max_workers=1)` background
thread at the TOP of each candle, before Door 2 runs. Doors 2→3 take ~40-50s.
By the time Door 4 needs flow, it has been running 40-50s — waits ~10-20s more.
Flow ALWAYS completes. No skip. No timeout.

### Locked decisions
1. Flow VETO = YES (blocks trades into absorption/divergence walls)
2. Flow BOOST = YES (adds conviction, dual role)
3. Conviction floor = 6 (lowered from 7, NEVER below 6, full Half-Kelly size always)
4. Per-clock-hour: take best ≥6 setup each hour (flow boost counts). If nothing hits 6, 0 trades that hour. Do NOT force sub-6.
5. Kill switch: 5 consecutive losses → halt day
6. ORDERFLOW_ENABLED kill switch preserved (off = original behavior)

## Stage Funnel (Idea 2 — built 2026-06-03, behind config.STAGE_FUNNEL_ENABLED)
Each clock hour = 4×15-min stages; the story space narrows stage by stage:
- Stage 1 (:00-:14) GATHER & NARRATE · Stage 2 (:15-:29) NARROW + ADD-MISSED ·
  Stage 3 (:30-:44) NARROW HARD · Stage 4 (:45-:59) COMMIT.
- NEW entries (Door 4) are ONLY attempted in the entry stage (config.ENTRY_STAGE=4).
  Trade management (Door 5) still runs every candle.
- stage_funnel.py: stage_of(), entry_allowed(), guidance(). Guidance is appended to
  Door 3's context so the M5 Sniper narrows per stage. Pure Python, nothing to fake.

## Door 0 — Bootstrap / Overall Map (built 2026-06-03)
Runs once per day BEFORE Door 1. Agent: **Cartographer** (strategic, reads H4/H1 + POI map).
- Re-anchors the OVERALL IDEOLOGY each cycle (structure→POI→aligned reading, buyer/seller only).
- WARM START (Idea 3): never enter blind — gathers prior higher-TF + POI map and runs the
  DIRECTION story engine (gather→narrow→story) the vision wanted for Direction, not just Entry.
- Produces a **cycle_map**: overall_control, direction, key_pois, 2-4 stories (funnel seed),
  what_to_watch. Stored in state["cycle_map"], carried forward, seeds Door 1/3/4 via summary().
- gates/door0_bootstrap.py. run.sh no longer resets to candle 0 (resumes warm).

## POI Engine (keystone — built 2026-06-03, behind config.POI_ENABLED)
Persistent, deterministic, NO-LEAK map of Points of Interest across 4H/1H/15m.
Each POI carries TWO scores (Idea 6 measurement layer):
- **structural_score** 0-10 — multi-TF alignment (how many TFs see it) + rejection strength
- **crowd_score** 0-10 — focal/attention (round numbers, prior day/week H-L) — PURE PYTHON, unfakeable
Derived **reaction_type**: CLEAN / QUIET / FIGHT / IGNORE (aligned=clean, conflict=FIGHT/liquidity-grab).
Rebuilt each clock hour, "armed" when price within POI_ARM_BAND_PTS, side flips live vs price.
Injected as context into Door 1 (direction), Door 3 (tree branches), Door 4 (entry).
See IDEAS.md (Ideas 1,2,4,6) for the vision. Future-leak fix lives in data_loader._agg_tail.

## Config Values
```python
ORDERFLOW_ENABLED   = True
REQUIRED_CONVICTION = 6        # lowered from 7
FLOW_BOOST_MAX      = 2.0
FLOW_PENALTY_MAX    = 2.5
FLOW_VETO_STRENGTH  = 7
MAX_DAILY_TRADES    = 24       # raised from 3
MAX_TOTAL_TRADES    = 30       # raised from 10
```

## File Map
```
main.py              — main loop, TeeLogger, bg flow thread, POI build/arm, stage funnel, Door 0/hour
config.py            — all constants (OF, POI, stage funnel)
claude_client.py     — ask(), ask_agent(), ask_parallel(); 6 agents registered incl. cartographer
data_loader.py       — _agg_tail() NO-LEAK higher-TF, get_h1_context/get_m15_context(m5,idx),
                       load_orderflow(), build_orderflow_index(), get_orderflow_for_m5/context()
flow_layer.py        — normalize(), conviction_modifier(), veto(), exit_signal(), build_prompt()
poi_engine.py        — POI keystone: build_map/arm/mark_tested/poi_block/map_block (dual-scored)
stage_funnel.py      — stage_of(), entry_allowed(), guidance() (4×15-min funnel, pure Python)
prompts.py           — 6 agent system prompts (AGENT0_CARTOGRAPHER..AGENT5_FLOW_READER) + blocks
build_orderflow.py   — builder: Binance aggTrades → orderflow_5m_YYYY-MM-DD.csv
gates/
  door0_bootstrap.py  — Cartographer: cycle map + warm-start + ideology anchor (NEW)
  door1_presession.py — H1 Commander, 12 questions (H4+H1), takes poi/cycle seed
  door2_candle.py     — M5 Sniper + M1 Trigger parallel (flow handled in main.py)
  door3_tree.py       — M5 Sniper tree + M15 Scout + flow modifier + stage guidance + POI
  door4_entry.py      — Gate 2.5 flow veto + Bull+Bear + Half-Kelly + POI + stage-gated entry
  door5_management.py — Re-eval + M1 exit + flow forced-exit parallel
  door6_log.py        — logs flow context + post-mortem to LEDGER.md
  door7_eod.py        — end-of-day review
  door8_session.py    — session summary
run.sh               — continuous WARM resume (no candle-0 reset)
logs/                — session logs (also copied to /sdcard/6yearsofpain_logs/)
```

## Data Available
- data/m5.csv              — 100,512 BTC M5 candles (2025-06-16 → 2026-05-31)
- data/m1.csv              — M1 sub-candle data (active)
- data/m15.csv             — NOT present (aggregated from M5 in memory)
- data/h1.csv              — NOT present (aggregated from M5 in memory)
- data/h4.csv              — NOT present (aggregated from M5 in memory)
- data/orderflow_5m_2025-06-17.csv — 288 bars, 25 cols, Binance spot IST verified

## How to Run
```bash
# Start from order flow day (recommended for flow testing)
cd /root/6yearsofpain17
python3 -c "import state_manager; s=state_manager.reset(); s['candle_index']=272; state_manager.save(s)"
python main.py

# Full run from candle 0
python main.py --reset

# Overnight continuous batches
bash run.sh

# View results
cat LEDGER.md
```

## Math Layers Implemented
- Half-Kelly position sizing: f* = 0.5 × (b×p - q) / b
- M15 conviction trim: -0.5 if neutral, -1.5 if conflicting
- H1 direction veto: blocks LONG if BEARISH mandate, blocks SHORT if BULLISH mandate
- Flow conviction modifier: +0→+2.0 boost (aligned), -0→-2.5 penalty (opposing)
- Flow veto: blocks entry when opposing flow strength ≥ 7 or ABSORPTION_REVERSAL/EXHAUSTION

## Kaaviya Clone
Separate JS project at /sdcard/kaaviya-clone17 (not modified).
Uses engine.js + DOOR 1-8 framework for live BTC trading via Bybit.

## Key Philosophy
"The market is a war zone between buyers and sellers."
NEVER: pattern names, indicator names, the word "trend"
ALWAYS: buyer/seller language, specific prices, who won and what followed

## Priority Order
1. ~~Fix h1_h4_aligned checklist bug~~ ✅ DONE 2026-06-03
2. ~~Test run — verify trades complete~~ ✅ DONE (deterministic pipeline test)
3. ~~Order Flow layer (Agent 5 Flow Reader)~~ ✅ BUILT 2026-06-03
4. ~~Fix Flow Reader blocking (background thread)~~ ✅ FIXED 2026-06-03
5. Run on 2025-06-17 order flow day — verify trades + flow verdicts in LEDGER
6. Build more order flow days (build_orderflow.py handles any date)
7. Consider downloading H4/H1 data from Bybit for richer analysis

## Known Behavior Notes
- First 272 candles (2025-06-16) have no order flow — fast, flow skipped cleanly
- Candle 272 onward (2025-06-17) — full 6-agent mode with flow + POI + stage funnel
- Flow Reader overlaps with Doors 2→3; total per-candle time ~50-70s (vs 90s before)
- Gemini is conservative: high-conviction setup needed. Floor is 6 (not 7) now.
- run.sh resets to candle 0 each batch — use manual candle_index=272 for flow testing
