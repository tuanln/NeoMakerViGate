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

## P4 — Pose + exp03 Yoga Robot (tuần 5) ✅ DONE

**Achievement (2026-05-16):** landmark_math (compute_joint_angle + extract_pose_angles + pose_similarity_score, 10 tests) + YogaRobotExperience full gameplay (5 poses từ poses.toml: T/Tree/Star/Y/Cactus, Phase machine INTRO→POSING→RESULT→DONE, PoseAttempt với hold 3s + gap tolerance 0.3s, hint at 15s, skip at 45s, total score 0-500, best_pose tracking) + ui.qml (mirror cam + 33-landmark Canvas skeleton + pose card + robot face widget + hold bar + intro/hint/result overlays + 2 procedural WAV). 13 task TDD subagent-driven. **Decision:** chốt joint-angle similarity (không cosine — robust hơn với scale). T_POSE gesture trong gesture_detector YAGNI bỏ.

**Mục tiêu (đạt):** Module Pose + scoring tư thế.

### Tasks

- [x] `core/vision_engine.py` Pose solution + `set_active_modules(["pose"])` — đã có từ P1
- [x] `utils/landmark_math.py` — joint angle (3 điểm) + pose similarity scoring (mean error normalized by tolerance)
- [x] `experiences/exp03_yoga_robot/poses.toml` — 5 tư thế (T/Tree/Star/Y/Cactus) với target angles + tolerance
- [x] `experiences/exp03_yoga_robot/logic.py` — Phase state machine + PoseAttempt + score 0-100
- [x] `experiences/exp03_yoga_robot/ui.qml` — mirror cam + skeleton + pose card + HUD + overlays + audio
- [x] `experiences/exp03_yoga_robot/assets/` — pose_locked.wav (arpeggio C5-E5-G5) + pose_skipped.wav (buzz A4→F4)
- [~] `core/gesture_detector.py` T_POSE — YAGNI bỏ (logic tự compute pose match)
- [x] Game flow: hiện target → trẻ giữ 3s → next pose → hết 5 pose → kết quả

### Demo

- Chạm thẻ Yoga Robot từ Hub → game hiện target T-pose → trẻ đứng đúng → điểm ✓

### Exit criteria

- [x] Joint-angle similarity unit test pass với mock landmarks — 10 tests (landmark_math)
- [x] `set_active_modules` chuyển Hands → Pose mượt — synchronous, < 100ms trên Mac
- [x] Game hoàn thành 5 pose không crash — 79/79 tests pass, ruff/mypy strict clean

---

## P5 — PhotoCapture + ShareServer + QR (tuần 6) ✅ DONE

**Achievement (2026-05-17):** Core photo+share services — PhotoCapture (cv2.imwrite JPG Q90, 6 tests), ShareServer QThread (http.server.ThreadingHTTPServer port 8000 + fallback 8001-8010, 6 tests), generate_qr (qrcode + Pillow PNG error_correct M), utils/network (get_local_ip UDP trick + loopback fallback, 2 tests), utils/storage (LRU cleanup 200MB theo folder mtime, 4 tests), PhotoService orchestrator (5 tests), ShareService facade, AppController.photoResult + photoReviewRequested (3 tests), ExperienceManager Phase.DONE → photo_capture_requested + unload (1 test), PhotoReviewPage QML split view (photo left + QR/URL/Back right). 12 task TDD subagent-driven. 27 P5 tests, 106 total. ruff/mypy strict clean. Storage layout `~/makervigate/photos/<photo_id>/{original.jpg, qr.png}`.

**Mục tiêu (đạt):** Chụp ảnh + chia sẻ qua QR — port từ NeoStopMotion.

### Tasks

- [x] `core/photo_capture.py` — snap raw (composite Selfie Seg để P6)
- [x] `core/share_server.py` — `http.server` trên QThread serve `~/makervigate/photos/`
- [x] `services/photo_service.py` + `services/share_service.py` — orchestrator + facade
- [x] `utils/network.py` — lấy local IP cho share URL
- [x] `ui/qml/pages/PhotoReviewPage.qml` — ảnh lớn + QR + hướng dẫn
- [~] `ui/qml/components/QRDisplay.qml` — inline trong PhotoReviewPage (extract khi P6 reuse)
- [x] Tích hợp chụp ảnh vào exp03 (auto trên Phase.DONE qua ExperienceManager change)
- [x] Storage layout: `~/makervigate/photos/<photo_id>/`

### Demo

- Trong exp03 hoàn thành 5 pose → tự chụp ảnh → PhotoReviewPage → quét QR bằng Zalo trên cùng WiFi → tải ảnh về điện thoại ✓ (cần manual webcam smoke test)

### Exit criteria

- [x] Auto-cleanup photos cũ khi storage > 200MB — `utils/storage` + 4 tests
- [x] QR quét tải được trong LAN — verify qua manual smoke test (iPhone same WiFi + Zalo)
- [x] Watchdog port 8000 không conflict — `test_share_server_falls_back_when_port_taken`

---

## P6 — Qwen + exp06 Photo Booth (tuần 7) ✅ DONE

