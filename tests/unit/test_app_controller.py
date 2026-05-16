"""Tests cho AppController extension — experienceState property + render timer."""

from __future__ import annotations

from dataclasses import dataclass

from neo_makervigate.core.models import ExperienceMeta
from neo_makervigate.experiences.experience_base import BaseExperience
from neo_makervigate.services.app_controller import AppController
from neo_makervigate.services.experience_manager import ExperienceManager


@dataclass
class _MutableState:
    counter: int = 0


class _StateExp(BaseExperience):
    meta = ExperienceMeta(
        id="state_test",
        title="StateTest",
        subtitle="",
        age_min=4,
        age_max=14,
        vision_modules=("hands",),
    )

    def __init__(self) -> None:
        super().__init__()
        self._state = _MutableState()

    def get_qml_path(self) -> str:
        return ""

    def bump(self) -> None:
        self._state.counter += 1

    def render_state(self) -> dict[str, object]:
        return {"counter": self._state.counter}


def test_experience_state_empty_when_no_experience(qapp) -> None:
    ctrl = AppController(experience_manager=None)
    assert ctrl.experienceState == {}


def test_experience_state_updates_after_load(qapp) -> None:
    mgr = ExperienceManager(registry={"state_test": _StateExp})
    ctrl = AppController(experience_manager=mgr)
    mgr.load("state_test")
    # Manual poll — timer may not have fired yet
    ctrl._poll_render_state()
    assert ctrl.experienceState == {"counter": 0}
    # Mutate underlying state
    inst = mgr.current_instance
    assert isinstance(inst, _StateExp)
    inst.bump()
    ctrl._poll_render_state()
    assert ctrl.experienceState == {"counter": 1}


def test_experience_state_cleared_on_end(qapp) -> None:
    mgr = ExperienceManager(registry={"state_test": _StateExp})
    ctrl = AppController(experience_manager=mgr)
    mgr.load("state_test")
    ctrl._poll_render_state()
    assert ctrl.experienceState != {}
    mgr.unload()
    # _on_experience_ended slot clears state
    assert ctrl.experienceState == {}
