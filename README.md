# NeoMakerViGate — Cổng Vào Làng Maker

> Trạm 1 (Cổng Vào) — Cổng Làng Maker @ FPT Shop
> 7 trải nghiệm vision-tracking cho trẻ 4–14 tuổi, chạy trên NEO One (ARM64).
> Maker Việt × Dế Foundation × ThingEdu — License MIT.

**Trạng thái:** v0.1.0 — Phase 0 skeleton, đang phát triển trên macOS, sẽ deploy NEO One Allwinner ARM64.

---

## Mục lục nhanh

- [Triết lý & sản phẩm](DOC/ARCHITECTURE.md#1-tổng-quan-sản-phẩm)
- [Kiến trúc 5 lớp](DOC/ARCHITECTURE.md#3-kiến-trúc-tổng-thể)
- [Scope MVP 3 trải nghiệm (đang làm)](DOC/ARCHITECTURE_MVP.md)
- [Phase plan 8 tuần solo dev](DOC/PHASES.md)

---

## Quickstart trên macOS

```bash
# 1. Clone
git clone https://github.com/tuanln/NeoMakerViGate.git
cd NeoMakerViGate

# 2. Virtualenv
python3.12 -m venv .venv
source .venv/bin/activate

# 3. Install deps (dev mode)
pip install -e ".[dev]"

# 4. Chạy với Vision Simulator (không cần webcam)
NEO_MAKERVIGATE_VISION=simulator python -m neo_makervigate

# Hoặc dùng webcam thật trên Mac
python -m neo_makervigate
```

## Chạy test

```bash
make test        # pytest unit + integration
make lint        # ruff + mypy
make all         # format + lint + test
```

## Deploy NEO One (ARM64 Ubuntu 22.04)

Xem [`DOC/DEPLOY_NEO_ONE.md`](DOC/DEPLOY_NEO_ONE.md) (Phase 7 deliverable).

```bash
# Trên NEO One — script tự cài deps + tải model + setup systemd kiosk
bash deployment/install-armbian.sh
```

---

## MVP scope (8 tuần solo dev)

3 trải nghiệm + Hub + chia sẻ ảnh qua QR:

| # | Plugin | Vision | Phase |
|---|---|---|---|
| 1 | `exp01_wave_cricket` — Vẫy Chào Dế | MediaPipe Hands | P3 |
| 2 | `exp03_yoga_robot` — Yoga Robot | MediaPipe Pose | P4 |
| 3 | `exp06_photo_booth` — Photo Booth Cổng Làng | Selfie Seg + Pose + Qwen | P6 |

4 trải nghiệm còn lại (exp02, exp04, exp05, exp07) lùi sau pilot.

---

## Liên hệ & License

- **Tổ chức:** Maker Việt × Dế Foundation — ThingEdu
- **License:** [MIT](LICENSE)
- **Kế thừa kiến trúc:** NeoStopMotion (SignalBus, Worker Thread, ShareServer), NEOSTEM (QML Singletons)
