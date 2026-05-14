"""Pytest fixtures dùng chung."""

from __future__ import annotations

import os

import pytest

# Force offscreen Qt platform để test trên CI không cần display
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def _reset_signal_bus(qapp):
    """Mỗi test bắt đầu với SignalBus rỗng. qapp phải chạy trước reset
    vì deleteLater() cần Qt event loop."""
    from neo_makervigate.utils.signal_bus import SignalBus

    SignalBus.reset()
    yield
    SignalBus.reset()


@pytest.fixture
def qapp():
    """Qt application fixture — share giữa tests (Qt không cho re-init)."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
