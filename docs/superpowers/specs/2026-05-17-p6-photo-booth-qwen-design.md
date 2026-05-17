# P6 — Qwen + exp06 Photo Booth Design

**Phase:** 6 (NeoMakerViGate — flagship experience MVP)
**Plugin id:** `exp06_photo_booth`
**Created:** 2026-05-17
**Status:** Design approved, ready for implementation plan (after Spike S2)

## Mục tiêu

Trải nghiệm flagship MVP: trẻ chọn nền yêu thích → làm chữ V → countdown → chụp → ghép nền AR (Selfie Seg) → AI viết caption tiếng Việt → QR cho phụ huynh tải về. Kết hợp 3 subsystems mới: Selfie Seg composite, Qwen LLM local (caption), exp06 gameplay.

## Quyết định thiết kế chốt với user (2026-05-17 brainstorm)

| Quyết định | Lựa chọn | Lý do |
|---|---|---|
| Scope | 1 spec duy nhất (~30 tasks) | Match P3/P4/P5 pattern; coupled subsystems |
| Qwen backend | Local only — llama-cpp-python + Qwen 2.5-VL-2B GGUF Q4_K_M | Offline; user chốt local-only |
| Backgrounds | 4 nền: Sân Đình, Lũy Tre, Sân FGC, Sao Hỏa | Theo ARCHITECTURE.md; procedural via Pillow |
| Gameplay flow | Pick → V_SIGN → countdown → capture | Vision-tracking spirit; tinh thần "thân thể là input" |
| Caption style | 1 câu shặt + emoji + fallback per nền | Phù hợp Qwen 2B; fast inference; có safety net |
| Composite quality | Soft mask + Gaussian blur edges | Trung dung scope/đẹp |

## 0. Pre-flight — Spike S2

**MUST run before implementation plan finalized:**

1. `.venv/bin/pip install llama-cpp-python`
2. Download `Qwen2.5-VL-2B-Instruct-Q4_K_M.gguf` + `mmproj-Qwen2.5-VL-2B-Instruct-f16.gguf` (~1.5GB) từ `bartowski/Qwen2.5-VL-2B-Instruct-GGUF` HF repo
3. Test inference Mac M4 với 1 ảnh sample + prompt tiếng Việt
4. **Pass:** caption < 10s, output có ý nghĩa → continue
5. **Fail:** model không inference được hoặc > 30s → escalate to user; fallback options:
   - Switch Qwen 2-VL-2B
   - Bỏ Qwen, all-template captions
   - Switch to API mode (DashScope)

Result của spike sẽ thêm vào spec trước khi finalize plan.

## 1. Architecture overview

```
VisionWorker (P1) — webcam → MediaPipe (hands + selfie cùng lúc)
    → vision_frame_ready (queued main thread)
        ├→ GestureDetector (extended với V_SIGN) — emit gesture_detected
        ├→ ExperienceManager._on_vision_frame → instance.on_vision_frame(frame)
        │     [PhotoBoothExperience: step phase, track V_SIGN hold, countdown]
        └→ PhotoService — handle photo_capture_requested signal

PhotoBoothExperience flow:
  INTRO(2s) → SELECT (POINT cycle, auto-advance) → STAGE (V_SIGN hold 0.5s)
    → COUNTDOWN(3s) → emit photo_capture_requested(experience_id, background_path)
        ↓
    PhotoService._on_capture_request
        ├─ frame = worker.latest_frame_bgr
        ├─ vf = worker.latest_vision_frame  (NEW property)
        ├─ PhotoCapture.save_original
        ├─ if vf.selfie_mask + background_path:
        │     PhotoCapture.save_composite (NEW method — soft mask blur)
        ├─ ShareService.make_share_url + make_qr (composite URL preferred)
        └─ emit photo_captured(PhotoResult with composite_path)
            ↓
    PhotoBoothExperience._on_photo_captured
        ├─ emit qwen_request_started({image_path: composite, prompt, max_tokens: 80})
            ↓
        QwenService (QThread) → QwenLocalBackend.describe_image
            ↓
        emit qwen_response_ready(text)  OR  qwen_failed(error)
            ↓
    PhotoBoothExperience._on_qwen_response or _on_qwen_failed
        ├─ write caption.txt to photo_dir
        ├─ set phase DONE (final_caption populated)
            ↓
    ExperienceManager Phase.DONE detection (P5)
        ├─ CHECK auto_capture_on_done attribute — exp06 = False → skip emit
        ├─ unload(summary)
            ↓
    AppController photoReviewRequested (P5) — already triggered by photo_captured
    PhotoReviewPage shows composite + caption + QR
```

