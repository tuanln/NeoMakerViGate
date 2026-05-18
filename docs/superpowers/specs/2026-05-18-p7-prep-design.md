# P7 prep — Hardware-Independent Deploy + IdleAttract Design

**Phase:** 7a (NeoMakerViGate — deployment prep, hardware-independent)
**Created:** 2026-05-18
**Status:** Design approved, ready for implementation plan

## Mục tiêu

Chuẩn bị mọi thứ cần thiết để deploy NEO One khi hardware về (P7b). Hardware-independent: viết được hết trên Mac, verify syntax + simulator. Hardware-dependent items (FPS measurement, RAM profile, 20-game smoke, real udev) defer P7b.

Scope:
1. **IdleAttractScreen + idle detection** — màn chờ 90s no-interaction
2. **Deploy scripts** — `install-armbian.sh`, `download-models.sh`
3. **systemd kiosk** — `makervigate.service` Qt eglfs fullscreen
4. **udev rule** — symlink `/dev/makervigate-cam`
5. **Docs** — flesh out `DEPLOY_NEO_ONE.md` + new `TEACHER_MANUAL.md`

## Quyết định chốt với user (2026-05-18)

| Quyết định | Lựa chọn | Lý do |
|---|---|---|
| Idle content | Logo + tiêu đề + hướng dẫn + pulsing dot | Nhẹ, không cần asset |
| Wake trigger | Tap màn + Hand detect ≥0.5s | Cả 2 paths; Hands active idle |
| Display backend | Qt eglfs (no X11/Wayland) | Ít RAM, native framebuffer |
| udev strategy | Symlink theo VENDOR:PRODUCT (Logitech) | Stable, dễ swap webcam |
| Scripts | 2 file tách (install + download-models) | Per PHASES.md, modular |

## 1. Architecture

```
NEO One boot → systemd makervigate.service auto-start
   QT_QPA_PLATFORM=eglfs → fullscreen direct framebuffer
       │
       ▼
NeoMakerViGate boots
   ShareServer :8000, VisionWorker, registry
       │
       ▼
MainWindow → IdleAttractScreen (initial)
       │
       ▼ Wake triggers:
       ├─ TouchEvent (MouseArea anywhere) → app.wakeFromIdle()
       └─ MediaPipe Hands detected ≥0.5s in frame → wakeRequested
       │
       ▼
Hub → User chơi game → photo + QR → review → Hub
       │
       ▼
AppController QTimer 1Hz check:
   if status == "hub" AND now - _last_interaction_at > 90s:
       emit idleTimeoutTriggered → MainWindow push IdleAttractScreen
```

## 2. Deployment scripts

### `deployment/install-armbian.sh` (~60 lines)

Steps:
1. apt update + install system deps (python3.12, opencv, gl/egl, v4l, fonts-noto-color-emoji + cjk, build tools)
2. python -m venv .venv + pip install -e .
3. Optional `pip install llama-cpp-python` (Qwen local)
4. Install udev rule + reload
5. Install systemd service (sed replace `%USER%`/`%HOME%`)

### `deployment/download-models.sh` (~30 lines)

Steps:
1. `ensure_model` cho hands/pose/selfie qua Python call
2. `python -m neo_makervigate.scripts.download_qwen` (nếu llama_cpp imported OK)
3. Fallback notice nếu Qwen không cài được

### `deployment/makervigate.service` (systemd unit)

```ini
[Unit]
Description=NeoMakerViGate Cổng Vào Làng Maker
After=multi-user.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=%USER%
Group=%USER%
WorkingDirectory=%HOME%/NeoMakerViGate
Environment=QT_QPA_PLATFORM=eglfs
Environment=QT_QPA_EGLFS_KMS_ATOMIC=1
Environment=QT_QPA_EGLFS_HIDECURSOR=1
Environment=PYTHONUNBUFFERED=1
ExecStart=%HOME%/NeoMakerViGate/.venv/bin/python -m neo_makervigate
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
StartLimitIntervalSec=60
StartLimitBurst=5

[Install]
WantedBy=multi-user.target
```

### `deployment/udev/99-makervigate-cam.rules`

3 lines cho Logitech C270/C310/C920 vendor 046d, product 0825/081b/082d → SYMLINK=makervigate-cam, GROUP=video, MODE=0664. Comment-out fallback rule cho ANY UVC.

## 3. IdleAttractScreen + idle detection

### QML `src/neo_makervigate/ui/qml/pages/IdleAttractScreen.qml`

- Full-screen gradient background (cream → tan)
- Center: "🏛️ 🦗 ✨" big + "Cổng Làng Maker" title + "Chạm màn hình hoặc vẫy tay để bắt đầu" + animated pulsing dot
- Footer: "Maker Việt × Dế Foundation × ThingEdu"
- MouseArea full-page → `wakeRequested()` signal
- Connections `target: app, onHandLandmarksChanged`: track `_handDetectedSince`, ≥0.5s → wake

