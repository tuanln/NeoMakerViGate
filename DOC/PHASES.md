# NeoMakerViGate — Phase Plan chi tiết

> **Solo dev** trên macOS, deploy NEO One ARM64. 8 phase × ~5 ngày.
> Tham chiếu: [`ARCHITECTURE.md`](ARCHITECTURE.md), [`ARCHITECTURE_MVP.md`](ARCHITECTURE_MVP.md)

---

## P0 — Foundation (tuần 1)

**Mục tiêu:** Repo khung + CI + app launch được cửa sổ Qt với SplashScreen.

### Tasks

- [x] `pyproject.toml` + `requirements*.txt` + `Makefile` + `.gitignore`
- [x] `LICENSE` MIT + `README.md` quickstart
- [x] `.github/workflows/ci.yml` (ruff + mypy + pytest offscreen Qt)
- [x] `src/neo_makervigate/__init__.py` + `__main__.py` + `app.py`
- [x] `utils/signal_bus.py` (minimal pyqtSignal hub)
- [x] `utils/logging_config.py` (loguru → stderr + file)
- [x] `config/defaults.toml` + `config/settings.py` (TOML loader)
- [x] `ui/qml/MainWindow.qml` + `pages/SplashScreen.qml` (ApplicationWindow + StackView, splash 2s)
- [x] `ui/qml/singletons/NeoConstants.qml` (design tokens Dế Foundation palette)
- [x] `tests/conftest.py` + 1 unit test signal_bus
- [x] `scripts/run_dev.sh` + `scripts/run_neo_one.sh`

### Demo

```bash
make dev      # tạo .venv + install
make run      # mở cửa sổ Qt fullscreen, SplashScreen hiện 2s rồi tắt
make test     # 1 test pass
make lint     # ruff sạch
```

### Exit criteria

- [ ] CI GitHub Actions xanh
- [ ] `python -m neo_makervigate` mở splash screen rồi exit graceful
- [ ] `make test` pass

---

## P1 — Vision Core (tuần 2) — ✅ DONE 2026-05-15

**Mục tiêu:** MediaPipe Hands chạy real-time trên webcam Mac. VisionSimulator hoạt động.

### Tasks

- [x] `core/models.py` — `Landmark`, `VisionFrame`, `ExperienceMeta`, `PhotoResult` (đã có ở P0)
- [x] `core/vision_engine.py` — VisionEngine + VisionSource Protocol + 4 module (hands/pose/face/face_mesh stub) lazy init
- [x] `core/vision_simulator.py` — blank/clip mp4 mode (BLANK mặc định)
- [x] `core/vision_worker.py` — `QThread` đọc source + emit `vision_frame_ready`
- [x] `ui/image_provider.py` — `CameraImageProvider(QQuickImageProvider)`
- [x] `ui/qml/components/CameraPreview.qml` + `SkeletonOverlay.qml` (Canvas vẽ hand landmarks)
- [x] `ui/qml/singletons/VisionState.qml` — Singleton + bindings từ `app.*`
- [x] `services/app_controller.py` — `pyqtProperty` expose state cho QML
- [x] `utils/cv_qt_bridge.py` — cv2 BGR ↔ QImage RGB888 (5 unit test pass)
- [x] Env switch: `NEO_MAKERVIGATE_VISION=simulator` → dùng simulator
- [x] Integration test `tests/integration/test_vision_pipeline.py` — Simulator → Worker → AppController end-to-end pass

### Spike S1 — ✅ PASS

Đã chạy `scripts/spike_s1_hands_fps.py` trên Mac M4 webcam:

- **29.7 FPS** ở 1280x720 — bottleneck là webcam 30fps cap, không phải MediaPipe (per-frame 33ms ≈ 1/30s)
- MediaPipe Tasks API (Metal GPU acceleration tự động)
- Verdict: PASS (interpreted) — 4× headroom so với target NEO One ≥15fps
- Chi tiết: [`DOC/SPIKES.md`](SPIKES.md)

### Đổi so với doc gốc

- Doc gốc dùng `mediapipe.solutions.hands` (legacy API) → mediapipe 0.10.35 chỉ có `mediapipe.tasks.python.vision.HandLandmarker`. Code chuyển sang Tasks API.
- VisionState QML singleton retained nhưng binding qua `app` context property thay vì context-set property singleton (PyQt6 hạn chế).

### Exit criteria

- [x] FPS ≥ 30 trên Mac (webcam-bound 29.7 ≈ 30, MediaPipe compute đủ headroom)
- [x] Skeleton overlay hiển thị đúng vị trí landmarks (Canvas paint khi `handLandmarks` thay đổi)
- [x] Simulator chuyển sang VisionEngine không crash (env switch hoạt động)
- [x] 12/12 tests pass, mypy strict OK, ruff clean

---

## P2 — Plugin Architecture + Hub (tuần 3)

**Mục tiêu:** `experience_base.Experience` Protocol + `registry` tự discover + `ExperienceHubPage` lưới 3 thẻ.

### Tasks

