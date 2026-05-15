# P3 — exp01 Wave Cricket Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first complete vision-tracking gameplay (`exp01_wave_cricket`) for NeoMakerViGate: wave hand → cricket emojis fly out from a bamboo grove. Rapid waves trigger flock bonus. 60s session → result screen → auto return to Hub.

**Architecture:** Python-driven gameplay. New `core/gesture_detector.py` listens to `vision_frame_ready` and emits `gesture_detected("WAVE")`. `WaveCricketExperience` (logic.py) owns all state (Cricket list, score, phase machine), exposes via `render_state()`. `AppController` polls render_state at 30Hz with `QTimer`, exposes as `experienceState` property to QML. QML renders camera mirror + bamboo grove + cricket Repeater + hand-landmark Canvas + HUD reading from `app.experienceState`.

**Tech Stack:** Python 3.12, PyQt6 6.11, MediaPipe Hands (already wired in P1), QML, numpy + scipy.io.wavfile for procedural WAV generation, pytest + pytest-qt.

**Reference spec:** `docs/superpowers/specs/2026-05-15-p3-wave-cricket-design.md`

---

## File Structure

**New files:**
- `src/neo_makervigate/core/gesture_detector.py` — WAVE detection from VisionFrame stream
- `src/neo_makervigate/experiences/exp01_wave_cricket/logic.py` — rewrite stub into full game (uses dataclass `Cricket` + phase machine)
- `src/neo_makervigate/experiences/exp01_wave_cricket/ui.qml` — rewrite stub into full game UI
- `src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py` — game logic tests
- `src/neo_makervigate/experiences/exp01_wave_cricket/assets/cricket_chirp.wav` — generated
- `src/neo_makervigate/experiences/exp01_wave_cricket/assets/score_ting.wav` — generated
- `src/neo_makervigate/experiences/exp01_wave_cricket/assets/end_fanfare.wav` — generated
- `src/neo_makervigate/experiences/exp01_wave_cricket/_gen_assets.py` — generator script (one-shot, committed for reproducibility)
- `tests/unit/test_gesture_detector.py` — detector tests
- `tests/unit/test_app_controller.py` — controller extension tests (file may exist or not, plan accommodates both)

**Modified files:**
- `src/neo_makervigate/services/app_controller.py` — add `experienceState` property + render QTimer
- `src/neo_makervigate/app.py` — wire GestureDetector to SignalBus
- `DOC/PHASES.md` — mark P3 done at end

---

## Task 1: GestureDetector test helper + skeleton

**Files:**
- Create: `tests/unit/test_gesture_detector.py`
- Create: `src/neo_makervigate/core/gesture_detector.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_gesture_detector.py`:

```python
"""Tests cho core/gesture_detector — WAVE phát hiện từ stream VisionFrame."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

import pytest

from neo_makervigate.core.gesture_detector import GestureDetector
from neo_makervigate.core.models import Landmark, VisionFrame


def _make_frame(wrist_x: float | None, t: float) -> VisionFrame:
    """Sinh VisionFrame với 1 tay có cổ tay tại wrist_x normalized, hoặc không có tay nếu None."""
    base = datetime(2026, 1, 1) + timedelta(seconds=t)
    vf = VisionFrame(timestamp=base, width=1280, height=720)
    if wrist_x is not None:
        wrist = Landmark(x=wrist_x, y=0.5, z=0.0)
        # 21 landmarks; chỉ cần wrist (idx 0) đúng, còn lại đặt cùng vị trí
        hand = [wrist] + [Landmark(x=wrist_x, y=0.5, z=0.0) for _ in range(20)]
        vf.hands = [hand]
        vf.has_person = True
    return vf


def _make_sine_frames(
    cycles: float, amplitude: float, fps: int, duration: float, start_t: float = 0.0
) -> list[VisionFrame]:
    """Sinh chuỗi frame với wrist x dao động sine quanh 0.5."""
    n = int(fps * duration)
    frames: list[VisionFrame] = []
    for i in range(n):
        t = start_t + i / fps
        phase = 2 * math.pi * cycles * (i / n)
        x = 0.5 + amplitude * math.sin(phase)
        frames.append(_make_frame(x, t))
    return frames


def test_no_hands_does_not_crash() -> None:
    det = GestureDetector()
    for i in range(20):
        result = det.feed(_make_frame(None, i / 30.0))
        assert result == []


def test_wrist_idle_no_gesture() -> None:
    det = GestureDetector()
    # 30 frames cổ tay đứng yên tại x=0.5
    gestures: list[str] = []
    for i in range(30):
        gestures.extend(det.feed(_make_frame(0.5, i / 30.0)))
    assert gestures == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/unit/test_gesture_detector.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'neo_makervigate.core.gesture_detector'`

- [ ] **Step 3: Create GestureDetector skeleton**

Create `src/neo_makervigate/core/gesture_detector.py`:

```python
"""GestureDetector — phát hiện cử chỉ rời rạc từ stream VisionFrame.

P3 chỉ implement WAVE (cổ tay dao động trái-phải > ngưỡng/1s). Phase sau
mở rộng V_SIGN, POINT, OPEN_PALM, T_POSE.

API tối giản: gọi `feed(frame)` mỗi VisionFrame, trả về list gesture mới
phát hiện. Đồng thời emit `SignalBus.gesture_detected` cho production.
Tách dual-path (return + emit) để test gọi `feed()` trực tiếp không cần Qt.
"""

from __future__ import annotations

import time
from collections import deque

from loguru import logger

from neo_makervigate.core.models import VisionFrame
from neo_makervigate.utils.signal_bus import SignalBus

# Tunable constants — sẽ tune ở P7 trên NEO One nếu cần
WAVE_WINDOW_SEC = 1.0
WAVE_MIN_AMPLITUDE = 0.05  # 5% screen width normalized
WAVE_MIN_CROSSINGS = 2
WAVE_COOLDOWN_SEC = 0.4
WAVE_MIN_SAMPLES = 8
BUFFER_MAXLEN = 60  # ~2s @ 30fps


class GestureDetector:
    """Stateful detector. 1 instance/session — reset() khi switch experience."""

    def __init__(self, window_seconds: float = WAVE_WINDOW_SEC) -> None:
        self._window = window_seconds
        self._buffer: deque[tuple[float, float]] = deque(maxlen=BUFFER_MAXLEN)
        self._cooldown_until: float = 0.0
        self._none_count = 0

    def feed(self, frame: VisionFrame) -> list[str]:
        """Cho ăn 1 frame. Trả về list gesture mới phát hiện trong frame này."""
        now = frame.timestamp.timestamp()

        if not frame.hands:
            self._none_count += 1
            if self._none_count > BUFFER_MAXLEN // 2:
                self._buffer.clear()
                self._none_count = 0
            return []

        self._none_count = 0
        wrist_x = frame.hands[0][0].x
        self._buffer.append((now, wrist_x))

        # Drop samples older than window
        cutoff = now - self._window
        while self._buffer and self._buffer[0][0] < cutoff:
            self._buffer.popleft()

        if len(self._buffer) < WAVE_MIN_SAMPLES:
            return []

        if now < self._cooldown_until:
            return []

        return self._check_wave(now)

    def _check_wave(self, now: float) -> list[str]:
        xs = [x for _, x in self._buffer]
        baseline = sum(xs) / len(xs)
        dxs = [x - baseline for x in xs]
        amplitude = max(dxs) - min(dxs)
        crossings = sum(1 for i in range(1, len(dxs)) if dxs[i - 1] * dxs[i] < 0)

        if crossings >= WAVE_MIN_CROSSINGS and amplitude >= WAVE_MIN_AMPLITUDE:
            self._cooldown_until = now + WAVE_COOLDOWN_SEC
            # Half-clear buffer để không re-trigger từ cùng pattern
            half = len(self._buffer) // 2
            for _ in range(half):
                self._buffer.popleft()
            try:
                SignalBus.instance().gesture_detected.emit("WAVE")
            except Exception as e:
                logger.warning(f"gesture_detected emit failed: {e}")
            return ["WAVE"]
        return []

    def reset(self) -> None:
        """Xóa buffer khi switch experience để không carry pattern qua trải nghiệm mới."""
        self._buffer.clear()
        self._cooldown_until = 0.0
        self._none_count = 0
        # Workaround mypy: dùng time để tránh "unused import"
        _ = time
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/unit/test_gesture_detector.py -v`
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_gesture_detector.py src/neo_makervigate/core/gesture_detector.py
git commit -m "$(cat <<'EOF'
feat(p3): GestureDetector skeleton with idle + no-hands tests

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: WAVE detection — sine cycles trigger, amplitude/crossing thresholds

