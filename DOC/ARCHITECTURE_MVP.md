# NeoMakerViGate — MVP Scope & Design Decisions

> **Phiên bản:** 0.1.0 (MVP Design)
> **Ngày soạn:** 2026-05-15
> **Áp dụng cho:** Phase 0 → Phase 7 (8 tuần solo dev macOS → ARM deploy)
> **Tài liệu cha:** [`ARCHITECTURE.md`](ARCHITECTURE.md) — kiến trúc đầy đủ 7 trải nghiệm

---

## 1. Vì sao có tài liệu này

Tài liệu kiến trúc gốc [`ARCHITECTURE.md`](ARCHITECTURE.md) (1376 dòng) thiết kế cho **team 4 người × 8 tuần** với **đủ 7 trải nghiệm**. Dự án này thực tế là **solo dev** (Tuấn) trên macOS, sẽ deploy NEO One Allwinner ARM64 — phần cứng đến trong 2-4 tuần.

Tài liệu này:

1. Cắt scope MVP còn **3 trải nghiệm** đủ chứng minh end-to-end kiến trúc plugin + vision pipeline + chia sẻ ảnh QR
2. Đề ra **risk register** với 4 spike kill-switch trước/trong Phase 1
3. Sắp xếp lại WBS thành **8 phase × ~5 ngày solo** thay vì 4 sprint × 2 tuần team
4. Quyết định nhanh các điểm doc gốc chưa chốt (Python version, package manager, lint policy)

Khi MVP pilot thành công, 4 trải nghiệm còn lại (exp02, exp04, exp05, exp07) + Voice (Whisper + Piper) sẽ bổ sung — kiến trúc plugin cho phép thêm mà không sửa lõi.

---

## 2. MVP Scope — 3 trải nghiệm

| # | Plugin | Module MediaPipe | Qwen | Voice | Lý do chọn |
|---|---|---|---|---|---|
| 1 | `exp01_wave_cricket` Vẫy Chào Dế | Hands (21) | — | — | Đơn giản nhất → chứng minh plugin + vision pipeline |
| 2 | `exp03_yoga_robot` Yoga Robot | Pose (33) | — | — | Module nặng nhất + scoring cosine similarity |
| 3 | `exp06_photo_booth` Photo Booth Cổng Làng | Selfie Seg + Pose | ✅ caption | — | Đầy đủ luồng PhotoCapture + composite + Qwen + QR |

**KHÔNG trong MVP v1:** exp02, exp04, exp05, exp07, VoiceIO (Whisper + Piper TTS), firmware ThingBot.

**Vẫn trong MVP v1:** Hub + StackView, PhotoCapture, ShareServer, QR, VisionSimulator, IdleAttractScreen, Qwen 2 backend (local + API).

---

## 3. Phase Plan — 8 phase × ~1 tuần solo

Mỗi phase **5 ngày × ~5h/ngày = 25h ≈ ~3 person-days hiệu suất**. Phase có buffer cho debug và spike.

| Phase | Tuần | Mục tiêu chính | Demo criteria |
|---|---|---|---|
| **P0** Foundation | 1 | Repo + pyproject + CI xanh + QML SplashScreen chạy trên Mac | `python -m neo_makervigate` mở cửa sổ Qt fullscreen, SplashScreen hiện 2s rồi tắt |
| **P1** Vision Core | 2 | `VisionEngine` + `VisionWorker` + MediaPipe Hands trên Mac + `VisionSimulator` mock | Webcam Mac → skeleton bàn tay vẽ realtime ≥30fps |
| **P2** Plugin Arch + Hub | 3 | `experience_base.py` + `registry.py` + `ExperienceHubPage` lưới 3 thẻ + StackView | Chạm thẻ → chuyển sang container page rỗng |
| **P3** exp01 Wave Cricket | 4 | Game 1 đầy đủ + đàn dế bay + scoring + back-to-Hub | Vẫy tay → dế phản ứng. Pytest logic plugin xanh |
| **P4** Pose + exp03 Yoga Robot | 5 | Pose module + `set_active_modules` + `landmark_math` cosine sim + exp03 với 5 tư thế | Đứng T-pose → game nhận đúng. Pose timeline đầy đủ. |
| **P5** PhotoCapture + ShareServer + QR | 6 | `PhotoCapture` + composite Selfie Seg + `ShareServer` + `PhotoReviewPage` | Quét QR bằng Zalo trên cùng WiFi → tải ảnh về điện thoại |
| **P6** Qwen + exp06 Photo Booth | 7 | `QwenClient` 2 backend + exp06 với 2 nền (Sân Đình, Lũy Tre) + caption tiếng Việt | Photo Booth flow xuyên suốt: chụp → composite → caption → QR |
| **P7** ARM Deploy + Smoke Test | 8 | `install-armbian.sh` + `makervigate.service` kiosk + đo FPS + RAM thực + bug fix | NEO One boot → app fullscreen, chơi cả 3 game không crash trong 20 lượt |

