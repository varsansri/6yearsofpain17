import os

MODEL = "gemini-2.5-flash | 4-agent system (H1+M15+M5+M1)"

# Trade limits  (raised for the forced 1-trade/hour order-flow test; originals: 3 / 10)
MAX_DAILY_TRADES = 24
MAX_TOTAL_TRADES = 30
KILL_SWITCH_LOSSES = 5      # consecutive SLs before day pause (resumes next day)

# ── Order Flow / Footprint layer (ADDITIVE — disable to restore original behavior) ──
# When False: required conviction = 7, no flow agent, no forcing → byte-for-byte old behavior.
ORDERFLOW_ENABLED   = True
REQUIRED_CONVICTION = 6      # entry conviction floor when OF on (NEVER below 6); 7 when OF off
FLOW_BOOST_MAX      = 2.0    # max conviction the Flow Reader can ADD to an aligned setup
FLOW_PENALTY_MAX    = 2.5    # max conviction the Flow Reader can SUBTRACT from an opposed setup
FLOW_VETO_STRENGTH  = 7      # opposing flow_strength (>=) that blocks an entry / exits a trade
FORCE_TRADE_PER_HOUR = True  # aim for >=1 trade per clock hour (Option A: respect the 6 floor)

# Risk parameters (in price units / pips)
MIN_RR = 1.5
MIN_SL_PIPS = 30
MAX_POI_PIPS = 300
FAST_EXIT_PIPS = 30         # first candle fast exit threshold

# Pip size: 1 for crypto (BTC=$1/pt), 0.0001 for forex (EURUSD)
PIP_SIZE = 1.0

# API
API_DELAY = 0.8             # seconds between calls
MAX_RETRIES = 3

# Context window — how many previous M5 candles to send with each call
CONTEXT_CANDLES = 12

# Position sizing (Half-Kelly)
MIN_POSITION_SIZE    = 0.10   # 10% minimum
MAX_POSITION_SIZE    = 1.00   # 100% maximum
DEFAULT_POSITION_SIZE = 0.50  # before any trade history

# ── POI ENGINE (additive keystone — structural + crowd dual scoring) ──────────
# Mark points of interest across 4H/1H/15m, score each on TWO axes, carry forward.
POI_ENABLED         = True
POI_LOOKBACK_DAYS   = 10      # how far back to scan for swings / session levels (bounds cost)
POI_SWING_K         = 2       # a swing needs K confirmed candles on EACH side (no future leak)
POI_CLUSTER_PTS     = 120     # levels within this many points are the SAME poi (cross-TF merge)
POI_ARM_BAND_PTS    = 160     # price within this distance of a poi → poi is "armed" (reaction zone)
POI_ROUND_BASES     = (1000, 500, 250)  # BTC psychological levels (focal/crowd attention)
POI_REBUILD_EVERY_HOURS = 1   # rebuild the map each clock hour (vision = hourly cycles)
# reaction-type thresholds on the 0-10 axes
POI_HIGH_SCORE      = 6.5      # at/above = "high" on an axis
POI_LOW_SCORE       = 3.5      # below = "low" on an axis
