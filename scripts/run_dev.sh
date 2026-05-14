#!/usr/bin/env bash
# Chạy NeoMakerViGate trên macOS dev mode với VisionSimulator.
# Không cần webcam thật.
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
    echo "[!] .venv chưa có. Chạy 'make dev' trước."
    exit 1
fi

export NEO_MAKERVIGATE_VISION="${NEO_MAKERVIGATE_VISION:-simulator}"
export NEO_MAKERVIGATE_LOG_LEVEL="${NEO_MAKERVIGATE_LOG_LEVEL:-DEBUG}"

exec .venv/bin/python -m neo_makervigate "$@"
