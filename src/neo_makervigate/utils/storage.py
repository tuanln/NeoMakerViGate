"""LRU cleanup cho photos directory.

cleanup_if_over_limit():
  1. Đo tổng size photos/
  2. Nếu > MAX_PHOTOS_STORAGE_MB: xóa folder cũ nhất (theo mtime) cho tới khi < limit
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

MAX_PHOTOS_STORAGE_MB = 200


def _dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def cleanup_if_over_limit(photos_base: Path, max_mb: int = MAX_PHOTOS_STORAGE_MB) -> int:
    """Trả về số folder đã xóa. LRU: xóa folder có mtime cũ nhất trước."""
    if not photos_base.exists():
        return 0
    total_bytes = _dir_size_bytes(photos_base)
    limit_bytes = max_mb * 1024 * 1024
    if total_bytes <= limit_bytes:
        return 0
    folders = sorted(
        [d for d in photos_base.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
    )
    deleted = 0
    for folder in folders:
        if total_bytes <= limit_bytes:
            break
        folder_size = _dir_size_bytes(folder)
        for f in folder.rglob("*"):
            if f.is_file():
                f.unlink()
        folder.rmdir()
        total_bytes -= folder_size
        deleted += 1
        logger.info(f"Cleaned up photo folder: {folder.name}")
    return deleted
