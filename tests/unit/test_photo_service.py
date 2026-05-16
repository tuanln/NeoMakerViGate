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
