import json
from pathlib import Path

STATE_FILE = "state.json"


def default_state():
    return {
        "candle_index": 0,
        "current_day": None,
        "presession_done": False,
        "presession_analysis": {},
        "possibility_tree": [],
        "daily_trades": 0,
        "total_trades": 0,
        "consecutive_losses": 0,
        "session_halted": False,
        "active_trade": None,
        "trade_history": [],
        "eod_done_days": [],
    }


def load() -> dict:
    p = Path(STATE_FILE)
    if p.exists():
        with open(p) as f:
            state = json.load(f)
        print(f"Resumed from state: candle #{state['candle_index']}, "
              f"trades={state['total_trades']}, halted={state['session_halted']}")
        return state
    return default_state()


def save(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def reset():
    Path(STATE_FILE).unlink(missing_ok=True)
    print("State reset. Starting fresh.")
    return default_state()
