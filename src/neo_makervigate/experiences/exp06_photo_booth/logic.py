"""exp06 Photo Booth Cổng Làng — gameplay đầy đủ (P6).

Flow: INTRO(2s) → SELECT (POINT cycle, auto-advance 3s)
      → STAGE (V_SIGN hold 0.5s) → COUNTDOWN(3s) → emit photo_capture_requested
      → PROCESSING (waiting_photo → waiting_qwen, max 12s, fallback nếu timeout)
      → DONE → ExperienceManager unload (auto_capture_on_done=False, plugin tự orchestrate)

Caption flow trong PROCESSING:
  photo_captured received → emit qwen_request_started(image, prompt)
  → qwen_response_ready OR qwen_failed → write caption.txt → emit photo_caption_ready
  → set phase DONE
"""

from __future__ import annotations

import contextlib
import time
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, ClassVar

from loguru import logger

from neo_makervigate.core.models import ExperienceMeta, PhotoResult, VisionFrame
from neo_makervigate.experiences.experience_base import BaseExperience
from neo_makervigate.utils.signal_bus import SignalBus

_QML_PATH = (Path(__file__).parent / "ui.qml").as_posix()
_PROMPTS_TOML = Path(__file__).parent / "prompts.toml"
_BACKGROUNDS_DIR = Path(__file__).parent / "backgrounds"

# Phase durations
INTRO_DURATION = 2.0
SELECT_AUTO_ADVANCE_SEC = 3.0
COUNTDOWN_DURATION = 3.0
PROCESSING_TIMEOUT = 12.0
V_SIGN_TRIGGER_HOLD = 0.5


class Phase(StrEnum):
    INTRO = "intro"
    SELECT = "select"
    STAGE = "stage"
    COUNTDOWN = "countdown"
    PROCESSING = "processing"
    DONE = "done"


@dataclass
class BackgroundOption:
    id: str
    title: str
    emoji: str
    path: Path
    fallback_caption: str


def _load_prompts() -> dict[str, Any]:
    with open(_PROMPTS_TOML, "rb") as f:
        return tomllib.load(f)


def _load_backgrounds(prompts: dict[str, Any]) -> list[BackgroundOption]:
    fallback = prompts.get("fallback", {})
    defs = [
        ("san_dinh", "Sân Đình", "🏛️"),
        ("luy_tre", "Lũy Tre", "🎍"),
        ("san_fgc", "Sân FGC", "🎮"),
        ("sao_hoa", "Sao Hỏa", "🚀"),
    ]
    return [
        BackgroundOption(
            id=bg_id,
            title=title,
            emoji=emoji,
            path=_BACKGROUNDS_DIR / f"{bg_id}.png",
            fallback_caption=fallback.get(bg_id, f"{emoji} Ảnh em chụp tại {title}!"),
        )
        for bg_id, title, emoji in defs
    ]


