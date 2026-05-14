"""TOML settings loader với user override.

Đọc `defaults.toml` (commit), merge với `~/.config/makervigate/config.toml` (user),
override bằng env vars `NEO_MAKERVIGATE_*` (deployment).
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULTS_PATH = Path(__file__).parent / "defaults.toml"
USER_CONFIG_PATH = Path.home() / ".config" / "makervigate" / "config.toml"


@dataclass(frozen=True)
class Settings:
    """Snapshot config tại thời điểm load."""

    app_name: str
    debug: bool
    language: str
    idle_timeout_seconds: int
    fullscreen: bool
    window_width: int
    window_height: int
    vision_source: str  # "engine" | "simulator"
    enabled_experiences: tuple[str, ...]
    raw: dict[str, Any]


def _deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    """Recursive merge: `over` overrides `base`."""
    result = dict(base)
    for key, value in over.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_settings() -> Settings:
    """Load + merge defaults → user → env."""
    with DEFAULTS_PATH.open("rb") as f:
        data = tomllib.load(f)

    if USER_CONFIG_PATH.exists():
        with USER_CONFIG_PATH.open("rb") as f:
            data = _deep_merge(data, tomllib.load(f))

    vision_source = os.environ.get("NEO_MAKERVIGATE_VISION", "engine").lower()
    if vision_source not in ("engine", "simulator"):
        vision_source = "engine"

    app = data.get("app", {})
    ui = data.get("ui", {})
    experiences = data.get("experiences", {})

    return Settings(
        app_name=str(app.get("name", "NeoMakerViGate")),
        debug=bool(app.get("debug", False)),
        language=str(app.get("language", "vi")),
        idle_timeout_seconds=int(app.get("idle_timeout_seconds", 90)),
        fullscreen=bool(ui.get("fullscreen", False)),
        window_width=int(ui.get("window_width", 1920)),
        window_height=int(ui.get("window_height", 1080)),
        vision_source=vision_source,
        enabled_experiences=tuple(experiences.get("enabled", [])),
        raw=data,
    )
