"""Experience Protocol — interface mọi trải nghiệm phải implement.

Phase 0 chỉ khai báo Protocol. Phase 2 sẽ implement registry + stub plugins.
Phase 3+ implement từng game.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from neo_makervigate.core.models import ExperienceMeta, VisionFrame


@runtime_checkable
class Experience(Protocol):
    """Interface trải nghiệm. Mỗi plugin export biến `EXPERIENCE` là class implement này."""

    meta: ExperienceMeta

    def on_enter(self) -> None:
        """Khởi tạo state, nạp asset. Gọi 1 lần khi vào trải nghiệm."""
        ...

    def on_vision_frame(self, frame: VisionFrame) -> None:
        """Nhận landmarks mỗi khung hình (~15-30fps). Cập nhật game state."""
        ...

    def on_gesture(self, gesture: str) -> None:
        """Nhận sự kiện cử chỉ rời rạc (WAVE, V_SIGN...)."""
        ...

    def on_qwen_response(self, text: str) -> None:
        """Nhận kết quả từ Qwen (chỉ trải nghiệm needs_qwen=True)."""
        ...

    def render_state(self) -> dict[str, object]:
        """Trả về state hiện tại để đẩy lên QML (score, vị trí sprite...)."""
        ...

    def get_qml_path(self) -> str:
        """Đường dẫn file ui.qml của trải nghiệm này."""
        ...

    def on_exit(self) -> None:
        """Dọn dẹp khi rời trải nghiệm. Giải phóng asset."""
        ...
