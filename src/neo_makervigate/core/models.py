"""Dataclasses chung — VisionFrame, ExperienceMeta, PhotoResult."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np


class AppStatus(StrEnum):
    IDLE = "idle"
    HUB = "hub"
    PLAYING = "playing"
    REVIEWING = "reviewing"
    ERROR = "error"


class Gesture(StrEnum):
    WAVE = "WAVE"
    POINT = "POINT"
    OPEN_PALM = "OPEN_PALM"
    V_SIGN = "V_SIGN"
    SMILE = "SMILE"
    T_POSE = "T_POSE"


@dataclass(frozen=True)
class Landmark:
    """Một điểm landmark chuẩn hóa 0.0-1.0."""

    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0


@dataclass
class VisionFrame:
    """Một khung hình đã qua MediaPipe.

    Populated by VisionEngine ở P1. Pose/hands/face có thể rỗng tùy module active.
    """

    timestamp: datetime
    width: int
    height: int
    pose: list[Landmark] = field(default_factory=list)
    hands: list[list[Landmark]] = field(default_factory=list)
    face: list[Landmark] = field(default_factory=list)
    has_person: bool = False
    raw_jpeg_path: Path | None = None
    selfie_mask: np.ndarray[Any, Any] | None = None


@dataclass(frozen=True)
class ExperienceMeta:
    """Metadata declared bởi mỗi experience plugin."""

    id: str
    title: str
    subtitle: str
    age_min: int
    age_max: int
    vision_modules: tuple[str, ...]
    needs_qwen: bool = False
    needs_voice: bool = False
    needs_internet: bool = False
    icon_path: str = ""
    dev_days: int = 0


@dataclass
class ExperienceSummary:
    """Kết quả một lượt chơi — KPI logging."""

    experience_id: str
    started_at: datetime
    ended_at: datetime
    duration_seconds: float
    score: int = 0
    completed: bool = False
    photo_taken: bool = False


@dataclass
class PhotoResult:
    """Kết quả chụp ảnh — emitted bởi PhotoCapture (P5)."""

    success: bool
    photo_id: str
    original_path: Path | None = None
    composite_path: Path | None = None
    caption: str = ""
    qr_path: Path | None = None
    download_url: str | None = None
    experience_id: str = ""
    error_message: str | None = None
