#!/usr/bin/env bash
# Remove a unidade systemd do Log Viewer.
# Uso: sudo ./UNINSTALL.sh
set -euo pipefail

SERVICE_NAME="log-viewer"
UNIT_DST="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ "${EUID:-0}" -ne 0 ]]; then
  echo "Execute como root, por exemplo: sudo $0" >&2
  exit 1
fi

systemctl stop "${SERVICE_NAME}.service" 2>/dev/null || true
systemctl disable "${SERVICE_NAME}.service" 2>/dev/null || true
rm -f "$UNIT_DST"
systemctl daemon-reload
systemctl reset-failed "${SERVICE_NAME}.service" 2>/dev/null || true
echo "Unidade ${SERVICE_NAME}.service removida (serviço parado e desabilitado)."
