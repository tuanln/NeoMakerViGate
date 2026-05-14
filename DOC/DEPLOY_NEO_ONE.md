# Deploy NEO One — Hướng dẫn cài đặt

> **Phase 7 deliverable** — tài liệu này hoàn thiện sau khi smoke test trên NEO One thật.
> Phase 0-6: chỉ placeholder + checklist sơ bộ.

## Phần cứng yêu cầu

- NEO One (Allwinner ARM64, 2GB RAM, Ubuntu 22.04 / Armbian Bookworm)
- 1× USB webcam UVC (Logitech C270 / C310 trở lên — autofocus tốt hơn)
- 1× màn hình HDMI (TV / monitor 1080p)
- 1× loa USB (tùy chọn — chỉ cần khi v1.1+ thêm voice)
- Bàn phím + chuột (chỉ dùng lúc cài đặt)

## Cài đặt nhanh (sau khi P7 xong)

```bash
# 1. Boot NEO One, đăng nhập user maker
ssh maker@neo-one.local

# 2. Clone repo
git clone https://github.com/tuanln/NeoMakerViGate.git
cd NeoMakerViGate

# 3. Chạy install script
bash deployment/install-armbian.sh

# 4. Tải model
bash deployment/download-models.sh

# 5. Enable systemd kiosk
sudo cp deployment/makervigate.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now makervigate.service

# 6. Reboot — app tự chạy fullscreen
sudo reboot
```

## Verify trên hardware

| Kiểm tra | Lệnh | Pass criteria |
|---|---|---|
| Webcam | `v4l2-ctl --list-devices` | Thấy `/dev/video0` |
| MediaPipe wheel | `python3 -c "import mediapipe; print(mediapipe.__version__)"` | In ra phiên bản |
| PyQt6 | `python3 -c "from PyQt6 import QtQuick"` | Không lỗi |
| App boot | `systemctl status makervigate` | active (running) |
| FPS Hands | đo trong exp01 console log | ≥ 10 fps |
| RAM peak | `free -h` lúc đang chạy exp06 | < 1.8GB used |

## Troubleshooting

(Chi tiết viết sau P7)

- Webcam không nhận: check `udev/99-webcam.rules`, reload udev
- FPS < 5: giảm `vision.resolution_width=640`, `pose_model_complexity=0`
- Qwen local OOM: chuyển `qwen.mode="api"`, cần internet ổn định
- Kiosk không full-screen: check `ui.fullscreen=true` trong `~/.config/makervigate/config.toml`