**Files:**
- Modify: `tests/unit/test_gesture_detector.py`

- [ ] **Step 1: Add 3 tests for WAVE algorithm core**

Append to `tests/unit/test_gesture_detector.py`:

```python
def test_wave_two_sine_cycles_triggers() -> None:
    det = GestureDetector()
    # 2 chu kỳ sine biên 0.1 trong 1s @ 30fps = 30 frames
    frames = _make_sine_frames(cycles=2, amplitude=0.1, fps=30, duration=1.0)
    gestures: list[str] = []
    for f in frames:
        gestures.extend(det.feed(f))
    assert "WAVE" in gestures


def test_wave_amplitude_too_small_no_trigger() -> None:
    det = GestureDetector()
    # Biên 0.02 < threshold 0.05 — không trigger dù có crossings
    frames = _make_sine_frames(cycles=2, amplitude=0.02, fps=30, duration=1.0)
    gestures: list[str] = []
    for f in frames:
        gestures.extend(det.feed(f))
    assert gestures == []


def test_wave_single_crossing_no_trigger() -> None:
    det = GestureDetector()
    # 0.5 cycle: chỉ qua baseline 1 lần (0 → 1 crossing)
    frames = _make_sine_frames(cycles=0.5, amplitude=0.1, fps=30, duration=1.0)
    gestures: list[str] = []
    for f in frames:
        gestures.extend(det.feed(f))
    assert gestures == []
```

- [ ] **Step 2: Run tests to verify all 5 pass**

Run: `.venv/bin/python -m pytest tests/unit/test_gesture_detector.py -v`
Expected: 5 tests PASS (existing logic already handles these — no code change needed)

If any test fails, debug the algorithm in `gesture_detector.py` (most likely a baseline calc or threshold issue). Do NOT loosen thresholds — fix the math.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_gesture_detector.py
git commit -m "$(cat <<'EOF'
test(p3): WAVE algorithm sine + threshold cases

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: WAVE cooldown + reset

**Files:**
- Modify: `tests/unit/test_gesture_detector.py`

- [ ] **Step 1: Add cooldown + reset tests**

Append to `tests/unit/test_gesture_detector.py`:

```python
def test_wave_cooldown_blocks_immediate_retrigger() -> None:
    det = GestureDetector()
    # Vẫy đủ trigger
    frames1 = _make_sine_frames(cycles=2, amplitude=0.1, fps=30, duration=1.0, start_t=0.0)
    gestures: list[str] = []
    for f in frames1:
        gestures.extend(det.feed(f))
    first_count = gestures.count("WAVE")
    assert first_count == 1

    # Vẫy lại ngay trong 0.3s — cooldown 0.4s phải chặn
    frames2 = _make_sine_frames(cycles=2, amplitude=0.1, fps=30, duration=0.3, start_t=1.0)
    for f in frames2:
        gestures.extend(det.feed(f))
    assert gestures.count("WAVE") == first_count


def test_wave_after_cooldown_triggers_again() -> None:
    det = GestureDetector()
    # Vẫy lần 1
    for f in _make_sine_frames(cycles=2, amplitude=0.1, fps=30, duration=1.0, start_t=0.0):
        det.feed(f)
    # Đợi qua cooldown (1.0s start_t + 0.5s gap = 1.5s)
    # Vẫy lần 2 với pattern mới start_t=1.5 (qua 0.4s cooldown)
    gestures: list[str] = []
    for f in _make_sine_frames(cycles=2, amplitude=0.1, fps=30, duration=1.0, start_t=1.5):
        gestures.extend(det.feed(f))
    assert "WAVE" in gestures


def test_reset_clears_buffer() -> None:
    det = GestureDetector()
    # Push 1 cycle (chưa đủ trigger)
    for f in _make_sine_frames(cycles=1, amplitude=0.1, fps=30, duration=0.5, start_t=0.0):
        det.feed(f)
    det.reset()
    # Push thêm 1 cycle nữa — vì reset đã clear, không có đủ data để trigger
    gestures: list[str] = []
    for f in _make_sine_frames(cycles=1, amplitude=0.1, fps=30, duration=0.5, start_t=0.5):
        gestures.extend(det.feed(f))
    assert gestures == []
```

- [ ] **Step 2: Run tests**

Run: `.venv/bin/python -m pytest tests/unit/test_gesture_detector.py -v`
Expected: 8 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_gesture_detector.py
git commit -m "$(cat <<'EOF'
test(p3): WAVE cooldown + reset cases

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Wire GestureDetector into app.py

**Files:**
- Modify: `src/neo_makervigate/app.py`

- [ ] **Step 1: Update app.py to instantiate + connect GestureDetector**

Find the section in `src/neo_makervigate/app.py` between worker creation and ExperienceManager creation. Modify it as follows.

Old (lines around 66-75):

```python
    # Vision pipeline
    source = _create_vision_source(settings.vision_source)
    worker = VisionWorker(source, initial_modules=["hands"])

    # Experience plugin registry + manager
    registry = discover_experiences()
    logger.info(f"Discovered {len(registry)} experience plugin(s): {list(registry.keys())}")
    exp_manager = ExperienceManager(registry=registry, worker=worker)
```

New:

```python
    # Vision pipeline
    source = _create_vision_source(settings.vision_source)
    worker = VisionWorker(source, initial_modules=["hands"])

    # Gesture detector — emit gesture_detected qua SignalBus
    gesture_detector = GestureDetector()
    bus.vision_frame_ready.connect(gesture_detector.feed)
    bus.experience_ended.connect(lambda *_: gesture_detector.reset())

    # Experience plugin registry + manager
    registry = discover_experiences()
    logger.info(f"Discovered {len(registry)} experience plugin(s): {list(registry.keys())}")
    exp_manager = ExperienceManager(registry=registry, worker=worker)
```

Also add import near other `from neo_makervigate...` imports:

```python
from neo_makervigate.core.gesture_detector import GestureDetector
```

- [ ] **Step 2: Run all tests to verify no regression**

Run: `.venv/bin/python -m pytest --tb=short`
Expected: All tests PASS (32 total: 24 prior + 8 detector)

- [ ] **Step 3: Run lint + type check**

```bash
source .venv/bin/activate && ruff check && mypy src/
```
Expected: All checks passed, no mypy errors.