## 2. V_SIGN gesture + Selfie Seg + composite

### V_SIGN extension trong `core/gesture_detector.py`

V_SIGN = index + middle fingers extended, ring + pinky curled. Static pose (no buffer/oscillation like WAVE).

```python
# MediaPipe Hand 21 landmarks:
# Wrist=0, Index tip=8/pip=6/mcp=5, Middle tip=12/pip=10/mcp=9,
# Ring tip=16/pip=14, Pinky tip=20/pip=18

V_SIGN_COOLDOWN_SEC = 0.4
V_SIGN_FINGER_MARGIN = 1.15  # tip must be 15% farther from wrist than pip


def _is_finger_extended(hand, tip_idx, pip_idx) -> bool:
    """Finger extended if tip is farther from wrist than its PIP joint."""
    wrist = hand[0]
    tip = hand[tip_idx]
    pip = hand[pip_idx]
    tip_dist = math.sqrt((tip.x - wrist.x)**2 + (tip.y - wrist.y)**2)
    pip_dist = math.sqrt((pip.x - wrist.x)**2 + (pip.y - wrist.y)**2)
    return tip_dist > pip_dist * V_SIGN_FINGER_MARGIN


def _check_v_sign(hand) -> bool:
    index_ext = _is_finger_extended(hand, 8, 6)
    middle_ext = _is_finger_extended(hand, 12, 10)
    ring_ext = _is_finger_extended(hand, 16, 14)
    pinky_ext = _is_finger_extended(hand, 20, 18)
    return index_ext and middle_ext and not ring_ext and not pinky_ext
```

Extend `GestureDetector.feed(frame)`:
- After WAVE check, also run `_check_v_sign(frame.hands[0])` if hands present.
- Separate cooldown for V_SIGN (independent from WAVE cooldown).
- Return list can contain `["WAVE"]`, `["V_SIGN"]`, both, or empty.
- Emit `SignalBus.gesture_detected.emit("V_SIGN")` for each detection.

### Selfie Seg enable trong `core/vision_engine.py`

Already has `_create_detector("selfie")` từ P1 (returns `ImageSegmenter`). Need to actually run it in `read()` loop:

```python
# In VisionEngine.read() existing for-loop, ADD after pose/face:
elif name == "selfie":
    result = detector.segment_for_video(mp_image, ts_ms)
    if result.confidence_masks:
        mask = result.confidence_masks[0].numpy_view()
        vf.selfie_mask = mask  # shape (H, W) float32
```

### Update `VisionFrame` dataclass

In `core/models.py`:
```python
@dataclass
class VisionFrame:
    ...existing fields...
    selfie_mask: np.ndarray[Any, Any] | None = None
```

### Composite logic in `core/photo_capture.py`

New method `save_composite`:

```python
def save_composite(
    self,
    frame_bgr: np.ndarray[Any, Any],
    mask: np.ndarray[Any, Any],   # float32 [0..1] HxW
    background_path: Path,
    photo_dir: Path,
) -> Path:
    """Composite foreground (trẻ) vào background, lưu composite.jpg.

    Soft mask + Gaussian blur edges để cạnh mượt.
    """
    if not photo_dir.exists():
        raise FileNotFoundError(f"photo_dir does not exist: {photo_dir}")
    h, w = frame_bgr.shape[:2]
    bg = cv2.imread(str(background_path))
    if bg is None:
        raise FileNotFoundError(f"background not found: {background_path}")
    bg = cv2.resize(bg, (w, h))

    # Resize mask to frame dimensions
    if mask.shape != (h, w):
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_LINEAR)
    # Soft edges
    mask_blurred = cv2.GaussianBlur(mask, (15, 15), 0).astype(np.float32)
    mask_3ch = np.stack([mask_blurred] * 3, axis=-1)

    fg = frame_bgr.astype(np.float32)
    bg_f = bg.astype(np.float32)
    composite = (fg * mask_3ch + bg_f * (1 - mask_3ch)).astype(np.uint8)

    path = photo_dir / "composite.jpg"
    ok = cv2.imwrite(str(path), composite, [cv2.IMWRITE_JPEG_QUALITY, JPG_QUALITY])
    if not ok:
        raise RuntimeError(f"cv2.imwrite failed: {path}")
    return path
```

### PhotoService extension

`_on_capture_request(params)` handle `background_path`:

