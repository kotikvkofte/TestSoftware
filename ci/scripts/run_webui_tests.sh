#!/usr/bin/env bash
# run_webui_tests.sh HOST HTTPS_PORT OUTDIR
set -euo pipefail
HOST="${1:-127.0.0.1}"
PORT="${2:-2443}"
OUT="${3:-artifacts/webui}"
mkdir -p "${OUT}"

# В репозитории тест-автомата есть папка gui/ для WebUI. Используем SeleniumLibrary. :contentReference[oaicite:4]{index=4}
cd openbmc-test-automation || exit 1
. ../.venv/bin/activate

# Отключаем проверку сертификата (самоподписанный cert в QEMU OpenBMC)
export ROBOT_SYSLOG_FILE="../${OUT}/robot_syslog.txt"
robot -v OPENBMC_HOST:${HOST} -v OPENBMC_PORT:${PORT} \
     -v VERIFY_TLS:false \
     --outputdir "../${OUT}" gui || true
