"""Tests cho PhotoBoothExperience — gameplay logic độc lập."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from typing import Any, cast

import pytest

from neo_makervigate.core.models import VisionFrame
from neo_makervigate.experiences.exp06_photo_booth.logic import (
    Phase,
    PhotoBoothExperience,
)


class _FakeClock:
    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def _make_empty_frame() -> VisionFrame:
    return VisionFrame(timestamp=datetime(2026, 1, 1), width=1280, height=720)


@pytest.fixture
def exp_with_clock(qapp: Any) -> Generator[tuple[PhotoBoothExperience, _FakeClock], None, None]:
    clock = _FakeClock(0.0)
    exp = PhotoBoothExperience(clock=clock)
    exp.on_enter()
    yield exp, clock
    exp.on_exit()


def test_meta_correct() -> None:
    meta = PhotoBoothExperience.meta
    assert meta.id == "exp06_photo_booth"
    assert "hands" in meta.vision_modules
    assert "selfie" in meta.vision_modules
    assert meta.needs_qwen is True


def test_auto_capture_on_done_is_false() -> None:
    assert PhotoBoothExperience.auto_capture_on_done is False


def test_initial_phase_is_intro(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    exp, _ = exp_with_clock
    state = exp.render_state()
    assert state["phase"] == Phase.INTRO.value


def test_backgrounds_loaded_4_options(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    exp, _ = exp_with_clock
    state = exp.render_state()
    backgrounds = cast(list[dict[str, Any]], state["backgrounds"])
    assert len(backgrounds) == 4
    ids = [bg["id"] for bg in backgrounds]
    assert "san_dinh" in ids
    assert "luy_tre" in ids
    assert "san_fgc" in ids
    assert "sao_hoa" in ids


def test_prompts_toml_loaded(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    exp, _ = exp_with_clock
    # User prompt should be non-empty
    assert exp._prompts["caption"]["user_prompt"]
    # Fallback dict has 4 entries
    fb = exp._prompts["fallback"]
    assert "san_dinh" in fb
    assert "luy_tre" in fb
    assert "san_fgc" in fb
    assert "sao_hoa" in fb


def test_intro_transitions_to_select_after_2s(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())
    assert exp.render_state()["phase"] == Phase.SELECT.value


def test_point_gesture_cycles_selection(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → SELECT
    initial = cast(int, exp.render_state()["selected_bg_index"])
    exp.on_gesture("POINT")
    new = cast(int, exp.render_state()["selected_bg_index"])
    assert new == (initial + 1) % 4


def test_select_auto_advances_to_stage_after_stable_3s(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → SELECT
    clock.advance(3.1)
    exp.on_vision_frame(_make_empty_frame())
    assert exp.render_state()["phase"] == Phase.STAGE.value


def test_point_resets_select_auto_advance_timer(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → SELECT
    clock.advance(2.0)
    exp.on_gesture("POINT")
    clock.advance(2.0)
    exp.on_vision_frame(_make_empty_frame())
    assert exp.render_state()["phase"] == Phase.SELECT.value
