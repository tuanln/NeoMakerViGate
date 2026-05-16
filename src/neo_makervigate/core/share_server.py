"""ShareServer — http.server background phục vụ ảnh trong LAN + QR generator.

Pattern: QThread chạy http.server.ThreadingHTTPServer.serve_forever().
Stop bằng shutdown() từ thread khác.

Port fixed 8000, fallback 8001-8010 nếu conflict.
"""

from __future__ import annotations

import http.server
import threading
from pathlib import Path
from typing import Any

import qrcode
from loguru import logger
from PyQt6.QtCore import QThread

from neo_makervigate.utils.network import get_local_ip

DEFAULT_PORT = 8000
FALLBACK_PORTS = range(8001, 8011)
QR_BOX_SIZE = 10
QR_BORDER = 2


class _PhotosHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTP serving from a fixed directory (passed via factory)."""

    photos_root: Path  # set by factory

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(self.__class__.photos_root), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug(f"share-http: {format % args}")


def _make_handler_class(photos_root: Path) -> type[_PhotosHandler]:
    """Build a fresh subclass binding photos_root."""
    return type(
        "_BoundPhotosHandler",
        (_PhotosHandler,),
        {"photos_root": photos_root},
    )


class ShareServer(QThread):
    """QThread wrapper http.server.ThreadingHTTPServer."""

    def __init__(self, photos_root: Path) -> None:
        super().__init__()
        self._photos_root = photos_root
        self._photos_root.mkdir(parents=True, exist_ok=True)
        self._server: http.server.ThreadingHTTPServer | None = None
        self._port: int | None = None
        self._lock = threading.Lock()
        self._ip = get_local_ip()

    @property
    def port(self) -> int | None:
        with self._lock:
            return self._port

    @property
    def ip(self) -> str:
        return self._ip

    def get_download_url(self, photo_id: str, filename: str = "original.jpg") -> str:
        port = self.port or DEFAULT_PORT
        return f"http://{self._ip}:{port}/{photo_id}/{filename}"

    def _try_bind(self, port: int) -> http.server.ThreadingHTTPServer | None:
        handler_cls = _make_handler_class(self._photos_root)
        try:
            return http.server.ThreadingHTTPServer(("0.0.0.0", port), handler_cls)
        except OSError as e:
            logger.warning(f"Port {port} unavailable: {e}")
            return None

    def run(self) -> None:
        for port in [DEFAULT_PORT, *FALLBACK_PORTS]:
            server = self._try_bind(port)
            if server is not None:
                with self._lock:
                    self._server = server
                    self._port = port
                logger.info(f"ShareServer listening on http://{self._ip}:{port}/")
                break
        else:
            logger.error("ShareServer: no port available in 8000-8010")
            return

        with self._lock:
            server = self._server
        if server is None:
            return
        try:
            server.serve_forever(poll_interval=0.5)
        except Exception as e:
            logger.exception(f"ShareServer crashed: {e}")
        finally:
            logger.info("ShareServer loop ended")

    def stop(self) -> None:
        with self._lock:
            server = self._server
        if server is not None:
            server.shutdown()
            server.server_close()
        self.wait(2000)


def generate_qr(url: str, out_path: Path) -> Path:
    """Sinh QR PNG cho URL. Trả về out_path."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=QR_BOX_SIZE,
        border=QR_BORDER,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(out_path)
    return out_path
