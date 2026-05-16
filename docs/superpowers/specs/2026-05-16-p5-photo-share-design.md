# P5 — PhotoCapture + ShareServer + QR Design

**Phase:** 5 (NeoMakerViGate — cross-experience capture + share)
**Created:** 2026-05-16
**Status:** Design approved, ready for implementation plan

## Mục tiêu

Thêm cơ chế "chụp ảnh + chia sẻ qua QR" như sợi chỉ chung xuyên mọi trải nghiệm. P5 implement core services (PhotoCapture, ShareServer, QR generator) + integrate với exp03 (auto-capture vào RESULT phase). exp01 và game khác có thể opt-in sau bằng cách emit `photo_capture_requested`.

## Quyết định thiết kế chốt với user (2026-05-16 brainstorm)

| Quyết định | Lựa chọn | Lý do |
|---|---|---|
| P5 scope | Raw photo only (no Selfie Seg composite) | Composite + caption Qwen để P6 cùng exp06 Photo Booth — keep P5 scope nhỏ |
| Capture trigger trong exp03 | Auto khi vào RESULT phase | Trẻ thấy ảnh + QR ngay khi xong game, không cần thao tác |
| ShareServer lifetime | Start at app boot, port 8000 fixed + fallback 8001-8010 | URL ổn định cho phụ huynh; fallback nếu conflict |
| PhotoReviewPage UX | Không auto-timeout, chỉ Back manual | Cho phụ huynh thoải mái scan + tải; FPT Shop đông trẻ có thể bypass bằng Back |
| Storage | `~/makervigate/photos/` + LRU cleanup 200MB | Cross-platform Mac+Linux; match PHASES.md exit criteria |

## 1. Architecture overview

```
App boot:
  ShareServer(QThread) starts on :8000 (fallback :8001-:8010 if taken)
       └─ serves ~/makervigate/photos/ via http.server.ThreadingHTTPServer

Per-experience flow:
  ExperienceManager._on_vision_frame detects render_state.phase == "done"
       │
       ├─ emit photo_capture_requested({"experience_id": exp_id, "summary": ...})
       └─ unload(summary)
                │
                ▼
  PhotoService._on_capture_request(params)  [signal handler, main thread]
       ├─ frame = VisionWorker.latest_frame_bgr  (P1 API)
       ├─ photo_id = "photo_<timestamp>_<exp_id>"
       ├─ photo_dir = ~/makervigate/photos/<photo_id>/
       ├─ PhotoCapture.save_original(frame, photo_dir) → original.jpg
       ├─ url = ShareService.make_share_url(photo_id)
       ├─ qr_path = ShareService.make_qr(url, photo_dir) → qr.png
       ├─ cleanup_if_over_limit(photos_base, 200MB)
       └─ emit photo_captured(PhotoResult(...))
                │
                ▼
  AppController._on_photo_captured(result)
       ├─ set photoResult property (dict)
       └─ emit photoReviewRequested
                │
                ▼
  MainWindow.qml Connections.onPhotoReviewRequested
       └─ stack.push(PhotoReviewPage)
                │
                ▼
  PhotoReviewPage shows: original.jpg + qr.png + URL + Back button
       └─ Back → stack.pop() → Hub
```

**Modules mới:**
- `core/photo_capture.py` (~60 LOC) — PhotoCapture class
- `core/share_server.py` (~150 LOC) — ShareServer QThread + generate_qr function
- `services/photo_service.py` (~80 LOC) — orchestrator
- `services/share_service.py` (~30 LOC) — ShareServer facade
- `utils/network.py` (~30 LOC) — get_local_ip
- `utils/storage.py` (~50 LOC) — LRU cleanup
- `ui/qml/pages/PhotoReviewPage.qml` (~120 LOC)

**Modules sửa:**
- `app.py` — instantiate ShareServer + services + connect SignalBus
- `services/app_controller.py` — add `photoResult` property + slot + `photoReviewRequested` signal
- `services/experience_manager.py` — replace auto-unload-on-done with `emit photo_capture_requested → unload`
- `ui/qml/MainWindow.qml` — add PhotoReviewPage component + onPhotoReviewRequested handler

## 2. PhotoCapture + storage

