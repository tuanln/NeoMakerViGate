# P5 — PhotoCapture + ShareServer + QR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build cross-experience photo capture + LAN share via QR. New core services: PhotoCapture (cv2.imwrite), ShareServer (http.server QThread serving `~/makervigate/photos/`), QR generator (qrcode + Pillow). Auto-capture vào RESULT phase exp03. Parent scans QR with Zalo → download photo to phone.

**Architecture:** ShareServer starts at app boot on port 8000 (fallback 8001-8010). When YogaRobotExperience reaches Phase.DONE, ExperienceManager emits `photo_capture_requested`; PhotoService snaps `VisionWorker.latest_frame_bgr`, saves JPG + QR PNG to `~/makervigate/photos/<photo_id>/`, then emits `photo_captured`. AppController pushes PhotoReviewPage showing photo + QR. LRU cleanup at 200MB.

**Tech Stack:** Python 3.12, PyQt6 6.11, OpenCV (cv2.imwrite), qrcode[pil] (already in deps), http.server stdlib, QThread, pytest + pytest-qt.

**Reference spec:** `docs/superpowers/specs/2026-05-16-p5-photo-share-design.md`

---

## File Structure

**New files:**
- `src/neo_makervigate/utils/network.py` — `get_local_ip()`
- `src/neo_makervigate/utils/storage.py` — `cleanup_if_over_limit()`
- `src/neo_makervigate/core/photo_capture.py` — `PhotoCapture` class
- `src/neo_makervigate/core/share_server.py` — `ShareServer` QThread + `generate_qr()`
- `src/neo_makervigate/services/photo_service.py` — orchestrator
- `src/neo_makervigate/services/share_service.py` — facade
- `src/neo_makervigate/ui/qml/pages/PhotoReviewPage.qml`
- `tests/unit/test_network.py`
- `tests/unit/test_storage.py`
- `tests/unit/test_photo_capture.py`
- `tests/unit/test_share_server.py`
- `tests/unit/test_photo_service.py`

**Modified files:**
- `src/neo_makervigate/services/app_controller.py` — `photoResult` + `photoReviewRequested`
- `src/neo_makervigate/services/experience_manager.py` — phase=done → photo_capture_requested + unload
- `src/neo_makervigate/app.py` — instantiate ShareServer + services
- `src/neo_makervigate/ui/qml/MainWindow.qml` — PhotoReviewPage component + Connections
- `DOC/PHASES.md` — mark P5 done

---

## Task 1: utils/network.py — get_local_ip

**Files:**
- Create: `tests/unit/test_network.py`
- Create: `src/neo_makervigate/utils/network.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_network.py`:

```python
"""Tests cho utils/network — local IP lookup."""

from __future__ import annotations

import socket
from unittest.mock import patch

from neo_makervigate.utils.network import get_local_ip


def test_get_local_ip_returns_ipv4_string() -> None:
    ip = get_local_ip()
    # IPv4 dotted quad, hoặc fallback 127.0.0.1
    parts = ip.split(".")
    assert len(parts) == 4
    for p in parts:
        assert 0 <= int(p) <= 255


def test_get_local_ip_fallback_to_loopback_on_error() -> None:
    """Khi socket.connect raise OSError → fallback 127.0.0.1."""
    with patch.object(socket.socket, "connect", side_effect=OSError("no network")):
        ip = get_local_ip()
        assert ip == "127.0.0.1"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_network.py -v
```
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 3: Create network.py**

Create `src/neo_makervigate/utils/network.py`:

```python
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
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_network.py -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: 2 tests PASS, lint clean.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_network.py src/neo_makervigate/utils/network.py
git commit -m "$(cat <<'EOF'
feat(p5): utils/network — get_local_ip with loopback fallback

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: utils/storage.py — LRU cleanup

**Files:**
- Create: `tests/unit/test_storage.py`
- Create: `src/neo_makervigate/utils/storage.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_storage.py`:

```python
"""Tests cho utils/storage — LRU cleanup photos directory."""

from __future__ import annotations

import os
from pathlib import Path

from neo_makervigate.utils.storage import cleanup_if_over_limit


def _make_folder_with_data(base: Path, name: str, size_kb: int, mtime: float) -> Path:
    folder = base / name
    folder.mkdir(parents=True, exist_ok=True)
    f = folder / "data.bin"
    f.write_bytes(b"\x00" * (size_kb * 1024))
    os.utime(folder, (mtime, mtime))
    os.utime(f, (mtime, mtime))
    return folder


def test_dir_size_zero_when_empty(tmp_path: Path) -> None:
    assert cleanup_if_over_limit(tmp_path / "empty", max_mb=200) == 0


def test_cleanup_does_nothing_under_limit(tmp_path: Path) -> None:
    _make_folder_with_data(tmp_path, "a", size_kb=10, mtime=1000)
    _make_folder_with_data(tmp_path, "b", size_kb=10, mtime=2000)
    deleted = cleanup_if_over_limit(tmp_path, max_mb=1)
    assert deleted == 0
    assert (tmp_path / "a").exists()
    assert (tmp_path / "b").exists()


