"""
6yearsofpain — Candle-by-candle trading backtester.
The AI answers questions. The code controls everything else.

Usage:
  python main.py                  # run (resumes from state.json)
  python main.py --reset          # clear state and start fresh
  python main.py --force-eod      # force end-of-day even with < 3 trades
  python main.py --report         # print ledger summary only
"""

import sys
import os
import shutil
from datetime import datetime
from pathlib import Path

import config
import state_manager
import display
import data_loader
import flow_layer
import poi_engine
import claude_client
from concurrent.futures import ThreadPoolExecutor as _FlowPool

from gates import (
    door1_presession,
    door2_candle,
    door3_tree,
    door4_entry,
    door5_management,
    door6_log,
    door7_eod,
    door8_session,
)


# ── Dual logger: writes to console AND log file simultaneously ────────────────

class TeeLogger:
    def __init__(self, log_path: str):
        self.terminal = sys.stdout
        self.log = open(log_path, "a", buffering=1, encoding="utf-8")

    def write(self, msg):
        self.terminal.write(msg)
        self.log.write(msg)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()


def _copy_log_to_sdcard(log_path: str):
    try:
        sdcard = "/sdcard/6yearsofpain_logs"
        Path(sdcard).mkdir(parents=True, exist_ok=True)
        dest = os.path.join(sdcard, os.path.basename(log_path))
        shutil.copy2(log_path, dest)
        print(f"\n  Log saved to phone: {dest}")
    except Exception as e:
        print(f"\n  [WARN] Could not copy log to sdcard: {e}")


