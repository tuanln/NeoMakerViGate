"""exp03 Yoga Robot — Face-based gameplay (P7c rewrite).

Switched từ pose detection (full body, nhiễu nhiều) sang Face Mesh
(5 biểu cảm). Trẻ ngồi sát kiosk, không cần lùi ra.

5 poses: CUOI_TO, MO_MIENG_O, WINK, NHUONG_MAY, LAC_DAU.

Detector dispatcher map id → algorithm trong _evaluate_pose.
Head shake tracks yaw history deque maxlen 60 (~2s @ 30fps).
"""

from __future__ import annotations

import time
import tomllib
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from loguru import logger

from neo_makervigate.core.models import ExperienceMeta, Landmark, VisionFrame
from neo_makervigate.experiences.experience_base import BaseExperience
from neo_makervigate.utils.face_math import (
    brow_raised_ratio,
    eye_aspect_ratio,
    head_yaw,
    mouth_aspect_ratio,
    mouth_width_ratio,
)

_QML_PATH = (Path(__file__).parent / "ui.qml").as_posix()
_POSES_TOML = Path(__file__).parent / "poses.toml"

# Phase durations (sec)
INTRO_DURATION = 2.0
RESULT_DURATION = 3.0

# Pose attempt config
HOLD_REQUIRED_SEC = 2.0
MATCH_GAP_TOLERANCE = 0.3
HINT_AFTER_SEC = 15.0
SKIP_AFTER_SEC = 45.0

# Head shake tracking
YAW_HISTORY_MAXLEN = 60  # ~2s @ 30fps


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
    detector: str
    thresholds: dict[str, float]


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
                detector=entry["detector"],
                thresholds={k: float(v) for k, v in entry["thresholds"].items()},
            )
        )
    return poses


