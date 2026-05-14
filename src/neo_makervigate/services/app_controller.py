"""AppController — root QObject exposed to QML.

Phase 1 trách nhiệm: cầu nối VisionFrame (Python) ↔ QML qua pyqtProperty.

QML bind:
    Connections { target: app
        function onHandLandmarksChanged() { ... }
    }
hoặc trực tiếp `app.handLandmarks` trong binding.
"""

from __future__ import annotations

import time
from collections import deque
from typing import TYPE_CHECKING, Any

from loguru import logger
from PyQt6.QtCore import (  # type: ignore[attr-defined]
    QObject,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)

from neo_makervigate.utils.signal_bus import SignalBus

if TYPE_CHECKING:
    from neo_makervigate.core.models import VisionFrame


class AppController(QObject):
    """Root facade exposed sang QML qua engine.rootContext().setContextProperty('app', ...)."""

    handLandmarksChanged = pyqtSignal()
    poseLandmarksChanged = pyqtSignal()
    faceLandmarksChanged = pyqtSignal()
    visionFpsChanged = pyqtSignal()
    cameraConnectedChanged = pyqtSignal()
    lastGestureChanged = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._hand_landmarks: list[list[dict[str, float]]] = []
        self._pose_landmarks: list[dict[str, float]] = []
        self._face_landmarks: list[dict[str, float]] = []
        self._vision_fps: float = 0.0
        self._camera_connected: bool = False
        self._last_gesture: str = ""
        self._frame_timestamps: deque[float] = deque(maxlen=30)

        bus = SignalBus.instance()
        bus.vision_frame_ready.connect(self._on_vision_frame)
        bus.vision_camera_ready.connect(self._on_camera_ready)
        bus.vision_camera_error.connect(self._on_camera_error)
        bus.gesture_detected.connect(self._on_gesture)

    # ---- Properties exposed to QML ----

    @pyqtProperty("QVariant", notify=handLandmarksChanged)
    def handLandmarks(self) -> Any:
        return self._hand_landmarks

    @pyqtProperty("QVariant", notify=poseLandmarksChanged)
    def poseLandmarks(self) -> Any:
        return self._pose_landmarks

    @pyqtProperty("QVariant", notify=faceLandmarksChanged)
    def faceLandmarks(self) -> Any:
        return self._face_landmarks

    @pyqtProperty(float, notify=visionFpsChanged)
    def visionFps(self) -> float:
        return self._vision_fps

    @pyqtProperty(bool, notify=cameraConnectedChanged)
    def cameraConnected(self) -> bool:
        return self._camera_connected

    @pyqtProperty(str, notify=lastGestureChanged)
    def lastGesture(self) -> str:
        return self._last_gesture

    # ---- Slots ----

    @pyqtSlot()
    def _on_camera_ready(self) -> None:
        logger.info("Camera ready")
        self._camera_connected = True
        self.cameraConnectedChanged.emit()

    @pyqtSlot(str)
    def _on_camera_error(self, msg: str) -> None:
        logger.error(f"Camera error: {msg}")
        self._camera_connected = False
        self.cameraConnectedChanged.emit()

    @pyqtSlot(str)
    def _on_gesture(self, gesture: str) -> None:
        self._last_gesture = gesture
        self.lastGestureChanged.emit()

    @pyqtSlot(object)
    def _on_vision_frame(self, frame: VisionFrame) -> None:
        """Cập nhật state từ frame mới. P1: hands chính + fps + pose/face nếu có."""
        now = time.perf_counter()
        self._frame_timestamps.append(now)
        if len(self._frame_timestamps) >= 2:
            span = self._frame_timestamps[-1] - self._frame_timestamps[0]
            new_fps = (len(self._frame_timestamps) - 1) / span if span > 0 else 0.0
        else:
            new_fps = 0.0

        # Update properties — chỉ emit changed signal nếu khác
        new_hands = [[{"x": lm.x, "y": lm.y} for lm in hand] for hand in frame.hands]
        if new_hands != self._hand_landmarks:
            self._hand_landmarks = new_hands
            self.handLandmarksChanged.emit()

        new_pose = (
            [{"x": lm.x, "y": lm.y, "visibility": lm.visibility} for lm in frame.pose]
            if frame.pose
            else []
        )
        if new_pose != self._pose_landmarks:
            self._pose_landmarks = new_pose
            self.poseLandmarksChanged.emit()

        new_face = [{"x": lm.x, "y": lm.y} for lm in frame.face] if frame.face else []
        if new_face != self._face_landmarks:
            self._face_landmarks = new_face
            self.faceLandmarksChanged.emit()

        # FPS chỉ emit khi đổi đáng kể (0.1 fps step)
        if abs(new_fps - self._vision_fps) > 0.1:
            self._vision_fps = new_fps
            self.visionFpsChanged.emit()