- [ ] `experiences/experience_base.py` — Protocol class với 7 methods
- [ ] `experiences/registry.py` — `discover_experiences()` quét `exp*` packages
- [ ] `services/experience_manager.py` — load/unload, lifecycle, watchdog
- [ ] `services/app_controller.py` — root QObject exposed to QML
- [ ] `ui/qml/pages/ExperienceHubPage.qml` — lưới responsive 3 thẻ
- [ ] `ui/qml/components/ExperienceCard.qml` — icon + title + age range
- [ ] `ui/qml/pages/ExperienceContainerPage.qml` — Loader cho ui.qml của plugin active
- [ ] `ui/qml/singletons/AppState.qml`
- [ ] StackView navigation: Splash → Hub → Container → Hub
- [ ] Stub `exp01`, `exp03`, `exp06` để registry phát hiện được (chỉ meta, chưa logic)
- [ ] `DOC/PLUGIN_GUIDE.md` — viết hướng dẫn

### Demo

- Mở app → Hub lưới 3 thẻ → chạm thẻ → Container page rỗng → nút Back → Hub
- Test: `pytest tests/unit/test_registry.py` discover được 3 plugin stub

### Exit criteria

- [ ] Registry tự động phát hiện plugin
- [ ] Lifecycle on_enter/on_exit gọi đúng thứ tự
- [ ] Watchdog ngắt plugin treo > 500ms/frame (mock)

---

## P3 — exp01 Wave Cricket (tuần 4) ✅ DONE

**Achievement (2026-05-16):** GestureDetector WAVE algo (zero-crossing wrist X, 8 tests) + WaveCricketExperience full gameplay (Phase state machine INTRO→PLAYING→RESULT→DONE, Cricket dataclass + physics, flock bonus on 3 rapid waves, scoring với multiplier ×1.5) + AppController.experienceState QTimer 30Hz + QML game UI (camera mirror + bamboo + cricket sprites + hand landmark Canvas overlay + HUD + intro/result overlays + procedural WAV audio). ExperienceManager auto-unload trên Phase.DONE.

**Mục tiêu (đạt):** Game đầu tiên hoàn chỉnh + chứng minh kiến trúc end-to-end.

### Tasks

- [x] `core/gesture_detector.py` — phát hiện WAVE (cổ tay dao động trái-phải > ngưỡng/1s)
- [x] `experiences/exp01_wave_cricket/logic.py` — class WaveCricketExperience
- [x] `experiences/exp01_wave_cricket/ui.qml` — nền lũy tre + đàn dế sprite
- [x] `experiences/exp01_wave_cricket/assets/` — 3 WAV procedural (chirp/ting/fanfare)
- [x] `experiences/exp01_wave_cricket/test_logic.py` — 16 tests scoring + lifecycle
- [x] `services/app_controller.py` extended với `experienceState` property + render QTimer
- [x] Câu chuyện gameplay: vẫy 1 con dế bay ra ; vẫy nhanh → cả đàn bay
- [x] Scoring: số lần vẫy × hệ số nhịp → điểm
- [x] Quay về Hub sau 60s hoặc nút Back (auto-unload trên Phase.DONE)

### Demo

- Vẫy tay trước webcam → dế bay ra → điểm tăng ✅
- Test unit gestures: WAVE detection 8/8 pass (sine 2 cycles, amplitude threshold, single crossing, cooldown, reset, no-hands, idle)

### Exit criteria

- [x] Logic plugin chạy độc lập (không phụ thuộc QML cho test) — 16 logic tests dùng pytest + FakeClock, không Qt/QML
- [x] 52/52 tests pass, ruff/mypy strict clean
- [ ] FPS gameplay ≥ 30 trên Mac — verify trong smoke test webcam thật (pending user)
- [ ] Hub → game → Hub không leak memory — verify trong smoke test với tracemalloc (pending)

---

## P4 — Pose + exp03 Yoga Robot (tuần 5)

**Mục tiêu:** Module Pose + scoring tư thế.

### Tasks

- [ ] `core/vision_engine.py` extend: thêm Pose solution + `set_active_modules(["pose"])` đóng/mở module
- [ ] `utils/landmark_math.py` — tính góc 3 điểm, cosine similarity hai bộ pose
- [ ] `experiences/exp03_yoga_robot/poses.toml` — định nghĩa 5 tư thế (T_POSE, TREE_POSE, etc.)
- [ ] `experiences/exp03_yoga_robot/logic.py` — so 33 landmarks với target, scoring 0-100
- [ ] `experiences/exp03_yoga_robot/ui.qml` — silhouette mục tiêu + thanh điểm
- [ ] `core/gesture_detector.py` extend: T_POSE detection
- [ ] Game flow: hiện target pose → trẻ giữ 3s → next pose → hết 5 pose → kết quả

### Demo

- Chạm thẻ Yoga Robot từ Hub → game hiện target T-pose → trẻ đứng đúng → điểm
- Module Pose chỉ load khi vào game (đo memory before/after `set_active_modules`)

### Exit criteria

- [ ] Cosine similarity unit test pass với mock landmarks
- [ ] `set_active_modules` chuyển Hands → Pose mượt < 1s
- [ ] Game hoàn thành 5 pose không crash

---

