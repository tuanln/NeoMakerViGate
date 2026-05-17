"""Tests cho services/qwen_service — QThread wrapper for Qwen inference."""

from __future__ import annotations

import time
from pathlib import Path

from neo_makervigate.services.qwen_service import QwenService
from neo_makervigate.utils.signal_bus import SignalBus


class _FakeBackend:
    """Backend stub that returns a canned response or raises."""

    def __init__(self, response: str = "Một bức ảnh!", raise_exc: Exception | None = None) -> None:
        self._response = response
        self._raise = raise_exc
        self.calls: list[dict] = []

    def is_ready(self) -> bool:
        return True

    def describe_image(self, image_path: Path, prompt: str, max_tokens: int = 80) -> str:
        self.calls.append({"image_path": image_path, "prompt": prompt, "max_tokens": max_tokens})
        if self._raise:
            raise self._raise
        return self._response


def _wait_signal(events: list, timeout: float = 2.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline and not events:
        time.sleep(0.05)


def test_qwen_service_calls_backend_via_signal(tmp_path: Path, qapp) -> None:
    backend = _FakeBackend(response="Em đứng cười tươi! 🌞")
    svc = QwenService(client=backend)
    try:
        responses: list[str] = []
        SignalBus.instance().qwen_response_ready.connect(lambda t: responses.append(t))
        img = tmp_path / "x.jpg"
        img.write_bytes(b"fake")
        SignalBus.instance().qwen_request_started.emit({
            "image_path": str(img),
            "prompt": "Mô tả ảnh",
            "max_tokens": 50,
        })
        _wait_signal(responses)
        qapp.processEvents()
        assert len(backend.calls) == 1
        assert backend.calls[0]["prompt"] == "Mô tả ảnh"
        assert responses == ["Em đứng cười tươi! 🌞"]
    finally:
        svc.stop()


def test_qwen_service_emits_response_on_success(tmp_path: Path, qapp) -> None:
    backend = _FakeBackend(response="caption ok")
    svc = QwenService(client=backend)
    try:
        responses: list[str] = []
        failures: list[str] = []
        SignalBus.instance().qwen_response_ready.connect(lambda t: responses.append(t))
        SignalBus.instance().qwen_failed.connect(lambda e: failures.append(e))
        img = tmp_path / "y.jpg"
        img.write_bytes(b"fake")
        SignalBus.instance().qwen_request_started.emit({
            "image_path": str(img), "prompt": "p",
        })
        _wait_signal(responses)
        qapp.processEvents()
        assert responses == ["caption ok"]
        assert failures == []
    finally:
        svc.stop()


def test_qwen_service_emits_failed_on_exception(tmp_path: Path, qapp) -> None:
    backend = _FakeBackend(raise_exc=RuntimeError("model crashed"))
    svc = QwenService(client=backend)
    try:
        failures: list[str] = []
        SignalBus.instance().qwen_failed.connect(lambda e: failures.append(e))
        img = tmp_path / "z.jpg"
        img.write_bytes(b"fake")
        SignalBus.instance().qwen_request_started.emit({
            "image_path": str(img), "prompt": "p",
        })
        _wait_signal(failures)
        qapp.processEvents()
        assert len(failures) == 1
        assert "model crashed" in failures[0]
    finally:
        svc.stop()


def test_qwen_service_stop_terminates_thread_cleanly(qapp) -> None:
    backend = _FakeBackend()
    svc = QwenService(client=backend)
    svc.stop()
    assert not svc._worker.isRunning()  # type: ignore[attr-defined]
