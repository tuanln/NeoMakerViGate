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


def test_app_controller_emits_photo_review_requested_on_capture(qapp) -> None:
    """Khi SignalBus.photo_captured emit success → photoReviewRequested signal."""
    from pathlib import Path

    from neo_makervigate.core.models import PhotoResult
    from neo_makervigate.utils.signal_bus import SignalBus

    ctrl = AppController(experience_manager=None)
    emits: list[bool] = []
    ctrl.photoReviewRequested.connect(lambda: emits.append(True))

    result = PhotoResult(
        success=True,
        photo_id="photo_test",
        original_path=Path("/tmp/x.jpg"),
        qr_path=Path("/tmp/qr.png"),
        download_url="http://test/photo_test/original.jpg",
        experience_id="exp_test",
    )
    SignalBus.instance().photo_captured.emit(result)
    qapp.processEvents()
    assert emits == [True]
    state = ctrl.photoResult
    assert state["photo_id"] == "photo_test"
    assert state["download_url"] == "http://test/photo_test/original.jpg"
    assert state["qr_path"] == "/tmp/qr.png"


def test_app_controller_does_not_emit_review_on_failed_capture(qapp) -> None:
    """Khi photo_captured emit failure → KHÔNG push review."""
    from neo_makervigate.core.models import PhotoResult
    from neo_makervigate.utils.signal_bus import SignalBus

    ctrl = AppController(experience_manager=None)
    emits: list[bool] = []
    ctrl.photoReviewRequested.connect(lambda: emits.append(True))

    result = PhotoResult(
        success=False, photo_id="", experience_id="exp", error_message="oops",
    )
    SignalBus.instance().photo_captured.emit(result)
    qapp.processEvents()
    assert emits == []


def test_photo_result_empty_by_default(qapp) -> None:
    ctrl = AppController(experience_manager=None)
    assert ctrl.photoResult == {}


def test_photo_caption_ready_updates_photo_result(qapp) -> None:
    """When photo_caption_ready signal fires, photoResult dict gets caption populated."""
    from pathlib import Path

    from neo_makervigate.core.models import PhotoResult
    from neo_makervigate.utils.signal_bus import SignalBus

    ctrl = AppController(experience_manager=None)
    # First, simulate photo_captured to set photoResult base
    result = PhotoResult(
        success=True,
        photo_id="photo_abc",
        original_path=Path("/tmp/orig.jpg"),
        qr_path=Path("/tmp/qr.png"),
        download_url="http://x/photo_abc/original.jpg",
        experience_id="exp06_photo_booth",
    )
    SignalBus.instance().photo_captured.emit(result)
    qapp.processEvents()
    assert ctrl.photoResult["caption"] == ""

    # Now fire photo_caption_ready
    changes: list[bool] = []
    ctrl.photoResultChanged.connect(lambda: changes.append(True))
    SignalBus.instance().photo_caption_ready.emit("photo_abc", "Em đứng cười tươi! 🌞")
    qapp.processEvents()
    assert ctrl.photoResult["caption"] == "Em đứng cười tươi! 🌞"
    assert len(changes) >= 1


def test_photo_caption_ready_ignored_for_different_photo_id(qapp) -> None:
    """Mismatched photo_id → caption not applied."""
    from pathlib import Path

    from neo_makervigate.core.models import PhotoResult
    from neo_makervigate.utils.signal_bus import SignalBus

    ctrl = AppController(experience_manager=None)
    result = PhotoResult(
        success=True,
        photo_id="photo_xyz",
        original_path=Path("/tmp/o.jpg"),
        qr_path=Path("/tmp/q.png"),
        download_url="http://x",
        experience_id="exp",
    )
    SignalBus.instance().photo_captured.emit(result)
    qapp.processEvents()

    SignalBus.instance().photo_caption_ready.emit("photo_other", "wrong caption")
    qapp.processEvents()
    assert ctrl.photoResult["caption"] == ""