- [ ] **Step 4: Commit**

```bash
git add src/neo_makervigate/app.py
git commit -m "$(cat <<'EOF'
feat(p3): wire GestureDetector into SignalBus

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: WaveCricketExperience — meta + Cricket dataclass + phase skeleton

**Files:**
- Modify: `src/neo_makervigate/experiences/exp01_wave_cricket/logic.py` (REWRITE)
- Create: `src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py`

- [ ] **Step 1: Write the failing tests for meta + initial state**

Create `src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py`:

```python
"""Tests cho WaveCricketExperience — gameplay logic độc lập, không Qt/QML."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from neo_makervigate.core.models import Landmark, VisionFrame
from neo_makervigate.experiences.exp01_wave_cricket.logic import (
    Phase,
    WaveCricketExperience,
)


class _FakeClock:
    """Fake clock thay time.perf_counter để test phase transitions."""

    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def _make_frame(wrist_x: float = 0.5, wrist_y: float = 0.5) -> VisionFrame:
    wrist = Landmark(x=wrist_x, y=wrist_y, z=0.0)
    hand = [wrist] + [Landmark(x=wrist_x, y=wrist_y) for _ in range(20)]
    vf = VisionFrame(timestamp=datetime(2026, 1, 1), width=1280, height=720)
    vf.hands = [hand]
    return vf


@pytest.fixture
def exp_with_clock() -> tuple[WaveCricketExperience, _FakeClock]:
    clock = _FakeClock(0.0)
    exp = WaveCricketExperience(clock=clock)
    exp.on_enter()
    return exp, clock


def test_meta_correct() -> None:
    meta = WaveCricketExperience.meta
    assert meta.id == "exp01_wave_cricket"
    assert "hands" in meta.vision_modules
    assert meta.age_min == 4


def test_initial_phase_is_intro(exp_with_clock: tuple[WaveCricketExperience, _FakeClock]) -> None:
    exp, _ = exp_with_clock
    state: dict[str, Any] = exp.render_state()
    assert state["phase"] == Phase.INTRO.value
    assert state["score"] == 0
    assert state["crickets"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py -v`
Expected: FAIL — `WaveCricketExperience` doesn't accept `clock` arg, no `Phase` enum, etc.

- [ ] **Step 3: Rewrite logic.py**

Replace contents of `src/neo_makervigate/experiences/exp01_wave_cricket/logic.py`:

```python
"""exp01 Vẫy Chào Dế — gameplay đầy đủ (P3).

State machine: INTRO(2s) → PLAYING(60s) → RESULT(3s) → unload.
WAVE detection do GestureDetector lo (core/gesture_detector.py).
Plugin chỉ quản entity Cricket + score + phase + spawn.

Test-friendly: nhận clock callable để inject FakeClock trong test_logic.py.
Production dùng time.perf_counter mặc định.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from neo_makervigate.core.models import ExperienceMeta, VisionFrame
from neo_makervigate.experiences.experience_base import BaseExperience

_QML_PATH = (Path(__file__).parent / "ui.qml").as_posix()
_ASSETS_DIR = (Path(__file__).parent / "assets").as_posix()


# Phase durations (seconds)
INTRO_DURATION = 2.0
PLAYING_DURATION = 60.0
RESULT_DURATION = 3.0

# Cricket physics
CRICKET_VX_RANGE = (-0.3, 0.3)
CRICKET_VY_RANGE = (-0.7, -0.5)
CRICKET_DESPAWN_Y = -0.1
CRICKET_MAX_AGE = 4.0

# Scoring
BASE_SCORE_PER_CRICKET = 10
FLOCK_RAPID_WAVE_COUNT = 3
FLOCK_RAPID_WAVE_WINDOW = 2.0
FLOCK_BONUS_DURATION = 3.0
FLOCK_MULTIPLIER = 1.5
FLOCK_EXTRA_CRICKETS = 5


class Phase(str, Enum):
    INTRO = "intro"
    PLAYING = "playing"
    RESULT = "result"
    DONE = "done"


@dataclass
class Cricket:
    id: int
    x: float
    y: float
    vx: float
    vy: float
    spawned_at: float
    alive: bool = True


@dataclass
class _Summary:
    score: int = 0
    crickets_flown: int = 0
    wave_count_total: int = 0