**`core/photo_capture.py`:**

```python
DEFAULT_PHOTOS_DIR = Path.home() / "makervigate" / "photos"
JPG_QUALITY = 90

class PhotoCapture:
    def __init__(self, base_dir: Path = DEFAULT_PHOTOS_DIR) -> None:
        self._base = base_dir
        self._base.mkdir(parents=True, exist_ok=True)

    def make_photo_id(self, experience_id: str = "") -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{experience_id}" if experience_id else ""
        return f"photo_{ts}{suffix}"

    def make_photo_dir(self, photo_id: str) -> Path:
        d = self._base / photo_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_original(self, frame_bgr: np.ndarray, photo_dir: Path) -> Path:
        path = photo_dir / "original.jpg"
        ok = cv2.imwrite(str(path), frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, JPG_QUALITY])
        if not ok:
            raise RuntimeError(f"cv2.imwrite failed: {path}")
        return path
```

**`utils/storage.py`:**

```python
MAX_PHOTOS_STORAGE_MB = 200

def _dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())

def cleanup_if_over_limit(photos_base: Path, max_mb: int = MAX_PHOTOS_STORAGE_MB) -> int:
    """LRU: xóa folder cũ nhất (theo mtime) cho tới khi total < limit. Trả số folder xóa."""
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
    return deleted
```

**`utils/network.py`:**

```python
def get_local_ip() -> str:
    """Trả LAN IP. Fallback 127.0.0.1 nếu offline."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # không thực sự gửi, chỉ bind outbound IP
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()
```

**Storage layout:**
```
~/makervigate/photos/
├── photo_20260516_143025_exp03_yoga_robot/
│   ├── original.jpg     (1280x720 JPG ~150KB)
│   └── qr.png           (300x300 PNG ~3KB)
└── photo_20260516_143812_exp01_wave_cricket/
    ├── original.jpg
    └── qr.png
```

## 3. ShareServer + QR

**`core/share_server.py`:**

```python
DEFAULT_PORT = 8000
FALLBACK_PORTS = range(8001, 8011)
QR_BOX_SIZE = 10
QR_BORDER = 2


class _PhotosHandler(http.server.SimpleHTTPRequestHandler):
    photos_root: Path  # set by factory

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(self.__class__.photos_root), **kwargs)

    def log_message(self, format: str, *args) -> None:
        logger.debug(f"share-http: {format % args}")


def _make_handler_class(photos_root: Path) -> type[_PhotosHandler]:
    return type("_BoundPhotosHandler", (_PhotosHandler,), {"photos_root": photos_root})


class ShareServer(QThread):
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
        port = self.port or DEFAULT_PORT
        return f"http://{self._ip}:{port}/{photo_id}/{filename}"

    def _try_bind(self, port: int) -> socketserver.ThreadingTCPServer | None:
        handler_cls = _make_handler_class(self._photos_root)
        try:
            return http.server.ThreadingHTTPServer(("0.0.0.0", port), handler_cls)
        except OSError:
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
        try:
            self._server.serve_forever(poll_interval=0.5)
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

**`services/share_service.py`:**

```python
class ShareService:
    def __init__(self, share_server: ShareServer) -> None:
        self._server = share_server

    def make_share_url(self, photo_id: str, filename: str = "original.jpg") -> str:
        return self._server.get_download_url(photo_id, filename)

    def make_qr(self, url: str, photo_dir: Path) -> Path:
        return generate_qr(url, photo_dir / "qr.png")
