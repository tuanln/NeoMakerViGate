"""Tests cho utils/landmark_math — joint angle + pose similarity scoring."""

from __future__ import annotations

import math

from neo_makervigate.core.models import Landmark
from neo_makervigate.utils.landmark_math import (
    compute_joint_angle,
    extract_pose_angles,
)


def test_compute_joint_angle_straight_line_returns_180() -> None:
    # a-b-c collinear → 180°
    a = Landmark(x=0.0, y=0.0)
    b = Landmark(x=1.0, y=0.0)
    c = Landmark(x=2.0, y=0.0)
    assert abs(compute_joint_angle(a, b, c) - 180.0) < 0.5


def test_compute_joint_angle_right_angle_returns_90() -> None:
    # a above b, c to right of b → 90°
    a = Landmark(x=0.0, y=0.0)
    b = Landmark(x=0.0, y=1.0)
    c = Landmark(x=1.0, y=1.0)
    assert abs(compute_joint_angle(a, b, c) - 90.0) < 0.5


def test_compute_joint_angle_acute_45() -> None:
    # 135° angle case
    a = Landmark(x=0.0, y=0.0)
    b = Landmark(x=1.0, y=0.0)
    c = Landmark(x=1.0 + math.cos(math.radians(45)), y=math.sin(math.radians(45)))
    # angle at b between ba=(-1,0) and bc=(cos45, sin45) → 180-45 = 135
    expected = 180 - 45
    assert abs(compute_joint_angle(a, b, c) - expected) < 0.5


def test_compute_joint_angle_degenerate_zero_length_returns_180() -> None:
    a = Landmark(x=0.0, y=0.0)
    b = Landmark(x=1.0, y=0.0)
    c = Landmark(x=1.0, y=0.0)
    angle = compute_joint_angle(a, b, c)
    # Accept 180 (chosen convention) or 0 (alternate convention); main: no exception
    assert angle == 180.0 or angle == 0.0


def test_extract_pose_angles_returns_8_joint_keys() -> None:
    landmarks = [Landmark(x=0.5, y=0.5) for _ in range(33)]
    angles = extract_pose_angles(landmarks)
    expected_keys = {
        "left_shoulder", "right_shoulder",
        "left_elbow", "right_elbow",
        "left_hip", "right_hip",
        "left_knee", "right_knee",
    }
    assert set(angles.keys()) == expected_keys


def test_extract_pose_angles_t_pose_synth() -> None:
    """Synthesize T-pose landmarks → verify extracted angles."""
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

    angles = extract_pose_angles(L)
    assert 70 < angles["left_shoulder"] < 110, (
        f"left_shoulder expected ~90, got {angles['left_shoulder']}"
    )
    assert 70 < angles["right_shoulder"] < 110
    assert angles["left_elbow"] > 160
    assert angles["right_elbow"] > 160
    assert angles["left_hip"] > 160
    assert angles["right_hip"] > 160
    assert angles["left_knee"] > 160
    assert angles["right_knee"] > 160


def test_pose_similarity_score_perfect_match_returns_100() -> None:
    from neo_makervigate.utils.landmark_math import pose_similarity_score

    current = {
        "left_shoulder": 90.0, "right_shoulder": 90.0,
        "left_elbow": 180.0, "right_elbow": 180.0,
    }
    target = dict(current)
    tolerance = {"shoulder": 20, "elbow": 15, "hip": 15, "knee": 30}
    assert pose_similarity_score(current, target, tolerance) == 100.0


def test_pose_similarity_score_off_by_tolerance_returns_around_50() -> None:
    from neo_makervigate.utils.landmark_math import pose_similarity_score

    # 1 joint off by exactly tolerance → score for that joint = 100 - 100 * tol/(2*tol) = 50
    current = {"left_shoulder": 110.0}  # off by 20
    target = {"left_shoulder": 90.0}
    tolerance = {"shoulder": 20, "elbow": 15, "hip": 15, "knee": 30}
    score = pose_similarity_score(current, target, tolerance)
    assert 45 <= score <= 55, f"expected ~50, got {score}"


def test_pose_similarity_score_off_by_2tolerance_returns_0() -> None:
    from neo_makervigate.utils.landmark_math import pose_similarity_score

    # off by 2x tolerance → 100 - 100 * 2tol/(2tol) = 0
    current = {"left_shoulder": 130.0}  # off by 40 from 90
    target = {"left_shoulder": 90.0}
    tolerance = {"shoulder": 20, "elbow": 15, "hip": 15, "knee": 30}
    score = pose_similarity_score(current, target, tolerance)
    assert score == 0.0


def test_pose_similarity_score_iterates_only_target_keys() -> None:
    """Target có 6 keys (no knee), current có 8 keys → chỉ score 6 keys của target."""
    from neo_makervigate.utils.landmark_math import pose_similarity_score

    current = {
        "left_shoulder": 90.0, "right_shoulder": 90.0,
        "left_elbow": 180.0, "right_elbow": 180.0,
        "left_hip": 180.0, "right_hip": 180.0,
        "left_knee": 90.0, "right_knee": 90.0,  # extra — không có trong target
    }
    target = {
        "left_shoulder": 90.0, "right_shoulder": 90.0,
        "left_elbow": 180.0, "right_elbow": 180.0,
        "left_hip": 180.0, "right_hip": 180.0,
    }
    tolerance = {"shoulder": 20, "elbow": 15, "hip": 15, "knee": 30}
    assert pose_similarity_score(current, target, tolerance) == 100.0
