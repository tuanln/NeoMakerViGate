"""Tests cho core/gesture_detector — WAVE phát hiện từ stream VisionFrame."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from neo_makervigate.core.gesture_detector import GestureDetector
from neo_makervigate.core.models import Landmark, VisionFrame


def _make_frame(wrist_x: float | None, t: float) -> VisionFrame:
    """Sinh VisionFrame với 1 tay có cổ tay tại wrist_x normalized, hoặc không có tay nếu None."""
    base = datetime(2026, 1, 1) + timedelta(seconds=t)
    vf = VisionFrame(timestamp=base, width=1280, height=720)
    if wrist_x is not None:
        wrist = Landmark(x=wrist_x, y=0.5, z=0.0)
        # 21 landmarks; chỉ cần wrist (idx 0) đúng, còn lại đặt cùng vị trí
        hand = [wrist] + [Landmark(x=wrist_x, y=0.5, z=0.0) for _ in range(20)]
        vf.hands = [hand]
        vf.has_person = True
    return vf


def _make_sine_frames(
    cycles: float, amplitude: float, fps: int, duration: float, start_t: float = 0.0
) -> list[VisionFrame]:
    """Sinh chuỗi frame với wrist x dao động sine quanh 0.5."""
    n = int(fps * duration)
    frames: list[VisionFrame] = []
    for i in range(n):
        t = start_t + i / fps
        phase = 2 * math.pi * cycles * (i / n)
        x = 0.5 + amplitude * math.sin(phase)
        frames.append(_make_frame(x, t))
    return frames


def test_no_hands_does_not_crash() -> None:
    det = GestureDetector()
    for i in range(20):
        result = det.feed(_make_frame(None, i / 30.0))
        assert result == []


def test_wrist_idle_no_gesture() -> None:
    det = GestureDetector()
    # 30 frames cổ tay đứng yên tại x=0.5
    gestures: list[str] = []
    for i in range(30):
        gestures.extend(det.feed(_make_frame(0.5, i / 30.0)))
    assert gestures == []