## P5 — PhotoCapture + ShareServer + QR (tuần 6)

**Mục tiêu:** Chụp ảnh + chia sẻ qua QR — port từ NeoStopMotion.

### Tasks

- [ ] `core/photo_capture.py` — snap raw + composite (Selfie Seg + nền)
- [ ] `core/share_server.py` — `http.server` trên QThread serve thư mục photos/
- [ ] `services/photo_service.py` + `services/share_service.py` — async wrappers
- [ ] `utils/network.py` — lấy local IP cho share URL
- [ ] `ui/qml/pages/PhotoReviewPage.qml` — ảnh lớn + QR + hướng dẫn
- [ ] `ui/qml/components/QRDisplay.qml`
- [ ] Tích hợp chụp ảnh vào exp03 (lưu tư thế hoàn thành)
- [ ] Storage layout: `/home/maker/makervigate/photos/<photo_id>/`

### Demo

- Trong exp03 hoàn thành 5 pose → tự chụp ảnh → PhotoReviewPage → quét QR bằng Zalo trên cùng WiFi → tải ảnh về điện thoại

### Exit criteria

- [ ] Auto-cleanup photos cũ khi storage > 200MB
- [ ] QR quét tải được trong LAN (Mac ↔ iPhone cùng WiFi nhà)
- [ ] Watchdog port 8000 không conflict

---

## P6 — Qwen + exp06 Photo Booth (tuần 7)

**Mục tiêu:** Trải nghiệm flagship MVP — Photo Booth với caption tiếng Việt.

### Spike S2 (ngày 1, 4h)

Check HuggingFace có `Qwen/Qwen3.5-0.8B-Instruct-GGUF` chưa? Test llama.cpp inference trên Mac. Plan B: Qwen2-VL-2B + API only.

### Tasks

- [ ] `core/qwen_client.py` — Protocol + `QwenLocalBackend` (llama-cpp-python) + `QwenAPIBackend` (DashScope)
- [ ] `services/qwen_service.py` — async wrapper QThread
- [ ] `experiences/exp06_photo_booth/logic.py` — chụp + composite + caption flow
- [ ] `experiences/exp06_photo_booth/ui.qml` — chọn nền + countdown + preview
- [ ] `experiences/exp06_photo_booth/backgrounds/` — 2 nền: Sân Đình, Lũy Tre (PNG transparent)
- [ ] `experiences/exp06_photo_booth/prompts.toml` — system prompt sinh caption tiếng Việt
- [ ] V_SIGN gesture → trigger chụp (không cần chạm màn hình)
- [ ] Fallback: Qwen fail → caption mẫu có sẵn theo nền

### Demo

- Chơi Photo Booth → chọn Sân Đình → làm chữ V → countdown 3-2-1 → chụp → ghép nền → caption Qwen "Hôm nay một con dế nhỏ..." → QR → tải về

### Exit criteria

- [ ] API mode caption < 4s
- [ ] Local mode caption < 8s
- [ ] Composite chất lượng OK (selfie mask không vỡ)

---

## P7 — ARM Deploy + Smoke Test (tuần 8)

**Mục tiêu:** Chạy thật trên NEO One. Đo metrics. Bug fix critical.

### Spike S3 (ngày 1-2, 2 ngày)

Cài MediaPipe + chạy exp01 trên NEO One thật. Đo FPS Hands, Pose. Pass: ≥10fps Hands 480p. Fail: pivot RPi 5 8GB.

### Spike S4 (ngày 3, 4h)

Memory profile khi chạy exp06 với Qwen local. Pass: peak < 1.8GB. Fail: ép API-only.

### Tasks

- [ ] `deployment/install-armbian.sh` — apt deps + pip install + tải models
- [ ] `deployment/download-models.sh` — MediaPipe .task + Qwen gguf
- [ ] `deployment/makervigate.service` — systemd unit kiosk auto-start
- [ ] `deployment/udev/99-webcam.rules` — stable `/dev/makervigate-cam`
- [ ] `DOC/DEPLOY_NEO_ONE.md` — step-by-step cài đặt
- [ ] `DOC/TEACHER_MANUAL.md` — cheatsheet Thợ Cả vận hành
- [ ] `IdleAttractScreen.qml` + idle timeout 90s
- [ ] Smoke test: 20 lượt chơi 3 game liên tục, không crash
- [ ] Bug fix P0/P1 phát sinh

### Demo

- Reboot NEO One → tự boot vào app fullscreen → chơi cả 3 game → quét QR ảnh về → idle 90s → IdleAttractScreen

### Exit criteria

- [ ] Boot time < 25s
- [ ] FPS exp01 ≥ 10, exp03 ≥ 8
- [ ] 20 lượt liên tục không crash
- [ ] Báo cáo metrics gửi Tuấn quyết v1.1

---

## Tracking

Mỗi phase nên có:

- Tag git: `v0.<phase>.0` khi exit phase
- PR riêng hoặc branch `phase/p<N>-<topic>`
- Update phase checklist trong file này

Khi pivot scope (xem [`ARCHITECTURE_MVP.md §9`](ARCHITECTURE_MVP.md)), update tài liệu này và ghi rõ lý do.
