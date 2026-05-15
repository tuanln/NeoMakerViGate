"""exp06 Photo Booth Cổng Làng — P2 stub.

Phase 5 implement PhotoCapture + ShareServer; Phase 6 implement Selfie Seg
composite + Qwen caption + QR.
"""

from __future__ import annotations

from pathlib import Path

from neo_makervigate.core.models import ExperienceMeta
from neo_makervigate.experiences.experience_base import BaseExperience

_QML_PATH = (Path(__file__).parent / "ui.qml").as_posix()


class PhotoBoothExperience(BaseExperience):
    """Chụp ảnh + ghép nền AR + Qwen caption + chia sẻ qua QR. P2 stub."""

    meta = ExperienceMeta(
        id="exp06_photo_booth",
        title="Photo Booth Cổng Làng",
        subtitle="Village Gate Photo Booth",
        age_min=4,
        age_max=14,
        vision_modules=("selfie", "pose"),
        needs_qwen=True,
        needs_voice=False,
        needs_internet=False,  # auto fallback local
        icon_path="",
        dev_days=7,
    )

    def get_qml_path(self) -> str:
        return _QML_PATH


EXPERIENCE = PhotoBoothExperience
