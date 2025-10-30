#!/usr/bin/env bash
# run_robot_tests.sh HOST HTTPS_PORT OUTDIR
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-2443}"
OUT="${3:-artifacts/robot}"
mkdir -p "${OUT}"

if [ ! -d openbmc-test-automation ]; then
  git clone --depth=1 https://github.com/openbmc/openbmc-test-automation.git
fi

. .venv/bin/activate
cd openbmc-test-automation

# минимальный набор тестов Redfish/IPMI
robot -v OPENBMC_HOST:${HOST} -v OPENBMC_PORT:${PORT} \
  --outputdir "../${OUT}" redfish ipmi || true
