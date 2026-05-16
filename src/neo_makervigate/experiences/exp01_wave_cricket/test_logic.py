"""Tests cho WaveCricketExperience — gameplay logic độc lập, không Qt/QML."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

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


def test_intro_waves_do_not_carry_into_playing() -> None:
    """Waves during INTRO must not contribute to flock detection in PLAYING."""
    clock = _FakeClock(0.0)
    exp = WaveCricketExperience(clock=clock)
    exp.on_enter()
    # 3 rapid waves during INTRO
    for offset in (0.3, 0.6, 0.9):
        clock.t = offset
        exp.on_gesture("WAVE")
    # Advance to PLAYING
    clock.advance(2.0 - 0.9 + 0.2)  # to t=2.2s
    exp.on_vision_frame(_make_frame())  # triggers phase transition in _step_phase
    assert exp.render_state()["phase"] == Phase.PLAYING.value
    # First WAVE in PLAYING — should spawn ONE, not a flock
    exp.on_gesture("WAVE")
    state = exp.render_state()
    crickets = cast(list[object], state["crickets"])
    assert len(crickets) == 1, f"Expected 1 cricket, got {len(crickets)} — flock pre-armed from INTRO"
    assert state["flock_bonus_active"] is False


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
