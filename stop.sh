#!/usr/bin/env bash
# Para o EvoNexus Log Viewer

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/log-viewer.pid"
PORT="${LOG_VIEWER_PORT:-8082}"

stop_by_pid_file() {
  if [[ -f "$PID_FILE" ]]; then
    local PID
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
      echo "[log-viewer] Parando PID $PID..."
      kill "$PID"
      local i
      for i in $(seq 1 6); do
        kill -0 "$PID" 2>/dev/null || break
        sleep 1
      done
      if kill -0 "$PID" 2>/dev/null; then
        kill -9 "$PID" 2>/dev/null || true
      fi
      rm -f "$PID_FILE"
      echo "[log-viewer] Parado."
      return 0
    fi
    rm -f "$PID_FILE"
  fi
  return 1
}

stop_by_port() {
  local PIDS
  PIDS=""
  if command -v lsof >/dev/null 2>&1; then
    PIDS=$(lsof -ti ":$PORT" 2>/dev/null | xargs 2>/dev/null || true)
  elif command -v fuser >/dev/null 2>&1; then
    PIDS=$(fuser -n tcp "$PORT" 2>/dev/null | tr -s ' ' '\n' | grep -E '^[0-9]+$' | xargs 2>/dev/null || true)
  fi
  if [[ -n "${PIDS:-}" ]]; then
    echo "[log-viewer] Encerrando processo(s) na porta $PORT: $PIDS"
    # shellcheck disable=SC2086
    kill $PIDS 2>/dev/null || true
    sleep 2
    rm -f "$PID_FILE"
    echo "[log-viewer] Parado (porta $PORT)."
    return 0
  fi
  return 1
}

stop_by_pid_file || stop_by_port || echo "[log-viewer] Nenhum processo encontrado na porta $PORT."
