"""Tests cho experiences/registry — discover plugin tự động.

P2: 3 stub plugins (exp01, exp03, exp06) phải được discover.
"""

from __future__ import annotations

from neo_makervigate.experiences.registry import discover_experiences


def test_discover_returns_dict() -> None:
    registry = discover_experiences()
    assert isinstance(registry, dict)


def test_discover_finds_three_stubs() -> None:
    registry = discover_experiences()
    assert "exp01_wave_cricket" in registry
    assert "exp03_yoga_robot" in registry
    assert "exp06_photo_booth" in registry
    assert len(registry) >= 3


def test_discovered_classes_have_meta() -> None:
    registry = discover_experiences()
    for exp_id, cls in registry.items():
        assert hasattr(cls, "meta"), f"{exp_id} thiếu class attribute meta"
        assert cls.meta.id == exp_id, f"{exp_id} meta.id mismatch: {cls.meta.id}"
        assert cls.meta.title, f"{exp_id} thiếu meta.title"
        assert cls.meta.vision_modules, f"{exp_id} thiếu vision_modules"


def test_discovered_classes_instantiable() -> None:
    registry = discover_experiences()
    for exp_id, cls in registry.items():
        instance = cls()
        assert instance is not None, f"{exp_id} instantiation failed"
        # BaseExperience.on_enter mặc định no-op
        instance.on_enter()
        # get_qml_path phải trỏ tới file ui.qml tồn tại
        from pathlib import Path

        qml_path = Path(instance.get_qml_path())
        assert qml_path.exists(), f"{exp_id} ui.qml not found at {qml_path}"
        instance.on_exit()
