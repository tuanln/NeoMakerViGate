# NeoMakerViGate — Tài liệu Kiến trúc & Kế hoạch Triển khai

> **Phiên bản:** 0.1.0 (Design — 2026-05-14)
> **Tổ chức:** Maker Việt × Dế Foundation — ThingEdu
> **Áp dụng cho:** Trạm 1 (Cổng Vào) — Cổng Làng Maker, Làng Maker @ FPT Shop
> **Tham chiếu kiến trúc:** NeoStopMotion (PyQt6 + QML + SignalBus + ShareServer), NEOSTEM (QML Singletons), NEO_CODE (PyQt6 + Worker Thread)
> **Tham chiếu sản phẩm:** Storyboard "Trò Chơi Cổng Làng" v0.1

---

## 0. Decision Log — Deltas vs Design (2026-05-17)

Document này viết ở P0 conceptual phase. Implementation P3-P6 đã thay đổi vài quyết định. **Code is canonical**, doc này preserved as historical reference.

| Topic | Design (P0) | Implementation | Reason |
|---|---|---|---|
| Qwen model | Qwen 3.5 (0.8B / 4B) | **Qwen 2.5-VL-2B-Instruct-Q4_K_M GGUF** | Qwen 3.5 release chưa có (status 2026-02-03 chỉ Qwen 2.5/3 series). Qwen 2.5-VL có GGUF qua `bartowski/Qwen2.5-VL-2B-Instruct-GGUF` |
| Qwen backend | Hybrid local+API (DashScope) | **Local only** (llama-cpp-python) | User chốt P6 brainstorm. Offline-first phù hợp FPT Shop WiFi chập chờn. DashScope APIBackend out-of-scope post-pilot. |
| Pose scoring (exp03) | Cosine similarity | **Joint-angle similarity** (8 joints × tolerance per group) | P4 brainstorm: angle-based robust hơn với scale + vị trí trẻ vs người lớn. `utils/landmark_math.py` không có cosine. |
| exp03 capture trigger | Manual button hoặc auto-photo cuối game | **Auto-capture vào RESULT phase** | P5 brainstorm. ExperienceManager Phase.DONE → emit `photo_capture_requested` (P5 mechanism). |
| exp06 capture trigger | Per design § 7.5 (gesture) | **V_SIGN hold 0.5s → countdown 3s → emit photo_capture_requested** | P6 brainstorm. `auto_capture_on_done=False` để plugin self-orchestrate (T8). |
| Backgrounds | 4 nền PNG transparent | 4 nền PNG opaque procedural Pillow (sky/ground gradient + simplified silhouettes) | P6 brainstorm: no designer asset needed; user thay PNG sau pilot dễ. |
| New signals (post-design) | — | `photo_capture_requested(dict)`, `photo_captured(PhotoResult)`, `photo_caption_ready(str, str)`, `experience_state` polling 30Hz | Added P5/P6 to support cross-experience photo + caption flow. |
| `BaseExperience.auto_capture_on_done` | — | `ClassVar[bool] = True`; exp06 overrides False | P6 T8. ExperienceManager checks before auto-emitting capture request. |
| Tests pattern | unit only | unit + colocated `expN/test_logic.py` (pyproject `testpaths = ["tests", "src"]`) | P3 T5 fix: plugin tests live with plugin code, registry pattern works. |
| Storage | `/home/maker/makervigate/photos/` | `~/makervigate/photos/` (cross-platform Mac+Linux) | P5 brainstorm. LRU cleanup 200MB theo folder mtime. |

Specs + plans for each phase: `docs/superpowers/specs/` + `docs/superpowers/plans/`.

---

## 1. Tổng quan sản phẩm

**NeoMakerViGate** là *cổng vào* (welcome gate) của mỗi Làng Maker @ FPT Shop — một ứng dụng chạy trên **NEO One** (Linux Ubuntu 22.04, Allwinner ARM64, 2GB RAM) kết nối **một camera USB** và **một màn hình**, mang lại **7 trải nghiệm vision-tracking** cho trẻ em 4–14 tuổi.

Khác với NeoStopMotion (một trạm, một ứng dụng làm phim, điều khiển bằng nút bấm vật lý qua ThingBot UART), NeoMakerViGate là một **hub đa trải nghiệm** — gần với một "máy game console mini" — nơi đứa trẻ chọn và chơi lần lượt nhiều trò, mỗi trò dạy một hạt giống tư duy STEM. Đầu vào không phải nút bấm mà là **cơ thể của chính đứa trẻ**: bàn tay, khuôn mặt, dáng người, được theo dõi real-time bằng **MediaPipe**. Hai trải nghiệm cao cấp nhất dùng thêm **Qwen 3.5** để hiểu hình ảnh và đối thoại tiếng Việt.

Xuyên suốt mọi trải nghiệm là một sợi chỉ chung: **đứa trẻ có thể chụp lại một khoảnh khắc** — một tư thế đẹp, một bức tranh vừa vẽ, một tấm ảnh trước Sân Đình — và **mang về nhà qua một mã QR**. Phụ huynh quét mã bằng Zalo, tải ảnh về điện thoại. Đây là cơ chế lan tỏa cốt lõi: mỗi đứa trẻ rời Làng mang theo một sản phẩm, mỗi phụ huynh chia sẻ một câu chuyện.

### Mục tiêu kỹ thuật v1.0

- Hub chọn trải nghiệm + 7 trải nghiệm chạy được trên NEO One với MediaPipe ≥15 FPS
- 5 trải nghiệm chạy 100% offline (chỉ MediaPipe); 2 trải nghiệm dùng Qwen 3.5 (local hoặc API)
- Chức năng chụp ảnh + chia sẻ qua mã QR hoạt động ở **mọi** trải nghiệm
- Kiến trúc plugin: thêm trải nghiệm thứ 8, 9 không cần sửa lõi
- Pilot tại 1 Làng Maker FPT Shop sau 8 tuần phát triển (4 sprint)
- Mã nguồn mở MIT theo cam kết Bình Dân Học STEM
- Chi phí phần cứng tăng thêm/Làng: **dưới 1 triệu VNĐ** (camera + loa + giá đỡ)

### Triết lý kiến trúc

- **Học từ NeoStopMotion**: 4 lớp, SignalBus, Worker Thread, ShareServer + QR, Singleton QML, design tokens, hardware abstraction, UART simulator → ở đây là *vision simulator*.
- **Mở rộng mới — Experience Plugin Architecture**: mỗi trải nghiệm là một plugin độc lập, implement chung một interface `Experience`. Một sinh viên Maker code được một game mà không đụng tới code của người khác.
- **Vision thay cho nút bấm**: đầu vào chính là `VisionEngine` (MediaPipe) thay cho `UARTListener` (pyserial). ThingBot trở thành tùy chọn, không bắt buộc.
- **Tinh thần Bình Dân Học STEM**: stack đơn giản, phần cứng rẻ, dev nhanh, dễ chuyển giao cho sinh viên Maker.

---

## 2. Technology Stack

| Lớp | Công nghệ | Phiên bản | Lý do chọn |
| --- | --- | --- | --- |
| OS target | Ubuntu 22.04 LTS / Armbian Bookworm | aarch64 | NEO One chuẩn |
| OS dev | macOS 14+ / Ubuntu 22.04 | x86_64 / arm64 | Cross-platform dev |
| Ngôn ngữ | Python | 3.10+ | Sinh viên Maker biết Python; ecosystem rich |
| GUI Framework | **PyQt6 + QML 6** | PyQt6 ≥ 6.5 | Kế thừa pattern NeoStopMotion/NEOSTEM; fluid touch UI |
| Vision tracking | **MediaPipe** | 0.10+ | Pose 33 / Hands 21 / FaceMesh 468 / Selfie Seg; chạy được trên ARM64; miễn phí Apache 2.0 |
| Computer Vision | OpenCV (cv2) | 4.8+ | Đọc webcam, xử lý ảnh, ghép nền (composite) |
| LLM đa phương thức | **Qwen 3.5** (0.8B–4B) | release 02–03/2026 | Hiểu ảnh + tiếng Việt; bản 0.8B chạy local NEO One, bản 4B qua API; Apache 2.0 |
| LLM runtime (local) | llama.cpp / Ollama | latest | Chạy Qwen 3.5-0.8B quantized Q4 trên ARM64 |
| LLM runtime (API) | DashScope HTTP API | - | Qwen 3.5-4B/Flash khi có internet; rẻ |
| Speech-to-text | Whisper.cpp (tiny/base) | latest | Game 7 nhận giọng nói tiếng Việt; offline |
| Text-to-speech | Piper TTS (vi-VN) | latest | Neo Tre đọc tiếng Việt; offline, nhẹ |
| QR generator | qrcode + Pillow | 7.4+ | Pure Python, không cần lib hệ thống |
| File server | http.server (built-in) | - | Đủ dùng cho LAN, không cần Flask/FastAPI |
| Config | tomllib (built-in 3.11+) hoặc tomli | - | TOML > JSON cho config user-facing |
| Audio | QtMultimedia (qua PyQt6) | - | Native Qt, tích hợp QML |
| Logging | logging (built-in) + loguru | - | Đủ + đẹp |
| Testing | pytest + pytest-qt | 7.4+ / 4.2+ | Chuẩn industry; test QML signals + vision mock |
| Linting | ruff + mypy | latest | Strict typing |
| Build | PyInstaller hoặc nuitka | - | Standalone binary cho NEO One |
| Firmware (tùy chọn) | Arduino C++ | - | ThingBot LED feedback — KHÔNG bắt buộc v1.0 |

**Khác biệt stack so với NeoStopMotion:** thêm MediaPipe (vision), Qwen 3.5 + runtime (LLM), Whisper + Piper (voice cho game 7). Bỏ ffmpeg (không xuất video, chỉ ảnh tĩnh). pyserial trở thành tùy chọn.

---

