"""Tests cho WaveCricketExperience — gameplay logic độc lập, không Qt/QML."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from neo_makervigate.core.models import Landmark, VisionFrame
from neo_makervigate.experiences.exp01_wave_cricket.logic import (
    Phase,
    WaveCricketExperience,
)


class _FakeClock:
    """Fake clock thay time.perf_counter để test phase transitions."""

    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def _make_frame(wrist_x: float = 0.5, wrist_y: float = 0.5) -> VisionFrame:
    wrist = Landmark(x=wrist_x, y=wrist_y, z=0.0)
    hand = [wrist] + [Landmark(x=wrist_x, y=wrist_y) for _ in range(20)]
    vf = VisionFrame(timestamp=datetime(2026, 1, 1), width=1280, height=720)
    vf.hands = [hand]
    return vf


@pytest.fixture
def exp_with_clock() -> tuple[WaveCricketExperience, _FakeClock]:
    clock = _FakeClock(0.0)
    exp = WaveCricketExperience(clock=clock)
    exp.on_enter()
    return exp, clock


def test_meta_correct() -> None:
    meta = WaveCricketExperience.meta
    assert meta.id == "exp01_wave_cricket"
    assert "hands" in meta.vision_modules
    assert meta.age_min == 4


def test_initial_phase_is_intro(exp_with_clock: tuple[WaveCricketExperience, _FakeClock]) -> None:
    exp, _ = exp_with_clock
    state: dict[str, Any] = exp.render_state()
    assert state["phase"] == Phase.INTRO.value
    assert state["score"] == 0
    assert state["crickets"] == []