def test_cleanup_removes_oldest_folder_first(tmp_path: Path) -> None:
    # 3 folders, each 400KB, limit 1MB (~1024KB) → must remove 1 (oldest)
    _make_folder_with_data(tmp_path, "old", size_kb=400, mtime=1000)
    _make_folder_with_data(tmp_path, "mid", size_kb=400, mtime=2000)
    _make_folder_with_data(tmp_path, "new", size_kb=400, mtime=3000)
    # Limit = 1MB (after cleanup, must be under 1024KB; 2 folders × 400KB = 800KB OK)
    # We use max_mb=1 — boundary check: 1200KB > 1024 → cleanup
    deleted = cleanup_if_over_limit(tmp_path, max_mb=1)
    assert deleted >= 1
    assert not (tmp_path / "old").exists()
    assert (tmp_path / "new").exists()


def test_cleanup_stops_when_under_limit(tmp_path: Path) -> None:
    # 4 folders × 400KB = 1600KB. max=1MB. Must delete enough to get <= 1024KB.
    # After 1 delete: 1200KB still > 1024 → delete another. After 2 deletes: 800KB OK.
    _make_folder_with_data(tmp_path, "a", size_kb=400, mtime=1000)
    _make_folder_with_data(tmp_path, "b", size_kb=400, mtime=2000)
    _make_folder_with_data(tmp_path, "c", size_kb=400, mtime=3000)
    _make_folder_with_data(tmp_path, "d", size_kb=400, mtime=4000)
    cleanup_if_over_limit(tmp_path, max_mb=1)
    # Newest "d" must survive
    assert (tmp_path / "d").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_storage.py -v
```
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 3: Create storage.py**

Create `src/neo_makervigate/utils/storage.py`:

```python
"""LRU cleanup cho photos directory.

cleanup_if_over_limit():
  1. Đo tổng size photos/
  2. Nếu > MAX_PHOTOS_STORAGE_MB: xóa folder cũ nhất (theo mtime) cho tới khi < limit
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

MAX_PHOTOS_STORAGE_MB = 200


def _dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def cleanup_if_over_limit(photos_base: Path, max_mb: int = MAX_PHOTOS_STORAGE_MB) -> int:
    """Trả về số folder đã xóa. LRU: xóa folder có mtime cũ nhất trước."""
    if not photos_base.exists():
        return 0
    total_bytes = _dir_size_bytes(photos_base)
    limit_bytes = max_mb * 1024 * 1024
    if total_bytes <= limit_bytes:
        return 0
    folders = sorted(
        [d for d in photos_base.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
    )
    deleted = 0
    for folder in folders:
        if total_bytes <= limit_bytes:
            break
        folder_size = _dir_size_bytes(folder)
        for f in folder.rglob("*"):
            if f.is_file():
                f.unlink()
        folder.rmdir()
        total_bytes -= folder_size
        deleted += 1
        logger.info(f"Cleaned up photo folder: {folder.name}")
    return deleted
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_storage.py -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: 4 tests PASS, clean.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_storage.py src/neo_makervigate/utils/storage.py
git commit -m "$(cat <<'EOF'
feat(p5): utils/storage — LRU cleanup photos by mtime

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: core/photo_capture.py — PhotoCapture class

**Files:**
- Create: `tests/unit/test_photo_capture.py`
- Create: `src/neo_makervigate/core/photo_capture.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_photo_capture.py`:

```python
"""Tests cho core/photo_capture — JPG snapshot saving."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from neo_makervigate.core.photo_capture import PhotoCapture


def _make_frame(w: int = 1280, h: int = 720) -> np.ndarray:
    # Synthetic BGR frame — solid blue (BGR = (255, 0, 0))
    frame: np.ndarray = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:, :, 0] = 255
    return frame


def test_make_photo_id_format(tmp_path: Path) -> None:
    pc = PhotoCapture(base_dir=tmp_path)
    pid = pc.make_photo_id()
    assert pid.startswith("photo_")
    parts = pid.split("_")
    # photo_YYYYMMDD_HHMMSS → 3 parts
    assert len(parts) == 3
    assert len(parts[1]) == 8   # YYYYMMDD
    assert len(parts[2]) == 6   # HHMMSS


def test_make_photo_id_with_experience(tmp_path: Path) -> None:
    pc = PhotoCapture(base_dir=tmp_path)
    pid = pc.make_photo_id("exp03_yoga_robot")
    assert pid.endswith("_exp03_yoga_robot")
    assert pid.startswith("photo_")


def test_make_photo_dir_creates_folder(tmp_path: Path) -> None:
    pc = PhotoCapture(base_dir=tmp_path)
    photo_id = "photo_test"
    d = pc.make_photo_dir(photo_id)
    assert d.exists()
    assert d.is_dir()
    assert d.parent == tmp_path


def test_save_original_writes_jpg(tmp_path: Path) -> None:
    pc = PhotoCapture(base_dir=tmp_path)
    photo_dir = pc.make_photo_dir("photo_t1")
    frame = _make_frame()
    path = pc.save_original(frame, photo_dir)
    assert path == photo_dir / "original.jpg"
    assert path.exists()
    # JPG header magic bytes: 0xFF 0xD8 0xFF
    with open(path, "rb") as f:
        header = f.read(3)
    assert header[:3] == b"\xff\xd8\xff"