## 3. Kiến trúc tổng thể (5 lớp — 4 lớp NeoStopMotion + lớp Experience Plugins)

```
+==================================================================+
|                                                                  |
|                      UI LAYER (QML 6)                            |
|                                                                  |
|  MainWindow.qml (ApplicationWindow + StackView)                  |
|    ├── SplashScreen.qml                                          |
|    ├── ExperienceHubPage.qml     ← MÀN HÌNH CHÍNH (chọn 7 trò)   |
|    │     └── ExperienceCard.qml × 7  (lưới trải nghiệm)          |
|    ├── ExperienceContainerPage.qml ← khung host game đang chơi   |
|    │     └── (nạp QML của experience plugin đang active)         |
|    ├── PhotoReviewPage.qml       ← xem ảnh + QR (giống Success)  |
|    └── IdleAttractScreen.qml     ← màn hình chờ thu hút khách    |
|                                                                  |
|  Singletons (Global state — kế thừa pattern NEOSTEM):            |
|    ├── NeoConstants.qml   (design tokens — màu tre/dế/gạch)      |
|    ├── NeoAudio.qml       (âm thanh chung)                       |
|    ├── AppState.qml       (current_experience, status)           |
|    └── VisionState.qml    (landmarks, gesture, fps — realtime)   |
|                                                                  |
+=============================+====================================+
                              | (Property Bindings + Signal/Slot)
+=============================v====================================+
|                                                                  |
|               APPLICATION LAYER (Python Services)                |
|                                                                  |
|  AppController        ExperienceManager      PhotoService        |
|  (Root QObject        (load/unload các        (chụp + ghép nền   |
|   exposed to QML;     experience plugin;      + lưu file)        |
|   facade pattern)     vòng đời trải nghiệm)                      |
|                                                                  |
|  ShareService         QwenService                                |
|  (async wrapper       (async wrapper cho                         |
|   cho ShareServer)    QwenClient — caption/đối thoại)            |
|                                                                  |
+=============================+====================================+
                              | SignalBus (pyqtSignal hub)
+=============================v====================================+
|                                                                  |
|               CORE PROCESSING LAYER                              |
|                                                                  |
|  VisionEngine        VisionRouter        ExperienceRuntime        |
|  (MediaPipe Pose/    (route landmarks    (game loop, scoring,    |
|   Hands/Face/Selfie   → experience đang   timer cho trò active)  |
|   trên QThread)       active)                                    |
|                                                                  |
|  PhotoCapture        QwenClient          ShareServer              |
|  (cv2 snapshot +     (llama.cpp local    (qrcode +               |
|   composite nền)      HOẶC DashScope API  http.server            |
|                       trên QThread)       trên QThread)          |
|                                                                  |
|  VoiceIO (tùy game 7: Whisper STT + Piper TTS trên QThread)      |
|                                                                  |
+=============================+====================================+
                              | (gọi qua interface Experience)
+=============================v====================================+
|                                                                  |
|               EXPERIENCE PLUGINS LAYER  ← MỚI                    |
|                                                                  |
|  experience_base.py  (abstract class Experience — interface)     |
|                                                                  |
|  exp01_wave_cricket/      exp02_catch_bug/      exp03_yoga_robot/ |
|  exp04_smile_charge/      exp05_turtle_logo/    exp06_photo_booth/|
|  exp07_neo_tre_vision/                                           |
|                                                                  |
|  Mỗi plugin = 1 thư mục: logic.py + ui.qml + assets/ + test      |
|                                                                  |
+=============================+====================================+
                              |
+=============================v====================================+
|                                                                  |
|               HARDWARE / DATA LAYER                              |
|                                                                  |
|  USB Webcam           NEO One              File system           |
|  (cv2 device 0,       (Linux ARM64,        /home/maker/          |
|   720p autofocus)      2GB RAM)             makervigate/         |
|                                              ├ photos/           |
|  Loa USB              Màn hình HDMI          ├ sessions/         |
|  (QtMultimedia)       (TV/monitor)           └ _shared/          |
|                                                                  |
|  [Tùy chọn] ThingBot — chỉ dùng cho LED/buzzer feedback,        |
|             KHÔNG bắt buộc v1.0                                  |
|                                                                  |
+==================================================================+
```

**Đọc sơ đồ:** dữ liệu hình ảnh đi từ dưới lên — Webcam → VisionEngine (MediaPipe) → VisionRouter → Experience Plugin đang active → cập nhật state → QML render. Khi đứa trẻ chụp ảnh, luồng đi ngang qua PhotoCapture → (tùy chọn QwenClient cho caption) → ShareServer tạo QR → PhotoReviewPage hiển thị.

---

## 4. Cấu trúc thư mục

```
NeoMakerViGate/
│
├── pyproject.toml              # Project metadata, deps, build config
├── requirements.txt            # Pinned runtime deps
├── requirements-dev.txt        # pytest, ruff, mypy, pyinstaller
├── requirements-arm64.txt      # Pinned deps cho NEO One (mediapipe, opencv ARM)
├── README.md
├── LICENSE                     # MIT
├── Makefile                    # `make dev`, `make test`, `make build`
│
├── DOC/
│   ├── ARCHITECTURE.md         # Tài liệu này
│   ├── EXPERIENCES.md          # Đặc tả 7 trải nghiệm chi tiết
│   ├── HARDWARE.md             # Camera + giá đỡ + (tùy chọn) ThingBot + BOM
│   ├── DEPLOY_NEO_ONE.md       # Cài đặt + systemd + kiosk
│   ├── TEACHER_MANUAL.md       # Cheatsheet cho Thợ Cả vận hành Cổng Làng
│   ├── PLUGIN_GUIDE.md         # Hướng dẫn viết experience plugin mới
│   └── QWEN_SETUP.md           # Cài Qwen 3.5 local / cấu hình API
│
├── src/
│   └── neo_makervigate/
│       │
│       ├── __init__.py         # Version: 0.1.0
│       ├── __main__.py         # Entry: python -m neo_makervigate
│       ├── app.py              # QApplication + QmlEngine init
│       │
│       ├── config/             # [Cấu hình]
│       │   ├── __init__.py
│       │   ├── settings.py     # TOML loader, dataclass
│       │   └── defaults.toml   # Giá trị mặc định
│       │
│       ├── core/               # [Xử lý lõi]
│       │   ├── __init__.py
│       │   ├── models.py            # Dataclasses: VisionFrame, ExperienceMeta, PhotoResult...
│       │   ├── vision_engine.py     # MediaPipe Pose/Hands/Face/Selfie wrapper
│       │   ├── vision_router.py     # Route landmarks → experience active
│       │   ├── gesture_detector.py  # Nhận diện WAVE / POINT / V_SIGN / SMILE...
│       │   ├── experience_runtime.py# Game loop, scoring, timer
│       │   ├── photo_capture.py     # cv2 snapshot + composite nền AR
│       │   ├── qwen_client.py       # llama.cpp local HOẶC DashScope API
│       │   ├── voice_io.py          # Whisper STT + Piper TTS (game 7)
│       │   └── share_server.py      # qrcode + http.server
│       │
│       ├── experiences/        # [EXPERIENCE PLUGINS — lớp mới]
│       │   ├── __init__.py
│       │   ├── experience_base.py   # Abstract class Experience (interface)
│       │   ├── registry.py          # Tự động phát hiện + đăng ký plugin
│       │   │
│       │   ├── exp01_wave_cricket/
│       │   │   ├── __init__.py
│       │   │   ├── logic.py         # Vẫy Chào Dế — class WaveCricketExperience
│       │   │   ├── ui.qml           # Giao diện game (lũy tre + đàn dế)
│       │   │   ├── assets/          # Sprite con dế, âm thanh
│       │   │   └── test_logic.py
│       │   ├── exp02_catch_bug/
│       │   │   ├── logic.py         # Tóm Bug Sửa Code
│       │   │   ├── ui.qml
│       │   │   ├── assets/
│       │   │   └── test_logic.py
│       │   ├── exp03_yoga_robot/
│       │   │   ├── logic.py         # Yoga Robot — pose matching
│       │   │   ├── ui.qml
│       │   │   ├── poses.toml       # Định nghĩa 5 tư thế mục tiêu
│       │   │   ├── assets/
│       │   │   └── test_logic.py
│       │   ├── exp04_smile_charge/
│       │   │   ├── logic.py         # Mặt Cười Sạc Pin Robot
│       │   │   ├── ui.qml
│       │   │   ├── assets/
│       │   │   └── test_logic.py
│       │   ├── exp05_turtle_logo/
│       │   │   ├── logic.py         # Hình Học Rùa Logo
│       │   │   ├── logo_interp.py   # Logo interpreter (TIẾN/QUAY)
│       │   │   ├── ui.qml
│       │   │   ├── assets/
│       │   │   └── test_logic.py
│       │   ├── exp06_photo_booth/
│       │   │   ├── logic.py         # Photo Booth Cổng Làng
│       │   │   ├── ui.qml
│       │   │   ├── backgrounds/     # Sân Đình, Lũy Tre, Sân FGC, Sao Hỏa
│       │   │   └── test_logic.py
│       │   └── exp07_neo_tre_vision/
│       │       ├── logic.py         # Neo Tre Hỏi Đáp Vision
│       │       ├── ui.qml
│       │       ├── prompts.toml     # System prompt Socratic tiếng Việt
│       │       ├── assets/          # Nhân vật Neo Tre
│       │       └── test_logic.py
│       │
│       ├── services/           # [Application layer]
│       │   ├── __init__.py
│       │   ├── app_controller.py    # QObject exposed to QML — root facade
│       │   ├── experience_manager.py# Load/unload experience lifecycle
│       │   ├── photo_service.py     # Async wrapper PhotoCapture
│       │   ├── qwen_service.py      # Async wrapper QwenClient
│       │   └── share_service.py     # Async wrapper ShareServer
│       │
│       ├── ui/                 # [Giao diện chung]
│       │   ├── __init__.py
│       │   ├── image_provider.py    # QQuickImageProvider cho camera + composite
│       │   ├── qml_loader.py        # QQmlApplicationEngine wrapper
│       │   └── qml/
│       │       ├── MainWindow.qml
│       │       ├── pages/
│       │       │   ├── SplashScreen.qml
│       │       │   ├── ExperienceHubPage.qml
│       │       │   ├── ExperienceContainerPage.qml
│       │       │   ├── PhotoReviewPage.qml
│       │       │   └── IdleAttractScreen.qml
│       │       ├── components/
│       │       │   ├── ExperienceCard.qml
│       │       │   ├── CameraPreview.qml      # webcam + skeleton overlay
│       │       │   ├── SkeletonOverlay.qml    # vẽ landmarks lên preview
│       │       │   ├── QRDisplay.qml
│       │       │   ├── ScoreBadge.qml
│       │       │   ├── CountdownOverlay.qml
│       │       │   ├── HintBar.qml
│       │       │   └── StatusBanner.qml
│       │       └── singletons/
│       │           ├── qmldir
│       │           ├── NeoConstants.qml       # design tokens
│       │           ├── NeoAudio.qml
│       │           ├── AppState.qml
│       │           └── VisionState.qml        # landmarks realtime → QML
│       │
│       ├── utils/              # [Tiện ích]
│       │   ├── __init__.py
│       │   ├── signal_bus.py        # Centralized pyqtSignal hub
│       │   ├── cv_qt_bridge.py      # cv2 numpy ↔ QImage
│       │   ├── landmark_math.py     # Tính góc khớp, cosine similarity tư thế
│       │   ├── network.py           # Lấy local IP cho share URL
│       │   └── logging_config.py
│       │
│       └── resources/          # [Tài nguyên chung]
│           ├── sounds/
│           │   ├── select.wav
│           │   ├── success.wav
│           │   ├── capture.wav
│           │   └── error.wav
│           ├── fonts/
│           │   └── BeVietnamPro-Regular.ttf
│           └── images/
│               ├── logo_de_foundation.png
│               └── splash.png
│
├── models/                     # [Model AI — tải khi cài, không commit]
│   ├── mediapipe/              # .task / .tflite cho Pose/Hands/Face/Selfie
│   ├── qwen/                   # qwen3.5-0.8b-q4.gguf (local fallback)
│   ├── whisper/                # whisper-tiny-vi (game 7)
│   └── piper/                  # vi-VN voice (game 7)
│
├── firmware/                   # [Tùy chọn — ThingBot LED feedback]
│   └── thingbot_gate/
│       ├── thingbot_gate.ino   # LED chỉ báo trạng thái — KHÔNG bắt buộc
│       └── README.md
│
├── deployment/                 # [Triển khai NEO One]
│   ├── install-armbian.sh           # Cài deps + tải model
│   ├── makervigate.service          # systemd unit cho kiosk mode
│   ├── download-models.sh           # Tải MediaPipe/Qwen/Whisper/Piper
│   └── udev/
│       └── 99-webcam.rules          # Stable /dev/makervigate-cam symlink
│
├── tests/                      # [Bộ test]
│   ├── conftest.py                  # Fixtures (Qt app, mock webcam, vision sim)
│   ├── unit/
│   │   ├── test_vision_engine.py
│   │   ├── test_gesture_detector.py
│   │   ├── test_experience_runtime.py
│   │   ├── test_photo_capture.py
│   │   ├── test_qwen_client.py
│   │   └── test_share_server.py
│   ├── integration/
│   │   ├── test_vision_to_experience.py
│   │   └── test_capture_to_qr.py
│   └── e2e/
│       └── test_full_experience_flow.py
│
└── scripts/
    ├── run_dev.sh                   # macOS dev: python -m + vision simulator
    ├── run_neo_one.sh               # NEO One: + camera + model thật
    └── record_vision_fixture.sh     # Ghi clip mẫu để test offline
```

