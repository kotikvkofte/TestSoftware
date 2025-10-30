#!/usr/bin/env bash
# wait_for_bmc.sh HOST PORT TIMEOUT_SEC
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-2443}"
TIMEOUT="${3:-300}"

echo "[INFO] Waiting for BMC ${HOST}:${PORT} up to ${TIMEOUT}s..."
SECS=0
until nc -z "${HOST}" "${PORT}"; do
  sleep 3
  SECS=$((SECS+3))
  if [ "${SECS}" -ge "${TIMEOUT}" ]; then
    echo "[ERROR] BMC did not come up in time"; exit 1
  fi
done
echo "[INFO] BMC is up."
