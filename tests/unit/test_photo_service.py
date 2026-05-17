"""Tests cho services/photo_service — orchestrator chụp ảnh + QR."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pytest

from neo_makervigate.core.models import PhotoResult
from neo_makervigate.core.share_server import ShareServer
from neo_makervigate.services.photo_service import PhotoService
from neo_makervigate.services.share_service import ShareService
from neo_makervigate.utils.signal_bus import SignalBus


class _FakeWorker:
    """Stub VisionWorker — only has latest_frame_bgr property."""

    def __init__(self, frame: np.ndarray[Any, Any] | None) -> None:
        self._frame = frame

    @property
    def latest_frame_bgr(self) -> np.ndarray[Any, Any] | None:
        return self._frame

    @property
    def latest_vision_frame(self) -> object | None:
        return None


def _make_frame(w: int = 640, h: int = 360) -> np.ndarray[Any, Any]:
    frame: np.ndarray[Any, Any] = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:, :, 1] = 200
    return frame


def _wait_for_port(server: ShareServer, timeout: float = 2.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if server.port is not None:
            return
        time.sleep(0.1)


@pytest.fixture
def share_setup(tmp_path: Path, qapp) -> tuple[ShareServer, ShareService]:
    server = ShareServer(photos_root=tmp_path)
    server.start()
    _wait_for_port(server)
    yield server, ShareService(server)
    server.stop()


def test_capture_request_with_no_frame_emits_failure(
    tmp_path: Path,
    share_setup: tuple[ShareServer, ShareService],
    qapp,
) -> None:
    _, share = share_setup
    worker = _FakeWorker(frame=None)
    _ = PhotoService(worker=worker, share=share, photos_base=tmp_path)  # type: ignore[arg-type]

    results: list[PhotoResult] = []
    SignalBus.instance().photo_captured.connect(lambda r: results.append(r))
    SignalBus.instance().photo_capture_requested.emit({"experience_id": "test"})
    qapp.processEvents()
    assert len(results) == 1
    assert results[0].success is False
    assert results[0].error_message is not None


def test_capture_request_emits_photo_captured_on_success(
    tmp_path: Path,
    share_setup: tuple[ShareServer, ShareService],
    qapp,
) -> None:
    _, share = share_setup
    worker = _FakeWorker(frame=_make_frame())
    _ = PhotoService(worker=worker, share=share, photos_base=tmp_path)  # type: ignore[arg-type]

    results: list[PhotoResult] = []
    SignalBus.instance().photo_captured.connect(lambda r: results.append(r))
    SignalBus.instance().photo_capture_requested.emit({"experience_id": "exp03_yoga_robot"})
    qapp.processEvents()
    assert len(results) == 1
    r = results[0]
    assert r.success is True
    assert r.experience_id == "exp03_yoga_robot"


def test_photo_result_has_url_and_qr_path(
    tmp_path: Path,
    share_setup: tuple[ShareServer, ShareService],
    qapp,
) -> None:
    _, share = share_setup
    worker = _FakeWorker(frame=_make_frame())
    _ = PhotoService(worker=worker, share=share, photos_base=tmp_path)  # type: ignore[arg-type]

    results: list[PhotoResult] = []
    SignalBus.instance().photo_captured.connect(lambda r: results.append(r))
    SignalBus.instance().photo_capture_requested.emit({"experience_id": "test"})
    qapp.processEvents()
    r = results[0]
    assert r.download_url is not None
    assert "http://" in r.download_url
    assert r.qr_path is not None
    assert r.qr_path.exists()
    assert r.original_path is not None
    assert r.original_path.exists()


def test_capture_with_experience_id_includes_in_path(
    tmp_path: Path,
    share_setup: tuple[ShareServer, ShareService],
    qapp,
) -> None:
    _, share = share_setup
    worker = _FakeWorker(frame=_make_frame())
    _ = PhotoService(worker=worker, share=share, photos_base=tmp_path)  # type: ignore[arg-type]

    results: list[PhotoResult] = []
    SignalBus.instance().photo_captured.connect(lambda r: results.append(r))
    SignalBus.instance().photo_capture_requested.emit({"experience_id": "exp01_wave_cricket"})
    qapp.processEvents()
    assert "_exp01_wave_cricket" in results[0].photo_id


def test_capture_failure_emits_with_error_message(
    tmp_path: Path,
    share_setup: tuple[ShareServer, ShareService],
    qapp,
) -> None:
    _, share = share_setup
    worker = _FakeWorker(frame=_make_frame())
    _ = PhotoService(worker=worker, share=share, photos_base=tmp_path)  # type: ignore[arg-type]

    results: list[PhotoResult] = []
    SignalBus.instance().photo_captured.connect(lambda r: results.append(r))

    with patch("neo_makervigate.core.photo_capture.cv2.imwrite", return_value=False):
        SignalBus.instance().photo_capture_requested.emit({"experience_id": "test"})
        qapp.processEvents()
    assert len(results) == 1
    assert results[0].success is False
    assert results[0].error_message is not None
    err = results[0].error_message.lower()
    assert "imwrite" in err or "failed" in err


class _FakeWorkerWithVf:
    """Stub with both latest_frame_bgr AND latest_vision_frame."""

    def __init__(self, frame: np.ndarray[Any, Any] | None, vf: object | None) -> None:
        self._frame = frame
        self._vf = vf

    @property
    def latest_frame_bgr(self) -> np.ndarray[Any, Any] | None:
        return self._frame

    @property
    def latest_vision_frame(self) -> object | None:
        return self._vf


def test_capture_with_background_produces_composite(
    tmp_path: Path,
    share_setup: tuple[ShareServer, ShareService],
    qapp,
) -> None:
    """When params include background_path AND selfie_mask is available → composite saved."""
    from datetime import datetime

    import cv2

    from neo_makervigate.core.models import VisionFrame

    _, share = share_setup
    fg = np.zeros((360, 640, 3), dtype=np.uint8)
    fg[:, :, 1] = 200
    vf = VisionFrame(
        timestamp=datetime.now(),
        width=640, height=360,
        selfie_mask=np.ones((360, 640), dtype=np.float32),
    )
    worker = _FakeWorkerWithVf(frame=fg, vf=vf)

    bg_path = tmp_path / "bg.png"
    bg = np.zeros((360, 640, 3), dtype=np.uint8)
    bg[:, :, 0] = 255
    cv2.imwrite(str(bg_path), bg)

    _ = PhotoService(worker=worker, share=share, photos_base=tmp_path)  # type: ignore[arg-type]

    results: list[PhotoResult] = []
    SignalBus.instance().photo_captured.connect(lambda r: results.append(r))
    SignalBus.instance().photo_capture_requested.emit({
        "experience_id": "exp06_photo_booth",
        "background_path": str(bg_path),
    })
    qapp.processEvents()
    assert len(results) == 1
    r = results[0]
    assert r.success is True
    assert r.composite_path is not None
    assert r.composite_path.exists()
    assert r.download_url is not None
    assert "composite.jpg" in r.download_url


def test_capture_without_background_skips_composite(
    tmp_path: Path,
    share_setup: tuple[ShareServer, ShareService],
    qapp,
) -> None:
    """No background_path in params → no composite, URL points to original."""
    _, share = share_setup
    fg = np.zeros((360, 640, 3), dtype=np.uint8)
    fg[:, :, 1] = 200
    worker = _FakeWorkerWithVf(frame=fg, vf=None)
    _ = PhotoService(worker=worker, share=share, photos_base=tmp_path)  # type: ignore[arg-type]

    results: list[PhotoResult] = []
    SignalBus.instance().photo_captured.connect(lambda r: results.append(r))
    SignalBus.instance().photo_capture_requested.emit({"experience_id": "exp01"})
    qapp.processEvents()
    assert results[0].composite_path is None
    assert results[0].download_url is not None
    assert "original.jpg" in results[0].download_url