---

## 5. Design patterns

### 5.1 SignalBus pattern (kế thừa NeoStopMotion)

Các module giao tiếp qua một hub trung tâm `utils/signal_bus.py`, tránh phụ thuộc trực tiếp.

```
VisionEngine      --vision_frame_ready(VisionFrame)--> SignalBus
                                                         │
                                                         ├── VisionRouter.route()
                                                         └── VisionState (QML) cập nhật

GestureDetector   --gesture_detected(str)-------------> SignalBus
                                                         └── Experience.on_gesture()

ExperienceManager --experience_started(str)-----------> SignalBus
                                                         └── VisionEngine.set_active_modules()

ExperienceRuntime --score_updated(int)----------------> SignalBus
                                                         └── ScoreBadge.qml

PhotoCapture      --photo_captured(PhotoResult)-------> SignalBus
                                                         ├── QwenService.request_caption()
                                                         └── ShareService.generate_qr()

QwenClient        --qwen_response_ready(str)----------> SignalBus
                                                         └── Experience / PhotoReviewPage

ShareServer       --share_qr_ready(str, str)----------> SignalBus
                                                         └── PhotoReviewPage.show(qr, url)
```

**Danh sách Signals chính** (`utils/signal_bus.py`):

| Nhóm | Signal | Payload | Mục đích |
| --- | --- | --- | --- |
| Vision | `vision_frame_ready` | `VisionFrame` | Landmarks 1 khung hình |
| Vision | `vision_camera_ready` | - | Webcam mở thành công |
| Vision | `vision_camera_error` | `str` | Lỗi webcam |
| Vision | `gesture_detected` | `str` | WAVE / POINT / V_SIGN / SMILE / OPEN_PALM... |
| Experience | `experience_selected` | `str` | exp_id người dùng chọn ở Hub |
| Experience | `experience_started` | `str` | Trải nghiệm đã nạp xong, bắt đầu |
| Experience | `experience_ended` | `str, dict` | exp_id, summary (điểm, thời lượng) |
| Experience | `score_updated` | `int` | Điểm hiện tại |
| Experience | `experience_progress` | `float` | 0.0 → 1.0 (vd 3/5 tư thế) |
| Photo | `photo_capture_requested` | `dict` | Tham số chụp (nền, overlay) |
| Photo | `photo_captured` | `PhotoResult` | Ảnh đã lưu |
| Qwen | `qwen_request_started` | `str` | Loại yêu cầu: caption / dialogue |
| Qwen | `qwen_response_ready` | `str` | Văn bản tiếng Việt trả về |
| Qwen | `qwen_failed` | `str` | Lỗi (timeout / offline) |
| Voice | `voice_transcribed` | `str` | Câu nói của trẻ (game 7) |
| Voice | `voice_speaking_done` | - | Neo Tre nói xong |
| Share | `share_qr_ready` | `str, str` | url, qr_path |
| App | `status_message` | `str, str` | level, message |
| App | `idle_timeout` | - | Không tương tác → về màn hình chờ |

### 5.2 Experience Plugin pattern (MỚI — điểm khác biệt cốt lõi)

Đây là pattern quan trọng nhất của NeoMakerViGate. Mỗi trải nghiệm là một **plugin độc lập** implement chung một interface trừu tượng. Lý do: 7 trải nghiệm (và sẽ còn thêm) — không thể nhét hết vào một file; mỗi sinh viên Maker cần code được một game riêng mà không đụng tới game của người khác.

```python
# experiences/experience_base.py
from typing import Protocol
from neo_makervigate.core.models import VisionFrame, ExperienceMeta

class Experience(Protocol):
    """Interface mọi trải nghiệm phải implement."""

    meta: ExperienceMeta          # id, title, age_range, icon...

    # MediaPipe module nào cần bật cho trải nghiệm này
    vision_modules: list[str]     # vd ["hands"], ["pose"], ["face"], ["selfie","pose"]
    needs_qwen: bool              # exp06, exp07 = True
    needs_voice: bool             # exp07 = True

    def on_enter(self) -> None:
        """Khởi tạo state, nạp asset. Gọi 1 lần khi vào trải nghiệm."""
        ...

    def on_vision_frame(self, frame: VisionFrame) -> None:
        """Nhận landmarks mỗi khung hình (~15-30fps). Cập nhật game state."""
        ...

    def on_gesture(self, gesture: str) -> None:
        """Nhận sự kiện cử chỉ rời rạc (WAVE, V_SIGN...)."""
        ...

    def on_qwen_response(self, text: str) -> None:
        """Nhận kết quả từ Qwen (chỉ trải nghiệm needs_qwen=True)."""
        ...

    def render_state(self) -> dict:
        """Trả về state hiện tại để đẩy lên QML (score, vị trí sprite...)."""
        ...

    def get_qml_path(self) -> str:
        """Đường dẫn file ui.qml của trải nghiệm này."""
        ...

    def on_exit(self) -> None:
        """Dọn dẹp khi rời trải nghiệm. Giải phóng asset."""
        ...
```

`experiences/registry.py` quét thư mục `experiences/exp*` lúc khởi động, tự động đăng ký mọi plugin. Thêm trải nghiệm mới = thêm một thư mục, **không sửa lõi**.

```python
# experiences/registry.py — rút gọn
def discover_experiences() -> dict[str, type[Experience]]:
    registry = {}
    for pkg in iter_modules(experiences.__path__):
        if pkg.name.startswith("exp"):
            module = import_module(f"neo_makervigate.experiences.{pkg.name}.logic")
            exp_class = module.EXPERIENCE      # mỗi logic.py export biến EXPERIENCE
            registry[exp_class.meta.id] = exp_class
    return registry
```

### 5.3 Worker Thread pattern (kế thừa NeoStopMotion)

Mọi tác vụ nặng chạy trên `QThread` riêng để UI luôn ≥30fps trên NEO One 2GB:

