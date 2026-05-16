"""ExperienceManager — vòng đời plugin.

Trách nhiệm:
1. Giữ registry các plugin discover được lúc khởi động.
2. `load(exp_id)`: instantiate plugin → on_enter() → set_active_modules trên VisionEngine → emit experience_started.
3. Route `vision_frame_ready` → instance.on_vision_frame()
4. Route `gesture_detected` → instance.on_gesture()
5. `unload()`: on_exit() → reset modules → emit experience_ended.
6. Watchdog: nếu on_vision_frame() > 500ms → ngắt plugin, quay về Hub.

P2 chưa nối VisionEngine.set_active_modules — sẽ làm khi exp01 thật chạy ở P3.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from loguru import logger

from neo_makervigate.utils.signal_bus import SignalBus

if TYPE_CHECKING:
    from neo_makervigate.core.models import ExperienceMeta, VisionFrame
    from neo_makervigate.core.vision_worker import VisionWorker
    from neo_makervigate.experiences.experience_base import Experience


WATCHDOG_THRESHOLD_MS = 500.0


class ExperienceManager:
    """Singleton-ish manager — một instance trong app.py giữ state."""

    def __init__(
        self,
        registry: dict[str, type[Experience]],
        worker: VisionWorker | None = None,
    ) -> None:
        self._registry = registry
        self._worker = worker
        self._current_id: str | None = None
        self._current_instance: Experience | None = None
        self._consecutive_slow_frames = 0

        bus = SignalBus.instance()
        bus.vision_frame_ready.connect(self._on_vision_frame)
        bus.gesture_detected.connect(self._on_gesture)
        bus.qwen_response_ready.connect(self._on_qwen_response)

    @property
    def experience_ids(self) -> list[str]:
        return list(self._registry.keys())

    @property
    def current_id(self) -> str | None:
        return self._current_id

    @property
    def current_instance(self) -> Experience | None:
        return self._current_instance

    def get_meta(self, exp_id: str) -> ExperienceMeta | None:
        cls = self._registry.get(exp_id)
        return cls.meta if cls is not None else None

    def all_metas(self) -> list[dict[str, object]]:
        """List of metadata dicts cho QML Hub."""
        result = []
        for exp_id, cls in self._registry.items():
            meta = cls.meta
            result.append(
                {
                    "id": meta.id,
                    "title": meta.title,
                    "subtitle": meta.subtitle,
                    "ageMin": meta.age_min,
                    "ageMax": meta.age_max,
                    "iconPath": meta.icon_path,
                    "needsQwen": meta.needs_qwen,
                    "needsVoice": meta.needs_voice,
                    "needsInternet": meta.needs_internet,
                }
            )
            _ = exp_id  # cho mypy
        return result

    def load(self, exp_id: str) -> bool:
        """Nạp plugin theo id. Trả True nếu thành công."""
        if self._current_id is not None:
            logger.warning(
                f"load({exp_id}) called while {self._current_id} active — unloading first"
            )
            self.unload()

        cls = self._registry.get(exp_id)
        if cls is None:
            logger.error(f"Unknown experience id: {exp_id}")
            return False

        try:
            instance = cls()
            instance.on_enter()
        except Exception as e:
            logger.exception(f"Plugin {exp_id} failed in on_enter: {e}")
            return False

        self._current_id = exp_id
        self._current_instance = instance
        self._consecutive_slow_frames = 0

        # Switch MediaPipe modules
        if self._worker is not None and instance.meta.vision_modules:
            try:
                self._worker.set_active_modules(list(instance.meta.vision_modules))
            except Exception as e:
                logger.warning(f"set_active_modules failed: {e}")

        SignalBus.instance().experience_started.emit(exp_id)
        logger.info(f"Experience started: {exp_id}")
        return True

    def unload(self, summary: dict[str, object] | None = None) -> None:
        """Kết thúc plugin hiện tại."""
        if self._current_instance is None or self._current_id is None:
            return
        exp_id = self._current_id
        try:
            self._current_instance.on_exit()
        except Exception as e:
            logger.warning(f"Plugin {exp_id} raised in on_exit: {e}")
        self._current_id = None
        self._current_instance = None
        SignalBus.instance().experience_ended.emit(exp_id, summary or {})
        logger.info(f"Experience ended: {exp_id}")

    # ---- Signal handlers ----

    def _on_vision_frame(self, frame: VisionFrame) -> None:
        if self._current_instance is None:
            return
        start = time.perf_counter()
        try:
            self._current_instance.on_vision_frame(frame)
        except Exception as e:
            logger.exception(f"Plugin {self._current_id} raised in on_vision_frame: {e}")
            self.unload({"crash": True, "where": "on_vision_frame", "error": str(e)})
            return
        # Auto-end when plugin signals completion via render_state phase==done
        if self._current_instance is not None:
            try:
                state = self._current_instance.render_state()
                if isinstance(state, dict) and state.get("phase") == "done":
                    summary_fn = getattr(self._current_instance, "completion_summary", None)
                    summary = summary_fn() if callable(summary_fn) else {"completed": True}
                    self.unload(summary)
                    return
            except Exception as e:
                logger.warning(f"render_state check failed: {e}")
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms > WATCHDOG_THRESHOLD_MS:
            self._consecutive_slow_frames += 1
            logger.warning(
                f"Plugin {self._current_id} slow frame {elapsed_ms:.0f}ms "
                f"(consecutive {self._consecutive_slow_frames})"
            )
            if self._consecutive_slow_frames > 5:
                logger.error(f"Plugin {self._current_id} watchdog tripped — unloading")
                self.unload({"watchdog": True})
        else:
            self._consecutive_slow_frames = 0

    def _on_gesture(self, gesture: str) -> None:
        if self._current_instance is None:
            return
        try:
            self._current_instance.on_gesture(gesture)
        except Exception as e:
            logger.exception(f"Plugin {self._current_id} raised in on_gesture: {e}")

    def _on_qwen_response(self, text: str) -> None:
        if self._current_instance is None:
            return
        try:
            self._current_instance.on_qwen_response(text)
        except Exception as e:
            logger.exception(f"Plugin {self._current_id} raised in on_qwen_response: {e}")
