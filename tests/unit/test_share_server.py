"""Tests cho core/share_server — http.server QThread + QR generation."""

from __future__ import annotations

import socket
import time
import urllib.request
from pathlib import Path

import pytest

from neo_makervigate.core.share_server import (
    DEFAULT_PORT,
    ShareServer,
    generate_qr,
)


def _wait_for_port(server: ShareServer, timeout: float = 2.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if server.port is not None:
            return
        time.sleep(0.1)


def test_generate_qr_creates_png(tmp_path: Path) -> None:
    out = tmp_path / "qr.png"
    result = generate_qr("http://example.com/foo", out)
    assert result == out
    assert out.exists()
    with open(out, "rb") as f:
        header = f.read(8)
    assert header[:8] == b"\x89PNG\r\n\x1a\n"


def test_share_server_starts_on_default_port(tmp_path: Path, qapp) -> None:
    server = ShareServer(photos_root=tmp_path)
    server.start()
    _wait_for_port(server)
    try:
        assert server.port == DEFAULT_PORT
    finally:
        server.stop()


def test_share_server_falls_back_when_port_taken(tmp_path: Path, qapp) -> None:
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        blocker.bind(("0.0.0.0", DEFAULT_PORT))
        blocker.listen(1)
    except OSError:
        pytest.skip(f"Cannot bind port {DEFAULT_PORT} for test setup")
    try:
        server = ShareServer(photos_root=tmp_path)
        server.start()
        _wait_for_port(server)
        try:
            assert server.port is not None
            assert server.port != DEFAULT_PORT
            assert 8001 <= server.port <= 8010
        finally:
            server.stop()
    finally:
        blocker.close()


def test_get_download_url_format(tmp_path: Path, qapp) -> None:
    server = ShareServer(photos_root=tmp_path)
    server.start()
    _wait_for_port(server)
    try:
        url = server.get_download_url("photo_test", "original.jpg")
        assert "http://" in url
        assert "/photo_test/original.jpg" in url
        assert f":{server.port}/" in url
    finally:
        server.stop()


def test_serves_photo_file_via_http(tmp_path: Path, qapp) -> None:
    photo_dir = tmp_path / "photo_test"
    photo_dir.mkdir()
    test_content = b"fake-jpg-bytes-here"
    (photo_dir / "original.jpg").write_bytes(test_content)

    server = ShareServer(photos_root=tmp_path)
    server.start()
    _wait_for_port(server)
    try:
        url = f"http://127.0.0.1:{server.port}/photo_test/original.jpg"
        response = urllib.request.urlopen(url, timeout=2)
        body = response.read()
        assert body == test_content
        assert response.status == 200
    finally:
        server.stop()


def test_stop_closes_socket_cleanly(tmp_path: Path, qapp) -> None:
    server = ShareServer(photos_root=tmp_path)
    server.start()
    _wait_for_port(server)
    port = server.port
    server.stop()
    assert port is not None
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
    finally:
        sock.close()