| Worker | Vòng lặp | Output |
| --- | --- | --- |
| **VisionWorker** | Đọc webcam + chạy MediaPipe ~15-30fps | emit `vision_frame_ready` |
| **QwenWorker** | Inference local llama.cpp HOẶC HTTP call DashScope | emit `qwen_response_ready` |
| **VoiceWorker** | Whisper STT (blocking) + Piper TTS | emit `voice_transcribed` / `voice_speaking_done` |
| **ShareServerWorker** | `http.server.serve_forever()` | serve file ảnh trong LAN |

**Lưu ý quan trọng:** VisionWorker là trục nóng nhất — nó vừa đọc webcam vừa chạy MediaPipe. Trên NEO One phải dùng `model_complexity=0` hoặc `1` cho Pose, và chỉ bật module MediaPipe mà trải nghiệm hiện tại cần (không chạy cả Pose + Hands + Face cùng lúc). `ExperienceManager` báo cho `VisionEngine` qua signal `experience_started` để chuyển module.

### 5.4 QML Image Provider pattern (kế thừa NeoStopMotion)

Khung hình webcam (kèm skeleton overlay tùy chọn) đẩy lên QML qua `QQuickImageProvider`. Khác NeoStopMotion: ở đây image provider phục vụ **camera preview với landmarks vẽ đè**, và **ảnh composite** (người + nền AR) cho game 6.

```python
# ui/image_provider.py
class CameraImageProvider(QQuickImageProvider):
    def __init__(self, vision_engine):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.vision = vision_engine

    def requestImage(self, id, requestedSize):
        # id = "preview" (raw) hoặc "skeleton" (có overlay) hoặc "composite"
        if id.startswith("composite"):
            frame = self.vision.get_composite_frame()   # người + nền AR
        elif id.startswith("skeleton"):
            frame = self.vision.get_annotated_frame()    # webcam + landmarks
        else:
            frame = self.vision.get_raw_frame()
        qimage = cv_to_qimage(frame)
        return qimage, qimage.size()
```

### 5.5 Singleton pattern cho global state (kế thừa NEOSTEM)

4 Singleton QML — phẳng, không chồng chéo. So với NeoStopMotion thêm `VisionState`:

```qml
// VisionState.qml (Singleton)
pragma Singleton
import QtQuick
QtObject {
    // Cập nhật mỗi khung hình từ VisionWorker (qua AppController)
    property var poseLandmarks: []        // 33 điểm — [{x,y,z,visibility}, ...]
    property var handLandmarks: []        // 21 điểm × số bàn tay
    property var faceLandmarks: []        // 468 điểm (khi cần)
    property string lastGesture: ""       // WAVE / POINT / V_SIGN / SMILE
    property real visionFps: 0.0
    property bool cameraConnected: false
    property int previewCounter: 0        // bust cache cho Image
}
```

```qml
// AppState.qml (Singleton)
pragma Singleton
import QtQuick
QtObject {
    property string currentExperience: ""   // "" = đang ở Hub
    property string status: "idle"          // idle | hub | playing | reviewing
    property int score: 0
    property real progress: 0.0
    property string sessionId: ""
}
```

### 5.6 StackView navigation (kế thừa NEOSTEM)

`MainWindow.qml` là `ApplicationWindow` chứa `StackView`. Khác NeoStopMotion ở chỗ có vòng lặp quay về **Hub** chứ không phải về một trang capture duy nhất:

```
SplashScreen → ExperienceHubPage ⇄ ExperienceContainerPage → PhotoReviewPage → ExperienceHubPage
                     ↑                                                              │
                     └──────────────── (chọn trải nghiệm khác) ─────────────────────┘
                     │
              IdleAttractScreen ──(chạm màn hình / phát hiện người)──> ExperienceHubPage
```

### 5.7 Hardware abstraction + Vision Simulator (kế thừa NeoStopMotion UART Simulator)

Tách `VisionEngine` thành interface để swap với `VisionSimulator` cho dev trên máy không có NEO One:

```python
class VisionSource(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def set_active_modules(self, modules: list[str]) -> None: ...
    # emit qua SignalBus

class VisionEngine:        # thật — webcam + MediaPipe
    ...

class VisionSimulator:     # dev mode — phát lại clip .mp4 đã ghi sẵn
    # HOẶC sinh landmarks giả từ chuột/bàn phím
    # Space = giả lập WAVE, V = giả lập V_SIGN...
    ...
```

App init đọc env `NEO_MAKERVIGATE_VISION=simulator` để chọn. Tăng tốc dev cycle 5-10× — sinh viên Maker code game trên laptop không cần NEO One.

---

## 6. Mô hình dữ liệu (`core/models.py`)

```python
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

class AppStatus(str, Enum):
    IDLE = "idle"
    HUB = "hub"
    PLAYING = "playing"
    REVIEWING = "reviewing"
    ERROR = "error"

class Gesture(str, Enum):
    WAVE = "WAVE"
    POINT = "POINT"
    OPEN_PALM = "OPEN_PALM"
    V_SIGN = "V_SIGN"
    SMILE = "SMILE"
    T_POSE = "T_POSE"

@dataclass
class Landmark:
    x: float          # toạ độ chuẩn hoá 0.0-1.0
    y: float
    z: float = 0.0
    visibility: float = 1.0

@dataclass
class VisionFrame:
    """Một khung hình đã qua MediaPipe."""
    timestamp: datetime
    width: int
    height: int
    pose: list[Landmark] = field(default_factory=list)        # 33 điểm
    hands: list[list[Landmark]] = field(default_factory=list) # 0-2 bàn tay × 21
    face: list[Landmark] = field(default_factory=list)        # 468 điểm
    has_person: bool = False
    raw_jpeg_path: Path | None = None   # chỉ lưu khi cần chụp

@dataclass
class ExperienceMeta:
    id: str                    # "exp01_wave_cricket"
    title: str                 # "Vẫy Chào Dế"
    subtitle: str              # "Wave Hello Cricket"
    age_min: int
    age_max: int
    vision_modules: list[str]  # ["hands"]
    needs_qwen: bool = False
    needs_voice: bool = False
    needs_internet: bool = False
    icon_path: str = ""
    dev_days: int = 0          # ước lượng — phục vụ WBS

@dataclass
class ExperienceSummary:
    """Kết quả một lượt chơi — phục vụ KPI."""
    experience_id: str
    started_at: datetime
    ended_at: datetime
    duration_seconds: float
    score: int = 0
    completed: bool = False
    photo_taken: bool = False

@dataclass
class PhotoResult:
    success: bool
    photo_id: str              # "photo_YYYY_MM_DD_HHMMSS_expNN"
    original_path: Path | None
    composite_path: Path | None    # ảnh đã ghép nền AR (nếu có)
    caption: str = ""              # Qwen sinh (nếu có)
    qr_path: Path | None = None
    download_url: str | None = None
    experience_id: str = ""
    error_message: str | None = None
```

### 6.1 File system layout

```
/home/maker/makervigate/
├── photos/
│   ├── photo_2026_05_14_143022_exp06/
│   │   ├── original.jpg          (ảnh webcam gốc, 1280×720)
│   │   ├── composite.jpg         (đã ghép nền Sân Đình — game 6)
│   │   ├── caption.txt           (Qwen sinh: "Hôm nay một con dế nhỏ...")
│   │   ├── qr.png                (QR trỏ tới download URL)
│   │   └── meta.json             (PhotoResult serialized)
│   ├── photo_2026_05_14_150210_exp05/
│   │   ├── original.jpg          (ảnh bức tranh rùa Logo vẽ được)
│   │   ├── qr.png
│   │   └── meta.json
│   └── ...
├── sessions/                     (log lượt chơi — KPI)
│   └── session_2026_05_14.jsonl  (mỗi dòng = 1 ExperienceSummary)
└── _shared/                      (logo, âm thanh fallback)
```

**Khác NeoStopMotion:** không có thư mục `frames/` và `output.mp4` — NeoMakerViGate chỉ lưu **ảnh tĩnh**. Mỗi ảnh là một thư mục riêng để gom ảnh gốc + composite + caption + QR.

---

## 7. Luồng dữ liệu chính

### 7.1 Khởi động ứng dụng

```
$ python -m neo_makervigate
       │
       ▼
  app.py main()
       │
       ├─ QApplication(argv)
       ├─ Load defaults.toml
       ├─ Init logger (loguru → /var/log/makervigate/app.log)
       ├─ Init SignalBus (singleton)
       │
       ├─ experiences/registry.discover_experiences()  → 7 plugin đăng ký
       │
       ├─ Init core services:
       │    ├─ VisionEngine.start()       → mở webcam; nạp MediaPipe model
       │    ├─ QwenClient.init()          → kiểm tra local model / API key
       │    ├─ ShareServer.start()        → http.server :8000 background
       │    └─ PhotoCapture()             → sẵn sàng
       │
       ├─ Init AppController (root QObject, exposed to QML)
       ├─ Init ExperienceManager (giữ registry 7 plugin)
       ├─ Register CameraImageProvider("camera", vision_engine)
       │
       ├─ qml_engine.load("MainWindow.qml")
       └─ app.exec()  →  SplashScreen → ExperienceHubPage (lưới 7 thẻ)
```

### 7.2 Chọn và nạp một trải nghiệm

```
[Đứa trẻ chạm thẻ trên Hub — HOẶC vẫy tay chọn — HOẶC Thợ Cả chạm]
       │
       ▼
ExperienceHubPage → AppController.select_experience("exp03_yoga_robot")
       │
       ▼
ExperienceManager.load("exp03_yoga_robot")
       │
       ├─ exp_class = registry["exp03_yoga_robot"]
       ├─ instance = exp_class()
       ├─ instance.on_enter()                    # nạp asset, khởi tạo state
       │
       ├─ SignalBus.experience_started.emit("exp03_yoga_robot")
       │      │
       │      └─ VisionEngine.set_active_modules(["pose"])   # chỉ bật Pose
       │
       ├─ AppState.currentExperience = "exp03_yoga_robot"
       └─ StackView.push(ExperienceContainerPage)
              │
              └─ Loader { source: instance.get_qml_path() }  # nạp ui.qml của game
```