**Tổng:** ~8 tuần solo, có buffer rộng. Nếu hardware về sớm, P7 chuẩn bị song song P4-P6.

---

## 4. Risk Register

### 4.1 Top 4 rủi ro cần khử sớm

| # | Rủi ro | Severity | Probability | Mitigation | Plan B |
|---|---|---|---|---|---|
| **R1** | MediaPipe Hands FPS < 10 trên NEO One Allwinner | Cao | Trung | Spike S3 ngay khi hardware về | RPi 5 8GB (~2.5tr) thay NEO One |
| **R2** | Qwen 3.5 0.8B-VL chưa có gguf stable cho llama.cpp khi cần | Cao | Trung-Cao | Spike S2 đầu P6 | Dùng Qwen2-VL-2B-Instruct cũ + ép API mode |
| **R3** | RAM 2GB peak khi all-active (PyQt+Vision+Qwen) > 1.8GB | Cao | Cao | Spike S4 cuối P6 | Bỏ Qwen local hoàn toàn → API-only |
| **R4** | Solo dev không kham nổi timeline 8 tuần | Trung | Trung | Buffer mỗi phase + scope MVP đã cắt 4/7 game | Lùi P7 deploy + chỉ pilot exp01+exp03 |

### 4.2 Spike Schedule

| Spike | Khi | Thời lượng | Pass criteria | Trigger Plan B nếu |
|---|---|---|---|---|
| **S1** MediaPipe Hands FPS trên Mac (M-series) | P1 ngày 1 | 4h | ≥30fps webcam 720p | < 15fps → đổi sang ncnn |
| **S2** Qwen gguf availability + LLM runtime ARM | P6 ngày 1 | 4h | Có Qwen3.5-0.8B Q4 gguf trên HuggingFace | Không có → dùng Qwen2-VL-2B + API only |
| **S3** MediaPipe Hands trên NEO One ARM64 thật | P7 ngày 1-2 | 2 ngày | ≥10fps 480p | < 5fps → pivot RPi 5 hoặc cắt scope offline-only |
| **S4** Memory profile all-active | P7 ngày 3 | 4h | Peak RAM < 1.8GB | > 1.8GB → bỏ Qwen local |

---

## 5. Tech Decisions — quyết định nhanh cho solo dev

| Quyết định | Khác doc gốc | Lý do |
|---|---|---|
| **Python 3.11+ minimum** (test 3.11 + 3.12) | Doc: 3.10+ | `tomllib` built-in; `Self` type; modern syntax. Python 3.13 còn mới, một số thư viện chưa wheel sẵn |
| **pip + venv** chuẩn (không uv) | Doc: không nêu | uv chưa cài máy user; pip đủ; giữ tương thích Ubuntu apt trên ARM |
| **`ruff` + `mypy --strict` từ P0** | Doc: có | Solo dev = lint là reviewer thứ hai |
| **`pytest-qt` mock vision frame** | Doc: có | Test plugin logic không cần webcam thật |
| **`Qwen mode="api"` cho dev macOS, `"auto"` cho NEO One** | Doc: auto cho cả 2 | Mac dev không cần tải model 1GB |
| **Bỏ Voice (Whisper + Piper) khỏi v1 MVP** | Doc: P4 / Sprint 4 | exp07 lùi sau pilot → tiết kiệm 1 tuần |
| **MIT license public từ ngày 1** | Doc: "public sau pilot" | User chọn public ngay — match cam kết Bình Dân Học STEM |
| **CI: ubuntu-latest only** (không macOS/Windows) | — | Solo budget, GitHub Actions free tier; Qt offscreen mode test đủ |

---

## 6. Cấu trúc thư mục MVP (rút gọn từ doc gốc §4)

