#!/usr/bin/env bash
# Chạy NeoMakerViGate trên NEO One ARM64 — production mode.
# Webcam thật, full Vision pipeline, Qwen auto.
set -euo pipefail

cd "$(dirname "$0")/.."

# Env override cho production
export NEO_MAKERVIGATE_VISION="engine"
export NEO_MAKERVIGATE_QWEN="${NEO_MAKERVIGATE_QWEN:-auto}"
export NEO_MAKERVIGATE_LOG_LEVEL="${NEO_MAKERVIGATE_LOG_LEVEL:-INFO}"

# Stable webcam symlink (udev rule trong deployment/udev/99-webcam.rules)
if [[ -e /dev/makervigate-cam ]]; then
    export NEO_MAKERVIGATE_CAM_DEVICE="/dev/makervigate-cam"
fi

exec python3 -m neo_makervigate "$@"
