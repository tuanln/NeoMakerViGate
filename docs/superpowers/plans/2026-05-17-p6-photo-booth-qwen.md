# P6 — exp06 Photo Booth + Qwen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build flagship MVP experience exp06 Photo Booth — trẻ chọn nền (4 backgrounds) → V_SIGN → countdown → chụp → Selfie Seg composite → Qwen 2.5-VL local caption tiếng Việt → QR cho phụ huynh tải.

**Architecture:** 3 subsystems coupled: V_SIGN gesture (GestureDetector extension), Selfie Seg composite (VisionEngine + PhotoCapture extension), Qwen LLM (core/qwen_client.py + services/qwen_service.py QThread). PhotoBoothExperience plugin self-orchestrates capture+caption via `auto_capture_on_done=False`.

**Tech Stack:** Python 3.12, PyQt6, MediaPipe Selfie Seg, llama-cpp-python (Qwen 2.5-VL-2B-Instruct-Q4_K_M GGUF), Pillow (background generation), OpenCV (composite alpha blend), pytest.

**Reference spec:** `docs/superpowers/specs/2026-05-17-p6-photo-booth-qwen-design.md`

**Pre-flight (USER MANUAL — Spike S2):** Verify `llama-cpp-python` + Qwen 2.5-VL-2B GGUF inference works on Mac M4. If fails, escalate before T11 (Qwen-touching tasks). All non-Qwen tasks (T1-T9, T14-T16) work without Spike.

---

## File Structure

**New files:**
- `src/neo_makervigate/core/qwen_client.py` — QwenClient Protocol + QwenLocalBackend
- `src/neo_makervigate/services/qwen_service.py` — QThread wrapper
- `src/neo_makervigate/scripts/download_qwen.py` — model downloader
- `src/neo_makervigate/scripts/__init__.py`
- `src/neo_makervigate/experiences/exp06_photo_booth/logic.py` — rewrite stub
- `src/neo_makervigate/experiences/exp06_photo_booth/ui.qml` — rewrite stub
- `src/neo_makervigate/experiences/exp06_photo_booth/prompts.toml`
- `src/neo_makervigate/experiences/exp06_photo_booth/_gen_assets.py`
- `src/neo_makervigate/experiences/exp06_photo_booth/test_logic.py`
- `src/neo_makervigate/experiences/exp06_photo_booth/backgrounds/*.png` (4 generated)
- `tests/unit/test_qwen_client.py`
- `tests/unit/test_qwen_service.py`
- `DOC/QWEN_SETUP.md`

**Modified files:**
- `src/neo_makervigate/core/gesture_detector.py` — V_SIGN detection
- `src/neo_makervigate/core/photo_capture.py` — save_composite
- `src/neo_makervigate/core/vision_engine.py` — selfie branch in read()
- `src/neo_makervigate/core/vision_worker.py` — latest_vision_frame property
- `src/neo_makervigate/core/models.py` — VisionFrame.selfie_mask
- `src/neo_makervigate/experiences/experience_base.py` — auto_capture_on_done class attr
- `src/neo_makervigate/services/experience_manager.py` — auto_capture_on_done check
- `src/neo_makervigate/services/app_controller.py` — photo_caption_ready slot
- `src/neo_makervigate/services/photo_service.py` — background_path → composite
- `src/neo_makervigate/utils/signal_bus.py` — photo_caption_ready signal
- `src/neo_makervigate/ui/qml/pages/PhotoReviewPage.qml` — caption display
- `src/neo_makervigate/app.py` — QwenLocalBackend + QwenService
- `tests/unit/test_gesture_detector.py` — V_SIGN tests
- `tests/unit/test_photo_capture.py` — composite tests
- `DOC/PHASES.md` — mark P6 done

---

## Task 1: GestureDetector — V_SIGN detection

**Files:**
- Modify: `src/neo_makervigate/core/gesture_detector.py`
- Modify: `tests/unit/test_gesture_detector.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/unit/test_gesture_detector.py`:

```python
import math as _math
from neo_makervigate.core.models import Landmark


def _make_hand_v_sign(wrist_x: float = 0.5, wrist_y: float = 0.5) -> list[Landmark]:
    """Synthesize 21-landmark hand in V-sign pose.

    Index + middle extended upward (tip far from wrist), ring + pinky curled (tip close).
    """
    L = [Landmark(x=wrist_x, y=wrist_y) for _ in range(21)]
    # Wrist at index 0
    L[0] = Landmark(x=wrist_x, y=wrist_y)
    # Index finger extended up: tip at y - 0.20, pip at y - 0.10
    L[5] = Landmark(x=wrist_x - 0.03, y=wrist_y - 0.05)  # mcp
    L[6] = Landmark(x=wrist_x - 0.03, y=wrist_y - 0.10)  # pip
    L[7] = Landmark(x=wrist_x - 0.03, y=wrist_y - 0.15)
    L[8] = Landmark(x=wrist_x - 0.03, y=wrist_y - 0.20)  # tip
    # Middle finger extended up: tip at y - 0.22
    L[9] = Landmark(x=wrist_x + 0.01, y=wrist_y - 0.05)
    L[10] = Landmark(x=wrist_x + 0.01, y=wrist_y - 0.11)
    L[11] = Landmark(x=wrist_x + 0.01, y=wrist_y - 0.16)
    L[12] = Landmark(x=wrist_x + 0.01, y=wrist_y - 0.22)
    # Ring curled: tip close to wrist (near mcp y-level)
    L[13] = Landmark(x=wrist_x + 0.04, y=wrist_y - 0.05)
    L[14] = Landmark(x=wrist_x + 0.04, y=wrist_y - 0.07)
    L[15] = Landmark(x=wrist_x + 0.04, y=wrist_y - 0.06)
    L[16] = Landmark(x=wrist_x + 0.04, y=wrist_y - 0.04)  # tip BELOW pip (closer to wrist than pip)
    # Pinky curled similarly
    L[17] = Landmark(x=wrist_x + 0.07, y=wrist_y - 0.04)
    L[18] = Landmark(x=wrist_x + 0.07, y=wrist_y - 0.06)
    L[19] = Landmark(x=wrist_x + 0.07, y=wrist_y - 0.05)
    L[20] = Landmark(x=wrist_x + 0.07, y=wrist_y - 0.03)  # tip closer to wrist than pip
    return L


def _make_hand_open_palm(wrist_x: float = 0.5, wrist_y: float = 0.5) -> list[Landmark]:
    """All 5 fingers extended."""
    L = [Landmark(x=wrist_x, y=wrist_y) for _ in range(21)]
    # All fingers extended up — tips far from wrist
    for finger_offset, mcp_idx in [(-0.06, 5), (-0.02, 9), (0.02, 13), (0.06, 17)]:
        L[mcp_idx] = Landmark(x=wrist_x + finger_offset, y=wrist_y - 0.05)
        L[mcp_idx + 1] = Landmark(x=wrist_x + finger_offset, y=wrist_y - 0.10)
        L[mcp_idx + 2] = Landmark(x=wrist_x + finger_offset, y=wrist_y - 0.15)
        L[mcp_idx + 3] = Landmark(x=wrist_x + finger_offset, y=wrist_y - 0.20)
    return L


def _make_hand_point(wrist_x: float = 0.5, wrist_y: float = 0.5) -> list[Landmark]:
    """Only index extended, others curled."""
    L = [Landmark(x=wrist_x, y=wrist_y) for _ in range(21)]
    # Index extended
    L[5] = Landmark(x=wrist_x, y=wrist_y - 0.05)
    L[6] = Landmark(x=wrist_x, y=wrist_y - 0.10)
    L[7] = Landmark(x=wrist_x, y=wrist_y - 0.15)
    L[8] = Landmark(x=wrist_x, y=wrist_y - 0.20)
    # Middle curled — tip close to wrist
    L[9] = Landmark(x=wrist_x + 0.03, y=wrist_y - 0.05)
    L[10] = Landmark(x=wrist_x + 0.03, y=wrist_y - 0.07)
    L[12] = Landmark(x=wrist_x + 0.03, y=wrist_y - 0.04)
    # Ring curled
    L[13] = Landmark(x=wrist_x + 0.05, y=wrist_y - 0.05)
    L[14] = Landmark(x=wrist_x + 0.05, y=wrist_y - 0.07)
    L[16] = Landmark(x=wrist_x + 0.05, y=wrist_y - 0.04)
    # Pinky curled
    L[17] = Landmark(x=wrist_x + 0.07, y=wrist_y - 0.05)
    L[18] = Landmark(x=wrist_x + 0.07, y=wrist_y - 0.07)
    L[20] = Landmark(x=wrist_x + 0.07, y=wrist_y - 0.04)
    return L


def _frame_with_hand(hand: list[Landmark], t: float = 0.0) -> VisionFrame:
    from datetime import datetime, timedelta
    base = datetime(2026, 1, 1) + timedelta(seconds=t)
    vf = VisionFrame(timestamp=base, width=1280, height=720)
    vf.hands = [hand]
    return vf


def test_v_sign_index_middle_extended_returns_v_sign() -> None:
    det = GestureDetector()
    result = det.feed(_frame_with_hand(_make_hand_v_sign(), t=0.0))
    assert "V_SIGN" in result


def test_v_sign_all_fingers_extended_no_trigger() -> None:
    det = GestureDetector()
    result = det.feed(_frame_with_hand(_make_hand_open_palm(), t=0.0))
    assert "V_SIGN" not in result


def test_v_sign_only_index_no_trigger() -> None:
    det = GestureDetector()
    result = det.feed(_frame_with_hand(_make_hand_point(), t=0.0))
    assert "V_SIGN" not in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_gesture_detector.py -v
```
Expected: 3 new tests FAIL.

- [ ] **Step 3: Modify gesture_detector.py**

Read `/Users/tuanln/Ai-Code/NeoMakerViGate/src/neo_makervigate/core/gesture_detector.py` first.

Add constants near top (after WAVE constants):

```python
V_SIGN_COOLDOWN_SEC = 0.4
V_SIGN_FINGER_MARGIN = 1.15
```

Add private helper functions at module level (before `class GestureDetector`):

```python
def _finger_dist_from_wrist(hand: list, idx: int) -> float:
    """Euclidean distance from wrist (idx 0) to landmark at idx."""
    import math as _math
    wrist = hand[0]
    pt = hand[idx]
    return _math.sqrt((pt.x - wrist.x) ** 2 + (pt.y - wrist.y) ** 2)


def _is_finger_extended(hand: list, tip_idx: int, pip_idx: int) -> bool:
    """Finger extended if tip is farther from wrist than its PIP joint."""
    tip_dist = _finger_dist_from_wrist(hand, tip_idx)
    pip_dist = _finger_dist_from_wrist(hand, pip_idx)
    return tip_dist > pip_dist * V_SIGN_FINGER_MARGIN


def _check_v_sign(hand: list) -> bool:
    """V-sign: index + middle extended, ring + pinky curled."""
    if len(hand) < 21:
        return False
    index_ext = _is_finger_extended(hand, 8, 6)
    middle_ext = _is_finger_extended(hand, 12, 10)
    ring_ext = _is_finger_extended(hand, 16, 14)
    pinky_ext = _is_finger_extended(hand, 20, 18)
    return index_ext and middle_ext and not ring_ext and not pinky_ext
```

In `GestureDetector.__init__`, add field:

```python
        self._v_sign_cooldown_until: float = 0.0
```

In `GestureDetector.feed(frame)`, AFTER the existing WAVE check + return statement, BEFORE the final return, add V_SIGN detection. Find this area in feed:

```python
        if len(self._buffer) < WAVE_MIN_SAMPLES:
            return []
        if now < self._cooldown_until:
            return []
        return self._check_wave(now)
```

Refactor to support both gestures. Replace the entire feed method:

