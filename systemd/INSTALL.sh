#!/usr/bin/env bash
# Instala a unidade systemd do Log Viewer.
# Uso: sudo ./INSTALL.sh
set -euo pipefail

SERVICE_NAME="log-viewer"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_SRC="${SCRIPT_DIR}/${SERVICE_NAME}.service"
UNIT_DST="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ "${EUID:-0}" -ne 0 ]]; then
  echo "Execute como root, por exemplo: sudo $0" >&2
  exit 1
fi

if [[ ! -f "$UNIT_SRC" ]]; then
  echo "Arquivo não encontrado: $UNIT_SRC" >&2
  exit 1
fi

install -m 644 "$UNIT_SRC" "$UNIT_DST"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
systemctl start "${SERVICE_NAME}.service"
systemctl status "${SERVICE_NAME}.service" --no-pager -l
