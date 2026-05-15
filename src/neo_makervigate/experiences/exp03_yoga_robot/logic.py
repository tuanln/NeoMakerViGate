"""exp03 Yoga Robot — P2 stub.

Phase 4 implement pose matching với cosine similarity giữa Pose 33 landmarks.
"""

from __future__ import annotations

from pathlib import Path

from neo_makervigate.core.models import ExperienceMeta
from neo_makervigate.experiences.experience_base import BaseExperience

_QML_PATH = (Path(__file__).parent / "ui.qml").as_posix()


class YogaRobotExperience(BaseExperience):
    """5 tư thế mục tiêu (T-pose, Tree, etc.) — chấm điểm theo similarity. P2 stub."""

    meta = ExperienceMeta(
        id="exp03_yoga_robot",
        title="Yoga Robot",
        subtitle="Robot Yoga",
        age_min=6,
        age_max=12,
        vision_modules=("pose",),
        needs_qwen=False,
        needs_voice=False,
        needs_internet=False,
        icon_path="",
        dev_days=5,
    )

    def get_qml_path(self) -> str:
        return _QML_PATH


EXPERIENCE = YogaRobotExperience
