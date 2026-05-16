"""Lấy local IP cho ShareServer URL."""

from __future__ import annotations

import socket


def get_local_ip() -> str:
    """Trả local LAN IP (vd 192.168.1.42). Fallback 127.0.0.1 nếu offline.

    Trick: kết nối UDP đến 8.8.8.8 — không thực sự gửi packet, chỉ để
    OS bind socket với IP outbound.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip: str = s.getsockname()[0]
        return ip
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()
