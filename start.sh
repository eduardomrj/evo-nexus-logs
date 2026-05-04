#!/usr/bin/env bash
# Inicia o EvoNexus Log Viewer em background e grava o PID

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/log-viewer.pid"
LOG_FILE="$SCRIPT_DIR/log-viewer.out"
PYTHON="${LOG_VIEWER_PYTHON:-python3}"

export BASE_PATH="${BASE_PATH:-${LOG_VIEWER_BASE_PATH:-/log-viewer}}"
PORT="${LOG_VIEWER_PORT:-8082}"
export LOG_VIEWER_PORT="$PORT"

command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python3"

if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE")
  if kill -0 "$PID" 2>/dev/null; then
    echo "[log-viewer] Já em execução (PID $PID) em http://127.0.0.1:$PORT${BASE_PATH}/"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

mkdir -p "$SCRIPT_DIR"

# Evita falso "health OK" de outro processo na mesma porta (novo Python falha com EADDRINUSE).
bash "$SCRIPT_DIR/stop.sh" >/dev/null 2>&1 || true

LISTEN_HOST="${LOG_VIEWER_HOST:-127.0.0.1}"

echo "[log-viewer] Iniciando (python: $PYTHON, $LISTEN_HOST:$PORT, BASE_PATH=$BASE_PATH)..."
nohup env BASE_PATH="$BASE_PATH" LOG_VIEWER_PORT="$PORT" LOG_VIEWER_HOST="$LISTEN_HOST" \
  "$PYTHON" "$SCRIPT_DIR/server.py" >> "$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"
echo "[log-viewer] Iniciado — PID $PID | log: $LOG_FILE"

for _ in $(seq 1 30); do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "[log-viewer] Erro: o processo $PID terminou ao iniciar — veja $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
  fi
  if curl -sf "http://127.0.0.1:${PORT}${BASE_PATH}/health" > /dev/null 2>&1; then
    echo "[log-viewer] Pronto em http://127.0.0.1:${PORT}${BASE_PATH}/"
    exit 0
  fi
  sleep 0.5
done
echo "[log-viewer] Aviso: health não respondeu após ~15s — verifique $LOG_FILE"
exit 1
