# Hướng dẫn vận hành — Thợ Cả Cổng Làng

Cheatsheet 1 trang cho Thợ Cả vận hành NeoMakerViGate tại Cổng Làng Maker FPT Shop.

## Mở Cổng buổi sáng

1. Bật TV/màn hình HDMI
2. Bật NEO One (nút nguồn ở thân) — chờ ~25-30s
3. Kiểm tra màn hình hiển thị `🏛️ 🦗 ✨ Cổng Làng Maker`
4. Test 1 game (vd chạm màn → Hub → vẫy tay vào exp01)
5. ✅ Cổng đã sẵn sàng đón trẻ

## Trong ngày

### Khi trẻ vào chơi

- Trẻ chạm màn HOẶC vẫy tay trước camera → vào Hub (3 thẻ game)
- Trẻ chọn 1 trong 3 game:
  - **Vẫy Chào Dế** (4-10t): vẫy tay → đàn dế bay (~60s)
  - **Yoga Robot** (5-12t): bắt chước 5 tư thế (~3 phút)
  - **Photo Booth Cổng Làng** (5-12t): chụp ảnh AR ghép nền (~1 phút)
- Chơi xong → màn QR hiện ra → phụ huynh quét bằng Zalo tải ảnh

### Khi đông trẻ đợi

- Mỗi lượt chơi: exp01 = 60s, exp03 = ~3 phút, exp06 = 1 phút
- Nếu trẻ đứng lâu trên màn QR review (không scan) → "Em ơi, cho bạn khác chơi nhé" → trẻ chạm nút **← Về Hub**

### WiFi cho phụ huynh

- **SSID:** Maker Cổng Vào
- **Pass:** cho-trong-vat
- ⚠️ **Quan trọng:** Phụ huynh phải connect WiFi này QR mới scan tải được ảnh. Dùng 4G không hoạt động.

## Sự cố thường gặp

### Trẻ vẫy tay/V-sign mà camera không detect

- Đứng cách camera ~1m
- Vào trong khung hình (xem preview trên màn)
- Đủ ánh sáng (không đứng quay lưng cửa sổ)
- Nếu vẫn không: SSH `sudo systemctl restart makervigate`

### Màn hình đen / app crash

```bash
ssh maker@neo-one.local
journalctl -u makervigate -n 30
sudo systemctl restart makervigate
```

Nếu vẫn không OK: `sudo reboot`.

### Phụ huynh scan QR không tải được ảnh

- Hỏi: WiFi đang dùng có phải `Maker Cổng Vào`?
- Nếu phụ huynh dùng 4G/5G → đổi WiFi
- Nếu vẫn không: gõ URL thủ công (text dưới QR) vào browser điện thoại

### Caption AI exp06 không hiện

- Bình thường — caption template tự fallback nếu Qwen chưa cài
- Phụ huynh vẫn tải được ảnh, chỉ là caption đơn giản hơn

### Đầy ổ ảnh

- App tự cleanup 200MB. Không cần xử lý
- Xóa thủ công: `rm -rf ~/makervigate/photos/`

## Đóng Cổng cuối ngày

1. SSH: `sudo poweroff` (hoặc nhấn nút nguồn 5s)
2. Tắt TV/màn hình
3. Đậy webcam (chống bụi)

## Liên hệ hỗ trợ

- **Tuấn Lê:** Zalo/SĐT — cập nhật trong file gắn cạnh máy
- **Github:** https://github.com/tuanln/NeoMakerViGate/issues
- **Doc đầy đủ:** [`DEPLOY_NEO_ONE.md`](DEPLOY_NEO_ONE.md) cho cài đặt + troubleshooting tech

---

*Bản v1.0 — 2026-05-18. Cập nhật sau pilot.*
