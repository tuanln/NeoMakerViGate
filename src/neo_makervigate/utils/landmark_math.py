"""Joint angle + pose similarity math cho exp03 Yoga Robot.

API stateless:
    compute_joint_angle(a, b, c) → góc tại b (0-180°)
    extract_pose_angles(landmarks_33) → dict 8 joint angles
    pose_similarity_score(current, target, tolerance) → 0-100

MediaPipe Pose indices được encode trực tiếp ở extract_pose_angles để giảm coupling.
"""

from __future__ import annotations

import math

from neo_makervigate.core.models import Landmark

# MediaPipe Pose landmark indices
SHOULDER_L = 11
SHOULDER_R = 12
ELBOW_L = 13
ELBOW_R = 14
WRIST_L = 15
WRIST_R = 16
HIP_L = 23
HIP_R = 24
KNEE_L = 25
KNEE_R = 26
ANKLE_L = 27
ANKLE_R = 28


def compute_joint_angle(a: Landmark, b: Landmark, c: Landmark) -> float:
    """Góc tại điểm b giữa hai đoạn ba và bc. Trả về độ (0-180).

    Degenerate (b==a hoặc b==c): trả 180 (coi như duỗi thẳng — không gập).
    """
    v1x, v1y = a.x - b.x, a.y - b.y
    v2x, v2y = c.x - b.x, c.y - b.y
    n1 = math.sqrt(v1x * v1x + v1y * v1y)
    n2 = math.sqrt(v2x * v2x + v2y * v2y)
    if n1 < 1e-9 or n2 < 1e-9:
        return 180.0
    cos_angle = (v1x * v2x + v1y * v2y) / (n1 * n2)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return math.degrees(math.acos(cos_angle))


def extract_pose_angles(landmarks: list[Landmark]) -> dict[str, float]:
    """Compute 8 joint angles từ 33 MediaPipe Pose landmarks.

    Returns dict với keys: {left,right}_{shoulder,elbow,hip,knee}.

    Definitions:
        shoulder: angle(hip, shoulder, elbow) — torso vs upper arm
        elbow: angle(shoulder, elbow, wrist) — upper arm vs forearm (180 = thẳng)
        hip: angle(shoulder, hip, knee) — torso vs thigh
        knee: angle(hip, knee, ankle) — thigh vs calf (180 = thẳng)
    """
    if len(landmarks) < 33:
        return {
            "left_shoulder": 180.0, "right_shoulder": 180.0,
            "left_elbow": 180.0, "right_elbow": 180.0,
            "left_hip": 180.0, "right_hip": 180.0,
            "left_knee": 180.0, "right_knee": 180.0,
        }
    return {
        "left_shoulder": compute_joint_angle(
            landmarks[HIP_L], landmarks[SHOULDER_L], landmarks[ELBOW_L]
        ),
        "right_shoulder": compute_joint_angle(
            landmarks[HIP_R], landmarks[SHOULDER_R], landmarks[ELBOW_R]
        ),
        "left_elbow": compute_joint_angle(
            landmarks[SHOULDER_L], landmarks[ELBOW_L], landmarks[WRIST_L]
        ),
        "right_elbow": compute_joint_angle(
            landmarks[SHOULDER_R], landmarks[ELBOW_R], landmarks[WRIST_R]
        ),
        "left_hip": compute_joint_angle(
            landmarks[SHOULDER_L], landmarks[HIP_L], landmarks[KNEE_L]
        ),
        "right_hip": compute_joint_angle(
            landmarks[SHOULDER_R], landmarks[HIP_R], landmarks[KNEE_R]
        ),
        "left_knee": compute_joint_angle(
            landmarks[HIP_L], landmarks[KNEE_L], landmarks[ANKLE_L]
        ),
        "right_knee": compute_joint_angle(
            landmarks[HIP_R], landmarks[KNEE_R], landmarks[ANKLE_R]
        ),
    }


def pose_similarity_score(
    current: dict[str, float],
    target: dict[str, float],
    tolerance: dict[str, float],
) -> float:
    """Score 0-100 dựa trên mean absolute error normalized by tolerance.

    Cho mỗi joint key trong target:
        diff = abs(current[joint] - target[joint])
        group = joint.split("_")[1]  # "shoulder" | "elbow" | "hip" | "knee"
        joint_score = max(0, 100 - 100 * diff / (2 * tolerance[group]))

    Returns mean joint_score over target keys (0 nếu target rỗng).
    """
    if not target:
        return 0.0
    scores: list[float] = []
    for joint, target_angle in target.items():
        if joint not in current:
            scores.append(0.0)
            continue
        group = joint.split("_", 1)[1]  # "left_shoulder" → "shoulder"
        tol = tolerance.get(group, 20.0)
        diff = abs(current[joint] - target_angle)
        joint_score = max(0.0, 100.0 - 100.0 * diff / (2.0 * tol))
        scores.append(joint_score)
    return sum(scores) / len(scores)
