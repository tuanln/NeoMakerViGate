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


def test_wave_two_sine_cycles_triggers() -> None:
    det = GestureDetector()
    # 2 chu kỳ sine biên 0.1 trong 1s @ 30fps = 30 frames
    frames = _make_sine_frames(cycles=2, amplitude=0.1, fps=30, duration=1.0)
    gestures: list[str] = []
    for f in frames:
        gestures.extend(det.feed(f))
    assert "WAVE" in gestures


def test_wave_amplitude_too_small_no_trigger() -> None:
    det = GestureDetector()
    # Biên 0.02 < threshold 0.05 — không trigger dù có crossings
    frames = _make_sine_frames(cycles=2, amplitude=0.02, fps=30, duration=1.0)
    gestures: list[str] = []
    for f in frames:
        gestures.extend(det.feed(f))
    assert gestures == []


def test_wave_single_crossing_no_trigger() -> None:
    det = GestureDetector()
    # 0.25 cycle: chỉ đi lên 1/4 sóng (0 → đỉnh), chỉ có 1 crossing qua mean → chưa đủ threshold 2
    frames = _make_sine_frames(cycles=0.25, amplitude=0.1, fps=30, duration=1.0)
    gestures: list[str] = []
    for f in frames:
        gestures.extend(det.feed(f))
    assert gestures == []


def test_wave_cooldown_blocks_immediate_retrigger() -> None:
    det = GestureDetector()
    # Vẫy đủ trigger
    frames1 = _make_sine_frames(cycles=2, amplitude=0.1, fps=30, duration=1.0, start_t=0.0)
    gestures: list[str] = []
    for f in frames1:
        gestures.extend(det.feed(f))
    first_count = gestures.count("WAVE")
    assert first_count >= 1

    # Vẫy lại ngay trong 0.05s (< 0.4s cooldown) — cooldown phải chặn
    # frames1 kết thúc ~1.0s, last WAVE ~0.67s → cooldown_until ~1.067s
    # frames2: 1 frame duy nhất tại t=1.0s (int(30*0.05)=1) — nằm trong cooldown (< 1.067s)
    frames2 = _make_sine_frames(cycles=2, amplitude=0.1, fps=30, duration=0.05, start_t=1.0)
    for f in frames2:
        gestures.extend(det.feed(f))
    assert gestures.count("WAVE") == first_count


def test_wave_after_cooldown_triggers_again() -> None:
    det = GestureDetector()
    # Vẫy lần 1
    for f in _make_sine_frames(cycles=2, amplitude=0.1, fps=30, duration=1.0, start_t=0.0):
        det.feed(f)
    # Đợi qua cooldown (1.0s start_t + 0.5s gap = 1.5s)
    # Vẫy lần 2 với pattern mới start_t=1.5 (qua 0.4s cooldown)
    gestures: list[str] = []
    for f in _make_sine_frames(cycles=2, amplitude=0.1, fps=30, duration=1.0, start_t=1.5):
        gestures.extend(det.feed(f))
    assert "WAVE" in gestures


def test_reset_clears_buffer() -> None:
    # Positive control: verify that WITHOUT reset, 7 buffered + 5 new samples
    # (all within the 1s window) produce a WAVE trigger.
    det_no_reset = GestureDetector()
    partial = _make_sine_frames(cycles=2, amplitude=0.1, fps=30, duration=1.0, start_t=0.0)[:7]
    for f in partial:
        det_no_reset.feed(f)
    after = _make_sine_frames(cycles=2, amplitude=0.1, fps=30, duration=1.0, start_t=0.5)[:5]
    gestures_no_reset: list[str] = []
    for f in after:
        gestures_no_reset.extend(det_no_reset.feed(f))
    assert "WAVE" in gestures_no_reset, "positive control failed: 7+5 samples should trigger WAVE"

    # Actual test: WITH reset, the same 5 new samples cannot trigger.
    # reset() wipes the 7 buffered samples so only 5 < WAVE_MIN_SAMPLES=8 remain.
    det = GestureDetector()
    for f in partial:
        det.feed(f)  # Load 7 samples into buffer
    det.reset()  # Clear buffer (and cooldown)
    gestures: list[str] = []
    for f in after:
        gestures.extend(det.feed(f))  # Only 5 new samples — below minimum
    assert gestures == []  # Buffer cleared → 5 < 8 → no trigger possible


