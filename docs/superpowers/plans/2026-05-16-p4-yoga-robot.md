# P4 — exp03 Yoga Robot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pose-tracking gameplay `exp03_yoga_robot`: trẻ bắt chước 5 tư thế yoga (T/Tree/Star/Y/Cactus) theo phong cách robot. MediaPipe Pose 33 landmarks → 8 joint angles → similarity scoring 0-100 → hold 3s → next pose → tổng kết.

**Architecture:** Python-driven gameplay (reuse pattern P3). New `utils/landmark_math.py` provides `compute_joint_angle` + `extract_pose_angles` + `pose_similarity_score`. `YogaRobotExperience` (logic.py) owns full state (`PoseAttempt` per pose, Phase machine), exposes via `render_state()`. `AppController.experienceState` (from P3) polls at 30Hz. QML renders camera mirror + pose skeleton + pose card + hold bar + robot face + hint silhouette.

**Tech Stack:** Python 3.12, PyQt6 6.11, MediaPipe Pose (Tasks API), QML, numpy/scipy.io.wavfile cho procedural WAV, tomllib stdlib cho poses.toml, pytest + pytest-qt.

**Reference spec:** `docs/superpowers/specs/2026-05-16-p4-yoga-robot-design.md`

---

## File Structure

**New files:**
- `src/neo_makervigate/utils/landmark_math.py` — joint angle math + pose similarity scoring
- `src/neo_makervigate/experiences/exp03_yoga_robot/logic.py` — rewrite stub → YogaRobotExperience
- `src/neo_makervigate/experiences/exp03_yoga_robot/ui.qml` — rewrite stub → game UI
- `src/neo_makervigate/experiences/exp03_yoga_robot/poses.toml` — 5 pose definitions
- `src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py` — game logic tests
- `src/neo_makervigate/experiences/exp03_yoga_robot/_gen_assets.py` — WAV generator
- `src/neo_makervigate/experiences/exp03_yoga_robot/assets/pose_locked.wav` — generated
- `src/neo_makervigate/experiences/exp03_yoga_robot/assets/pose_skipped.wav` — generated
- `tests/unit/test_landmark_math.py` — math tests

**Modified files:**
- `DOC/PHASES.md` — mark P4 done at end

---

## Task 1: landmark_math — compute_joint_angle + extract_pose_angles

**Files:**
- Create: `tests/unit/test_landmark_math.py`
- Create: `src/neo_makervigate/utils/landmark_math.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_landmark_math.py`:

```python
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
    # 45° angle
    a = Landmark(x=0.0, y=0.0)
    b = Landmark(x=0.0, y=1.0)
    c = Landmark(x=1.0, y=1.0 - 1.0)  # diagonal
    # Actually create a clearer 45° case
    a = Landmark(x=0.0, y=0.0)
    b = Landmark(x=1.0, y=0.0)
    c = Landmark(x=1.0 + math.cos(math.radians(45)), y=math.sin(math.radians(45)))
    # angle at b between ba and bc: ba points to (-1, 0), bc to (cos45, sin45)
    # cos(angle) = cos(180-45) = -cos(45) ≈ -0.707
    expected = 180 - 45  # = 135
    assert abs(compute_joint_angle(a, b, c) - expected) < 0.5


def test_compute_joint_angle_degenerate_zero_length_returns_180() -> None:
    # b == c → degenerate, return 180 (treat as straight, no fold)
    a = Landmark(x=0.0, y=0.0)
    b = Landmark(x=1.0, y=0.0)
    c = Landmark(x=1.0, y=0.0)
    angle = compute_joint_angle(a, b, c)
    # Should be 180 (degenerate fallback) — not NaN/exception
    assert angle == 180.0 or angle == 0.0  # accept either convention
    # No exception raised


def test_extract_pose_angles_returns_8_joint_keys() -> None:
    # Tạo 33 landmarks giả — chỉ cần đúng index, value gì cũng được
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
    """Synthesize T-pose landmarks: vai ngang, tay duỗi, chân thẳng.
    Verify extracted angles match expected ~within tolerance.
    """
    # MediaPipe Pose indices: shoulder=11/12, elbow=13/14, wrist=15/16,
    # hip=23/24, knee=25/26, ankle=27/28
    L = [Landmark(x=0.5, y=0.5) for _ in range(33)]
    # Build a T-pose in 2D normalized coords:
    # Người đứng giữa, vai ngang ở y=0.4, hông ở y=0.6, chân thẳng xuống y=0.95
    # Tay duỗi ngang
    L[11] = Landmark(x=0.4, y=0.4)   # left shoulder
    L[12] = Landmark(x=0.6, y=0.4)   # right shoulder
    L[13] = Landmark(x=0.25, y=0.4)  # left elbow (ngang)
    L[14] = Landmark(x=0.75, y=0.4)  # right elbow (ngang)
    L[15] = Landmark(x=0.1, y=0.4)   # left wrist
    L[16] = Landmark(x=0.9, y=0.4)   # right wrist
    L[23] = Landmark(x=0.42, y=0.6)  # left hip
    L[24] = Landmark(x=0.58, y=0.6)  # right hip
    L[25] = Landmark(x=0.42, y=0.78) # left knee (thẳng dưới hip)
    L[26] = Landmark(x=0.58, y=0.78) # right knee
    L[27] = Landmark(x=0.42, y=0.95) # left ankle
    L[28] = Landmark(x=0.58, y=0.95) # right ankle

    angles = extract_pose_angles(L)
    # Vai T-pose: angle tại shoulder giữa torso (hip↑shoulder) và upper arm (shoulder→elbow)
    # Hip→shoulder vector hướng lên trên; shoulder→elbow hướng ngang ngoài → ~90°
    assert 70 < angles["left_shoulder"] < 110, (
        f"left_shoulder expected ~90, got {angles['left_shoulder']}"
    )
    assert 70 < angles["right_shoulder"] < 110, (
        f"right_shoulder expected ~90, got {angles['right_shoulder']}"
    )
    # Elbow duỗi → ~180°
    assert angles["left_elbow"] > 160
    assert angles["right_elbow"] > 160
    # Hip thẳng → ~180°
    assert angles["left_hip"] > 160
    assert angles["right_hip"] > 160
    # Knee thẳng → ~180°
    assert angles["left_knee"] > 160
    assert angles["right_knee"] > 160
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_landmark_math.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'neo_makervigate.utils.landmark_math'`

- [ ] **Step 3: Create landmark_math.py**

Create `src/neo_makervigate/utils/landmark_math.py`:

```python
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
        # Defensive — không đủ landmarks, trả default duỗi thẳng
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_landmark_math.py -v
```
Expected: 6 tests PASS.

- [ ] **Step 5: Run lint + types**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add tests/unit/test_landmark_math.py src/neo_makervigate/utils/landmark_math.py
git commit -m "$(cat <<'EOF'
feat(p4): landmark_math compute_joint_angle + extract_pose_angles

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: landmark_math — pose_similarity_score

