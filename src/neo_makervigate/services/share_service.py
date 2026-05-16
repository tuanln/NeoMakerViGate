"""ShareService — facade quanh ShareServer cho service layer."""

from __future__ import annotations

from pathlib import Path

from neo_makervigate.core.share_server import ShareServer, generate_qr


class ShareService:
    def __init__(self, share_server: ShareServer) -> None:
        self._server = share_server

    def make_share_url(self, photo_id: str, filename: str = "original.jpg") -> str:
        return self._server.get_download_url(photo_id, filename)

    def make_qr(self, url: str, photo_dir: Path) -> Path:
        qr_path = photo_dir / "qr.png"
        return generate_qr(url, qr_path)
