# Deploy NEO One — Hướng dẫn cài đặt

Triển khai NeoMakerViGate lên NEO One ARM64 (Allwinner SoC). Sau khi xong, app tự boot fullscreen, phụ huynh quét QR tải ảnh về điện thoại.

## Phần cứng yêu cầu

- NEO One (Allwinner H313/H616 ARM64, 2GB RAM, Armbian Bookworm hoặc Ubuntu 22.04 ARM64)
- 1× USB webcam UVC (Logitech C270/C310/C920 đề xuất — autofocus tốt)
- 1× màn hình HDMI (TV/monitor 1080p, hỗ trợ touch tùy chọn)
- 1× loa USB (tùy chọn, chỉ dùng từ v1.1+ với voice)
- Bàn phím + chuột USB (chỉ cần lúc cài đặt; sau kiosk không cần)
- Cáp HDMI, microSD ≥16GB cho hệ điều hành
- Kết nối mạng WiFi (FPT Shop WiFi đề xuất `Maker Cổng Vào`)

## Pre-install — chuẩn bị hệ điều hành

1. Flash Armbian Bookworm hoặc Ubuntu 22.04 ARM64 lên microSD bằng Raspberry Pi Imager hoặc balenaEtcher
2. Boot NEO One, set user `maker` + password
3. Connect WiFi qua `nmcli` hoặc `armbian-config`
4. Verify SSH: `ssh maker@<ip>` từ máy khác → OK

## Cài đặt nhanh

```bash
# 1. SSH vào NEO One
ssh maker@neo-one.local  # hoặc IP

# 2. Clone repo
git clone https://github.com/tuanln/NeoMakerViGate.git
cd NeoMakerViGate

# 3. Chạy install script (sẽ hỏi password sudo + có cài Qwen không)
bash deployment/install-armbian.sh

# 4. Download models (MediaPipe ~30MB, Qwen ~1.5GB nếu có)
bash deployment/download-models.sh

# 5. Enable + start kiosk service
sudo systemctl enable --now makervigate.service

# 6. Verify chạy OK rồi reboot
sudo systemctl status makervigate
sudo reboot
```

Sau khi boot lại, NEO One sẽ tự vào fullscreen IdleAttractScreen.

## Verify trên hardware

| Kiểm tra | Lệnh | Pass criteria |
|---|---|---|
| Webcam detect | `v4l2-ctl --list-devices` | Thấy `/dev/video0` (USB) |
| Symlink udev | `ls -l /dev/makervigate-cam` | → `/dev/video0` (hoặc video1) |
| MediaPipe import | `.venv/bin/python -c "import mediapipe; print(mediapipe.__version__)"` | In phiên bản |
| PyQt6 import | `.venv/bin/python -c "from PyQt6 import QtQuick"` | Không lỗi |
| App service | `systemctl status makervigate` | `active (running)` |
| Qt eglfs | journalctl logs | Không "Could not initialize EGLFS" |
| ShareServer | `curl http://localhost:8000/` | Directory listing |
| FPS Hands | exp01 console log (visionFps property) | ≥ 10 fps |
| RAM peak | `free -h` lúc chạy exp06 | < 1.8GB used |

## Troubleshooting

### Webcam không nhận

```bash
dmesg | grep -i usb | tail -20         # check USB enumeration
v4l2-ctl --list-devices                 # check kernel detect
ls -l /dev/video* /dev/makervigate-cam  # check udev symlink
sudo udevadm test /sys/class/video4linux/video0  # debug rule
```

Nếu vendor:product webcam khác Logitech:

```bash
lsusb | grep -i cam   # tìm vendor:product
sudo nano /etc/udev/rules.d/99-makervigate-cam.rules  # thêm dòng mới
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### FPS quá thấp

- Giảm resolution: edit `~/.config/makervigate/config.toml` → `vision.resolution_width=640`
- Tắt module không dùng: chỉ active `hands` trong exp01 (đã default)
- Pose model complexity: `pose_model_complexity=0` (lite mode)

### Qwen OOM (chỉ với caption local)

- Check RAM: `free -h` peak khi exp06 chạy
- Nếu > 1.8GB → xóa Qwen model: `rm -rf ~/makervigate/models/qwen/`
- exp06 tự fallback caption template (không cần config thêm)

### Qt eglfs black screen

```bash
journalctl -u makervigate -n 50 | grep -i egl
glxinfo 2>/dev/null | grep -i renderer  # check GPU driver
```

Fallback to linuxfb (slower nhưng không cần GPU):

```bash
sudo systemctl edit makervigate
# Add:
[Service]
Environment=QT_QPA_PLATFORM=linuxfb
```

### Service crash loop

```bash
journalctl -u makervigate -n 100 --no-pager  # full log
sudo systemctl reset-failed makervigate
sudo systemctl restart makervigate
```

Nếu crash 5+ lần trong 60s, systemd ngưng restart (StartLimitBurst=5). Reset:

```bash
sudo systemctl reset-failed makervigate
```

### IdleAttract không pop sau 90s

- Đảm bảo trạng thái Hub (không vào game)
- Check log: `journalctl -u makervigate | grep -i idle`

## Update + rollback

```bash
cd ~/NeoMakerViGate
git pull
.venv/bin/pip install -e .
sudo systemctl restart makervigate
```

Rollback nếu update lỗi:

```bash
git log --oneline | head -10   # tìm commit cũ
git checkout <sha>
.venv/bin/pip install -e .
sudo systemctl restart makervigate
```

## Uninstall

```bash
sudo systemctl disable --now makervigate
sudo rm /etc/systemd/system/makervigate.service
sudo rm /etc/udev/rules.d/99-makervigate-cam.rules
sudo udevadm control --reload-rules
rm -rf ~/NeoMakerViGate
rm -rf ~/makervigate           # photos + Qwen models
```