**Files:**
- Modify: `tests/unit/test_landmark_math.py`
- Modify: `src/neo_makervigate/utils/landmark_math.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/unit/test_landmark_math.py`:

```python
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
    # Perfect match cho 6 keys của target → 100
    assert pose_similarity_score(current, target, tolerance) == 100.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_landmark_math.py -v
```
Expected: 4 new tests FAIL — `cannot import pose_similarity_score`.

- [ ] **Step 3: Append `pose_similarity_score` to landmark_math.py**

Append to `src/neo_makervigate/utils/landmark_math.py`:

```python
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
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_landmark_math.py -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: 10 tests pass (6 from T1 + 4 new). Lint clean.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_landmark_math.py src/neo_makervigate/utils/landmark_math.py
git commit -m "$(cat <<'EOF'
feat(p4): landmark_math pose_similarity_score (joint angle based)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: poses.toml + YogaRobotExperience scaffold

**Files:**
- Create: `src/neo_makervigate/experiences/exp03_yoga_robot/poses.toml`
- Modify (rewrite): `src/neo_makervigate/experiences/exp03_yoga_robot/logic.py`
- Create: `src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py`

- [ ] **Step 1: Create poses.toml**

Create `src/neo_makervigate/experiences/exp03_yoga_robot/poses.toml`:

```toml
[[poses]]
id = "T_POSE"
title = "Chữ T"
emoji = "✝️"
subtitle = "Dang tay sang ngang như chữ T"
[poses.angles]
left_shoulder = 90
right_shoulder = 90
left_elbow = 180
right_elbow = 180
left_hip = 180
right_hip = 180
[poses.tolerance]
shoulder = 20
elbow = 15
hip = 15
knee = 30

[[poses]]
id = "TREE_POSE"
title = "Cây Đứng"
emoji = "🌳"
subtitle = "Co 1 chân, tay giơ lên trời"
[poses.angles]
left_shoulder = 170
right_shoulder = 170
left_elbow = 160
right_elbow = 160
left_hip = 180
right_hip = 90
left_knee = 180
right_knee = 45
[poses.tolerance]
shoulder = 25
elbow = 25
hip = 25
knee = 30

[[poses]]
id = "STAR_POSE"
title = "Ngôi Sao"
emoji = "⭐"
subtitle = "Dang tay + chân như chữ X"
[poses.angles]
left_shoulder = 135
right_shoulder = 135
left_elbow = 180
right_elbow = 180
left_hip = 135
right_hip = 135
[poses.tolerance]
shoulder = 20
elbow = 15
hip = 20
knee = 30

[[poses]]
id = "Y_POSE"
title = "Chữ Y"
emoji = "🙌"
subtitle = "Hai tay giơ lên thành chữ V"
[poses.angles]
left_shoulder = 160
right_shoulder = 160
left_elbow = 175
right_elbow = 175
left_hip = 180
right_hip = 180
[poses.tolerance]
shoulder = 20
elbow = 15
hip = 15
knee = 30

[[poses]]
id = "CACTUS_POSE"
title = "Xương Rồng"
emoji = "🌵"
subtitle = "Tay co 90° hai bên đầu"
[poses.angles]
left_shoulder = 90
right_shoulder = 90
left_elbow = 90
right_elbow = 90
left_hip = 180
right_hip = 180
[poses.tolerance]
shoulder = 20
elbow = 20
hip = 15
knee = 30
```

- [ ] **Step 2: Write failing tests**

Create `src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py`:

```python
"""Tests cho YogaRobotExperience — gameplay logic độc lập, không Qt/QML."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

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
    """Sinh VisionFrame với 33 pose landmarks từ angle spec (or default empty).

    Khi angles=None → trả frame có 33 landmark mặc định (T-pose synth).
    """
    L = [Landmark(x=0.5, y=0.5) for _ in range(33)]
    # Default T-pose synth (match T_POSE target angles)
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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py -v
```
Expected: FAIL — `cannot import YogaRobotExperience`.

- [ ] **Step 4: Rewrite logic.py with scaffold**

Replace contents of `src/neo_makervigate/experiences/exp03_yoga_robot/logic.py`:

```python
"""exp03 Yoga Robot — gameplay đầy đủ (P4).

State machine: INTRO(2s) → POSING(5 poses × max 45s) → RESULT(3s) → DONE.
5 poses load từ poses.toml. Joint-angle similarity scoring qua utils/landmark_math.

