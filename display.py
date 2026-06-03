"""Terminal display helpers — readable output for each door."""

W = 68


def divider(char="═"):
    print(char * W)


def header(title):
    print()
    divider()
    print(f"  {title}")
    divider("─")


def door_header(num, name):
    print()
    print("╔" + "═" * (W - 2) + "╗")
    label = f"  DOOR {num} — {name}"
    print("║" + label + " " * (W - 2 - len(label)) + "║")
    print("╚" + "═" * (W - 2) + "╝")


def show_candle(m5, m1_list=None):
    body = m5["close"] - m5["open"]
    rng = m5["high"] - m5["low"]
    direction = "▲ BULL" if body >= 0 else "▼ BEAR"
    print(f"\n  M5  {m5['timestamp']}  {direction}")
    print(f"  O:{m5['open']}  H:{m5['high']}  L:{m5['low']}  C:{m5['close']}")
    print(f"  Range: {rng:.1f}  Body: {body:+.1f}")
    if m1_list:
        print("  ─── M1 sub-candles ───")
        for m1 in m1_list:
            b = m1["close"] - m1["open"]
            b_str = f"{b:+.1f}"
            tag = ""
            abs_b = abs(b)
            if abs_b >= rng * 0.4:
                tag = "  ←AGG BUY" if b > 0 else "  ←AGG SELL"
            ts = str(m1["timestamp"])[-5:]  # HH:MM
            print(f"  {ts}  O:{m1['open']}  H:{m1['high']}  L:{m1['low']}  C:{m1['close']}  body:{b_str}{tag}")


def show_answers(qna: dict):
    """Print question → answer pairs from a flat dict."""
    for key, val in qna.items():
        if key.startswith("q") or key.startswith("Q"):
            label = key.replace("_", " ").upper()
            print(f"\n  [{label}]")
            if isinstance(val, list):
                for item in val:
                    print(f"    • {item}")
            elif isinstance(val, dict):
                for k2, v2 in val.items():
                    print(f"    {k2}: {v2}")
            else:
                print(f"    {val}")


def show_tree(branches: list):
    print("\n  POSSIBILITY TREE:")
    for i, b in enumerate(branches, 1):
        name = b.get("name", f"Branch {i}")
        direction = b.get("direction", "")
        print(f"\n  [{i}] {name}  ({direction.upper()})")
        print(f"    Confirm   : {b.get('confirm', '?')}")
        print(f"    Invalidate: {b.get('invalidate', '?')}")
        if b.get("target"):
            print(f"    Target    : {b.get('target')}")


def show_trade_setup(trade: dict):
    print("\n  ┌── TRADE SETUP ─────────────────────────────")
    print(f"  │  Direction : {trade.get('direction')}")
    print(f"  │  Entry     : {trade.get('entry')}")
    print(f"  │  Stop Loss : {trade.get('sl')}")
    print(f"  │  Take Profit: {trade.get('tp')}")
    print(f"  │  R:R       : {trade.get('rr')}:1")
    print(f"  │  Conviction: {trade.get('conviction')}/10")
    print("  └─────────────────────────────────────────────")


def show_checklist(checklist: dict):
    print("\n  14-RULE CHECKLIST:")
    all_yes = True
    for k, v in checklist.items():
        icon = "✓" if v else "✗"
        if not v:
            all_yes = False
        print(f"  {icon} {k.replace('_', ' ')}")
    return all_yes


def show_pnl(active_trade: dict, current_price: float):
    entry = active_trade["entry"]
    direction = active_trade["direction"]
    if direction == "LONG":
        pnl = current_price - entry
    else:
        pnl = entry - current_price
    print(f"\n  P&L: {pnl:+.1f} pts | Max fav: {active_trade.get('max_fav', 0):+.1f} | Max against: {active_trade.get('max_against', 0):+.1f}")


def block(msg: str, style="INFO"):
    icons = {"WARN": "⚠", "BLOCK": "✗", "PASS": "✓", "INFO": "•", "HALT": "⛔"}
    print(f"\n  {icons.get(style, '•')} {msg}")


def trade_result(result: str, trade: dict):
    icon = "✓ WIN" if result == "WIN" else "✗ LOSS"
    pips = trade.get("result_pips", 0)
    print(f"\n{'═'*W}")
    print(f"  {icon}  |  {trade['direction']}  {trade['entry']} → {trade.get('exit_price', '?')}  |  {pips:+.1f} pts")
    print(f"{'═'*W}")
