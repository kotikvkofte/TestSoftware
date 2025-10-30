#!/usr/bin/env bash
# run_load_test.sh URL OUTDIR
set -euo pipefail
URL="${1}"
OUT="${2:-artifacts/load}"
mkdir -p "${OUT}"

# Небольшая нагрузка с помощью hey (одно бинарное, не требует root)
if ! command -v hey >/dev/null 2>&1; then
  curl -L -o hey.tar.gz https://hey-release.s3.us-east-2.amazonaws.com/hey_linux_amd64.tar.gz
  tar -xzf hey.tar.gz hey && chmod +x hey && sudo mv hey /usr/local/bin/
fi

# 2k запросов, 50 concur., таймаут 5s — как пример
hey -z 60s -c 50 -q 0 -m GET "${URL}/" > "${OUT}/hey.txt" 2>&1 || true

# Простой CSV для артефактов
grep -E 'Requests/sec|Latency' "${OUT}/hey.txt" | sed 's/  */ /g' > "${OUT}/summary.txt"
