#!/usr/bin/env bash
# Cài NeoMakerViGate trên NEO One (Armbian/Ubuntu 22.04 ARM64)
# Run với user thường (KHÔNG root) — script sẽ sudo khi cần.
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/NeoMakerViGate}"
PYTHON_VER="3.12"

if [[ $EUID -eq 0 ]]; then
    echo "❌ KHÔNG chạy script này với sudo/root. Chạy với user thường, script tự sudo khi cần."
    exit 1
fi

# Verify $USER tồn tại + an toàn cho sed
if ! getent passwd "$USER" >/dev/null; then
    echo "❌ User $USER không tồn tại trong /etc/passwd"
    exit 1
fi

echo "==> 1. apt update + system deps"
sudo apt update
sudo apt install -y --no-install-recommends \
    python${PYTHON_VER} python${PYTHON_VER}-venv python3-pip \
    libopencv-dev libgl1-mesa-dri libegl1 \
    libxcb1 libxkbcommon0 libfontconfig1 \
    libpulse0 \
    v4l-utils \
    fonts-noto-color-emoji fonts-noto-cjk \
    build-essential cmake git \
    libssl-dev libffi-dev

echo "==> 2. Setup Python venv tại $REPO_DIR/.venv"
cd "$REPO_DIR"
python${PYTHON_VER} -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip wheel

echo "==> 3. Install Python deps (production)"
pip install -e .

echo "==> 4. (Optional) Install Qwen local backend"
read -r -p "Cài Qwen local cho exp06 caption? [y/N] " -n 1 reply
echo
if [[ "$reply" =~ ^[Yy]$ ]]; then
    pip install llama-cpp-python
fi

echo "==> 5. udev rule cho webcam"
sudo cp deployment/udev/99-makervigate-cam.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "==> 6. systemd service"
sudo cp deployment/makervigate.service /etc/systemd/system/
sudo sed -i "s|%USER%|$USER|g" /etc/systemd/system/makervigate.service
sudo sed -i "s|%HOME%|$HOME|g" /etc/systemd/system/makervigate.service
sudo systemctl daemon-reload

echo
echo "✅ Install xong. Bước tiếp:"
echo "   bash deployment/download-models.sh"
echo "   sudo systemctl enable --now makervigate"
echo "   sudo reboot"