```
NeoMakerViGate/
├── pyproject.toml, requirements*.txt, Makefile, README.md, LICENSE
├── .gitignore, .github/workflows/ci.yml
│
├── DOC/
│   ├── ARCHITECTURE.md          # nguyên bản 1376 dòng — source of truth kiến trúc
│   ├── ARCHITECTURE_MVP.md      # tài liệu này — scope MVP
│   ├── PHASES.md                # phase plan chi tiết
│   ├── PLUGIN_GUIDE.md          # P2 deliverable
│   └── DEPLOY_NEO_ONE.md        # P7 deliverable
│
├── src/neo_makervigate/
│   ├── __init__.py, __main__.py, app.py
│   ├── config/                  # P0 — defaults.toml + settings.py
│   ├── core/                    # P1-P6 — vision_engine, photo_capture, qwen_client, share_server, models
│   ├── experiences/             # P2 base, P3/P4/P6 plugins
│   │   ├── experience_base.py
│   │   ├── registry.py
│   │   ├── exp01_wave_cricket/  # P3
│   │   ├── exp03_yoga_robot/    # P4
│   │   └── exp06_photo_booth/   # P6
│   ├── services/                # P2 — app_controller, experience_manager, photo_service, qwen_service, share_service
│   ├── ui/                      # P0 + xuyên suốt — image_provider + qml/
│   ├── utils/                   # P0-P1 — signal_bus, cv_qt_bridge, landmark_math, network, logging_config
│   └── resources/               # sounds, fonts, images chung
│
├── models/                      # gitignore — download bằng deployment/download-models.sh
├── deployment/                  # P7 — install-armbian.sh, makervigate.service
├── tests/                       # song song mỗi phase — unit + integration + e2e
└── scripts/                     # run_dev.sh, run_neo_one.sh
```

**Bỏ tạm khỏi MVP repo:**

- `firmware/` (ThingBot Arduino) — không cần khi không có UART
- `src/neo_makervigate/experiences/exp02_catch_bug/`, `exp04_smile_charge/`, `exp05_turtle_logo/`, `exp07_neo_tre_vision/`
- `src/neo_makervigate/core/voice_io.py` + `models/whisper/` + `models/piper/`

---

## 7. Tiêu chí thành công MVP v1

| Metric | Ngưỡng | Đo ở phase |
|---|---|---|
| App boot time trên NEO One | < 25s từ power-on | P7 |
| MediaPipe Hands FPS NEO One | ≥ 10 fps 480p | P7 (S3) |
| MediaPipe Pose FPS NEO One | ≥ 8 fps 480p `model_complexity=0` | P7 |
| Chuyển Hub → exp01 → Hub | < 3s | P3 |
| Qwen caption (API mode) | < 4s | P6 |
| Chụp ảnh → QR hiện | < 5s không caption; < 9s có caption | P5, P6 |
| Crash-free 20 lượt liên tục | 100% | P7 |
| Quét QR tải ảnh thành công | ≥ 80% | P7 pilot |

Nới so với doc gốc §17 (15fps target) — vì là MVP, NEO One có thể chưa được tune tối ưu. v1.1 sẽ siết.

---

## 8. Phụ thuộc DAG

```
P0 Foundation
    │
    ▼
P1 Vision Core  ←──── Spike S1 (MediaPipe Mac FPS)
    │
    ▼
P2 Plugin Architecture + Hub
    │
    ▼
P3 exp01 Wave Cricket
    │
    ▼
P4 Pose + exp03 Yoga Robot
    │
    ▼
P5 PhotoCapture + ShareServer + QR
    │
    ▼
P6 Qwen + exp06 Photo Booth  ←─── Spike S2 (Qwen gguf availability)
    │
    ▼
P7 ARM Deploy + Smoke Test  ←──── Spike S3 (NEO One FPS) + S4 (Memory)
```

P7 có thể chạy song song P4-P6 khi hardware NEO One về.

---

## 9. Khi nào pivot scope

Trigger pivot nếu:

- **S3 fail** (< 5fps trên NEO One): switch sang RPi 5 8GB ngay, không tiếc 2 tuần đã đầu tư vì 100% code chạy được trên RPi
- **S4 fail** (RAM > 1.9GB): bỏ Qwen local hoàn toàn, exp06 caption chỉ chạy khi có internet (đã có UX fallback)
- **Tuần 5 chưa xong P3+P4**: cắt exp03 khỏi MVP, chỉ giữ exp01 + exp06; pilot sớm hơn 1 tuần
- **Tuần 7 chưa xong P5**: hoãn exp06, pilot với 2 game offline (exp01 + exp03 + chụp ảnh + QR, bỏ Qwen)

Phương châm: **một Cổng Làng luôn hoạt động tốt hơn một Cổng Làng đôi khi rất thông minh** (kế thừa từ doc gốc §15.4).

---

**HẾT — v0.1.0 MVP Design**

Tham chiếu: [`ARCHITECTURE.md`](ARCHITECTURE.md), [`PHASES.md`](PHASES.md)