class WaveCricketExperience(BaseExperience):
    """Vẫy tay → đàn dế bay khỏi lũy tre. Scoring nhân nhịp."""

    meta = ExperienceMeta(
        id="exp01_wave_cricket",
        title="Vẫy Chào Dế",
        subtitle="Wave Hello Cricket",
        age_min=4,
        age_max=10,
        vision_modules=("hands",),
        needs_qwen=False,
        needs_voice=False,
        needs_internet=False,
        icon_path="",
        dev_days=3,
    )

    def __init__(
        self,
        clock: Callable[[], float] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        super().__init__()
        self._clock: Callable[[], float] = clock or time.perf_counter
        self._rng = rng or random.Random()
        self._phase: Phase = Phase.INTRO
        self._phase_started_at: float = 0.0
        self._crickets: list[Cricket] = []
        self._next_cricket_id: int = 0
        self._last_step_at: float = 0.0
        self._summary: _Summary = _Summary()
        self._wave_timestamps: list[float] = []
        self._flock_bonus_until: float = 0.0
        self._last_wrist: tuple[float, float] | None = None

    def get_qml_path(self) -> str:
        return _QML_PATH

    def on_enter(self) -> None:
        now = self._clock()
        self._phase = Phase.INTRO
        self._phase_started_at = now
        self._last_step_at = now
        self._crickets.clear()
        self._summary = _Summary()
        self._wave_timestamps.clear()
        self._flock_bonus_until = 0.0
        self._last_wrist = None
        self._next_cricket_id = 0

    def on_vision_frame(self, frame: VisionFrame) -> None:
        now = self._clock()
        dt = max(0.0, now - self._last_step_at)
        self._last_step_at = now

        # Track wrist for spawn position
        if frame.hands:
            wrist = frame.hands[0][0]
            self._last_wrist = (wrist.x, wrist.y)

        self._step_phase(now)
        self._step_physics(dt, now)

    def on_gesture(self, gesture: str) -> None:
        if gesture != "WAVE":
            return
        now = self._clock()
        self._summary.wave_count_total += 1
        self._wave_timestamps.append(now)
        # Drop wave history outside flock window
        self._wave_timestamps = [
            t for t in self._wave_timestamps if now - t <= FLOCK_RAPID_WAVE_WINDOW
        ]

        if self._phase != Phase.PLAYING:
            return

        # Check flock bonus trigger
        if len(self._wave_timestamps) >= FLOCK_RAPID_WAVE_COUNT:
            self._flock_bonus_until = now + FLOCK_BONUS_DURATION
            self._spawn_flock(now)
        else:
            self._spawn_one(now)

    def render_state(self) -> dict[str, object]:
        now = self._clock()
        remaining = 0.0
        if self._phase == Phase.PLAYING:
            elapsed_playing = now - self._phase_started_at
            remaining = max(0.0, PLAYING_DURATION - elapsed_playing)
        return {
            "phase": self._phase.value,
            "elapsed_in_phase": now - self._phase_started_at,
            "remaining": remaining,
            "score": self._summary.score,
            "crickets_flown": self._summary.crickets_flown,
            "flock_bonus_active": now < self._flock_bonus_until,
            "wave_count_total": self._summary.wave_count_total,
            "wrist": (
                {"x": self._last_wrist[0], "y": self._last_wrist[1]}
                if self._last_wrist is not None
                else None
            ),
            "crickets": [
                {"id": c.id, "x": c.x, "y": c.y, "alive": c.alive}
                for c in self._crickets
            ],
        }

    def completion_summary(self) -> dict[str, Any]:
        """Dict trả về cho manager.unload({summary})."""
        return {
            "completed": True,
            "score": self._summary.score,
            "crickets_flown": self._summary.crickets_flown,
            "wave_count_total": self._summary.wave_count_total,
        }

    # ---- Internal ----

    def _step_phase(self, now: float) -> None:
        elapsed = now - self._phase_started_at
        if self._phase == Phase.INTRO and elapsed >= INTRO_DURATION:
            self._phase = Phase.PLAYING
            self._phase_started_at = now
        elif self._phase == Phase.PLAYING and elapsed >= PLAYING_DURATION:
            self._phase = Phase.RESULT
            self._phase_started_at = now
        elif self._phase == Phase.RESULT and elapsed >= RESULT_DURATION:
            self._phase = Phase.DONE
            self._phase_started_at = now

    def _step_physics(self, dt: float, now: float) -> None:
        for c in self._crickets:
            if not c.alive:
                continue
            c.x += c.vx * dt
            c.y += c.vy * dt
            age = now - c.spawned_at
            if c.y < CRICKET_DESPAWN_Y:
                c.alive = False
                self._summary.crickets_flown += 1
                mult = FLOCK_MULTIPLIER if now < self._flock_bonus_until else 1.0
                self._summary.score += int(BASE_SCORE_PER_CRICKET * mult)
            elif age > CRICKET_MAX_AGE:
                c.alive = False
        # Reap
        self._crickets = [c for c in self._crickets if c.alive]

    def _spawn_one(self, now: float) -> None:
        x, y = self._last_wrist if self._last_wrist is not None else (0.5, 0.5)
        self._crickets.append(self._make_cricket(x, y, now))

    def _spawn_flock(self, now: float) -> None:
        x, y = self._last_wrist if self._last_wrist is not None else (0.5, 0.5)
        # Spawn 1 + 5 extra around wrist
        self._crickets.append(self._make_cricket(x, y, now))
        for i in range(FLOCK_EXTRA_CRICKETS):
            offset_x = (i - FLOCK_EXTRA_CRICKETS / 2) * 0.04
            self._crickets.append(self._make_cricket(x + offset_x, y, now))

    def _make_cricket(self, x: float, y: float, now: float) -> Cricket:
        c = Cricket(
            id=self._next_cricket_id,
            x=max(0.0, min(1.0, x)),
            y=max(0.0, min(1.0, y)),
            vx=self._rng.uniform(*CRICKET_VX_RANGE),
            vy=self._rng.uniform(*CRICKET_VY_RANGE),
            spawned_at=now,
        )
        self._next_cricket_id += 1
        return c


EXPERIENCE = WaveCricketExperience
```

- [ ] **Step 4: Run tests to verify the 2 new tests pass**

Run: `.venv/bin/python -m pytest src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py -v`
Expected: 2 tests PASS

- [ ] **Step 5: Run all tests + lint**

```bash
.venv/bin/python -m pytest --tb=short
source .venv/bin/activate && ruff check && mypy src/
```
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add src/neo_makervigate/experiences/exp01_wave_cricket/logic.py \
        src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py
git commit -m "$(cat <<'EOF'
feat(p3): WaveCricketExperience scaffold — meta + Cricket + phase enum

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Phase transitions INTRO → PLAYING → RESULT → DONE

**Files:**
- Modify: `src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py`

- [ ] **Step 1: Add phase transition tests**

Append to `test_logic.py`:

```python
def test_intro_transitions_to_playing_after_2s(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    # Tick frame ngay sau enter
    exp.on_vision_frame(_make_frame())
    assert exp.render_state()["phase"] == Phase.INTRO.value
    # Advance 2.1s qua INTRO duration
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame())
    assert exp.render_state()["phase"] == Phase.PLAYING.value


def test_playing_transitions_to_result_after_60s(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    # INTRO → PLAYING
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame())
    assert exp.render_state()["phase"] == Phase.PLAYING.value
    # PLAYING 60s → RESULT
    clock.advance(60.1)
    exp.on_vision_frame(_make_frame())
    assert exp.render_state()["phase"] == Phase.RESULT.value


def test_result_transitions_to_done_after_3s(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame())  # → PLAYING
    clock.advance(60.1)
    exp.on_vision_frame(_make_frame())  # → RESULT
    clock.advance(3.1)
    exp.on_vision_frame(_make_frame())  # → DONE
    assert exp.render_state()["phase"] == Phase.DONE.value
```

- [ ] **Step 2: Run tests**

Run: `.venv/bin/python -m pytest src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py -v`
Expected: 5 tests PASS (existing logic already implements transitions correctly).

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py
git commit -m "$(cat <<'EOF'
test(p3): phase transitions INTRO/PLAYING/RESULT/DONE

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Spawn cricket on WAVE (only during PLAYING)

**Files:**
- Modify: `src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py`

- [ ] **Step 1: Add spawn tests**

Append to `test_logic.py`:

```python
def test_wave_during_intro_does_not_spawn(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    exp, _ = exp_with_clock
    exp.on_vision_frame(_make_frame(wrist_x=0.3, wrist_y=0.4))
    exp.on_gesture("WAVE")
    assert exp.render_state()["crickets"] == []


def test_wave_during_playing_spawns_cricket_at_wrist(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame(wrist_x=0.3, wrist_y=0.4))  # → PLAYING
    exp.on_gesture("WAVE")
    crickets = exp.render_state()["crickets"]
    assert len(crickets) == 1
    assert abs(crickets[0]["x"] - 0.3) < 1e-6
    assert abs(crickets[0]["y"] - 0.4) < 1e-6


def test_non_wave_gesture_ignored(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame())
    exp.on_gesture("V_SIGN")
    exp.on_gesture("POINT")
    assert exp.render_state()["crickets"] == []
    assert exp.render_state()["score"] == 0
```

- [ ] **Step 2: Run tests**

Run: `.venv/bin/python -m pytest src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py -v`
Expected: 8 tests PASS (logic already handles spawn correctly).

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py
git commit -m "$(cat <<'EOF'
test(p3): cricket spawn at wrist during PLAYING only

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Cricket physics + despawn + scoring

**Files:**
- Modify: `src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py`

- [ ] **Step 1: Add physics + despawn + score tests**

Append to `test_logic.py`:

```python
def test_cricket_position_updates_with_velocity(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    # Dùng RNG seed cố định để velocity deterministic
    import random as _r
    clock = _FakeClock(0.0)
    exp = WaveCricketExperience(clock=clock, rng=_r.Random(42))
    exp.on_enter()
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.8))
    exp.on_gesture("WAVE")
    before = exp.render_state()["crickets"][0]
    # Advance 0.5s — y giảm (vy âm)
    clock.advance(0.5)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.8))
    after = exp.render_state()["crickets"][0]
    assert after["y"] < before["y"], "Cricket should rise (vy negative)"


