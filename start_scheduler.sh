#!/bin/bash
# ================================================================= #
# FOLIUX MASTER SCHEDULER START SCRIPT                              #
# ================================================================= #

LIVE_DIR="/home/foliux"
PYTHON_BIN="$LIVE_DIR/venv/bin/python"
MANAGE_PY="$LIVE_DIR/manage.py"
LOG_FILE="$LIVE_DIR/scheduler.log"

echo "Checking for any running Master Scheduler..."
PID=$(pgrep -f "manage.py master_scheduler")

if [ -n "$PID" ]; then
    echo "Found running scheduler with PID $PID. Stopping it first..."
    kill $PID
    sleep 2
    # Verify if it stopped, otherwise force kill
    if pgrep -f "manage.py master_scheduler" > /dev/null; then
        kill -9 $PID
    fi
    echo "Previous scheduler stopped."
fi

echo "Starting Master Scheduler in the background..."
nohup $PYTHON_BIN $MANAGE_PY master_scheduler > $LOG_FILE 2>&1 &

sleep 2

NEW_PID=$(pgrep -f "manage.py master_scheduler")
if [ -n "$NEW_PID" ]; then
    echo -e "\033[0;32mSUCCESS: Master Scheduler started successfully in the background!\033[0m"
    echo "- PID: $NEW_PID"
    echo "- Logs are being written to: $LOG_FILE"
    echo "To view live logs, run: tail -f $LOG_FILE"
else
    echo -e "\033[0;31mERROR: Failed to start Master Scheduler. Please check $LOG_FILE for details.\033[0m"
fi