### 7.3 Vòng lặp vision (trục nóng — chạy nền liên tục)

```
VisionWorker (QThread, ~15-30fps)
       │
       ├─ ret, frame = cv2.VideoCapture.read()
       ├─ results = mediapipe_solution.process(frame)   # CHỈ module đang active
       ├─ vision_frame = build_vision_frame(results)
       │
       ▼ pyqtSignal
SignalBus.vision_frame_ready.emit(vision_frame)
       │
       ├──> VisionRouter.route(vision_frame)
       │       │
       │       └─ active_experience.on_vision_frame(vision_frame)
       │              │
       │              └─ (game cập nhật state — vd so 33 điểm với tư thế mục tiêu)
       │
       ├──> GestureDetector.feed(vision_frame)
       │       │
       │       └─ nếu phát hiện cử chỉ → SignalBus.gesture_detected.emit("T_POSE")
       │              │
       │              └─ active_experience.on_gesture("T_POSE")
       │
       └──> VisionState (QML) cập nhật landmarks → SkeletonOverlay.qml vẽ lại
```

### 7.4 Vòng lặp render trải nghiệm

```
QML Timer trong ui.qml (33ms / ~30fps)
       │
       ▼
AppController.poll_experience_state()
       │
       ▼
active_experience.render_state()  →  dict {score, sprites, progress, ...}
       │
       ▼
Cập nhật AppState.score, AppState.progress + property riêng của game
       │
       ▼
QML render → màn hình NEO One
```

### 7.5 Chụp ảnh + chia sẻ qua QR (luồng xuyên suốt mọi trải nghiệm)

Đây là luồng Tuấn yêu cầu nhấn mạnh — **chụp ảnh, gửi qua mạng qua mã QR**. Bất kỳ trải nghiệm nào cũng có thể kích hoạt: game 6 chụp ảnh trước Sân Đình, game 5 lưu bức tranh rùa Logo, game 3 tự chụp khi đạt tư thế đẹp.

```
[Trải nghiệm gọi chụp ảnh]
   active_experience phát: SignalBus.photo_capture_requested.emit(params)
   params = {background: "san_dinh", overlay: "logo", caption_prompt: "..."}
       │
       ▼
PhotoService.handle_capture(params)
       │
       ├─ frame = PhotoCapture.snap()                  # cv2 chụp 1 khung nét
       ├─ original_path = lưu original.jpg
       │
       ├─ nếu params.background:                        # game 6 — ghép nền AR
       │     mask = VisionEngine.get_selfie_mask()      # MediaPipe Selfie Seg
       │     composite = ghép(frame, mask, background)
       │     composite_path = lưu composite.jpg
       │
       ├─ nếu params.caption_prompt:                    # game 6 — caption Qwen
       │     SignalBus.qwen_request_started.emit("caption")
       │     QwenWorker: caption = QwenClient.describe(composite, prompt)
       │     lưu caption.txt
       │
       ├─ SignalBus.photo_captured.emit(PhotoResult)
       │
       ▼
ShareService.generate_qr(photo_result)
       │
       ├─ url = ShareServer.get_download_url(photo_id)
       │        # http://192.168.x.x:8000/photos/photo_..._exp06/composite.jpg
       ├─ qr_path = ShareServer.generate_qr(url)        # qrcode + Pillow
       │
       ├─ SignalBus.share_qr_ready.emit(url, qr_path)
       │
       ▼
StackView.push(PhotoReviewPage)
       ├─ Ảnh lớn (composite hoặc original)
       ├─ Caption tiếng Việt (nếu có) — "Hôm nay một con dế nhỏ tên Minh..."
       ├─ QR code lớn
       ├─ Hướng dẫn: "Ba mẹ ơi, quét mã bằng Zalo để tải ảnh về!"
       │     + hiển thị SSID WiFi nếu cần
       └─ Nút "Chơi tiếp" → quay lại ExperienceHubPage
```

### 7.6 Trải nghiệm dùng Qwen — đối thoại (game 7)

```
[Đứa trẻ giơ vật trước camera + nói câu hỏi]
       │
       ├─ VoiceWorker: Whisper STT → SignalBus.voice_transcribed.emit("đây là cái gì?")
       ├─ PhotoCapture.snap() → ảnh hiện tại
       │
       ▼
exp07.on_vision_frame() + on voice → QwenService.ask(image, question, history)
       │
       ▼ QwenWorker (QThread)
QwenClient.chat(
    image = ảnh webcam,
    messages = [system_prompt_socratic_vi, ...history, user_question],
    model = "qwen3.5-4b" (API) HOẶC "qwen3.5-0.8b" (local)
)
       │
       ▼
SignalBus.qwen_response_ready.emit("Câu hỏi hay đấy! Em thử nhìn xem nó có mấy bánh xe?")
       │
       ├─ exp07.on_qwen_response(text) → hiển thị bong bóng thoại Neo Tre
       └─ VoiceWorker: Piper TTS đọc câu trả lời tiếng Việt qua loa
              │
              └─ SignalBus.voice_speaking_done.emit() → sẵn sàng nghe câu tiếp
```

---

## 8. Bảy trải nghiệm — đặc tả tóm tắt

Chi tiết đầy đủ ở `DOC/EXPERIENCES.md`. Bảng dưới là tóm tắt để định hướng kiến trúc — tham chiếu Storyboard "Trò Chơi Cổng Làng" v0.1.

| # | Plugin | Tên | MediaPipe module | Qwen | Voice | Internet | Dev |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 01 | `exp01_wave_cricket` | Vẫy Chào Dế | Hands (21) | — | — | Offline | 3 ngày |
| 02 | `exp02_catch_bug` | Tóm Bug Sửa Code | Hands (pointing) | — | — | Offline | 4 ngày |
| 03 | `exp03_yoga_robot` | Yoga Robot | Pose (33) | — | — | Offline | 5 ngày |
| 04 | `exp04_smile_charge` | Mặt Cười Sạc Pin Robot | Face Mesh (468) | — | — | Offline | 3 ngày |
| 05 | `exp05_turtle_logo` | Hình Học Rùa Logo | Hands (finger trail) | — | — | Offline | 5 ngày |
| 06 | `exp06_photo_booth` | Photo Booth Cổng Làng | Selfie Seg + Pose | ✅ caption | — | Cần (caption) | 7 ngày |
| 07 | `exp07_neo_tre_vision` | Neo Tre Hỏi Đáp Vision | — (Qwen-VL trực tiếp) | ✅ đối thoại | ✅ | Cần (ổn định) | 5 ngày |

**Hệ quả kiến trúc rút ra từ bảng:**

1. **VisionEngine phải hỗ trợ 4 module MediaPipe** (Hands, Pose, Face Mesh, Selfie Segmentation) nhưng **chỉ bật module mà trải nghiệm hiện tại cần** — đây là lý do `set_active_modules()` tồn tại. Trên NEO One 2GB không thể chạy cả 4 cùng lúc.

2. **Hands là module được dùng lại nhiều nhất** (game 1, 2, 5) — `GestureDetector` cho bàn tay (WAVE, POINT, OPEN_PALM) cần được làm chắc và tái sử dụng.

3. **5/7 trải nghiệm chạy offline hoàn toàn** — chúng chỉ phụ thuộc MediaPipe, có thể chơi cả khi mạng FPT Shop chập chờn. Đây là quyết định thiết kế quan trọng cho độ tin cậy.

4. **Qwen có hai chế độ** — game 6 chỉ cần Qwen sinh một caption ngắn (chấp nhận chờ 1-2s, có thể local 0.8B); game 7 cần đối thoại nhiều vòng có độ trễ thấp (nên dùng API 4B khi có internet). `QwenClient` phải trừu tượng hóa cả hai sau một interface.

5. **Chỉ game 7 cần Voice** — `VoiceWorker` (Whisper + Piper) chỉ khởi động khi nạp `exp07`, không chạy nền lãng phí RAM.

6. **PhotoCapture phục vụ mọi trải nghiệm** — không chỉ game 6. Game 5 lưu tranh, game 3 chụp tư thế. Vì thế PhotoCapture nằm ở Core Layer, không nằm trong plugin.

---

## 9. Vision Pipeline (MediaPipe) — `core/vision_engine.py`

### 9.1 Bốn solution và khi nào bật

| Solution MediaPipe | Output | Trải nghiệm dùng | Chi phí tương đối |
| --- | --- | --- | --- |
| **Hands** | 21 điểm × ≤2 bàn tay | exp01, exp02, exp05 | Nhẹ |
| **Pose** | 33 điểm thân người | exp03 | Trung bình (dùng `model_complexity=1`) |
| **Face Mesh** | 468 điểm khuôn mặt | exp04 | Trung bình |
| **Selfie Segmentation** | mask người/nền | exp06 | Nhẹ |

`exp07` không dùng MediaPipe trực tiếp — nó gửi ảnh thô cho Qwen-VL. Nhưng vẫn có thể bật Hands nhẹ để biết "đứa trẻ đang giơ vật lên" làm tín hiệu chụp.

### 9.2 Cấu trúc VisionEngine

```python
# core/vision_engine.py — rút gọn
class VisionEngine:
    def __init__(self, config):
        self._solutions = {}          # lazy-init từng MediaPipe solution
        self._active_modules = []
        self._cap = None              # cv2.VideoCapture
        self._last_frame = None       # khung gần nhất (cho PhotoCapture)

    def set_active_modules(self, modules: list[str]):
        """ExperienceManager gọi khi chuyển trải nghiệm.
        Đóng solution không cần, mở solution cần."""
        for m in self._active_modules:
            if m not in modules:
                self._solutions[m].close()
        for m in modules:
            if m not in self._solutions:
                self._solutions[m] = self._create_solution(m)
        self._active_modules = modules

    def process(self, frame) -> VisionFrame:
        """VisionWorker gọi mỗi khung hình."""
        vf = VisionFrame(timestamp=now(), width=..., height=...)
        if "pose" in self._active_modules:
            vf.pose = self._solutions["pose"].process(frame)
        if "hands" in self._active_modules:
            vf.hands = self._solutions["hands"].process(frame)
        # ... face, selfie
        self._last_frame = frame
        return vf

    def get_selfie_mask(self):
        """PhotoCapture gọi khi game 6 ghép nền."""
        ...
```