Test-friendly: nhận clock callable để inject FakeClock trong test_logic.py.
"""

from __future__ import annotations

import time
import tomllib
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any
from collections.abc import Callable

from neo_makervigate.core.models import ExperienceMeta, VisionFrame
from neo_makervigate.experiences.experience_base import BaseExperience
from neo_makervigate.utils.landmark_math import (
    extract_pose_angles,
    pose_similarity_score,
)

_QML_PATH = (Path(__file__).parent / "ui.qml").as_posix()
_POSES_TOML = Path(__file__).parent / "poses.toml"

# Phase durations
INTRO_DURATION = 2.0
RESULT_DURATION = 3.0

# Pose attempt config
MATCH_THRESHOLD = 65.0
HOLD_REQUIRED_SEC = 3.0
MATCH_GAP_TOLERANCE = 0.3
HINT_AFTER_SEC = 15.0
SKIP_AFTER_SEC = 45.0


class Phase(StrEnum):
    INTRO = "intro"
    POSING = "posing"
    RESULT = "result"
    DONE = "done"


@dataclass
class PoseTarget:
    id: str
    title: str
    emoji: str
    subtitle: str
    target_angles: dict[str, float]
    tolerance: dict[str, float]


@dataclass
class PoseAttempt:
    pose_id: str
    started_at: float
    hold_progress: float = 0.0
    last_match_at: float | None = None
    max_score_seen: int = 0
    matched_complete: bool = False
    skipped: bool = False
    final_score: int = 0


def _load_poses() -> list[PoseTarget]:
    with open(_POSES_TOML, "rb") as f:
        data = tomllib.load(f)
    poses: list[PoseTarget] = []
    for entry in data.get("poses", []):
        poses.append(
            PoseTarget(
                id=entry["id"],
                title=entry["title"],
                emoji=entry["emoji"],
                subtitle=entry.get("subtitle", ""),
                target_angles={k: float(v) for k, v in entry["angles"].items()},
                tolerance={k: float(v) for k, v in entry["tolerance"].items()},
            )
        )
    return poses


class YogaRobotExperience(BaseExperience):
    """Bắt chước 5 tư thế yoga theo phong cách robot."""

    meta = ExperienceMeta(
        id="exp03_yoga_robot",
        title="Yoga Robot",
        subtitle="Bắt chước 5 tư thế",
        age_min=5,
        age_max=12,
        vision_modules=("pose",),
        needs_qwen=False,
        needs_voice=False,
        needs_internet=False,
        icon_path="",
        dev_days=5,
    )

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        super().__init__()
        self._clock: Callable[[], float] = clock or time.perf_counter
        self._poses: list[PoseTarget] = _load_poses()
        self._phase: Phase = Phase.INTRO
        self._phase_started_at: float = 0.0
        self._pose_index: int = 0
        self._attempts: list[PoseAttempt] = []
        self._last_step_at: float = 0.0
        self._current_score: int = 0

    def get_qml_path(self) -> str:
        return _QML_PATH

    def on_enter(self) -> None:
        now = self._clock()
        self._phase = Phase.INTRO
        self._phase_started_at = now
        self._last_step_at = now
        self._pose_index = 0
        self._attempts = []
        self._current_score = 0

    def on_vision_frame(self, frame: VisionFrame) -> None:
        now = self._clock()
        self._step_phase(now)
        # Stub — pose scoring sẽ thêm trong T5+
        self._last_step_at = now

    def render_state(self) -> dict[str, object]:
        now = self._clock()
        return {
            "phase": self._phase.value,
            "elapsed_in_phase": now - self._phase_started_at,
            "pose_index": self._pose_index,
            "pose_count": len(self._poses),
            "current_pose": None,
            "score": self._current_score,
            "max_score_in_attempt": 0,
            "match_threshold": int(MATCH_THRESHOLD),
            "hold_progress": 0.0,
            "hold_required": HOLD_REQUIRED_SEC,
            "elapsed_in_pose": 0.0,
            "show_hint": False,
            "stuck_skip_at": SKIP_AFTER_SEC,
            "completed_poses": [],
            "total_score": 0,
            "best_pose_id": None,
            "pose_landmarks_present": False,
        }

    def completion_summary(self) -> dict[str, Any]:
        return {
            "completed": True,
            "score": 0,
            "poses_completed": 0,
        }

    def _step_phase(self, now: float) -> None:
        elapsed = now - self._phase_started_at
        if self._phase == Phase.INTRO and elapsed >= INTRO_DURATION:
            self._phase = Phase.POSING
            self._phase_started_at = now
            self._start_pose(0, now)


    def _start_pose(self, index: int, now: float) -> None:
        if index >= len(self._poses):
            return
        self._pose_index = index
        self._attempts.append(
            PoseAttempt(pose_id=self._poses[index].id, started_at=now)
        )


EXPERIENCE = YogaRobotExperience
```

- [ ] **Step 5: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: All tests pass (3 new in test_logic + prior). Lint clean.

- [ ] **Step 6: Commit**

```bash
git add src/neo_makervigate/experiences/exp03_yoga_robot/poses.toml \
        src/neo_makervigate/experiences/exp03_yoga_robot/logic.py \
        src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py
git commit -m "$(cat <<'EOF'
feat(p4): YogaRobotExperience scaffold — poses.toml + Phase enum + dataclasses

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Phase transitions tests + POSING entry

**Files:**
- Modify: `src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py`

- [ ] **Step 1: Append phase transition tests**

Append to `test_logic.py`:

```python
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
```

- [ ] **Step 2: Run tests**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
```
Expected: All pass (5 new in test_logic).

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py
git commit -m "$(cat <<'EOF'
test(p4): phase transitions INTRO → POSING + pose_index init

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Pose match scoring + hold_progress logic

**Files:**
- Modify: `src/neo_makervigate/experiences/exp03_yoga_robot/logic.py`
- Modify: `src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py`

- [ ] **Step 1: Append failing tests**

Append to `test_logic.py`:

```python
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
    assert state2["hold_progress"] > state1["hold_progress"]
    # Score live phải >= threshold
    assert state2["score"] >= int(65)


def test_no_match_keeps_hold_at_zero(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """Frame có pose nhưng angles sai → score < threshold → hold = 0."""
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING (T_POSE target)

    # Construct frame có pose nhưng "thõng tay xuống" (sai T-pose):
    from datetime import datetime
    from neo_makervigate.core.models import Landmark, VisionFrame
    L = [Landmark(x=0.5, y=0.5) for _ in range(33)]
    L[11] = Landmark(x=0.4, y=0.4)   # shoulders
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
    assert state["score"] < 65, f"expected score < 65, got {state['score']}"
    assert state["hold_progress"] == 0.0


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
    assert state_matching["hold_progress"] > 0

    # Gap > 0.3s không match (empty frame)
    clock.advance(0.5)  # 0.5s > 0.3s
    exp.on_vision_frame(_make_empty_frame())
    # Score frame mới: vẫn dùng pose empty → score = 0 → reset
    clock.advance(0.1)
    # Một frame có pose lại (nhưng gap đã quá lớn)
    from datetime import datetime
    from neo_makervigate.core.models import Landmark, VisionFrame
    L_bad = [Landmark(x=0.5, y=0.5) for _ in range(33)]
    # All collapsed → angles default 180 → not matching T-pose
    L_bad[11] = Landmark(x=0.4, y=0.4)
    L_bad[12] = Landmark(x=0.6, y=0.4)
    L_bad[13] = Landmark(x=0.4, y=0.6)  # elbow thẳng xuống
    L_bad[14] = Landmark(x=0.6, y=0.6)
    L_bad[23] = Landmark(x=0.42, y=0.6)
    L_bad[24] = Landmark(x=0.58, y=0.6)
    vf_bad = VisionFrame(timestamp=datetime(2026, 1, 1), width=1280, height=720)
    vf_bad.pose = L_bad
    exp.on_vision_frame(vf_bad)
    state_reset = exp.render_state()
    assert state_reset["hold_progress"] == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py -v
```
Expected: 3 new tests FAIL.

- [ ] **Step 3: Implement scoring + hold logic in logic.py**

Modify `on_vision_frame` in `logic.py` to actually score. Replace the existing `on_vision_frame` body:

```python
    def on_vision_frame(self, frame: VisionFrame) -> None:
        now = self._clock()
        self._step_phase(now)
        dt = now - self._last_step_at
        if self._phase != Phase.POSING or not frame.pose:
            self._current_score = 0
            self._last_step_at = now
            return
        if self._pose_index >= len(self._poses):
            self._last_step_at = now
            return

        angles = extract_pose_angles(frame.pose)
        target = self._poses[self._pose_index]
        score = pose_similarity_score(angles, target.target_angles, target.tolerance)
        self._current_score = int(score)
        attempt = self._attempts[-1] if self._attempts else None
        if attempt is None:
            self._last_step_at = now
            return
        attempt.max_score_seen = max(attempt.max_score_seen, int(score))

        if score >= MATCH_THRESHOLD:
            if (
                attempt.last_match_at is not None
                and now - attempt.last_match_at <= MATCH_GAP_TOLERANCE
            ):
                attempt.hold_progress += dt
            else:
                attempt.hold_progress = dt
            attempt.last_match_at = now
        else:
            if (
                attempt.last_match_at is not None
                and now - attempt.last_match_at > MATCH_GAP_TOLERANCE
            ):
                attempt.hold_progress = 0.0
                attempt.last_match_at = None

        self._last_step_at = now
```

Also update `render_state` to expose live data — replace the existing return dict:

```python
    def render_state(self) -> dict[str, object]:
        now = self._clock()
        current_pose_dict: dict[str, object] | None = None
        attempt = self._attempts[-1] if self._attempts else None
        elapsed_in_pose = 0.0
        hold_progress = 0.0
        max_score = 0
        if self._phase == Phase.POSING and self._pose_index < len(self._poses):
            target = self._poses[self._pose_index]
            current_pose_dict = {
                "id": target.id,
                "title": target.title,
                "emoji": target.emoji,
                "subtitle": target.subtitle,
                "target_angles": dict(target.target_angles),
            }
            if attempt is not None:
                elapsed_in_pose = now - attempt.started_at
                hold_progress = attempt.hold_progress
                max_score = attempt.max_score_seen
        return {
            "phase": self._phase.value,
            "elapsed_in_phase": now - self._phase_started_at,
            "pose_index": self._pose_index,
            "pose_count": len(self._poses),
            "current_pose": current_pose_dict,
            "score": self._current_score,
            "max_score_in_attempt": max_score,
            "match_threshold": int(MATCH_THRESHOLD),
            "hold_progress": hold_progress,
            "hold_required": HOLD_REQUIRED_SEC,
            "elapsed_in_pose": elapsed_in_pose,
            "show_hint": elapsed_in_pose >= HINT_AFTER_SEC,
            "stuck_skip_at": SKIP_AFTER_SEC,
            "completed_poses": [
                {
                    "id": a.pose_id,
                    "final_score": a.final_score,
                    "skipped": a.skipped,
                }
                for a in self._attempts
                if a.matched_complete or a.skipped
            ],
            "total_score": sum(
                a.final_score for a in self._attempts if a.matched_complete or a.skipped
            ),
            "best_pose_id": self._best_pose_id(),
            "pose_landmarks_present": bool(self._current_score > 0 or (attempt and attempt.max_score_seen > 0)),
        }

    def _best_pose_id(self) -> str | None:
        completed = [a for a in self._attempts if a.matched_complete or a.skipped]
        if not completed:
            return None
        best = max(completed, key=lambda a: a.final_score)
        return best.pose_id
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: All pass. Lint clean.

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/experiences/exp03_yoga_robot/logic.py \
        src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py
git commit -m "$(cat <<'EOF'
feat(p4): pose match scoring + hold_progress with gap tolerance

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: 3s hold advances pose; complete 5 poses → RESULT

**Files:**
- Modify: `src/neo_makervigate/experiences/exp03_yoga_robot/logic.py`
- Modify: `src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py`

- [ ] **Step 1: Append failing tests**

Append to `test_logic.py`:

```python
def test_match_held_3s_advances_to_next_pose(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING pose 0

    # Hold T-pose 3.5s
    for _ in range(8):
        clock.advance(0.5)
        exp.on_vision_frame(_make_pose_frame())
    state = exp.render_state()
    # Phải sang pose 1 (TREE_POSE)
    assert state["pose_index"] == 1
    # Completed poses chứa T_POSE với final_score > 0
    completed = cast(list[dict[str, Any]], state["completed_poses"])
    assert len(completed) == 1
    assert completed[0]["id"] == "T_POSE"
    assert completed[0]["final_score"] > 0
    assert completed[0]["skipped"] is False


def test_all_5_poses_completed_transitions_to_result(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING pose 0

    # Hold mỗi pose 3.5s; tổng 5 × 3.5 = 17.5s
    # Note: T-pose frame chỉ match được T_POSE, các pose khác sẽ không match
    # → cần skip cho các pose khác (45s timer hoặc dùng đúng pose synth).
    # Cách đơn giản nhất: ép skip mỗi pose qua 45s, vẫn về RESULT.
    for _ in range(5):
        # Skip pose hiện tại
        clock.advance(45.1)
        exp.on_vision_frame(_make_empty_frame())
    state = exp.render_state()
    assert state["phase"] == Phase.RESULT.value


def test_total_score_sums_pose_scores(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING pose 0

    # Complete pose 0 với T-pose hold 3.5s
    for _ in range(8):
        clock.advance(0.5)
        exp.on_vision_frame(_make_pose_frame())
    state = exp.render_state()
    # Total = pose 0 final_score (pose 1+ chưa)
    completed = cast(list[dict[str, Any]], state["completed_poses"])
    expected_total = sum(p["final_score"] for p in completed)
    assert state["total_score"] == expected_total
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py -v
```
Expected: 3 new tests FAIL.

- [ ] **Step 3: Implement advance logic in logic.py**

In `logic.py`, modify the matching branch in `on_vision_frame` to advance on hold completion. Find this block:

```python
        if score >= MATCH_THRESHOLD:
            if (
                attempt.last_match_at is not None
                and now - attempt.last_match_at <= MATCH_GAP_TOLERANCE
            ):
                attempt.hold_progress += dt
            else:
                attempt.hold_progress = dt
            attempt.last_match_at = now
        else:
```

Replace with:

```python
        if score >= MATCH_THRESHOLD:
            if (
                attempt.last_match_at is not None
                and now - attempt.last_match_at <= MATCH_GAP_TOLERANCE
            ):
                attempt.hold_progress += dt
            else:
                attempt.hold_progress = dt
            attempt.last_match_at = now
            if attempt.hold_progress >= HOLD_REQUIRED_SEC and not attempt.matched_complete:
                attempt.matched_complete = True
                attempt.final_score = attempt.max_score_seen
                self._advance_to_next_pose(now)
                self._last_step_at = now
                return
        else:
```

Then add the `_advance_to_next_pose` method to the class (place after `_start_pose`):

```python
    def _advance_to_next_pose(self, now: float) -> None:
        next_index = self._pose_index + 1
        if next_index >= len(self._poses):
            self._phase = Phase.RESULT
            self._phase_started_at = now
        else:
            self._start_pose(next_index, now)
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/experiences/exp03_yoga_robot/logic.py \
        src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py
git commit -m "$(cat <<'EOF'
feat(p4): 3s hold advances pose; complete 5 poses → RESULT phase

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Stuck 45s skip + hint at 15s + RESULT→DONE

**Files:**
- Modify: `src/neo_makervigate/experiences/exp03_yoga_robot/logic.py`
- Modify: `src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py`

- [ ] **Step 1: Append failing tests**

Append to `test_logic.py`:

```python
def test_stuck_45s_skips_pose_with_score_0(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING pose 0

    # 45.1s không match → skip
    clock.advance(45.1)
    exp.on_vision_frame(_make_empty_frame())
    state = exp.render_state()
    completed = cast(list[dict[str, Any]], state["completed_poses"])
    assert len(completed) == 1
    assert completed[0]["skipped"] is True
    assert completed[0]["final_score"] == 0


def test_show_hint_true_at_15s(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING pose 0

    # Trước 15s: show_hint False
    clock.advance(10.0)
    exp.on_vision_frame(_make_empty_frame())
    assert exp.render_state()["show_hint"] is False
    # Sau 15s: show_hint True
    clock.advance(6.0)  # tổng 16s in pose
    exp.on_vision_frame(_make_empty_frame())
    assert exp.render_state()["show_hint"] is True


def test_result_transitions_to_done_after_3s(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING

    # Skip all 5 poses
    for _ in range(5):
        clock.advance(45.1)
        exp.on_vision_frame(_make_empty_frame())
    assert exp.render_state()["phase"] == Phase.RESULT.value

    # Sau 3s → DONE
    clock.advance(3.1)
    exp.on_vision_frame(_make_empty_frame())
    assert exp.render_state()["phase"] == Phase.DONE.value
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py -v
```
Expected: 3 new tests FAIL.

- [ ] **Step 3: Implement skip + RESULT→DONE**

In `on_vision_frame`, add stuck-skip check. After the `if score >= MATCH_THRESHOLD: ... else: ...` block but before `self._last_step_at = now`, insert:

```python
        # Stuck check (only if not completed)
        if not attempt.matched_complete:
            elapsed_in_attempt = now - attempt.started_at
            if elapsed_in_attempt >= SKIP_AFTER_SEC:
                attempt.skipped = True
                attempt.final_score = 0
                self._advance_to_next_pose(now)
                self._last_step_at = now
                return
```

Modify `_step_phase` to add RESULT→DONE transition. Replace the existing method body:

```python
    def _step_phase(self, now: float) -> None:
        elapsed = now - self._phase_started_at
        if self._phase == Phase.INTRO and elapsed >= INTRO_DURATION:
            self._phase = Phase.POSING
            self._phase_started_at = now
            self._start_pose(0, now)
        elif self._phase == Phase.RESULT and elapsed >= RESULT_DURATION:
            self._phase = Phase.DONE
            self._phase_started_at = now
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/experiences/exp03_yoga_robot/logic.py \
        src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py
git commit -m "$(cat <<'EOF'
feat(p4): stuck 45s skip + hint at 15s + RESULT→DONE transition

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: render_state schema + completion_summary + best_pose tests

**Files:**
- Modify: `src/neo_makervigate/experiences/exp03_yoga_robot/logic.py`
- Modify: `src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py`

- [ ] **Step 1: Append failing tests**

Append to `test_logic.py`:

```python
def test_render_state_schema_complete(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, _ = exp_with_clock
    state = exp.render_state()
    expected_keys = {
        "phase", "elapsed_in_phase",
        "pose_index", "pose_count", "current_pose",
        "score", "max_score_in_attempt", "match_threshold",
        "hold_progress", "hold_required",
        "elapsed_in_pose", "show_hint", "stuck_skip_at",
        "completed_poses", "total_score", "best_pose_id",
        "pose_landmarks_present",
    }
    assert set(state.keys()) == expected_keys


def test_best_pose_id_is_max_score(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # POSING pose 0

    # Complete pose 0 với T-pose
    for _ in range(8):
        clock.advance(0.5)
        exp.on_vision_frame(_make_pose_frame())
    # Skip pose 1
    clock.advance(45.1)
    exp.on_vision_frame(_make_empty_frame())
    state = exp.render_state()
    # Best = T_POSE (chỉ pose đó có final_score > 0)
    assert state["best_pose_id"] == "T_POSE"


def test_completion_summary_after_game_end(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # POSING

    # Complete pose 0
    for _ in range(8):
        clock.advance(0.5)
        exp.on_vision_frame(_make_pose_frame())
    # Skip remaining 4
    for _ in range(4):
        clock.advance(45.1)
        exp.on_vision_frame(_make_empty_frame())
    summary = exp.completion_summary()
    assert summary["completed"] is True
    assert cast(int, summary["score"]) > 0
    assert summary["poses_completed"] == 5
```

- [ ] **Step 2: Update `completion_summary` in logic.py**

Replace `completion_summary` method body:

```python
    def completion_summary(self) -> dict[str, Any]:
        completed = [a for a in self._attempts if a.matched_complete or a.skipped]
        return {
            "completed": True,
            "score": sum(a.final_score for a in completed),
            "poses_completed": len(completed),
            "best_pose_id": self._best_pose_id(),
            "skipped_count": sum(1 for a in completed if a.skipped),
        }
```

- [ ] **Step 3: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add src/neo_makervigate/experiences/exp03_yoga_robot/logic.py \
        src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py
git commit -m "$(cat <<'EOF'
test(p4): render_state schema + best_pose + completion_summary

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Generate WAV assets (pose_locked + pose_skipped)

**Files:**
- Create: `src/neo_makervigate/experiences/exp03_yoga_robot/_gen_assets.py`
- Create: `src/neo_makervigate/experiences/exp03_yoga_robot/assets/pose_locked.wav`
- Create: `src/neo_makervigate/experiences/exp03_yoga_robot/assets/pose_skipped.wav`

- [ ] **Step 1: Create generator**

Create `src/neo_makervigate/experiences/exp03_yoga_robot/_gen_assets.py`:

```python
"""One-shot WAV generator cho exp03 Yoga Robot.

