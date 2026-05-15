# P3 — exp01 Vẫy Chào Dế (Wave Cricket) Design

**Phase:** 3 (NeoMakerViGate — gameplay đầu tiên)
**Plugin id:** `exp01_wave_cricket`
**Created:** 2026-05-15
**Status:** Design approved, ready for implementation plan

## Mục tiêu

Game vision-tracking đầu tiên hoàn chỉnh end-to-end, chứng minh kiến trúc plugin + vision pipeline hoạt động. Trẻ 4-10 tuổi vẫy tay trước webcam → đàn dế 🦗 bay ra khỏi lũy tre. Vẫy nhanh → flock 5 con. Hết 60s → màn kết quả → tự về Hub.

## Quyết định thiết kế chốt với user (2026-05-15 brainstorm)

| Quyết định | Lựa chọn | Lý do |
|---|---|---|
| Asset visual | Emoji 🦗 + QML shapes vẽ lũy tre | Nhanh dụng, không cần asset ngoài, phù hợp MVP |
| WAVE algorithm | Zero-crossing wrist X trong window 1s | Đơn giản, test được với mock landmark sine |
| Game end | Màn kết quả 3s → auto Hub | Trẻ thấy thành quả, không cần thao tác |
| Audio | Asset WAV nhỏ (chip dế, ting score, fanfare) | Tăng feedback cho trẻ; nguồn Pixabay CC0 |
| Camera view | Mirror full + hand landmark overlay | Trẻ thấy mình + dế bay đè lên — sinh động nhất |
| Architecture | Python-driven (logic Python, QML passive) | Match exit criteria "logic test độc lập" |

## 1. Architecture overview

```
VisionWorker (QThread)
    → SignalBus.vision_frame_ready (queued to main thread)
        ├→ GestureDetector.feed(frame)
        │       └→ SignalBus.gesture_detected.emit("WAVE")
        ├→ ExperienceManager._on_vision_frame
        │       └→ instance.on_vision_frame(frame)
        │              [WaveCricketExperience: step physics, despawn]
        └→ ExperienceManager._on_gesture
                └→ instance.on_gesture("WAVE")
                       [spawn cricket(s) + scoring]

AppController.QTimer(33ms)
    → instance.render_state() → experienceState dict
        → experienceStateChanged signal
            → QML binding update (cricket positions, score, phase)
```

**Module mới:**
- `core/gesture_detector.py` (~120 LOC)
- `experiences/exp01_wave_cricket/logic.py` (rewrite, ~250 LOC)
- `experiences/exp01_wave_cricket/ui.qml` (rewrite, ~150 LOC)
- `experiences/exp01_wave_cricket/test_logic.py` (~13 tests)
- `experiences/exp01_wave_cricket/assets/{cricket_chirp,score_ting,end_fanfare}.wav`
- `tests/unit/test_gesture_detector.py` (~8 tests)

**Module sửa:**
- `services/app_controller.py` — thêm `experienceState` property + QTimer poll
- `app.py` — khởi tạo `GestureDetector`, connect SignalBus

## 2. Game state machine

```
INTRO (2s) → PLAYING (60s) → RESULT (3s) → manager.unload()
```

- **INTRO**: banner "Vẫy tay chào đàn dế!" + countdown 3-2-1. Cricket chưa spawn. WAVE bị bỏ qua.
- **PLAYING**: WAVE → spawn cricket tại vị trí cổ tay. Timer countdown góc trên. Score realtime.
- **RESULT**: freeze sprite, overlay "🎉 Bạn vẫy cho X con dế bay! Điểm: Y". Sau 3s emit `unload({"completed": True, "score": Y, "crickets_flown": X, "duration_seconds": 65.0})`.

Tự động unload sau 65s tổng (2 + 60 + 3) hoặc khi user bấm Back bất kỳ lúc nào.

## 3. Cricket entity + physics

```python
@dataclass
class Cricket:
    id: int
    x: float          # 0.0-1.0 normalized
    y: float          # 0.0-1.0
    vx: float         # velocity normalized/s
    vy: float
    spawned_at: float # time.perf_counter()
    alive: bool = True
```

**Spawn (on_gesture "WAVE" khi phase=PLAYING):**
- Vị trí: lấy `frame.hands[0][0]` (wrist) — fallback (0.5, 0.5) nếu thiếu hand.
- Velocity: `vx = uniform(-0.3, 0.3)`, `vy = uniform(-0.7, -0.5)` (bay chéo lên).
- Bonus flock: nếu ≥3 WAVE trong 2 giây cuối → spawn thêm 5 con cùng lúc (xếp vòng quanh wrist) + active multiplier ×1.5 trong 3s.

**Step physics (on_vision_frame):**
```python
dt = now - self._last_step_time
for c in self._crickets:
    c.x += c.vx * dt
    c.y += c.vy * dt
    age = now - c.spawned_at
    if c.y < -0.1 or age > 4.0:
        c.alive = False
        if c.y < -0.1:
            self._crickets_flown_count += 1
            self._score += int(10 * self._current_multiplier)
self._crickets = [c for c in self._crickets if c.alive]
```