```python
    def feed(self, frame: VisionFrame) -> list[str]:
        """Cho ăn 1 frame. Trả về list gesture mới phát hiện trong frame này."""
        now = frame.timestamp.timestamp()
        gestures: list[str] = []

        if not frame.hands:
            self._none_count += 1
            if self._none_count > BUFFER_MAXLEN // 2:
                self._buffer.clear()
                self._none_count = 0
            return gestures

        self._none_count = 0
        first_hand = frame.hands[0]

        # V_SIGN — pose check, no buffer needed
        if now >= self._v_sign_cooldown_until and _check_v_sign(first_hand):
            self._v_sign_cooldown_until = now + V_SIGN_COOLDOWN_SEC
            try:
                SignalBus.instance().gesture_detected.emit("V_SIGN")
            except Exception as e:
                logger.warning(f"gesture_detected V_SIGN emit failed: {e}")
            gestures.append("V_SIGN")

        # WAVE — buffer-based motion check
        wrist_x = first_hand[0].x
        self._buffer.append((now, wrist_x))
        cutoff = now - self._window
        while self._buffer and self._buffer[0][0] < cutoff:
            self._buffer.popleft()
        if len(self._buffer) >= WAVE_MIN_SAMPLES and now >= self._cooldown_until:
            wave_result = self._check_wave(now)
            gestures.extend(wave_result)

        return gestures
```

Note: V_SIGN check fires BEFORE WAVE. Both can fire in same frame if conditions met. Cooldowns are separate.

Also update `reset()` to clear v_sign cooldown:

```python
    def reset(self) -> None:
        self._buffer.clear()
        self._cooldown_until = 0.0
        self._v_sign_cooldown_until = 0.0
        self._none_count = 0
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_gesture_detector.py -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all 11 tests PASS (8 WAVE + 3 V_SIGN). Lint clean.

If old WAVE tests fail, double-check refactor preserved buffer logic. Don't loosen V_SIGN_FINGER_MARGIN unless tests truly mock fingers correctly.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_gesture_detector.py src/neo_makervigate/core/gesture_detector.py
git commit -m "$(cat <<'EOF'
feat(p6): GestureDetector — V_SIGN detection (pose-based)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Selfie Seg in VisionEngine + VisionFrame + VisionWorker

**Files:**
- Modify: `src/neo_makervigate/core/models.py`
- Modify: `src/neo_makervigate/core/vision_engine.py`
- Modify: `src/neo_makervigate/core/vision_worker.py`

No new tests — covered by integration smoke test and PhotoService tests (T4).

- [ ] **Step 1: Add selfie_mask to VisionFrame**

In `src/neo_makervigate/core/models.py`, modify the `VisionFrame` dataclass:

Find:
```python
@dataclass
class VisionFrame:
    """Một khung hình đã qua MediaPipe.
    ...
    """
    timestamp: datetime
    width: int
    height: int
    pose: list[Landmark] = field(default_factory=list)
    hands: list[list[Landmark]] = field(default_factory=list)
    face: list[Landmark] = field(default_factory=list)
    has_person: bool = False
    raw_jpeg_path: Path | None = None
```

Add `import numpy as np` at top if not present. Add field:

```python
import numpy as np
from typing import Any  # if not present

@dataclass
class VisionFrame:
    ...existing fields...
    selfie_mask: np.ndarray[Any, Any] | None = None
```

If `np` import needs guard for mypy, add `from typing import TYPE_CHECKING` and `numpy as np` regardless.

- [ ] **Step 2: Enable selfie branch in vision_engine.read()**

Read `/Users/tuanln/Ai-Code/NeoMakerViGate/src/neo_makervigate/core/vision_engine.py`. Find the for-loop in `read()`:

```python
            for name in self._active:
                detector = self._detectors.get(name)
                if detector is None:
                    continue
                result = detector.detect_for_video(mp_image, ts_ms)  # type: ignore[attr-defined]
                if name == "hands" and result.hand_landmarks:
                    ...
                elif name == "pose" and result.pose_landmarks:
                    ...
                elif name == "face" and result.face_landmarks:
                    ...
```

Selfie segmenter uses `segment_for_video()`, not `detect_for_video()`. Replace the for-loop with this version that branches by method:

```python
            for name in self._active:
                detector = self._detectors.get(name)
                if detector is None:
                    continue
                if name == "selfie":
                    seg_result = detector.segment_for_video(mp_image, ts_ms)  # type: ignore[attr-defined]
                    if seg_result.confidence_masks:
                        # confidence_masks[0] is float32 [0..1] mask of person
                        mask = seg_result.confidence_masks[0].numpy_view()
                        vf.selfie_mask = mask
                        vf.has_person = True
                    continue
                result = detector.detect_for_video(mp_image, ts_ms)  # type: ignore[attr-defined]
                if name == "hands" and result.hand_landmarks:
                    vf.hands = [
                        [Landmark(x=lm.x, y=lm.y, z=lm.z) for lm in hand]
                        for hand in result.hand_landmarks
                    ]
                    vf.has_person = True
                elif name == "pose" and result.pose_landmarks:
                    vf.pose = [
                        Landmark(x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility)
                        for lm in result.pose_landmarks[0]
                    ]
                    vf.has_person = True
                elif name == "face" and result.face_landmarks:
                    vf.face = [
                        Landmark(x=lm.x, y=lm.y, z=lm.z) for lm in result.face_landmarks[0]
                    ]
                    vf.has_person = True
```

- [ ] **Step 3: Expose latest_vision_frame on VisionWorker**

Read `/Users/tuanln/Ai-Code/NeoMakerViGate/src/neo_makervigate/core/vision_worker.py`. Find the existing `latest_frame_bgr` property:

```python
    @property
    def latest_frame_bgr(self) -> np.ndarray[Any, Any] | None:
        """Last raw BGR frame — đọc an toàn từ thread khác."""
        with self._lock:
            return None if self._latest_frame_bgr is None else self._latest_frame_bgr.copy()
```

Add a new property below it:

```python
    @property
    def latest_vision_frame(self) -> VisionFrame | None:
        """Last VisionFrame (with landmarks + selfie_mask)."""
        with self._lock:
            return self._latest_vision_frame
```

This reads existing `self._latest_vision_frame` field (already set in `run()` loop from P1).

- [ ] **Step 4: Verify tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass (no new tests, only ensure no regression).

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/core/models.py src/neo_makervigate/core/vision_engine.py src/neo_makervigate/core/vision_worker.py
git commit -m "$(cat <<'EOF'
feat(p6): selfie seg in VisionEngine + VisionFrame.selfie_mask + latest_vision_frame property

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: PhotoCapture.save_composite

**Files:**
- Modify: `src/neo_makervigate/core/photo_capture.py`
- Modify: `tests/unit/test_photo_capture.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/unit/test_photo_capture.py`:

```python
def test_save_composite_with_full_mask_returns_foreground(tmp_path: Path) -> None:
    """Mask all 1 (full foreground) → composite ≈ foreground frame."""
    import cv2
    pc = PhotoCapture(base_dir=tmp_path)
    photo_dir = pc.make_photo_dir("photo_t_full")
    # Foreground: solid red
    fg = np.zeros((360, 640, 3), dtype=np.uint8)
    fg[:, :, 2] = 255  # red (BGR)
    # Background: solid blue
    bg_path = tmp_path / "bg.png"
    bg = np.zeros((360, 640, 3), dtype=np.uint8)
    bg[:, :, 0] = 255
    cv2.imwrite(str(bg_path), bg)
    # Mask: all 1.0
    mask = np.ones((360, 640), dtype=np.float32)

    path = pc.save_composite(fg, mask, bg_path, photo_dir)
    assert path == photo_dir / "composite.jpg"
    assert path.exists()
    out = cv2.imread(str(path))
    # Center pixel should be red (foreground) since mask=1
    assert out[180, 320, 2] > 200, f"expected red center, got BGR={out[180, 320]}"
    assert out[180, 320, 0] < 50, f"expected no blue, got BGR={out[180, 320]}"


def test_save_composite_with_zero_mask_returns_background_only(tmp_path: Path) -> None:
    """Mask all 0 (no foreground) → composite ≈ background."""
    import cv2
    pc = PhotoCapture(base_dir=tmp_path)
    photo_dir = pc.make_photo_dir("photo_t_zero")
    fg = np.zeros((360, 640, 3), dtype=np.uint8)
    fg[:, :, 2] = 255  # red
    bg_path = tmp_path / "bg2.png"
    bg = np.zeros((360, 640, 3), dtype=np.uint8)
    bg[:, :, 0] = 255  # blue
    cv2.imwrite(str(bg_path), bg)
    mask = np.zeros((360, 640), dtype=np.float32)

    path = pc.save_composite(fg, mask, bg_path, photo_dir)
    out = cv2.imread(str(path))
    # Center should be blue (background)
    assert out[180, 320, 0] > 200
    assert out[180, 320, 2] < 50


def test_save_composite_writes_jpg(tmp_path: Path) -> None:
    """Composite file is valid JPG."""
    import cv2
    pc = PhotoCapture(base_dir=tmp_path)
    photo_dir = pc.make_photo_dir("photo_t_jpg")
    fg = np.zeros((360, 640, 3), dtype=np.uint8)
    fg[:, :, 1] = 200
    bg_path = tmp_path / "bg3.png"
    bg = np.zeros((360, 640, 3), dtype=np.uint8)
    bg[:, :, 1] = 100
    cv2.imwrite(str(bg_path), bg)
    mask = np.ones((360, 640), dtype=np.float32) * 0.5

    path = pc.save_composite(fg, mask, bg_path, photo_dir)
    assert path.exists()
    with open(path, "rb") as f:
        header = f.read(3)
    assert header[:3] == b"\xff\xd8\xff"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_photo_capture.py -v
```
Expected: 3 new tests FAIL — `save_composite` not defined.

- [ ] **Step 3: Add save_composite method**

In `src/neo_makervigate/core/photo_capture.py`, add the method to PhotoCapture class (after `save_original`):

```python
    def save_composite(
        self,
        frame_bgr: np.ndarray[Any, Any],
        mask: np.ndarray[Any, Any],
        background_path: Path,
        photo_dir: Path,
    ) -> Path:
        """Composite foreground (trẻ) vào background, lưu composite.jpg.

        Soft mask + Gaussian blur edges để cạnh mượt.
        - frame_bgr: BGR HxWx3 uint8
        - mask: float32 HxW with values [0..1] (1 = person, 0 = background)
        - background_path: PNG/JPG to use as background
        - photo_dir: output directory
        """
        if not photo_dir.exists():
            raise FileNotFoundError(f"photo_dir does not exist: {photo_dir}")
        h, w = frame_bgr.shape[:2]
        bg = cv2.imread(str(background_path))
        if bg is None:
            raise FileNotFoundError(f"background not found: {background_path}")
        bg = cv2.resize(bg, (w, h))

        # Resize mask to frame dimensions if needed
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

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_photo_capture.py -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all 9 tests PASS (6 existing + 3 new).

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/core/photo_capture.py tests/unit/test_photo_capture.py
git commit -m "$(cat <<'EOF'
feat(p6): PhotoCapture.save_composite — alpha blend with Gaussian blur edges

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: PhotoService — handle background_path → composite

**Files:**
- Modify: `src/neo_makervigate/services/photo_service.py`
- Modify: `tests/unit/test_photo_service.py`

- [ ] **Step 1: Append failing test**

Append to `tests/unit/test_photo_service.py`:

```python
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
    # Foreground frame: green
    fg = np.zeros((360, 640, 3), dtype=np.uint8)
    fg[:, :, 1] = 200
    # VisionFrame with selfie_mask all 1.0
    vf = VisionFrame(
        timestamp=datetime.now(),
        width=640, height=360,
        selfie_mask=np.ones((360, 640), dtype=np.float32),
    )
    worker = _FakeWorkerWithVf(frame=fg, vf=vf)

    # Write background file
    bg_path = tmp_path / "bg.png"
    bg = np.zeros((360, 640, 3), dtype=np.uint8)
    bg[:, :, 0] = 255  # blue
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
    # URL should point to composite.jpg
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
```