### AppController extension

Constants:
```python
IDLE_TIMEOUT_SEC = 90.0
IDLE_CHECK_INTERVAL_MS = 1000
```

New signals: `idleTimeoutTriggered`, `idleWakeRequested`.

`__init__` add:
- `self._last_interaction_at: float = time.perf_counter()`
- `self._idle_timer = QTimer(self)` interval 1000ms → `_check_idle`
- Connect signal bus: `gesture_detected`, `experience_started`, `photo_capture_requested` all → `_touch_interaction`

Methods:
- `_touch_interaction(*args)` — update timestamp
- `@pyqtSlot() touchEvent()` — QML reachable, calls `_touch_interaction`
- `@pyqtSlot() wakeFromIdle()` — emit `idleWakeRequested`
- `_check_idle()` — if `status == "hub"` AND elapsed ≥ 90s → emit `idleTimeoutTriggered`, debounce timestamp

### MainWindow.qml

```qml
Component {
    id: idleAttractComponent
    IdleAttractScreen {
        onWakeRequested: {
            app.wakeFromIdle()
            stack.pop()
        }
    }
}

Connections {
    target: app
    function onIdleTimeoutTriggered() {
        if (stack.depth > 0) {
            stack.push(idleAttractComponent)
        }
    }
}
```

Note: IdleAttractScreen pushes on top of Hub. On wake, pop returns to Hub.

## 4. Testing strategy

**Unit tests** (`tests/unit/test_app_controller.py` extend — 3 new):
- `test_idle_timeout_emits_after_90s_when_hub`
- `test_idle_timeout_does_not_fire_during_playing`
- `test_touch_interaction_resets_idle_timer`

Use monkeypatch on `time.perf_counter` to simulate fast-forward 90s.

**Manual smoke test (simulator mode on Mac):**
1. Boot app simulator → MainWindow loads (currently starts at Splash)
2. **Issue:** initial state shows Splash → Hub. Idle only triggers in Hub. After Hub appears, idle 90s → IdleAttract pushes
3. Tap window → wakes
4. (Requires webcam) Hand in frame → wakes after 0.5s

**Scripts validation:**
- `shellcheck deployment/*.sh` (syntax)
- systemd unit `systemd-analyze verify deployment/makervigate.service`
- udev rule `udevadm verify deployment/udev/*.rules`
- DEPLOY_NEO_ONE.md + TEACHER_MANUAL.md markdown lint (visual review)

**Hardware tests deferred P7b:**
- Qt eglfs black screen check on Allwinner GPU
- Real Logitech udev symlink verify
- FPS S3, RAM S4, 20-game smoke
- Boot time

## 5. File layout

```
deployment/
├── install-armbian.sh           # MỚI ~60 lines
├── download-models.sh           # MỚI ~30 lines
├── makervigate.service          # MỚI ~25 lines
└── udev/
    └── 99-makervigate-cam.rules # MỚI ~10 lines

src/neo_makervigate/
├── ui/qml/pages/
│   └── IdleAttractScreen.qml    # MỚI ~120 LOC
├── ui/qml/MainWindow.qml        # SỬA: Component + Connections
└── services/app_controller.py   # SỬA: idle detection (3 tests)

tests/unit/
└── test_app_controller.py       # SỬA: + 3 idle tests

DOC/
├── DEPLOY_NEO_ONE.md            # REWRITE (~150 LOC)
└── TEACHER_MANUAL.md            # MỚI (~80 LOC)
```

**~500 LOC total** across bash + QML + Python + Markdown.

## 6. Risk register

| Risk | Mitigation |
|---|---|
| Qt eglfs black screen Allwinner | service file fallback `QT_QPA_PLATFORM=linuxfb`; DEPLOY troubleshoot has guide |
| udev rule not matching new webcam | install hint Logitech; rules file comment for adding vendor:product |
| systemd `%USER%` sed fail special chars | install-armbian.sh `getent passwd $USER` verify before sed |
| IdleAttract MouseArea conflicts | Only IdleAttractScreen has full overlay; gameplay screens don't fire wake handler |
| Hand wake false positive ngang qua | 0.5s hold filter — acceptable v1.0 |
| TEACHER_MANUAL outdated post-pilot | Cheatsheet format dễ update |
| Scripts not bash-portable | `set -euo pipefail`, no bashisms, shellcheck pass |

## 7. Out of scope

- All hardware tests (P7b)
- Auto-update mechanism (post-pilot)
- Remote monitoring/telemetry (out of scope MVP)
- Multi-user / profile switching (single-user maker)
- Network configuration UI (assume FPT WiFi pre-configured)
- Voice + Whisper (exp07, post-MVP)
- Touch screen calibration (assume HDMI display, mouse fallback for touch)
- IdleAttractScreen demo loop video (text + emoji enough)

---

Liên quan: [[2026-05-15-p3-wave-cricket-design]] (idle state machine pattern), DEPLOY_NEO_ONE.md (current skeleton).
