"""GestureDetector — phát hiện cử chỉ rời rạc từ stream VisionFrame.

P3 chỉ implement WAVE (cổ tay dao động trái-phải > ngưỡng/1s). Phase sau
mở rộng V_SIGN, POINT, OPEN_PALM, T_POSE.

API tối giản: gọi `feed(frame)` mỗi VisionFrame, trả về list gesture mới
phát hiện. Đồng thời emit `SignalBus.gesture_detected` cho production.
Tách dual-path (return + emit) để test gọi `feed()` trực tiếp không cần Qt.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Any

from loguru import logger

from neo_makervigate.core.models import VisionFrame
from neo_makervigate.utils.signal_bus import SignalBus

# Tunable constants — sẽ tune ở P7 trên NEO One nếu cần
WAVE_WINDOW_SEC = 1.0
WAVE_MIN_AMPLITUDE = 0.05  # 5% screen width normalized
WAVE_MIN_CROSSINGS = 2
WAVE_COOLDOWN_SEC = 0.4
WAVE_MIN_SAMPLES = 8
BUFFER_MAXLEN = 60  # ~2s @ 30fps

V_SIGN_COOLDOWN_SEC = 0.4
V_SIGN_FINGER_MARGIN = 1.05


def _finger_dist_from_wrist(hand: list[Any], idx: int) -> float:
    """Euclidean distance from wrist (idx 0) to landmark at idx."""
    wrist = hand[0]
    pt = hand[idx]
    return math.sqrt((pt.x - wrist.x) ** 2 + (pt.y - wrist.y) ** 2)


def _is_finger_extended(hand: list[Any], tip_idx: int, pip_idx: int) -> bool:
    """Finger extended if tip is farther from wrist than its PIP joint."""
    tip_dist = _finger_dist_from_wrist(hand, tip_idx)
    pip_dist = _finger_dist_from_wrist(hand, pip_idx)
    return tip_dist > pip_dist * V_SIGN_FINGER_MARGIN


def _check_v_sign(hand: list[Any]) -> bool:
    """V-sign: index + middle extended, ring + pinky curled."""
    if len(hand) < 21:
        return False
    index_ext = _is_finger_extended(hand, 8, 6)
    middle_ext = _is_finger_extended(hand, 12, 10)
    ring_ext = _is_finger_extended(hand, 16, 14)
    pinky_ext = _is_finger_extended(hand, 20, 18)
    return index_ext and middle_ext and not ring_ext and not pinky_ext


class GestureDetector:
    """Stateful detector. 1 instance/session — reset() khi switch experience."""

    def __init__(self, window_seconds: float = WAVE_WINDOW_SEC) -> None:
        self._window = window_seconds
        self._buffer: deque[tuple[float, float]] = deque(maxlen=BUFFER_MAXLEN)
        self._cooldown_until: float = 0.0
        self._v_sign_cooldown_until: float = 0.0
        self._none_count: int = 0

    def feed(self, frame: VisionFrame) -> list[str]:
        """Cho ăn 1 frame. Trả về list gesture mới phát hiện trong frame này."""
        now = frame.timestamp.timestamp()
        gestures: list[str] = []

        if not frame.hands:
            self._none_count += 1
            if self._none_count > BUFFER_MAXLEN // 2:
                self._buffer.clear()
                self._none_count = 0
            return gestures

        self._none_count = 0
        first_hand = frame.hands[0]

        # V_SIGN — pose check, no buffer needed
        if now >= self._v_sign_cooldown_until and _check_v_sign(first_hand):
            self._v_sign_cooldown_until = now + V_SIGN_COOLDOWN_SEC
            try:
                SignalBus.instance().gesture_detected.emit("V_SIGN")
            except Exception as e:
                logger.warning(f"gesture_detected V_SIGN emit failed: {e}")
            gestures.append("V_SIGN")

        # WAVE — buffer-based motion check
        wrist_x = first_hand[0].x
        self._buffer.append((now, wrist_x))
        cutoff = now - self._window
        while self._buffer and self._buffer[0][0] < cutoff:
            self._buffer.popleft()
        if len(self._buffer) >= WAVE_MIN_SAMPLES and now >= self._cooldown_until:
            wave_result = self._check_wave(now)
            gestures.extend(wave_result)

        return gestures

    def _check_wave(self, now: float) -> list[str]:
        xs = [x for _, x in self._buffer]
        baseline = sum(xs) / len(xs)
        dxs = [x - baseline for x in xs]
        amplitude = max(dxs) - min(dxs)
        crossings = sum(1 for i in range(1, len(dxs)) if dxs[i - 1] * dxs[i] < 0)

        if crossings >= WAVE_MIN_CROSSINGS and amplitude >= WAVE_MIN_AMPLITUDE:
            self._cooldown_until = now + WAVE_COOLDOWN_SEC
            # Half-clear buffer để không re-trigger từ cùng pattern
            half = len(self._buffer) // 2
            for _ in range(half):
                self._buffer.popleft()
            try:
                SignalBus.instance().gesture_detected.emit("WAVE")
            except Exception as e:
                logger.warning(f"gesture_detected emit failed: {e}")
            return ["WAVE"]
        return []

    def reset(self) -> None:
        """Xóa buffer khi switch experience để không carry pattern qua trải nghiệm mới."""
        self._buffer.clear()
        self._cooldown_until = 0.0
        self._v_sign_cooldown_until = 0.0
        self._none_count = 0