### 9.3 Gesture Detector — `core/gesture_detector.py`

`GestureDetector` nhận chuỗi `VisionFrame` và phát hiện **cử chỉ rời rạc** từ landmarks liên tục. Đây là lớp tách biệt khỏi từng game để tái sử dụng:

| Cử chỉ | Cách phát hiện (rút gọn) | Trải nghiệm dùng |
| --- | --- | --- |
| `WAVE` | Cổ tay dao động trái-phải > ngưỡng trong 1s | exp01 |
| `POINT` | Ngón trỏ duỗi, các ngón khác cụp | exp02, exp05 |
| `OPEN_PALM` | 5 ngón duỗi | (dự phòng — chọn menu) |
| `V_SIGN` | Ngón trỏ + giữa duỗi tạo chữ V | exp06 (kích hoạt chụp) |
| `SMILE` | Độ cong khoé miệng (Face Mesh) > ngưỡng | exp04 |
| `T_POSE` | Hai tay dang ngang, so với 33 điểm Pose | exp03 (một trong các tư thế) |

Lưu ý `landmark_math.py` chứa hàm dùng chung: tính góc giữa 3 điểm, cosine similarity giữa hai bộ landmarks (để game 3 chấm điểm tư thế), độ cong khoé miệng.

---

## 10. Qwen 3.5 Integration — `core/qwen_client.py`

### 10.1 Hai chế độ sau một interface

```python
class QwenBackend(Protocol):
    def describe(self, image, prompt: str) -> str: ...
    def chat(self, image, messages: list[dict]) -> str: ...

class QwenLocalBackend:    # llama.cpp / Ollama — qwen3.5-0.8b-q4.gguf
    # Chạy trên NEO One, offline, chậm hơn (~2-5s/câu)
    # Dùng cho: caption game 6 khi không có internet
    ...

class QwenAPIBackend:      # DashScope HTTP API — qwen3.5-4b / flash
    # Cần internet, nhanh (~1s/câu), rẻ
    # Dùng cho: đối thoại game 7, caption game 6 khi có internet
    ...

class QwenClient:
    """Tự chọn backend theo config + tình trạng mạng."""
    def __init__(self, config):
        self.mode = config.qwen.mode   # "auto" | "local" | "api"
        ...
    def _select_backend(self) -> QwenBackend:
        if self.mode == "local":
            return self._local
        if self.mode == "api":
            return self._api
        # auto: thử ping API, fail thì fallback local
        return self._api if network_available() else self._local
```

### 10.2 System prompt — phương pháp Socratic tiếng Việt

`exp07_neo_tre_vision/prompts.toml` chứa system prompt định hình tính cách Neo Tre — **không cho đáp án, chỉ đặt câu hỏi gợi mở**, đúng tinh thần Constructionism của Papert. Prompt là tài sản nội dung do nhóm sư phạm Maker Việt biên soạn, tách khỏi code để chỉnh sửa không cần lập trình viên.

### 10.3 Ranh giới an toàn

- Mọi phản hồi Qwen cho trẻ em đi qua một bộ lọc từ khóa cơ bản trước khi hiển thị/đọc.
- Game 6: caption sinh ra được giới hạn độ dài, chủ đề tích cực (prompt ràng buộc), và **Thợ Cả có thể tắt tính năng caption** trong config nếu mạng kém.
- Không ảnh nào của trẻ em rời khỏi NEO One trừ khi phụ huynh chủ động quét QR trong mạng LAN. Qwen API (nếu dùng) chỉ nhận ảnh tạm thời để sinh caption — ghi rõ trong `DOC/QWEN_SETUP.md` và cấu hình được tắt.

---

## 11. Chụp ảnh & Chia sẻ qua mã QR — `core/photo_capture.py` + `core/share_server.py`

Kế thừa gần như nguyên vẹn `ShareServer` của NeoStopMotion — đây là phần đã được chứng minh hoạt động.

### 11.1 PhotoCapture

```python
# core/photo_capture.py — rút gọn
class PhotoCapture:
    def snap(self) -> Path:
        """Chụp 1 khung hình nét nhất từ buffer webcam, lưu original.jpg."""
        frame = self.vision_engine.get_sharp_frame()   # chọn khung nét
        path = self._save_jpeg(frame, "original.jpg")
        return path

    def composite(self, frame, mask, background_name: str) -> Path:
        """Ghép người (từ selfie mask) lên nền AR. Dùng cho game 6."""
        bg = load_background(background_name)
        result = blend(frame, mask, bg)
        return self._save_jpeg(result, "composite.jpg")
```

### 11.2 ShareServer (kế thừa NeoStopMotion §7.5)

- `http.server` chạy trên `QThread`, phục vụ thư mục `photos/` trong mạng LAN của FPT Shop.
- URL tải: `http://<local_ip>:8000/photos/<photo_id>/<file>` — `<local_ip>` lấy động qua `utils/network.py`.
- `qrcode` + `Pillow` sinh ảnh QR trỏ tới URL đó.
- Phụ huynh quét QR bằng Zalo/camera điện thoại → tải ảnh về.
- **Privacy-first, no cloud** — giống NeoStopMotion §12.7: ảnh chỉ truy cập được trong WiFi LAN, không upload internet ở v1.0.

### 11.3 Khác biệt so với NeoStopMotion

| | NeoStopMotion | NeoMakerViGate |
| --- | --- | --- |
| Nội dung chia sẻ | 1 video MP4 + GIF/session | 1 ảnh JPG (original / composite)/lượt |
| Ai kích hoạt | Nút EXPORT trên ThingBot | Bất kỳ trải nghiệm nào gọi `photo_capture_requested` |
| Xử lý trước khi share | ffmpeg ghép video | (tùy chọn) ghép nền AR + caption Qwen |
| Trang hiển thị QR | SuccessPage | PhotoReviewPage |

---

## 12. Design tokens (`NeoConstants.qml` — port từ NEOSTEM, palette Dế Foundation)

```qml
// Singleton — design tokens
pragma Singleton
import QtQuick

QtObject {
    // Brand colors — Dế Foundation (đồng bộ Storyboard v0.1)
    readonly property color tre:        "#5C8A3A"   // Tre xanh — màu chủ đạo
    readonly property color treDark:    "#3F6627"
    readonly property color de:         "#C77B2C"   // Dế cam ấm — accent chính
    readonly property color gach:       "#B85C38"   // Gạch terracotta
    readonly property color song:       "#2A5C8A"   // Xanh nước
    readonly property color accent:     "#E8C547"   // Vàng lúa — sao thành tích
    readonly property color background: "#FAF6EE"   // Giấy kem
    readonly property color surface:    "#FFFCF5"
    readonly property color textPrimary:"#1F2937"
    readonly property color success:    "#2E7D32"
    readonly property color warning:    "#FF8F00"
    readonly property color error:      "#C62828"

    // Typography (Be Vietnam Pro)
    property bool largeTextMode: false
    readonly property real textScale:    largeTextMode ? 1.25 : 1.0
    readonly property int fontTitle:     Math.round(40 * textScale)
    readonly property int fontBody:      Math.round(24 * textScale)
    readonly property int fontButton:    Math.round(24 * textScale)
    readonly property int fontScore:     Math.round(72 * textScale)  // điểm to & đậm

    // Touch targets (trẻ em — ngón tay nhỏ)
    readonly property int touchMin:      largeTextMode ? 64 : 56
    readonly property int cardWidth:     320   // ExperienceCard
    readonly property int cardHeight:    240
    readonly property int previewWidth:  1280
    readonly property int previewHeight: 720

    // Animation
    readonly property int animFast:    200
    readonly property int animNormal:  400
    readonly property int animSlow:    800

    // Vision-specific
    readonly property int targetVisionFps: 15   // ngưỡng tối thiểu chấp nhận
    readonly property color landmarkColor:  "#4ADE80"   // xanh neon vẽ skeleton
    readonly property real idleTimeoutSec:  90          // không tương tác → màn hình chờ
}
```

---

## 13. Cấu hình hệ thống (`config/defaults.toml`)

```toml
[app]
name = "NeoMakerViGate"
version = "1.0.0"
language = "vi"
debug = false
idle_timeout_seconds = 90

[vision]
webcam_index = 0
resolution_width = 1280
resolution_height = 720
target_fps = 15
pose_model_complexity = 1       # 0=nhẹ nhất, 1=cân bằng, 2=chính xác (không dùng trên NEO One)
max_num_hands = 2
auto_retry_count = 3

[qwen]
mode = "auto"                   # auto | local | api
local_model_path = "models/qwen/qwen3.5-0.8b-q4.gguf"
api_endpoint = "https://dashscope.aliyuncs.com/..."
api_model = "qwen3.5-4b"
api_timeout_seconds = 8
caption_enabled = true          # Thợ Cả tắt được khi mạng kém
caption_max_words = 40

[voice]
enabled = true                  # chỉ ảnh hưởng game 7
whisper_model = "models/whisper/whisper-tiny-vi"
piper_voice = "models/piper/vi-VN-medium"

[experiences]
# Thợ Cả bật/tắt từng trải nghiệm tại Làng cụ thể
enabled = [
  "exp01_wave_cricket", "exp02_catch_bug", "exp03_yoga_robot",
  "exp04_smile_charge", "exp05_turtle_logo", "exp06_photo_booth",
  "exp07_neo_tre_vision"
]
default_experience = ""         # "" = hiện Hub; hoặc ép 1 trải nghiệm

[storage]
photos_dir = "/home/maker/makervigate/photos"
sessions_dir = "/home/maker/makervigate/sessions"
max_photos = 200
auto_cleanup_threshold_mb = 200

[server]
http_port = 8000
qr_size = 400
wifi_ssid = ""                  # hiển thị trên PhotoReviewPage nếu cần
wifi_password = ""

[ui]
fullscreen = true
window_width = 1920
window_height = 1080
font_family = "Be Vietnam Pro"
sound_enabled = true
show_skeleton_overlay = true    # vẽ landmarks lên camera preview
```

