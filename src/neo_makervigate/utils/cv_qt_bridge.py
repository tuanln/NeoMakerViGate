"""Bridge giữa OpenCV numpy arrays và Qt QImage.

cv2 dùng BGR, QImage dùng RGB. Cần chuyển và copy để QImage sở hữu buffer
riêng (không giữ tham chiếu vào numpy array có thể bị GC).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from PyQt6.QtGui import QImage


def cv_bgr_to_qimage(frame_bgr: np.ndarray[Any, Any]) -> QImage:
    """Chuyển frame OpenCV BGR (H, W, 3) sang QImage RGB888.

    QImage giữ buffer riêng (deep copy) để khỏi crash khi numpy GC.
    """
    if frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
        raise ValueError(f"Expected BGR image shape (H, W, 3), got {frame_bgr.shape}")

    height, width, _ = frame_bgr.shape
    # cv2 BGR → RGB
    rgb = frame_bgr[..., ::-1].copy()
    # QImage cần contiguous bytes; ép ascontiguousarray cho chắc
    rgb_contig = np.ascontiguousarray(rgb)
    bytes_per_line = 3 * width
    qimg = QImage(
        rgb_contig.tobytes(),
        width,
        height,
        bytes_per_line,
        QImage.Format.Format_RGB888,
    )
    # Buffer đã copy vào tobytes() — QImage giờ độc lập.
    return qimg


def cv_rgb_to_qimage(frame_rgb: np.ndarray[Any, Any]) -> QImage:
    """Chuyển frame RGB (đã convert) sang QImage. Hữu ích nếu đã có RGB."""
    if frame_rgb.ndim != 3 or frame_rgb.shape[2] != 3:
        raise ValueError(f"Expected RGB image shape (H, W, 3), got {frame_rgb.shape}")
    height, width, _ = frame_rgb.shape
    contig = np.ascontiguousarray(frame_rgb)
    bytes_per_line = 3 * width
    return QImage(
        contig.tobytes(),
        width,
        height,
        bytes_per_line,
        QImage.Format.Format_RGB888,
    )
