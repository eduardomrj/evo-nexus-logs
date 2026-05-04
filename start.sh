#!/usr/bin/env bash
# Inicia o EvoNexus Log Viewer em background
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/log-viewer.pid"
LOG_FILE="$SCRIPT_DIR/log-viewer.out"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Log Viewer já está rodando (PID $PID)."
        exit 0
    fi
fi

BASE_PATH=/log-viewer nohup python3 "$SCRIPT_DIR/server.py" > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Log Viewer iniciado (PID $(cat "$PID_FILE")) → http://localhost:8082"
