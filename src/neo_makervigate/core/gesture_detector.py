"""GestureDetector — phát hiện cử chỉ rời rạc từ stream VisionFrame.

P3 chỉ implement WAVE (cổ tay dao động trái-phải > ngưỡng/1s). Phase sau
mở rộng V_SIGN, POINT, OPEN_PALM, T_POSE.

API tối giản: gọi `feed(frame)` mỗi VisionFrame, trả về list gesture mới
phát hiện. Đồng thời emit `SignalBus.gesture_detected` cho production.
Tách dual-path (return + emit) để test gọi `feed()` trực tiếp không cần Qt.
"""

from __future__ import annotations

import time
from collections import deque

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


class GestureDetector:
    """Stateful detector. 1 instance/session — reset() khi switch experience."""

    def __init__(self, window_seconds: float = WAVE_WINDOW_SEC) -> None:
        self._window = window_seconds
        self._buffer: deque[tuple[float, float]] = deque(maxlen=BUFFER_MAXLEN)
        self._cooldown_until: float = 0.0
        self._none_count = 0

    def feed(self, frame: VisionFrame) -> list[str]:
        """Cho ăn 1 frame. Trả về list gesture mới phát hiện trong frame này."""
        now = frame.timestamp.timestamp()

        if not frame.hands:
            self._none_count += 1
            if self._none_count > BUFFER_MAXLEN // 2:
                self._buffer.clear()
                self._none_count = 0
            return []

        self._none_count = 0
        wrist_x = frame.hands[0][0].x
        self._buffer.append((now, wrist_x))

        # Drop samples older than window
        cutoff = now - self._window
        while self._buffer and self._buffer[0][0] < cutoff:
            self._buffer.popleft()

        if len(self._buffer) < WAVE_MIN_SAMPLES:
            return []

        if now < self._cooldown_until:
            return []

        return self._check_wave(now)

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
        self._none_count = 0
        # Workaround mypy: dùng time để tránh "unused import"
        _ = time