def main():
    args = sys.argv[1:]

    if "--report" in args:
        _print_report()
        return

    # ── Set up log file ───────────────────────────────────────────────────────
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = str(log_dir / f"session_{session_ts}.log")
    tee = TeeLogger(log_path)
    sys.stdout = tee
    print(f"  Logging to: {log_path}")

    try:
        _run(args, log_path)
    except KeyboardInterrupt:
        print("\n  Interrupted by user.")
    except Exception as e:
        print(f"\n  [FATAL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sys.stdout = tee.terminal
        tee.close()
        _copy_log_to_sdcard(log_path)


def _run(args, log_path):
    force_eod = "--force-eod" in args

    if "--reset" in args:
        state = state_manager.reset()
    else:
        state = state_manager.load()

    # ── Load data ─────────────────────────────────────────────────────────────
    # H1/H4/M15 are NOT pre-aggregated: context getters build them backward from the
    # current M5 index so the most recent higher-TF candle is in-progress (no leak).
    m5_data, m1_data, _h1_unused, _h4_unused = data_loader.load_data("data")

    # Index M1 by parent-M5 timestamp once (O(1) per-candle lookup during backtest)
    m1_index = data_loader.build_m1_index(m1_data)
    if m1_index:
        print(f"Indexed M1: {len(m1_index)} M5-buckets for M1 Trigger")

    # ── Order Flow layer (additive) ───────────────────────────────────────────
    of_data  = data_loader.load_orderflow("data") if config.ORDERFLOW_ENABLED else None
    of_index = data_loader.build_orderflow_index(of_data)
    if of_index:
        print(f"Indexed order flow: {len(of_index)} bars for the Flow Reader")
    # Dedicated single-thread pool so Flow Reader never shares workers with required agents
    _flow_pool = _FlowPool(max_workers=1) if config.ORDERFLOW_ENABLED else None
    _flow_future = None  # background future for current candle's flow read
    # Entry conviction floor: lowered to REQUIRED_CONVICTION when OF on, else original 7
    required_conviction = config.REQUIRED_CONVICTION if config.ORDERFLOW_ENABLED else 7
    # Per-clock-hour trade tracking (forced ≥1 trade/hour goal — Option A respects the floor)
    cur_hour = None
    hour_count = 0
    _poi_map = []   # persistent POI map (rebuilt each clock hour)

    total_candles = len(m5_data)

    display.divider()
    print(f"  6YEARSOFPAIN — Backtester")
    print(f"  Candles : {total_candles} M5 | Starting at #{state['candle_index']}")
    print(f"  Model   : {config.MODEL}")
    print(f"  Target  : {config.MAX_TOTAL_TRADES} trades | {config.MAX_DAILY_TRADES}/day | R:R≥{config.MIN_RR}")
    print(f"  Log     : {log_path}")
    display.divider()

    # ── Main candle loop ──────────────────────────────────────────────────────
    for idx in range(state["candle_index"], total_candles):

        if state.get("total_trades", 0) >= config.MAX_TOTAL_TRADES:
            display.block(
                f"Target reached: {state['total_trades']}/{config.MAX_TOTAL_TRADES} trades. Session complete.",
                "PASS"
            )
            break

        m5 = data_loader.candle_to_dict(m5_data[idx])
        m1_list = data_loader.get_m1_for_m5(m1_index, m5["timestamp"])
        of_current = data_loader.get_orderflow_for_m5(of_index, m5["timestamp"])
        of_recent  = data_loader.get_orderflow_context(of_index, m5["timestamp"], 6)
        current_day = str(m5["timestamp"])[:10]

        # ── Start Flow Reader in background NOW (runs while Doors 2→3 process) ──
        if _flow_pool and of_current:
            _flow_prompt = flow_layer.build_prompt(of_current, of_recent)
            _flow_future = _flow_pool.submit(
                claude_client.ask_agent, "flow_reader", _flow_prompt, "Flow Reader"
            )
        else:
            _flow_future = None

        # Per-clock-hour trade tracking (report ≥1 entry/hour goal)
        this_hour = str(m5["timestamp"])[:13]
        hour_changed = cur_hour is not None and this_hour != cur_hour
        if hour_changed:
            tag = "OK" if hour_count >= 1 else "NO TRADE THIS HOUR"
            print(f"\n  [HOUR {cur_hour}:00] entries: {hour_count}  [{tag}]")
            hour_count = 0
        first_candle = cur_hour is None
        cur_hour = this_hour

        # ── POI ENGINE (additive keystone) — rebuild hourly, arm every candle ──
        poi_ctx = ""
        if config.POI_ENABLED:
            if hour_changed or first_candle or not _poi_map:
                _poi_map = poi_engine.build_map(m5_data, idx)
            poi_engine.mark_tested(_poi_map, m5)
            armed = poi_engine.arm(_poi_map, m5["close"])
            poi_ctx = poi_engine.poi_block(armed, m5["close"])
            if armed:
                print(f"  POI: {len(armed)} armed | nearest {armed[0]['price']} "
                      f"({armed[0]['side']}, {armed[0]['reaction_type']}, {armed[0]['distance_pts']:.0f}pts)")

        start  = max(0, idx - config.CONTEXT_CANDLES)
        recent = [data_loader.candle_to_dict(m5_data[i]) for i in range(start, idx)]

        # ── Day boundary ──────────────────────────────────────────────────────
        prev_day = state.get("current_day")
        if prev_day and current_day != prev_day:
            if prev_day not in state.get("eod_done_days", []):
                day_trades = [t for t in state["trade_history"]
                              if str(t.get("entry_candle", ""))[:10] == prev_day]
                try:
                    eod = door7_eod.run(prev_day, len(day_trades), day_trades, state)
                    if eod.get("kill_switch"):
                        state["session_halted"] = True
                        state_manager.save(state)
                        break
                except Exception as e:
                    print(f"  [SKIP] Door 7 error: {e} — continuing")
                done = state.setdefault("eod_done_days", [])
                done.append(prev_day)
            state["daily_trades"] = 0
            state["current_day"] = current_day

        if state.get("current_day") is None:
            state["current_day"] = current_day

        # Auto-clear halted state on new day so session continues
        if state.get("session_halted") and current_day != state.get("halted_day"):
            print(f"  [RESUME] New day {current_day} — clearing halt from {state.get('halted_day')}")
            state["session_halted"] = False
            state["consecutive_losses"] = 0

        if state.get("session_halted"):
            state["candle_index"] = idx + 1
            state_manager.save(state)
            continue

        # ── Pre-session (once per day) ────────────────────────────────────────
        if not state.get("presession_done") or state.get("presession_day") != current_day:
            try:
                h4c, h1c = data_loader.get_h1_context(m5_data, idx)
                presession = door1_presession.run(h4c, h1c, poi_ctx)
                state["presession_analysis"] = presession
                state["presession_done"] = True
                state["presession_day"] = current_day
                state_manager.save(state)
            except Exception as e:
                print(f"  [SKIP] Door 1 error: {e} — using empty presession")
                state["presession_analysis"] = {}
                state["presession_done"] = True
                state["presession_day"] = current_day

        presession = state.get("presession_analysis", {})

        # ── DOOR 2: Candle advance ────────────────────────────────────────────
        try:
            d2 = door2_candle.run(m5, m1_list, recent, state, presession,
                                  state.get("possibility_tree", []))
        except Exception as e:
            print(f"  [SKIP] Door 2 error: {e}")
            state["candle_index"] = idx + 1
            state_manager.save(state)
            continue

        if d2.get("blocked"):
            state["candle_index"] = idx + 1
            state_manager.save(state)
            continue
        state["last_timestamp"] = m5["timestamp"]

        # ── Collect Flow Reader result (was running in background during Door 2) ─
        # Flow started before Door 2; by now D2 took ~20-40s so flow may be ready.
        # Block here — flow ALWAYS completes, no skip.
        if _flow_future is not None:
            try:
                _flow_result = _flow_future.result()  # waits however long it takes
                d2["flow"] = _flow_result
                fl = flow_layer.normalize(_flow_result)
                print(f"  Flow Reader: {fl['verdict']} | bias {fl['bias']} | strength {fl['strength']:.0f}"
                      f" — {str(fl.get('note',''))[:140]}")
            except Exception as e:
                print(f"  [WARN] Flow Reader error: {e} — flow neutral this candle")
                d2["flow"] = {}
        else:
            d2["flow"] = {}

        # ── DOOR 3: Possibility tree ──────────────────────────────────────────
        try:
            m15_ctx = data_loader.get_m15_context(m5_data, idx)
            d3 = door3_tree.run(m5, m1_list, recent, d2, state, presession, m15_ctx,
                                required_conviction=required_conviction, poi_ctx=poi_ctx)
            state["possibility_tree"] = d3.get("branches", [])
        except Exception as e:
            print(f"  [SKIP] Door 3 error: {e}")
            state["candle_index"] = idx + 1
            state_manager.save(state)
            continue

        # ── DOOR 5: Trade management (if in trade) ────────────────────────────
        if state.get("active_trade"):
            try:
                d5 = door5_management.run(m5, m1_list, recent, state, presession,
                                          of_current, of_recent)
                state["active_trade"] = d5.get("trade", state["active_trade"])

                if d5.get("closed"):
                    trade  = d5["trade"]
                    result = d5["result"]

                    if result == "LOSS":
                        state["consecutive_losses"] = state.get("consecutive_losses", 0) + 1
                    else:
                        state["consecutive_losses"] = 0

                    if state["consecutive_losses"] >= config.KILL_SWITCH_LOSSES:
                        display.block(
                            f"KILL SWITCH — {state['consecutive_losses']} consecutive losses. "
                            f"Pausing for today.", "HALT"
                        )
                        state["session_halted"] = True
                        state["halted_day"] = current_day

                    door6_log.run(trade, result, d5.get("exit_candle", ""), recent)
                    state["trade_history"].append(trade)
                    state["active_trade"] = None
                    state["daily_trades"]  = state.get("daily_trades", 0) + 1
                    state["total_trades"]  = state.get("total_trades", 0) + 1
                    print(f"\n  Trades: {state['total_trades']}/{config.MAX_TOTAL_TRADES}")
                    # Periodic sdcard backup after every trade
                    _copy_log_to_sdcard(log_path)

            except Exception as e:
                print(f"  [WARN] Door 5 error: {e} — trade remains open")

        # ── DOOR 4: Entry ─────────────────────────────────────────────────────
        elif not state.get("active_trade"):
            signal = d3.get("entry_signal", {})
            if signal.get("exists") and signal.get("conviction", 0) >= required_conviction:
                try:
                    d4 = door4_entry.run(
                        m5, m1_list, recent, signal, d2, d3, state, presession,
                        required_conviction=required_conviction, poi_ctx=poi_ctx
                    )
                    if d4.get("enter") and not d4.get("blocked"):
                        state["active_trade"] = d4["trade"]
                        hour_count += 1
                except Exception as e:
                    print(f"  [SKIP] Door 4 error: {e}")

        # ── Save state ────────────────────────────────────────────────────────
        state["candle_index"] = idx + 1
        state_manager.save(state)

    # ── Session end ───────────────────────────────────────────────────────────
    if state.get("active_trade"):
        display.block("Session ended with open trade.", "WARN")

    last_day = state.get("current_day")
    if last_day and last_day not in state.get("eod_done_days", []):
        day_trades = [t for t in state["trade_history"]
                      if str(t.get("entry_candle", ""))[:10] == last_day]
        if len(day_trades) >= 3 or force_eod:
            try:
                door7_eod.run(last_day, len(day_trades), day_trades, state)
            except Exception as e:
                print(f"  [SKIP] Final Door 7 error: {e}")

    if state.get("trade_history"):
        try:
            door8_session.run(state)
        except Exception as e:
            print(f"  [SKIP] Door 8 error: {e}")

    state_manager.save(state)
    display.divider()
    print(f"  Done. Total trades: {state.get('total_trades', 0)}/{config.MAX_TOTAL_TRADES}")


def _print_report():
    p = Path("LEDGER.md")
    if p.exists():
        print(p.read_text())
    else:
        print("No LEDGER.md found. Run a backtest first.")


if __name__ == "__main__":
    main()