## 4. GestureDetector algorithm

**File:** `core/gesture_detector.py`

**API:**
```python
class GestureDetector:
    def __init__(self, window_seconds: float = 1.0) -> None: ...
    def feed(self, frame: VisionFrame) -> list[str]: ...
    def reset(self) -> None: ...
```

**WAVE algorithm (zero-crossing wrist X):**

1. Lấy `wrist = frame.hands[0][0]` nếu có, push `(timestamp, x, y)` vào deque maxlen=60.
2. Drop sample > 1s tuổi.
3. Nếu < 8 sample → return `[]`.
4. `baseline = mean(xs)`, `dxs = [x - baseline for x in xs]`.
5. `zero_crossings = sum(1 for i in range(1, n) if dxs[i-1] * dxs[i] < 0)`.
6. `amplitude = max(dxs) - min(dxs)`.
7. Trigger nếu `zero_crossings >= 2` AND `amplitude >= 0.05`.
8. Khi trigger:
   - `feed()` trả về `["WAVE"]` (cho test gọi trực tiếp được).
   - Đồng thời `SignalBus.gesture_detected.emit("WAVE")` (cho production routing qua ExperienceManager + AppController).
   - Set `_cooldown_until = now + 0.4s`, half-clear buffer.

**Tham số (constants module-level, tunable):**
```python
WAVE_WINDOW_SEC = 1.0
WAVE_MIN_AMPLITUDE = 0.05      # 5% screen width
WAVE_MIN_CROSSINGS = 2
WAVE_COOLDOWN_SEC = 0.4
WAVE_MIN_SAMPLES = 8
```

**Edge cases:**
- Không thấy tay → push None, nếu nửa buffer là None → reset baseline.
- 2 tay → chỉ track `hands[0]` (P3 đơn giản).
- Cooldown chặn re-trigger từ cùng motion cluster.

**Connect (trong `app.py` boot sequence):**
- Tạo 1 `GestureDetector` instance.
- `SignalBus.vision_frame_ready.connect(detector.feed)` — feed mọi frame.
- `SignalBus.experience_ended.connect(lambda *_: detector.reset())` — clear buffer khi switch experience để không carry pattern qua trải nghiệm mới.

## 5. Data flow Python → QML

**AppController extension (~30 LOC mới):**
- Property `experienceState: QVariant` (dict snapshot từ `render_state()`).
- `QTimer(33ms)` poll khi có experience active. Stop khi `experience_ended`.
- Shallow dict comparison trước khi emit `experienceStateChanged` → tránh QML re-render khi state không đổi.

**`render_state()` schema cho exp01:**
```python
{
    "phase": "intro" | "playing" | "result",
    "elapsed_in_phase": float,
    "remaining": float,            # seconds còn lại của phase playing
    "score": int,
    "crickets_flown": int,
    "flock_bonus_active": bool,
    "wave_count_total": int,
    "wrist": {"x": float, "y": float} | None,
    "crickets": [
        {"id": int, "x": float, "y": float, "alive": bool}, ...
    ],
}
```

**QML binding (key elements):**
- Background: `Image { source: "image://camera/latest?t=..." }` + `Scale { xScale: -1 }` cho mirror.
- Lũy tre: `Rectangle` gradient nâu-xanh ở 30% chiều cao dưới + Repeater "thân tre".
- Cricket sprite: `Repeater { model: app.experienceState.crickets }` → `Text { text: "🦗"; font.pixelSize: 48; x: modelData.x * width; y: modelData.y * height; Behavior on x/y { NumberAnimation { duration: 100 } } }`.
- Hand overlay: `Canvas` vẽ 21 điểm `app.handLandmarks` màu tre, skeleton kết nối.
- HUD: `Text` score góc trái, countdown góc phải.
- Intro/Result overlay: `Rectangle { visible: phase === "intro" || "result" }` với banner.
- Audio: 3 `SoundEffect { source: "assets/..." }`, play khi state change (cricket spawn → chirp, cricket flown → ting, result phase enter → fanfare).

## 6. File layout

```
src/neo_makervigate/
├── core/
│   └── gesture_detector.py          # MỚI
├── services/
│   └── app_controller.py            # SỬA: experienceState + render timer
├── experiences/exp01_wave_cricket/
│   ├── logic.py                     # REWRITE
│   ├── ui.qml                       # REWRITE
│   ├── test_logic.py                # MỚI
│   └── assets/
│       ├── cricket_chirp.wav        # MỚI
│       ├── score_ting.wav           # MỚI
│       └── end_fanfare.wav          # MỚI
└── app.py                           # SỬA: tạo GestureDetector, connect

tests/unit/
└── test_gesture_detector.py         # MỚI

docs/superpowers/specs/
└── 2026-05-15-p3-wave-cricket-design.md   # file này

DOC/PHASES.md                        # SỬA cuối phase: mark P3 done
```

## 7. Testing strategy (TDD)

