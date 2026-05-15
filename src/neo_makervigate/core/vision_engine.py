"""VisionEngine — bọc MediaPipe Tasks API.

Hỗ trợ 4 module: hands, pose, face, selfie. P1 chỉ implement hands; P4 thêm
pose; P6 thêm selfie+face.

set_active_modules() đóng/mở module theo nhu cầu trải nghiệm — quan trọng
trên NEO One 2GB không chạy nổi cả 4 module cùng lúc.
"""

from __future__ import annotations

import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

import cv2
import mediapipe as mp
import numpy as np
from loguru import logger
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from neo_makervigate.core.models import Landmark, VisionFrame

# Model registry — URL + đường dẫn local. Tải tự động bằng ensure_models().
MODELS_DIR = Path(__file__).parent.parent.parent.parent / "models" / "mediapipe"
_MODEL_URLS: dict[str, str] = {
    "hands": (
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/latest/hand_landmarker.task"
    ),
    "pose": (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
    ),
    "face": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/latest/face_landmarker.task"
    ),
    "selfie": (
        "https://storage.googleapis.com/mediapipe-models/selfie_segmenter/"
        "selfie_segmenter/float16/latest/selfie_segmenter.tflite"
    ),
}


def model_path(name: str) -> Path:
    """Trả về đường dẫn local cho model."""
    suffix = ".tflite" if name == "selfie" else ".task"
    return MODELS_DIR / f"{name}_landmarker{suffix}"


def ensure_model(name: str) -> Path:
    """Tải model nếu chưa có. Trả về path."""
    if name not in _MODEL_URLS:
        raise ValueError(f"Unknown model: {name}")
    path = model_path(name)
    if path.exists() and path.stat().st_size > 100_000:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Downloading MediaPipe model: {name} → {path}")
    urllib.request.urlretrieve(_MODEL_URLS[name], path)
    logger.info(f"  ↳ {path.stat().st_size / 1024:.0f} KB")
    return path


class VisionSource(Protocol):
    """Interface chung — VisionEngine (webcam thật) hoặc VisionSimulator."""

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def set_active_modules(self, modules: list[str]) -> None: ...
    def read(self) -> tuple[bool, np.ndarray[Any, Any] | None, VisionFrame | None]: ...


