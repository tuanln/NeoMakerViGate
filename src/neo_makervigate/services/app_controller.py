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
    QTimer,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)

from neo_makervigate.utils.signal_bus import SignalBus

if TYPE_CHECKING:
    from neo_makervigate.core.models import VisionFrame
    from neo_makervigate.services.experience_manager import ExperienceManager


class AppController(QObject):
    """Root facade exposed sang QML qua engine.rootContext().setContextProperty('app', ...)."""

    handLandmarksChanged = pyqtSignal()
    poseLandmarksChanged = pyqtSignal()
    faceLandmarksChanged = pyqtSignal()
    visionFpsChanged = pyqtSignal()
    cameraConnectedChanged = pyqtSignal()
    lastGestureChanged = pyqtSignal()
    experienceMetasChanged = pyqtSignal()
    currentExperienceChanged = pyqtSignal()
    statusChanged = pyqtSignal()
    experienceStateChanged = pyqtSignal()
    photoResultChanged = pyqtSignal()
    photoReviewRequested = pyqtSignal()

    def __init__(self, experience_manager: ExperienceManager | None = None) -> None:
        super().__init__()
        self._hand_landmarks: list[list[dict[str, float]]] = []
        self._pose_landmarks: list[dict[str, float]] = []
        self._face_landmarks: list[dict[str, float]] = []
        self._vision_fps: float = 0.0
        self._camera_connected: bool = False
        self._last_gesture: str = ""
        self._frame_timestamps: deque[float] = deque(maxlen=30)

        # Experience state
        self._experience_manager = experience_manager
        self._current_experience: str = ""
        self._status: str = "idle"  # idle | hub | playing | reviewing
        self._experience_metas: list[dict[str, object]] = (
            experience_manager.all_metas() if experience_manager is not None else []
        )
        self._experience_state: dict[str, object] = {}
        self._render_timer = QTimer(self)
        self._render_timer.setInterval(33)  # ~30Hz
        self._render_timer.timeout.connect(self._poll_render_state)

        self._photo_result: dict[str, object] = {}

        bus = SignalBus.instance()
        bus.vision_frame_ready.connect(self._on_vision_frame)
        bus.vision_camera_ready.connect(self._on_camera_ready)
        bus.vision_camera_error.connect(self._on_camera_error)
        bus.gesture_detected.connect(self._on_gesture)
        bus.experience_started.connect(self._on_experience_started)
        bus.experience_ended.connect(self._on_experience_ended)
        bus.photo_captured.connect(self._on_photo_captured)
        bus.photo_caption_ready.connect(self._on_photo_caption_ready)

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

    @pyqtProperty("QVariant", notify=experienceMetasChanged)
    def experienceMetas(self) -> Any:
        return self._experience_metas

    @pyqtProperty(str, notify=currentExperienceChanged)
    def currentExperience(self) -> str:
        return self._current_experience

    @pyqtProperty(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @pyqtProperty("QVariant", notify=experienceStateChanged)
    def experienceState(self) -> Any:
        return self._experience_state

    @pyqtProperty("QVariant", notify=photoResultChanged)
    def photoResult(self) -> Any:
        return self._photo_result

    # ---- Public slots invokable từ QML ----

    @pyqtSlot(str, result=bool)  # type: ignore[arg-type]
    def selectExperience(self, exp_id: str) -> bool:
        """QML gọi khi user chạm thẻ trên Hub."""
        if self._experience_manager is None:
            logger.warning("selectExperience called but ExperienceManager not set")
            return False
        ok = self._experience_manager.load(exp_id)
        if ok:
            self._status = "playing"
            self.statusChanged.emit()
        return ok

    @pyqtSlot()
    def exitExperience(self) -> None:
        """QML gọi khi user bấm Back từ ExperienceContainerPage."""
        if self._experience_manager is None:
            return
        self._experience_manager.unload()

    @pyqtSlot(result=str)  # type: ignore[arg-type]
    def currentQmlPath(self) -> str:
        """Đường dẫn ui.qml của plugin đang active — Loader binding."""
        if self._experience_manager is None:
            return ""
        inst = self._experience_manager.current_instance
        return inst.get_qml_path() if inst is not None else ""

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

    @pyqtSlot(str)
    def _on_experience_started(self, exp_id: str) -> None:
        self._current_experience = exp_id
        self._status = "playing"
        self.currentExperienceChanged.emit()
        self.statusChanged.emit()
        self._render_timer.start()

    @pyqtSlot(str, dict)
    def _on_experience_ended(self, exp_id: str, summary: dict[str, object]) -> None:
        _ = exp_id, summary
        self._render_timer.stop()
        self._current_experience = ""
        self._status = "hub"
        self._experience_state = {}
        self.currentExperienceChanged.emit()
        self.statusChanged.emit()
        self.experienceStateChanged.emit()

    def _poll_render_state(self) -> None:
        if self._experience_manager is None:
            return
        inst = self._experience_manager.current_instance
        if inst is None:
            return
        try:
            new_state = inst.render_state()
        except Exception as e:
            logger.warning(f"render_state() raised: {e}")
            return
        if new_state != self._experience_state:
            self._experience_state = new_state
            self.experienceStateChanged.emit()

    @pyqtSlot(object)
    def _on_photo_captured(self, result: Any) -> None:
        if not getattr(result, "success", False):
            logger.warning(
                f"Photo capture failed: {getattr(result, 'error_message', 'unknown')}"
            )
            return
        self._photo_result = {
            "photo_id": result.photo_id,
            "original_path": str(result.original_path) if result.original_path else "",
            "composite_path": str(result.composite_path) if result.composite_path else "",
            "qr_path": str(result.qr_path) if result.qr_path else "",
            "download_url": result.download_url or "",
            "experience_id": result.experience_id,
            "caption": "",  # populated by photo_caption_ready signal
        }
        self.photoResultChanged.emit()
        self.photoReviewRequested.emit()

    @pyqtSlot(str, str)
    def _on_photo_caption_ready(self, photo_id: str, caption: str) -> None:
        if self._photo_result.get("photo_id") != photo_id:
            return
        self._photo_result = dict(self._photo_result)
        self._photo_result["caption"] = caption
        self.photoResultChanged.emit()

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