```

**Security notes (acceptable cho MVP pilot):**
- `0.0.0.0:8000` → mọi máy LAN truy cập được. Tại FPT Shop WiFi public, list `/` thấy được index. OK vì:
  - Ảnh không nhạy cảm (sản phẩm chơi của trẻ)
  - 200MB LRU cleanup nên không tích lũy
  - Sau pilot có thể nâng cấp: token URL hoặc auth header
- Path traversal: `SimpleHTTPRequestHandler` đã sanitize built-in
- Symlinks không follow

## 4. PhotoService + AppController + QML flow

**`services/photo_service.py`:**

```python
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

    def _on_capture_request(self, params: dict) -> None:
        experience_id = params.get("experience_id", "") if isinstance(params, dict) else ""
        bus = SignalBus.instance()
        frame = self._worker.latest_frame_bgr
        if frame is None:
            logger.warning("PhotoService: no frame available")
            bus.photo_captured.emit(PhotoResult(
                success=False, photo_id="", experience_id=experience_id,
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
            bus.photo_captured.emit(result)
        except Exception as e:
            logger.exception(f"PhotoService capture failed: {e}")
            bus.photo_captured.emit(PhotoResult(
                success=False, photo_id="", experience_id=experience_id,
                error_message=str(e),
            ))
```

**AppController changes:**

```python
photoResultChanged = pyqtSignal()
photoReviewRequested = pyqtSignal()

# in __init__:
self._photo_result: dict[str, object] = {}
bus.photo_captured.connect(self._on_photo_captured)

@pyqtProperty("QVariant", notify=photoResultChanged)
def photoResult(self) -> Any:
    return self._photo_result

@pyqtSlot(object)
def _on_photo_captured(self, result: PhotoResult) -> None:
    if not result.success:
        logger.warning(f"Photo capture failed: {result.error_message}")
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

**ExperienceManager change** (replace existing phase==done block in `_on_vision_frame`):

```python
if isinstance(state, dict) and state.get("phase") == "done":
    summary_fn = getattr(self._current_instance, "completion_summary", None)
    summary = summary_fn() if callable(summary_fn) else {"completed": True}
    exp_id = self._current_id or ""
    SignalBus.instance().photo_capture_requested.emit({
        "experience_id": exp_id,
        "summary": summary,
    })
    self.unload(summary)
    return
```

**Order trade-off:**
1. `photo_capture_requested` emit (synchronous, signal queued)
2. `unload(summary)` → `experience_ended` emit → AppController pops Container → Hub visible
3. PhotoService processes signal #1 → captures frame (cached `latest_frame_bgr` từ trước unload) → emit `photo_captured`
4. AppController `photoReviewRequested` → MainWindow push PhotoReviewPage on top of Hub

Flow đúng: trẻ thấy Hub thoáng qua → PhotoReviewPage push lên top. Back → pop về Hub clean.

**`PhotoReviewPage.qml`** (key elements):

- Left half: `Image { source: "file://" + originalPath }` photo lớn
- Right half: `Column` với:
  - Hướng dẫn "Ba mẹ ơi, quét mã bằng Zalo để tải ảnh!"
  - QR `Image { source: "file://" + qrPath }` 360x360
  - WiFi SSID + URL text (debug + redundancy)
  - "← Hub" button → emit backRequested

**`MainWindow.qml` changes:**

```qml
Component {
    id: photoReviewComponent
    PhotoReviewPage {
        onBackRequested: stack.pop()
    }
}

Connections {
    target: app
    function onPhotoReviewRequested() {
        stack.push(photoReviewComponent)
    }
}
```

## 5. File layout + Testing strategy

**Files:**

```
src/neo_makervigate/
├── core/
│   ├── photo_capture.py             # MỚI
│   └── share_server.py              # MỚI
├── services/
│   ├── photo_service.py             # MỚI
│   ├── share_service.py             # MỚI
│   ├── app_controller.py            # SỬA
│   └── experience_manager.py        # SỬA
├── utils/
│   ├── network.py                   # MỚI
│   └── storage.py                   # MỚI
├── app.py                           # SỬA
└── ui/qml/
    ├── MainWindow.qml               # SỬA
    └── pages/PhotoReviewPage.qml    # MỚI

tests/unit/
├── test_photo_capture.py            # MỚI
├── test_share_server.py             # MỚI
├── test_storage.py                  # MỚI
├── test_network.py                  # MỚI
└── test_photo_service.py            # MỚI
```

### Testing (TDD, ~23 tests)

**1. `test_photo_capture.py`** (6 tests)
- `test_make_photo_id_format` — "photo_YYYYMMDD_HHMMSS"
- `test_make_photo_id_with_experience` — includes exp suffix
- `test_make_photo_dir_creates_folder` (tmp_path)
- `test_save_original_writes_jpg` (tmp_path)
- `test_save_original_with_corrupt_frame_raises` (tmp_path) — zero-size frame
- `test_save_original_quality_param_respected` (tmp_path) — JPG size sanity

**2. `test_share_server.py`** (6 tests, requires qapp)
- `test_share_server_starts_on_default_port` (tmp_path, qapp)
- `test_share_server_falls_back_when_port_taken` (tmp_path, qapp) — bind dummy socket to 8000 first
- `test_get_download_url_format` (tmp_path, qapp)
- `test_serves_photo_file_via_http` (tmp_path, qapp) — urllib GET, assert 200 + content
- `test_generate_qr_creates_png` (tmp_path) — standalone, no qapp
- `test_stop_closes_socket_cleanly` (tmp_path, qapp)

**3. `test_storage.py`** (4 tests)
- `test_dir_size_zero_when_empty` (tmp_path)
- `test_cleanup_does_nothing_under_limit` (tmp_path)
- `test_cleanup_removes_oldest_folder_first` (tmp_path) — use os.utime for mtime control
- `test_cleanup_stops_when_under_limit` (tmp_path) — preserves newer folders

**4. `test_network.py`** (2 tests)
- `test_get_local_ip_returns_ipv4_string`
- `test_get_local_ip_fallback_to_loopback_on_error` (monkeypatch socket.connect to raise OSError)

**5. `test_photo_service.py`** (5 tests, requires qapp + tmp_path)
- `test_capture_request_with_no_frame_emits_failure`
- `test_capture_request_emits_photo_captured_on_success`
- `test_photo_result_has_url_and_qr_path`
- `test_capture_with_experience_id_includes_in_path`
- `test_capture_failure_emits_with_error_message` — monkeypatch cv2.imwrite to fail

Use fake `VisionWorker` with controllable `latest_frame_bgr` (synthetic np.zeros frame).

### Smoke test thủ công

1. Launch app → log "ShareServer listening on http://192.168.x.x:8000/"
2. `curl http://localhost:8000/` → directory listing
3. Play exp03 (or skip-through 5 poses) → RESULT → PhotoReviewPage push
4. iPhone same WiFi: scan QR with Zalo → ảnh tải về
5. `ls ~/makervigate/photos/` → folder mới
6. Back → Hub clean

### Exit criteria mapping

| PHASES.md §P5 criteria | Cách verify |
|---|---|
| Auto-cleanup khi storage > 200MB | `test_cleanup_*` + manual fill + capture |
| QR quét tải được trong LAN | Manual iPhone scan |
| Watchdog port 8000 không conflict | `test_share_server_falls_back_when_port_taken` |

### Risk + mitigation

| Risk | Mitigation |
|---|---|
| http.server không stop cleanly | `shutdown()` từ thread khác + `server_close()` + `wait(2000)` |
| `latest_frame_bgr` None at capture | PhotoService emit failure; AppController logs nhưng không crash |
| macOS Firewall block port 8000 | Smoke test phát hiện; user prompt allow connection |
| Path traversal | `SimpleHTTPRequestHandler` đã sanitize; symlinks không follow |
| Multiple rapid captures cùng giây | photo_id timestamp seconds → có thể clash. Trẻ không capture < 1s/lần thật sự — accept overwrite cho MVP |
| pytest-qt waiting cho HTTP server thread | `qtbot.wait(100)` sau start, hoặc urllib timeout |

## 6. Out of scope (P6 và sau)

- **Selfie segmentation + composite background** — P6
- **Caption Qwen** — P6
- **Auth token trong URL** — post-pilot
- **mDNS/Bonjour cho friendlier URL** — overkill cho 1 station
- **Auto-share to cloud** — privacy + complexity
- **Photo gallery (list photos cũ)** — chỉ current capture
- **Capture trigger trong exp01** — chỉ exp03 trong P5
- **`QRDisplay.qml` reusable component** — inline trong PhotoReviewPage (extract khi P6 cần reuse)

---

Liên quan: [[2026-05-15-p3-wave-cricket-design]], [[2026-05-16-p4-yoga-robot-design]] — reuse Python-driven + AppController pattern. PhotoCapture phục vụ mọi experience qua signal — exp01 và exp03 đều có thể trigger.
