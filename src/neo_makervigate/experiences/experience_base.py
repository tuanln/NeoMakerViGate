"""Experience Protocol + BaseExperience helper.

Pattern:
- `Experience` Protocol: contract bắt buộc — ExperienceManager type-check qua isinstance().
- `BaseExperience` abstract class: tiện kế thừa cho plugin viết nhanh — no-op default cho hầu hết method, chỉ cần override on_vision_frame + meta.

Plugin format: thư mục `exp*/logic.py` export biến `EXPERIENCE = SomeExperience`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Protocol, runtime_checkable

from neo_makervigate.core.models import ExperienceMeta, VisionFrame


@runtime_checkable
class Experience(Protocol):
    """Contract mọi trải nghiệm phải tuân thủ."""

    meta: ExperienceMeta

    def on_enter(self) -> None: ...
    def on_vision_frame(self, frame: VisionFrame) -> None: ...
    def on_gesture(self, gesture: str) -> None: ...
    def on_qwen_response(self, text: str) -> None: ...
    def render_state(self) -> dict[str, object]: ...
    def get_qml_path(self) -> str: ...
    def on_exit(self) -> None: ...


class BaseExperience(ABC):
    """Helper class cho plugin tiện kế thừa.

    Mặc định mọi callback là no-op trừ `meta` (bắt buộc define).
    Plugin chỉ cần override những method thực sự dùng (vd `on_vision_frame`).
    """

    # Plugin override
    meta: ClassVar[ExperienceMeta]

    def __init__(self) -> None:
        if not hasattr(self.__class__, "meta"):
            raise TypeError(
                f"{self.__class__.__name__} thiếu class attribute 'meta: ExperienceMeta'"
            )

    @abstractmethod
    def get_qml_path(self) -> str:
        """Plugin phải override để trỏ tới ui.qml của mình."""
        raise NotImplementedError

    def on_enter(self) -> None:  # noqa: B027 — intentional default no-op
        """Mặc định no-op. Override để load asset."""

    def on_exit(self) -> None:  # noqa: B027 — intentional default no-op
        """Mặc định no-op. Override để dọn dẹp."""

    def on_vision_frame(self, frame: VisionFrame) -> None:
        """Mặc định no-op. Override để cập nhật state từ landmarks."""
        _ = frame

    def on_gesture(self, gesture: str) -> None:
        """Mặc định no-op. Override để phản ứng cử chỉ (WAVE, V_SIGN...)."""
        _ = gesture

    def on_qwen_response(self, text: str) -> None:
        """Mặc định no-op. Override nếu meta.needs_qwen=True."""
        _ = text

    def render_state(self) -> dict[str, object]:
        """Mặc định trả dict rỗng. Override để đẩy state lên QML."""
        return {}