def test_cricket_despawns_when_out_of_top_and_scores(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    import random as _r
    clock = _FakeClock(0.0)
    exp = WaveCricketExperience(clock=clock, rng=_r.Random(42))
    exp.on_enter()
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.1))
    exp.on_gesture("WAVE")
    assert len(exp.render_state()["crickets"]) == 1
    # Advance enough cho cricket bay khỏi top (y < -0.1).
    # vy in [-0.7, -0.5] → cần ~ 0.2/0.5 = 0.4s tối thiểu, advance 2s an toàn.
    clock.advance(2.0)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.1))
    state = exp.render_state()
    assert state["crickets"] == []
    assert state["crickets_flown"] == 1
    assert state["score"] >= 10  # base 10 (no bonus)


def test_cricket_despawns_after_max_age_without_score(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    import random as _r
    clock = _FakeClock(0.0)
    # Custom RNG → vy gần 0 để không bay khỏi screen → trigger age despawn
    class _StaticRng:
        def uniform(self, a: float, b: float) -> float:
            return 0.0  # vx=0, vy=0
    exp = WaveCricketExperience(clock=clock, rng=_StaticRng())  # type: ignore[arg-type]
    exp.on_enter()
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.5))
    exp.on_gesture("WAVE")
    assert len(exp.render_state()["crickets"]) == 1
    # Advance > 4s
    clock.advance(4.5)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.5))
    state = exp.render_state()
    assert state["crickets"] == []
    # Despawned by age — không tính score
    assert state["score"] == 0
    assert state["crickets_flown"] == 0
```

- [ ] **Step 2: Run tests**

Run: `.venv/bin/python -m pytest src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py -v`
Expected: 11 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py
git commit -m "$(cat <<'EOF'
test(p3): cricket physics, despawn, score

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Flock bonus on rapid waves

**Files:**
- Modify: `src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py`

- [ ] **Step 1: Add flock bonus tests**

Append to `test_logic.py`:

```python
def test_three_rapid_waves_spawn_flock(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.5))
    # WAVE 1 + 2: spawn 1 con mỗi lần
    exp.on_gesture("WAVE")
    clock.advance(0.2)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.5))
    exp.on_gesture("WAVE")
    assert len(exp.render_state()["crickets"]) == 2
    # WAVE 3 trong vòng 2s: trigger flock — spawn 1 + 5 = 6 thêm
    clock.advance(0.2)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.5))
    exp.on_gesture("WAVE")
    state = exp.render_state()
    assert len(state["crickets"]) == 2 + 6
    assert state["flock_bonus_active"] is True


def test_flock_multiplier_applies_to_score(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    import random as _r
    clock = _FakeClock(0.0)
    exp = WaveCricketExperience(clock=clock, rng=_r.Random(42))
    exp.on_enter()
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.1))
    # 3 rapid WAVE để trigger flock
    exp.on_gesture("WAVE")
    clock.advance(0.1)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.1))
    exp.on_gesture("WAVE")
    clock.advance(0.1)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.1))
    exp.on_gesture("WAVE")
    # Advance cho tất cả bay khỏi top (vy có thể tới -0.5 → ~0.4s)
    clock.advance(2.0)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.1))
    state = exp.render_state()
    # Mỗi cricket flown trong window bonus → 15 điểm thay 10
    assert state["score"] >= 15 * state["crickets_flown"]
```

- [ ] **Step 2: Run tests**

Run: `.venv/bin/python -m pytest src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py -v`
Expected: 13 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py
git commit -m "$(cat <<'EOF'
test(p3): flock bonus rapid waves + multiplier

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: render_state schema test + completion_summary

**Files:**
- Modify: `src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py`

- [ ] **Step 1: Add schema + summary tests**

Append to `test_logic.py`:

```python
def test_render_state_schema_complete(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    exp, _ = exp_with_clock
    state = exp.render_state()
    expected_keys = {
        "phase",
        "elapsed_in_phase",
        "remaining",
        "score",
        "crickets_flown",
        "flock_bonus_active",
        "wave_count_total",
        "wrist",
        "crickets",
    }
    assert set(state.keys()) == expected_keys


def test_completion_summary_after_game_end(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    import random as _r
    clock = _FakeClock(0.0)
    exp = WaveCricketExperience(clock=clock, rng=_r.Random(42))
    exp.on_enter()
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.1))
    exp.on_gesture("WAVE")
    clock.advance(2.0)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.1))
    # Advance to RESULT
    clock.advance(58.0)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.1))
    summary = exp.completion_summary()
    assert summary["completed"] is True
    assert summary["score"] >= 10
    assert summary["wave_count_total"] == 1
```

- [ ] **Step 2: Run all tests + lint**

```bash
.venv/bin/python -m pytest --tb=short
source .venv/bin/activate && ruff check && mypy src/
```
Expected: 15 logic tests + 8 detector + 24 existing = 47 tests PASS. Lint/mypy clean.

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/experiences/exp01_wave_cricket/test_logic.py
git commit -m "$(cat <<'EOF'
test(p3): render_state schema + completion summary

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: AppController experienceState property + render QTimer

**Files:**
- Modify: `src/neo_makervigate/services/app_controller.py`
- Create: `tests/unit/test_app_controller.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_app_controller.py`:

```python
"""Tests cho AppController extension — experienceState property + render timer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from neo_makervigate.core.models import ExperienceMeta
from neo_makervigate.experiences.experience_base import BaseExperience
from neo_makervigate.services.app_controller import AppController
from neo_makervigate.services.experience_manager import ExperienceManager
from neo_makervigate.utils.signal_bus import SignalBus


@dataclass
class _MutableState:
    counter: int = 0


class _StateExp(BaseExperience):
    meta = ExperienceMeta(
        id="state_test",
        title="StateTest",
        subtitle="",
        age_min=4,
        age_max=14,
        vision_modules=("hands",),
    )

    def __init__(self) -> None:
        super().__init__()
        self._state = _MutableState()

    def get_qml_path(self) -> str:
        return ""

    def bump(self) -> None:
        self._state.counter += 1

    def render_state(self) -> dict[str, object]:
        return {"counter": self._state.counter}


def test_experience_state_empty_when_no_experience(qapp) -> None:
    ctrl = AppController(experience_manager=None)
    assert ctrl.experienceState == {}


def test_experience_state_updates_after_load(qapp) -> None:
    mgr = ExperienceManager(registry={"state_test": _StateExp})
    ctrl = AppController(experience_manager=mgr)
    mgr.load("state_test")
    # Manual poll — timer may not have fired yet
    ctrl._poll_render_state()
    assert ctrl.experienceState == {"counter": 0}
    # Mutate underlying state
    inst = mgr.current_instance
    assert isinstance(inst, _StateExp)
    inst.bump()
    ctrl._poll_render_state()
    assert ctrl.experienceState == {"counter": 1}


def test_experience_state_cleared_on_end(qapp) -> None:
    mgr = ExperienceManager(registry={"state_test": _StateExp})
    ctrl = AppController(experience_manager=mgr)
    mgr.load("state_test")
    ctrl._poll_render_state()
    assert ctrl.experienceState != {}
    mgr.unload()
    # _on_experience_ended slot clears state
    assert ctrl.experienceState == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/unit/test_app_controller.py -v`
Expected: FAIL — `experienceState` property + `_poll_render_state` not defined.

- [ ] **Step 3: Modify app_controller.py**

In `src/neo_makervigate/services/app_controller.py`:

Add import at top:

```python
from PyQt6.QtCore import (  # type: ignore[attr-defined]
    QObject,
    QTimer,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)
```

Add new signal in the signal declarations block (after `statusChanged = pyqtSignal()`):

```python
    experienceStateChanged = pyqtSignal()
```

In `__init__`, after `self._experience_metas = ...` line:

```python
        self._experience_state: dict[str, object] = {}
        self._render_timer = QTimer(self)
        self._render_timer.setInterval(33)  # ~30Hz
        self._render_timer.timeout.connect(self._poll_render_state)
```

Add new property method (placed with other pyqtProperty blocks, e.g. after `status` property):

```python
    @pyqtProperty("QVariant", notify=experienceStateChanged)
    def experienceState(self) -> Any:
        return self._experience_state
```

Modify `_on_experience_started`:

```python
    @pyqtSlot(str)
    def _on_experience_started(self, exp_id: str) -> None:
        self._current_experience = exp_id
        self._status = "playing"
        self.currentExperienceChanged.emit()
        self.statusChanged.emit()
        self._render_timer.start()
```

Modify `_on_experience_ended`:

```python
    @pyqtSlot(str, dict)
    def _on_experience_ended(self, exp_id: str, summary: dict[str, object]) -> None:
        _ = exp_id, summary
        self._render_timer.stop()
        self._current_experience = ""
        self._status = "hub"
        self._experience_state = {}
        self.currentExperienceChanged.emit()
        self.statusChanged.emit()
        self.experienceStateChanged.emit()
```

Add new method (anywhere in class body):

```python
    def _poll_render_state(self) -> None:
        if self._experience_manager is None:
            return
        inst = self._experience_manager.current_instance
        if inst is None:
            return
        try:
            new_state = inst.render_state()
        except Exception as e:
            logger.warning(f"render_state() raised: {e}")
            return
        if new_state != self._experience_state:
            self._experience_state = new_state
            self.experienceStateChanged.emit()
```

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/unit/test_app_controller.py -v
.venv/bin/python -m pytest --tb=short
source .venv/bin/activate && ruff check && mypy src/
```
Expected: 3 controller tests + 47 prior = 50 total. Lint/mypy clean.

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/services/app_controller.py tests/unit/test_app_controller.py
git commit -m "$(cat <<'EOF'
feat(p3): AppController.experienceState + 30Hz render timer

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Generate WAV assets

**Files:**
- Create: `src/neo_makervigate/experiences/exp01_wave_cricket/_gen_assets.py`
- Create: `src/neo_makervigate/experiences/exp01_wave_cricket/assets/cricket_chirp.wav`
- Create: `src/neo_makervigate/experiences/exp01_wave_cricket/assets/score_ting.wav`
- Create: `src/neo_makervigate/experiences/exp01_wave_cricket/assets/end_fanfare.wav`

- [ ] **Step 1: Write the asset generator**

Create `src/neo_makervigate/experiences/exp01_wave_cricket/_gen_assets.py`:

```python
"""One-shot generator cho WAV assets exp01.