class YogaRobotExperience(BaseExperience):
    """Face Yoga — 5 biểu cảm vui (P7c)."""

    meta = ExperienceMeta(
        id="exp03_yoga_robot",
        title="Yoga Robot",
        subtitle="Bắt chước 5 biểu cảm vui!",
        age_min=5,
        age_max=12,
        vision_modules=("face",),
        needs_qwen=False,
        needs_voice=False,
        needs_internet=False,
        icon_path="",
        dev_days=7,
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
        self._yaw_history: deque[tuple[float, float]] = deque(maxlen=YAW_HISTORY_MAXLEN)

    def get_qml_path(self) -> str:
        return _QML_PATH

    def on_enter(self) -> None:
        now = self._clock()
        logger.info(f"YogaRobot (Face): on_enter ({len(self._poses)} poses loaded)")
        self._phase = Phase.INTRO
        self._phase_started_at = now
        self._last_step_at = now
        self._pose_index = 0
        self._attempts = []
        self._current_score = 0
        self._yaw_history.clear()

    def on_vision_frame(self, frame: VisionFrame) -> None:
        now = self._clock()
        self._step_phase(now)
        dt = now - self._last_step_at
        if self._phase != Phase.POSING or not frame.face:
            self._current_score = 0
            self._last_step_at = now
            return
        if self._pose_index >= len(self._poses):
            self._last_step_at = now
            return

        target = self._poses[self._pose_index]
        score, matched = self._evaluate_pose(frame.face, target, now)
        self._current_score = score
        if not self._attempts:
            self._last_step_at = now
            return
        attempt = self._attempts[-1]
        attempt.max_score_seen = max(attempt.max_score_seen, score)

        if matched:
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
            if (
                attempt.last_match_at is not None
                and now - attempt.last_match_at > MATCH_GAP_TOLERANCE
            ):
                attempt.hold_progress = 0.0
                attempt.last_match_at = None

        # Stuck-skip check
        if not attempt.matched_complete:
            elapsed_in_attempt = now - attempt.started_at
            if elapsed_in_attempt >= SKIP_AFTER_SEC:
                attempt.skipped = True
                attempt.final_score = 0
                self._advance_to_next_pose(now)
                self._last_step_at = now
                return

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
            "match_threshold": 65,
            "hold_progress": hold_progress,
            "hold_required": HOLD_REQUIRED_SEC,
            "elapsed_in_pose": elapsed_in_pose,
            "show_hint": elapsed_in_pose >= HINT_AFTER_SEC,
            "stuck_skip_at": SKIP_AFTER_SEC,
            "completed_poses": [
                {"id": a.pose_id, "final_score": a.final_score, "skipped": a.skipped}
                for a in self._attempts
                if a.matched_complete or a.skipped
            ],
            "total_score": sum(
                a.final_score for a in self._attempts if a.matched_complete or a.skipped
            ),
            "best_pose_id": self._best_pose_id(),
            "face_landmarks_present": bool(self._current_score > 0),
        }

    def completion_summary(self) -> dict[str, Any]:
        completed = [a for a in self._attempts if a.matched_complete or a.skipped]
        return {
            "completed": True,
            "score": sum(a.final_score for a in completed),
            "poses_completed": len(completed),
            "best_pose_id": self._best_pose_id(),
            "skipped_count": sum(1 for a in completed if a.skipped),
        }

    # ---- Internal ----

    def _evaluate_pose(
        self, face: list[Landmark], target: PoseTarget, now: float
    ) -> tuple[int, bool]:
        """Returns (score 0-100, matched bool)."""
        detector = target.detector
        th = target.thresholds
        if detector == "smile":
            mar = mouth_aspect_ratio(face)
            mwr = mouth_width_ratio(face)
            matched = mwr >= th["mouth_width_ratio_min"] and mar <= th["mar_max"]
            score = min(100, int((mwr / th["mouth_width_ratio_min"]) * 70))
            return score, matched
        if detector == "mouth_open":
            mar = mouth_aspect_ratio(face)
            matched = mar >= th["mar_min"]
            score = min(100, int((mar / th["mar_min"]) * 70))
            return score, matched
        if detector == "wink":
            ear_l = eye_aspect_ratio(face, "left")
            ear_r = eye_aspect_ratio(face, "right")
            left_winking = (
                ear_l <= th["closed_eye_ear_max"] and ear_r >= th["open_eye_ear_min"]
            )
            right_winking = (
                ear_r <= th["closed_eye_ear_max"] and ear_l >= th["open_eye_ear_min"]
            )
            matched = left_winking or right_winking
            return (100 if matched else 30), matched
        if detector == "brow_raised":
            ratio = brow_raised_ratio(face)
            matched = ratio >= th["brow_raised_min"]
            score = min(100, int((ratio / th["brow_raised_min"]) * 70))
            return score, matched
        if detector == "head_shake":
            yaw = head_yaw(face)
            self._yaw_history.append((now, yaw))
            matched, oscillations = self._check_head_shake(th)
            return min(100, oscillations * 33), matched
        return 0, False

    def _check_head_shake(self, th: dict[str, float]) -> tuple[bool, int]:
        """Returns (matched, oscillation_count)."""
        if len(self._yaw_history) < 8:
            return False, 0
        window = th.get("oscillation_window_sec", 1.5)
        amplitude_min = th.get("yaw_amplitude_min", 0.25)
        min_crossings = int(th.get("oscillation_min_crossings", 2))

        now = self._yaw_history[-1][0]
        recent = [(t, y) for t, y in self._yaw_history if now - t <= window]
        if len(recent) < 8:
            return False, 0
        yaws = [y for _, y in recent]
        amplitude = max(yaws) - min(yaws)
        if amplitude < amplitude_min:
            return False, 0
        baseline = sum(yaws) / len(yaws)
        dyaws = [y - baseline for y in yaws]
        crossings = sum(1 for i in range(1, len(dyaws)) if dyaws[i - 1] * dyaws[i] < 0)
        return crossings >= min_crossings, crossings

    def _step_phase(self, now: float) -> None:
        elapsed = now - self._phase_started_at
        if self._phase == Phase.INTRO and elapsed >= INTRO_DURATION:
            self._phase = Phase.POSING
            self._phase_started_at = now
            self._start_pose(0, now)
        elif self._phase == Phase.RESULT and elapsed >= RESULT_DURATION:
            self._phase = Phase.DONE
            self._phase_started_at = now

    def _start_pose(self, index: int, now: float) -> None:
        if index >= len(self._poses):
            return
        self._pose_index = index
        self._attempts.append(
            PoseAttempt(pose_id=self._poses[index].id, started_at=now)
        )
        self._yaw_history.clear()

    def _advance_to_next_pose(self, now: float) -> None:
        next_index = self._pose_index + 1
        if next_index >= len(self._poses):
            self._phase = Phase.RESULT
            self._phase_started_at = now
        else:
            self._start_pose(next_index, now)

    def _best_pose_id(self) -> str | None:
        completed = [a for a in self._attempts if a.matched_complete or a.skipped]
        if not completed:
            return None
        best = max(completed, key=lambda a: a.final_score)
        return best.pose_id


EXPERIENCE = YogaRobotExperience
