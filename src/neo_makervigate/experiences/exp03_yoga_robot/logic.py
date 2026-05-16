"""exp03 Yoga Robot — gameplay đầy đủ (P4).

State machine: INTRO(2s) → POSING(5 poses × max 45s) → RESULT(3s) → DONE.
5 poses load từ poses.toml. Joint-angle similarity scoring qua utils/landmark_math.

Test-friendly: nhận clock callable để inject FakeClock trong test_logic.py.
"""

from __future__ import annotations

import time
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

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
        dt = now - self._last_step_at
        if self._phase != Phase.POSING:
            self._current_score = 0
            self._last_step_at = now
            return
        # Stuck check — fires even on empty frames so 45s skip works without pose
        if self._attempts:
            attempt = self._attempts[-1]
            if not attempt.matched_complete:
                elapsed_in_attempt = now - attempt.started_at
                if elapsed_in_attempt >= SKIP_AFTER_SEC:
                    attempt.skipped = True
                    attempt.final_score = 0
                    self._advance_to_next_pose(now)
                    self._last_step_at = now
                    return
        if not frame.pose:
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
        if not self._attempts:
            self._last_step_at = now
            return
        attempt = self._attempts[-1]
        attempt.max_score_seen = max(attempt.max_score_seen, int(score))

        if score >= MATCH_THRESHOLD:
            attempt.hold_progress += dt
            attempt.last_match_at = now
            if attempt.hold_progress >= HOLD_REQUIRED_SEC and not attempt.matched_complete:
                attempt.matched_complete = True
                attempt.final_score = attempt.max_score_seen
                self._advance_to_next_pose(now)
                self._last_step_at = now
                return
        else:
            if (
                attempt.last_match_at is not None
                and now - attempt.last_match_at > MATCH_GAP_TOLERANCE
            ):
                attempt.hold_progress = 0.0
                attempt.last_match_at = None

        self._last_step_at = now

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
            "pose_landmarks_present": bool(
                self._current_score > 0
                or (attempt is not None and attempt.max_score_seen > 0)
            ),
        }

    def _best_pose_id(self) -> str | None:
        completed = [a for a in self._attempts if a.matched_complete or a.skipped]
        if not completed:
            return None
        best = max(completed, key=lambda a: a.final_score)
        return best.pose_id

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

    def _advance_to_next_pose(self, now: float) -> None:
        next_index = self._pose_index + 1
        if next_index >= len(self._poses):
            self._phase = Phase.RESULT
            self._phase_started_at = now
        else:
            self._start_pose(next_index, now)


EXPERIENCE = YogaRobotExperience
