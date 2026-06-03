"""
DOOR 5 — TRADE MANAGEMENT
Agents:
  Default    — 4 re-evaluation questions on M5 story validity
  M1 Trigger — reads M1 sub-candles for exit timing precision
Both run in PARALLEL. M1 verdict can force early exit independently.
"""

import claude_client
import display
import config
import flow_layer
from prompts import candle_block, context_block, m1_block


def _update_pnl(trade: dict, m5: dict) -> dict:
    direction = trade["direction"]
    entry = trade["entry"]
    fav     = (m5["high"] - entry) if direction == "LONG" else (entry - m5["low"])
    against = (entry - m5["low"]) if direction == "LONG" else (m5["high"] - entry)
    trade["max_fav"]     = max(trade.get("max_fav", 0), fav)
    trade["max_against"] = max(trade.get("max_against", 0), against)
    return trade


def _check_sl_tp(trade: dict, m5: dict) -> tuple[str | None, float]:
    direction, sl, tp = trade["direction"], trade["sl"], trade["tp"]
    if direction == "LONG":
        if m5["low"]  <= sl: return "LOSS", sl
        if m5["high"] >= tp: return "WIN",  tp
    else:
        if m5["high"] >= sl: return "LOSS", sl
        if m5["low"]  <= tp: return "WIN",  tp
    return None, 0.0


def _first_candle_check(trade: dict, m5: dict) -> tuple[bool, str]:
    direction = trade["direction"]
    entry     = trade["entry"]
    close     = m5["close"]
    against   = (entry - close) if direction == "LONG" else (close - entry)
    if against >= config.FAST_EXIT_PIPS:
        return True, (
            f"First candle closed {against:.1f}pts against entry. "
            f"Branch wrong immediately. Fast exit at {close}."
        )
    return False, ""