User config override tại `~/.config/makervigate/config.toml`. Env override config (vd `NEO_MAKERVIGATE_VISION=simulator`, `NEO_MAKERVIGATE_QWEN=local`).

---

## 14. Edge cases & error handling

| Tình huống | Layer | Chiến lược | UI |
| --- | --- | --- | --- |
| Webcam không mở được | VisionEngine | Auto-retry 3 lần delay 1s; fail → emit `vision_camera_error` | Banner đỏ: "Camera đang ngủ — gọi Thợ Cả" |
| Webcam disconnect runtime | VisionWorker | Bắt `cv2.error`, retry mở lại 3 lần | Banner amber + freeze khung cuối |
| MediaPipe FPS tụt < 10 | VisionEngine | Hạ `pose_model_complexity`, giảm độ phân giải | (im lặng) + log cảnh báo |
| Không phát hiện người trong khung | VisionRouter | `has_person=False` → game hiện gợi ý | Hint: "Con đứng vào giữa khung hình nhé!" |
| Qwen API timeout | QwenClient | Fallback `QwenLocalBackend`; nếu local cũng fail → caption rỗng | Game 6: bỏ caption, vẫn lưu ảnh. Game 7: "Neo Tre suy nghĩ chậm xíu, thử lại nha" |
| Qwen local quá chậm (>10s) | QwenWorker | Hủy, dùng caption mẫu có sẵn theo nền | (im lặng) |
| Mạng FPT Shop mất | QwenClient + ShareServer | 5 game offline vẫn chạy; game 6/7 báo nhẹ; QR vẫn hoạt động trong LAN | Banner amber: "Mạng tạm nghỉ — vẫn chơi được 5 trò!" |
| Whisper nghe không rõ (game 7) | VoiceWorker | Trả chuỗi rỗng → Neo Tre hỏi lại | "Neo Tre chưa nghe rõ, em nói lại được không?" |
| Storage < 200MB | PhotoCapture | Auto xóa `photo_*` cũ nhất | Banner: "Sắp hết chỗ — đang dọn..." |
| Plugin lỗi khi `on_enter()` | ExperienceManager | Bắt exception, quay về Hub, log | "Trò này đang bảo trì — chọn trò khác nha" |
| Plugin treo trong `on_vision_frame()` | VisionRouter | Watchdog: nếu 1 frame xử lý > 500ms, ngắt trải nghiệm | Quay về Hub + log |
| QR scan không tải được | ShareServer | Kiểm tra cùng WiFi; hiện SSID + mật khẩu | "Ba mẹ ơi, kết nối WiFi: Maker_Lang_FPT" |
| Đứa trẻ bỏ đi giữa chừng | AppController | `idle_timeout` 90s không có người → tự về IdleAttractScreen | Màn hình chờ thu hút khách mới |
| Mất điện đột ngột | PhotoCapture | Ảnh JPG ghi atomic vẫn còn; khởi động lại vào Hub | Sau khởi động lại |

---

## 15. Quyết định thiết kế quan trọng

### 15.1 Experience Plugin Architecture thay vì if/else trong một file

7 trải nghiệm (và sẽ thêm) — nếu nhét vào một `AppController` khổng lồ sẽ không bảo trì nổi. Plugin architecture cho phép mỗi sinh viên Maker nhận một game, code trong một thư mục, test riêng, không đụng người khác. Thêm game thứ 8 = thêm một thư mục. **Trade-off:** thiết lập ban đầu phức tạp hơn (~2 ngày dựng `experience_base` + `registry`), nhưng tiết kiệm hàng tuần khi mở rộng.

### 15.2 Vision thay cho nút bấm vật lý — bỏ phụ thuộc ThingBot bắt buộc

NeoStopMotion cần ThingBot vì làm phim cần nút bấm chính xác. NeoMakerViGate dùng chính cơ thể đứa trẻ làm đầu vào — không cần phần cứng điều khiển. ThingBot xuống thành **tùy chọn** (chỉ để LED/buzzer feedback cho vui). **Hệ quả:** giảm chi phí và độ phức tạp lắp đặt mỗi Làng; nhưng đòi hỏi `VisionEngine` ổn định, đó là lý do có `VisionSimulator` để test.

### 15.3 Chỉ bật MediaPipe module mà trải nghiệm cần (`set_active_modules`)

NEO One 2GB RAM không chạy nổi Pose + Hands + Face + Selfie cùng lúc ở FPS chấp nhận được. Mỗi trải nghiệm khai báo `vision_modules`, `ExperienceManager` báo `VisionEngine` chuyển module khi vào game. **Critical:** đây là điểm dễ sai — nếu để cả 4 chạy nền, FPS sẽ tụt xuống dưới 5 và game giật.

### 15.4 5/7 trải nghiệm offline hoàn toàn

WiFi FPT Shop không phải lúc nào cũng ổn định. Thiết kế để 5 trải nghiệm chỉ phụ thuộc MediaPipe local — luôn chơi được. Chỉ game 6 (caption) và game 7 (đối thoại) cần internet, và cả hai đều có fallback. **Triết lý:** độ tin cậy quan trọng hơn tính năng hào nhoáng — một Cổng Làng luôn hoạt động tốt hơn một Cổng Làng đôi khi rất thông minh.

### 15.5 Qwen hai chế độ sau một interface (`QwenClient`)

Local 0.8B cho privacy + offline; API 4B cho tốc độ + chất lượng. `mode = "auto"` tự chọn theo tình trạng mạng. **Trade-off:** code phức tạp hơn một chút, nhưng cho phép cùng một bản build chạy tốt ở Làng có internet mạnh lẫn Làng vùng sâu.

### 15.6 PhotoCapture + ShareServer ở Core Layer, không ở plugin

Tuấn yêu cầu "chụp ảnh, gửi qua mạng qua mã QR" là tính năng xuyên suốt. Đặt ở Core Layer để **mọi** trải nghiệm gọi được qua signal `photo_capture_requested` — game 6 ghép nền, game 5 lưu tranh, game 3 chụp tư thế. Nếu đặt trong plugin sẽ phải lặp code 7 lần.

### 15.7 Kế thừa tối đa NeoStopMotion — không phát minh lại

SignalBus, Worker Thread, QML Image Provider, Singleton, StackView, ShareServer + QR, design tokens, hardware simulator — tất cả đã được chứng minh ở NeoStopMotion. NeoMakerViGate giữ nguyên để **đội ngũ Maker Việt chuyển giao dễ dàng** giữa hai dự án, và để tận dụng kinh nghiệm đã có. Chỉ thêm cái thực sự mới: Experience Plugin Layer + Vision Pipeline.

### 15.8 Privacy-first, no cloud (kế thừa NeoStopMotion §12.7)

Ảnh trẻ em lưu local trên NEO One. QR chỉ truy cập trong WiFi LAN. Qwen API (nếu bật) chỉ nhận ảnh tạm để sinh caption, cấu hình tắt được. Không upload internet ở v1.0.

### 15.9 Mã nguồn mở MIT

Theo cam kết Bình Dân Học STEM. Public GitHub Maker Việt sau pilot — cùng repo style với NeoStopMotion để cộng đồng học được cả hai.

### 15.10 Tái sử dụng cho các trạm tương lai

Nếu Cổng Vào thành công, kiến trúc Experience Plugin có thể tái dùng cho các trạm khác: Trạm Âm Nhạc (vẫy tay tạo nhạc), Trạm Vẽ (vẽ bằng cử chỉ), Trạm Thể Thao AR. Mỗi trạm = cùng skeleton + bộ plugin khác.

---

## 16. Phân tách công việc (Work Breakdown Structure)

Theo Storyboard "Trò Chơi Cổng Làng" v0.1 — **4 sprint × 2 tuần = 8 tuần**, team 2 backend + 1 UI + 1 nội dung/sư phạm.

### Sprint 1 — Foundation + trải nghiệm đầu tiên (Tuần 1-2)

Mục tiêu: khung chạy được, MediaPipe hoạt động trên NEO One, một trải nghiệm MVP.

| ID | Task | Owner | Output |
| --- | --- | --- | --- |
| S1.1 | Project skeleton + `pyproject.toml` + CI | Backend | `pip install -e .` work, CI xanh |
| S1.2 | PyQt6 + QML scaffold + `MainWindow.qml` + StackView | UI | `python -m` hiện cửa sổ + SplashScreen |
| S1.3 | SignalBus + Logging + Config loader TOML | Backend | Unit test pass |
| S1.4 | `NeoConstants.qml` palette Dế Foundation + `ExperienceHubPage` | UI | Hub hiện lưới 7 thẻ (placeholder) |
| S1.5 | `experience_base.py` + `registry.py` + Plugin loader | Backend | Registry phát hiện plugin giả |
| S1.6 | `VisionEngine` + `VisionWorker` + MediaPipe Hands | Backend | Skeleton bàn tay vẽ lên preview |
| S1.7 | `VisionSimulator` (phát clip mp4) cho dev macOS | Backend | Env switch hoạt động |
| S1.8 | **exp01 Vẫy Chào Dế** — plugin hoàn chỉnh đầu tiên | Backend + UI | Vẫy tay → đàn dế bay; chạy trên NEO One ≥15 FPS |