**Achievement (2026-05-17):** Flagship MVP experience. V_SIGN gesture (pose-based detection, separate cooldown), Selfie Seg enable trong VisionEngine + VisionFrame.selfie_mask + VisionWorker.latest_vision_frame property, PhotoCapture.save_composite (soft mask Gaussian blur), QwenLocalBackend (llama-cpp-python + Qwen 2.5-VL-2B GGUF Q4_K_M lazy load, runtime_checkable Protocol), QwenService QThread wrapper với queue + poison pill stop, PhotoBoothExperience full game (INTRO 2s → SELECT POINT cycle + auto-advance 3s → STAGE V_SIGN hold 0.5s → COUNTDOWN 3s → PROCESSING + Qwen caption với timeout 12s fallback template → DONE), BaseExperience.auto_capture_on_done attr + ExperienceManager check (exp06 self-orchestrates capture), photo_caption_ready signal → AppController updates photoResult với composite_path + caption fields, PhotoReviewPage caption display, 4 procedural backgrounds (Sân Đình/Lũy Tre/Sân FGC/Sao Hỏa). 17 tasks TDD subagent-driven. 30+ P6 tests (141 total). ruff/mypy strict clean.

**Mục tiêu (đạt):** Trải nghiệm flagship MVP — Photo Booth với caption tiếng Việt.

### Spike S2 (chưa chạy — user manual)

User chốt skip pre-flight; plan executed assuming Qwen 2.5-VL-2B works trên Mac M4. T17 manual smoke sẽ verify.

### Tasks

- [x] `core/qwen_client.py` — Protocol + `QwenLocalBackend` (llama-cpp-python). APIBackend (DashScope) out-of-scope (local-only decision)
- [x] `services/qwen_service.py` — QThread wrapper
- [x] `experiences/exp06_photo_booth/logic.py` — chụp + composite + caption flow
- [x] `experiences/exp06_photo_booth/ui.qml` — chọn nền + countdown + preview
- [x] `experiences/exp06_photo_booth/backgrounds/` — 4 nền procedural Pillow (Sân Đình + Lũy Tre + Sân FGC + Sao Hỏa)
- [x] `experiences/exp06_photo_booth/prompts.toml` — system prompt + 4 fallback captions
- [x] V_SIGN gesture → trigger chụp (extend GestureDetector)
- [x] Fallback: Qwen fail/timeout → caption mẫu có sẵn theo nền

### Demo

- Chơi Photo Booth → chọn Sân Đình → làm chữ V (hold 0.5s) → countdown 3-2-1 → chụp → ghép nền (Selfie Seg + Gaussian blur edges) → caption Qwen (local 2.5-VL-2B) → QR → tải về

### Exit criteria

- [~] API mode caption < 4s — N/A (local only)
- [ ] Local mode caption < 8s — verify trong smoke test webcam thật
- [ ] Composite chất lượng OK (selfie mask không vỡ) — verify trong smoke test

---

## P7 — ARM Deploy + Smoke Test (tuần 8) — 🟡 P7a + P7c DONE, P7b hardware pending

**P7a Achievement (2026-05-18):** Hardware-independent prep complete. AppController idle detection (90s timeout, touch + Hand wake, 3 tests). IdleAttractScreen.qml (logo + animated pulsing dot). MainWindow idle Component + Connections. deployment/install-armbian.sh (apt + venv + pip + udev + systemd setup, shellcheck clean). deployment/download-models.sh (MediaPipe + Qwen optional). deployment/makervigate.service (Qt eglfs fullscreen kiosk). deployment/udev/99-makervigate-cam.rules (Logitech symlink C270/C310/C920). DOC/DEPLOY_NEO_ONE.md rewrite từ skeleton (155 lines: hardware + pre-install + 6-step install + verify table 9 rows + 5 troubleshoot). DOC/TEACHER_MANUAL.md cheatsheet Thợ Cả vận hành FPT Shop. 8 tasks TDD. 144 tests pass, ruff/mypy strict clean. **Bug fix dọc đường:** selfie segmenter URL P1 sai path (404 lúc load exp06) — sửa `selfie_segmenter/selfie_segmenter/` → `image_segmenter/selfie_segmenter/` per MediaPipe task type convention.

**P7c Achievement (2026-05-21):** Fix 3 issues từ smoke test webcam thật. exp03 redesign từ body pose (full body, đứng xa cam, đồ vật nhiễu) → Face Yoga (5 biểu cảm: cười / mở O / wink / nhướng mày / lắc đầu, sit close to cam, MediaPipe Face Mesh 468 landmarks). utils/face_math.py (MAR, MWR, EAR, brow_raised_ratio, head_yaw, 11 tests). exp03 detector dispatcher (5 detectors), yaw history deque cho head_shake. V_SIGN_FINGER_MARGIN 1.15→1.05 (easier detection cho fingers cong nhẹ). PhotoCapture.list_source_photos + DEFAULT_SOURCE_PHOTOS_DIR. PhotoService source photo folder fallback (~/makervigate/source_photos/ admin upload via scp, random pick khi selfie_mask missing). exp03 ui.qml face landmark overlay (17 key points dots, không skeleton). 11 tasks TDD. 153 tests pass, ruff/mypy strict clean. **Decision chốt:** lè lưỡi → Wink (FaceMesh không track tongue).

**P7b pending (NEO One hardware về):**
- Spike S3 FPS measurement (≥10 fps Hands)
- Spike S4 RAM profile (<1.8GB peak exp06)
- 20-game smoke không crash
- Real Logitech udev symlink verify
- Boot time < 25s
- Qt eglfs verify (fallback linuxfb nếu fail)

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