def run(m5: dict, m1_list: list, recent_candles: list,
        state: dict, presession: dict,
        of_current: dict = None, of_recent: list = None) -> dict:

    trade = state["active_trade"]
    display.door_header(5, "TRADE MANAGEMENT — M5 RE-EVAL + M1 + FLOW")
    display.show_candle(m5, m1_list)
    display.show_pnl(trade, m5["close"])

    trade = _update_pnl(trade, m5)
    state["active_trade"] = trade

    # ── First candle fast exit (hard rule, no AI needed) ─────────────────────
    if trade.get("is_first_candle"):
        fast_exit, reason = _first_candle_check(trade, m5)
        trade["is_first_candle"] = False
        if fast_exit:
            display.block(f"FAST EXIT — {reason}", "WARN")
            return {
                "closed": True, "result": "LOSS",
                "exit_price": m5["close"], "exit_reason": "fast_exit_first_candle",
                "exit_candle": m5["timestamp"], "trade": trade,
            }

    # ── SL / TP check (hard rule) ─────────────────────────────────────────────
    result, exit_price = _check_sl_tp(trade, m5)
    if result:
        trade["exit_price"]  = exit_price
        trade["exit_candle"] = m5["timestamp"]
        pips = (exit_price - trade["entry"]) if trade["direction"] == "LONG" \
               else (trade["entry"] - exit_price)
        trade["result_pips"] = round(pips / config.PIP_SIZE, 1)
        display.trade_result(result, trade)
        return {
            "closed": True, "result": result, "exit_price": exit_price,
            "exit_reason": "sl_tp_hit", "exit_candle": m5["timestamp"], "trade": trade,
        }

    # ── Parallel: M5 re-eval + M1 exit timing ────────────────────────────────
    pnl_str = f"{'+'if trade['direction']=='LONG' else '-'}{abs(m5['close']-trade['entry']):.1f}pts"

    reeval_prompt = f"""
{context_block(recent_candles)}
CURRENT CANDLE: {candle_block(m5)}

ACTIVE TRADE:
Direction: {trade['direction']} | Entry: {trade['entry']} | SL: {trade['sl']} | TP: {trade['tp']}
P&L: {pnl_str} | Max fav: {trade.get('max_fav',0):.1f}pts | Max against: {trade.get('max_against',0):.1f}pts
Inversion point: {trade.get('inversion_point','not set')}
Original branch: {trade.get('dominant_branch','not set')}

Evaluate whether this trade should still be held. Answer in buyer/seller terms only.

Return ONLY this JSON:
{{
  "q1_branch_valid": true,
  "q1_explanation": "Is the original trade branch still valid? Are entry conditions still in place?",
  "q2_bs_expected": true,
  "q2_explanation": "Are buyers/sellers doing EXACTLY what was expected? What is happening vs predicted?",
  "q3_inversion_intact": true,
  "q3_explanation": "Is the inversion point still intact — has price NOT crossed it?",
  "q4_new_branch": false,
  "q4_explanation": "Has a new branch overtaken the original? Is the market telling a DIFFERENT story now?",
  "exit_early": false,
  "exit_reason": null,
  "exit_price_if_early": null
}}
Set exit_early=true only if the STORY has changed — not just because price is against you.
"""

    m1_exit_prompt = f"""
{m1_block(m1_list, m5)}

ACTIVE TRADE:
Direction: {trade['direction']} | Entry: {trade['entry']} | SL: {trade['sl']} | TP: {trade['tp']}
P&L: {pnl_str}
Original branch: {trade.get('dominant_branch','not set')}

You are the M1 TRIGGER monitoring this open trade.
Read ONLY the M1 sub-candles above. Is the M1 momentum supporting the trade or reversing?

Return ONLY this JSON:
{{
  "m1_momentum_with_trade": true,
  "m1_reversal_signal": false,
  "m1_absorption_against": false,
  "m1_verdict": "HOLD|EXIT|WATCH",
  "m1_exit_urgency": "LOW|MEDIUM|HIGH",
  "m1_reason": "one sentence with specific M1 prices explaining verdict"
}}
HOLD = M1 supports continuing. EXIT = M1 showing clear reversal, exit now. WATCH = uncertain.
"""

    # ── Re-eval (+ M1 exit + Flow Reader, all in parallel when data exists) ───
    calls = [("default", reeval_prompt, "Door 5 — Re-eval")]
    if m1_list:
        calls.append(("m1_trigger", m1_exit_prompt, "Door 5 — M1 Exit"))
    use_flow = config.ORDERFLOW_ENABLED and of_current
    if use_flow:
        calls.append(("flow_reader",
                      flow_layer.build_prompt(of_current, of_recent),
                      "Door 5 — Flow Reader"))
    if len(calls) > 1:
        parallel = claude_client.ask_parallel(calls, optional={"flow_reader"})
        reeval = parallel["default"]
    else:
        reeval = claude_client.ask_agent("default", reeval_prompt, "Door 5 — Re-eval")
        parallel = {"default": reeval}
    m1exit   = parallel.get("m1_trigger", {})
    flow_raw = parallel.get("flow_reader", {})

    # ── Display re-eval ───────────────────────────────────────────────────────
    print("\n  4 RE-EVALUATION QUESTIONS:")
    q_validity = ["q1_branch_valid", "q2_bs_expected", "q3_inversion_intact", "q4_new_branch"]
    for i in range(1, 5):
        icon = "✓" if reeval.get(q_validity[i-1]) else "✗"
        print(f"  Q{i} {icon}: {str(reeval.get(f'q{i}_explanation',''))[:200]}")

    should_exit  = reeval.get("exit_early", False)
    exit_reason  = reeval.get("exit_reason", "")
    exit_price_r = reeval.get("exit_price_if_early", m5["close"])

    # ── M1 Trigger forced exit: clear reversal at high urgency overrides hold ──
    m1_verdict = (m1exit.get("m1_verdict") or "").upper()
    m1_urgency = (m1exit.get("m1_exit_urgency") or "").upper()
    if m1exit:
        print(f"  M1 Exit: {m1_verdict or 'N/A'} ({m1_urgency or '-'}) — {str(m1exit.get('m1_reason',''))[:160]}")
    if not should_exit and m1_verdict == "EXIT" and m1_urgency == "HIGH":
        should_exit  = True
        exit_reason  = "M1 Trigger reversal — " + str(m1exit.get("m1_reason", ""))
        exit_price_r = m5["close"]

    # ── Flow Reader forced exit: the tape flipped hard against the open trade ──
    if config.ORDERFLOW_ENABLED and flow_raw:
        flow = flow_layer.normalize(flow_raw)
        print(f"  Flow Reader: {flow['verdict']} | bias {flow['bias']} | strength {flow['strength']:.0f}")
        if not should_exit:
            f_exit, f_reason = flow_layer.exit_signal(flow, trade["direction"])
            if f_exit:
                should_exit  = True
                exit_reason  = f_reason
                exit_price_r = m5["close"]

    if should_exit:
        if not exit_price_r:
            exit_price_r = m5["close"]
        display.block(f"EARLY EXIT — {exit_reason}", "WARN")
        trade["exit_price"]  = exit_price_r
        trade["exit_candle"] = m5["timestamp"]
        pips = (exit_price_r - trade["entry"]) if trade["direction"] == "LONG" \
               else (trade["entry"] - exit_price_r)
        trade["result_pips"] = round(pips / config.PIP_SIZE, 1)
        result_str = "WIN" if pips > 0 else "LOSS"
        display.trade_result(result_str, trade)
        return {
            "closed": True, "result": result_str, "exit_price": exit_price_r,
            "exit_reason": "early_exit", "exit_candle": m5["timestamp"], "trade": trade,
        }

    display.block("Trade continuing — story intact", "INFO")
    return {"closed": False, "trade": trade}