def test_save_original_with_invalid_path_raises(tmp_path: Path) -> None:
    pc = PhotoCapture(base_dir=tmp_path)
    frame = _make_frame()
    # Write to a non-existent + non-writable directory
    bad_dir = tmp_path / "does_not_exist_xyz"
    # Don't mkdir — save_original should fail
    with pytest.raises(Exception):
        pc.save_original(frame, bad_dir)


def test_save_original_jpg_size_reasonable(tmp_path: Path) -> None:
    """1280x720 solid color JPG should be < 100KB at quality 90."""
    pc = PhotoCapture(base_dir=tmp_path)
    photo_dir = pc.make_photo_dir("photo_t2")
    frame = _make_frame()
    path = pc.save_original(frame, photo_dir)
    size = path.stat().st_size
    assert 1000 < size < 100_000, f"JPG size {size} out of expected range"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_photo_capture.py -v
```
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 3: Create photo_capture.py**

Create `src/neo_makervigate/core/photo_capture.py`:

```python
"""PhotoCapture — lưu khung hình hiện tại thành JPG.

Stateless: nhận BGR frame + thư mục đích, lưu original.jpg.
Không truy cập webcam trực tiếp — frame được pass từ VisionWorker.latest_frame_bgr.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np


DEFAULT_PHOTOS_DIR = Path.home() / "makervigate" / "photos"
JPG_QUALITY = 90


class PhotoCapture:
    """Helper class — pure functions wrapped for testability."""

    def __init__(self, base_dir: Path = DEFAULT_PHOTOS_DIR) -> None:
        self._base = base_dir
        self._base.mkdir(parents=True, exist_ok=True)

    def make_photo_id(self, experience_id: str = "") -> str:
        """Sinh photo_id từ timestamp + experience_id."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{experience_id}" if experience_id else ""
        return f"photo_{ts}{suffix}"

    def make_photo_dir(self, photo_id: str) -> Path:
        d = self._base / photo_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_original(
        self,
        frame_bgr: np.ndarray[Any, Any],
        photo_dir: Path,
    ) -> Path:
        """Lưu frame BGR thành original.jpg ở photo_dir/. Trả về path."""
        if not photo_dir.exists():
            raise FileNotFoundError(f"photo_dir does not exist: {photo_dir}")
        path = photo_dir / "original.jpg"
        ok = cv2.imwrite(str(path), frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, JPG_QUALITY])
        if not ok:
            raise RuntimeError(f"cv2.imwrite failed: {path}")
        return path
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_photo_capture.py -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_photo_capture.py src/neo_makervigate/core/photo_capture.py
git commit -m "$(cat <<'EOF'
feat(p5): PhotoCapture class — JPG save + photo_id + dir helpers

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: core/share_server.py — ShareServer QThread + generate_qr

**Files:**
- Create: `tests/unit/test_share_server.py`
- Create: `src/neo_makervigate/core/share_server.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_share_server.py`:

```python
"""Tests cho core/share_server — http.server QThread + QR generation."""

from __future__ import annotations

import socket
import urllib.request
from pathlib import Path

import pytest

from neo_makervigate.core.share_server import (
    DEFAULT_PORT,
    ShareServer,
    generate_qr,
)


def test_generate_qr_creates_png(tmp_path: Path) -> None:
    out = tmp_path / "qr.png"
    result = generate_qr("http://example.com/foo", out)
    assert result == out
    assert out.exists()
    # PNG magic bytes
    with open(out, "rb") as f:
        header = f.read(8)
    assert header[:8] == b"\x89PNG\r\n\x1a\n"


def test_share_server_starts_on_default_port(tmp_path: Path, qapp) -> None:
    server = ShareServer(photos_root=tmp_path)
    server.start()
    # Wait up to 2s for server thread to bind
    import time
    for _ in range(20):
        if server.port is not None:
            break
        time.sleep(0.1)
    try:
        assert server.port == DEFAULT_PORT
    finally:
        server.stop()


def test_share_server_falls_back_when_port_taken(tmp_path: Path, qapp) -> None:
    # Pre-bind DEFAULT_PORT
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
        import time
        for _ in range(20):
            if server.port is not None:
                break
            time.sleep(0.1)
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
    import time
    for _ in range(20):
        if server.port is not None:
            break
        time.sleep(0.1)
    try:
        url = server.get_download_url("photo_test", "original.jpg")
        assert "http://" in url
        assert "/photo_test/original.jpg" in url
        assert f":{server.port}/" in url
    finally:
        server.stop()


def test_serves_photo_file_via_http(tmp_path: Path, qapp) -> None:
    # Setup file before starting
    photo_dir = tmp_path / "photo_test"
    photo_dir.mkdir()
    test_content = b"fake-jpg-bytes-here"
    (photo_dir / "original.jpg").write_bytes(test_content)

    server = ShareServer(photos_root=tmp_path)
    server.start()
    import time
    for _ in range(20):
        if server.port is not None:
            break
        time.sleep(0.1)
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
    import time
    for _ in range(20):
        if server.port is not None:
            break
        time.sleep(0.1)
    port = server.port
    server.stop()
    # After stop, port must be free — rebind should succeed
    assert port is not None
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
    finally:
        sock.close()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_share_server.py -v
```
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 3: Create share_server.py**

Create `src/neo_makervigate/core/share_server.py`:

