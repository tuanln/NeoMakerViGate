"""Smoke test cho registry — Phase 0 baseline.

Phase 0 chưa có plugin nào, registry rỗng nhưng không crash.
"""

from __future__ import annotations

from neo_makervigate.experiences.registry import discover_experiences


def test_discover_does_not_crash_when_empty() -> None:
    registry = discover_experiences()
    assert isinstance(registry, dict)