**Demo Sprint 1:** mở app trên NEO One, thấy Hub, chọn "Vẫy Chào Dế", vẫy tay → đàn dế phản ứng. Chứng minh kiến trúc plugin + vision pipeline hoạt động.

### Sprint 2 — Vision đầy đủ + nhóm game tay/thân (Tuần 3-4)

Mục tiêu: 3 module MediaPipe còn lại + 3 trải nghiệm offline.

| ID | Task | Owner | Output |
| --- | --- | --- | --- |
| S2.1 | `VisionEngine` thêm Pose + Face Mesh + `set_active_modules` | Backend | Chuyển module mượt khi đổi game |
| S2.2 | `GestureDetector` + `landmark_math` (POINT, T_POSE, SMILE) | Backend | Unit test cử chỉ |
| S2.3 | **exp02 Tóm Bug Sửa Code** | Backend + UI | Chỉ tay → tóm bug, tính điểm |
| S2.4 | **exp03 Yoga Robot** + `poses.toml` + cosine similarity | Backend + UI | So 33 điểm với tư thế, chấm điểm |
| S2.5 | **exp04 Mặt Cười Sạc Pin Robot** | Backend + UI | Cười → sạc pin robot |
| S2.6 | `ExperienceManager` lifecycle + watchdog plugin treo | Backend | Vào/ra game sạch, không leak |
| S2.7 | Test với 10 trẻ em ở văn phòng Maker Việt | Toàn team | Báo cáo: thời gian chơi, tỷ lệ chơi lại |

**Demo Sprint 2:** 4 trải nghiệm offline chạy được, chuyển qua lại giữa các game qua Hub mượt mà.

### Sprint 3 — Logo + Photo Booth + Qwen + QR (Tuần 5-6)

Mục tiêu: trải nghiệm có chiều sâu + chụp ảnh + chia sẻ QR + Qwen.

| ID | Task | Owner | Output |
| --- | --- | --- | --- |
| S3.1 | **exp05 Hình Học Rùa Logo** + `logo_interp.py` | Backend + UI | Vẽ bằng ngón tay + lệnh Logo |
| S3.2 | `PhotoCapture` + composite (Selfie Segmentation) | Backend | Chụp + ghép nền AR |
| S3.3 | `ShareServer` + QR generator + `PhotoReviewPage` | Backend + UI | Quét QR bằng Zalo → tải ảnh |
| S3.4 | `QwenClient` hai backend (local + API) + `QwenService` | Backend | Sinh caption tiếng Việt cho ảnh |
| S3.5 | **exp06 Photo Booth Cổng Làng** + 4 nền | Backend + UI + Nội dung | Chụp ảnh + caption Qwen + QR |
| S3.6 | Tích hợp chụp ảnh vào exp03, exp05 (lưu tư thế/tranh) | Backend | Mọi game đều chia sẻ được ảnh |

**Demo Sprint 3:** chơi Photo Booth → chọn nền Sân Đình → làm chữ V → tự chụp → Qwen viết caption → QR hiện ra → quét tải về điện thoại.

### Sprint 4 — Neo Tre Vision + Polish + Pilot (Tuần 7-8)

Mục tiêu: trải nghiệm đỉnh cao + triển khai Làng thật.

| ID | Task | Owner | Output |
| --- | --- | --- | --- |
| S4.1 | `VoiceIO` — Whisper STT + Piper TTS tiếng Việt | Backend | Nghe + nói tiếng Việt offline |
| S4.2 | **exp07 Neo Tre Hỏi Đáp Vision** + `prompts.toml` Socratic | Backend + Nội dung | Đối thoại đa vòng có hình + giọng |
| S4.3 | `IdleAttractScreen` + idle timeout + UX polish | UI | Màn hình chờ thu hút khách |
| S4.4 | `NeoAudio` âm thanh chung + hiệu ứng chuyển cảnh | UI | Trải nghiệm liền mạch |
| S4.5 | `install-armbian.sh` + `makervigate.service` kiosk + `download-models.sh` | Backend | Boot NEO One → app fullscreen |
| S4.6 | Deploy 1 NEO One thật, smoke test 7 trải nghiệm liên tục | Toàn team | Không crash sau 20 lượt |
| S4.7 | Pilot tại 1 Làng Maker (Xa Đàn / Trần Phú), 30 ngày | Toàn team | Báo cáo KPI + bug v1.1 |

**Demo Sprint 4:** một đứa trẻ thật đi hết hành trình — Hub → chơi 3-4 trải nghiệm → chụp ảnh Photo Booth → hỏi Neo Tre một câu → quét QR mang ảnh về. Không crash.

### Phụ thuộc DAG

```
Sprint 1 (Foundation + exp01)
    │
    ▼
Sprint 2 (Vision đầy đủ + exp02,03,04)
    │
    ▼
Sprint 3 (exp05 + PhotoCapture + ShareServer + Qwen + exp06)
    │
    ▼
Sprint 4 (VoiceIO + exp07 + Deploy + Pilot)
```

Khác NeoStopMotion (Epic 2 & 3 song song): NeoMakerViGate tuyến tính hơn vì mỗi sprint xây trên nền sprint trước. Trong mỗi sprint, các task `expNN` có thể song song giữa nhiều người vì plugin độc lập.

### Tổng timeline

| Sprint | Tuần | Deliverable |
| --- | --- | --- |
| 1 | 1-2 | v0.2: khung + vision pipeline + exp01 chạy trên NEO One |
| 2 | 3-4 | v0.5: 4 trải nghiệm offline + Hub hoàn chỉnh |
| 3 | 5-6 | v0.8: + exp05,06 + chụp ảnh + QR + Qwen |
| 4 | 7-8 | **v1.0**: đủ 7 trải nghiệm + pilot xong tại 1 Làng Maker |

---

## 17. Tiêu chí thành công v1.0

| Metric | Ngưỡng |
| --- | --- |
| App boot time trên NEO One | < 20s từ power-on (gồm nạp MediaPipe model) |
| Vision FPS (mỗi module đơn lẻ) | ≥ 15 fps trên NEO One 2GB |
| Độ trễ landmark → game phản ứng | < 100ms |
| Chuyển trải nghiệm (Hub → game) | < 2s |
| Qwen caption (game 6, API) | < 3s |
| Qwen đối thoại (game 7, API) | < 4s/lượt |
| Chụp ảnh → QR hiện ra | < 5s (không caption), < 8s (có caption) |
| 5 trải nghiệm offline chạy khi mất mạng | 100% |
| Crash-free | ≥ 99% trong 20 lượt pilot liên tục |
| Trẻ em tự chơi được không cần Thợ Cả hướng dẫn | ≥ 80% (game 1-4) |
| Phụ huynh quét QR tải ảnh thành công | ≥ 80% |
| Bug P0/P1 sau pilot | ≤ 3 |

---

## 18. Roadmap sau v1.0

### Phase 2 — Pilot mở rộng (Tuần 9-16)

- v1.1: bug fix + UX cải tiến từ feedback pilot
- v1.2: "Hộ chiếu Làng Maker" — passport số, mỗi Làng một con dấu (liên kết concept đã đề xuất)
- Triển khai 3 Làng Maker pilot (HN — ĐN — SG)
- Bảng xếp hạng điểm trải nghiệm theo Làng

### Phase 3 — Mở rộng 34 Làng (Tuần 17+)

- Trải nghiệm mới (plugin thứ 8, 9, 10): Trạm Âm Nhạc cử chỉ, Vẽ Tranh AR, Thể Thao AR
- Đồng bộ ảnh + KPI về trung tâm Dế Foundation (opt-in, có kiểm soát privacy)
- Tích hợp với các trạm khác trong Làng (Trạm 6 NeoStopMotion, v.v.)
- Đa ngôn ngữ — chuẩn bị cho ASEAN (Qwen hỗ trợ 200+ ngôn ngữ sẵn)

---

## 19. Tài liệu liên quan

- `DOC/EXPERIENCES.md` — Đặc tả chi tiết 7 trải nghiệm (luật chơi, asset, scoring)
- `DOC/HARDWARE.md` — Camera + giá đỡ + (tùy chọn) ThingBot + BOM
- `DOC/DEPLOY_NEO_ONE.md` — Hướng dẫn cài đặt NEO One step-by-step
- `DOC/TEACHER_MANUAL.md` — Cheatsheet cho Thợ Cả vận hành Cổng Làng
- `DOC/PLUGIN_GUIDE.md` — Hướng dẫn viết experience plugin mới
- `DOC/QWEN_SETUP.md` — Cài Qwen 3.5 local / cấu hình API + privacy
- Tham chiếu: `NeoStopMotion/DOC/ARCHITECTURE.md`, Storyboard "Trò Chơi Cổng Làng" v0.1

---

## 20. License & Credits

- **Phát triển**: Maker Việt × Dế Foundation × ThingEdu
- **Stack**: Python 3.10+ / PyQt6 / QML 6 / MediaPipe / OpenCV / Qwen 3.5 / Whisper / Piper
- **License**: MIT (cam kết public sau pilot, theo tinh thần Bình Dân Học STEM)
- **Kế thừa kiến trúc**: NeoStopMotion (SignalBus, Worker Thread, ShareServer), NEOSTEM (QML Singletons), NEO_CODE (PyQt6 patterns)
- **Cảm ơn**: Google MediaPipe và Alibaba Qwen cho công cụ mã nguồn mở; Intel Museum cho cảm hứng AR Photo Booth

---

> *"Cổng làng ngày xưa là nơi đứa trẻ bước ra thế giới. Cổng Làng Maker là nơi đứa trẻ bước vào tư duy — bằng chính đôi tay, nụ cười và dáng đứng của mình. Chúng ta không xây một máy game. Chúng ta xây một cánh cửa."* — Maker Việt × Dế Foundation, 05/2026

**HẾT TÀI LIỆU KIẾN TRÚC v0.1 (Design)**
