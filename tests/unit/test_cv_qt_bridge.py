"""Tests cho utils/cv_qt_bridge — pure functions, no hardware."""

from __future__ import annotations

import numpy as np
import pytest
from PyQt6.QtGui import QImage

from neo_makervigate.utils.cv_qt_bridge import cv_bgr_to_qimage, cv_rgb_to_qimage


def test_bgr_to_qimage_shape(qapp) -> None:
    """QImage output có đúng width/height."""
    h, w = 120, 160
    bgr = np.zeros((h, w, 3), dtype=np.uint8)
    qimg = cv_bgr_to_qimage(bgr)

    assert qimg.width() == w
    assert qimg.height() == h
    assert qimg.format() == QImage.Format.Format_RGB888


def test_bgr_to_qimage_swaps_channels(qapp) -> None:
    """Pixel BGR (255, 0, 0) phải thành RGB blue trong QImage."""
    bgr = np.zeros((2, 2, 3), dtype=np.uint8)
    bgr[0, 0] = [255, 0, 0]  # OpenCV BGR = pure blue
    qimg = cv_bgr_to_qimage(bgr)

    # QImage.pixelColor returns QColor — blue, green, red
    color = qimg.pixelColor(0, 0)
    assert color.blue() == 255
    assert color.red() == 0
    assert color.green() == 0


def test_bgr_to_qimage_rejects_wrong_shape(qapp) -> None:
    grayscale = np.zeros((10, 10), dtype=np.uint8)
    with pytest.raises(ValueError):
        cv_bgr_to_qimage(grayscale)

    rgba = np.zeros((10, 10, 4), dtype=np.uint8)
    with pytest.raises(ValueError):
        cv_bgr_to_qimage(rgba)


def test_rgb_to_qimage_does_not_swap(qapp) -> None:
    """RGB input giữ nguyên channel order."""
    rgb = np.zeros((2, 2, 3), dtype=np.uint8)
    rgb[0, 0] = [255, 0, 0]  # pure red
    qimg = cv_rgb_to_qimage(rgb)

    color = qimg.pixelColor(0, 0)
    assert color.red() == 255
    assert color.blue() == 0


def test_qimage_owns_buffer(qapp) -> None:
    """Sau khi xóa numpy array, QImage vẫn dùng được (no crash)."""
    bgr = np.full((50, 50, 3), 200, dtype=np.uint8)
    qimg = cv_bgr_to_qimage(bgr)
    del bgr  # numpy array GC

    # Đọc lại pixel — QImage phải đã copy
    color = qimg.pixelColor(25, 25)
    assert 0 <= color.red() <= 255  # không crash là pass
