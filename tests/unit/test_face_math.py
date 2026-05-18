"""Tests cho utils/face_math — MediaPipe Face Mesh helpers."""

from __future__ import annotations

from neo_makervigate.core.models import Landmark
from neo_makervigate.utils.face_math import (
    LEFT_BROW_INNER,
    LEFT_EYE_BOTTOM,
    LEFT_EYE_INNER,
    LEFT_EYE_OUTER,
    LEFT_EYE_TOP,
    LEFT_TEMPLE,
    LIP_BOTTOM,
    LIP_LEFT,
    LIP_RIGHT,
    LIP_TOP,
    NOSE_TIP,
    RIGHT_BROW_INNER,
    RIGHT_EYE_BOTTOM,
    RIGHT_EYE_INNER,
    RIGHT_EYE_OUTER,
    RIGHT_EYE_TOP,
    RIGHT_TEMPLE,
    brow_raised_ratio,
    eye_aspect_ratio,
    head_yaw,
    mouth_aspect_ratio,
    mouth_width_ratio,
)


def _empty_face_landmarks(n: int = 468) -> list[Landmark]:
    """Empty face — all landmarks at center."""
    return [Landmark(x=0.5, y=0.5) for _ in range(n)]


def _set_lm(landmarks: list[Landmark], idx: int, x: float, y: float) -> None:
    landmarks[idx] = Landmark(x=x, y=y)


def test_mar_open_mouth_high() -> None:
    L = _empty_face_landmarks()
    _set_lm(L, LIP_TOP, 0.5, 0.55)
    _set_lm(L, LIP_BOTTOM, 0.5, 0.70)
    _set_lm(L, LIP_LEFT, 0.46, 0.625)
    _set_lm(L, LIP_RIGHT, 0.54, 0.625)
    mar = mouth_aspect_ratio(L)
    assert mar > 1.5


def test_mar_closed_mouth_low() -> None:
    L = _empty_face_landmarks()
    _set_lm(L, LIP_TOP, 0.5, 0.62)
    _set_lm(L, LIP_BOTTOM, 0.5, 0.63)
    _set_lm(L, LIP_LEFT, 0.46, 0.625)
    _set_lm(L, LIP_RIGHT, 0.54, 0.625)
    mar = mouth_aspect_ratio(L)
    assert mar < 0.2


def test_mouth_width_ratio_smile() -> None:
    L = _empty_face_landmarks()
    _set_lm(L, LIP_LEFT, 0.40, 0.625)
    _set_lm(L, LIP_RIGHT, 0.60, 0.625)
    _set_lm(L, LEFT_TEMPLE, 0.30, 0.50)
    _set_lm(L, RIGHT_TEMPLE, 0.70, 0.50)
    mwr = mouth_width_ratio(L)
    assert 0.45 < mwr < 0.55


def test_mouth_width_ratio_neutral() -> None:
    L = _empty_face_landmarks()
    _set_lm(L, LIP_LEFT, 0.46, 0.625)
    _set_lm(L, LIP_RIGHT, 0.54, 0.625)
    _set_lm(L, LEFT_TEMPLE, 0.30, 0.50)
    _set_lm(L, RIGHT_TEMPLE, 0.70, 0.50)
    mwr = mouth_width_ratio(L)
    assert mwr < 0.30


def test_ear_open_eye() -> None:
    L = _empty_face_landmarks()
    _set_lm(L, LEFT_EYE_TOP, 0.40, 0.48)
    _set_lm(L, LEFT_EYE_BOTTOM, 0.40, 0.51)
    _set_lm(L, LEFT_EYE_INNER, 0.43, 0.495)
    _set_lm(L, LEFT_EYE_OUTER, 0.35, 0.495)
    ear = eye_aspect_ratio(L, side="left")
    assert 0.30 < ear < 0.45


def test_ear_closed_eye() -> None:
    L = _empty_face_landmarks()
    _set_lm(L, RIGHT_EYE_TOP, 0.60, 0.495)
    _set_lm(L, RIGHT_EYE_BOTTOM, 0.60, 0.500)
    _set_lm(L, RIGHT_EYE_INNER, 0.57, 0.497)
    _set_lm(L, RIGHT_EYE_OUTER, 0.65, 0.497)
    ear = eye_aspect_ratio(L, side="right")
    assert ear < 0.10


def test_brow_raised_ratio_normal() -> None:
    L = _empty_face_landmarks()
    _set_lm(L, LEFT_BROW_INNER, 0.45, 0.46)
    _set_lm(L, LEFT_EYE_TOP, 0.45, 0.48)
    _set_lm(L, RIGHT_BROW_INNER, 0.55, 0.46)
    _set_lm(L, RIGHT_EYE_TOP, 0.55, 0.48)
    _set_lm(L, NOSE_TIP, 0.50, 0.55)
    ratio = brow_raised_ratio(L)
    assert 0.03 < ratio < 0.09


def test_brow_raised_ratio_raised() -> None:
    L = _empty_face_landmarks()
    _set_lm(L, LEFT_BROW_INNER, 0.45, 0.43)
    _set_lm(L, LEFT_EYE_TOP, 0.45, 0.48)
    _set_lm(L, RIGHT_BROW_INNER, 0.55, 0.43)
    _set_lm(L, RIGHT_EYE_TOP, 0.55, 0.48)
    _set_lm(L, NOSE_TIP, 0.50, 0.55)
    ratio = brow_raised_ratio(L)
    assert ratio > 0.10


def test_head_yaw_facing_forward_zero() -> None:
    L = _empty_face_landmarks()
    _set_lm(L, NOSE_TIP, 0.50, 0.55)
    _set_lm(L, LEFT_TEMPLE, 0.30, 0.50)
    _set_lm(L, RIGHT_TEMPLE, 0.70, 0.50)
    yaw = head_yaw(L)
    assert abs(yaw) < 0.05


def test_head_yaw_facing_left() -> None:
    L = _empty_face_landmarks()
    _set_lm(L, NOSE_TIP, 0.35, 0.55)
    _set_lm(L, LEFT_TEMPLE, 0.25, 0.50)
    _set_lm(L, RIGHT_TEMPLE, 0.70, 0.50)
    yaw = head_yaw(L)
    assert yaw > 0.10


def test_head_yaw_facing_right() -> None:
    L = _empty_face_landmarks()
    _set_lm(L, NOSE_TIP, 0.65, 0.55)
    _set_lm(L, LEFT_TEMPLE, 0.30, 0.50)
    _set_lm(L, RIGHT_TEMPLE, 0.75, 0.50)
    yaw = head_yaw(L)
    assert yaw < -0.10