class VisionEngine:
    """Đọc webcam + chạy MediaPipe trên CPU/GPU. Implement VisionSource Protocol.

    Pattern dùng:
        engine = VisionEngine(webcam_index=0, width=1280, height=720)
        engine.set_active_modules(["hands"])
        engine.start()
        while running:
            ok, frame, vf = engine.read()
            if ok:
                # frame: BGR numpy; vf: VisionFrame với landmarks
                ...
        engine.stop()
    """

    def __init__(
        self,
        webcam_index: int = 0,
        width: int = 1280,
        height: int = 720,
        pose_model_complexity: int = 1,
    ) -> None:
        self._webcam_index = webcam_index
        self._width = width
        self._height = height
        self._pose_complexity = pose_model_complexity
        self._cap: cv2.VideoCapture | None = None
        self._detectors: dict[str, object] = {}
        self._active: list[str] = []
        self._clock_start: float = 0.0
        # RLock bảo vệ _cap/_detectors/_active. Main thread gọi
        # set_active_modules() và stop() trong khi worker thread chạy read().
        # Race trước đây: pop("hands") trước khi update _active gây KeyError
        # trong read() khi check "hands" in _active → True nhưng dict đã rỗng.
        self._lock = threading.RLock()

    # ---- VisionSource Protocol ----

    def start(self) -> None:
        """Mở webcam. Module được kích hoạt riêng qua set_active_modules()."""
        with self._lock:
            if self._cap is not None:
                return
            cap = cv2.VideoCapture(self._webcam_index)
            if not cap.isOpened():
                raise RuntimeError(f"Không mở được webcam index {self._webcam_index}")
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
            self._cap = cap
            self._clock_start = time.perf_counter()
            actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.info(
                f"Webcam opened: {actual_w}x{actual_h} (requested {self._width}x{self._height})"
            )

    def stop(self) -> None:
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
            # Update _active trước khi close detectors để giữ invariant
            # "name in _active ⇒ name in _detectors" cho mọi reader.
            self._active = []
            for det in self._detectors.values():
                close = getattr(det, "close", None)
                if close is not None:
                    close()
            self._detectors.clear()

    def set_active_modules(self, modules: list[str]) -> None:
        """Đóng module không cần, mở module cần. An toàn gọi nhiều lần.

        Thứ tự thao tác giữ invariant `name in _active ⇒ name in _detectors`:
          1) tạo detector mới (additions)
          2) cập nhật _active = modules
          3) đóng detector cũ (removals)
        """
        with self._lock:
            new_set = set(modules)
            old_set = set(self._active)

            # 1) Mở module mới TRƯỚC khi expose qua _active
            for name in new_set - old_set:
                self._detectors[name] = self._create_detector(name)
                logger.debug(f"Opened module: {name}")

            # 2) Update _active — sau bước này reader chỉ thấy module hợp lệ
            self._active = list(modules)

            # 3) Đóng module bỏ — sau khi reader đã không còn check tên đó
            for name in old_set - new_set:
                det = self._detectors.pop(name, None)
                if det is not None:
                    close = getattr(det, "close", None)
                    if close is not None:
                        close()
                    logger.debug(f"Closed module: {name}")

    def read(self) -> tuple[bool, np.ndarray[Any, Any] | None, VisionFrame | None]:
        """Đọc 1 khung hình + chạy mọi module active. Trả về (ok, bgr_frame, VisionFrame).

        Toàn bộ phương thức chạy dưới `_lock` để loại race với set_active_modules()
        và stop() từ thread khác. MediaPipe inference ~30ms — main thread gọi
        set_active_modules sẽ đợi tối đa 1 frame, chấp nhận được.
        """
        with self._lock:
            if self._cap is None:
                return False, None, None
            ret, frame_bgr = self._cap.read()
            if not ret or frame_bgr is None:
                return False, None, None

            ts_ms = int((time.perf_counter() - self._clock_start) * 1000)
            h, w = frame_bgr.shape[:2]
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            vf = VisionFrame(timestamp=datetime.now(), width=w, height=h)

            for name in self._active:
                detector = self._detectors.get(name)
                if detector is None:
                    continue
                result = detector.detect_for_video(mp_image, ts_ms)  # type: ignore[attr-defined]
                if name == "hands" and result.hand_landmarks:
                    vf.hands = [
                        [Landmark(x=lm.x, y=lm.y, z=lm.z) for lm in hand]
                        for hand in result.hand_landmarks
                    ]
                    vf.has_person = True
                elif name == "pose" and result.pose_landmarks:
                    vf.pose = [
                        Landmark(x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility)
                        for lm in result.pose_landmarks[0]
                    ]
                    vf.has_person = True
                elif name == "face" and result.face_landmarks:
                    vf.face = [
                        Landmark(x=lm.x, y=lm.y, z=lm.z) for lm in result.face_landmarks[0]
                    ]
                    vf.has_person = True

            return True, frame_bgr, vf

    # ---- Internal ----

    def _create_detector(self, name: str) -> object:
        path = ensure_model(name)
        base = mp_python.BaseOptions(model_asset_path=str(path))

        if name == "hands":
            return mp_vision.HandLandmarker.create_from_options(
                mp_vision.HandLandmarkerOptions(
                    base_options=base,
                    running_mode=mp_vision.RunningMode.VIDEO,
                    num_hands=2,
                    min_hand_detection_confidence=0.5,
                    min_hand_presence_confidence=0.5,
                    min_tracking_confidence=0.5,
                )
            )
        if name == "pose":
            return mp_vision.PoseLandmarker.create_from_options(
                mp_vision.PoseLandmarkerOptions(
                    base_options=base,
                    running_mode=mp_vision.RunningMode.VIDEO,
                    num_poses=1,
                    min_pose_detection_confidence=0.5,
                    min_pose_presence_confidence=0.5,
                    min_tracking_confidence=0.5,
                )
            )
        if name == "face":
            return mp_vision.FaceLandmarker.create_from_options(
                mp_vision.FaceLandmarkerOptions(
                    base_options=base,
                    running_mode=mp_vision.RunningMode.VIDEO,
                    num_faces=1,
                    min_face_detection_confidence=0.5,
                    min_face_presence_confidence=0.5,
                    min_tracking_confidence=0.5,
                )
            )
        raise ValueError(f"Module not yet implemented: {name}")
