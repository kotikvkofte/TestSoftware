#!/usr/bin/env bash
# Usage: run_qemu_openbmc.sh HTTPS_PORT SSH_PORT IPMI_PORT
set -euo pipefail
HTTPS_PORT="${1:-2443}"
SSH_PORT="${2:-2222}"
IPMI_PORT="${3:-2623}"

WORKDIR="${PWD}/.qemu"
mkdir -p "${WORKDIR}"
cd "${WORKDIR}"

# 1) тянем архив romulus.zip c Jenkins OpenBMC и распаковываем
if [ ! -f romulus/obmc-phosphor-image-romulus.static.mtd ]; then
  echo "[INFO] downloading romulus.zip image..."
  curl -L -o romulus.zip \
    "https://jenkins.openbmc.org/job/ci-openbmc/lastSuccessfulBuild/distro=ubuntu,label=docker-builder,target=romulus/artifact/openbmc/build/tmp/deploy/images/romulus/*zip*/romulus.zip"
  rm -rf romulus
  mkdir -p romulus
  unzip -o romulus.zip -d romulus
fi

# 2) проверяем наличие qemu-system-arm
if ! command -v qemu-system-arm >/dev/null 2>&1; then
  echo "[ERROR] qemu-system-arm not found. Install it (apt-get install qemu-system-arm) before running."
  exit 1
fi

# 3) стартуем BMC (Romulus) с пробросом портов
#    - HTTPS: 2443, SSH: 2222, IPMI: 2623/udp
echo "[INFO] starting QEMU (romulus-bmc)..."
qemu-system-arm -m 256 -M romulus-bmc -nographic \
  -drive file=romulus/obmc-phosphor-image-romulus.static.mtd,format=raw,if=mtd \
  -net nic -net user,hostfwd=:0.0.0.0:${SSH_PORT}-:22,hostfwd=:0.0.0.0:${HTTPS_PORT}-:443,hostfwd=udp:0.0.0.0:${IPMI_PORT}-:623,hostname=qemu \
  2>&1
