# NeoMakerViGate — Cổng Vào Làng Maker

> Trạm 1 (Cổng Vào) — Cổng Làng Maker @ FPT Shop
> Vision-tracking platform cho trẻ 4–14 tuổi, chạy trên NEO One (ARM64).
> Maker Việt × Dế Foundation × ThingEdu — License MIT.

**Trạng thái (2026-05-17):** MVP 3 game hoàn tất (P0-P6), pending NEO One deploy (P7) + manual smoke test webcam.

- 141 tests pass (ruff/mypy strict clean)
- exp01 Wave Cricket + exp03 Yoga Robot + exp06 Photo Booth done
- ShareServer + QR share via LAN done
- Qwen 2.5-VL caption (optional — fallback templates nếu model missing)

---

## Mục lục nhanh

- [Triết lý & sản phẩm](DOC/ARCHITECTURE.md#1-tổng-quan-sản-phẩm)
- [Kiến trúc 5 lớp](DOC/ARCHITECTURE.md#3-kiến-trúc-tổng-thể)
- [Scope MVP 3 trải nghiệm](DOC/ARCHITECTURE_MVP.md)
- [Phase plan](DOC/PHASES.md)
- [Plugin guide — viết experience mới](DOC/PLUGIN_GUIDE.md)
- [Qwen setup — caption AI cho exp06](DOC/QWEN_SETUP.md)
- [Deploy NEO One](DOC/DEPLOY_NEO_ONE.md) (P7)
- [Spec + plan archives](docs/superpowers/)

---

## MVP scope — 3 trải nghiệm + share

| # | Plugin | Vision | Game flow | Phase |
|---|---|---|---|---|
| 1 | `exp01_wave_cricket` — Vẫy Chào Dế | Hands (WAVE) | INTRO→PLAYING 60s→RESULT 3s | P3 ✅ |
| 2 | `exp03_yoga_robot` — Yoga Robot | Pose 33 landmarks | INTRO→POSING 5×45s→RESULT | P4 ✅ |
| 3 | `exp06_photo_booth` — Photo Booth Cổng Làng | Hands + Selfie Seg | SELECT bg→V_SIGN→COUNTDOWN→PROCESSING+Qwen→DONE | P6 ✅ |

**Cross-experience features:**
- PhotoCapture + ShareServer + QR (every experience can share photos) — P5 ✅
- exp06 ghép nền 4 cảnh (Sân Đình / Lũy Tre / Sân FGC / Sao Hỏa) + Qwen caption tiếng Việt

**Out-of-scope post-pilot:** exp02 Catch Bug, exp04 Smile Charge, exp05 Turtle Logo, exp07 Neo Tre Vision (Qwen dialog + voice).

---

## Quickstart trên macOS

```bash
# 1. Clone + venv
git clone https://github.com/tuanln/NeoMakerViGate.git
cd NeoMakerViGate
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Install deps (dev mode)
pip install -e ".[dev]"

# 3. (Optional) Qwen local model cho exp06 caption
# Cần ~1.5GB disk space — xem DOC/QWEN_SETUP.md
pip install llama-cpp-python
python -m neo_makervigate.scripts.download_qwen

# 4. Chạy
# Webcam thật (cần macOS Camera permission cho Terminal):
python -m neo_makervigate

# Hoặc Vision Simulator (test UI flow, không cần webcam):
NEO_MAKERVIGATE_VISION=simulator python -m neo_makervigate
```

### Test với phụ huynh

1. Trên Mac M4: app boot → ShareServer `http://<lan-ip>:8000`
2. Chơi exp06 → V-sign → ảnh được ghép nền + caption AI
3. iPhone cùng WiFi: scan QR bằng Zalo → tải ảnh về

## Run test

```bash
.venv/bin/python -m pytest          # 141 tests (~17s)
ruff check                          # lint
mypy src/                           # types strict
```

Test files được colocated với plugin (`src/.../test_logic.py`) + dùng chung với `tests/unit/`.

---

## Deploy NEO One (ARM64)

Pending P7 (hardware về 2-4 tuần). Khi sẵn sàng:

```bash
# Trên NEO One — script tự cài deps + tải models + systemd kiosk
bash deployment/install-armbian.sh
sudo systemctl enable makervigate
sudo reboot
```

Chi tiết: [`DOC/DEPLOY_NEO_ONE.md`](DOC/DEPLOY_NEO_ONE.md).

---

## Liên hệ & License

- **Tổ chức:** Maker Việt × Dế Foundation × ThingEdu
- **License:** [MIT](LICENSE)
- **Kế thừa kiến trúc:** NeoStopMotion (SignalBus, Worker Thread, ShareServer), NEOSTEM (QML Singletons)
- **Dev workflow:** spec → plan → subagent-driven TDD execution (docs/superpowers/)
