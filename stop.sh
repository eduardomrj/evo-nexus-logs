#!/usr/bin/env bash
# Para o EvoNexus Log Viewer
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/log-viewer.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "PID file não encontrado. Servidor pode não estar rodando."
    exit 1
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    rm -f "$PID_FILE"
    echo "Log Viewer parado (PID $PID)."
else
    echo "Processo $PID não encontrado. Removendo PID file."
    rm -f "$PID_FILE"
fi
