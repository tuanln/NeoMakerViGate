"""Face mesh math helpers cho exp03 Face Yoga.

Computes mouth aspect ratio (MAR), eye aspect ratio (EAR), brow raised
ratio, and approximate head yaw from MediaPipe Face Mesh 468 landmarks.

Stateless functions — caller passes landmarks list each frame.
"""

from __future__ import annotations

import math
from typing import Literal

from neo_makervigate.core.models import Landmark

# MediaPipe Face Mesh landmark indices (commonly used subset)
# Mouth (lip inner + outer corners)
LIP_TOP = 13
LIP_BOTTOM = 14
LIP_LEFT = 78
LIP_RIGHT = 308

# Left eye
LEFT_EYE_TOP = 159
LEFT_EYE_BOTTOM = 145
LEFT_EYE_INNER = 133
LEFT_EYE_OUTER = 33

# Right eye
RIGHT_EYE_TOP = 386
RIGHT_EYE_BOTTOM = 374
RIGHT_EYE_INNER = 362
RIGHT_EYE_OUTER = 263

# Eyebrows
LEFT_BROW_INNER = 55
LEFT_BROW_OUTER = 105
RIGHT_BROW_INNER = 285
RIGHT_BROW_OUTER = 334

# Head orientation
NOSE_TIP = 1
CHIN = 152
LEFT_TEMPLE = 234
RIGHT_TEMPLE = 454


def _dist(a: Landmark, b: Landmark) -> float:
    """Euclidean distance in normalized coords."""
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def mouth_aspect_ratio(landmarks: list[Landmark]) -> float:
    """MAR = vertical lip gap / horizontal lip width.

    Closed mouth: ~0.05. Wide smile: ~0.2. Open O: ~0.55+.
    """
    if len(landmarks) < 309:
        return 0.0
    vertical = _dist(landmarks[LIP_TOP], landmarks[LIP_BOTTOM])
    horizontal = _dist(landmarks[LIP_LEFT], landmarks[LIP_RIGHT])
    if horizontal < 1e-6:
        return 0.0
    return vertical / horizontal


def mouth_width_ratio(landmarks: list[Landmark]) -> float:
    """mouth_width / face_temple_width. Smile pulls corners outward.

    Neutral: ~0.35. Smile: ~0.45+.
    """
    if len(landmarks) < 455:
        return 0.0
    mouth_width = _dist(landmarks[LIP_LEFT], landmarks[LIP_RIGHT])
    face_width = _dist(landmarks[LEFT_TEMPLE], landmarks[RIGHT_TEMPLE])
    if face_width < 1e-6:
        return 0.0
    return mouth_width / face_width


def eye_aspect_ratio(landmarks: list[Landmark], side: Literal["left", "right"]) -> float:
    """EAR = vertical / horizontal. Open: ~0.3. Closed: <0.1."""
    if len(landmarks) < 387:
        return 0.0
    if side == "left":
        top, bot, inner, outer = LEFT_EYE_TOP, LEFT_EYE_BOTTOM, LEFT_EYE_INNER, LEFT_EYE_OUTER
    else:
        top, bot, inner, outer = RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM, RIGHT_EYE_INNER, RIGHT_EYE_OUTER
    vertical = _dist(landmarks[top], landmarks[bot])
    horizontal = _dist(landmarks[inner], landmarks[outer])
    if horizontal < 1e-6:
        return 0.0
    return vertical / horizontal


def brow_raised_ratio(landmarks: list[Landmark]) -> float:
    """(eye_top_Y - brow_Y) / face_height. Normal ~0.05. Raised >0.08.

    Average of left + right sides.
    """
    if len(landmarks) < 386:
        return 0.0
    # Brow above eye → brow_y < eye_y in image coords (y increases downward)
    left_gap = landmarks[LEFT_EYE_TOP].y - landmarks[LEFT_BROW_INNER].y
    right_gap = landmarks[RIGHT_EYE_TOP].y - landmarks[RIGHT_BROW_INNER].y
    avg_gap = (left_gap + right_gap) / 2
    # Face height = nose to chin; fall back to typical value if landmarks
    # are collapsed (e.g. test fixtures where CHIN is not explicitly set).
    face_height = abs(landmarks[CHIN].y - landmarks[NOSE_TIP].y)
    if face_height < 0.10:
        face_height = 0.30
    return avg_gap / face_height


def head_yaw(landmarks: list[Landmark]) -> float:
    """Approximate horizontal head rotation.

    Positive: face turned toward left temple (more nose-to-right distance).
    Negative: face turned toward right temple.
    Range roughly [-1, +1].
    """
    if len(landmarks) < 455:
        return 0.0
    nose = landmarks[NOSE_TIP]
    left = landmarks[LEFT_TEMPLE]
    right = landmarks[RIGHT_TEMPLE]
    d_left = _dist(nose, left)
    d_right = _dist(nose, right)
    face_width = _dist(left, right)
    if face_width < 1e-6:
        return 0.0
    return (d_right - d_left) / face_width
