"""VisionSimulator — phát clip mp4 đã ghi sẵn, hoặc khung hình giả lập.

Dùng cho dev macOS không có webcam thật / NEO One xa, hoặc test CI offscreen.
Implement VisionSource Protocol giống VisionEngine.

Hai chế độ:
1. **Clip mode** (NEO_MAKERVIGATE_SIM_CLIP=path/to/clip.mp4): play loop video file
2. **Blank mode** (mặc định): trả khung đen + landmarks rỗng — đủ để UI test

Module active được tôn trọng nhưng không thực sự chạy MediaPipe — chỉ đảm bảo
API tương thích với VisionEngine.
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from loguru import logger

from neo_makervigate.core.models import VisionFrame


class VisionSimulator:
    """Phát clip mp4 hoặc khung trắng — đủ để UI develop không cần webcam."""

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        clip_path: Path | None = None,
    ) -> None:
        self._width = width
        self._height = height
        self._clip_path = clip_path or self._discover_clip()
        self._cap: cv2.VideoCapture | None = None
        self._active: list[str] = []
        self._frame_count = 0
        self._clock_start: float = 0.0

    def _discover_clip(self) -> Path | None:
        env = os.environ.get("NEO_MAKERVIGATE_SIM_CLIP")
        if env:
            p = Path(env)
            if p.exists():
                return p
            logger.warning(f"NEO_MAKERVIGATE_SIM_CLIP path not found: {env}")
        return None

    # ---- VisionSource Protocol ----

    def start(self) -> None:
        if self._clip_path is not None:
            cap = cv2.VideoCapture(str(self._clip_path))
            if cap.isOpened():
                self._cap = cap
                logger.info(f"VisionSimulator playing clip: {self._clip_path}")
            else:
                logger.warning(f"Cannot open clip {self._clip_path} — falling back to blank")
                self._cap = None
        else:
            logger.info("VisionSimulator running in BLANK mode (no clip)")
        self._clock_start = time.perf_counter()

    def stop(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._active = []

    def set_active_modules(self, modules: list[str]) -> None:
        self._active = list(modules)
        logger.debug(f"VisionSimulator active modules: {modules}")

    def read(self) -> tuple[bool, np.ndarray[Any, Any] | None, VisionFrame | None]:
        self._frame_count += 1

        if self._cap is not None:
            ret, frame_bgr = self._cap.read()
            if not ret:
                # Loop video
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame_bgr = self._cap.read()
                if not ret:
                    return False, None, None
            # Resize to target nếu lệch
            h, w = frame_bgr.shape[:2]
            if (w, h) != (self._width, self._height):
                frame_bgr = cv2.resize(frame_bgr, (self._width, self._height))
        else:
            # Blank mode — khung xám đen với 1 dòng text identifier
            frame_bgr = np.full((self._height, self._width, 3), 30, dtype=np.uint8)
            text = f"VisionSimulator BLANK  frame={self._frame_count}"
            cv2.putText(
                frame_bgr,
                text,
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (200, 200, 200),
                2,
            )

        h, w = frame_bgr.shape[:2]
        vf = VisionFrame(
            timestamp=datetime.now(),
            width=w,
            height=h,
            # Simulator không sinh landmarks giả ở P1 — sẽ thêm ở P3 nếu cần
            has_person=False,
        )
        # Throttle ~30fps để mô phỏng webcam
        elapsed = time.perf_counter() - self._clock_start
        expected = self._frame_count / 30.0
        if expected > elapsed:
            time.sleep(min(0.05, expected - elapsed))

        return True, frame_bgr, vf