Also update the existing `_FakeWorker` class to add `latest_vision_frame` returning None (so existing tests still work):

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_photo_service.py -v
```
Expected: 2 new tests FAIL — composite logic not yet implemented.

- [ ] **Step 3: Modify photo_service.py**

In `src/neo_makervigate/services/photo_service.py`, find this section in `_on_capture_request`:

```python
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
```

Replace with composite-aware version:

```python
        try:
            photo_id = self._capture.make_photo_id(experience_id)
            photo_dir = self._capture.make_photo_dir(photo_id)
            original_path = self._capture.save_original(frame, photo_dir)

            # Optional composite (P6 — exp06 Photo Booth)
            composite_path: Path | None = None
            bg_path_str = params.get("background_path") if isinstance(params, dict) else None
            if bg_path_str:
                bg_path = Path(str(bg_path_str))
                latest_vf = getattr(self._worker, "latest_vision_frame", None)
                if latest_vf is not None and getattr(latest_vf, "selfie_mask", None) is not None:
                    try:
                        composite_path = self._capture.save_composite(
                            frame, latest_vf.selfie_mask, bg_path, photo_dir,
                        )
                    except Exception as e:
                        logger.warning(f"Composite failed, falling back to original: {e}")
                else:
                    logger.warning("background_path provided but no selfie_mask available")

            filename = "composite.jpg" if composite_path is not None else "original.jpg"
            url = self._share.make_share_url(photo_id, filename=filename)
            qr_path = self._share.make_qr(url, photo_dir)
            cleanup_if_over_limit(self._photos_base)

            result = PhotoResult(
                success=True,
                photo_id=photo_id,
                original_path=original_path,
                composite_path=composite_path,
                qr_path=qr_path,
                download_url=url,
                experience_id=experience_id,
            )
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass (7 PhotoService tests now: 5 original + 2 composite).

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/services/photo_service.py tests/unit/test_photo_service.py
git commit -m "$(cat <<'EOF'
feat(p6): PhotoService composite from selfie_mask + background_path

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: QwenClient Protocol + QwenLocalBackend

**Files:**
- Create: `src/neo_makervigate/core/qwen_client.py`
- Create: `tests/unit/test_qwen_client.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_qwen_client.py`:

```python
"""Tests cho core/qwen_client — Qwen 2.5-VL local backend."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from neo_makervigate.core.qwen_client import (
    DEFAULT_MMPROJ_NAME,
    DEFAULT_MODEL_NAME,
    MODELS_DIR,
    QwenClient,
    QwenLocalBackend,
)


def test_local_backend_is_ready_false_when_model_missing(tmp_path: Path) -> None:
    backend = QwenLocalBackend(
        model_path=tmp_path / "nonexistent.gguf",
        mmproj_path=tmp_path / "nonexistent_mmproj.gguf",
    )
    assert backend.is_ready() is False


def test_local_backend_is_ready_true_when_files_exist(tmp_path: Path) -> None:
    model = tmp_path / DEFAULT_MODEL_NAME
    mmproj = tmp_path / DEFAULT_MMPROJ_NAME
    model.write_bytes(b"fake-model")
    mmproj.write_bytes(b"fake-mmproj")
    backend = QwenLocalBackend(model_path=model, mmproj_path=mmproj)
    assert backend.is_ready() is True


def test_describe_image_raises_when_model_missing(tmp_path: Path) -> None:
    backend = QwenLocalBackend(
        model_path=tmp_path / "missing.gguf",
        mmproj_path=tmp_path / "missing_mmproj.gguf",
    )
    img_path = tmp_path / "img.jpg"
    img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # fake JPEG header
    with pytest.raises(FileNotFoundError, match="Qwen model not found"):
        backend.describe_image(img_path, "Describe this", max_tokens=10)


def test_describe_image_calls_llama_with_image_and_prompt(tmp_path: Path) -> None:
    """Verify backend wires up llama-cpp correctly. Mock Llama + chat handler."""
    # Set up fake model files so is_ready() passes
    model = tmp_path / DEFAULT_MODEL_NAME
    mmproj = tmp_path / DEFAULT_MMPROJ_NAME
    model.write_bytes(b"fake")
    mmproj.write_bytes(b"fake")

    # Create a small real JPEG (use Pillow if available, else minimal valid header)
    from PIL import Image as PILImage
    img_path = tmp_path / "test.jpg"
    PILImage.new("RGB", (100, 100), color="red").save(img_path)

    backend = QwenLocalBackend(model_path=model, mmproj_path=mmproj)

    # Mock llama_cpp imports
    mock_llm = MagicMock()
    mock_llm.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "Một bức ảnh đẹp! 📸"}}]
    }
    mock_llama_class = MagicMock(return_value=mock_llm)
    mock_handler_class = MagicMock()

    with patch.dict("sys.modules", {
        "llama_cpp": MagicMock(Llama=mock_llama_class),
        "llama_cpp.llama_chat_format": MagicMock(Qwen25VLChatHandler=mock_handler_class),
    }):
        result = backend.describe_image(img_path, "Describe this image", max_tokens=50)

    assert result == "Một bức ảnh đẹp! 📸"
    mock_llm.create_chat_completion.assert_called_once()
    call_args = mock_llm.create_chat_completion.call_args
    messages = call_args.kwargs["messages"]
    # Should contain image_url and text
    content = messages[0]["content"]
    assert any(c.get("type") == "image_url" for c in content)
    assert any(c.get("type") == "text" and "Describe" in c["text"] for c in content)


def test_qwen_protocol_runtime_checkable_with_fake_backend() -> None:
    """A class implementing the protocol methods should satisfy isinstance(QwenClient)."""

    class FakeBackend:
        def describe_image(self, image_path: Path, prompt: str, max_tokens: int = 80) -> str:
            return "fake"

        def is_ready(self) -> bool:
            return True

    fake = FakeBackend()
    # Protocol may not be runtime_checkable by default; structural check via hasattr
    assert hasattr(fake, "describe_image")
    assert hasattr(fake, "is_ready")
    # If QwenClient is decorated @runtime_checkable, this works:
    # assert isinstance(fake, QwenClient)
    _ = QwenClient  # silence unused-import
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_qwen_client.py -v
```
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 3: Create qwen_client.py**

Create `src/neo_makervigate/core/qwen_client.py`:

```python
"""Qwen 2.5-VL local client cho caption generation.

Protocol-based: dễ swap LocalBackend (llama-cpp-python) ↔ APIBackend (DashScope).
P6 chỉ implement LocalBackend.

Model: Qwen 2.5-VL-2B-Instruct quantized Q4_K_M (~1GB RAM).
Chạy trên Mac M4 CPU OK; NEO One 2GB cần spike verify (S2).
"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from loguru import logger
from PIL import Image


@runtime_checkable
class QwenClient(Protocol):
    """Interface mọi backend phải implement."""

    def describe_image(
        self,
        image_path: Path,
        prompt: str,
        max_tokens: int = 80,
    ) -> str: ...

    def is_ready(self) -> bool: ...


MODELS_DIR = Path.home() / "makervigate" / "models" / "qwen"
DEFAULT_MODEL_NAME = "qwen2.5-vl-2b-instruct-q4_k_m.gguf"
DEFAULT_MMPROJ_NAME = "qwen2.5-vl-2b-instruct-mmproj-f16.gguf"
DEFAULT_CONTEXT_SIZE = 2048


class QwenLocalBackend:
    """llama-cpp-python backend chạy Qwen 2.5-VL local trên CPU.

    Model loaded lazy lần đầu describe_image() — process boot không block.
    """

    def __init__(
        self,
        model_path: Path | None = None,
        mmproj_path: Path | None = None,
        n_ctx: int = DEFAULT_CONTEXT_SIZE,
    ) -> None:
        self._model_path = model_path or (MODELS_DIR / DEFAULT_MODEL_NAME)
        self._mmproj_path = mmproj_path or (MODELS_DIR / DEFAULT_MMPROJ_NAME)
        self._n_ctx = n_ctx
        self._llm: Any = None

    def is_ready(self) -> bool:
        return self._model_path.exists() and self._mmproj_path.exists()

    def _ensure_loaded(self) -> None:
        if self._llm is not None:
            return
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
            n_ctx=self._n_ctx,
            n_gpu_layers=0,
            verbose=False,
        )
        logger.info(f"Qwen loaded: {self._model_path.name}")

    def describe_image(
        self,
        image_path: Path,
        prompt: str,
        max_tokens: int = 80,
    ) -> str:
        self._ensure_loaded()
        if self._llm is None:
            raise RuntimeError("Qwen model failed to load")

        # Encode image as base64 data URI
        img = Image.open(image_path).convert("RGB")
        img.thumbnail((512, 512))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        data_uri = f"data:image/jpeg;base64,{b64}"

        response = self._llm.create_chat_completion(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_uri}},
                    {"type": "text", "text": prompt},
                ],
            }],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        text: str = response["choices"][0]["message"]["content"].strip()
        return text
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_qwen_client.py -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: 5 tests PASS. mypy may complain about `Any` from llama_cpp — that's expected since it's an optional dep.

If mypy fails on llama_cpp import, add to pyproject.toml `[[tool.mypy.overrides]]`:
```toml
module = ["llama_cpp", "llama_cpp.*"]
ignore_missing_imports = true
```

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_qwen_client.py src/neo_makervigate/core/qwen_client.py pyproject.toml
git commit -m "$(cat <<'EOF'
feat(p6): QwenClient Protocol + QwenLocalBackend (llama-cpp-python)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: QwenService — QThread wrapper

**Files:**
- Create: `src/neo_makervigate/services/qwen_service.py`
- Create: `tests/unit/test_qwen_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_qwen_service.py`:

```python
"""Tests cho services/qwen_service — QThread wrapper for Qwen inference."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from neo_makervigate.services.qwen_service import QwenService
from neo_makervigate.utils.signal_bus import SignalBus


class _FakeBackend:
    """Backend stub that returns a canned response or raises."""

    def __init__(self, response: str = "Một bức ảnh!", raise_exc: Exception | None = None) -> None:
        self._response = response
        self._raise = raise_exc
        self.calls: list[dict] = []

    def is_ready(self) -> bool:
        return True

    def describe_image(self, image_path: Path, prompt: str, max_tokens: int = 80) -> str:
        self.calls.append({"image_path": image_path, "prompt": prompt, "max_tokens": max_tokens})
        if self._raise:
            raise self._raise
        return self._response


def _wait_signal(events: list, timeout: float = 2.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline and not events:
        time.sleep(0.05)


def test_qwen_service_calls_backend_via_signal(tmp_path: Path, qapp) -> None:
    backend = _FakeBackend(response="Em đứng cười tươi! 🌞")
    svc = QwenService(client=backend)
    try:
        responses: list[str] = []
        SignalBus.instance().qwen_response_ready.connect(lambda t: responses.append(t))
        img = tmp_path / "x.jpg"
        img.write_bytes(b"fake")
        SignalBus.instance().qwen_request_started.emit({
            "image_path": str(img),
            "prompt": "Mô tả ảnh",
            "max_tokens": 50,
        })
        _wait_signal(responses)
        qapp.processEvents()
        assert len(backend.calls) == 1
        assert backend.calls[0]["prompt"] == "Mô tả ảnh"
        assert responses == ["Em đứng cười tươi! 🌞"]
    finally:
        svc.stop()


def test_qwen_service_emits_response_on_success(tmp_path: Path, qapp) -> None:
    backend = _FakeBackend(response="caption ok")
    svc = QwenService(client=backend)
    try:
        responses: list[str] = []
        failures: list[str] = []
        SignalBus.instance().qwen_response_ready.connect(lambda t: responses.append(t))
        SignalBus.instance().qwen_failed.connect(lambda e: failures.append(e))
        img = tmp_path / "y.jpg"
        img.write_bytes(b"fake")
        SignalBus.instance().qwen_request_started.emit({
            "image_path": str(img), "prompt": "p",
        })
        _wait_signal(responses)
        qapp.processEvents()
        assert responses == ["caption ok"]
        assert failures == []
    finally:
        svc.stop()


def test_qwen_service_emits_failed_on_exception(tmp_path: Path, qapp) -> None:
    backend = _FakeBackend(raise_exc=RuntimeError("model crashed"))
    svc = QwenService(client=backend)
    try:
        failures: list[str] = []
        SignalBus.instance().qwen_failed.connect(lambda e: failures.append(e))
        img = tmp_path / "z.jpg"
        img.write_bytes(b"fake")
        SignalBus.instance().qwen_request_started.emit({
            "image_path": str(img), "prompt": "p",
        })
        _wait_signal(failures)
        qapp.processEvents()
        assert len(failures) == 1
        assert "model crashed" in failures[0]
    finally:
        svc.stop()


def test_qwen_service_stop_terminates_thread_cleanly(qapp) -> None:
    backend = _FakeBackend()
    svc = QwenService(client=backend)
    svc.stop()
    # If we get here without hang, thread terminated. Verify worker not running:
    assert not svc._worker.isRunning()  # type: ignore[attr-defined]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_qwen_service.py -v
```
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 3: Create qwen_service.py**

Create `src/neo_makervigate/services/qwen_service.py`:

```python
"""QwenService — QThread wrapper for QwenClient.