```python
"""ShareServer — http.server background phục vụ ảnh trong LAN + QR generator.

Pattern: QThread chạy http.server.ThreadingHTTPServer.serve_forever().
Stop bằng shutdown() từ thread khác.

Port fixed 8000, fallback 8001-8010 nếu conflict.
"""

from __future__ import annotations

import http.server
import socketserver
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
        # Silence default stderr logging; use loguru instead
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
        self._server: socketserver.ThreadingTCPServer | None = None
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
        """URL cho phụ huynh quét."""
        port = self.port or DEFAULT_PORT
        return f"http://{self._ip}:{port}/{photo_id}/{filename}"

    def _try_bind(self, port: int) -> socketserver.ThreadingTCPServer | None:
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
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_share_server.py -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: 6 tests PASS, lint clean.

If `test_share_server_falls_back_when_port_taken` SKIPs in your environment, that's OK (port 8000 may be in use locally by another service). The fallback logic is still verified by running the test in a clean environment.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_share_server.py src/neo_makervigate/core/share_server.py
git commit -m "$(cat <<'EOF'
feat(p5): ShareServer QThread + generate_qr (port 8000 + fallback)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: services/share_service.py — facade

**Files:**
- Create: `src/neo_makervigate/services/share_service.py`

- [ ] **Step 1: Create share_service.py**

This is a thin facade — no separate test file needed (covered by PhotoService tests in T6).

Create `src/neo_makervigate/services/share_service.py`:

```python
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
```

- [ ] **Step 2: Verify lint + types**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/services/share_service.py
git commit -m "$(cat <<'EOF'
feat(p5): ShareService facade for ShareServer + QR generation

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: services/photo_service.py — orchestrator

**Files:**
- Create: `tests/unit/test_photo_service.py`
- Create: `src/neo_makervigate/services/photo_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_photo_service.py`:

```python
"""Tests cho services/photo_service — orchestrator chụp ảnh + QR."""

from __future__ import annotations

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
    frame[:, :, 1] = 200  # greenish
    return frame


@pytest.fixture
def share_setup(tmp_path: Path, qapp) -> tuple[ShareServer, ShareService]:
    server = ShareServer(photos_root=tmp_path)
    server.start()
    import time
    for _ in range(20):
        if server.port is not None:
            break
        time.sleep(0.1)
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

    # Patch cv2.imwrite to return False (simulate write failure)
    with patch("neo_makervigate.core.photo_capture.cv2.imwrite", return_value=False):
        SignalBus.instance().photo_capture_requested.emit({"experience_id": "test"})
        qapp.processEvents()
    assert len(results) == 1
    assert results[0].success is False
    assert results[0].error_message is not None
    assert "imwrite" in results[0].error_message.lower() or "failed" in results[0].error_message.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_photo_service.py -v