**Viết test TRƯỚC implementation cho cả 3 file mới.**

### 7.1 `tests/unit/test_gesture_detector.py` (~8 tests)
- `test_wrist_idle_no_gesture` — wrist x đứng yên 1s → []
- `test_wave_two_sine_cycles_triggers` — 2 chu kỳ sine biên 0.1 trong 1s → ["WAVE"]
- `test_wave_amplitude_too_small_no_trigger` — biên 0.02 → []
- `test_wave_single_crossing_no_trigger` — chỉ 1 chuyển hướng → []
- `test_wave_cooldown_blocks_immediate_retrigger` — vẫy → vẫy lại ngay trong 0.3s → 1 trigger
- `test_wave_after_cooldown_triggers_again` — vẫy → sleep 0.5s → vẫy → 2 trigger
- `test_no_hands_does_not_crash` — feed frame không có hands → []
- `test_reset_clears_buffer` — vẫy nửa pattern → reset → vẫy nửa kia → không trigger

Helper `make_wave_frames(wrist_x_series, fps=30, start_time=0.0)` sinh chuỗi `VisionFrame` với timestamps đều.

### 7.2 `experiences/exp01_wave_cricket/test_logic.py` (~13 tests)
- `test_meta_correct_id_and_modules`
- `test_initial_phase_is_intro`
- `test_intro_transitions_to_playing_after_2s` (monkeypatch time)
- `test_wave_during_intro_does_not_spawn`
- `test_wave_during_playing_spawns_cricket_at_wrist`
- `test_cricket_position_updates_with_velocity` (advance 1s, check position)
- `test_cricket_despawns_when_out_of_top`
- `test_cricket_despawns_after_4s_age`
- `test_score_increases_when_cricket_flown_out`
- `test_three_rapid_waves_activate_flock_bonus`
- `test_flock_bonus_spawns_5_extra_crickets`
- `test_60s_elapsed_transitions_to_result`
- `test_result_phase_returns_completion_summary_after_3s`
- `test_render_state_schema_correct`

Time control: monkeypatch `time.perf_counter` qua một fake clock object.

### 7.3 `tests/unit/test_app_controller.py` extension (~3 tests)
- `test_experience_state_empty_when_no_experience`
- `test_experience_state_updates_when_render_state_changes` (qtbot wait_signal)
- `test_render_timer_stops_on_experience_ended`

### 7.4 Smoke test thủ công sau khi unit pass
1. `python -m neo_makervigate` → vào exp01
2. Intro 2s countdown OK
3. Vẫy 1 lần → 1 con dế bay từ vị trí cổ tay lên trên
4. Vẫy nhanh 3 lần → flock 5 con + score x1.5 visible
5. Hết 60s → result 3s → tự về Hub
6. FPS hiển thị qua `app.visionFps` ≥ 30 trên Mac M4
7. Vào/thoát exp01 5 lần → no crash, không leak (theo dõi bằng `tracemalloc`)

### 7.5 Pre-commit gate
- Test: ~45 tests pass (24 cũ + 8 detector + 13 logic + 3 controller)
- `ruff check` clean
- `mypy src/ --strict` clean

## 8. Exit criteria mapping

| PHASES.md §P3 criteria | Cách verify |
|---|---|
| FPS gameplay ≥ 30 trên Mac | Smoke test, đọc `app.visionFps` overlay debug |
| Logic plugin chạy độc lập (không phụ thuộc QML cho test) | `test_logic.py` không import Qt — pure dataclass + pytest |
| Hub → game → Hub không leak memory | `tracemalloc.take_snapshot` trước/sau 5 lần load/unload, delta < 5MB |

## 9. Risk + mitigation

| Risk | Mitigation |
|---|---|
| WAV asset license-free khó tìm | Ưu tiên Pixabay CC0; fallback sinh procedurally bằng `numpy.sin + scipy.io.wavfile` |
| QtMultimedia trên macOS delay first play | Warmup load `QMediaPlayer` + preload buffer trong `on_enter` |
| QTimer 30Hz lag khi vision thread chiếm GIL | Fallback giảm 20Hz hoặc emit signal trực tiếp từ `on_vision_frame` thay vì poll |
| False positive WAVE từ tay run | Cooldown 0.4s + amplitude threshold 0.05; tune ở P7 trên NEO One nếu cần |
| Cricket sprite có thể không hiện trên ARM (font emoji thiếu) | Fallback dùng QML Canvas vẽ ellipse + chân nếu emoji không render |

## 10. Out of scope (sẽ làm ở phase khác)

- **POINT, V_SIGN, OPEN_PALM gestures** — P4-P6 thêm dần
- **Per-hand tracking riêng biệt** — P3 chỉ track `hands[0]`
- **Cricket sprite hand-drawn SVG/PNG** — MVP scope chốt emoji
- **Particle effect khi dế bay (sparkle, dust)** — P7 polish nếu kịp
- **Leaderboard / save best score local** — không cần cho Cổng Vào
- **NEO One ARM perf tuning** — P7