```python
# After saving original.jpg:
composite_path: Path | None = None
if isinstance(params, dict) and params.get("background_path"):
    bg_path = Path(str(params["background_path"]))
    latest_vf = self._worker.latest_vision_frame  # NEW property
    if latest_vf is not None and latest_vf.selfie_mask is not None:
        try:
            composite_path = self._capture.save_composite(
                frame, latest_vf.selfie_mask, bg_path, photo_dir,
            )
        except Exception as e:
            logger.warning(f"Composite failed, using original: {e}")

# URL prefers composite if available
filename = "composite.jpg" if composite_path else "original.jpg"
url = self._share.make_share_url(photo_id, filename=filename)
```

### `VisionWorker.latest_vision_frame` property (NEW)

```python
@property
def latest_vision_frame(self) -> VisionFrame | None:
    with self._lock:
        return self._latest_vision_frame
```

(VisionWorker already stores `_latest_vision_frame` since P1, just exposing now.)

## 3. Qwen client + service

### `core/qwen_client.py` — Protocol + LocalBackend

```python
class QwenClient(Protocol):
    def describe_image(
        self, image_path: Path, prompt: str, max_tokens: int = 80,
    ) -> str: ...
    def is_ready(self) -> bool: ...


MODELS_DIR = Path.home() / "makervigate" / "models" / "qwen"
DEFAULT_MODEL_NAME = "qwen2.5-vl-2b-instruct-q4_k_m.gguf"
DEFAULT_MMPROJ_NAME = "qwen2.5-vl-2b-instruct-mmproj-f16.gguf"
DEFAULT_CONTEXT_SIZE = 2048


class QwenLocalBackend:
    """llama-cpp-python backend chạy Qwen 2.5-VL local trên CPU."""

    def __init__(
        self, model_path: Path | None = None,
        mmproj_path: Path | None = None,
        n_ctx: int = DEFAULT_CONTEXT_SIZE,
    ) -> None:
        self._model_path = model_path or (MODELS_DIR / DEFAULT_MODEL_NAME)
        self._mmproj_path = mmproj_path or (MODELS_DIR / DEFAULT_MMPROJ_NAME)
        self._n_ctx = n_ctx
        self._llm: object | None = None

    def is_ready(self) -> bool:
        return self._model_path.exists() and self._mmproj_path.exists()

    def _ensure_loaded(self) -> None:
        if self._llm is not None: return
        if not self.is_ready():
            raise FileNotFoundError(
                f"Qwen model not found at {self._model_path}. "
                "Run: python -m neo_makervigate.scripts.download_qwen"
            )
        from llama_cpp import Llama
        from llama_cpp.llama_chat_format import Qwen25VLChatHandler
        chat_handler = Qwen25VLChatHandler(clip_model_path=str(self._mmproj_path))
        self._llm = Llama(
            model_path=str(self._model_path),
            chat_handler=chat_handler,
            n_ctx=self._n_ctx, n_gpu_layers=0, verbose=False,
        )

    def describe_image(
        self, image_path: Path, prompt: str, max_tokens: int = 80,
    ) -> str:
        self._ensure_loaded()
        # Encode image as data URI
        img = Image.open(image_path).convert("RGB")
        img.thumbnail((512, 512))
        buf = BytesIO(); img.save(buf, format="JPEG", quality=85)
        data_uri = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
        response = self._llm.create_chat_completion(  # type: ignore[attr-defined]
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": data_uri}},
                {"type": "text", "text": prompt},
            ]}],
            max_tokens=max_tokens, temperature=0.7,
        )
        return response["choices"][0]["message"]["content"].strip()


def download_qwen_models(target_dir: Path = MODELS_DIR) -> None:
    """Helper script (run via scripts/download_qwen.py)."""
    target_dir.mkdir(parents=True, exist_ok=True)
    urls = {
        DEFAULT_MODEL_NAME: "https://huggingface.co/bartowski/Qwen2.5-VL-2B-Instruct-GGUF/resolve/main/Qwen2.5-VL-2B-Instruct-Q4_K_M.gguf",
        DEFAULT_MMPROJ_NAME: "https://huggingface.co/bartowski/Qwen2.5-VL-2B-Instruct-GGUF/resolve/main/mmproj-Qwen2.5-VL-2B-Instruct-f16.gguf",
    }
    import urllib.request
    for name, url in urls.items():
        out = target_dir / name
        if out.exists(): continue
        logger.info(f"Downloading {name} (~700MB)...")
        urllib.request.urlretrieve(url, out)
```

### `services/qwen_service.py` — QThread wrapper

