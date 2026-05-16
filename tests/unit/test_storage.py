"""Tests cho utils/storage — LRU cleanup photos directory."""

from __future__ import annotations

import os
from pathlib import Path

from neo_makervigate.utils.storage import cleanup_if_over_limit


def _make_folder_with_data(base: Path, name: str, size_kb: int, mtime: float) -> Path:
    folder = base / name
    folder.mkdir(parents=True, exist_ok=True)
    f = folder / "data.bin"
    f.write_bytes(b"\x00" * (size_kb * 1024))
    os.utime(folder, (mtime, mtime))
    os.utime(f, (mtime, mtime))
    return folder


def test_dir_size_zero_when_empty(tmp_path: Path) -> None:
    assert cleanup_if_over_limit(tmp_path / "empty", max_mb=200) == 0


def test_cleanup_does_nothing_under_limit(tmp_path: Path) -> None:
    _make_folder_with_data(tmp_path, "a", size_kb=10, mtime=1000)
    _make_folder_with_data(tmp_path, "b", size_kb=10, mtime=2000)
    deleted = cleanup_if_over_limit(tmp_path, max_mb=1)
    assert deleted == 0
    assert (tmp_path / "a").exists()
    assert (tmp_path / "b").exists()


def test_cleanup_removes_oldest_folder_first(tmp_path: Path) -> None:
    # 3 folders, each 400KB, limit 1MB (~1024KB) → must remove 1 (oldest)
    _make_folder_with_data(tmp_path, "old", size_kb=400, mtime=1000)
    _make_folder_with_data(tmp_path, "mid", size_kb=400, mtime=2000)
    _make_folder_with_data(tmp_path, "new", size_kb=400, mtime=3000)
    # Total = 1200KB > 1024KB limit → cleanup
    deleted = cleanup_if_over_limit(tmp_path, max_mb=1)
    assert deleted >= 1
    assert not (tmp_path / "old").exists()
    assert (tmp_path / "new").exists()


def test_cleanup_stops_when_under_limit(tmp_path: Path) -> None:
    # 4 folders × 400KB = 1600KB. max=1MB. Must delete enough to get <= 1024KB.
    _make_folder_with_data(tmp_path, "a", size_kb=400, mtime=1000)
    _make_folder_with_data(tmp_path, "b", size_kb=400, mtime=2000)
    _make_folder_with_data(tmp_path, "c", size_kb=400, mtime=3000)
    _make_folder_with_data(tmp_path, "d", size_kb=400, mtime=4000)
    cleanup_if_over_limit(tmp_path, max_mb=1)
    # Newest "d" must survive
    assert (tmp_path / "d").exists()