Chạy: `.venv/bin/python -m neo_makervigate.experiences.exp01_wave_cricket._gen_assets`

Sinh procedurally bằng numpy để không phụ thuộc asset ngoài + reproducible.
Commit cả script này + 3 file WAV để repo self-contained.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io import wavfile

SAMPLE_RATE = 22050
ASSETS_DIR = Path(__file__).parent / "assets"


def _envelope(n: int, attack: float = 0.05, release: float = 0.3) -> np.ndarray:
    """Linear attack + exponential release envelope."""
    env = np.ones(n)
    a = int(attack * n)
    r = int(release * n)
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if r > 0:
        env[-r:] = np.linspace(1, 0, r) ** 2
    return env


def _save(name: str, signal: np.ndarray) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    # Normalize to int16 range
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.8
    pcm = (signal * 32767).astype(np.int16)
    wavfile.write(ASSETS_DIR / name, SAMPLE_RATE, pcm)
    print(f"Wrote {ASSETS_DIR / name} ({len(signal) / SAMPLE_RATE:.2f}s)")


def gen_cricket_chirp() -> None:
    """Tiếng dế ríu rít — burst 3 chirp ngắn."""
    duration = 0.6
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # Chirp: 2.8kHz + 3.2kHz mix
    chirp = 0.5 * np.sin(2 * np.pi * 2800 * t) + 0.5 * np.sin(2 * np.pi * 3200 * t)
    # Amplitude modulation 30Hz để giống cánh dế
    am = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 30 * t))
    signal = chirp * am * _envelope(len(t), attack=0.02, release=0.4)
    _save("cricket_chirp.wav", signal)


def gen_score_ting() -> None:
    """Ting score — bell-like."""
    duration = 0.4
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # Bell: 880Hz + 1760Hz + 2640Hz harmonics, exp decay
    decay = np.exp(-4 * t)
    signal = (
        0.6 * np.sin(2 * np.pi * 880 * t)
        + 0.3 * np.sin(2 * np.pi * 1760 * t)
        + 0.1 * np.sin(2 * np.pi * 2640 * t)
    ) * decay
    signal *= _envelope(len(t), attack=0.005, release=0.5)
    _save("score_ting.wav", signal)


def gen_end_fanfare() -> None:
    """Fanfare kết thúc — 3 nốt arpeggio C5-E5-G5."""
    notes_hz = [523.25, 659.25, 783.99]  # C5, E5, G5
    note_dur = 0.25
    samples_per_note = int(SAMPLE_RATE * note_dur)
    parts = []
    for hz in notes_hz:
        t = np.linspace(0, note_dur, samples_per_note, endpoint=False)
        sig = np.sin(2 * np.pi * hz * t) * _envelope(samples_per_note, attack=0.02, release=0.3)
        parts.append(sig)
    signal = np.concatenate(parts)
    # Add final sustain on G5
    t_sus = np.linspace(0, 0.5, int(SAMPLE_RATE * 0.5), endpoint=False)
    sus = (
        np.sin(2 * np.pi * 783.99 * t_sus)
        * _envelope(len(t_sus), attack=0.01, release=0.7)
    )
    signal = np.concatenate([signal, sus])
    _save("end_fanfare.wav", signal)


def main() -> None:
    gen_cricket_chirp()
    gen_score_ting()
    gen_end_fanfare()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify scipy is available; if not, install**

```bash
.venv/bin/python -c "import scipy.io.wavfile" 2>&1
```
If `ModuleNotFoundError`: `.venv/bin/pip install scipy`

- [ ] **Step 3: Run generator**

```bash
.venv/bin/python -m neo_makervigate.experiences.exp01_wave_cricket._gen_assets
```
Expected: 3 files written under `assets/`.

Verify:
```bash
ls -la src/neo_makervigate/experiences/exp01_wave_cricket/assets/
```

- [ ] **Step 4: Add scipy to pyproject if necessary**

Check `pyproject.toml` dependencies. If scipy isn't listed, append it under `dependencies`. Format example:

```toml
dependencies = [
    # existing lines preserved …
    "scipy>=1.11",
]
```

Run `.venv/bin/pip install -e .` to confirm install resolves.

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/experiences/exp01_wave_cricket/_gen_assets.py \
        src/neo_makervigate/experiences/exp01_wave_cricket/assets/ \
        pyproject.toml
git commit -m "$(cat <<'EOF'
feat(p3): generate procedural WAV assets (chirp/ting/fanfare)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: ui.qml — camera mirror + bamboo + cricket sprites

**Files:**
- Modify: `src/neo_makervigate/experiences/exp01_wave_cricket/ui.qml` (REWRITE)

- [ ] **Step 1: Replace stub QML with gameplay scene**

