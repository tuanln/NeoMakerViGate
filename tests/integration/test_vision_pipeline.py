"""Integration test — VisionSimulator → SignalBus → AppController.

Không cần QML hay webcam thật. Chạy QThread thực ~500ms, verify:
1. SignalBus.vision_camera_ready fire
2. AppController nhận vision_frame_ready và update FPS
3. AppController.cameraConnected = True
"""

from __future__ import annotations

import time

import pytest

from neo_makervigate.core.vision_simulator import VisionSimulator
from neo_makervigate.core.vision_worker import VisionWorker
from neo_makervigate.services.app_controller import AppController
from neo_makervigate.utils.signal_bus import SignalBus


@pytest.mark.integration
def test_simulator_to_controller_pipeline(qapp) -> None:
    """Wiring end-to-end: Simulator → Worker → SignalBus → AppController."""
    bus = SignalBus.instance()
    camera_ready_count = [0]

    def _on_ready() -> None:
        camera_ready_count[0] += 1

    bus.vision_camera_ready.connect(_on_ready)

    controller = AppController()
    source = VisionSimulator(width=320, height=180)  # nhỏ cho nhanh
    worker = VisionWorker(source, initial_modules=["hands"])

    worker.start()

    # Cho worker chạy ~600ms — đủ để generate ≥15 frame ở 30fps
    end = time.perf_counter() + 0.6
    while time.perf_counter() < end:
        qapp.processEvents()
        time.sleep(0.02)

    worker.stop()
    # Drain remaining events
    qapp.processEvents()

    assert camera_ready_count[0] == 1, "vision_camera_ready phải fire đúng 1 lần"
    assert controller.cameraConnected is True
    # Simulator blank mode: không sinh hand landmarks → hands rỗng nhưng FPS > 0
    assert controller.visionFps > 0.0, f"Expected FPS > 0, got {controller.visionFps}"
