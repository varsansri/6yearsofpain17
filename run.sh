#!/bin/bash
# Continuous runner — RESUMES from saved state each time (warm-start, Idea 3).
# Does NOT reset to candle 0: candle_index, cycle_map and accumulated context all
# carry forward, so each restart continues where the last one stopped.
# Logs go to logs/ and are copied to /sdcard/6yearsofpain_logs/

cd /root/6yearsofpain17

echo "================================================"
echo "  6YEARSOFPAIN — Continuous Runner (warm-start)"
echo "  Resumes from saved state — no reset"
echo "  Started: $(date)"
echo "  Press Ctrl+C to stop"
echo "================================================"

# To start a fresh run from candle 0:    python main.py --reset
# To start from the order-flow day:       python3 -c "import state_manager as s; st=s.reset(); st['candle_index']=272; s.save(st)"

while true; do
    echo ""
    echo "  ── Resuming at $(date) ──"

    python main.py        # resumes from state.json candle_index (warm)
    EXIT=$?

    IDX=$(python3 -c "
import json
try:
    s = json.load(open('state.json')); print(s.get('candle_index', 0))
except: print(0)
" 2>/dev/null)

    echo ""
    echo "  [Resumed run] stopped at candle $IDX | Exit: $EXIT | $(date)"

    if [ "$EXIT" -ne "0" ]; then
        echo "  Crashed — restarting (warm) in 15s..."
        sleep 15
        continue
    fi

    echo "  Clean stop (target reached or data exhausted). Waiting 60s then re-checking..."
    sleep 60
done
