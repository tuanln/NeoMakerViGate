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
    msg = f"Expected 1 cricket, got {len(crickets)} — flock pre-armed from INTRO"
    assert len(crickets) == 1, msg
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


def test_wave_during_intro_does_not_spawn(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    exp, _ = exp_with_clock
    exp.on_vision_frame(_make_frame(wrist_x=0.3, wrist_y=0.4))
    exp.on_gesture("WAVE")
    state: dict[str, Any] = exp.render_state()
    crickets = cast(list[object], state["crickets"])
    assert crickets == []


def test_wave_during_playing_spawns_cricket_at_wrist(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame(wrist_x=0.3, wrist_y=0.4))  # → PLAYING
    exp.on_gesture("WAVE")
    state: dict[str, Any] = exp.render_state()
    crickets = cast(list[object], state["crickets"])
    assert len(crickets) == 1
    c0 = cast(dict[str, Any], crickets[0])
    assert isinstance(c0["x"], float)
    assert isinstance(c0["y"], float)
    assert abs(c0["x"] - 0.3) < 1e-6
    assert abs(c0["y"] - 0.4) < 1e-6


def test_non_wave_gesture_ignored(
    exp_with_clock: tuple[WaveCricketExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame())
    exp.on_gesture("V_SIGN")
    exp.on_gesture("POINT")
    state: dict[str, Any] = exp.render_state()
    assert state["crickets"] == []
    assert state["score"] == 0


def test_cricket_position_updates_with_velocity() -> None:
    """Cricket bay lên do vy âm — y giảm sau khi tiến thời gian."""
    import random as _r
    clock = _FakeClock(0.0)
    exp = WaveCricketExperience(clock=clock, rng=_r.Random(42))
    exp.on_enter()
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.8))
    exp.on_gesture("WAVE")
    state_before = exp.render_state()
    before_crickets = cast(list[dict[str, Any]], state_before["crickets"])
    assert len(before_crickets) == 1
    before_y = cast(float, before_crickets[0]["y"])
    # Advance 0.5s — y giảm (vy âm)
    clock.advance(0.5)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.8))
    state_after = exp.render_state()
    after_crickets = cast(list[dict[str, Any]], state_after["crickets"])
    after_y = cast(float, after_crickets[0]["y"])
    assert after_y < before_y, "Cricket should rise (vy negative)"


def test_cricket_despawns_when_out_of_top_and_scores() -> None:
    """Cricket bay khỏi top (y < -0.1) → despawn + score tăng."""
    import random as _r
    clock = _FakeClock(0.0)
    exp = WaveCricketExperience(clock=clock, rng=_r.Random(42))
    exp.on_enter()
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.1))
    exp.on_gesture("WAVE")
    state = exp.render_state()
    crickets = cast(list[dict[str, Any]], state["crickets"])
    assert len(crickets) == 1
    # Advance đủ để cricket bay khỏi top (vy in [-0.7, -0.5], y=0.1 → ~ 0.2/0.5 = 0.4s tối thiểu).
    # Advance 2s an toàn.
    clock.advance(2.0)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.1))
    state = exp.render_state()
    crickets = cast(list[dict[str, Any]], state["crickets"])
    assert crickets == []
    score = cast(int, state["score"])
    crickets_flown = cast(int, state["crickets_flown"])
    assert crickets_flown == 1
    assert score >= 10  # base 10 (no bonus)


def test_cricket_despawns_after_max_age_without_score() -> None:
    """Cricket sống quá CRICKET_MAX_AGE (4s) → despawn nhưng không tính score."""
    clock = _FakeClock(0.0)
    # RNG zero velocity → cricket đứng yên, không bay khỏi top → trigger age despawn
    class _StaticRng:
        def uniform(self, a: float, b: float) -> float:
            return 0.0

    exp = WaveCricketExperience(clock=clock, rng=cast(Any, _StaticRng()))
    exp.on_enter()
    clock.advance(2.1)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.5))
    exp.on_gesture("WAVE")
    state = exp.render_state()
    crickets = cast(list[dict[str, Any]], state["crickets"])
    assert len(crickets) == 1
    # Advance > 4s
    clock.advance(4.5)
    exp.on_vision_frame(_make_frame(wrist_x=0.5, wrist_y=0.5))
    state = exp.render_state()
    crickets = cast(list[dict[str, Any]], state["crickets"])
    assert crickets == []
    # Despawned by age — không tính score
    score = cast(int, state["score"])
    crickets_flown = cast(int, state["crickets_flown"])
    assert score == 0
    assert crickets_flown == 0
