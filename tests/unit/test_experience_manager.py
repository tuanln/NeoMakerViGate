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


def test_phase_done_emits_photo_capture_requested_before_unload(qapp) -> None:
    """Khi plugin trả phase=done, manager emit photo_capture_requested rồi unload."""
    from datetime import datetime

    from neo_makervigate.core.models import ExperienceMeta, VisionFrame
    from neo_makervigate.experiences.experience_base import BaseExperience

    class _DoneExp(BaseExperience):
        meta = ExperienceMeta(
            id="done_p5",
            title="Done P5",
            subtitle="",
            age_min=4,
            age_max=14,
            vision_modules=("hands",),
        )

        def __init__(self) -> None:
            super().__init__()
            self.frames = 0

        def get_qml_path(self) -> str:
            return ""

        def on_vision_frame(self, frame: VisionFrame) -> None:
            self.frames += 1

        def render_state(self) -> dict[str, object]:
            if self.frames >= 2:
                return {"phase": "done"}
            return {"phase": "playing"}

        def completion_summary(self) -> dict[str, object]:
            return {"completed": True, "score": 100}

    mgr = ExperienceManager(registry={"done_p5": _DoneExp})
    mgr.load("done_p5")
    captured_requests: list[dict] = []
    SignalBus.instance().photo_capture_requested.connect(lambda p: captured_requests.append(p))

    bus = SignalBus.instance()
    bus.vision_frame_ready.emit(VisionFrame(timestamp=datetime.now(), width=640, height=360))
    bus.vision_frame_ready.emit(VisionFrame(timestamp=datetime.now(), width=640, height=360))

    assert len(captured_requests) == 1
    assert captured_requests[0]["experience_id"] == "done_p5"
    assert "summary" in captured_requests[0]
    assert mgr.current_id is None


def test_phase_done_triggers_auto_unload(qapp) -> None:
    """Plugin có render_state()['phase']=='done' phải auto-unload qua _on_vision_frame."""

    class _DoneExp(BaseExperience):
        meta = ExperienceMeta(
            id="done_test",
            title="DoneTest",
            subtitle="",
            age_min=4,
            age_max=14,
            vision_modules=("hands",),
        )

        def __init__(self) -> None:
            super().__init__()
            self.frame_count = 0

        def get_qml_path(self) -> str:
            return ""

        def on_vision_frame(self, frame: VisionFrame) -> None:
            self.frame_count += 1

        def render_state(self) -> dict[str, object]:
            # Hết phase == "playing" lần đầu; lần thứ 2 trả "done" → auto-unload
            if self.frame_count >= 2:
                return {"phase": "done"}
            return {"phase": "playing"}

        def completion_summary(self) -> dict[str, object]:
            return {"completed": True, "score": 42}

    mgr = ExperienceManager(registry={"done_test": _DoneExp})
    mgr.load("done_test")
    assert mgr.current_id == "done_test"

    bus = SignalBus.instance()
    # Frame 1 — instance still PLAYING
    bus.vision_frame_ready.emit(VisionFrame(timestamp=datetime.now(), width=640, height=360))
    assert mgr.current_id == "done_test"
    # Frame 2 — instance trả "done" → manager auto-unload
    bus.vision_frame_ready.emit(VisionFrame(timestamp=datetime.now(), width=640, height=360))
    assert mgr.current_id is None


def test_auto_capture_on_done_false_skips_photo_request(qapp) -> None:
    """Plugin với auto_capture_on_done=False → manager KHÔNG emit photo_capture_requested."""
    from datetime import datetime

    from neo_makervigate.core.models import ExperienceMeta, VisionFrame
    from neo_makervigate.experiences.experience_base import BaseExperience

    class _SelfOrchExp(BaseExperience):
        auto_capture_on_done = False
        meta = ExperienceMeta(
            id="self_orch",
            title="SelfOrch",
            subtitle="",
            age_min=4,
            age_max=14,
            vision_modules=("hands",),
        )

        def __init__(self) -> None:
            super().__init__()
            self.frames = 0

        def get_qml_path(self) -> str:
            return ""

        def on_vision_frame(self, frame: VisionFrame) -> None:
            self.frames += 1

        def render_state(self) -> dict[str, object]:
            return {"phase": "done"} if self.frames >= 2 else {"phase": "playing"}

        def completion_summary(self) -> dict[str, object]:
            return {"completed": True}

    mgr = ExperienceManager(registry={"self_orch": _SelfOrchExp})
    mgr.load("self_orch")
    requests: list[dict] = []
    SignalBus.instance().photo_capture_requested.connect(lambda p: requests.append(p))

    bus = SignalBus.instance()
    bus.vision_frame_ready.emit(VisionFrame(timestamp=datetime.now(), width=640, height=360))
    bus.vision_frame_ready.emit(VisionFrame(timestamp=datetime.now(), width=640, height=360))

    assert mgr.current_id is None
    assert requests == []