class PhotoBoothExperience(BaseExperience):
    """Photo Booth Cổng Làng — chọn nền, làm V, chụp, AI caption."""

    auto_capture_on_done: ClassVar[bool] = False  # plugin self-orchestrates

    meta = ExperienceMeta(
        id="exp06_photo_booth",
        title="Photo Booth Cổng Làng",
        subtitle="Chụp ảnh + caption AI",
        age_min=5,
        age_max=12,
        vision_modules=("hands", "selfie"),
        needs_qwen=True,
        needs_voice=False,
        needs_internet=False,
        icon_path="",
        dev_days=7,
    )

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        super().__init__()
        self._clock: Callable[[], float] = clock or time.perf_counter
        self._prompts: dict[str, Any] = _load_prompts()
        self._backgrounds: list[BackgroundOption] = _load_backgrounds(self._prompts)
        self._phase: Phase = Phase.INTRO
        self._phase_started_at: float = 0.0
        self._selected_bg_index: int = 0
        self._select_last_change_at: float = 0.0
        self._countdown_remaining: float = 0.0
        self._v_sign_holding_since: float | None = None
        self._photo_id: str = ""
        self._photo_dir: Path | None = None
        self._composite_path: Path | None = None
        self._caption: str = ""
        self._caption_from_qwen: bool = False
        self._processing_status: str = ""
        self._processing_started_at: float = 0.0

    def get_qml_path(self) -> str:
        return _QML_PATH

    def on_enter(self) -> None:
        now = self._clock()
        self._phase = Phase.INTRO
        self._phase_started_at = now
        self._select_last_change_at = now
        self._selected_bg_index = 0
        self._countdown_remaining = 0.0
        self._v_sign_holding_since = None
        self._photo_id = ""
        self._photo_dir = None
        self._composite_path = None
        self._caption = ""
        self._caption_from_qwen = False
        self._processing_status = ""

        bus = SignalBus.instance()
        bus.photo_captured.connect(self._on_photo_captured)
        bus.qwen_response_ready.connect(self._on_qwen_response)
        bus.qwen_failed.connect(self._on_qwen_failed)
        logger.info(f"PhotoBooth: on_enter ({len(self._backgrounds)} backgrounds)")

    def on_exit(self) -> None:
        bus = SignalBus.instance()
        for sig, slot in [
            (bus.photo_captured, self._on_photo_captured),
            (bus.qwen_response_ready, self._on_qwen_response),
            (bus.qwen_failed, self._on_qwen_failed),
        ]:
            with contextlib.suppress(TypeError, RuntimeError):
                sig.disconnect(slot)  # type: ignore[call-overload]

    def on_vision_frame(self, frame: VisionFrame) -> None:
        now = self._clock()
        self._step_phase(now)

    def on_gesture(self, gesture: str) -> None:
        now = self._clock()
        if gesture == "POINT" and self._phase == Phase.SELECT:
            self._selected_bg_index = (self._selected_bg_index + 1) % len(self._backgrounds)
            self._select_last_change_at = now
            return
        if gesture == "V_SIGN" and self._phase == Phase.STAGE:
            if self._v_sign_holding_since is None:
                self._v_sign_holding_since = now
            elif now - self._v_sign_holding_since >= V_SIGN_TRIGGER_HOLD:
                self._enter_countdown(now)

    def render_state(self) -> dict[str, object]:
        now = self._clock()
        v_sign_progress = 0.0
        if self._v_sign_holding_since is not None:
            v_sign_progress = min(1.0, (now - self._v_sign_holding_since) / V_SIGN_TRIGGER_HOLD)
        return {
            "phase": self._phase.value,
            "elapsed_in_phase": now - self._phase_started_at,
            "backgrounds": [
                {"id": bg.id, "title": bg.title, "emoji": bg.emoji, "path": str(bg.path)}
                for bg in self._backgrounds
            ],
            "selected_bg_index": self._selected_bg_index,
            "v_sign_progress": v_sign_progress,
            "countdown_remaining": self._countdown_remaining,
            "processing_status": self._processing_status,
            "caption": self._caption,
            "qwen_unavailable": False,
        }

    def completion_summary(self) -> dict[str, Any]:
        bg = self._backgrounds[self._selected_bg_index]
        return {
            "completed": True,
            "background_id": bg.id,
            "caption": self._caption,
            "qwen_used": self._caption_from_qwen,
        }

    # --- Internal ---

    def _step_phase(self, now: float) -> None:
        elapsed = now - self._phase_started_at
        if self._phase == Phase.INTRO and elapsed >= INTRO_DURATION:
            self._phase = Phase.SELECT
            self._phase_started_at = now
            self._select_last_change_at = now
        elif self._phase == Phase.SELECT:
            since_change = now - self._select_last_change_at
            if since_change >= SELECT_AUTO_ADVANCE_SEC:
                self._phase = Phase.STAGE
                self._phase_started_at = now
        elif self._phase == Phase.COUNTDOWN:
            self._countdown_remaining = max(0.0, COUNTDOWN_DURATION - elapsed)
            if elapsed >= COUNTDOWN_DURATION:
                self._enter_processing(now)
        elif self._phase == Phase.PROCESSING:
            if (now - self._processing_started_at) >= PROCESSING_TIMEOUT:
                self._fallback_caption()

    def _enter_countdown(self, now: float) -> None:
        self._phase = Phase.COUNTDOWN
        self._phase_started_at = now
        self._countdown_remaining = COUNTDOWN_DURATION
        self._v_sign_holding_since = None

    def _enter_processing(self, now: float) -> None:
        self._phase = Phase.PROCESSING
        self._phase_started_at = now
        self._processing_started_at = now
        self._processing_status = "waiting_photo"
        bg = self._backgrounds[self._selected_bg_index]
        SignalBus.instance().photo_capture_requested.emit({
            "experience_id": self.meta.id,
            "background_path": str(bg.path),
        })

    def _fallback_caption(self) -> None:
        # Real implementation in T14; for now just transition to DONE
        bg = self._backgrounds[self._selected_bg_index]
        self._caption = bg.fallback_caption
        self._caption_from_qwen = False
        self._processing_status = "done"
        self._phase = Phase.DONE
        self._phase_started_at = self._clock()

    # Placeholders — flesh out in T12-T14
    def _on_photo_captured(self, result: PhotoResult) -> None:
        pass

    def _on_qwen_response(self, text: str) -> None:
        pass

    def _on_qwen_failed(self, error: str) -> None:
        pass


EXPERIENCE = PhotoBoothExperience