```
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 3: Create photo_service.py**

Create `src/neo_makervigate/services/photo_service.py`:

```python
"""PhotoService — orchestrate flow chụp ảnh + sinh QR.

Listens: SignalBus.photo_capture_requested(dict)
Emits: SignalBus.photo_captured(PhotoResult)

Sequence:
  1. Lấy frame từ VisionWorker.latest_frame_bgr (P1 API)
  2. PhotoCapture: tạo photo_id + folder + lưu original.jpg
  3. ShareService: build URL + sinh qr.png
  4. LRU cleanup nếu storage > 200MB
  5. emit photo_captured(PhotoResult)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from neo_makervigate.core.models import PhotoResult
from neo_makervigate.core.photo_capture import DEFAULT_PHOTOS_DIR, PhotoCapture
from neo_makervigate.utils.signal_bus import SignalBus
from neo_makervigate.utils.storage import cleanup_if_over_limit

if TYPE_CHECKING:
    from neo_makervigate.core.vision_worker import VisionWorker
    from neo_makervigate.services.share_service import ShareService


class PhotoService:
    def __init__(
        self,
        worker: VisionWorker,
        share: ShareService,
        photos_base: Path = DEFAULT_PHOTOS_DIR,
    ) -> None:
        self._worker = worker
        self._share = share
        self._photos_base = photos_base
        self._capture = PhotoCapture(base_dir=photos_base)
        SignalBus.instance().photo_capture_requested.connect(self._on_capture_request)

    def _on_capture_request(self, params: object) -> None:
        if isinstance(params, dict):
            exp_id_raw = params.get("experience_id", "")
            experience_id = str(exp_id_raw) if exp_id_raw is not None else ""
        else:
            experience_id = ""
        bus = SignalBus.instance()
        frame = self._worker.latest_frame_bgr
        if frame is None:
            logger.warning("PhotoService: no frame available")
            bus.photo_captured.emit(PhotoResult(
                success=False,
                photo_id="",
                experience_id=experience_id,
                error_message="No webcam frame available",
            ))
            return

        try:
            photo_id = self._capture.make_photo_id(experience_id)
            photo_dir = self._capture.make_photo_dir(photo_id)
            original_path = self._capture.save_original(frame, photo_dir)
            url = self._share.make_share_url(photo_id, filename="original.jpg")
            qr_path = self._share.make_qr(url, photo_dir)
            cleanup_if_over_limit(self._photos_base)

            result = PhotoResult(
                success=True,
                photo_id=photo_id,
                original_path=original_path,
                qr_path=qr_path,
                download_url=url,
                experience_id=experience_id,
            )
            logger.info(f"Photo captured: {photo_id} → {url}")
            bus.photo_captured.emit(result)
        except Exception as e:
            logger.exception(f"PhotoService capture failed: {e}")
            bus.photo_captured.emit(PhotoResult(
                success=False,
                photo_id="",
                experience_id=experience_id,
                error_message=str(e),
            ))
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_photo_service.py -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: 5 tests PASS, lint clean.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_photo_service.py src/neo_makervigate/services/photo_service.py
git commit -m "$(cat <<'EOF'
feat(p5): PhotoService orchestrator — snap + QR + LRU cleanup

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: AppController — photoResult + photoReviewRequested

**Files:**
- Modify: `src/neo_makervigate/services/app_controller.py`
- Modify: `tests/unit/test_app_controller.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/unit/test_app_controller.py`:

```python
def test_app_controller_emits_photo_review_requested_on_capture(qapp) -> None:
    """Khi SignalBus.photo_captured emit success → photoReviewRequested signal."""
    from pathlib import Path
    from neo_makervigate.core.models import PhotoResult
    from neo_makervigate.utils.signal_bus import SignalBus

    ctrl = AppController(experience_manager=None)
    emits: list[bool] = []
    ctrl.photoReviewRequested.connect(lambda: emits.append(True))

    result = PhotoResult(
        success=True,
        photo_id="photo_test",
        original_path=Path("/tmp/x.jpg"),
        qr_path=Path("/tmp/qr.png"),
        download_url="http://test/photo_test/original.jpg",
        experience_id="exp_test",
    )
    SignalBus.instance().photo_captured.emit(result)
    qapp.processEvents()
    assert emits == [True]
    state = ctrl.photoResult
    assert state["photo_id"] == "photo_test"
    assert state["download_url"] == "http://test/photo_test/original.jpg"
    assert state["qr_path"] == "/tmp/qr.png"


def test_app_controller_does_not_emit_review_on_failed_capture(qapp) -> None:
    """Khi photo_captured emit failure → KHÔNG push review."""
    from neo_makervigate.core.models import PhotoResult
    from neo_makervigate.utils.signal_bus import SignalBus

    ctrl = AppController(experience_manager=None)
    emits: list[bool] = []
    ctrl.photoReviewRequested.connect(lambda: emits.append(True))

    result = PhotoResult(
        success=False, photo_id="", experience_id="exp", error_message="oops",
    )
    SignalBus.instance().photo_captured.emit(result)
    qapp.processEvents()
    assert emits == []


def test_photo_result_empty_by_default(qapp) -> None:
    ctrl = AppController(experience_manager=None)
    assert ctrl.photoResult == {}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_app_controller.py -v
```
Expected: 3 new tests FAIL.

- [ ] **Step 3: Modify app_controller.py**

Read `/Users/tuanln/Ai-Code/NeoMakerViGate/src/neo_makervigate/services/app_controller.py` first to see structure.

Add new signal in the signal declarations block (after `experienceStateChanged = pyqtSignal()`):

```python
    photoResultChanged = pyqtSignal()
    photoReviewRequested = pyqtSignal()
```

Add to `__init__` (place after the experience_state initialization):

```python
        self._photo_result: dict[str, object] = {}
        bus.photo_captured.connect(self._on_photo_captured)
```

Add property method (place near other pyqtProperty methods, e.g. after experienceState):

```python
    @pyqtProperty("QVariant", notify=photoResultChanged)
    def photoResult(self) -> Any:
        return self._photo_result
```

Add new slot method (place near other slot methods):

```python
    @pyqtSlot(object)
    def _on_photo_captured(self, result: Any) -> None:
        # PhotoResult import deferred to avoid circular
        if not getattr(result, "success", False):
            logger.warning(
                f"Photo capture failed: {getattr(result, 'error_message', 'unknown')}"
            )
            return
        self._photo_result = {
            "photo_id": result.photo_id,
            "original_path": str(result.original_path) if result.original_path else "",
            "qr_path": str(result.qr_path) if result.qr_path else "",
            "download_url": result.download_url or "",
            "experience_id": result.experience_id,
        }
        self.photoResultChanged.emit()
        self.photoReviewRequested.emit()
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass. New tests included.

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/services/app_controller.py tests/unit/test_app_controller.py
git commit -m "$(cat <<'EOF'
feat(p5): AppController.photoResult + photoReviewRequested signal

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: ExperienceManager — request photo before unload on Phase.DONE

**Files:**
- Modify: `src/neo_makervigate/services/experience_manager.py`
- Modify: `tests/unit/test_experience_manager.py`

- [ ] **Step 1: Append failing test**

Append to `tests/unit/test_experience_manager.py`:

```python
def test_phase_done_emits_photo_capture_requested_before_unload(qapp) -> None:
    """Khi plugin trả phase=done, manager emit photo_capture_requested rồi unload."""
    from datetime import datetime
    from neo_makervigate.core.models import ExperienceMeta, VisionFrame
    from neo_makervigate.experiences.experience_base import BaseExperience

    class _DoneExp(BaseExperience):
        meta = ExperienceMeta(
            id="done_p5",
            title="Done P5",
            subtitle="",
            age_min=4,
            age_max=14,
            vision_modules=("hands",),
        )

        def __init__(self) -> None:
            super().__init__()
            self.frames = 0

        def get_qml_path(self) -> str:
            return ""

        def on_vision_frame(self, frame: VisionFrame) -> None:
            self.frames += 1

        def render_state(self) -> dict[str, object]:
            if self.frames >= 2:
                return {"phase": "done"}
            return {"phase": "playing"}

        def completion_summary(self) -> dict[str, object]:
            return {"completed": True, "score": 100}

    mgr = ExperienceManager(registry={"done_p5": _DoneExp})
    mgr.load("done_p5")
    captured_requests: list[dict] = []
    SignalBus.instance().photo_capture_requested.connect(lambda p: captured_requests.append(p))

    bus = SignalBus.instance()
    bus.vision_frame_ready.emit(VisionFrame(timestamp=datetime.now(), width=640, height=360))
    bus.vision_frame_ready.emit(VisionFrame(timestamp=datetime.now(), width=640, height=360))

    assert len(captured_requests) == 1
    assert captured_requests[0]["experience_id"] == "done_p5"
    assert "summary" in captured_requests[0]
    # Also verify unload happened
    assert mgr.current_id is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_experience_manager.py::test_phase_done_emits_photo_capture_requested_before_unload -v
```
Expected: FAIL — assertion `len(captured_requests) == 1` fails (currently no emit).

- [ ] **Step 3: Modify experience_manager.py**

Read `/Users/tuanln/Ai-Code/NeoMakerViGate/src/neo_makervigate/services/experience_manager.py`. Find this block in `_on_vision_frame`:

```python
        # Auto-end when plugin signals completion via render_state phase==done
        if self._current_instance is not None:
            try:
                state = self._current_instance.render_state()
                if isinstance(state, dict) and state.get("phase") == "done":
                    summary_fn = getattr(self._current_instance, "completion_summary", None)
                    summary = summary_fn() if callable(summary_fn) else {"completed": True}
                    self.unload(summary)
                    return
            except Exception as e:
                logger.warning(f"render_state check failed: {e}")
```

Replace with:

```python
        # Auto-end when plugin signals completion via render_state phase==done
        if self._current_instance is not None:
            try:
                state = self._current_instance.render_state()
                if isinstance(state, dict) and state.get("phase") == "done":
                    summary_fn = getattr(self._current_instance, "completion_summary", None)
                    summary = summary_fn() if callable(summary_fn) else {"completed": True}
                    exp_id = self._current_id or ""
                    # P5: request photo capture BEFORE unload — PhotoService will use
                    # VisionWorker.latest_frame_bgr (still valid at this point).
                    SignalBus.instance().photo_capture_requested.emit({
                        "experience_id": exp_id,
                        "summary": summary,
                    })
                    self.unload(summary)
                    return
            except Exception as e:
                logger.warning(f"render_state check failed: {e}")
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/services/experience_manager.py tests/unit/test_experience_manager.py
git commit -m "$(cat <<'EOF'
feat(p5): ExperienceManager emits photo_capture_requested on phase=done

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: app.py — wire ShareServer + services at boot

**Files:**
- Modify: `src/neo_makervigate/app.py`

- [ ] **Step 1: Read current app.py**

```bash
cat /Users/tuanln/Ai-Code/NeoMakerViGate/src/neo_makervigate/app.py
```

You should see the existing boot sequence: setup_logging → load_settings → SignalBus → QGuiApplication → VisionWorker + GestureDetector + ExperienceManager + AppController → engine.load(MainWindow.qml).

- [ ] **Step 2: Modify app.py**

Add new imports near the existing imports (after `from neo_makervigate.services.experience_manager import ExperienceManager`):

```python
from neo_makervigate.core.photo_capture import DEFAULT_PHOTOS_DIR
from neo_makervigate.core.share_server import ShareServer
from neo_makervigate.services.photo_service import PhotoService
from neo_makervigate.services.share_service import ShareService
```

In `run()`, after `gesture_detector` setup and BEFORE `# Experience plugin registry + manager` block, add:

```python
    # P5: Share/Photo services — ShareServer in background QThread on port 8000
    share_server = ShareServer(photos_root=DEFAULT_PHOTOS_DIR)
    share_server.start()
    share_service = ShareService(share_server=share_server)
    photo_service = PhotoService(
        worker=worker,
        share=share_service,
        photos_base=DEFAULT_PHOTOS_DIR,
    )
    _ = photo_service  # keep ref alive (signal connection only)
```

Then in the shutdown sequence at the end of `run()`, after `worker.stop()`, add:

```python
    logger.info("Shutting down: stopping ShareServer")
    share_server.stop()
```

- [ ] **Step 3: Verify tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add src/neo_makervigate/app.py
git commit -m "$(cat <<'EOF'
feat(p5): wire ShareServer + PhotoService + ShareService at app boot

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: PhotoReviewPage.qml

**Files:**
- Create: `src/neo_makervigate/ui/qml/pages/PhotoReviewPage.qml`

- [ ] **Step 1: Create PhotoReviewPage.qml**

Create `src/neo_makervigate/ui/qml/pages/PhotoReviewPage.qml`:

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../singletons" as Sing

Item {
    id: page

    signal backRequested()

    readonly property var result: app.photoResult
    readonly property string qrPath: result && result.qr_path ? result.qr_path : ""
    readonly property string downloadUrl: result && result.download_url ? result.download_url : ""
    readonly property string originalPath: result && result.original_path ? result.original_path : ""

    Rectangle {
        anchors.fill: parent
        color: Sing.NeoConstants.background
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 32
        spacing: 32

        // Left: original photo
        Item {
            Layout.fillHeight: true
            Layout.preferredWidth: parent.width * 0.55
            Image {
                anchors.fill: parent
                source: page.originalPath ? "file://" + page.originalPath : ""
                fillMode: Image.PreserveAspectFit
                cache: false
            }
        }

        // Right: QR + instructions + back
        ColumnLayout {
            Layout.fillHeight: true
            Layout.fillWidth: true
            spacing: 20

            Text {
                text: "📸 Đã chụp xong!"
                font.pixelSize: 36
                font.bold: true
                color: Sing.NeoConstants.tre
                Layout.alignment: Qt.AlignHCenter
            }

            Text {
                text: "Ba mẹ ơi, quét mã bằng Zalo\nđể tải ảnh về điện thoại!"
                font.pixelSize: 22
                color: Sing.NeoConstants.de
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
            }

            // QR image
            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 360
                Layout.preferredHeight: 360
                color: "white"
                border.color: Sing.NeoConstants.tre
                border.width: 2
                Image {
                    anchors.fill: parent
                    anchors.margins: 8
                    source: page.qrPath ? "file://" + page.qrPath : ""
                    fillMode: Image.PreserveAspectFit
                    cache: false
                }
            }

            Text {
                text: page.downloadUrl
                font.pixelSize: 14
                color: Sing.NeoConstants.textPrimary
                opacity: 0.6
                wrapMode: Text.WrapAnywhere
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
            }

            Item { Layout.fillHeight: true }

            // Back button
            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 240
                Layout.preferredHeight: 64
                radius: 32
                color: Sing.NeoConstants.tre
                Text {
                    anchors.centerIn: parent
                    text: "← Về Hub"
                    color: "white"
                    font.pixelSize: 24
                    font.bold: true
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: page.backRequested()
                }
            }
        }
    }
}
```

- [ ] **Step 2: Verify tests still pass**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
```
Expected: all pass (QML changes don't affect Python tests).

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/ui/qml/pages/PhotoReviewPage.qml
git commit -m "$(cat <<'EOF'
feat(p5): PhotoReviewPage QML — photo + QR + instructions

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: MainWindow.qml — wire PhotoReviewPage navigation

**Files:**
- Modify: `src/neo_makervigate/ui/qml/MainWindow.qml`

- [ ] **Step 1: Read current MainWindow.qml**

```bash
cat /Users/tuanln/Ai-Code/NeoMakerViGate/src/neo_makervigate/ui/qml/MainWindow.qml
```

The file currently has `ApplicationWindow` containing `StackView` with components for Splash, Hub, Container. Need to add PhotoReviewPage component + Connections handler for `app.photoReviewRequested`.

- [ ] **Step 2: Modify MainWindow.qml**

Add a new Component definition (place after `containerComponent` definition):

```qml
    Component {
        id: photoReviewComponent
        PhotoReviewPage {
            onBackRequested: stack.pop()
        }
    }
```

Then add a Connections block (place anywhere inside the ApplicationWindow, near the StackView):

```qml
    Connections {
        target: app
        function onPhotoReviewRequested() {
            stack.push(photoReviewComponent)
        }
    }
```

- [ ] **Step 3: Verify tests still pass**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add src/neo_makervigate/ui/qml/MainWindow.qml
git commit -m "$(cat <<'EOF'
feat(p5): MainWindow wire PhotoReviewPage on photoReviewRequested

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Final verify + smoke test + PHASES.md done

- [ ] **Step 1: Full test + lint sweep**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all green. Total ~100+ tests (79 P4 + ~23 P5 = ~102).

- [ ] **Step 2: Manual smoke test**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m neo_makervigate
```

Verify in logs:
1. "ShareServer listening on http://192.168.x.x:8000/" line appears
2. Open browser http://localhost:8000/ — directory listing works (might be empty)
3. Play exp03 (or skip-through 5 poses to RESULT) → PhotoReviewPage appears with photo + QR
4. iPhone same WiFi: scan QR with Zalo → ảnh tải về
5. Verify `ls ~/makervigate/photos/` shows new folder with original.jpg + qr.png
6. Back → Hub clean, no crash

If webcam denied, smoke test simulator mode:
```bash
NEO_MAKERVIGATE_VISION=simulator .venv/bin/python -m neo_makervigate
```
Simulator's latest_frame_bgr returns blank frame → capture succeeds but photo is blank black/blue. Still validates the pipeline.

- [ ] **Step 3: Update PHASES.md**

In `DOC/PHASES.md`, find the P5 section:

```markdown
## P5 — PhotoCapture + ShareServer + QR (tuần 6)
```

Replace with:

```markdown
## P5 — PhotoCapture + ShareServer + QR (tuần 6) ✅ DONE

**Achievement (2026-05-16):** Core photo+share services — PhotoCapture (cv2.imwrite JPG quality 90), ShareServer QThread (http.server.ThreadingHTTPServer port 8000 + fallback 8001-8010), generate_qr (qrcode + Pillow PNG 360x360 error_correct M), utils/network (get_local_ip qua UDP trick), utils/storage (LRU cleanup 200MB theo folder mtime), PhotoService orchestrator (handle photo_capture_requested → save + URL + QR → emit photo_captured), ShareService facade, AppController.photoResult + photoReviewRequested, ExperienceManager emit photo_capture_requested trên Phase.DONE thay vì auto-unload, PhotoReviewPage QML (photo lớn + QR + URL + Back button). ~23 unit tests, ruff/mypy strict clean. Storage layout ~/makervigate/photos/<photo_id>/{original.jpg, qr.png}.
```

Mark all task checkmarks:

```markdown
### Tasks

- [x] `core/photo_capture.py` — snap raw + composite (P6 sẽ thêm composite)
- [x] `core/share_server.py` — `http.server` trên QThread serve thư mục photos/
- [x] `services/photo_service.py` + `services/share_service.py` — async wrappers
- [x] `utils/network.py` — lấy local IP cho share URL
- [x] `ui/qml/pages/PhotoReviewPage.qml` — ảnh lớn + QR + hướng dẫn
- [~] `ui/qml/components/QRDisplay.qml` — inline trong PhotoReviewPage (extract sau)
- [x] Tích hợp chụp ảnh vào exp03 (lưu RESULT phase)
- [x] Storage layout: `~/makervigate/photos/<photo_id>/`

### Exit criteria

- [x] Auto-cleanup photos cũ khi storage > 200MB — utils/storage + test_storage
- [x] QR quét tải được trong LAN (verify qua manual smoke test)
- [x] Watchdog port 8000 không conflict — test_share_server_falls_back
```

- [ ] **Step 4: Commit**

```bash
git add DOC/PHASES.md
git commit -m "$(cat <<'EOF'
docs(p5): mark Phase 5 done in PHASES.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 5: Update auto-memory project status**

Edit `/Users/tuanln/.claude/projects/-Users-tuanln/memory/project_neomakervigate_status.md`. Find the line:

```markdown
- **P5 PhotoCapture + ShareServer + QR**: chụp ảnh + chia sẻ qua QR — port từ NeoStopMotion
```

Replace with:

```markdown
- **P5 PhotoCapture + ShareServer + QR ✅ DONE** (2026-05-16, head commit `<hash>`): PhotoCapture (cv2.imwrite JPG Q90, photo_id + dir helpers, 6 tests) + ShareServer QThread (http.server.ThreadingHTTPServer port 8000 + fallback 8001-8010 + serve `~/makervigate/photos/`, 6 tests) + generate_qr (qrcode + Pillow PNG error_correct M) + utils/network (get_local_ip UDP trick + loopback fallback, 2 tests) + utils/storage (LRU cleanup 200MB theo mtime, 4 tests) + PhotoService orchestrator (handle photo_capture_requested → save + URL + QR → emit photo_captured, 5 tests) + ShareService facade + AppController.photoResult + photoReviewRequested signal (3 tests) + ExperienceManager Phase.DONE → emit photo_capture_requested rồi unload (1 test) + PhotoReviewPage QML (photo lớn + QR 360px + URL + Back). ~23 P5 tests + 79 P4 = ~102 total. Subagent-driven dev qua 12 task TDD. Out of scope (P6): Selfie Seg composite, caption Qwen, exp06 photo booth game.
- **P6 Qwen + exp06 Photo Booth**: Qwen 3.5 caption + Selfie Seg composite + exp06 game
```

(Memory không track git — không commit.)

---

## Self-Review Summary

**Spec coverage check:**

- §1 Architecture overview → Tasks 9 (app.py wiring), 7-8 (AppController + ExperienceManager). ✓
- §2 PhotoCapture + storage → Tasks 1 (network), 2 (storage), 3 (photo_capture). ✓
- §3 ShareServer + QR → Tasks 4 (ShareServer + generate_qr), 5 (ShareService). ✓
- §4 PhotoService + AppController + QML flow → Tasks 6 (PhotoService), 7 (AppController), 8 (ExperienceManager), 10 (PhotoReviewPage), 11 (MainWindow). ✓
- §5 File layout + testing → All tasks together produce listed files; ~23 tests covered. ✓
- §6 Out of scope respected: no Selfie Seg, no caption, no auth token, no gallery, no QRDisplay extract.

**Placeholders scan:** None.

**Type consistency:**
- `PhotoResult` dataclass used consistently across Tasks 6, 7, 8.
- `photo_capture_requested` signal payload = `dict` consistent (Task 6 reads, Task 8 emits).
- `photoResult` dict keys: `photo_id`, `original_path`, `qr_path`, `download_url`, `experience_id` — same in Task 7 (AppController) and Task 10 (PhotoReviewPage QML).
- `ShareServer.get_download_url(photo_id, filename)` signature consistent in Tasks 4, 5.
- `cleanup_if_over_limit(photos_base, max_mb=200)` signature consistent Tasks 2, 6.

**Plan ends with:** Working P5 — photo capture pipeline functional + tests + commits + docs updated.