```python
class _QwenWorker(QThread):
    def __init__(self, client: QwenClient) -> None:
        super().__init__()
        self._client = client
        self._queue: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self._running = False

    def enqueue(self, request: dict[str, Any]) -> None:
        self._queue.put(request)

    def stop(self) -> None:
        self._running = False
        self._queue.put(None)
        self.wait(3000)

    def run(self) -> None:
        self._running = True
        bus = SignalBus.instance()
        while self._running:
            item = self._queue.get()
            if item is None: break
            try:
                text = self._client.describe_image(
                    Path(str(item["image_path"])),
                    str(item["prompt"]),
                    int(item.get("max_tokens", 80)),
                )
                bus.qwen_response_ready.emit(text)
            except Exception as e:
                logger.exception(f"Qwen inference failed: {e}")
                bus.qwen_failed.emit(str(e))


class QwenService:
    def __init__(self, client: QwenClient) -> None:
        self._client = client
        self._worker = _QwenWorker(client)
        self._worker.start()
        SignalBus.instance().qwen_request_started.connect(self._on_request)

    def _on_request(self, params: object) -> None:
        if not isinstance(params, dict):
            logger.warning(f"QwenService: invalid params type {type(params)}")
            return
        self._worker.enqueue(dict(params))

    def stop(self) -> None:
        self._worker.stop()
```

### Lazy load + graceful degrade

- Backend constructor không load model. First `describe_image()` triggers load (3-5s cold start).
- If `is_ready() == False` → exp06 reads on `on_enter()` → sets `qwen_unavailable = True` → UI shows "Đang dùng caption mẫu" → all captures use template fallback.
- If inference raises (model corrupt, OOM, etc) → `qwen_failed` → plugin uses fallback.

## 4. exp06 PhotoBoothExperience + UI

### State machine

```
INTRO (2s)
SELECT (POINT cycle, auto-advance 3s of stable index)
STAGE (V_SIGN hold ≥0.5s)
COUNTDOWN (3s) → emit photo_capture_requested at end
PROCESSING (max 12s) — wait photo + caption
DONE — set phase, ExperienceManager unload + auto PhotoReviewPage
```

### Constants

```python
INTRO_DURATION = 2.0
SELECT_AUTO_ADVANCE_SEC = 3.0   # stable selection for 3s → auto STAGE
COUNTDOWN_DURATION = 3.0
PROCESSING_TIMEOUT = 12.0
V_SIGN_TRIGGER_HOLD = 0.5
```

### Phase enum

```python
class Phase(StrEnum):
    INTRO = "intro"
    SELECT = "select"
    STAGE = "stage"
    COUNTDOWN = "countdown"
    PROCESSING = "processing"
    DONE = "done"
```

### Dataclass

```python
@dataclass
class BackgroundOption:
    id: str
    title: str
    emoji: str
    path: Path
    fallback_caption: str
```

### Plugin contract — `auto_capture_on_done = False`

`BaseExperience` defaults `auto_capture_on_done: ClassVar[bool] = True`. PhotoBoothExperience overrides to `False` so ExperienceManager skips emitting `photo_capture_requested` at Phase.DONE — plugin self-orchestrated capture.

### ExperienceManager change

```python
# In _on_vision_frame, modify phase==done block:
if isinstance(state, dict) and state.get("phase") == "done":
    summary_fn = ...
    summary = ...
    auto_capture = getattr(self._current_instance, "auto_capture_on_done", True)
    if auto_capture:
        SignalBus.instance().photo_capture_requested.emit({
            "experience_id": self._current_id or "",
            "summary": summary,
        })
    self.unload(summary)
    return
```

### `render_state()` schema

```python
{
    "phase": "intro" | "select" | "stage" | "countdown" | "processing" | "done",
    "elapsed_in_phase": float,
    "backgrounds": [
        {"id": str, "title": str, "emoji": str, "path": str},
        ...4 total
    ],
    "selected_bg_index": int,
    "v_sign_progress": float,        # 0.0-1.0 holding ratio
    "countdown_remaining": float,    # 3.0 → 0.0 in COUNTDOWN
    "processing_status": str,        # "waiting_photo" | "waiting_qwen" | "done"
    "caption": str,                  # populated after caption arrives
    "qwen_unavailable": bool,
}
```

### `completion_summary`

```python
def completion_summary(self) -> dict[str, Any]:
    return {
        "completed": True,
        "background_id": self._backgrounds[self._selected_bg_index].id,
        "caption": self._caption,
        "qwen_used": not self._qwen_unavailable and self._caption_from_qwen,
    }
```

