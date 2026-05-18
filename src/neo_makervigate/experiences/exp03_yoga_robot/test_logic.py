"""Tests cho YogaRobotExperience (Face Yoga) — gameplay logic độc lập."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from typing import Any, cast  # noqa: F401  -- re-used in T7+ detector tests

import pytest

from neo_makervigate.core.models import Landmark, VisionFrame
from neo_makervigate.experiences.exp03_yoga_robot.logic import (
    Phase,
    YogaRobotExperience,
)
from neo_makervigate.utils import face_math as fm


class _FakeClock:
    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def _make_face_frame(scenario: str = "neutral", t: float = 0.0) -> VisionFrame:
    """Synthesize 468-landmark face for various scenarios."""
    L = [Landmark(x=0.5, y=0.5) for _ in range(468)]

    # Anchor landmarks
    L[fm.LEFT_TEMPLE] = Landmark(x=0.30, y=0.50)
    L[fm.RIGHT_TEMPLE] = Landmark(x=0.70, y=0.50)
    L[fm.NOSE_TIP] = Landmark(x=0.50, y=0.55)
    L[fm.CHIN] = Landmark(x=0.50, y=0.85)

    if scenario == "neutral":
        L[fm.LIP_TOP] = Landmark(x=0.50, y=0.62)
        L[fm.LIP_BOTTOM] = Landmark(x=0.50, y=0.63)
        L[fm.LIP_LEFT] = Landmark(x=0.46, y=0.625)
        L[fm.LIP_RIGHT] = Landmark(x=0.54, y=0.625)
        L[fm.LEFT_EYE_TOP] = Landmark(x=0.40, y=0.48)
        L[fm.LEFT_EYE_BOTTOM] = Landmark(x=0.40, y=0.51)
        L[fm.LEFT_EYE_INNER] = Landmark(x=0.43, y=0.495)
        L[fm.LEFT_EYE_OUTER] = Landmark(x=0.35, y=0.495)
        L[fm.RIGHT_EYE_TOP] = Landmark(x=0.60, y=0.48)
        L[fm.RIGHT_EYE_BOTTOM] = Landmark(x=0.60, y=0.51)
        L[fm.RIGHT_EYE_INNER] = Landmark(x=0.57, y=0.495)
        L[fm.RIGHT_EYE_OUTER] = Landmark(x=0.65, y=0.495)
        L[fm.LEFT_BROW_INNER] = Landmark(x=0.45, y=0.46)
        L[fm.RIGHT_BROW_INNER] = Landmark(x=0.55, y=0.46)

    elif scenario == "smile":
        L[fm.LIP_TOP] = Landmark(x=0.50, y=0.62)
        L[fm.LIP_BOTTOM] = Landmark(x=0.50, y=0.625)
        L[fm.LIP_LEFT] = Landmark(x=0.40, y=0.625)
        L[fm.LIP_RIGHT] = Landmark(x=0.60, y=0.625)
        L[fm.LEFT_EYE_TOP] = Landmark(x=0.40, y=0.48)
        L[fm.LEFT_EYE_BOTTOM] = Landmark(x=0.40, y=0.51)
        L[fm.LEFT_EYE_INNER] = Landmark(x=0.43, y=0.495)
        L[fm.LEFT_EYE_OUTER] = Landmark(x=0.35, y=0.495)
        L[fm.RIGHT_EYE_TOP] = Landmark(x=0.60, y=0.48)
        L[fm.RIGHT_EYE_BOTTOM] = Landmark(x=0.60, y=0.51)
        L[fm.RIGHT_EYE_INNER] = Landmark(x=0.57, y=0.495)
        L[fm.RIGHT_EYE_OUTER] = Landmark(x=0.65, y=0.495)
        L[fm.LEFT_BROW_INNER] = Landmark(x=0.45, y=0.46)
        L[fm.RIGHT_BROW_INNER] = Landmark(x=0.55, y=0.46)

    elif scenario == "mouth_open":
        L[fm.LIP_TOP] = Landmark(x=0.50, y=0.55)
        L[fm.LIP_BOTTOM] = Landmark(x=0.50, y=0.70)
        L[fm.LIP_LEFT] = Landmark(x=0.46, y=0.625)
        L[fm.LIP_RIGHT] = Landmark(x=0.54, y=0.625)
        L[fm.LEFT_EYE_TOP] = Landmark(x=0.40, y=0.48)
        L[fm.LEFT_EYE_BOTTOM] = Landmark(x=0.40, y=0.51)
        L[fm.LEFT_EYE_INNER] = Landmark(x=0.43, y=0.495)
        L[fm.LEFT_EYE_OUTER] = Landmark(x=0.35, y=0.495)
        L[fm.RIGHT_EYE_TOP] = Landmark(x=0.60, y=0.48)
        L[fm.RIGHT_EYE_BOTTOM] = Landmark(x=0.60, y=0.51)
        L[fm.RIGHT_EYE_INNER] = Landmark(x=0.57, y=0.495)
        L[fm.RIGHT_EYE_OUTER] = Landmark(x=0.65, y=0.495)
        L[fm.LEFT_BROW_INNER] = Landmark(x=0.45, y=0.46)
        L[fm.RIGHT_BROW_INNER] = Landmark(x=0.55, y=0.46)

    elif scenario == "wink_left":
        L[fm.LIP_TOP] = Landmark(x=0.50, y=0.62)
        L[fm.LIP_BOTTOM] = Landmark(x=0.50, y=0.63)
        L[fm.LIP_LEFT] = Landmark(x=0.46, y=0.625)
        L[fm.LIP_RIGHT] = Landmark(x=0.54, y=0.625)
        # Left eye closed
        L[fm.LEFT_EYE_TOP] = Landmark(x=0.40, y=0.495)
        L[fm.LEFT_EYE_BOTTOM] = Landmark(x=0.40, y=0.500)
        L[fm.LEFT_EYE_INNER] = Landmark(x=0.43, y=0.497)
        L[fm.LEFT_EYE_OUTER] = Landmark(x=0.35, y=0.497)
        # Right eye open
        L[fm.RIGHT_EYE_TOP] = Landmark(x=0.60, y=0.48)
        L[fm.RIGHT_EYE_BOTTOM] = Landmark(x=0.60, y=0.51)
        L[fm.RIGHT_EYE_INNER] = Landmark(x=0.57, y=0.495)
        L[fm.RIGHT_EYE_OUTER] = Landmark(x=0.65, y=0.495)
        L[fm.LEFT_BROW_INNER] = Landmark(x=0.45, y=0.46)
        L[fm.RIGHT_BROW_INNER] = Landmark(x=0.55, y=0.46)

    elif scenario == "brow_up":
        L[fm.LIP_TOP] = Landmark(x=0.50, y=0.62)
        L[fm.LIP_BOTTOM] = Landmark(x=0.50, y=0.63)
        L[fm.LIP_LEFT] = Landmark(x=0.46, y=0.625)
        L[fm.LIP_RIGHT] = Landmark(x=0.54, y=0.625)
        L[fm.LEFT_EYE_TOP] = Landmark(x=0.40, y=0.48)
        L[fm.LEFT_EYE_BOTTOM] = Landmark(x=0.40, y=0.51)
        L[fm.LEFT_EYE_INNER] = Landmark(x=0.43, y=0.495)
        L[fm.LEFT_EYE_OUTER] = Landmark(x=0.35, y=0.495)
        L[fm.RIGHT_EYE_TOP] = Landmark(x=0.60, y=0.48)
        L[fm.RIGHT_EYE_BOTTOM] = Landmark(x=0.60, y=0.51)
        L[fm.RIGHT_EYE_INNER] = Landmark(x=0.57, y=0.495)
        L[fm.RIGHT_EYE_OUTER] = Landmark(x=0.65, y=0.495)
        L[fm.LEFT_BROW_INNER] = Landmark(x=0.45, y=0.43)
        L[fm.RIGHT_BROW_INNER] = Landmark(x=0.55, y=0.43)

    elif scenario == "head_left":
        L[fm.NOSE_TIP] = Landmark(x=0.35, y=0.55)
        L[fm.LIP_TOP] = Landmark(x=0.35, y=0.62)
        L[fm.LIP_BOTTOM] = Landmark(x=0.35, y=0.63)
        L[fm.LIP_LEFT] = Landmark(x=0.31, y=0.625)
        L[fm.LIP_RIGHT] = Landmark(x=0.39, y=0.625)

    elif scenario == "head_right":
        L[fm.NOSE_TIP] = Landmark(x=0.65, y=0.55)
        L[fm.LIP_TOP] = Landmark(x=0.65, y=0.62)
        L[fm.LIP_BOTTOM] = Landmark(x=0.65, y=0.63)
        L[fm.LIP_LEFT] = Landmark(x=0.61, y=0.625)
        L[fm.LIP_RIGHT] = Landmark(x=0.69, y=0.625)

    vf = VisionFrame(timestamp=datetime(2026, 1, 1), width=1280, height=720)
    vf.face = L
    return vf


def _make_empty_frame() -> VisionFrame:
    return VisionFrame(timestamp=datetime(2026, 1, 1), width=1280, height=720)


@pytest.fixture
def exp_with_clock(qapp: object) -> Generator[tuple[YogaRobotExperience, _FakeClock], None, None]:  # qapp ensures QObject / Qt event loop is initialized
    clock = _FakeClock(0.0)
    exp = YogaRobotExperience(clock=clock)
    exp.on_enter()
    yield exp, clock
    exp.on_exit()


def test_meta_face_module() -> None:
    meta = YogaRobotExperience.meta
    assert meta.id == "exp03_yoga_robot"
    assert "face" in meta.vision_modules
    assert "pose" not in meta.vision_modules


def test_initial_phase_is_intro(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, _ = exp_with_clock
    state = exp.render_state()
    assert state["phase"] == Phase.INTRO.value


def test_poses_toml_loaded_5_face_poses(
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
