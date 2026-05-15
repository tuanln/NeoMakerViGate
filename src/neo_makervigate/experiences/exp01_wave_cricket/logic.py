"""exp01 Vẫy Chào Dế — P2 stub.

Phase 2 chỉ là placeholder để registry phát hiện và navigation test.
Phase 3 sẽ implement gameplay: WAVE detection → đàn dế bay.
"""

from __future__ import annotations

from pathlib import Path

from neo_makervigate.core.models import ExperienceMeta
from neo_makervigate.experiences.experience_base import BaseExperience

_QML_PATH = (Path(__file__).parent / "ui.qml").as_posix()


class WaveCricketExperience(BaseExperience):
    """Vẫy tay để đàn dế bay ra khỏi luỹ tre. P2 stub — chưa có logic."""

    meta = ExperienceMeta(
        id="exp01_wave_cricket",
        title="Vẫy Chào Dế",
        subtitle="Wave Hello Cricket",
        age_min=4,
        age_max=10,
        vision_modules=("hands",),
        needs_qwen=False,
        needs_voice=False,
        needs_internet=False,
        icon_path="",
        dev_days=3,
    )

    def get_qml_path(self) -> str:
        return _QML_PATH


EXPERIENCE = WaveCricketExperience
