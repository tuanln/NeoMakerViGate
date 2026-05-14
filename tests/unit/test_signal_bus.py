"""Smoke test cho SignalBus — Phase 0 baseline."""

from __future__ import annotations

from neo_makervigate.utils.signal_bus import SignalBus


def test_signal_bus_is_singleton(qapp) -> None:
    bus1 = SignalBus.instance()
    bus2 = SignalBus.instance()
    assert bus1 is bus2


def test_gesture_signal_fires(qapp) -> None:
    bus = SignalBus.instance()
    received: list[str] = []

    bus.gesture_detected.connect(received.append)
    bus.gesture_detected.emit("WAVE")

    assert received == ["WAVE"]


def test_status_message_payload(qapp) -> None:
    bus = SignalBus.instance()
    received: list[tuple[str, str]] = []

    bus.status_message.connect(lambda lvl, msg: received.append((lvl, msg)))
    bus.status_message.emit("info", "ready")

    assert received == [("info", "ready")]
