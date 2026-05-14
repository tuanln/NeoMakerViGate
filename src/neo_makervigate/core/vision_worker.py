"""VisionWorker — chạy VisionSource trong QThread riêng.

Emit:
    SignalBus.vision_camera_ready khi đã start thành công
    SignalBus.vision_camera_error nếu lỗi khi start hoặc disconnect runtime
    SignalBus.vision_frame_ready với mỗi VisionFrame (kèm raw frame trong cache)

VisionWorker giữ frame BGR mới nhất ở thuộc tính `latest_frame_bgr` để
CameraImageProvider đọc khi QML request ảnh.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

import numpy as np
from loguru import logger
from PyQt6.QtCore import QThread

from neo_makervigate.utils.signal_bus import SignalBus

if TYPE_CHECKING:
    from neo_makervigate.core.models import VisionFrame
    from neo_makervigate.core.vision_engine import VisionSource


class VisionWorker(QThread):
    """QThread driver cho VisionSource (Engine hoặc Simulator)."""

    def __init__(self, source: VisionSource, initial_modules: list[str] | None = None) -> None:
        super().__init__()
        self._source = source
        self._initial_modules = initial_modules or []
        self._running = False
        self._lock = threading.Lock()
        self._latest_frame_bgr: np.ndarray[Any, Any] | None = None
        self._latest_vision_frame: VisionFrame | None = None
        self._fps_samples: list[float] = []

    @property
    def latest_frame_bgr(self) -> np.ndarray[Any, Any] | None:
        """Last raw BGR frame — đọc an toàn từ thread khác."""
        with self._lock:
            return None if self._latest_frame_bgr is None else self._latest_frame_bgr.copy()

    def set_active_modules(self, modules: list[str]) -> None:
        """Thread-safe API để ExperienceManager đổi module."""
        self._source.set_active_modules(modules)

    def stop(self) -> None:
        self._running = False
        self.wait(2000)

    def run(self) -> None:
        bus = SignalBus.instance()
        try:
            self._source.start()
            if self._initial_modules:
                self._source.set_active_modules(self._initial_modules)
            bus.vision_camera_ready.emit()
        except Exception as e:
            logger.exception(f"VisionWorker start failed: {e}")
            bus.vision_camera_error.emit(str(e))
            return

        self._running = True
        consecutive_fails = 0
        logger.info("VisionWorker loop started")

        while self._running:
            ok, frame_bgr, vf = self._source.read()
            if not ok:
                consecutive_fails += 1
                if consecutive_fails > 30:
                    logger.error("VisionWorker: 30+ consecutive read failures")
                    bus.vision_camera_error.emit("Webcam read failed repeatedly")
                    break
                self.msleep(33)
                continue
            consecutive_fails = 0

            with self._lock:
                self._latest_frame_bgr = frame_bgr
                self._latest_vision_frame = vf

            if vf is not None:
                bus.vision_frame_ready.emit(vf)

        try:
            self._source.stop()
        except Exception as e:
            logger.warning(f"VisionSource.stop() raised: {e}")
        logger.info("VisionWorker loop ended")