Listens: SignalBus.qwen_request_started(dict)
Emits:   SignalBus.qwen_response_ready(str) — caption text
         SignalBus.qwen_failed(str) — error message

Inference can take 4-8s; QThread keeps UI responsive.
"""

from __future__ import annotations

import queue
from pathlib import Path
from typing import Any

from loguru import logger
from PyQt6.QtCore import QThread

from neo_makervigate.core.qwen_client import QwenClient
from neo_makervigate.utils.signal_bus import SignalBus


class _QwenWorker(QThread):
    """Background thread chạy inference."""

    def __init__(self, client: QwenClient) -> None:
        super().__init__()
        self._client = client
        self._queue: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self._running = False

    def enqueue(self, request: dict[str, Any]) -> None:
        self._queue.put(request)

    def stop(self) -> None:
        self._running = False
        self._queue.put(None)  # poison pill
        self.wait(3000)

    def run(self) -> None:
        self._running = True
        bus = SignalBus.instance()
        while self._running:
            item = self._queue.get()
            if item is None:
                break
            try:
                image_path = Path(str(item["image_path"]))
                prompt = str(item["prompt"])
                max_tokens = int(item.get("max_tokens", 80))
                text = self._client.describe_image(image_path, prompt, max_tokens)
                bus.qwen_response_ready.emit(text)
            except Exception as e:
                logger.exception(f"Qwen inference failed: {e}")
                bus.qwen_failed.emit(str(e))


class QwenService:
    """Facade — instantiate at app boot, holds reference to QThread worker."""

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

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_qwen_service.py -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_qwen_service.py src/neo_makervigate/services/qwen_service.py
git commit -m "$(cat <<'EOF'
feat(p6): QwenService — QThread wrapper for async inference

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: download_qwen.py script + QWEN_SETUP.md

**Files:**
- Create: `src/neo_makervigate/scripts/__init__.py`
- Create: `src/neo_makervigate/scripts/download_qwen.py`
- Create: `DOC/QWEN_SETUP.md`

- [ ] **Step 1: Create scripts package**

```bash
mkdir -p /Users/tuanln/Ai-Code/NeoMakerViGate/src/neo_makervigate/scripts
touch /Users/tuanln/Ai-Code/NeoMakerViGate/src/neo_makervigate/scripts/__init__.py
```

- [ ] **Step 2: Create download_qwen.py**

Create `src/neo_makervigate/scripts/download_qwen.py`:

```python
"""Download Qwen 2.5-VL-2B GGUF model files for local inference.

Usage: python -m neo_makervigate.scripts.download_qwen
Downloads to ~/makervigate/models/qwen/ (~1.5GB total).
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

from loguru import logger

from neo_makervigate.core.qwen_client import (
    DEFAULT_MMPROJ_NAME,
    DEFAULT_MODEL_NAME,
    MODELS_DIR,
)


URLS = {
    DEFAULT_MODEL_NAME: (
        "https://huggingface.co/bartowski/Qwen2.5-VL-2B-Instruct-GGUF/"
        "resolve/main/Qwen2.5-VL-2B-Instruct-Q4_K_M.gguf"
    ),
    DEFAULT_MMPROJ_NAME: (
        "https://huggingface.co/bartowski/Qwen2.5-VL-2B-Instruct-GGUF/"
        "resolve/main/mmproj-Qwen2.5-VL-2B-Instruct-f16.gguf"
    ),
}


