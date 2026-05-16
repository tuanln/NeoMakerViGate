"""Tests cho utils/network — local IP lookup."""

from __future__ import annotations

import socket
from unittest.mock import patch

from neo_makervigate.utils.network import get_local_ip


def test_get_local_ip_returns_ipv4_string() -> None:
    ip = get_local_ip()
    parts = ip.split(".")
    assert len(parts) == 4
    for p in parts:
        assert 0 <= int(p) <= 255


def test_get_local_ip_fallback_to_loopback_on_error() -> None:
    """Khi socket.connect raise OSError → fallback 127.0.0.1."""
    with patch.object(socket.socket, "connect", side_effect=OSError("no network")):
        ip = get_local_ip()
        assert ip == "127.0.0.1"
