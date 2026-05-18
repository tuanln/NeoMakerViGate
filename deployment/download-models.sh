#!/usr/bin/env bash
# Tải MediaPipe models + Qwen GGUF (nếu có llama-cpp-python).
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/NeoMakerViGate}"
cd "$REPO_DIR"

if [[ ! -d ".venv" ]]; then
    echo "❌ Chưa có .venv. Chạy bash deployment/install-armbian.sh trước."
    exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> MediaPipe models (Hands + Pose + Selfie)"
python -c "
from neo_makervigate.core.vision_engine import ensure_model
for name in ('hands', 'pose', 'selfie'):
    print(f'  → {name} ...')
    p = ensure_model(name)
    print(f'    {p} ({p.stat().st_size // 1024 // 1024} MB)')
print('MediaPipe OK')
"

echo
echo "==> Qwen 2.5-VL local model (~1.5GB)"
if python -c "import llama_cpp" 2>/dev/null; then
    python -m neo_makervigate.scripts.download_qwen
else
    echo "  llama-cpp-python chưa cài — bỏ qua Qwen."
    echo "  exp06 sẽ dùng caption template fallback."
    echo "  Nếu cần caption AI:"
    echo "    pip install llama-cpp-python"
    echo "    bash deployment/download-models.sh"
fi

echo
echo "✅ Models ready. Verify:"
echo "   ls $REPO_DIR/models/mediapipe/"
echo "   ls ~/makervigate/models/qwen/ 2>/dev/null || echo '(no Qwen)'"
