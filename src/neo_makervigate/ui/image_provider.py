"""CameraImageProvider — phục vụ frame webcam cho QML qua QQuickImageProvider.

QML side gọi: Image { source: "image://camera/preview?bust=42" }
bust param để cache khỏi serve frame cũ — QML tăng property mỗi vài ms.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QImage
from PyQt6.QtQuick import QQuickImageProvider

from neo_makervigate.utils.cv_qt_bridge import cv_bgr_to_qimage

if TYPE_CHECKING:
    from neo_makervigate.core.vision_worker import VisionWorker


class CameraImageProvider(QQuickImageProvider):
    """ID parameter của QML xác định source:
    - "preview" hoặc "preview?bust=N" → raw webcam frame BGR → RGB
    - (P5) "composite?bg=san_dinh" → người + nền AR
    """

    def __init__(self, worker: VisionWorker) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._worker = worker

    def requestImage(
        self,
        id: str | None,
        requestedSize: QSize,
    ) -> tuple[QImage, QSize]:
        _ = id, requestedSize  # not used at P1, sẽ dùng ở P5 cho composite mode
        frame = self._worker.latest_frame_bgr
        if frame is None:
            # Trả ảnh placeholder 320x180 xám
            placeholder = np.full((180, 320, 3), 64, dtype=np.uint8)
            qimg = cv_bgr_to_qimage(placeholder)
            return qimg, qimg.size()

        qimg = cv_bgr_to_qimage(frame)
        return qimg, qimg.size()
