"""Tests cho core/photo_capture — JPG snapshot saving."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from neo_makervigate.core.photo_capture import PhotoCapture


def _make_frame(w: int = 1280, h: int = 720) -> np.ndarray[Any, Any]:
    frame: np.ndarray[Any, Any] = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:, :, 0] = 255
    return frame


def test_make_photo_id_format(tmp_path: Path) -> None:
    pc = PhotoCapture(base_dir=tmp_path)
    pid = pc.make_photo_id()
    assert pid.startswith("photo_")
    parts = pid.split("_")
    assert len(parts) == 3
    assert len(parts[1]) == 8
    assert len(parts[2]) == 6


def test_make_photo_id_with_experience(tmp_path: Path) -> None:
    pc = PhotoCapture(base_dir=tmp_path)
    pid = pc.make_photo_id("exp03_yoga_robot")
    assert pid.endswith("_exp03_yoga_robot")
    assert pid.startswith("photo_")


def test_make_photo_dir_creates_folder(tmp_path: Path) -> None:
    pc = PhotoCapture(base_dir=tmp_path)
    photo_id = "photo_test"
    d = pc.make_photo_dir(photo_id)
    assert d.exists()
    assert d.is_dir()
    assert d.parent == tmp_path


def test_save_original_writes_jpg(tmp_path: Path) -> None:
    pc = PhotoCapture(base_dir=tmp_path)
    photo_dir = pc.make_photo_dir("photo_t1")
    frame = _make_frame()
    path = pc.save_original(frame, photo_dir)
    assert path == photo_dir / "original.jpg"
    assert path.exists()
    with open(path, "rb") as f:
        header = f.read(3)
    assert header[:3] == b"\xff\xd8\xff"


def test_save_original_with_invalid_path_raises(tmp_path: Path) -> None:
    pc = PhotoCapture(base_dir=tmp_path)
    frame = _make_frame()
    bad_dir = tmp_path / "does_not_exist_xyz"
    with pytest.raises(Exception):  # noqa: B017
        pc.save_original(frame, bad_dir)


def test_save_original_jpg_size_reasonable(tmp_path: Path) -> None:
    """1280x720 solid color JPG should be < 100KB at quality 90."""
    pc = PhotoCapture(base_dir=tmp_path)
    photo_dir = pc.make_photo_dir("photo_t2")
    frame = _make_frame()
    path = pc.save_original(frame, photo_dir)
    size = path.stat().st_size
    assert 1000 < size < 100_000, f"JPG size {size} out of expected range"


def test_save_composite_with_full_mask_returns_foreground(tmp_path: Path) -> None:
    """Mask all 1 (full foreground) → composite ≈ foreground frame."""
    import cv2
    pc = PhotoCapture(base_dir=tmp_path)
    photo_dir = pc.make_photo_dir("photo_t_full")
    fg = np.zeros((360, 640, 3), dtype=np.uint8)
    fg[:, :, 2] = 255  # red (BGR)
    bg_path = tmp_path / "bg.png"
    bg = np.zeros((360, 640, 3), dtype=np.uint8)
    bg[:, :, 0] = 255  # blue
    cv2.imwrite(str(bg_path), bg)
    mask = np.ones((360, 640), dtype=np.float32)

    path = pc.save_composite(fg, mask, bg_path, photo_dir)
    assert path == photo_dir / "composite.jpg"
    assert path.exists()
    out = cv2.imread(str(path))
    assert out[180, 320, 2] > 200, f"expected red center, got BGR={out[180, 320]}"
    assert out[180, 320, 0] < 50, f"expected no blue, got BGR={out[180, 320]}"


def test_save_composite_with_zero_mask_returns_background_only(tmp_path: Path) -> None:
    """Mask all 0 (no foreground) → composite ≈ background."""
    import cv2
    pc = PhotoCapture(base_dir=tmp_path)
    photo_dir = pc.make_photo_dir("photo_t_zero")
    fg = np.zeros((360, 640, 3), dtype=np.uint8)
    fg[:, :, 2] = 255
    bg_path = tmp_path / "bg2.png"
    bg = np.zeros((360, 640, 3), dtype=np.uint8)
    bg[:, :, 0] = 255
    cv2.imwrite(str(bg_path), bg)
    mask = np.zeros((360, 640), dtype=np.float32)

    path = pc.save_composite(fg, mask, bg_path, photo_dir)
    out = cv2.imread(str(path))
    assert out[180, 320, 0] > 200
    assert out[180, 320, 2] < 50


def test_save_composite_writes_jpg(tmp_path: Path) -> None:
    """Composite file is valid JPG."""
    import cv2
    pc = PhotoCapture(base_dir=tmp_path)
    photo_dir = pc.make_photo_dir("photo_t_jpg")
    fg = np.zeros((360, 640, 3), dtype=np.uint8)
    fg[:, :, 1] = 200
    bg_path = tmp_path / "bg3.png"
    bg = np.zeros((360, 640, 3), dtype=np.uint8)
    bg[:, :, 1] = 100
    cv2.imwrite(str(bg_path), bg)
    mask = np.ones((360, 640), dtype=np.float32) * 0.5

    path = pc.save_composite(fg, mask, bg_path, photo_dir)
    assert path.exists()
    with open(path, "rb") as f:
        header = f.read(3)
    assert header[:3] == b"\xff\xd8\xff"


def test_list_source_photos_empty_when_dir_missing(tmp_path: Path) -> None:
    from neo_makervigate.core.photo_capture import list_source_photos
    result = list_source_photos(tmp_path / "nonexistent")
    assert result == []


def test_list_source_photos_returns_jpg_png(tmp_path: Path) -> None:
    from neo_makervigate.core.photo_capture import list_source_photos
    (tmp_path / "a.jpg").write_bytes(b"\xff\xd8\xff")
    (tmp_path / "b.png").write_bytes(b"\x89PNG\r\n")
    (tmp_path / "c.txt").write_text("not image")
    result = list_source_photos(tmp_path)
    names = sorted(p.name for p in result)
    assert names == ["a.jpg", "b.png"]


def test_list_source_photos_sorted(tmp_path: Path) -> None:
    from neo_makervigate.core.photo_capture import list_source_photos
    for n in ("zebra.jpg", "apple.jpg", "mango.png"):
        (tmp_path / n).write_bytes(b"\xff\xd8\xff")
    result = list_source_photos(tmp_path)
    assert [p.name for p in result] == ["apple.jpg", "mango.png", "zebra.jpg"]
