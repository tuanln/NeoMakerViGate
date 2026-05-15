"""Tests cho services/experience_manager — lifecycle + watchdog."""

from __future__ import annotations

import time
from datetime import datetime

from neo_makervigate.core.models import ExperienceMeta, VisionFrame
from neo_makervigate.experiences.experience_base import BaseExperience
from neo_makervigate.services.experience_manager import ExperienceManager
from neo_makervigate.utils.signal_bus import SignalBus


class _FakeExperience(BaseExperience):
    meta = ExperienceMeta(
        id="fake_test",
        title="Fake",
        subtitle="Fake test",
        age_min=4,
        age_max=14,
        vision_modules=("hands",),
    )

    def __init__(self) -> None:
        super().__init__()
        self.entered = False
        self.exited = False
        self.frames_seen = 0
        self.gestures_seen: list[str] = []

    def get_qml_path(self) -> str:
        return ""

    def on_enter(self) -> None:
        self.entered = True

    def on_exit(self) -> None:
        self.exited = True

    def on_vision_frame(self, frame: VisionFrame) -> None:
        self.frames_seen += 1

    def on_gesture(self, gesture: str) -> None:
        self.gestures_seen.append(gesture)


def _make_frame() -> VisionFrame:
    return VisionFrame(timestamp=datetime.now(), width=320, height=180)


def test_load_calls_on_enter(qapp) -> None:
    mgr = ExperienceManager(registry={"fake_test": _FakeExperience})

    ok = mgr.load("fake_test")
    assert ok is True
    assert mgr.current_id == "fake_test"
    inst = mgr.current_instance
    assert inst is not None
    assert inst.entered is True
    assert inst.exited is False


def test_unload_calls_on_exit(qapp) -> None:
    mgr = ExperienceManager(registry={"fake_test": _FakeExperience})
    mgr.load("fake_test")
    inst = mgr.current_instance

    mgr.unload()

    assert mgr.current_id is None
    assert inst is not None
    assert inst.exited is True


def test_vision_frame_routed_to_active_plugin(qapp) -> None:
    mgr = ExperienceManager(registry={"fake_test": _FakeExperience})
    mgr.load("fake_test")
    inst = mgr.current_instance
    assert inst is not None

    bus = SignalBus.instance()
    bus.vision_frame_ready.emit(_make_frame())
    bus.vision_frame_ready.emit(_make_frame())

    assert inst.frames_seen == 2


def test_no_routing_when_no_experience_loaded(qapp) -> None:
    mgr = ExperienceManager(registry={"fake_test": _FakeExperience})
    # No load called

    bus = SignalBus.instance()
    bus.vision_frame_ready.emit(_make_frame())

    # Không crash, current_instance vẫn None
    assert mgr.current_instance is None


def test_gesture_routed_to_plugin(qapp) -> None:
    mgr = ExperienceManager(registry={"fake_test": _FakeExperience})
    mgr.load("fake_test")
    inst = mgr.current_instance
    assert inst is not None

    bus = SignalBus.instance()
    bus.gesture_detected.emit("WAVE")
    bus.gesture_detected.emit("V_SIGN")

    assert inst.gestures_seen == ["WAVE", "V_SIGN"]


def test_unknown_experience_id_returns_false(qapp) -> None:
    mgr = ExperienceManager(registry={"fake_test": _FakeExperience})
    ok = mgr.load("nonexistent")
    assert ok is False
    assert mgr.current_id is None


def test_all_metas_returns_list_of_dicts(qapp) -> None:
    mgr = ExperienceManager(registry={"fake_test": _FakeExperience})
    metas = mgr.all_metas()
    assert isinstance(metas, list)
    assert len(metas) == 1
    assert metas[0]["id"] == "fake_test"
    assert metas[0]["title"] == "Fake"
    assert metas[0]["ageMin"] == 4


def test_plugin_exception_in_vision_frame_unloads(qapp) -> None:
    class _CrashyExperience(_FakeExperience):
        meta = ExperienceMeta(
            id="crashy",
            title="Crashy",
            subtitle="",
            age_min=4,
            age_max=14,
            vision_modules=("hands",),
        )

        def on_vision_frame(self, frame: VisionFrame) -> None:
            raise RuntimeError("intentional crash")

    mgr = ExperienceManager(registry={"crashy": _CrashyExperience})
    mgr.load("crashy")
    assert mgr.current_id == "crashy"

    bus = SignalBus.instance()
    bus.vision_frame_ready.emit(_make_frame())

    # Manager nên unload sau exception
    assert mgr.current_id is None


def test_watchdog_unloads_slow_plugin(qapp) -> None:
    class _SlowExperience(_FakeExperience):
        meta = ExperienceMeta(
            id="slow",
            title="Slow",
            subtitle="",
            age_min=4,
            age_max=14,
            vision_modules=("hands",),
        )

        def on_vision_frame(self, frame: VisionFrame) -> None:
            time.sleep(0.6)  # > 500ms threshold

    mgr = ExperienceManager(registry={"slow": _SlowExperience})
    mgr.load("slow")

    bus = SignalBus.instance()
    # 6 slow frames consecutive → tripped (threshold > 5)
    for _ in range(7):
        bus.vision_frame_ready.emit(_make_frame())

    assert mgr.current_id is None  # watchdog đã unload