### UI per phase

- **INTRO** — full overlay "🤖 Chào mừng đến Photo Booth!" + subtitle, "Chọn cảnh em thích, làm chữ V để chụp."
- **SELECT** — camera mirror full + bottom row 4 thumbnails với highlight, instructions "Chỉ tay để đổi cảnh"
- **STAGE** — camera mirror + bg ghost overlay (alpha 0.3) + center text "✌️ Làm chữ V để chụp!" + V_SIGN hold progress bar bottom
- **COUNTDOWN** — giant number animated 3 → 2 → 1 → 📸
- **PROCESSING** — spinner + "Đang chụp + viết caption..." + status text từ processing_status
- **DONE** — brief flash (just before manager unload pops to PhotoReviewPage)

PhotoReviewPage (P5) already displays composite + QR. Need extend to show caption text — read from `photoResult.caption_path` or directly `photoResult.caption` if AppController populates from caption.txt file.

**AppController extension:** when `photo_captured` arrives, also read `caption.txt` from photo_dir if exists, include in `photoResult` dict:

```python
caption_text = ""
photo_dir = original_path.parent if original_path else None
if photo_dir:
    caption_file = photo_dir / "caption.txt"
    if caption_file.exists():
        caption_text = caption_file.read_text(encoding="utf-8").strip()
self._photo_result = {..., "caption": caption_text}
```

But: caption.txt is written AFTER photo_captured (by plugin in `_on_qwen_response`). So initial photoResult won't have caption. Two solutions:

**A.** Plugin extends `photo_captured` signal payload — but PhotoResult dataclass doesn't have caption field by default. Don't bloat for 1 experience.

**B.** Plugin emits its own `photo_caption_ready(photo_id, caption)` signal. AppController listens + re-populates photoResult + emits photoResultChanged. PhotoReviewPage automatically re-renders.

**Choose B.** Add to SignalBus: `photo_caption_ready = pyqtSignal(str, str)`  # photo_id, caption.

### PhotoReviewPage QML extension

Add caption display:

```qml
Text {
    text: page.caption || "..."
    font.pixelSize: 22
    color: Sing.NeoConstants.de
    font.italic: true
    wrapMode: Text.WordWrap
    horizontalAlignment: Text.AlignHCenter
    Layout.fillWidth: true
}
```

Property:
```qml
readonly property string caption: result && result.caption ? result.caption : ""
```

## 5. File layout + Testing + Risks

### Files

```
src/neo_makervigate/
├── core/
│   ├── gesture_detector.py          # SỬA: V_SIGN
│   ├── photo_capture.py             # SỬA: save_composite
│   ├── qwen_client.py               # MỚI
│   ├── vision_engine.py             # SỬA: selfie in read()
│   ├── vision_worker.py             # SỬA: latest_vision_frame property
│   └── models.py                    # SỬA: VisionFrame.selfie_mask
├── services/
│   ├── app_controller.py            # SỬA: photo_caption_ready slot + caption in photoResult
│   ├── experience_manager.py        # SỬA: auto_capture_on_done check
│   ├── photo_service.py             # SỬA: background_path → composite
│   └── qwen_service.py              # MỚI
├── experiences/
│   ├── experience_base.py           # SỬA: auto_capture_on_done = True default
│   └── exp06_photo_booth/
│       ├── logic.py                 # REWRITE
│       ├── ui.qml                   # REWRITE
│       ├── prompts.toml             # MỚI
│       ├── _gen_assets.py           # MỚI
│       ├── test_logic.py            # MỚI
│       └── backgrounds/{san_dinh,luy_tre,san_fgc,sao_hoa}.png
├── ui/qml/pages/PhotoReviewPage.qml # SỬA: caption display
├── utils/signal_bus.py              # SỬA: photo_caption_ready signal
├── scripts/
│   └── download_qwen.py             # MỚI
└── app.py                           # SỬA: QwenLocalBackend + QwenService

tests/unit/
├── test_gesture_detector.py         # SỬA: + 3 V_SIGN tests
├── test_photo_capture.py            # SỬA: + 3 composite tests
├── test_qwen_client.py              # MỚI
├── test_qwen_service.py             # MỚI

pyproject.toml                       # SỬA: ensure llama-cpp-python in qwen-local optional
DOC/PHASES.md                        # mark P6 done
DOC/QWEN_SETUP.md                    # MỚI
```

### Testing (~30 tests)

