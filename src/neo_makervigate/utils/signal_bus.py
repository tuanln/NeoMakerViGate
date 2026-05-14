"""Centralized SignalBus — kế thừa pattern NeoStopMotion.

Mọi module giao tiếp qua đây thay vì gọi trực tiếp lẫn nhau. Đây là hub trung tâm.
Phase 0 chỉ khai báo các signal khung; mỗi phase sau sẽ wire-up dần.
"""

from __future__ import annotations

from typing import ClassVar

from PyQt6.QtCore import QObject, pyqtSignal


class SignalBus(QObject):
    """Singleton SignalBus. Truy cập qua `SignalBus.instance()`."""

    _instance: ClassVar[SignalBus | None] = None

    # ── Vision ───────────────────────────────────────────────────
    vision_frame_ready = pyqtSignal(object)  # VisionFrame (P1)
    vision_camera_ready = pyqtSignal()
    vision_camera_error = pyqtSignal(str)
    gesture_detected = pyqtSignal(str)

    # ── Experience ──────────────────────────────────────────────
    experience_selected = pyqtSignal(str)
    experience_started = pyqtSignal(str)
    experience_ended = pyqtSignal(str, dict)
    score_updated = pyqtSignal(int)
    experience_progress = pyqtSignal(float)

    # ── Photo ───────────────────────────────────────────────────
    photo_capture_requested = pyqtSignal(dict)
    photo_captured = pyqtSignal(object)  # PhotoResult (P5)

    # ── Qwen ────────────────────────────────────────────────────
    qwen_request_started = pyqtSignal(str)
    qwen_response_ready = pyqtSignal(str)
    qwen_failed = pyqtSignal(str)

    # ── Share ───────────────────────────────────────────────────
    share_qr_ready = pyqtSignal(str, str)  # url, qr_path

    # ── App ─────────────────────────────────────────────────────
    status_message = pyqtSignal(str, str)  # level, message
    idle_timeout = pyqtSignal()

    @classmethod
    def instance(cls) -> SignalBus:
        """Lazy singleton — Qt yêu cầu QObject chỉ init một lần qua __init__ chuẩn,
        nên ta giữ instance ở class-level thay vì override __new__."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Test helper — xóa singleton giữa các test."""
        if cls._instance is not None:
            cls._instance.deleteLater()
            cls._instance = None
