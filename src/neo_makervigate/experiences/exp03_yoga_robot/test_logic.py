"""Tests cho YogaRobotExperience — gameplay logic độc lập, không Qt/QML."""

from __future__ import annotations

from datetime import datetime
from typing import cast

import pytest

from neo_makervigate.core.models import Landmark, VisionFrame
from neo_makervigate.experiences.exp03_yoga_robot.logic import (
    Phase,
    YogaRobotExperience,
)


class _FakeClock:
    """Fake clock thay time.perf_counter để test phase transitions."""

    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def _make_pose_frame(angles: dict[str, float] | None = None) -> VisionFrame:
    """Sinh VisionFrame với 33 pose landmarks (T-pose synth mặc định)."""
    L = [Landmark(x=0.5, y=0.5) for _ in range(33)]
    L[11] = Landmark(x=0.4, y=0.4)
    L[12] = Landmark(x=0.6, y=0.4)
    L[13] = Landmark(x=0.25, y=0.4)
    L[14] = Landmark(x=0.75, y=0.4)
    L[15] = Landmark(x=0.1, y=0.4)
    L[16] = Landmark(x=0.9, y=0.4)
    L[23] = Landmark(x=0.42, y=0.6)
    L[24] = Landmark(x=0.58, y=0.6)
    L[25] = Landmark(x=0.42, y=0.78)
    L[26] = Landmark(x=0.58, y=0.78)
    L[27] = Landmark(x=0.42, y=0.95)
    L[28] = Landmark(x=0.58, y=0.95)
    vf = VisionFrame(timestamp=datetime(2026, 1, 1), width=1280, height=720)
    vf.pose = L
    return vf


def _make_empty_frame() -> VisionFrame:
    """Frame không có pose detection."""
    return VisionFrame(timestamp=datetime(2026, 1, 1), width=1280, height=720)


@pytest.fixture
def exp_with_clock() -> tuple[YogaRobotExperience, _FakeClock]:
    clock = _FakeClock(0.0)
    exp = YogaRobotExperience(clock=clock)
    exp.on_enter()
    return exp, clock


def test_meta_correct() -> None:
    meta = YogaRobotExperience.meta
    assert meta.id == "exp03_yoga_robot"
    assert "pose" in meta.vision_modules
    assert meta.age_min == 5


def test_initial_phase_is_intro(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, _ = exp_with_clock
    state = exp.render_state()
    assert state["phase"] == Phase.INTRO.value


def test_poses_toml_loaded_5_poses(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, _ = exp_with_clock
    state = exp.render_state()
    assert state["pose_count"] == 5


def test_intro_transitions_to_posing_after_2s(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    state = exp.render_state()
    assert state["phase"] == Phase.INTRO.value
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())
    assert exp.render_state()["phase"] == Phase.POSING.value


def test_posing_starts_at_pose_index_0(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())
    state = exp.render_state()
    assert state["pose_index"] == 0


def test_match_increments_hold_progress(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """T-pose synth → score >= MATCH_THRESHOLD → hold_progress tăng."""
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING
    # Frame 1 (delta=0): start hold
    exp.on_vision_frame(_make_pose_frame())
    state1 = exp.render_state()
    # Advance 0.5s, frame 2
    clock.advance(0.5)
    exp.on_vision_frame(_make_pose_frame())
    state2 = exp.render_state()
    # hold_progress phải tăng
    assert cast(float, state2["hold_progress"]) > cast(float, state1["hold_progress"])
    # Score live phải >= threshold
    assert cast(int, state2["score"]) >= 65


def test_no_match_keeps_hold_at_zero(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """Frame có pose nhưng angles sai → score < threshold → hold = 0."""
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING (T_POSE target)

    # Construct frame có pose nhưng "thõng tay xuống" (sai T-pose):
    L = [Landmark(x=0.5, y=0.5) for _ in range(33)]
    L[11] = Landmark(x=0.4, y=0.4)
    L[12] = Landmark(x=0.6, y=0.4)
    L[13] = Landmark(x=0.4, y=0.55)  # elbow xuống dưới (sai T)
    L[14] = Landmark(x=0.6, y=0.55)
    L[15] = Landmark(x=0.4, y=0.7)
    L[16] = Landmark(x=0.6, y=0.7)
    L[23] = Landmark(x=0.42, y=0.6)
    L[24] = Landmark(x=0.58, y=0.6)
    L[25] = Landmark(x=0.42, y=0.78)
    L[26] = Landmark(x=0.58, y=0.78)
    L[27] = Landmark(x=0.42, y=0.95)
    L[28] = Landmark(x=0.58, y=0.95)
    vf = VisionFrame(timestamp=datetime(2026, 1, 1), width=1280, height=720)
    vf.pose = L

    clock.advance(0.5)
    exp.on_vision_frame(vf)
    state = exp.render_state()
    assert cast(int, state["score"]) < 65, f"expected score < 65, got {state['score']}"
    assert cast(float, state["hold_progress"]) == 0.0


def test_match_lost_resets_hold_after_gap_tolerance(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """Match → lost > MATCH_GAP_TOLERANCE → hold reset."""
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING

    # Match
    exp.on_vision_frame(_make_pose_frame())
    clock.advance(0.5)
    exp.on_vision_frame(_make_pose_frame())
    state_matching = exp.render_state()
    assert cast(float, state_matching["hold_progress"]) > 0

    # Gap > 0.3s không match (empty frame)
    clock.advance(0.5)
    exp.on_vision_frame(_make_empty_frame())
    clock.advance(0.1)
    # Frame có pose lại nhưng pose sai → score < threshold
    L_bad = [Landmark(x=0.5, y=0.5) for _ in range(33)]
    L_bad[11] = Landmark(x=0.4, y=0.4)
    L_bad[12] = Landmark(x=0.6, y=0.4)
    L_bad[13] = Landmark(x=0.4, y=0.6)
    L_bad[14] = Landmark(x=0.6, y=0.6)
    L_bad[23] = Landmark(x=0.42, y=0.6)
    L_bad[24] = Landmark(x=0.58, y=0.6)
    vf_bad = VisionFrame(timestamp=datetime(2026, 1, 1), width=1280, height=720)
    vf_bad.pose = L_bad
    exp.on_vision_frame(vf_bad)
    state_reset = exp.render_state()
    assert cast(float, state_reset["hold_progress"]) == 0.0
