#!/bin/bash
# Overnight runner — continuous batches of 10 trades until you stop it.
# Each batch resets state and starts fresh from the next candle position.
# Logs every batch separately to /sdcard/6yearsofpain_logs/

cd /root/6yearsofpain17

BATCH=1

echo "================================================"
echo "  6YEARSOFPAIN — Overnight Runner"
echo "  Continuous batches of 10 trades"
echo "  Started: $(date)"
echo "  Press Ctrl+C to stop"
echo "================================================"

while true; do
    echo ""
    echo "  ══════════════════════════════════════"
    echo "  BATCH $BATCH — Starting at $(date)"
    echo "  ══════════════════════════════════════"

    # Reset state for fresh batch
    python3 -c "import state_manager; state_manager.reset()" 2>/dev/null

    python main.py
    EXIT=$?

    TRADES=$(python3 -c "
import json
try:
    s = json.load(open('state.json'))
    print(s.get('total_trades', 0))
except:
    print(0)
" 2>/dev/null)

    echo ""
    echo "  [Batch $BATCH] Finished — $TRADES trades | Exit: $EXIT | $(date)"

    if [ "$TRADES" -ge "10" ]; then
        echo "  [Batch $BATCH] COMPLETE — 10 trades done."
        BATCH=$((BATCH + 1))
        echo "  Starting Batch $BATCH in 30s..."
        sleep 30
        continue
    fi

    if [ "$EXIT" -ne "0" ]; then
        echo "  [Batch $BATCH] Crashed — restarting in 15s..."
        sleep 15
        continue
    fi

    # Clean exit but < 10 trades — data exhausted
    echo "  [Batch $BATCH] Data exhausted. Waiting 60s and retrying..."
    sleep 60
done
