#!/bin/bash
# ================================================================= #
# FOLIUX MASTER SCHEDULER STOP SCRIPT                               #
# ================================================================= #

echo "Searching for running Master Scheduler..."
PID=$(pgrep -f "manage.py master_scheduler")

if [ -n "$PID" ]; then
    echo "Stopping Master Scheduler (PID: $PID)..."
    kill $PID
    sleep 2
    
    if pgrep -f "manage.py master_scheduler" > /dev/null; then
        echo "Scheduler did not stop gracefully. Forcing shutdown..."
        kill -9 $PID
    fi
    echo -e "\033[0;32mSUCCESS: Master Scheduler has been stopped.\033[0m"
else
    echo "Master Scheduler is not currently running."
fi