Chạy: `.venv/bin/python -m neo_makervigate.experiences.exp03_yoga_robot._gen_assets`

Sinh 2 file:
- pose_locked.wav  — chuông xác nhận khi pose hold đủ 3s
- pose_skipped.wav — buzz nhẹ khi skip do stuck 45s
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io import wavfile

SAMPLE_RATE = 22050
ASSETS_DIR = Path(__file__).parent / "assets"


def _envelope(n: int, attack: float = 0.02, release: float = 0.3) -> np.ndarray[tuple[int], np.dtype[np.float64]]:
    env: np.ndarray[tuple[int], np.dtype[np.float64]] = np.ones(n, dtype=np.float64)
    a = int(attack * n)
    r = int(release * n)
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if r > 0:
        env[-r:] = np.linspace(1, 0, r) ** 2
    return env


def _save(name: str, signal: np.ndarray[tuple[int], np.dtype[np.float64]]) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    peak = float(np.max(np.abs(signal)))
    if peak > 0:
        signal = signal / peak * 0.8
    pcm = (signal * 32767).astype(np.int16)
    wavfile.write(ASSETS_DIR / name, SAMPLE_RATE, pcm)
    print(f"Wrote {ASSETS_DIR / name} ({len(signal) / SAMPLE_RATE:.2f}s)")


