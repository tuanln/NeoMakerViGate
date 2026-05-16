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