def _make_hand_v_sign(wrist_x: float = 0.5, wrist_y: float = 0.5) -> list[Landmark]:
    """Synthesize 21-landmark hand in V-sign pose.

    Index + middle extended upward (tip far from wrist), ring + pinky curled (tip close).
    """
    L = [Landmark(x=wrist_x, y=wrist_y) for _ in range(21)]
    L[0] = Landmark(x=wrist_x, y=wrist_y)
    # Index extended: tip 0.20 above wrist, pip 0.10 above
    L[5] = Landmark(x=wrist_x - 0.03, y=wrist_y - 0.05)
    L[6] = Landmark(x=wrist_x - 0.03, y=wrist_y - 0.10)
    L[7] = Landmark(x=wrist_x - 0.03, y=wrist_y - 0.15)
    L[8] = Landmark(x=wrist_x - 0.03, y=wrist_y - 0.20)
    # Middle extended: tip 0.22 above
    L[9] = Landmark(x=wrist_x + 0.01, y=wrist_y - 0.05)
    L[10] = Landmark(x=wrist_x + 0.01, y=wrist_y - 0.11)
    L[11] = Landmark(x=wrist_x + 0.01, y=wrist_y - 0.16)
    L[12] = Landmark(x=wrist_x + 0.01, y=wrist_y - 0.22)
    # Ring curled: tip CLOSER to wrist than pip
    L[13] = Landmark(x=wrist_x + 0.04, y=wrist_y - 0.05)
    L[14] = Landmark(x=wrist_x + 0.04, y=wrist_y - 0.07)
    L[15] = Landmark(x=wrist_x + 0.04, y=wrist_y - 0.06)
    L[16] = Landmark(x=wrist_x + 0.04, y=wrist_y - 0.04)
    # Pinky curled similarly
    L[17] = Landmark(x=wrist_x + 0.07, y=wrist_y - 0.04)
    L[18] = Landmark(x=wrist_x + 0.07, y=wrist_y - 0.06)
    L[19] = Landmark(x=wrist_x + 0.07, y=wrist_y - 0.05)
    L[20] = Landmark(x=wrist_x + 0.07, y=wrist_y - 0.03)
    return L


def _make_hand_open_palm(wrist_x: float = 0.5, wrist_y: float = 0.5) -> list[Landmark]:
    """All 5 fingers extended."""
    L = [Landmark(x=wrist_x, y=wrist_y) for _ in range(21)]
    for finger_offset, mcp_idx in [(-0.06, 5), (-0.02, 9), (0.02, 13), (0.06, 17)]:
        L[mcp_idx] = Landmark(x=wrist_x + finger_offset, y=wrist_y - 0.05)
        L[mcp_idx + 1] = Landmark(x=wrist_x + finger_offset, y=wrist_y - 0.10)
        L[mcp_idx + 2] = Landmark(x=wrist_x + finger_offset, y=wrist_y - 0.15)
        L[mcp_idx + 3] = Landmark(x=wrist_x + finger_offset, y=wrist_y - 0.20)
    return L


def _make_hand_point(wrist_x: float = 0.5, wrist_y: float = 0.5) -> list[Landmark]:
    """Only index extended, others curled."""
    L = [Landmark(x=wrist_x, y=wrist_y) for _ in range(21)]
    L[5] = Landmark(x=wrist_x, y=wrist_y - 0.05)
    L[6] = Landmark(x=wrist_x, y=wrist_y - 0.10)
    L[7] = Landmark(x=wrist_x, y=wrist_y - 0.15)
    L[8] = Landmark(x=wrist_x, y=wrist_y - 0.20)
    L[9] = Landmark(x=wrist_x + 0.03, y=wrist_y - 0.05)
    L[10] = Landmark(x=wrist_x + 0.03, y=wrist_y - 0.07)
    L[12] = Landmark(x=wrist_x + 0.03, y=wrist_y - 0.04)
    L[13] = Landmark(x=wrist_x + 0.05, y=wrist_y - 0.05)
    L[14] = Landmark(x=wrist_x + 0.05, y=wrist_y - 0.07)
    L[16] = Landmark(x=wrist_x + 0.05, y=wrist_y - 0.04)
    L[17] = Landmark(x=wrist_x + 0.07, y=wrist_y - 0.05)
    L[18] = Landmark(x=wrist_x + 0.07, y=wrist_y - 0.07)
    L[20] = Landmark(x=wrist_x + 0.07, y=wrist_y - 0.04)
    return L


def _frame_with_hand(hand: list[Landmark], t: float = 0.0) -> VisionFrame:
    base = datetime(2026, 1, 1) + timedelta(seconds=t)
    vf = VisionFrame(timestamp=base, width=1280, height=720)
    vf.hands = [hand]
    return vf


def test_v_sign_index_middle_extended_returns_v_sign() -> None:
    det = GestureDetector()
    result = det.feed(_frame_with_hand(_make_hand_v_sign(), t=0.0))
    assert "V_SIGN" in result


def test_v_sign_all_fingers_extended_no_trigger() -> None:
    det = GestureDetector()
    result = det.feed(_frame_with_hand(_make_hand_open_palm(), t=0.0))
    assert "V_SIGN" not in result


def test_v_sign_only_index_no_trigger() -> None:
    det = GestureDetector()
    result = det.feed(_frame_with_hand(_make_hand_point(), t=0.0))
    assert "V_SIGN" not in result