def main() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in URLS.items():
        out = MODELS_DIR / name
        if out.exists():
            logger.info(f"Already exists: {out.name} ({out.stat().st_size // 1024 // 1024} MB)")
            continue
        logger.info(f"Downloading {name}...")
        logger.info(f"  from {url}")
        logger.info(f"  to   {out}")
        urllib.request.urlretrieve(url, out)
        logger.info(f"  done: {out.stat().st_size // 1024 // 1024} MB")
    logger.info("All Qwen models ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Create QWEN_SETUP.md**

Create `DOC/QWEN_SETUP.md`:

```markdown
# Qwen 2.5-VL Local Setup

Hướng dẫn cài Qwen 2.5-VL-2B local cho caption tiếng Việt trong exp06 Photo Booth.

## 1. Cài llama-cpp-python

```bash
.venv/bin/pip install llama-cpp-python
```

Trên Mac M4: dùng OpenBLAS hoặc Metal backend tuỳ chọn — default CPU OK cho 2B model.

Trên ARM64 NEO One: pin trong `requirements-arm64.txt`. Có thể cần compile từ source — xem llama-cpp-python README cho ARM build flags.

## 2. Download model

```bash
.venv/bin/python -m neo_makervigate.scripts.download_qwen
```

Files (~1.5GB) sẽ lưu tại `~/makervigate/models/qwen/`:
- `qwen2.5-vl-2b-instruct-q4_k_m.gguf` (~1.1GB) — quantized weights
- `qwen2.5-vl-2b-instruct-mmproj-f16.gguf` (~400MB) — vision projector

Nguồn: `bartowski/Qwen2.5-VL-2B-Instruct-GGUF` trên HuggingFace.

## 3. Verify

```bash
.venv/bin/python -c "
from pathlib import Path
from neo_makervigate.core.qwen_client import QwenLocalBackend
b = QwenLocalBackend()
print('Ready:', b.is_ready())
# Test inference (đợi 4-8s lần đầu)
from PIL import Image
test_img = Path('/tmp/test_qwen.jpg')
Image.new('RGB', (200, 200), color='red').save(test_img)
print(b.describe_image(test_img, 'Mô tả ảnh trong 1 câu, có emoji.', max_tokens=50))
"
```

Expected: caption tiếng Việt 1 câu, < 10s trên Mac M4.

## 4. Fallback

Nếu model không có hoặc Qwen fail:
- exp06 sẽ dùng caption template từ `experiences/exp06_photo_booth/prompts.toml`
- Mỗi background có 1 template fallback caption
- User vẫn có thể chơi Photo Booth, chỉ là caption không personalized

## 5. Disk space

Model files: 1.5GB. Có thể xoá khi không cần:
```bash
rm -rf ~/makervigate/models/qwen/
```

Sau đó exp06 tự fallback template caption.
```

- [ ] **Step 4: Verify lint + tests**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/scripts/ DOC/QWEN_SETUP.md
git commit -m "$(cat <<'EOF'
feat(p6): scripts/download_qwen.py + QWEN_SETUP.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: BaseExperience.auto_capture_on_done + ExperienceManager check

**Files:**
- Modify: `src/neo_makervigate/experiences/experience_base.py`
- Modify: `src/neo_makervigate/services/experience_manager.py`
- Modify: `tests/unit/test_experience_manager.py`

- [ ] **Step 1: Append failing test**

Append to `tests/unit/test_experience_manager.py`:

```python
def test_auto_capture_on_done_false_skips_photo_request(qapp) -> None:
    """Plugin với auto_capture_on_done=False → manager KHÔNG emit photo_capture_requested."""
    from datetime import datetime
    from neo_makervigate.core.models import ExperienceMeta, VisionFrame
    from neo_makervigate.experiences.experience_base import BaseExperience

    class _SelfOrchExp(BaseExperience):
        auto_capture_on_done = False
        meta = ExperienceMeta(
            id="self_orch",
            title="SelfOrch",
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
            return {"phase": "done"} if self.frames >= 2 else {"phase": "playing"}

        def completion_summary(self) -> dict[str, object]:
            return {"completed": True}

    mgr = ExperienceManager(registry={"self_orch": _SelfOrchExp})
    mgr.load("self_orch")
    requests: list[dict] = []
    SignalBus.instance().photo_capture_requested.connect(lambda p: requests.append(p))

    bus = SignalBus.instance()
    bus.vision_frame_ready.emit(VisionFrame(timestamp=datetime.now(), width=640, height=360))
    bus.vision_frame_ready.emit(VisionFrame(timestamp=datetime.now(), width=640, height=360))

    assert mgr.current_id is None  # unloaded
    assert requests == []  # NO photo_capture_requested emitted
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_experience_manager.py::test_auto_capture_on_done_false_skips_photo_request -v
```
Expected: FAIL — `len(requests)` is 1 (currently always emits).

- [ ] **Step 3: Add auto_capture_on_done to BaseExperience**

Read `/Users/tuanln/Ai-Code/NeoMakerViGate/src/neo_makervigate/experiences/experience_base.py`. Add class attribute to `BaseExperience` (place near `meta: ClassVar[ExperienceMeta]`):

```python
    # Plugin can override to False (e.g., exp06 self-orchestrates capture+caption)
    auto_capture_on_done: ClassVar[bool] = True
```

- [ ] **Step 4: Modify ExperienceManager._on_vision_frame**

In `src/neo_makervigate/services/experience_manager.py`, find the phase=done block (modified by P5):

```python
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
```

Replace with:

```python
                if isinstance(state, dict) and state.get("phase") == "done":
                    summary_fn = getattr(self._current_instance, "completion_summary", None)
                    summary = summary_fn() if callable(summary_fn) else {"completed": True}
                    exp_id = self._current_id or ""
                    # P6: skip auto-capture if plugin self-orchestrates (e.g., exp06)
                    auto_capture = getattr(self._current_instance, "auto_capture_on_done", True)
                    if auto_capture:
                        SignalBus.instance().photo_capture_requested.emit({
                            "experience_id": exp_id,
                            "summary": summary,
                        })
                    self.unload(summary)
                    return
```

- [ ] **Step 5: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass (including new + previous P5 test still passes since BaseExperience default is True).

- [ ] **Step 6: Commit**

```bash
git add src/neo_makervigate/experiences/experience_base.py src/neo_makervigate/services/experience_manager.py tests/unit/test_experience_manager.py
git commit -m "$(cat <<'EOF'
feat(p6): BaseExperience.auto_capture_on_done + manager check

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: SignalBus.photo_caption_ready + AppController slot

**Files:**
- Modify: `src/neo_makervigate/utils/signal_bus.py`
- Modify: `src/neo_makervigate/services/app_controller.py`
- Modify: `tests/unit/test_app_controller.py`

- [ ] **Step 1: Append failing test**

Append to `tests/unit/test_app_controller.py`:

```python
def test_photo_caption_ready_updates_photo_result(qapp) -> None:
    """When photo_caption_ready signal fires, photoResult dict gets caption populated."""
    from pathlib import Path
    from neo_makervigate.core.models import PhotoResult
    from neo_makervigate.utils.signal_bus import SignalBus

    ctrl = AppController(experience_manager=None)
    # First, simulate photo_captured to set photoResult base
    result = PhotoResult(
        success=True,
        photo_id="photo_abc",
        original_path=Path("/tmp/orig.jpg"),
        qr_path=Path("/tmp/qr.png"),
        download_url="http://x/photo_abc/original.jpg",
        experience_id="exp06_photo_booth",
    )
    SignalBus.instance().photo_captured.emit(result)
    qapp.processEvents()
    assert ctrl.photoResult["caption"] == ""

    # Now fire photo_caption_ready
    changes: list[bool] = []
    ctrl.photoResultChanged.connect(lambda: changes.append(True))
    SignalBus.instance().photo_caption_ready.emit("photo_abc", "Em đứng cười tươi! 🌞")
    qapp.processEvents()
    assert ctrl.photoResult["caption"] == "Em đứng cười tươi! 🌞"
    assert len(changes) >= 1


def test_photo_caption_ready_ignored_for_different_photo_id(qapp) -> None:
    """Mismatched photo_id → caption not applied."""
    from pathlib import Path
    from neo_makervigate.core.models import PhotoResult
    from neo_makervigate.utils.signal_bus import SignalBus

    ctrl = AppController(experience_manager=None)
    result = PhotoResult(
        success=True,
        photo_id="photo_xyz",
        original_path=Path("/tmp/o.jpg"),
        qr_path=Path("/tmp/q.png"),
        download_url="http://x",
        experience_id="exp",
    )
    SignalBus.instance().photo_captured.emit(result)
    qapp.processEvents()

    SignalBus.instance().photo_caption_ready.emit("photo_other", "wrong caption")
    qapp.processEvents()
    assert ctrl.photoResult["caption"] == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_app_controller.py -v
```
Expected: 2 new tests FAIL — `photo_caption_ready` signal doesn't exist.

- [ ] **Step 3: Add photo_caption_ready to SignalBus**

In `src/neo_makervigate/utils/signal_bus.py`, find the Photo section:

```python
    # ── Photo ───────────────────────────────────────────────────
    photo_capture_requested = pyqtSignal(dict)
    photo_captured = pyqtSignal(object)  # PhotoResult (P5)
```

Add a new signal:

```python
    # ── Photo ───────────────────────────────────────────────────
    photo_capture_requested = pyqtSignal(dict)
    photo_captured = pyqtSignal(object)  # PhotoResult (P5)
    photo_caption_ready = pyqtSignal(str, str)  # photo_id, caption text (P6)
```

- [ ] **Step 4: Add slot in AppController**

In `src/neo_makervigate/services/app_controller.py`, find the `_on_photo_captured` slot. Modify the dict to initialize `caption` field:

```python
        self._photo_result = {
            "photo_id": result.photo_id,
            "original_path": str(result.original_path) if result.original_path else "",
            "composite_path": str(result.composite_path) if result.composite_path else "",  # NEW
            "qr_path": str(result.qr_path) if result.qr_path else "",
            "download_url": result.download_url or "",
            "experience_id": result.experience_id,
            "caption": "",  # populated by photo_caption_ready signal
        }
```

In `__init__`, after `bus.photo_captured.connect(...)` line, add:

```python
        bus.photo_caption_ready.connect(self._on_photo_caption_ready)
```

Add new slot (place near _on_photo_captured):

```python
    @pyqtSlot(str, str)
    def _on_photo_caption_ready(self, photo_id: str, caption: str) -> None:
        if self._photo_result.get("photo_id") != photo_id:
            return
        self._photo_result = dict(self._photo_result)
        self._photo_result["caption"] = caption
        self.photoResultChanged.emit()
```

- [ ] **Step 5: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/neo_makervigate/utils/signal_bus.py src/neo_makervigate/services/app_controller.py tests/unit/test_app_controller.py
git commit -m "$(cat <<'EOF'
feat(p6): photo_caption_ready signal + AppController slot

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: exp06 backgrounds + prompts.toml + _gen_assets.py

**Files:**
- Create: `src/neo_makervigate/experiences/exp06_photo_booth/prompts.toml`
- Create: `src/neo_makervigate/experiences/exp06_photo_booth/_gen_assets.py`
- Create: `src/neo_makervigate/experiences/exp06_photo_booth/backgrounds/*.png` (4 files)

- [ ] **Step 1: Create prompts.toml**

Create `src/neo_makervigate/experiences/exp06_photo_booth/prompts.toml`:

```toml
[caption]
system_prompt = "Bạn là người viết caption ảnh cho trẻ em Việt Nam, vui vẻ, ấm áp, 1 câu ngắn, có 1 emoji."
user_prompt = "Hãy viết 1 câu caption ngắn vui cho ảnh này, có 1 emoji phù hợp. Chỉ trả về caption, không giải thích."

[fallback]
san_dinh = "🏛️ Em đứng trước sân đình quê hương!"
luy_tre = "🎍 Lũy tre xanh ôm em vào lòng làng."
san_fgc = "🎮 Em đang ở Trạm Maker FPT Shop!"
sao_hoa = "🚀 Phi hành gia nhí trên sao Hỏa!"
```

- [ ] **Step 2: Create _gen_assets.py**

Create `src/neo_makervigate/experiences/exp06_photo_booth/_gen_assets.py`:

```python
"""Generate 4 background PNGs cho Photo Booth procedurally via Pillow.

Chạy: python -m neo_makervigate.experiences.exp06_photo_booth._gen_assets
Output: backgrounds/{san_dinh,luy_tre,san_fgc,sao_hoa}.png (1280x720)
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).parent / "backgrounds"
WIDTH = 1280
HEIGHT = 720


def _gradient_bg(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    """Vertical gradient."""
    img = Image.new("RGB", (WIDTH, HEIGHT))
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(top[0] * (1 - ratio) + bottom[0] * ratio)
        g = int(top[1] * (1 - ratio) + bottom[1] * ratio)
        b = int(top[2] * (1 - ratio) + bottom[2] * ratio)
        for x in range(WIDTH):
            img.putpixel((x, y), (r, g, b))
    return img


def _gradient_bg_fast(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    """Fast gradient via numpy."""
    import numpy as np
    arr = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for c in range(3):
        col = np.linspace(top[c], bottom[c], HEIGHT, dtype=np.float32)
        arr[:, :, c] = np.tile(col[:, None], (1, WIDTH)).astype(np.uint8)
    return Image.fromarray(arr)


def gen_san_dinh() -> None:
    """Sân Đình — sky blue top, brown/red ground."""
    img = _gradient_bg_fast((135, 206, 235), (139, 90, 60))
    draw = ImageDraw.Draw(img)
    # Simplified dinh silhouette
    # Roof — red triangle
    draw.polygon([(440, 280), (840, 280), (640, 180)], fill=(178, 34, 34))
    # Building body — brown rectangle
    draw.rectangle([(480, 280), (800, 520)], fill=(160, 100, 60))
    # 3 columns — yellow
    for x in [520, 620, 720]:
        draw.rectangle([(x, 320), (x + 30, 520)], fill=(218, 165, 32))
    # Door
    draw.rectangle([(615, 400), (665, 520)], fill=(101, 67, 33))
    # Text label corner
    draw.text((40, 40), "Sân Đình", fill=(255, 255, 255))
    img.save(ASSETS_DIR / "san_dinh.png")
    print(f"Wrote {ASSETS_DIR / 'san_dinh.png'}")


def gen_luy_tre() -> None:
    """Lũy Tre — green hues, vertical bamboo strokes."""
    img = _gradient_bg_fast((180, 220, 140), (60, 130, 40))
    draw = ImageDraw.Draw(img)
    # Many bamboo stalks
    for x in range(80, WIDTH, 90):
        draw.rectangle([(x, 100), (x + 18, HEIGHT)], fill=(85, 140, 60))
        # nodes
        for ny in range(150, HEIGHT, 90):
            draw.rectangle([(x - 2, ny), (x + 20, ny + 4)], fill=(45, 95, 30))
    draw.text((40, 40), "Lũy Tre", fill=(255, 255, 255))
    img.save(ASSETS_DIR / "luy_tre.png")
    print(f"Wrote {ASSETS_DIR / 'luy_tre.png'}")


def gen_san_fgc() -> None:
    """Sân FGC — modern store, white + orange + blue."""
    img = _gradient_bg_fast((230, 240, 255), (200, 210, 230))
    draw = ImageDraw.Draw(img)
    # Storefront — large rectangle
    draw.rectangle([(200, 100), (1080, 600)], fill=(255, 255, 255))
    draw.rectangle([(200, 100), (1080, 200)], fill=(247, 135, 36))  # orange banner
    # 'F P T   S h o p' simulated as colored squares
    for i, color in enumerate([(0, 100, 200), (247, 135, 36), (0, 150, 80)]):
        draw.rectangle([(280 + i * 200, 130), (380 + i * 200, 170)], fill=color)
    # Glass panels — light blue
    for x in range(220, 1060, 180):
        draw.rectangle([(x, 230), (x + 160, 580)], fill=(170, 200, 230))
    draw.text((40, 40), "Sân FGC", fill=(50, 50, 50))
    img.save(ASSETS_DIR / "san_fgc.png")
    print(f"Wrote {ASSETS_DIR / 'san_fgc.png'}")


def gen_sao_hoa() -> None:
    """Sao Hỏa — Mars surface, red/orange terrain, dark sky with stars."""
    import numpy as np
    img = _gradient_bg_fast((30, 10, 40), (180, 80, 40))
    draw = ImageDraw.Draw(img)
    # Stars
    rng = np.random.default_rng(seed=42)
    for _ in range(80):
        sx = int(rng.integers(0, WIDTH))
        sy = int(rng.integers(0, HEIGHT // 2))
        draw.ellipse([(sx, sy), (sx + 2, sy + 2)], fill=(255, 255, 255))
    # Rocky horizon
    horizon_y = HEIGHT // 2 + 50
    for x in range(0, WIDTH, 60):
        peak = int(rng.integers(20, 80))
        draw.polygon(
            [(x, horizon_y), (x + 30, horizon_y - peak), (x + 60, horizon_y)],
            fill=(140, 60, 30),
        )
    draw.text((40, 40), "Sao Hỏa", fill=(255, 255, 255))
    img.save(ASSETS_DIR / "sao_hoa.png")
    print(f"Wrote {ASSETS_DIR / 'sao_hoa.png'}")


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    gen_san_dinh()
    gen_luy_tre()
    gen_san_fgc()
    gen_sao_hoa()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Generate the PNGs**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m neo_makervigate.experiences.exp06_photo_booth._gen_assets
```
Expected: 4 "Wrote ..." lines.

Verify:
```bash
ls -la src/neo_makervigate/experiences/exp06_photo_booth/backgrounds/
file src/neo_makervigate/experiences/exp06_photo_booth/backgrounds/*.png
```
Should report 4 PNG files (RIFF/PNG headers).

- [ ] **Step 4: Verify lint + tests**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
```
Expected: all clean.

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/experiences/exp06_photo_booth/prompts.toml \
        src/neo_makervigate/experiences/exp06_photo_booth/_gen_assets.py \
        src/neo_makervigate/experiences/exp06_photo_booth/backgrounds/
git commit -m "$(cat <<'EOF'
feat(p6): exp06 backgrounds (4 PNGs via Pillow) + prompts.toml

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: PhotoBoothExperience scaffold + meta tests

**Files:**
- Modify (rewrite): `src/neo_makervigate/experiences/exp06_photo_booth/logic.py`
- Create: `src/neo_makervigate/experiences/exp06_photo_booth/test_logic.py`

- [ ] **Step 1: Write failing tests**

Create `src/neo_makervigate/experiences/exp06_photo_booth/test_logic.py`:

```python
"""Tests cho PhotoBoothExperience — gameplay logic độc lập."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

import pytest

from neo_makervigate.core.models import Landmark, VisionFrame
from neo_makervigate.experiences.exp06_photo_booth.logic import (
    Phase,
    PhotoBoothExperience,
)


class _FakeClock:
    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def _make_empty_frame() -> VisionFrame:
    return VisionFrame(timestamp=datetime(2026, 1, 1), width=1280, height=720)


@pytest.fixture
def exp_with_clock(qapp) -> tuple[PhotoBoothExperience, _FakeClock]:
    clock = _FakeClock(0.0)
    exp = PhotoBoothExperience(clock=clock)
    exp.on_enter()
    yield exp, clock
    exp.on_exit()


def test_meta_correct() -> None:
    meta = PhotoBoothExperience.meta
    assert meta.id == "exp06_photo_booth"
    assert "hands" in meta.vision_modules
    assert "selfie" in meta.vision_modules
    assert meta.needs_qwen is True


def test_auto_capture_on_done_is_false() -> None:
    assert PhotoBoothExperience.auto_capture_on_done is False


def test_initial_phase_is_intro(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    exp, _ = exp_with_clock
    state = exp.render_state()
    assert state["phase"] == Phase.INTRO.value


def test_backgrounds_loaded_4_options(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    exp, _ = exp_with_clock
    state = exp.render_state()
    backgrounds = cast(list[dict[str, Any]], state["backgrounds"])
    assert len(backgrounds) == 4
    ids = [bg["id"] for bg in backgrounds]
    assert "san_dinh" in ids
    assert "luy_tre" in ids
    assert "san_fgc" in ids
    assert "sao_hoa" in ids


def test_prompts_toml_loaded(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    exp, _ = exp_with_clock
    # User prompt should be non-empty
    assert exp._prompts["caption"]["user_prompt"]  # type: ignore[attr-defined]
    # Fallback dict has 4 entries
    fb = exp._prompts["fallback"]  # type: ignore[attr-defined]
    assert "san_dinh" in fb
    assert "luy_tre" in fb
    assert "san_fgc" in fb
    assert "sao_hoa" in fb
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest src/neo_makervigate/experiences/exp06_photo_booth/test_logic.py -v
```
Expected: FAIL — cannot import PhotoBoothExperience or attributes missing.

- [ ] **Step 3: Rewrite logic.py with scaffold**

Replace contents of `src/neo_makervigate/experiences/exp06_photo_booth/logic.py`:

```python
"""exp06 Photo Booth Cổng Làng — gameplay đầy đủ (P6).

Flow: INTRO(2s) → SELECT (POINT cycle, auto-advance 3s)
      → STAGE (V_SIGN hold 0.5s) → COUNTDOWN(3s) → emit photo_capture_requested
      → PROCESSING (waiting_photo → waiting_qwen, max 12s, fallback nếu timeout)
      → DONE → ExperienceManager unload (auto_capture_on_done=False, plugin tự orchestrate)

Caption flow trong PROCESSING:
  photo_captured received → emit qwen_request_started(image, prompt)
  → qwen_response_ready OR qwen_failed → write caption.txt → emit photo_caption_ready
  → set phase DONE
"""

from __future__ import annotations

import time
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, ClassVar

from loguru import logger

from neo_makervigate.core.models import ExperienceMeta, PhotoResult, VisionFrame
from neo_makervigate.experiences.experience_base import BaseExperience
from neo_makervigate.utils.signal_bus import SignalBus

_QML_PATH = (Path(__file__).parent / "ui.qml").as_posix()
_PROMPTS_TOML = Path(__file__).parent / "prompts.toml"
_BACKGROUNDS_DIR = Path(__file__).parent / "backgrounds"

# Phase durations
INTRO_DURATION = 2.0
SELECT_AUTO_ADVANCE_SEC = 3.0
COUNTDOWN_DURATION = 3.0
PROCESSING_TIMEOUT = 12.0
V_SIGN_TRIGGER_HOLD = 0.5


class Phase(StrEnum):
    INTRO = "intro"
    SELECT = "select"
    STAGE = "stage"
    COUNTDOWN = "countdown"
    PROCESSING = "processing"
    DONE = "done"


@dataclass
class BackgroundOption:
    id: str
    title: str
    emoji: str
    path: Path
    fallback_caption: str


def _load_prompts() -> dict[str, Any]:
    with open(_PROMPTS_TOML, "rb") as f:
        return tomllib.load(f)


def _load_backgrounds(prompts: dict[str, Any]) -> list[BackgroundOption]:
    fallback = prompts.get("fallback", {})
    defs = [
        ("san_dinh", "Sân Đình", "🏛️"),
        ("luy_tre", "Lũy Tre", "🎍"),
        ("san_fgc", "Sân FGC", "🎮"),
        ("sao_hoa", "Sao Hỏa", "🚀"),
    ]
    return [
        BackgroundOption(
            id=bg_id,
            title=title,
            emoji=emoji,
            path=_BACKGROUNDS_DIR / f"{bg_id}.png",
            fallback_caption=fallback.get(bg_id, f"{emoji} Ảnh em chụp tại {title}!"),
        )
        for bg_id, title, emoji in defs
    ]


class PhotoBoothExperience(BaseExperience):
    """Photo Booth Cổng Làng — chọn nền, làm V, chụp, AI caption."""

    auto_capture_on_done: ClassVar[bool] = False  # plugin self-orchestrates

    meta = ExperienceMeta(
        id="exp06_photo_booth",
        title="Photo Booth Cổng Làng",
        subtitle="Chụp ảnh + caption AI",
        age_min=5,
        age_max=12,
        vision_modules=("hands", "selfie"),
        needs_qwen=True,
        needs_voice=False,
        needs_internet=False,
        icon_path="",
        dev_days=7,
    )

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        super().__init__()
        self._clock: Callable[[], float] = clock or time.perf_counter
        self._prompts: dict[str, Any] = _load_prompts()
        self._backgrounds: list[BackgroundOption] = _load_backgrounds(self._prompts)
        self._phase: Phase = Phase.INTRO
        self._phase_started_at: float = 0.0
        self._selected_bg_index: int = 0
        self._select_last_change_at: float = 0.0
        self._countdown_remaining: float = 0.0
        self._v_sign_holding_since: float | None = None
        self._photo_id: str = ""
        self._photo_dir: Path | None = None
        self._composite_path: Path | None = None
        self._caption: str = ""
        self._caption_from_qwen: bool = False
        self._processing_status: str = ""
        self._processing_started_at: float = 0.0

    def get_qml_path(self) -> str:
        return _QML_PATH

    def on_enter(self) -> None:
        now = self._clock()
        self._phase = Phase.INTRO
        self._phase_started_at = now
        self._select_last_change_at = now
        self._selected_bg_index = 0
        self._countdown_remaining = 0.0
        self._v_sign_holding_since = None
        self._photo_id = ""
        self._photo_dir = None
        self._composite_path = None
        self._caption = ""
        self._caption_from_qwen = False
        self._processing_status = ""

        # Wire signals
        bus = SignalBus.instance()
        bus.photo_captured.connect(self._on_photo_captured)
        bus.qwen_response_ready.connect(self._on_qwen_response)
        bus.qwen_failed.connect(self._on_qwen_failed)
        logger.info(f"PhotoBooth: on_enter ({len(self._backgrounds)} backgrounds)")

    def on_exit(self) -> None:
        bus = SignalBus.instance()
        for sig, slot in [
            (bus.photo_captured, self._on_photo_captured),
            (bus.qwen_response_ready, self._on_qwen_response),
            (bus.qwen_failed, self._on_qwen_failed),
        ]:
            try:
                sig.disconnect(slot)
            except (TypeError, RuntimeError):
                pass

    def on_vision_frame(self, frame: VisionFrame) -> None:
        now = self._clock()
        self._step_phase(now)

    def on_gesture(self, gesture: str) -> None:
        now = self._clock()
        if gesture == "V_SIGN" and self._phase == Phase.STAGE:
            if self._v_sign_holding_since is None:
                self._v_sign_holding_since = now
            elif now - self._v_sign_holding_since >= V_SIGN_TRIGGER_HOLD:
                self._enter_countdown(now)
        # POINT cycling — handled later

    def render_state(self) -> dict[str, object]:
        now = self._clock()
        v_sign_progress = 0.0
        if self._v_sign_holding_since is not None:
            v_sign_progress = min(1.0, (now - self._v_sign_holding_since) / V_SIGN_TRIGGER_HOLD)
        return {
            "phase": self._phase.value,
            "elapsed_in_phase": now - self._phase_started_at,
            "backgrounds": [
                {"id": bg.id, "title": bg.title, "emoji": bg.emoji, "path": str(bg.path)}
                for bg in self._backgrounds
            ],
            "selected_bg_index": self._selected_bg_index,
            "v_sign_progress": v_sign_progress,
            "countdown_remaining": self._countdown_remaining,
            "processing_status": self._processing_status,
            "caption": self._caption,
            "qwen_unavailable": False,  # will be set in T14 if needed
        }

    def completion_summary(self) -> dict[str, Any]:
        bg = self._backgrounds[self._selected_bg_index]
        return {
            "completed": True,
            "background_id": bg.id,
            "caption": self._caption,
            "qwen_used": self._caption_from_qwen,
        }

    # --- Internal ---

    def _step_phase(self, now: float) -> None:
        elapsed = now - self._phase_started_at
        if self._phase == Phase.INTRO and elapsed >= INTRO_DURATION:
            self._phase = Phase.SELECT
            self._phase_started_at = now
            self._select_last_change_at = now

    def _enter_countdown(self, now: float) -> None:
        self._phase = Phase.COUNTDOWN
        self._phase_started_at = now
        self._countdown_remaining = COUNTDOWN_DURATION
        self._v_sign_holding_since = None

    # Placeholders — flesh out in T12-T14
    def _on_photo_captured(self, result: PhotoResult) -> None:
        pass

    def _on_qwen_response(self, text: str) -> None:
        pass

    def _on_qwen_failed(self, error: str) -> None:
        pass


EXPERIENCE = PhotoBoothExperience
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass (5 new exp06 tests + prior).

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/experiences/exp06_photo_booth/logic.py src/neo_makervigate/experiences/exp06_photo_booth/test_logic.py
git commit -m "$(cat <<'EOF'
feat(p6): PhotoBoothExperience scaffold + meta/baseline tests

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Phase transitions + POINT cycling + auto-advance

**Files:**
- Modify: `src/neo_makervigate/experiences/exp06_photo_booth/logic.py`
- Modify: `src/neo_makervigate/experiences/exp06_photo_booth/test_logic.py`

- [ ] **Step 1: Append failing tests**

Append to `test_logic.py`:

```python
def test_intro_transitions_to_select_after_2s(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())
    assert exp.render_state()["phase"] == Phase.SELECT.value


def test_point_gesture_cycles_selection(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → SELECT
    initial = cast(int, exp.render_state()["selected_bg_index"])
    exp.on_gesture("POINT")
    new = cast(int, exp.render_state()["selected_bg_index"])
    assert new == (initial + 1) % 4


def test_select_auto_advances_to_stage_after_stable_3s(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → SELECT
    # No POINT for 3.1s → auto-advance to STAGE
    clock.advance(3.1)
    exp.on_vision_frame(_make_empty_frame())
    assert exp.render_state()["phase"] == Phase.STAGE.value


def test_point_resets_select_auto_advance_timer(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → SELECT
    clock.advance(2.0)
    exp.on_gesture("POINT")  # reset stability timer
    clock.advance(2.0)
    exp.on_vision_frame(_make_empty_frame())
    # Total 4s but only 2s since last POINT — still in SELECT
    assert exp.render_state()["phase"] == Phase.SELECT.value
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest src/neo_makervigate/experiences/exp06_photo_booth/test_logic.py -v
```
Expected: POINT cycling + auto-advance tests FAIL.

- [ ] **Step 3: Implement POINT cycling + auto-advance**

In `src/neo_makervigate/experiences/exp06_photo_booth/logic.py`:

Update `on_gesture` to handle POINT:

```python
    def on_gesture(self, gesture: str) -> None:
        now = self._clock()
        if gesture == "POINT" and self._phase == Phase.SELECT:
            self._selected_bg_index = (self._selected_bg_index + 1) % len(self._backgrounds)
            self._select_last_change_at = now
            return
        if gesture == "V_SIGN" and self._phase == Phase.STAGE:
            if self._v_sign_holding_since is None:
                self._v_sign_holding_since = now
            elif now - self._v_sign_holding_since >= V_SIGN_TRIGGER_HOLD:
                self._enter_countdown(now)
```

Update `_step_phase` to auto-advance from SELECT after stable selection:

```python
    def _step_phase(self, now: float) -> None:
        elapsed = now - self._phase_started_at
        if self._phase == Phase.INTRO and elapsed >= INTRO_DURATION:
            self._phase = Phase.SELECT
            self._phase_started_at = now
            self._select_last_change_at = now
        elif self._phase == Phase.SELECT:
            since_change = now - self._select_last_change_at
            if since_change >= SELECT_AUTO_ADVANCE_SEC:
                self._phase = Phase.STAGE
                self._phase_started_at = now
```

Note: GestureDetector doesn't currently emit POINT — but ExperienceManager routes any `gesture_detected("POINT")` to plugin. For tests, we call `on_gesture("POINT")` directly. Production: POINT detection can be added later or use V_SIGN-only flow (skip select via tap or auto-pick).

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/experiences/exp06_photo_booth/logic.py src/neo_makervigate/experiences/exp06_photo_booth/test_logic.py
git commit -m "$(cat <<'EOF'
feat(p6): exp06 SELECT phase POINT cycling + auto-advance 3s

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: V_SIGN hold → COUNTDOWN → emit photo_capture_requested

**Files:**
- Modify: `src/neo_makervigate/experiences/exp06_photo_booth/logic.py`
- Modify: `src/neo_makervigate/experiences/exp06_photo_booth/test_logic.py`

- [ ] **Step 1: Append failing tests**

Append to `test_logic.py`:

```python
def test_v_sign_in_stage_triggers_countdown_after_hold(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    # Get to STAGE
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → SELECT
    clock.advance(3.1)
    exp.on_vision_frame(_make_empty_frame())  # → STAGE
    # First V_SIGN — starts holding
    exp.on_gesture("V_SIGN")
    assert exp.render_state()["phase"] == Phase.STAGE.value
    # After hold duration
    clock.advance(0.6)
    exp.on_gesture("V_SIGN")
    assert exp.render_state()["phase"] == Phase.COUNTDOWN.value


def test_countdown_advances_3_to_0_then_emits_capture(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    from neo_makervigate.utils.signal_bus import SignalBus
    exp, clock = exp_with_clock
    # Get to COUNTDOWN
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # SELECT
    clock.advance(3.1)
    exp.on_vision_frame(_make_empty_frame())  # STAGE
    exp.on_gesture("V_SIGN")
    clock.advance(0.6)
    exp.on_gesture("V_SIGN")  # → COUNTDOWN

    requests: list[dict] = []
    SignalBus.instance().photo_capture_requested.connect(lambda p: requests.append(p))

    # Tick frames during countdown
    clock.advance(1.0)
    exp.on_vision_frame(_make_empty_frame())
    state = exp.render_state()
    assert state["phase"] == Phase.COUNTDOWN.value
    rem = cast(float, state["countdown_remaining"])
    assert 1.5 < rem < 2.5  # ~2s remaining

    # End of countdown
    clock.advance(2.5)
    exp.on_vision_frame(_make_empty_frame())
    state = exp.render_state()
    assert state["phase"] == Phase.PROCESSING.value
    # photo_capture_requested emitted with background_path
    assert len(requests) == 1
    params = requests[0]
    assert params["experience_id"] == "exp06_photo_booth"
    assert "background_path" in params
```

- [ ] **Step 2: Run tests**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest src/neo_makervigate/experiences/exp06_photo_booth/test_logic.py -v
```
Expected: V_SIGN hold test passes (already implemented in T11); COUNTDOWN test FAILs.

- [ ] **Step 3: Implement COUNTDOWN tick + emit at end**

In `_step_phase` in logic.py, add COUNTDOWN handling:

```python
    def _step_phase(self, now: float) -> None:
        elapsed = now - self._phase_started_at
        if self._phase == Phase.INTRO and elapsed >= INTRO_DURATION:
            self._phase = Phase.SELECT
            self._phase_started_at = now
            self._select_last_change_at = now
        elif self._phase == Phase.SELECT:
            since_change = now - self._select_last_change_at
            if since_change >= SELECT_AUTO_ADVANCE_SEC:
                self._phase = Phase.STAGE
                self._phase_started_at = now
        elif self._phase == Phase.COUNTDOWN:
            self._countdown_remaining = max(0.0, COUNTDOWN_DURATION - elapsed)
            if elapsed >= COUNTDOWN_DURATION:
                self._enter_processing(now)
        elif self._phase == Phase.PROCESSING:
            if (now - self._processing_started_at) >= PROCESSING_TIMEOUT:
                self._fallback_caption()
```

Add `_enter_processing`:

```python
    def _enter_processing(self, now: float) -> None:
        self._phase = Phase.PROCESSING
        self._phase_started_at = now
        self._processing_started_at = now
        self._processing_status = "waiting_photo"
        bg = self._backgrounds[self._selected_bg_index]
        SignalBus.instance().photo_capture_requested.emit({
            "experience_id": self.meta.id,
            "background_path": str(bg.path),
        })
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/experiences/exp06_photo_booth/logic.py src/neo_makervigate/experiences/exp06_photo_booth/test_logic.py
git commit -m "$(cat <<'EOF'
feat(p6): exp06 COUNTDOWN → PROCESSING + emit photo_capture_requested

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: photo_captured → qwen → caption → DONE

**Files:**
- Modify: `src/neo_makervigate/experiences/exp06_photo_booth/logic.py`
- Modify: `src/neo_makervigate/experiences/exp06_photo_booth/test_logic.py`

- [ ] **Step 1: Append failing tests**

Append to `test_logic.py`:

```python
def test_photo_captured_triggers_qwen_request(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    from pathlib import Path
    from neo_makervigate.core.models import PhotoResult
    from neo_makervigate.utils.signal_bus import SignalBus

    exp, clock = exp_with_clock
    # Skip to PROCESSING
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # SELECT
    clock.advance(3.1)
    exp.on_vision_frame(_make_empty_frame())  # STAGE
    exp.on_gesture("V_SIGN")
    clock.advance(0.6)
    exp.on_gesture("V_SIGN")  # COUNTDOWN
    clock.advance(3.1)
    exp.on_vision_frame(_make_empty_frame())  # PROCESSING

    qwen_requests: list[dict] = []
    SignalBus.instance().qwen_request_started.connect(lambda p: qwen_requests.append(p))

    # Simulate photo_captured
    result = PhotoResult(
        success=True,
        photo_id="photo_test",
        original_path=Path("/tmp/orig.jpg"),
        composite_path=Path("/tmp/comp.jpg"),
        qr_path=Path("/tmp/qr.png"),
        download_url="http://x/composite.jpg",
        experience_id="exp06_photo_booth",
    )
    SignalBus.instance().photo_captured.emit(result)
    qapp_proc = pytest.importorskip("PyQt6.QtCore").QCoreApplication.instance()
    if qapp_proc:
        qapp_proc.processEvents()

    assert len(qwen_requests) == 1
    assert "image_path" in qwen_requests[0]


def test_qwen_response_sets_caption_and_advances_to_done(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    from pathlib import Path
    import tempfile
    from neo_makervigate.core.models import PhotoResult
    from neo_makervigate.utils.signal_bus import SignalBus

    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())
    clock.advance(3.1)
    exp.on_vision_frame(_make_empty_frame())
    exp.on_gesture("V_SIGN")
    clock.advance(0.6)
    exp.on_gesture("V_SIGN")
    clock.advance(3.1)
    exp.on_vision_frame(_make_empty_frame())  # PROCESSING

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        result = PhotoResult(
            success=True,
            photo_id="photo_test",
            original_path=tdp / "orig.jpg",
            composite_path=tdp / "comp.jpg",
            qr_path=tdp / "qr.png",
            download_url="http://x",
            experience_id="exp06_photo_booth",
        )
        (tdp / "orig.jpg").write_bytes(b"\xff\xd8\xff")
        SignalBus.instance().photo_captured.emit(result)
        SignalBus.instance().qwen_response_ready.emit("Em vẫy chào! 👋")
        state = exp.render_state()
        assert state["caption"] == "Em vẫy chào! 👋"
        assert state["phase"] == Phase.DONE.value
        # caption.txt should be written
        assert (tdp / "caption.txt").exists()


def test_qwen_failure_uses_fallback_caption(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    from pathlib import Path
    import tempfile
    from neo_makervigate.core.models import PhotoResult
    from neo_makervigate.utils.signal_bus import SignalBus

    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())
    clock.advance(3.1)
    exp.on_vision_frame(_make_empty_frame())
    exp.on_gesture("V_SIGN")
    clock.advance(0.6)
    exp.on_gesture("V_SIGN")
    clock.advance(3.1)
    exp.on_vision_frame(_make_empty_frame())

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        result = PhotoResult(
            success=True,
            photo_id="photo_test",
            original_path=tdp / "orig.jpg",
            composite_path=None,
            qr_path=tdp / "qr.png",
            download_url="http://x",
            experience_id="exp06_photo_booth",
        )
        (tdp / "orig.jpg").write_bytes(b"\xff\xd8\xff")
        SignalBus.instance().photo_captured.emit(result)
        SignalBus.instance().qwen_failed.emit("model crash")
        state = exp.render_state()
        # Should be fallback caption for default selected (san_dinh)
        assert "Sân Đình" in state["caption"] or "🏛️" in state["caption"]
        assert state["phase"] == Phase.DONE.value


def test_processing_timeout_uses_fallback(
    exp_with_clock: tuple[PhotoBoothExperience, _FakeClock],
) -> None:
    """If PROCESSING > 12s without qwen response, fallback caption."""
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())
    clock.advance(3.1)
    exp.on_vision_frame(_make_empty_frame())
    exp.on_gesture("V_SIGN")
    clock.advance(0.6)
    exp.on_gesture("V_SIGN")
    clock.advance(3.1)
    exp.on_vision_frame(_make_empty_frame())
    assert exp.render_state()["phase"] == Phase.PROCESSING.value
    clock.advance(13.0)
    exp.on_vision_frame(_make_empty_frame())
    state = exp.render_state()
    assert state["phase"] == Phase.DONE.value
    assert state["caption"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest src/neo_makervigate/experiences/exp06_photo_booth/test_logic.py -v
```
Expected: 4 new tests FAIL.

- [ ] **Step 3: Implement signal handlers + fallback in logic.py**

Replace the placeholder `_on_photo_captured`, `_on_qwen_response`, `_on_qwen_failed`:

```python
    def _on_photo_captured(self, result: PhotoResult) -> None:
        if self._phase != Phase.PROCESSING:
            return
        if result.experience_id != self.meta.id:
            return
        if not result.success:
            self._fallback_caption()
            return
        self._photo_id = result.photo_id
        self._photo_dir = result.original_path.parent if result.original_path else None
        self._composite_path = result.composite_path
        self._processing_status = "waiting_qwen"
        target = result.composite_path or result.original_path
        if target is None:
            self._fallback_caption()
            return
        SignalBus.instance().qwen_request_started.emit({
            "image_path": str(target),
            "prompt": self._prompts["caption"]["user_prompt"],
            "max_tokens": 80,
        })

    def _on_qwen_response(self, text: str) -> None:
        if self._phase != Phase.PROCESSING:
            return
        cleaned = text.strip()
        if len(cleaned) < 5:
            self._fallback_caption()
            return
        self._caption = cleaned
        self._caption_from_qwen = True
        self._save_caption_and_finish()

    def _on_qwen_failed(self, error: str) -> None:
        if self._phase != Phase.PROCESSING:
            return
        logger.warning(f"Qwen failed in exp06: {error}")
        self._fallback_caption()

    def _fallback_caption(self) -> None:
        bg = self._backgrounds[self._selected_bg_index]
        self._caption = bg.fallback_caption
        self._caption_from_qwen = False
        self._save_caption_and_finish()

    def _save_caption_and_finish(self) -> None:
        if self._photo_dir:
            try:
                (self._photo_dir / "caption.txt").write_text(self._caption, encoding="utf-8")
            except OSError as e:
                logger.warning(f"caption.txt write failed: {e}")
        # Notify AppController to refresh photoResult.caption
        if self._photo_id:
            SignalBus.instance().photo_caption_ready.emit(self._photo_id, self._caption)
        self._processing_status = "done"
        self._phase = Phase.DONE
        self._phase_started_at = self._clock()
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/experiences/exp06_photo_booth/logic.py src/neo_makervigate/experiences/exp06_photo_booth/test_logic.py
git commit -m "$(cat <<'EOF'
feat(p6): exp06 photo_captured → qwen → caption → DONE flow

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: app.py wire QwenLocalBackend + QwenService

**Files:**
- Modify: `src/neo_makervigate/app.py`

- [ ] **Step 1: Modify app.py**

Read current `app.py`. Add imports near other neo_makervigate imports:

```python
from neo_makervigate.core.qwen_client import QwenLocalBackend
from neo_makervigate.services.qwen_service import QwenService
```

In `run()`, after PhotoService instantiation, add:

```python
    # P6: Qwen LLM (local) — for exp06 Photo Booth caption
    qwen_backend = QwenLocalBackend()
    if qwen_backend.is_ready():
        qwen_service = QwenService(client=qwen_backend)
        _ = qwen_service  # keep ref
    else:
        logger.warning(
            "Qwen model not found. exp06 will use template captions. "
            "Install: python -m neo_makervigate.scripts.download_qwen"
        )
        qwen_service = None
```

In shutdown sequence, after `share_server.stop()`:

```python
    if qwen_service is not None:
        logger.info("Shutting down: stopping QwenService")
        qwen_service.stop()
```

Need conditional import — if `qwen_service` is `None`, can't call methods. The `if qwen_service is not None:` guard handles this.

- [ ] **Step 2: Verify tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/app.py
git commit -m "$(cat <<'EOF'
feat(p6): wire QwenLocalBackend + QwenService at app boot

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 16: ui.qml + PhotoReviewPage caption

**Files:**
- Modify (rewrite): `src/neo_makervigate/experiences/exp06_photo_booth/ui.qml`
- Modify: `src/neo_makervigate/ui/qml/pages/PhotoReviewPage.qml`

- [ ] **Step 1: Rewrite exp06 ui.qml**

Replace contents of `src/neo_makervigate/experiences/exp06_photo_booth/ui.qml`:

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../ui/qml/singletons" as Sing

Item {
    id: root
    anchors.fill: parent

    readonly property var state: app.experienceState
    readonly property string phase: state && state.phase ? state.phase : "intro"
    readonly property var backgrounds: state && state.backgrounds ? state.backgrounds : []
    readonly property int selectedIdx: state && state.selected_bg_index !== undefined ? state.selected_bg_index : 0
    readonly property real vSignProgress: state && state.v_sign_progress !== undefined ? state.v_sign_progress : 0.0
    readonly property real countdownRemaining: state && state.countdown_remaining !== undefined ? state.countdown_remaining : 0.0
    readonly property string processingStatus: state && state.processing_status ? state.processing_status : ""
    readonly property string caption: state && state.caption ? state.caption : ""

    // Camera mirror background
    Image {
        id: cameraView
        anchors.fill: parent
        cache: false
        fillMode: Image.PreserveAspectCrop
        source: "image://camera/latest"
        transform: Scale { xScale: -1; origin.x: cameraView.width / 2 }
        property int tick: 0
        Timer {
            interval: 33
            running: true
            repeat: true
            onTriggered: {
                cameraView.tick++
                cameraView.source = "image://camera/latest?t=" + cameraView.tick
            }
        }
    }

    Rectangle { anchors.fill: parent; color: "#20000000" }

    // Background ghost overlay during STAGE
    Image {
        visible: root.phase === "stage" && root.backgrounds.length > 0
        anchors.fill: parent
        opacity: 0.3
        fillMode: Image.PreserveAspectCrop
        source: root.backgrounds.length > 0 ? "file://" + root.backgrounds[root.selectedIdx].path : ""
        cache: false
    }

    // INTRO overlay
    Rectangle {
        visible: root.phase === "intro"
        anchors.fill: parent
        color: "#A0000000"
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 24
            Text {
                text: "📸 Chào mừng đến Photo Booth!"
                color: "white"
                font.pixelSize: 56
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Chọn cảnh em thích, làm chữ V để chụp."
                color: "#FAF6EE"
                font.pixelSize: 28
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    // SELECT — thumbnails bottom row
    Rectangle {
        visible: root.phase === "select"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 200
        color: "#C0000000"
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 8
            Text {
                text: "Chỉ tay (POINT) để đổi cảnh — tự chọn sau 3 giây"
                color: "white"
                font.pixelSize: 18
                Layout.alignment: Qt.AlignHCenter
            }
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 16
                Repeater {
                    model: root.backgrounds
                    Rectangle {
                        Layout.preferredWidth: 200
                        Layout.preferredHeight: 130
                        radius: 12
                        color: "white"
                        border.color: index === root.selectedIdx ? Sing.NeoConstants.de : "transparent"
                        border.width: index === root.selectedIdx ? 6 : 0
                        Image {
                            anchors.fill: parent
                            anchors.margins: 4
                            source: "file://" + modelData.path
                            fillMode: Image.PreserveAspectCrop
                            cache: false
                        }
                        Text {
                            anchors.bottom: parent.bottom
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.emoji + " " + modelData.title
                            color: "white"
                            font.pixelSize: 14
                            font.bold: true
                            style: Text.Outline
                            styleColor: "black"
                        }
                    }
                }
            }
        }
    }

    // STAGE — V_SIGN prompt + hold bar
    Rectangle {
        visible: root.phase === "stage"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 120
        color: "#A0000000"
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 12
            Text {
                text: "✌️ Làm chữ V để chụp!"
                color: "white"
                font.pixelSize: 32
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            // Hold progress
            Rectangle {
                Layout.preferredWidth: 400
                Layout.preferredHeight: 20
                radius: 10
                color: "#FF1F3018"
                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.margins: 3
                    width: root.vSignProgress * (parent.width - 6)
                    radius: 8
                    color: Sing.NeoConstants.tre
                }
            }
        }
    }

    // COUNTDOWN — giant number
    Text {
        visible: root.phase === "countdown"
        anchors.centerIn: parent
        text: {
            const r = Math.ceil(root.countdownRemaining)
            if (r <= 0) return "📸"
            return String(r)
        }
        color: "white"
        font.pixelSize: 200
        font.bold: true
        style: Text.Outline
        styleColor: "black"
    }

    // PROCESSING — spinner + status
    Rectangle {
        visible: root.phase === "processing"
        anchors.fill: parent
        color: "#C0000000"
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 24
            BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                running: true
            }
            Text {
                text: "Đang chụp + viết caption..."
                color: "white"
                font.pixelSize: 32
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: root.processingStatus
                color: "#FAF6EE"
                font.pixelSize: 20
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
}
```

- [ ] **Step 2: Modify PhotoReviewPage.qml to show caption**

Read `src/neo_makervigate/ui/qml/pages/PhotoReviewPage.qml`. Add caption property:

```qml
    readonly property string caption: result && result.caption ? result.caption : ""
```

In the right column ColumnLayout, add a Text element for caption (place between QR Rectangle and downloadUrl Text):

```qml
            Text {
                visible: page.caption.length > 0
                text: page.caption
                font.pixelSize: 22
                font.bold: true
                color: Sing.NeoConstants.de
                font.italic: true
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
            }
```

- [ ] **Step 3: Verify tests still pass**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add src/neo_makervigate/experiences/exp06_photo_booth/ui.qml \
        src/neo_makervigate/ui/qml/pages/PhotoReviewPage.qml
git commit -m "$(cat <<'EOF'
feat(p6): exp06 ui.qml all phases + PhotoReviewPage caption display

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 17: Final verify + smoke test + PHASES.md done

- [ ] **Step 1: Full test + lint sweep**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all green. Total ~140 tests (106 P5 + ~30 P6).

- [ ] **Step 2: Manual smoke test (webcam + Qwen optional)**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m neo_makervigate
```

Verify in logs:
1. ShareServer listening on port 8000
2. If Qwen model present: no warning; if missing: "Qwen model not found. exp06 will use template captions"
3. Hub → click "Photo Booth Cổng Làng"
4. INTRO 2s → SELECT (4 thumbnails)
5. (Optional) Make POINT gesture → cycle thumbnails; or wait 3s → STAGE
6. STAGE: V_SIGN (giữ 0.5s) → COUNTDOWN 3→2→1→📸
7. PROCESSING: spinner ~6s (or instant fallback if Qwen unavailable)
8. PhotoReviewPage: composite ảnh ghép nền + caption Vietnamese + QR
9. iPhone Zalo scan QR → ảnh tải về với caption embedded? No, caption only in UI — photo download is just the image

- [ ] **Step 3: Update PHASES.md**

In `DOC/PHASES.md`, find P6 section and update:

Replace:
```markdown
## P6 — Qwen + exp06 Photo Booth (tuần 7)
```

With:
```markdown
## P6 — Qwen + exp06 Photo Booth (tuần 7) ✅ DONE

**Achievement (2026-05-17):** Flagship MVP experience. V_SIGN gesture (pose-based detection trong GestureDetector), Selfie Seg enable trong VisionEngine + VisionFrame.selfie_mask field, PhotoCapture.save_composite (soft mask Gaussian blur), QwenLocalBackend (llama-cpp-python + Qwen 2.5-VL-2B GGUF Q4_K_M lazy load, fallback nếu model missing), QwenService QThread wrapper, PhotoBoothExperience full game (INTRO → SELECT POINT cycle + auto-advance 3s → STAGE V_SIGN hold 0.5s → COUNTDOWN 3s → PROCESSING + Qwen caption với timeout 12s fallback template → DONE), BaseExperience.auto_capture_on_done attr + ExperienceManager check (exp06 self-orchestrates capture), photo_caption_ready signal → AppController updates photoResult, PhotoReviewPage caption display, 4 procedural backgrounds (Sân Đình/Lũy Tre/Sân FGC/Sao Hỏa). 17 tasks TDD. ~30 P6 tests, ruff/mypy strict clean.
```

Mark task checkmarks similarly.

- [ ] **Step 4: Commit**

```bash
git add DOC/PHASES.md
git commit -m "$(cat <<'EOF'
docs(p6): mark Phase 6 done in PHASES.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 5: Update auto-memory project status**

Edit `/Users/tuanln/.claude/projects/-Users-tuanln/memory/project_neomakervigate_status.md`. Find:

```markdown
- **P6 Qwen + exp06 Photo Booth**: Qwen 3.5 caption + Selfie Seg composite + exp06 game
```

Replace with detailed achievement line including head commit SHA. Add P7 placeholder line.

(Memory không track git — không commit.)

---

## Self-Review Summary

**Spec coverage:**
- §0 Pre-flight Spike S2 → User manual; assumed pass for plan execution. Risk noted.
- §1 Architecture → Tasks 1-9, 15.
- §2 V_SIGN + Selfie + composite → Tasks 1, 2, 3, 4.
- §3 Qwen → Tasks 5, 6, 7.
- §4 exp06 + UI → Tasks 8, 9, 10, 11, 12, 13, 14, 16.
- §5 File layout + testing → All tasks distribute these.

**Placeholders:** None.

**Type consistency:**
- `Phase` enum values consistent across tasks 11-14 + ui.qml.
- `BackgroundOption` dataclass fields consistent.
- `auto_capture_on_done: ClassVar[bool]` consistent on BaseExperience (T8) + override on PhotoBoothExperience (T11).
- Signal `photo_caption_ready(str, str)` consistent in signal_bus.py (T9), emitted in exp06 logic (T14), handled in AppController (T9).

**Plan ends with:** Working exp06 Photo Booth + Qwen integration (if model installed) or template fallback.
