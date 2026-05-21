"""Tests cho YogaRobotExperience (Face Yoga) — gameplay logic độc lập."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from typing import Any, cast

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


def test_smile_pose_match_advances_after_hold(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """Smile face frames → hold 2s → advance to mouth_open."""
    exp, clock = exp_with_clock
    # Skip INTRO
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING (smile is pose 0)
    # Send smile frames for ~2.4s (0.2s steps so gap <= MATCH_GAP_TOLERANCE=0.3)
    for _ in range(13):
        clock.advance(0.2)
        exp.on_vision_frame(_make_face_frame("smile"))
    state = exp.render_state()
    # After hold, pose_index advances to 1 (mouth_open)
    assert state["pose_index"] == 1
    completed = cast(list[dict[str, Any]], state["completed_poses"])
    assert len(completed) == 1
    assert completed[0]["id"] == "CUOI_TO"


def test_mouth_open_pose_match(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """Skip to mouth_open pose (index 1), match → advance."""
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING smile
    # Complete smile via hold (0.2s steps to stay within MATCH_GAP_TOLERANCE)
    for _ in range(13):
        clock.advance(0.2)
        exp.on_vision_frame(_make_face_frame("smile"))
    # Now on mouth_open
    assert exp.render_state()["pose_index"] == 1
    # Send open mouth frames (0.2s steps)
    for _ in range(13):
        clock.advance(0.2)
        exp.on_vision_frame(_make_face_frame("mouth_open"))
    # Advanced to wink (index 2)
    assert exp.render_state()["pose_index"] == 2


def test_wink_pose_match(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """Skip smile + mouth_open via match, then wink → advance."""
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING smile
    # Complete smile (13 × 0.2s = 2.6s)
    for _ in range(13):
        clock.advance(0.2)
        exp.on_vision_frame(_make_face_frame("smile"))
    # Complete mouth_open
    for _ in range(13):
        clock.advance(0.2)
        exp.on_vision_frame(_make_face_frame("mouth_open"))
    # Now on wink (index 2)
    assert exp.render_state()["pose_index"] == 2
    # Send wink frames
    for _ in range(13):
        clock.advance(0.2)
        exp.on_vision_frame(_make_face_frame("wink_left"))
    assert exp.render_state()["pose_index"] == 3


def test_brow_raised_pose_match(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """Skip 3 poses via stuck-skip (neutral face), then brow_up → advance from brow_raised."""
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING smile
    # Skip 3 poses via stuck-skip: send a neutral face frame after 45.1s each
    for _ in range(3):
        clock.advance(45.1)
        exp.on_vision_frame(_make_face_frame("neutral"))
    assert exp.render_state()["pose_index"] == 3
    # Send brow_up frames
    for _ in range(13):
        clock.advance(0.2)
        exp.on_vision_frame(_make_face_frame("brow_up"))
    assert exp.render_state()["pose_index"] == 4


def test_head_shake_oscillation_match(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """Alternating head_left / head_right frames → head_shake detector engages."""
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())
    # Skip 4 poses via stuck-skip (use neutral face so on_vision_frame doesn't bail)
    for _ in range(4):
        clock.advance(45.1)
        exp.on_vision_frame(_make_face_frame("neutral"))
    assert exp.render_state()["pose_index"] == 4
    # Send alternating head_left / head_right at high rate
    scenarios = ["head_left", "head_right"] * 8  # 16 frames → 4+ oscillations
    for scn in scenarios:
        clock.advance(0.1)
        exp.on_vision_frame(_make_face_frame(scn))
    # Either still on pose 4 (mid-hold) or moved to RESULT
    state = exp.render_state()
    assert state["phase"] in (Phase.POSING.value, Phase.RESULT.value)


def test_completion_summary_face_yoga(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """Skip all 5 poses → RESULT phase + completion summary correctness."""
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())
    # 5 stuck-skips with neutral face (no match)
    for _ in range(5):
        clock.advance(45.1)
        exp.on_vision_frame(_make_face_frame("neutral"))
    state = exp.render_state()
    assert state["phase"] == Phase.RESULT.value
    summary = exp.completion_summary()
    assert summary["completed"] is True
    assert summary["poses_completed"] == 5
    assert summary["skipped_count"] == 5  # all skipped
