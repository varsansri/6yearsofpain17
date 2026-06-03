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
