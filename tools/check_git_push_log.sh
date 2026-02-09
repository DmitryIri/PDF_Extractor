#!/bin/bash
# Check git auto-push log

LOG_FILE="/tmp/git-auto-push.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "No auto-push log found at $LOG_FILE"
    exit 0
fi

echo "=== Recent auto-push events ==="
tail -20 "$LOG_FILE"

echo ""
echo "=== Failed pushes ==="
grep -i "FAILED" "$LOG_FILE" | tail -10 || echo "No failures found"