Replace contents of `src/neo_makervigate/experiences/exp01_wave_cricket/ui.qml`:

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import "../../ui/qml/singletons" as Sing

Item {
    id: root
    anchors.fill: parent

    // ---- State helpers from app.experienceState ----
    readonly property var state: app.experienceState
    readonly property string phase: state && state.phase ? state.phase : "intro"
    readonly property int score: state && state.score !== undefined ? state.score : 0
    readonly property real remaining: state && state.remaining !== undefined ? state.remaining : 0
    readonly property bool flockBonus: state && state.flock_bonus_active ? true : false
    readonly property var crickets: state && state.crickets ? state.crickets : []

    // ---- Camera mirror background ----
    Image {
        id: cameraView
        anchors.fill: parent
        cache: false
        fillMode: Image.PreserveAspectCrop
        source: "image://camera/latest"
        transform: Scale { xScale: -1; origin.x: cameraView.width / 2 }
        // Force refresh — bind to a property that ticks
        property int tick: 0
        Timer {
            interval: 33
            running: true
            repeat: true
            onTriggered: {
                cameraView.tick++
                cameraView.source = "image://camera/latest?t=" + cameraView.tick
            }
        }
    }

    // Tint overlay nhẹ để sprite + HUD rõ hơn
    Rectangle {
        anchors.fill: parent
        color: "#20000000"
    }

    // ---- Lũy tre bottom ----
    Rectangle {
        id: bamboo
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: parent.height * 0.3
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#005C8A3A" }
            GradientStop { position: 0.5; color: "#FF5C8A3A" }
            GradientStop { position: 1.0; color: "#FF3F6627" }
        }
        Row {
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 8
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 18
            Repeater {
                model: 8
                Rectangle {
                    width: 12
                    height: 80 + (index % 3) * 24
                    radius: 6
                    color: "#3F6627"
                    border.color: "#5C8A3A"
                    border.width: 1
                }
            }
        }
    }

    // ---- Cricket sprite layer ----
    Repeater {
        model: root.crickets
        Text {
            text: "🦗"
            font.pixelSize: 56
            x: modelData.x * root.width - width / 2
            y: modelData.y * root.height - height / 2
            opacity: modelData.alive ? 1.0 : 0.0
            Behavior on x { NumberAnimation { duration: 80; easing.type: Easing.Linear } }
            Behavior on y { NumberAnimation { duration: 80; easing.type: Easing.Linear } }
        }
    }
}
```

- [ ] **Step 2: Verify all tests still pass (no Python regression)**

```bash
.venv/bin/python -m pytest --tb=short
```
Expected: 50 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/experiences/exp01_wave_cricket/ui.qml
git commit -m "$(cat <<'EOF'
feat(p3): ui.qml camera mirror + bamboo + cricket Repeater

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: ui.qml — hand landmark overlay + HUD + intro/result overlays + audio

**Files:**
- Modify: `src/neo_makervigate/experiences/exp01_wave_cricket/ui.qml`

- [ ] **Step 1: Add Canvas overlay + HUD + audio**

Insert the following blocks into `ui.qml` AFTER the cricket Repeater block but BEFORE the closing `}` of `Item { id: root`.

```qml
    // ---- Hand landmark overlay (Canvas) ----
    Canvas {
        id: handCanvas
        anchors.fill: parent
        renderTarget: Canvas.FramebufferObject

        // Redraw when handLandmarks updates
        Connections {
            target: app
            function onHandLandmarksChanged() { handCanvas.requestPaint() }
        }

        onPaint: {
            const ctx = handCanvas.getContext("2d")
            ctx.reset()
            const hands = app.handLandmarks
            if (!hands || hands.length === 0) return

            ctx.strokeStyle = "#5C8A3A"
            ctx.fillStyle = "#C77B2C"
            ctx.lineWidth = 3

            for (let h = 0; h < hands.length; h++) {
                const hand = hands[h]
                // Skeleton connections — wrist(0) → MCP joints
                const connections = [
                    [0,1],[1,2],[2,3],[3,4],
                    [0,5],[5,6],[6,7],[7,8],
                    [0,9],[9,10],[10,11],[11,12],
                    [0,13],[13,14],[14,15],[15,16],
                    [0,17],[17,18],[18,19],[19,20]
                ]
                for (let c = 0; c < connections.length; c++) {
                    const [a, b] = connections[c]
                    if (a >= hand.length || b >= hand.length) continue
                    // Mirror x (cam is flipped)
                    const ax = (1 - hand[a].x) * width
                    const ay = hand[a].y * height
                    const bx = (1 - hand[b].x) * width
                    const by = hand[b].y * height
                    ctx.beginPath()
                    ctx.moveTo(ax, ay)
                    ctx.lineTo(bx, by)
                    ctx.stroke()
                }
                // Dots
                for (let i = 0; i < hand.length; i++) {
                    const px = (1 - hand[i].x) * width
                    const py = hand[i].y * height
                    ctx.beginPath()
                    ctx.arc(px, py, 5, 0, 2 * Math.PI)
                    ctx.fill()
                }
            }
        }
    }

    // ---- HUD: score top-left, countdown top-right ----
    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.margins: 24
        width: scoreText.implicitWidth + 32
        height: 56
        radius: 28
        color: root.flockBonus ? "#C77B2C" : "#FF5C8A3A"
        Text {
            id: scoreText
            anchors.centerIn: parent
            text: "🎯 " + root.score + (root.flockBonus ? "  ×1.5" : "")
            color: "white"
            font.pixelSize: 28
            font.bold: true
        }
    }

    Rectangle {
        visible: root.phase === "playing"
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 24
        width: 110
        height: 56
        radius: 28
        color: "#FF3F6627"
        Text {
            anchors.centerIn: parent
            text: Math.ceil(root.remaining) + "s"
            color: "white"
            font.pixelSize: 28
            font.bold: true
        }
    }

    // ---- Intro overlay ----
    Rectangle {
        visible: root.phase === "intro"
        anchors.fill: parent
        color: "#A0000000"

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 24
            Text {
                text: "🦗 Vẫy tay chào đàn dế!"
                color: "white"
                font.pixelSize: 56
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Sẵn sàng nhé..."
                color: "#FAF6EE"
                font.pixelSize: 28
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    // ---- Result overlay ----
    Rectangle {
        visible: root.phase === "result"
        anchors.fill: parent
        color: "#C0000000"

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 24
            Text {
                text: "🎉 Tuyệt vời!"
                color: "white"
                font.pixelSize: 72
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Bạn vẫy cho " + (state && state.crickets_flown ? state.crickets_flown : 0) + " con dế bay"
                color: "#FAF6EE"
                font.pixelSize: 32
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Điểm: " + root.score
                color: "#C77B2C"
                font.pixelSize: 48
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    // ---- Audio (cricket spawn / cricket flown / result enter) ----
    SoundEffect {
        id: sfxChirp
        source: Qt.resolvedUrl("assets/cricket_chirp.wav")
    }
    SoundEffect {
        id: sfxTing
        source: Qt.resolvedUrl("assets/score_ting.wav")
    }
    SoundEffect {
        id: sfxFanfare
        source: Qt.resolvedUrl("assets/end_fanfare.wav")
    }

    // Track cricket count to trigger sfx when changes
    property int lastCricketCount: 0
    property int lastFlownCount: 0
    property string lastPhase: ""

    onCricketsChanged: {
        if (crickets.length > lastCricketCount) {
            sfxChirp.play()
        }
        lastCricketCount = crickets.length
        // crickets_flown increments
        const flown = state && state.crickets_flown ? state.crickets_flown : 0
        if (flown > lastFlownCount) {
            sfxTing.play()
        }
        lastFlownCount = flown
    }

    onPhaseChanged: {
        if (phase === "result" && lastPhase !== "result") {
            sfxFanfare.play()
        }
        lastPhase = phase
    }
}
```

(Remove the final closing brace `}` from the previous Task 13 file content — the new content above closes the `Item { id: root }` properly.)

NOTE: in the actual file edit, you are inserting the new blocks INTO the existing `Item { id: root … }`. Make sure you preserve the existing background/Rectangle tint/Lũy tre/cricket Repeater from Task 13 — only ADD the new overlays + Canvas + HUD + audio after them.

- [ ] **Step 2: Run all tests**

```bash
.venv/bin/python -m pytest --tb=short
```
Expected: 50 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/experiences/exp01_wave_cricket/ui.qml
git commit -m "$(cat <<'EOF'
feat(p3): ui.qml hand overlay + HUD + intro/result + audio

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: ExperienceManager auto-unload on Phase.DONE

**Files:**
- Modify: `src/neo_makervigate/services/experience_manager.py`

The game logic transitions to `Phase.DONE` after RESULT 3s. Manager must detect this and auto-call `unload()` with the completion summary, so the app returns to Hub without user pressing Back.

- [ ] **Step 1: Add detection in _on_vision_frame after instance step**

Find this section in `experience_manager.py`:

```python
    def _on_vision_frame(self, frame: VisionFrame) -> None:
        if self._current_instance is None:
            return
        start = time.perf_counter()
        try:
            self._current_instance.on_vision_frame(frame)
        except Exception as e:
            logger.exception(f"Plugin {self._current_id} raised in on_vision_frame: {e}")
            self.unload({"crash": True, "where": "on_vision_frame", "error": str(e)})
            return
```

After the `try / except` block, BEFORE the `elapsed_ms = ...` line, insert:

```python
        # Auto-end when plugin signals completion via render_state phase==done
        if self._current_instance is not None:
            try:
                state = self._current_instance.render_state()
                if isinstance(state, dict) and state.get("phase") == "done":
                    summary_fn = getattr(self._current_instance, "completion_summary", None)
                    summary = summary_fn() if callable(summary_fn) else {"completed": True}
                    self.unload(summary)
                    return
            except Exception as e:
                logger.warning(f"render_state check failed: {e}")
```

- [ ] **Step 2: Verify tests still pass**

```bash
.venv/bin/python -m pytest --tb=short
```
Expected: 50 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/services/experience_manager.py
git commit -m "$(cat <<'EOF'
feat(p3): ExperienceManager auto-unload on phase=done

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 16: Final verification — full test suite + smoke test

- [ ] **Step 1: Run full test suite + lint + types**

```bash
.venv/bin/python -m pytest --tb=short -v
source .venv/bin/activate && ruff check && mypy src/
```
Expected: 50 tests PASS. Ruff/mypy clean.

- [ ] **Step 2: Manual smoke test with real webcam**

Run:
```bash
.venv/bin/python -m neo_makervigate
```

Verify:
1. App opens window, Splash → Hub (3 cards).
2. Click "Vẫy Chào Dế" card → enter game.
3. Intro overlay "Vẫy tay chào đàn dế!" visible ~2s.
4. PLAYING phase: countdown visible top-right.
5. Wave hand left↔right in front of webcam → 🦗 appears at wrist, flies up.
6. Wave rapidly 3 times → flock of 6 appear, score multiplier shows "×1.5".
7. Hand landmark overlay (green dots + lines) tracks hand.
8. Wait 60s (or restart and adjust PLAYING_DURATION temporarily) → RESULT overlay shows score + crickets flown.
9. After 3s in RESULT, app auto-returns to Hub.
10. Repeat: click exp01 again → no crash, FPS still smooth.

If FPS drops below 30, check `app.visionFps` in logs or add temporary `Text` to QML to show it.

- [ ] **Step 3: Update PHASES.md**

In `DOC/PHASES.md`, find the P3 section header:

```markdown
## P3 — exp01 Wave Cricket (tuần 4)
```

Replace with:

```markdown
## P3 — exp01 Wave Cricket (tuần 4) ✅ DONE
```

And add a brief "Achievement" note after the section header:

```markdown
**Achievement (date):** GestureDetector WAVE algo + WaveCricketExperience (3-phase state machine, Cricket physics, flock bonus, scoring) + AppController render-state polling + QML game UI (camera mirror, bamboo, cricket sprites, hand landmark overlay, HUD, intro/result overlays, procedural WAV audio).
```

- [ ] **Step 4: Commit final**

```bash
git add DOC/PHASES.md
git commit -m "$(cat <<'EOF'
docs(p3): mark Phase 3 done in PHASES.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 5: Update auto-memory project status**

Edit `/Users/tuanln/.claude/projects/-Users-tuanln/memory/project_neomakervigate_status.md`:

Find the line:

```markdown
- **P3 exp01 Wave Cricket**: ...
```

Replace with:

```markdown
- **P3 exp01 Wave Cricket ✅ DONE** (date, commit `<hash>`): GestureDetector WAVE (zero-crossing wrist X, 8 tests) + WaveCricketExperience full gameplay (Phase state machine INTRO→PLAYING→RESULT→DONE, Cricket dataclass + physics, flock bonus on 3 rapid waves, scoring with multiplier ×1.5) + AppController.experienceState QTimer 30Hz + QML game UI (camera mirror, bamboo, cricket sprites, hand landmark Canvas overlay, HUD, intro/result overlays, procedural WAV audio). 50/50 tests, ruff/mypy strict OK, smoke test webcam thật chạy mượt.
- **P4 Pose + exp03 Yoga Robot**: thêm Pose module + cosine similarity scoring + 5 tư thế
```

(Memory is not git-tracked — no commit needed for this file.)

---

## Self-Review Summary

**Spec coverage check:**
- §1 Architecture overview → Tasks 4, 11 (wire detector + AppController poll). ✓
- §2 Game state machine → Tasks 5, 6 (phase enum + transitions). ✓
- §3 Cricket entity + physics → Tasks 5, 8 (dataclass + step). ✓
- §4 GestureDetector algorithm → Tasks 1, 2, 3 (full algo + edge cases). ✓
- §5 Data flow Python→QML → Task 11 (AppController experienceState). ✓
- §6 File layout → All tasks together produce listed files. ✓
- §7 Testing strategy → Tasks 1-3, 5-10, 11 cover the 24 planned tests. ✓
- §8 Exit criteria → Task 16 smoke test verifies FPS + independence + leak. ✓
- §9 Risk register → WAV procedural ✓ (Task 12), QtMultimedia preload partially addressed (SoundEffect auto-preloads). FPS fallback documented in plan, no separate task.
- §10 Out of scope → Respected: only WAVE, only hands[0], emoji sprites.

**Type consistency:**
- `Phase` enum used consistently as `Phase.INTRO.value` → "intro" string in QML.
- `Cricket` dataclass fields: id/x/y/vx/vy/spawned_at/alive — same in tests, logic, render_state.
- `experienceState` dict keys match spec §5 schema exactly.
- `GestureDetector.feed(frame) → list[str]` and `reset() → None` consistent across tasks.

**Placeholders scan:** None found.

**Plan ends with:** Working P3 — full gameplay + tests + commits.
