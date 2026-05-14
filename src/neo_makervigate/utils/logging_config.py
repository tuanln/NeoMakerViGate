"""Logging setup — loguru → stderr (dev) + file (NEO One)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from loguru import logger


def setup_logging(log_dir: Path | None = None) -> None:
    """Init loguru. Dev: stderr only. NEO One: stderr + rotating file."""
    logger.remove()

    level = os.environ.get("NEO_MAKERVIGATE_LOG_LEVEL", "INFO").upper()

    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:HH:mm:ss}</green> "
            "<level>{level: <8}</level> "
            "<cyan>{name}:{function}:{line}</cyan> "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_dir / "app.log",
            level=level,
            rotation="10 MB",
            retention=3,
            compression="zip",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        )

    logger.debug(f"Logging initialized at level={level}")