**`test_gesture_detector.py` extend (3 tests):**
- `test_v_sign_index_middle_extended_returns_v_sign`
- `test_v_sign_all_fingers_extended_no_trigger`
- `test_v_sign_only_index_no_trigger`

**`test_photo_capture.py` extend (3 tests):**
- `test_save_composite_blends_foreground_with_background` (synthetic mask)
- `test_save_composite_with_zero_mask_returns_background_only`
- `test_save_composite_with_full_mask_returns_foreground`

**`test_qwen_client.py` (5 tests):**
- `test_local_backend_is_ready_false_when_model_missing`
- `test_local_backend_is_ready_true_when_files_exist`
- `test_describe_image_raises_when_model_missing`
- `test_describe_image_calls_llama_with_image_and_prompt` (monkeypatch `Llama` class)
- `test_qwen_protocol_runtime_checkable_with_fake_backend`

**`test_qwen_service.py` (4 tests):**
- `test_qwen_service_calls_backend_via_signal` (fake backend)
- `test_qwen_service_emits_response_on_success`
- `test_qwen_service_emits_failed_on_exception`
- `test_qwen_service_stop_terminates_thread_cleanly`

**`exp06_photo_booth/test_logic.py` (~14 tests):**
- `test_meta_correct`
- `test_initial_phase_is_intro`
- `test_prompts_toml_loaded`
- `test_backgrounds_loaded_4_options`
- `test_auto_capture_on_done_is_false`
- `test_intro_transitions_to_select_after_2s`
- `test_point_gesture_cycles_selection`
- `test_select_auto_advances_to_stage_after_stable`
- `test_v_sign_in_stage_triggers_countdown_after_hold`
- `test_countdown_advances_3_to_0_then_emits_capture`
- `test_photo_captured_triggers_qwen_request`
- `test_qwen_response_sets_caption_and_advances_to_done`
- `test_qwen_failure_uses_fallback_caption`
- `test_processing_timeout_uses_fallback`
- `test_completion_summary_includes_caption`

### Smoke test (manual, requires Qwen model)

1. `python -m neo_makervigate.scripts.download_qwen` (1.5GB, ~10 min)
2. Launch app → vào Photo Booth
3. INTRO 2s → SELECT (point hand → cycle, auto-advance ~3s sau khi đứng yên)
4. STAGE: thấy bg ghost overlay; làm V_SIGN → COUNTDOWN 3-2-1
5. CAPTURE: ảnh chụp + composite ghép nền
6. PROCESSING: spinner ~6s (Qwen)
7. PhotoReviewPage: composite + caption tiếng Việt + QR
8. iPhone Zalo scan QR → tải về

### Exit criteria

| PHASES.md §P6 criteria | Verify |
|---|---|
| API mode caption < 4s | N/A (local only) |
| Local mode caption < 8s | Smoke test timing log |
| Composite không vỡ | Visual inspect smoke test |

### Risk register

| Risk | Mitigation |
|---|---|
| Qwen 2.5-VL-2B GGUF inference fail/quá chậm | Spike S2 verify trước. Fallback options ghi rõ. |
| llama-cpp-python build fail trên ARM64 | Pin trong `arm64` extras. P7 verify. Mac dev OK |
| Inference > 8s | `PROCESSING_TIMEOUT=12s` → fallback template |
| Model file missing | `qwen_unavailable` mode — app vẫn chạy, all-template captions |
| Selfie mask jagged | Soft mask Gaussian blur. Fallback dùng original |
| photo_captured signal connect leak giữa sessions | `on_exit` MUST disconnect; included |
| Qwen output có markdown/special chars | Strip + truncate trong `_on_qwen_response` |
| 4 background procedural xấu | Acceptable MVP; user thay PNG sau pilot |
| Hands + Selfie cùng lúc NEO One 2GB | P1 set_active_modules support; cost = nhẹ + nhẹ |
| POINT cycle UX gây nhầm (trẻ vô tình point) | Auto-advance 3s stable; tap thumbnail cũng works |
| Caption.txt I/O fail | Catch + ignore; caption sẽ rỗng nhưng app vẫn chạy |

### Out of scope (post-P6)

- Qwen API backend (DashScope) — local-only decision
- Streaming caption display — wait-and-show OK MVP
- Multiple captures per session
- Caption editing by user
- Background animation
- Custom upload background
- Photo gallery

---

Liên quan: [[2026-05-16-p5-photo-share-design]] — base infrastructure cho photo+share. P6 extend PhotoCapture với composite, AppController với caption support.
