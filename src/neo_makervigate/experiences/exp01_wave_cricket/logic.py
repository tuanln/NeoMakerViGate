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
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from neo_makervigate.core.models import ExperienceMeta, VisionFrame
from neo_makervigate.experiences.experience_base import BaseExperience

_QML_PATH = (Path(__file__).parent / "ui.qml").as_posix()


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


class Phase(StrEnum):
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
            # Don't carry pre-game waves into play
            self._wave_timestamps.clear()
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