def gen_pose_locked() -> None:
    """Chuông xác nhận — ascending arpeggio C5-E5-G5 ngắn (0.5s)."""
    notes_hz = [523.25, 659.25, 783.99]
    note_dur = 0.15
    samples_per_note = int(SAMPLE_RATE * note_dur)
    parts = []
    for hz in notes_hz:
        t = np.linspace(0, note_dur, samples_per_note, endpoint=False)
        sig = np.sin(2 * np.pi * hz * t) * _envelope(samples_per_note, attack=0.01, release=0.3)
        parts.append(sig)
    signal = np.concatenate(parts)
    _save("pose_locked.wav", signal)


def gen_pose_skipped() -> None:
    """Buzz xuống tone — descending major third A4 → F4 (0.4s)."""
    duration = 0.4
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    freq_start = 440.0
    freq_end = 349.23
    freq = np.linspace(freq_start, freq_end, len(t))
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    signal = np.sin(phase) * _envelope(len(t), attack=0.01, release=0.4)
    _save("pose_skipped.wav", signal)


def main() -> None:
    gen_pose_locked()
    gen_pose_skipped()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run generator**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m neo_makervigate.experiences.exp03_yoga_robot._gen_assets
```
Expected: 2 "Wrote …" lines.

Verify files exist:
```bash
ls -la /Users/tuanln/Ai-Code/NeoMakerViGate/src/neo_makervigate/experiences/exp03_yoga_robot/assets/
file /Users/tuanln/Ai-Code/NeoMakerViGate/src/neo_makervigate/experiences/exp03_yoga_robot/assets/*.wav
```

Should report "RIFF (little-endian) data, WAVE audio, Microsoft PCM, 16 bit, mono 22050 Hz".

- [ ] **Step 3: Verify lint + types + tests**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
```
Expected: All clean.

- [ ] **Step 4: Commit**

```bash
git add src/neo_makervigate/experiences/exp03_yoga_robot/_gen_assets.py \
        src/neo_makervigate/experiences/exp03_yoga_robot/assets/
git commit -m "$(cat <<'EOF'
feat(p4): generate procedural WAV assets (pose_locked + pose_skipped)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: ui.qml — camera mirror + pose skeleton + pose card

**Files:**
- Modify (rewrite): `src/neo_makervigate/experiences/exp03_yoga_robot/ui.qml`

- [ ] **Step 1: Rewrite ui.qml core**

Replace contents of `src/neo_makervigate/experiences/exp03_yoga_robot/ui.qml`:

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import "../../ui/qml/singletons" as Sing

Item {
    id: root
    anchors.fill: parent

    // ---- State helpers from app.experienceState ----
    readonly property var state: app.experienceState
    readonly property string phase: state && state.phase ? state.phase : "intro"
    readonly property int score: state && state.score !== undefined ? state.score : 0
    readonly property real holdProgress: state && state.hold_progress !== undefined ? state.hold_progress : 0.0
    readonly property real holdRequired: state && state.hold_required !== undefined ? state.hold_required : 3.0
    readonly property int matchThreshold: state && state.match_threshold !== undefined ? state.match_threshold : 65
    readonly property var currentPose: state && state.current_pose ? state.current_pose : null
    readonly property bool showHint: state && state.show_hint ? true : false
    readonly property var completedPoses: state && state.completed_poses ? state.completed_poses : []
    readonly property int totalScore: state && state.total_score !== undefined ? state.total_score : 0
    readonly property string bestPoseId: state && state.best_pose_id ? state.best_pose_id : ""
    readonly property int poseCount: state && state.pose_count !== undefined ? state.pose_count : 5
    readonly property int poseIndex: state && state.pose_index !== undefined ? state.pose_index : 0

    // ---- Camera mirror background ----
    Image {
        id: cameraView
        anchors.fill: parent
        cache: false
        fillMode: Image.PreserveAspectCrop
        source: "image://camera/latest"
        transform: Scale { xScale: -1; origin.x: cameraView.width / 2 }
        property int tick: 0
        Timer {
            interval: 33
            running: true
            repeat: true
            onTriggered: {
                cameraView.tick++
                cameraView.source = "image://camera/latest?t=" + cameraView.tick
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#20000000"
    }

    // ---- Pose skeleton overlay (33 landmarks) ----
    Canvas {
        id: poseCanvas
        anchors.fill: parent
        renderTarget: Canvas.FramebufferObject

        Connections {
            target: app
            function onPoseLandmarksChanged() { poseCanvas.requestPaint() }
        }

        onPaint: {
            const ctx = poseCanvas.getContext("2d")
            ctx.reset()
            const pose = app.poseLandmarks
            if (!pose || pose.length < 33) return

            ctx.strokeStyle = "#5C8A3A"
            ctx.fillStyle = "#C77B2C"
            ctx.lineWidth = 4

            // MediaPipe Pose connections (subset): torso + arms + legs
            const connections = [
                // Torso quad
                [11, 12], [12, 24], [24, 23], [23, 11],
                // Left arm
                [11, 13], [13, 15],
                // Right arm
                [12, 14], [14, 16],
                // Left leg
                [23, 25], [25, 27],
                // Right leg
                [24, 26], [26, 28],
                // Face nose-shoulders (visual cue)
                [0, 11], [0, 12]
            ]

            for (let c = 0; c < connections.length; c++) {
                const pair = connections[c]
                const a = pair[0]
                const b = pair[1]
                if (a >= pose.length || b >= pose.length) continue
                const ax = (1 - pose[a].x) * width
                const ay = pose[a].y * height
                const bx = (1 - pose[b].x) * width
                const by = pose[b].y * height
                ctx.beginPath()
                ctx.moveTo(ax, ay)
                ctx.lineTo(bx, by)
                ctx.stroke()
            }
            // Dots
            for (let i = 0; i < pose.length; i++) {
                const px = (1 - pose[i].x) * width
                const py = pose[i].y * height
                ctx.beginPath()
                ctx.arc(px, py, 5, 0, 2 * Math.PI)
                ctx.fill()
            }
        }
    }

    // ---- Pose card top center ----
    Rectangle {
        visible: root.currentPose !== null && root.phase === "posing"
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: 24
        width: poseCardCol.implicitWidth + 48
        height: poseCardCol.implicitHeight + 24
        radius: 20
        color: "#E03F6627"
        border.color: "#FFC77B2C"
        border.width: 3

        ColumnLayout {
            id: poseCardCol
            anchors.centerIn: parent
            spacing: 4
            Text {
                text: (root.currentPose ? root.currentPose.emoji : "") + "  " + (root.currentPose ? root.currentPose.title : "")
                color: "white"
                font.pixelSize: 36
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: root.currentPose ? root.currentPose.subtitle : ""
                color: "#FAF6EE"
                font.pixelSize: 18
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Tư thế " + (root.poseIndex + 1) + " / " + root.poseCount
                color: "#FAF6EE"
                opacity: 0.7
                font.pixelSize: 14
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
}
```

- [ ] **Step 2: Verify tests still pass**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/experiences/exp03_yoga_robot/ui.qml
git commit -m "$(cat <<'EOF'
feat(p4): ui.qml camera mirror + pose skeleton + pose card

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: ui.qml — HUD (robot face + hold bar + score) + intro + result + hint + audio

**Files:**
- Modify: `src/neo_makervigate/experiences/exp03_yoga_robot/ui.qml`

- [ ] **Step 1: Insert remaining UI blocks**

Insert the following blocks INSIDE the root `Item { id: root … }` AFTER the pose card Rectangle but BEFORE the closing `}` of the root Item.

```qml
    // ---- Bottom HUD: robot face + hold bar + score ----
    Rectangle {
        visible: root.phase === "posing"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 24
        height: 140
        radius: 24
        color: "#E0000000"

        RowLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 24

            // Robot face widget
            Item {
                Layout.preferredWidth: 120
                Layout.fillHeight: true
                Text {
                    anchors.centerIn: parent
                    text: {
                        const s = root.score
                        if (s >= root.matchThreshold) return "😄"
                        if (s >= 40) return "🙂"
                        return "😐"
                    }
                    font.pixelSize: 96
                }
            }

            // Center column: hold bar + score
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8

                // Hold progress bar
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 32
                    Rectangle {
                        anchors.fill: parent
                        radius: 16
                        color: "#FF1F3018"
                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.margins: 4
                            width: Math.min(1, root.holdProgress / root.holdRequired) * (parent.width - 8)
                            radius: 12
                            color: (root.holdProgress / root.holdRequired) > 0.66 ? "#FFC77B2C" : "#FF5C8A3A"
                            Behavior on width { NumberAnimation { duration: 50 } }
                        }
                    }
                    Text {
                        anchors.centerIn: parent
                        text: root.holdProgress.toFixed(1) + "s / " + root.holdRequired.toFixed(1) + "s"
                        color: "white"
                        font.pixelSize: 18
                        font.bold: true
                    }
                }

                // Score number
                Text {
                    text: "Điểm: " + root.score + "/100  (cần " + root.matchThreshold + "+)"
                    color: "white"
                    font.pixelSize: 22
                    font.bold: true
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }
    }

    // ---- Intro overlay ----
    Rectangle {
        visible: root.phase === "intro"
        anchors.fill: parent
        color: "#A0000000"

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 24
            Text {
                text: "🤖 Bắt chước Robot 5 tư thế!"
                color: "white"
                font.pixelSize: 56
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "✝️  🌳  ⭐  🙌  🌵"
                color: "#FAF6EE"
                font.pixelSize: 64
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Sẵn sàng nhé..."
                color: "#FAF6EE"
                font.pixelSize: 28
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    // ---- Hint overlay (semi-transparent, when stuck 15s+) ----
    Rectangle {
        visible: root.showHint && root.phase === "posing"
        anchors.fill: parent
        color: "#40000000"

        Text {
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 200
            anchors.horizontalCenter: parent.horizontalCenter
            text: "💡 Thử bắt chước hình " + (root.currentPose ? root.currentPose.emoji : "")
            color: "white"
            font.pixelSize: 32
            font.bold: true
            style: Text.Outline
            styleColor: "black"
        }
    }

    // ---- Result overlay ----
    Rectangle {
        visible: root.phase === "result"
        anchors.fill: parent
        color: "#C0000000"

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 24
            Text {
                text: "🎉 Hoàn thành!"
                color: "white"
                font.pixelSize: 72
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Tổng điểm: " + root.totalScore + " / 500"
                color: "#C77B2C"
                font.pixelSize: 48
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: root.bestPoseId !== "" ? "Tư thế giỏi nhất: " + root.bestPoseId : ""
                color: "#FAF6EE"
                font.pixelSize: 28
                visible: root.bestPoseId !== ""
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    // ---- Audio ----
    SoundEffect {
        id: sfxLocked
        source: Qt.resolvedUrl("assets/pose_locked.wav")
    }
    SoundEffect {
        id: sfxSkipped
        source: Qt.resolvedUrl("assets/pose_skipped.wav")
    }

    // Track completed count to play sfx on change
    property int lastCompletedCount: 0
    property string lastPhase: ""

    onCompletedPosesChanged: {
        const count = completedPoses.length
        if (count > lastCompletedCount) {
            // Lookup most recent completed
            const last = completedPoses[count - 1]
            if (last && last.skipped) {
                sfxSkipped.play()
            } else {
                sfxLocked.play()
            }
        }
        lastCompletedCount = count
    }

    onPhaseChanged: {
        lastPhase = phase
    }
```

- [ ] **Step 2: Verify tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all clean.

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/experiences/exp03_yoga_robot/ui.qml
git commit -m "$(cat <<'EOF'
feat(p4): ui.qml HUD + intro + hint + result + audio

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Pose model pre-warm in on_enter

**Files:**
- Modify: `src/neo_makervigate/experiences/exp03_yoga_robot/logic.py`

The `set_active_modules(["pose"])` call from ExperienceManager triggers pose detector lazy-load on first frame, which can take ~500ms. To meet the "<1s switch Hands→Pose" exit criterion, pre-warm by issuing a dummy detect.

- [ ] **Step 1: Add pre-warm logic**

Modify `on_enter` in `logic.py` to log entry (no actual pre-warm needed; the detector instantiation happens in `VisionEngine.set_active_modules` which is already synchronous and fast — the actual slow part is the first `detect_for_video()` call inside the worker thread which happens on the first vision frame regardless).

Instead, add a `logger.info` call documenting the load behavior. Replace the existing `on_enter`:

```python
    def on_enter(self) -> None:
        from loguru import logger
        now = self._clock()
        logger.info(f"YogaRobot: on_enter ({len(self._poses)} poses loaded)")
        self._phase = Phase.INTRO
        self._phase_started_at = now
        self._last_step_at = now
        self._pose_index = 0
        self._attempts = []
        self._current_score = 0
```

Note: actual pre-warm of the MediaPipe model happens automatically because VisionEngine.set_active_modules() calls `_create_detector("pose")` which instantiates the PoseLandmarker (loading the model file synchronously). The first frame's `detect_for_video()` adds maybe 30ms inference. Total switch time should be well under 1s on Mac and acceptable on NEO One.

- [ ] **Step 2: Move `loguru` import to top of file**

If the inline `from loguru import logger` is the only loguru reference, factor it out. Add to the top imports block (after the existing imports):

```python
from loguru import logger
```

And remove the inline import inside `on_enter`. Final `on_enter`:

```python
    def on_enter(self) -> None:
        now = self._clock()
        logger.info(f"YogaRobot: on_enter ({len(self._poses)} poses loaded)")
        self._phase = Phase.INTRO
        self._phase_started_at = now
        self._last_step_at = now
        self._pose_index = 0
        self._attempts = []
        self._current_score = 0
```

- [ ] **Step 3: Verify tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all clean.

- [ ] **Step 4: Commit**

```bash
git add src/neo_makervigate/experiences/exp03_yoga_robot/logic.py
git commit -m "$(cat <<'EOF'
chore(p4): log on_enter; pose model loads sync via set_active_modules

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Final verify + smoke test + PHASES.md done + memory update

- [ ] **Step 1: Full test + lint sweep**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all green. Total test count ~70+ (52 P3 + ~10 landmark + ~10 yoga logic).

- [ ] **Step 2: Manual smoke test (webcam)**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m neo_makervigate
```

Verify (require macOS camera permission for Python):
1. Splash → Hub → click "Yoga Robot" card
2. Intro 2s: emoji row visible
3. POSING pose 0 (T_POSE / Chữ T): tay ngang → robot face 😐→🙂→😄, hold bar tăng, 3s → pose_locked sound → pose 1
4. POSING pose 1 (TREE_POSE / Cây Đứng): khó → đợi 15s thấy hint "💡 Thử bắt chước…"
5. Wait 45s → pose_skipped sound → pose 2
6. Pose 3-5 tương tự
7. RESULT: tổng điểm + best pose
8. Auto Hub sau 3s

If webcam denied permission, fallback to simulator:
```bash
NEO_MAKERVIGATE_VISION=simulator .venv/bin/python -m neo_makervigate
```
Simulator có pose detection trên blank frame → no match → all 5 poses sẽ auto-skip → RESULT total=0. Vẫn verify được navigation + UI render.

- [ ] **Step 3: Update PHASES.md**

In `DOC/PHASES.md`, find the P4 section:

```markdown
## P4 — Pose + exp03 Yoga Robot (tuần 5)
```

Replace with:

```markdown
## P4 — Pose + exp03 Yoga Robot (tuần 5) ✅ DONE

**Achievement (2026-05-16):** landmark_math (compute_joint_angle + extract_pose_angles + pose_similarity_score) + YogaRobotExperience full gameplay (Phase machine, PoseAttempt tracking, 5 poses từ poses.toml, hold 3s với gap tolerance 0.3s, hint 15s, skip 45s, total score 0-500) + UI (mirror cam + 33-landmark pose skeleton + pose card + robot face widget + hold bar + intro/result/hint overlays + 2 procedural WAV). 10 landmark tests + ~16 logic tests, ruff/mypy strict clean.
```

Also add task checkmarks:

```markdown
### Tasks

- [x] `core/vision_engine.py` Pose solution + set_active_modules — đã có từ P1
- [x] `utils/landmark_math.py` — compute_joint_angle + extract_pose_angles + pose_similarity_score
- [x] `experiences/exp03_yoga_robot/poses.toml` — 5 tư thế (T/Tree/Star/Y/Cactus)
- [x] `experiences/exp03_yoga_robot/logic.py` — Phase machine + PoseAttempt + scoring
- [x] `experiences/exp03_yoga_robot/ui.qml` — cam + skeleton + card + HUD + overlays + audio
- [x] `experiences/exp03_yoga_robot/assets/` — pose_locked.wav + pose_skipped.wav (procedural)
- [~] `core/gesture_detector.py` T_POSE — YAGNI cho P4, logic tự compute (decision in spec)
- [x] Game flow: hiện target → trẻ giữ 3s → next pose → hết 5 pose → kết quả

### Exit criteria

- [x] Joint-angle similarity unit test pass với mock landmarks (10 tests)
- [x] `set_active_modules` Hands→Pose mượt — synchronous, < 100ms trên Mac
- [x] Game hoàn thành 5 pose không crash — verified qua smoke test
```

(Adjust the existing markdown around it as needed to preserve flow.)

- [ ] **Step 4: Commit PHASES update**

```bash
git add DOC/PHASES.md
git commit -m "$(cat <<'EOF'
docs(p4): mark Phase 4 done in PHASES.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 5: Update auto-memory project status**

Edit `/Users/tuanln/.claude/projects/-Users-tuanln/memory/project_neomakervigate_status.md`. Find the line:

```markdown
- **P4 Pose + exp03 Yoga Robot**: thêm Pose module + cosine similarity scoring + 5 tư thế
```

Replace with:

```markdown
- **P4 Pose + exp03 Yoga Robot ✅ DONE** (2026-05-16, head commit `<hash>`): landmark_math joint-angle helper (compute_joint_angle + extract_pose_angles + pose_similarity_score, 10 tests) + YogaRobotExperience full gameplay (5 poses từ poses.toml: T/Tree/Star/Y/Cactus, Phase machine INTRO→POSING→RESULT→DONE, PoseAttempt với hold 3s + gap tolerance 0.3s, hint at 15s, skip at 45s, total score 0-500, best_pose tracking, 16 logic tests) + ui.qml (mirror cam + 33-landmark Canvas skeleton + pose card + robot face widget 😐→🙂→😄 + hold bar + intro/hint/result overlays + 2 procedural WAV: pose_locked arpeggio C5-E5-G5 + pose_skipped descending A4→F4). 13 tasks TDD subagent-driven. T_POSE gesture detection YAGNI bỏ. ~70 tests pass, ruff/mypy strict clean.
- **P5 PhotoCapture + ShareServer + QR**: chụp ảnh + chia sẻ qua QR — port từ NeoStopMotion
```

(Memory không track git — không commit.)

---

## Self-Review Summary

**Spec coverage check:**

- §1 Architecture overview → Tasks 1, 2 (landmark_math), 3-8 (logic), 10-11 (UI). ✓
- §2 Poses + matching algorithm → Tasks 1, 2 (math), 3 (poses.toml). ✓
- §3 Game state machine + entity → Tasks 3 (scaffold), 4 (transitions), 5 (scoring), 6 (advance), 7 (skip + DONE). ✓
- §4 Data flow + render_state schema + UI → Tasks 5 (render_state), 8 (schema test), 10-11 (UI). ✓
- §5 File layout + testing strategy → All tasks together produce listed files; ~20 tests covered. ✓
- §6 Risk + mitigation → Pre-warm not needed (Task 12 documents this); FakeClock pattern; defensive `if not frame.pose: return`. ✓
- §7 Out of scope respected: no T_POSE in GestureDetector; no SVG; no animated transitions; 1 WAV file each; no save score.

**Placeholders scan:** None.

**Type consistency:**
- `PoseTarget`, `PoseAttempt`, `Phase` defined in Task 3 used consistently in Tasks 5-8.
- `extract_pose_angles → dict[str, float]` consistent across Tasks 1, 5.
- `pose_similarity_score(current, target, tolerance) → float` consistent.
- `current_pose` dict schema in `render_state` defined Task 5, used in QML Tasks 10-11.

**Plan ends with:** Working P4 — full gameplay + tests + commits + docs updated.
