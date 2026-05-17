"""PhotoCapture — lưu khung hình hiện tại thành JPG.

Stateless: nhận BGR frame + thư mục đích, lưu original.jpg.
Không truy cập webcam trực tiếp — frame được pass từ VisionWorker.latest_frame_bgr.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

DEFAULT_PHOTOS_DIR = Path.home() / "makervigate" / "photos"
JPG_QUALITY = 90


class PhotoCapture:
    """Helper class — pure functions wrapped for testability."""

    def __init__(self, base_dir: Path = DEFAULT_PHOTOS_DIR) -> None:
        self._base = base_dir
        self._base.mkdir(parents=True, exist_ok=True)

    def make_photo_id(self, experience_id: str = "") -> str:
        """Sinh photo_id từ timestamp + experience_id."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{experience_id}" if experience_id else ""
        return f"photo_{ts}{suffix}"

    def make_photo_dir(self, photo_id: str) -> Path:
        d = self._base / photo_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_original(
        self,
        frame_bgr: np.ndarray[Any, Any],
        photo_dir: Path,
    ) -> Path:
        """Lưu frame BGR thành original.jpg ở photo_dir/. Trả về path."""
        if not photo_dir.exists():
            raise FileNotFoundError(f"photo_dir does not exist: {photo_dir}")
        path = photo_dir / "original.jpg"
        ok = cv2.imwrite(str(path), frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, JPG_QUALITY])
        if not ok:
            raise RuntimeError(f"cv2.imwrite failed: {path}")
        return path

    def save_composite(
        self,
        frame_bgr: np.ndarray[Any, Any],
        mask: np.ndarray[Any, Any],
        background_path: Path,
        photo_dir: Path,
    ) -> Path:
        """Composite foreground (trẻ) vào background, lưu composite.jpg.

        Soft mask + Gaussian blur edges để cạnh mượt.
        - frame_bgr: BGR HxWx3 uint8
        - mask: float32 HxW with values [0..1] (1 = person, 0 = background)
        - background_path: PNG/JPG to use as background
        - photo_dir: output directory
        """
        if not photo_dir.exists():
            raise FileNotFoundError(f"photo_dir does not exist: {photo_dir}")
        h, w = frame_bgr.shape[:2]
        bg = cv2.imread(str(background_path))
        if bg is None:
            raise FileNotFoundError(f"background not found: {background_path}")
        bg = cv2.resize(bg, (w, h))

        # Resize mask to frame dimensions if needed
        if mask.shape != (h, w):
            mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_LINEAR)
        # Soft edges via Gaussian blur
        mask_blurred = cv2.GaussianBlur(mask, (15, 15), 0).astype(np.float32)
        mask_3ch = np.stack([mask_blurred] * 3, axis=-1)

        fg = frame_bgr.astype(np.float32)
        bg_f = bg.astype(np.float32)
        composite = (fg * mask_3ch + bg_f * (1 - mask_3ch)).astype(np.uint8)

        path = photo_dir / "composite.jpg"
        ok = cv2.imwrite(str(path), composite, [cv2.IMWRITE_JPEG_QUALITY, JPG_QUALITY])
        if not ok:
            raise RuntimeError(f"cv2.imwrite failed: {path}")
        return path
