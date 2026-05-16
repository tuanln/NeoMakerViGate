"""Tests cho YogaRobotExperience — gameplay logic độc lập, không Qt/QML."""

from __future__ import annotations

from datetime import datetime

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
