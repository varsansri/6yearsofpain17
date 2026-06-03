import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from prompts import (
    SYSTEM_PROMPT,
    AGENT0_CARTOGRAPHER,
    AGENT1_H1_COMMANDER,
    AGENT2_M15_SCOUT,
    AGENT3_M5_SNIPER,
    AGENT4_M1_TRIGGER,
    AGENT5_FLOW_READER,
)

FORBIDDEN = [
    "double top", "double bottom", "head and shoulders", "engulfing", "doji",
    "hammer", "shooting star", "morning star", "evening star", "wedge", "flag",
    "pennant", "channel", "triangle", "macd", "moving average",
    "bollinger", "fibonacci", "fib", "support and resistance", "trendline",
]

# Agent routing — maps agent_id to its system prompt
AGENT_PROMPTS = {
    "cartographer": AGENT0_CARTOGRAPHER,
    "h1_commander": AGENT1_H1_COMMANDER,
    "m15_scout":    AGENT2_M15_SCOUT,
    "m5_sniper":    AGENT3_M5_SNIPER,
    "m1_trigger":   AGENT4_M1_TRIGGER,
    "flow_reader":  AGENT5_FLOW_READER,
    "default":      SYSTEM_PROMPT,
}

ENV = {**os.environ, "GOOGLE_GENAI_USE_GCA": "1", "NO_COLOR": "1"}


# ── Core JSON helpers ─────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    raw = re.sub(r'\x1B\[[0-9;]*m', '', raw).strip()
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip().lstrip("json").strip()
            try:
                return json.loads(part)
            except json.JSONDecodeError:
                continue
    start, end = raw.find("{"), raw.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(raw[start:end])
    raise json.JSONDecodeError("no JSON object found", raw, 0)


def _validate(data: dict) -> str | None:
    text = json.dumps(data).lower()
    for word in FORBIDDEN:
        if re.search(r'\b' + re.escape(word) + r'\b', text):
            return f'pattern language: "{word}"'
    if not re.search(r'\d{2,}', text):
        return "no specific prices found"
    return None


# ── Spinner ───────────────────────────────────────────────────────────────────

def _spinner(stop_event: threading.Event, label: str):
    chars = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    i = 0
    start = time.time()
    while not stop_event.is_set():
        elapsed = int(time.time() - start)
        sys.stdout.write(f"\r  {chars[i % len(chars)]} {label}... {elapsed}s")
        sys.stdout.flush()
        i += 1
        time.sleep(0.1)
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()


# ── Raw Gemini call ───────────────────────────────────────────────────────────

def _gemini_call(full_prompt: str, label: str = "") -> str:
    """Single Gemini call with spinner. Returns raw stdout."""
    stop = threading.Event()
    t = threading.Thread(
        target=_spinner,
        args=(stop, f"Gemini {label}" if label else "Gemini thinking"),
        daemon=True,
    )
    t.start()
    try:
        result = subprocess.run(
            ["gemini", "-m", "gemini-2.5-flash", "-p", full_prompt],
            capture_output=True,
            text=True,
            timeout=300,
            env=ENV,
        )
        return result.stdout or ""
    finally:
        stop.set()
        t.join()


# ── Single agent call (with retry + validation) ───────────────────────────────

def _agent_call(agent_id: str, prompt: str, label: str = "") -> dict:
    """
    Call Gemini with the correct agent system prompt.
    Retries up to MAX_RETRIES on validation failure.
    """
    system = AGENT_PROMPTS.get(agent_id, SYSTEM_PROMPT)
    full_prompt = f"{system}\n\n{prompt}"
    last_error = None

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            if attempt > 1:
                print(f"  [{agent_id} retry {attempt}/{config.MAX_RETRIES}] {label}")

            raw = _gemini_call(full_prompt, label=f"[{agent_id}]")
            clean = re.sub(r'\x1B\[[0-9;]*m', '', raw).strip()
            if clean:
                print(f"\n  ── {agent_id.upper()} ──")
                print(clean)
                print()

            data = _parse_json(raw)
            violation = _validate(data)
            if violation:
                last_error = f"validation failed: {violation}"
                print(f"  [{agent_id}] {violation} — retrying")
                continue

            return data

        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {e} | raw: {raw[:200]}"
        except subprocess.TimeoutExpired:
            last_error = f"timed out after 300s"
        except Exception as e:
            last_error = str(e)

    raise RuntimeError(
        f"Agent '{agent_id}' failed after {config.MAX_RETRIES} attempts [{label}]: {last_error}"
    )


# ── Parallel multi-agent call ─────────────────────────────────────────────────

def ask_parallel(calls: list, optional: set = None) -> dict:
    """
    Run multiple agent calls in parallel.

    calls = [
        (agent_id, prompt, label),
        ...
    ]
    optional: agent_ids whose failure is NON-fatal — they return {} instead of
              raising. Default None → every agent is required (original behavior).

    Returns {agent_id: result_dict}
    Raises RuntimeError if any REQUIRED agent fails after all retries.
    """
    optional = optional or set()
    results = {}
    errors  = {}

    print(f"\n  ▶ Running {len(calls)} agents in parallel: {[c[0] for c in calls]}")

    with ThreadPoolExecutor(max_workers=len(calls)) as executor:
        futures = {
            executor.submit(_agent_call, agent_id, prompt, label): agent_id
            for agent_id, prompt, label in calls
        }
        for future in as_completed(futures):
            agent_id = futures[future]
            try:
                results[agent_id] = future.result()
                print(f"  ✓ {agent_id} complete")
            except Exception as e:
                if agent_id in optional:
                    results[agent_id] = {}
                    print(f"  ⚠ {agent_id} failed (optional) — continuing: {e}")
                else:
                    errors[agent_id] = str(e)
                    print(f"  ✗ {agent_id} failed: {e}")

    if errors:
        raise RuntimeError(f"Parallel agents failed: {errors}")

    return results


# ── Public API ────────────────────────────────────────────────────────────────

def ask(prompt: str, label: str = "") -> dict:
    """
    Single Gemini call using default system prompt.
    Used by doors that don't need multi-agent splitting (Door 6, 7, 8).
    Unchanged behaviour from before.
    """
    return _agent_call("default", prompt, label)


def ask_agent(agent_id: str, prompt: str, label: str = "") -> dict:
    """
    Single agent call with specific role.
    agent_id: 'h1_commander' | 'm15_scout' | 'm5_sniper' | 'm1_trigger'
    """
    return _agent_call(agent_id, prompt, label)
