"""Smoke test cho config loader — Phase 0."""

from __future__ import annotations

from neo_makervigate.config.settings import load_settings


def test_load_defaults() -> None:
    settings = load_settings()

    assert settings.app_name == "NeoMakerViGate"
    assert settings.language == "vi"
    assert "exp01_wave_cricket" in settings.enabled_experiences
    assert "exp03_yoga_robot" in settings.enabled_experiences
    assert "exp06_photo_booth" in settings.enabled_experiences
    assert settings.idle_timeout_seconds == 90


def test_vision_source_default() -> None:
    settings = load_settings()
    assert settings.vision_source in ("engine", "simulator")
