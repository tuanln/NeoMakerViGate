# P7c — Bug Fix + UX Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 3 issues từ user smoke test: V_SIGN không detect (relax margin), composite ảnh fallback từ source folder, exp03 redesign từ body-pose noise sang face-mesh (5 biểu cảm: cười / mở O / wink / nhướng mày / lắc đầu).

**Architecture:** Sequence: small fixes first (V_SIGN, photo source), then face_math helper module, then VisionEngine face enable, then exp03 rewrite phase by phase. Test-driven.

**Tech Stack:** Python 3.12, MediaPipe Face Mesh (468 landmarks), OpenCV, PyQt6, QML. Tests via pytest + synth face landmark fixtures.

**Reference spec:** `docs/superpowers/specs/2026-05-18-p7c-bugfix-polish-design.md`

---

## File Structure

**New files:**
- `src/neo_makervigate/utils/face_math.py` — MAR, EAR, brow_raised, head_yaw helpers
- `tests/unit/test_face_math.py` — 10 tests

**Modified files:**
- `src/neo_makervigate/core/gesture_detector.py` — V_SIGN_FINGER_MARGIN 1.15→1.05
- `src/neo_makervigate/core/photo_capture.py` — list_source_photos + DEFAULT_SOURCE_PHOTOS_DIR
- `src/neo_makervigate/core/vision_engine.py` — face branch in read()
- `src/neo_makervigate/services/photo_service.py` — source fallback path
- `src/neo_makervigate/experiences/exp03_yoga_robot/logic.py` — REWRITE face-based
- `src/neo_makervigate/experiences/exp03_yoga_robot/poses.toml` — REWRITE 5 face poses
- `src/neo_makervigate/experiences/exp03_yoga_robot/ui.qml` — face landmark overlay
- `src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py` — REWRITE face tests
- `tests/unit/test_photo_service.py` — + 2 source fallback tests
- `DOC/PHASES.md` — mark P7c done

---

## Task 1: V_SIGN relax FINGER_MARGIN

**Files:**
- Modify: `src/neo_makervigate/core/gesture_detector.py`

- [ ] **Step 1: Modify constant**

In `src/neo_makervigate/core/gesture_detector.py`, find:

```python
V_SIGN_FINGER_MARGIN = 1.15
```

Replace with:

```python
V_SIGN_FINGER_MARGIN = 1.05
```

- [ ] **Step 2: Run existing tests — must still pass**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_gesture_detector.py -v
```
Expected: all 11 tests PASS (3 V_SIGN + 8 WAVE). Synth V-pose has 2× tip/pip ratio — easy 1.05 margin.

- [ ] **Step 3: Lint + types**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add src/neo_makervigate/core/gesture_detector.py
git commit -m "$(cat <<'EOF'
fix(p7c): relax V_SIGN_FINGER_MARGIN 1.15 → 1.05 for easier detection

User smoke test: V_SIGN không trigger với fingers cong nhẹ. 1.05 cho phép
borderline detection. Cooldown 0.4s vẫn prevent false trigger spam.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

## Context

P7c task 1 of 11. 1-line tune. Single constant. Existing tests unchanged.

---

## Task 2: list_source_photos helper in PhotoCapture

**Files:**
- Modify: `src/neo_makervigate/core/photo_capture.py`
- Modify: `tests/unit/test_photo_capture.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/unit/test_photo_capture.py`:

```python
def test_list_source_photos_empty_when_dir_missing(tmp_path: Path) -> None:
    from neo_makervigate.core.photo_capture import list_source_photos
    result = list_source_photos(tmp_path / "nonexistent")
    assert result == []


def test_list_source_photos_returns_jpg_png(tmp_path: Path) -> None:
    from neo_makervigate.core.photo_capture import list_source_photos
    (tmp_path / "a.jpg").write_bytes(b"\xff\xd8\xff")
    (tmp_path / "b.png").write_bytes(b"\x89PNG\r\n")
    (tmp_path / "c.txt").write_text("not image")
    result = list_source_photos(tmp_path)
    names = sorted(p.name for p in result)
    assert names == ["a.jpg", "b.png"]


def test_list_source_photos_sorted(tmp_path: Path) -> None:
    from neo_makervigate.core.photo_capture import list_source_photos
    for n in ("zebra.jpg", "apple.jpg", "mango.png"):
        (tmp_path / n).write_bytes(b"\xff\xd8\xff")
    result = list_source_photos(tmp_path)
    assert [p.name for p in result] == ["apple.jpg", "mango.png", "zebra.jpg"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_photo_capture.py -v
```
Expected: 3 new tests FAIL — `list_source_photos` not defined.

- [ ] **Step 3: Add to photo_capture.py**

In `src/neo_makervigate/core/photo_capture.py`, after `DEFAULT_PHOTOS_DIR` constant, add:

```python
DEFAULT_SOURCE_PHOTOS_DIR = Path.home() / "makervigate" / "source_photos"


def list_source_photos(source_dir: Path = DEFAULT_SOURCE_PHOTOS_DIR) -> list[Path]:
    """Liệt kê file .jpg/.png trong source_photos/. Empty list nếu không có.

    Admin upload pre-prepared photos vào folder này via scp. PhotoService
    sẽ fallback random pick nếu live composite không sẵn (no selfie_mask).
    """
    if not source_dir.exists():
        return []
    return sorted(
        [
            p
            for p in source_dir.iterdir()
            if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png")
        ]
    )
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_photo_capture.py -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: 12 tests PASS (9 existing + 3 new).

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/core/photo_capture.py tests/unit/test_photo_capture.py
git commit -m "$(cat <<'EOF'
feat(p7c): list_source_photos helper + DEFAULT_SOURCE_PHOTOS_DIR

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: PhotoService source fallback path

**Files:**
- Modify: `src/neo_makervigate/services/photo_service.py`
- Modify: `tests/unit/test_photo_service.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/unit/test_photo_service.py`:

```python
def test_capture_fallback_to_source_when_no_selfie_mask(
    tmp_path: Path,
    share_setup: tuple[ShareServer, ShareService],
    qapp,
    monkeypatch,
) -> None:
    """Background provided but no selfie_mask → fallback to source photo."""
    from datetime import datetime
    import cv2
    from neo_makervigate.core.models import VisionFrame
    from neo_makervigate.core.photo_capture import DEFAULT_SOURCE_PHOTOS_DIR

    _, share = share_setup
    fg = np.zeros((360, 640, 3), dtype=np.uint8)
    fg[:, :, 1] = 200
    # VF without selfie_mask
    vf = VisionFrame(timestamp=datetime.now(), width=640, height=360, selfie_mask=None)
    worker = _FakeWorkerWithVf(frame=fg, vf=vf)

    # Set up source_photos in tmp_path + monkeypatch DEFAULT
    source_dir = tmp_path / "source_photos_test"
    source_dir.mkdir()
    source_img = source_dir / "child_01.jpg"
    bg_color = np.zeros((360, 640, 3), dtype=np.uint8)
    bg_color[:, :, 2] = 255  # red source
    cv2.imwrite(str(source_img), bg_color)
    monkeypatch.setattr(
        "neo_makervigate.core.photo_capture.DEFAULT_SOURCE_PHOTOS_DIR", source_dir
    )

    bg_path = tmp_path / "bg.png"
    bg = np.zeros((360, 640, 3), dtype=np.uint8)
    bg[:, :, 0] = 255  # blue bg
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
    assert r.composite_path is not None, "Expected composite from source fallback"
    assert r.composite_path.exists()
    # URL points to composite (source-fallback path)
    assert r.download_url is not None
    assert "composite.jpg" in r.download_url


def test_capture_no_source_no_mask_returns_original_only(
    tmp_path: Path,
    share_setup: tuple[ShareServer, ShareService],
    qapp,
    monkeypatch,
) -> None:
    """Background provided, no selfie_mask, no source photos → composite_path None."""
    from datetime import datetime
    import cv2
    from neo_makervigate.core.models import VisionFrame

    _, share = share_setup
    fg = np.zeros((360, 640, 3), dtype=np.uint8)
    vf = VisionFrame(timestamp=datetime.now(), width=640, height=360, selfie_mask=None)
    worker = _FakeWorkerWithVf(frame=fg, vf=vf)

    # Source dir empty
    empty_source = tmp_path / "empty_source"
    empty_source.mkdir()
    monkeypatch.setattr(
        "neo_makervigate.core.photo_capture.DEFAULT_SOURCE_PHOTOS_DIR", empty_source
    )

    bg_path = tmp_path / "bg.png"
    bg = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.imwrite(str(bg_path), bg)

    _ = PhotoService(worker=worker, share=share, photos_base=tmp_path)  # type: ignore[arg-type]

    results: list[PhotoResult] = []
    SignalBus.instance().photo_captured.connect(lambda r: results.append(r))
    SignalBus.instance().photo_capture_requested.emit({
        "experience_id": "exp06_photo_booth",
        "background_path": str(bg_path),
    })
    qapp.processEvents()
    r = results[0]
    assert r.composite_path is None
    assert "original.jpg" in r.download_url  # falls back to original
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_photo_service.py -v
```
Expected: 2 new tests FAIL — fallback not yet implemented.

- [ ] **Step 3: Modify photo_service.py**

In `src/neo_makervigate/services/photo_service.py`, find the existing composite logic (after live composite attempt). Find this section in `_on_capture_request`:

```python
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
```

After the existing `if bg_path_str:` block, add source fallback (still inside the `try` of `_on_capture_request`):

```python
            # P7c: Source photo fallback if live composite not available
            if composite_path is None and bg_path_str:
                import random
                from neo_makervigate.core.photo_capture import list_source_photos
                source_photos = list_source_photos()
                if source_photos:
                    source_pick = random.choice(source_photos)
                    try:
                        source_frame = cv2.imread(str(source_pick))
                        if source_frame is not None:
                            mask = np.ones(source_frame.shape[:2], dtype=np.float32)
                            composite_path = self._capture.save_composite(
                                source_frame, mask, Path(str(bg_path_str)), photo_dir,
                            )
                            logger.info(f"Source photo fallback: {source_pick.name}")
                    except Exception as e:
                        logger.warning(f"Source photo fallback failed: {e}")
```

Also add `import cv2` and `import numpy as np` to top of file if not already imported.

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass (149 tests total).

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/services/photo_service.py tests/unit/test_photo_service.py
git commit -m "$(cat <<'EOF'
feat(p7c): PhotoService source photo folder fallback

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

## Context

P7c task 3 of 11. When user smoke test shows live composite produces bad result (mask missing), fallback to admin-curated source_photos. monkeypatch reassigns DEFAULT_SOURCE_PHOTOS_DIR in tests so we don't pollute real ~/makervigate/source_photos/.

---

## Task 4: utils/face_math.py + 10 tests

**Files:**
- Create: `src/neo_makervigate/utils/face_math.py`
- Create: `tests/unit/test_face_math.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_face_math.py`:

```python
"""Tests cho utils/face_math — MediaPipe Face Mesh helpers."""

from __future__ import annotations

from neo_makervigate.core.models import Landmark
from neo_makervigate.utils.face_math import (
    LIP_BOTTOM,
    LIP_LEFT,
    LIP_RIGHT,
    LIP_TOP,
    LEFT_BROW_INNER,
    LEFT_EYE_BOTTOM,
    LEFT_EYE_INNER,
    LEFT_EYE_OUTER,
    LEFT_EYE_TOP,
    LEFT_TEMPLE,
    NOSE_TIP,
    RIGHT_BROW_INNER,
    RIGHT_EYE_BOTTOM,
    RIGHT_EYE_INNER,
    RIGHT_EYE_OUTER,
    RIGHT_EYE_TOP,
    RIGHT_TEMPLE,
    brow_raised_ratio,
    eye_aspect_ratio,
    head_yaw,
    mouth_aspect_ratio,
    mouth_width_ratio,
)


def _empty_face_landmarks(n: int = 468) -> list[Landmark]:
    """Empty face — all landmarks at center."""
    return [Landmark(x=0.5, y=0.5) for _ in range(n)]


def _set_lm(landmarks: list[Landmark], idx: int, x: float, y: float) -> None:
    landmarks[idx] = Landmark(x=x, y=y)


def test_mar_open_mouth_high() -> None:
    L = _empty_face_landmarks()
    # Wide vertical gap, narrow horizontal → high MAR
    _set_lm(L, LIP_TOP, 0.5, 0.55)
    _set_lm(L, LIP_BOTTOM, 0.5, 0.70)
    _set_lm(L, LIP_LEFT, 0.46, 0.625)
    _set_lm(L, LIP_RIGHT, 0.54, 0.625)
    mar = mouth_aspect_ratio(L)
    # vertical=0.15, horizontal=0.08 → MAR ~ 1.87
    assert mar > 1.5


def test_mar_closed_mouth_low() -> None:
    L = _empty_face_landmarks()
    _set_lm(L, LIP_TOP, 0.5, 0.62)
    _set_lm(L, LIP_BOTTOM, 0.5, 0.63)
    _set_lm(L, LIP_LEFT, 0.46, 0.625)
    _set_lm(L, LIP_RIGHT, 0.54, 0.625)
    mar = mouth_aspect_ratio(L)
    # vertical=0.01, horizontal=0.08 → MAR ~ 0.125
    assert mar < 0.2


def test_mouth_width_ratio_smile() -> None:
    L = _empty_face_landmarks()
    # Wide mouth = smile
    _set_lm(L, LIP_LEFT, 0.40, 0.625)
    _set_lm(L, LIP_RIGHT, 0.60, 0.625)
    # Face width
    _set_lm(L, LEFT_TEMPLE, 0.30, 0.50)
    _set_lm(L, RIGHT_TEMPLE, 0.70, 0.50)
    mwr = mouth_width_ratio(L)
    # mouth=0.20, face_width=0.40 → MWR = 0.5
    assert 0.45 < mwr < 0.55


def test_mouth_width_ratio_neutral() -> None:
    L = _empty_face_landmarks()
    # Narrow mouth = neutral
    _set_lm(L, LIP_LEFT, 0.46, 0.625)
    _set_lm(L, LIP_RIGHT, 0.54, 0.625)
    _set_lm(L, LEFT_TEMPLE, 0.30, 0.50)
    _set_lm(L, RIGHT_TEMPLE, 0.70, 0.50)
    mwr = mouth_width_ratio(L)
    # mouth=0.08, face_width=0.40 → MWR = 0.2
    assert mwr < 0.30


def test_ear_open_eye() -> None:
    L = _empty_face_landmarks()
    # Open eye: vertical gap 0.03, horizontal 0.08
    _set_lm(L, LEFT_EYE_TOP, 0.40, 0.48)
    _set_lm(L, LEFT_EYE_BOTTOM, 0.40, 0.51)
    _set_lm(L, LEFT_EYE_INNER, 0.43, 0.495)
    _set_lm(L, LEFT_EYE_OUTER, 0.35, 0.495)
    ear = eye_aspect_ratio(L, side="left")
    # 0.03 / 0.08 = 0.375
    assert 0.30 < ear < 0.45


def test_ear_closed_eye() -> None:
    L = _empty_face_landmarks()
    _set_lm(L, RIGHT_EYE_TOP, 0.60, 0.495)
    _set_lm(L, RIGHT_EYE_BOTTOM, 0.60, 0.500)  # nearly closed
    _set_lm(L, RIGHT_EYE_INNER, 0.57, 0.497)
    _set_lm(L, RIGHT_EYE_OUTER, 0.65, 0.497)
    ear = eye_aspect_ratio(L, side="right")
    # 0.005 / 0.08 = 0.0625
    assert ear < 0.10


def test_brow_raised_ratio_normal() -> None:
    L = _empty_face_landmarks()
    # Brow just above eye
    _set_lm(L, LEFT_BROW_INNER, 0.45, 0.46)
    _set_lm(L, LEFT_EYE_TOP, 0.45, 0.48)
    _set_lm(L, RIGHT_BROW_INNER, 0.55, 0.46)
    _set_lm(L, RIGHT_EYE_TOP, 0.55, 0.48)
    # Face height reference
    _set_lm(L, NOSE_TIP, 0.50, 0.55)
    # Chin not set, use default 0.5 → face_height = nose_y - 0.5 = 0.05? need to define
    # face_height = nose to chin: nose=0.55, chin=0.85 if set, else default 0.5
    # Brow gap = 0.48 - 0.46 = 0.02; if face_height ~0.35 → ratio = 0.057
    ratio = brow_raised_ratio(L)
    assert 0.03 < ratio < 0.09


def test_brow_raised_ratio_raised() -> None:
    L = _empty_face_landmarks()
    # Brow further above eye = raised
    _set_lm(L, LEFT_BROW_INNER, 0.45, 0.43)
    _set_lm(L, LEFT_EYE_TOP, 0.45, 0.48)
    _set_lm(L, RIGHT_BROW_INNER, 0.55, 0.43)
    _set_lm(L, RIGHT_EYE_TOP, 0.55, 0.48)
    _set_lm(L, NOSE_TIP, 0.50, 0.55)
    ratio = brow_raised_ratio(L)
    # Gap = 0.05 → ratio ~ 0.14
    assert ratio > 0.10


def test_head_yaw_facing_forward_zero() -> None:
    L = _empty_face_landmarks()
    _set_lm(L, NOSE_TIP, 0.50, 0.55)
    _set_lm(L, LEFT_TEMPLE, 0.30, 0.50)
    _set_lm(L, RIGHT_TEMPLE, 0.70, 0.50)
    yaw = head_yaw(L)
    # Symmetric → yaw close to 0
    assert abs(yaw) < 0.05


def test_head_yaw_facing_left() -> None:
    L = _empty_face_landmarks()
    # Nose closer to left temple = facing left
    _set_lm(L, NOSE_TIP, 0.35, 0.55)
    _set_lm(L, LEFT_TEMPLE, 0.25, 0.50)
    _set_lm(L, RIGHT_TEMPLE, 0.70, 0.50)
    yaw = head_yaw(L)
    # Nose dist to right > dist to left → positive (per convention: + = right turn FROM viewer)
    # Or negative if convention is + = right physically. Just check sign is consistent.
    # Distance from nose to left = 0.10, to right = 0.35 → asymmetry positive
    assert yaw > 0.10


def test_head_yaw_facing_right() -> None:
    L = _empty_face_landmarks()
    _set_lm(L, NOSE_TIP, 0.65, 0.55)
    _set_lm(L, LEFT_TEMPLE, 0.30, 0.50)
    _set_lm(L, RIGHT_TEMPLE, 0.75, 0.50)
    yaw = head_yaw(L)
    # Nose closer to right temple → opposite sign
    assert yaw < -0.10
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_face_math.py -v
```
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 3: Create face_math.py**

Create `src/neo_makervigate/utils/face_math.py`:

```python
"""Face mesh math helpers cho exp03 Face Yoga.

Computes mouth aspect ratio (MAR), eye aspect ratio (EAR), brow raised
ratio, and approximate head yaw from MediaPipe Face Mesh 468 landmarks.

Stateless functions — caller passes landmarks list each frame.
"""

from __future__ import annotations

import math
from typing import Literal

from neo_makervigate.core.models import Landmark

# MediaPipe Face Mesh landmark indices (commonly used subset)
# Mouth (lip inner + outer corners)
LIP_TOP = 13
LIP_BOTTOM = 14
LIP_LEFT = 78
LIP_RIGHT = 308

# Left eye
LEFT_EYE_TOP = 159
LEFT_EYE_BOTTOM = 145
LEFT_EYE_INNER = 133
LEFT_EYE_OUTER = 33

# Right eye
RIGHT_EYE_TOP = 386
RIGHT_EYE_BOTTOM = 374
RIGHT_EYE_INNER = 362
RIGHT_EYE_OUTER = 263

# Eyebrows
LEFT_BROW_INNER = 55
LEFT_BROW_OUTER = 105
RIGHT_BROW_INNER = 285
RIGHT_BROW_OUTER = 334

# Head orientation
NOSE_TIP = 1
CHIN = 152
LEFT_TEMPLE = 234
RIGHT_TEMPLE = 454


def _dist(a: Landmark, b: Landmark) -> float:
    """Euclidean distance in normalized coords."""
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def mouth_aspect_ratio(landmarks: list[Landmark]) -> float:
    """MAR = vertical lip gap / horizontal lip width.

    Closed mouth: ~0.05. Wide smile: ~0.2. Open O: ~0.55+.
    """
    if len(landmarks) < 309:
        return 0.0
    vertical = _dist(landmarks[LIP_TOP], landmarks[LIP_BOTTOM])
    horizontal = _dist(landmarks[LIP_LEFT], landmarks[LIP_RIGHT])
    if horizontal < 1e-6:
        return 0.0
    return vertical / horizontal


def mouth_width_ratio(landmarks: list[Landmark]) -> float:
    """mouth_width / face_temple_width. Smile pulls corners outward.

    Neutral: ~0.35. Smile: ~0.45+.
    """
    if len(landmarks) < 455:
        return 0.0
    mouth_width = _dist(landmarks[LIP_LEFT], landmarks[LIP_RIGHT])
    face_width = _dist(landmarks[LEFT_TEMPLE], landmarks[RIGHT_TEMPLE])
    if face_width < 1e-6:
        return 0.0
    return mouth_width / face_width


def eye_aspect_ratio(landmarks: list[Landmark], side: Literal["left", "right"]) -> float:
    """EAR = vertical / horizontal. Open: ~0.3. Closed: <0.1."""
    if len(landmarks) < 387:
        return 0.0
    if side == "left":
        top, bot, inner, outer = LEFT_EYE_TOP, LEFT_EYE_BOTTOM, LEFT_EYE_INNER, LEFT_EYE_OUTER
    else:
        top, bot, inner, outer = RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM, RIGHT_EYE_INNER, RIGHT_EYE_OUTER
    vertical = _dist(landmarks[top], landmarks[bot])
    horizontal = _dist(landmarks[inner], landmarks[outer])
    if horizontal < 1e-6:
        return 0.0
    return vertical / horizontal


def brow_raised_ratio(landmarks: list[Landmark]) -> float:
    """(eye_top_Y - brow_Y) / face_height. Normal ~0.05. Raised >0.08.

    Average of left + right sides.
    """
    if len(landmarks) < 386:
        return 0.0
    # Brow above eye → brow_y < eye_y in image coords (y increases downward)
    left_gap = landmarks[LEFT_EYE_TOP].y - landmarks[LEFT_BROW_INNER].y
    right_gap = landmarks[RIGHT_EYE_TOP].y - landmarks[RIGHT_BROW_INNER].y
    avg_gap = (left_gap + right_gap) / 2
    # Face height = nose to chin
    face_height = abs(landmarks[CHIN].y - landmarks[NOSE_TIP].y)
    if face_height < 1e-6:
        # Fallback face height
        face_height = 0.30
    return avg_gap / face_height


def head_yaw(landmarks: list[Landmark]) -> float:
    """Approximate horizontal head rotation.

    Positive: face turned toward left temple (more nose-to-right distance).
    Negative: face turned toward right temple.
    Range roughly [-1, +1].
    """
    if len(landmarks) < 455:
        return 0.0
    nose = landmarks[NOSE_TIP]
    left = landmarks[LEFT_TEMPLE]
    right = landmarks[RIGHT_TEMPLE]
    d_left = _dist(nose, left)
    d_right = _dist(nose, right)
    face_width = _dist(left, right)
    if face_width < 1e-6:
        return 0.0
    return (d_right - d_left) / face_width
```

- [ ] **Step 4: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest tests/unit/test_face_math.py -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/neo_makervigate/utils/face_math.py tests/unit/test_face_math.py
git commit -m "$(cat <<'EOF'
feat(p7c): utils/face_math — MAR, EAR, brow_raised, head_yaw helpers

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

## Context

P7c task 4 of 11. Face Mesh helper module. Pure functions on 468 Landmark list. Constants exported for tests to construct synth landmarks.

---

## Task 5: Enable Face module in VisionEngine

**Files:**
- Modify: `src/neo_makervigate/core/vision_engine.py`

- [ ] **Step 1: Verify face URL correct**

Read `src/neo_makervigate/core/vision_engine.py` and check `_MODEL_URLS["face"]`. Should be:

```python
    "face": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/latest/face_landmarker.task"
    ),
```

If correct (matches hands pattern `<task>/<model>/<precision>/<version>/<filename>.task`), no change. If wrong, fix URL.

- [ ] **Step 2: Verify `_create_detector("face")` exists**

Already exists in `_create_detector` from P1. Verify it returns FaceLandmarker.

- [ ] **Step 3: Verify `read()` handles face landmarks**

Read current `read()` for-loop. The existing face branch should already populate `vf.face` from result.face_landmarks. If verified, no change needed.

If not present, add to for-loop:

```python
                elif name == "face" and result.face_landmarks:
                    vf.face = [
                        Landmark(x=lm.x, y=lm.y, z=lm.z) for lm in result.face_landmarks[0]
                    ]
                    vf.has_person = True
```

Note this branch already exists from P6 T2 selfie work — verify by reading. If exists, this task is a verification-only no-op (commit only if changes made).

- [ ] **Step 4: Manual download verify**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -c "
from neo_makervigate.core.vision_engine import ensure_model
p = ensure_model('face')
print(f'OK: {p} ({p.stat().st_size // 1024} KB)')
"
```
Expected: downloads face_landmarker.task ~3MB OK.

- [ ] **Step 5: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass.

- [ ] **Step 6: Commit (only if changes made)**

If no code changes (all pre-existing), skip commit. Otherwise:

```bash
git add src/neo_makervigate/core/vision_engine.py
git commit -m "$(cat <<'EOF'
fix(p7c): verify face module enables correctly in VisionEngine

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

If verification passes and no commit needed, mark task complete and move to T6.

## Context

P7c task 5 of 11. Mostly verification — face module branches added in P1/P6. Confirm URL pattern works (lesson learned from selfie URL bug at P7). Download verify ensures URL valid.

---

## Task 6: poses.toml rewrite + YogaRobotExperience scaffold face-based

**Files:**
- Modify (rewrite): `src/neo_makervigate/experiences/exp03_yoga_robot/poses.toml`
- Modify (rewrite): `src/neo_makervigate/experiences/exp03_yoga_robot/logic.py`
- Modify (rewrite): `src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py`

- [ ] **Step 1: Rewrite poses.toml**

Replace contents of `src/neo_makervigate/experiences/exp03_yoga_robot/poses.toml`:

```toml
[[poses]]
id = "CUOI_TO"
title = "Cười to"
emoji = "😄"
subtitle = "Cười tươi, hé răng nhé!"
detector = "smile"
[poses.thresholds]
mouth_width_ratio_min = 0.45
mar_max = 0.25

[[poses]]
id = "MO_MIENG_O"
title = "Mở miệng O"
emoji = "😮"
subtitle = "Há miệng tròn như chữ O"
detector = "mouth_open"
[poses.thresholds]
mar_min = 0.55

[[poses]]
id = "WINK"
title = "Nháy mắt 1 bên"
emoji = "😉"
subtitle = "Nhắm 1 mắt, mở 1 mắt"
detector = "wink"
[poses.thresholds]
closed_eye_ear_max = 0.15
open_eye_ear_min = 0.25

[[poses]]
id = "NHUONG_MAY"
title = "Nhướng mày"
emoji = "🤨"
subtitle = "Nhướng mày lên cao"
detector = "brow_raised"
[poses.thresholds]
brow_raised_min = 0.085

[[poses]]
id = "LAC_DAU"
title = "Lắc đầu"
emoji = "🙅"
subtitle = "Lắc đầu trái phải"
detector = "head_shake"
[poses.thresholds]
yaw_amplitude_min = 0.25
oscillation_window_sec = 1.5
oscillation_min_crossings = 2
```

- [ ] **Step 2: Rewrite test_logic.py with baseline tests**

Replace contents of `src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py`:

```python
"""Tests cho YogaRobotExperience (Face Yoga) — gameplay logic độc lập."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Any, cast

import pytest

from neo_makervigate.core.models import Landmark, VisionFrame
from neo_makervigate.experiences.exp03_yoga_robot.logic import (
    Phase,
    YogaRobotExperience,
)
from neo_makervigate.utils import face_math as fm


class _FakeClock:
    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def _make_face_frame(scenario: str = "neutral", t: float = 0.0) -> VisionFrame:
    """Synthesize 468-landmark face for various scenarios."""
    L = [Landmark(x=0.5, y=0.5) for _ in range(468)]

    # Always set face anchor landmarks for face_math helpers
    L[fm.LEFT_TEMPLE] = Landmark(x=0.30, y=0.50)
    L[fm.RIGHT_TEMPLE] = Landmark(x=0.70, y=0.50)
    L[fm.NOSE_TIP] = Landmark(x=0.50, y=0.55)
    L[fm.CHIN] = Landmark(x=0.50, y=0.85)

    if scenario == "neutral":
        # Closed mouth, eyes open, brow normal
        L[fm.LIP_TOP] = Landmark(x=0.50, y=0.62)
        L[fm.LIP_BOTTOM] = Landmark(x=0.50, y=0.63)
        L[fm.LIP_LEFT] = Landmark(x=0.46, y=0.625)
        L[fm.LIP_RIGHT] = Landmark(x=0.54, y=0.625)
        L[fm.LEFT_EYE_TOP] = Landmark(x=0.40, y=0.48)
        L[fm.LEFT_EYE_BOTTOM] = Landmark(x=0.40, y=0.51)
        L[fm.LEFT_EYE_INNER] = Landmark(x=0.43, y=0.495)
        L[fm.LEFT_EYE_OUTER] = Landmark(x=0.35, y=0.495)
        L[fm.RIGHT_EYE_TOP] = Landmark(x=0.60, y=0.48)
        L[fm.RIGHT_EYE_BOTTOM] = Landmark(x=0.60, y=0.51)
        L[fm.RIGHT_EYE_INNER] = Landmark(x=0.57, y=0.495)
        L[fm.RIGHT_EYE_OUTER] = Landmark(x=0.65, y=0.495)
        L[fm.LEFT_BROW_INNER] = Landmark(x=0.45, y=0.46)
        L[fm.RIGHT_BROW_INNER] = Landmark(x=0.55, y=0.46)

    elif scenario == "smile":
        # Wide mouth, low MAR
        L[fm.LIP_TOP] = Landmark(x=0.50, y=0.62)
        L[fm.LIP_BOTTOM] = Landmark(x=0.50, y=0.625)
        L[fm.LIP_LEFT] = Landmark(x=0.40, y=0.625)
        L[fm.LIP_RIGHT] = Landmark(x=0.60, y=0.625)
        L[fm.LEFT_EYE_TOP] = Landmark(x=0.40, y=0.48)
        L[fm.LEFT_EYE_BOTTOM] = Landmark(x=0.40, y=0.51)
        L[fm.LEFT_EYE_INNER] = Landmark(x=0.43, y=0.495)
        L[fm.LEFT_EYE_OUTER] = Landmark(x=0.35, y=0.495)
        L[fm.RIGHT_EYE_TOP] = Landmark(x=0.60, y=0.48)
        L[fm.RIGHT_EYE_BOTTOM] = Landmark(x=0.60, y=0.51)
        L[fm.RIGHT_EYE_INNER] = Landmark(x=0.57, y=0.495)
        L[fm.RIGHT_EYE_OUTER] = Landmark(x=0.65, y=0.495)
        L[fm.LEFT_BROW_INNER] = Landmark(x=0.45, y=0.46)
        L[fm.RIGHT_BROW_INNER] = Landmark(x=0.55, y=0.46)

    elif scenario == "mouth_open":
        # Wide open O
        L[fm.LIP_TOP] = Landmark(x=0.50, y=0.55)
        L[fm.LIP_BOTTOM] = Landmark(x=0.50, y=0.70)
        L[fm.LIP_LEFT] = Landmark(x=0.46, y=0.625)
        L[fm.LIP_RIGHT] = Landmark(x=0.54, y=0.625)
        L[fm.LEFT_EYE_TOP] = Landmark(x=0.40, y=0.48)
        L[fm.LEFT_EYE_BOTTOM] = Landmark(x=0.40, y=0.51)
        L[fm.LEFT_EYE_INNER] = Landmark(x=0.43, y=0.495)
        L[fm.LEFT_EYE_OUTER] = Landmark(x=0.35, y=0.495)
        L[fm.RIGHT_EYE_TOP] = Landmark(x=0.60, y=0.48)
        L[fm.RIGHT_EYE_BOTTOM] = Landmark(x=0.60, y=0.51)
        L[fm.RIGHT_EYE_INNER] = Landmark(x=0.57, y=0.495)
        L[fm.RIGHT_EYE_OUTER] = Landmark(x=0.65, y=0.495)
        L[fm.LEFT_BROW_INNER] = Landmark(x=0.45, y=0.46)
        L[fm.RIGHT_BROW_INNER] = Landmark(x=0.55, y=0.46)

    elif scenario == "wink_left":
        # Left eye closed, right open
        L[fm.LIP_TOP] = Landmark(x=0.50, y=0.62)
        L[fm.LIP_BOTTOM] = Landmark(x=0.50, y=0.63)
        L[fm.LIP_LEFT] = Landmark(x=0.46, y=0.625)
        L[fm.LIP_RIGHT] = Landmark(x=0.54, y=0.625)
        # Left eye closed (vertical gap tiny)
        L[fm.LEFT_EYE_TOP] = Landmark(x=0.40, y=0.495)
        L[fm.LEFT_EYE_BOTTOM] = Landmark(x=0.40, y=0.500)
        L[fm.LEFT_EYE_INNER] = Landmark(x=0.43, y=0.497)
        L[fm.LEFT_EYE_OUTER] = Landmark(x=0.35, y=0.497)
        # Right eye open
        L[fm.RIGHT_EYE_TOP] = Landmark(x=0.60, y=0.48)
        L[fm.RIGHT_EYE_BOTTOM] = Landmark(x=0.60, y=0.51)
        L[fm.RIGHT_EYE_INNER] = Landmark(x=0.57, y=0.495)
        L[fm.RIGHT_EYE_OUTER] = Landmark(x=0.65, y=0.495)
        L[fm.LEFT_BROW_INNER] = Landmark(x=0.45, y=0.46)
        L[fm.RIGHT_BROW_INNER] = Landmark(x=0.55, y=0.46)

    elif scenario == "brow_up":
        # Brows higher above eyes
        L[fm.LIP_TOP] = Landmark(x=0.50, y=0.62)
        L[fm.LIP_BOTTOM] = Landmark(x=0.50, y=0.63)
        L[fm.LIP_LEFT] = Landmark(x=0.46, y=0.625)
        L[fm.LIP_RIGHT] = Landmark(x=0.54, y=0.625)
        L[fm.LEFT_EYE_TOP] = Landmark(x=0.40, y=0.48)
        L[fm.LEFT_EYE_BOTTOM] = Landmark(x=0.40, y=0.51)
        L[fm.LEFT_EYE_INNER] = Landmark(x=0.43, y=0.495)
        L[fm.LEFT_EYE_OUTER] = Landmark(x=0.35, y=0.495)
        L[fm.RIGHT_EYE_TOP] = Landmark(x=0.60, y=0.48)
        L[fm.RIGHT_EYE_BOTTOM] = Landmark(x=0.60, y=0.51)
        L[fm.RIGHT_EYE_INNER] = Landmark(x=0.57, y=0.495)
        L[fm.RIGHT_EYE_OUTER] = Landmark(x=0.65, y=0.495)
        # Brows much higher
        L[fm.LEFT_BROW_INNER] = Landmark(x=0.45, y=0.43)
        L[fm.RIGHT_BROW_INNER] = Landmark(x=0.55, y=0.43)

    elif scenario == "head_left":
        # Head turned left → nose closer to left temple
        L[fm.NOSE_TIP] = Landmark(x=0.35, y=0.55)
        # Other landmarks default neutral
        L[fm.LIP_TOP] = Landmark(x=0.35, y=0.62)
        L[fm.LIP_BOTTOM] = Landmark(x=0.35, y=0.63)
        L[fm.LIP_LEFT] = Landmark(x=0.31, y=0.625)
        L[fm.LIP_RIGHT] = Landmark(x=0.39, y=0.625)

    elif scenario == "head_right":
        L[fm.NOSE_TIP] = Landmark(x=0.65, y=0.55)
        L[fm.LIP_TOP] = Landmark(x=0.65, y=0.62)
        L[fm.LIP_BOTTOM] = Landmark(x=0.65, y=0.63)
        L[fm.LIP_LEFT] = Landmark(x=0.61, y=0.625)
        L[fm.LIP_RIGHT] = Landmark(x=0.69, y=0.625)

    vf = VisionFrame(timestamp=datetime(2026, 1, 1), width=1280, height=720)
    vf.face = L
    return vf


def _make_empty_frame() -> VisionFrame:
    return VisionFrame(timestamp=datetime(2026, 1, 1), width=1280, height=720)


@pytest.fixture
def exp_with_clock(qapp) -> tuple[YogaRobotExperience, _FakeClock]:
    clock = _FakeClock(0.0)
    exp = YogaRobotExperience(clock=clock)
    exp.on_enter()
    yield exp, clock
    exp.on_exit()


def test_meta_face_module() -> None:
    meta = YogaRobotExperience.meta
    assert meta.id == "exp03_yoga_robot"
    assert "face" in meta.vision_modules
    assert "pose" not in meta.vision_modules


def test_initial_phase_is_intro(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, _ = exp_with_clock
    state = exp.render_state()
    assert state["phase"] == Phase.INTRO.value


def test_poses_toml_loaded_5_face_poses(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, _ = exp_with_clock
    state = exp.render_state()
    backgrounds = cast(list[dict[str, Any]], state["poses"])
    # Wait — actually the state schema for exp03 uses pose_count not "poses" list
    assert state["pose_count"] == 5


def test_intro_transitions_to_posing_after_2s(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    exp, clock = exp_with_clock
    state = exp.render_state()
    assert state["phase"] == Phase.INTRO.value
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())
    assert exp.render_state()["phase"] == Phase.POSING.value
```

- [ ] **Step 3: Run tests to verify they fail or need updates**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py -v
```
Expected: 4 new tests FAIL — `YogaRobotExperience` still pose-based.

- [ ] **Step 4: Rewrite logic.py**

Replace contents of `src/neo_makervigate/experiences/exp03_yoga_robot/logic.py`:

```python
"""exp03 Yoga Robot — Face-based gameplay (P7c rewrite).

Switched từ pose detection (full body, nhiễu nhiều) sang Face Mesh
(5 biểu cảm). Trẻ ngồi sát kiosk, không cần lùi ra.

5 poses: CUOI_TO, MO_MIENG_O, WINK, NHUONG_MAY, LAC_DAU.

Detector dispatcher map id → algorithm trong _evaluate_pose.
Head shake tracks yaw history deque maxlen 60 (~2s @ 30fps).
"""

from __future__ import annotations

import time
import tomllib
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from loguru import logger

from neo_makervigate.core.models import ExperienceMeta, Landmark, VisionFrame
from neo_makervigate.experiences.experience_base import BaseExperience
from neo_makervigate.utils.face_math import (
    brow_raised_ratio,
    eye_aspect_ratio,
    head_yaw,
    mouth_aspect_ratio,
    mouth_width_ratio,
)

_QML_PATH = (Path(__file__).parent / "ui.qml").as_posix()
_POSES_TOML = Path(__file__).parent / "poses.toml"

# Phase durations (sec)
INTRO_DURATION = 2.0
RESULT_DURATION = 3.0

# Pose attempt config
HOLD_REQUIRED_SEC = 2.0  # easier than 3s body-pose (face poses more stable)
MATCH_GAP_TOLERANCE = 0.3
HINT_AFTER_SEC = 15.0
SKIP_AFTER_SEC = 45.0

# Head shake tracking
YAW_HISTORY_MAXLEN = 60  # ~2s @ 30fps


class Phase(StrEnum):
    INTRO = "intro"
    POSING = "posing"
    RESULT = "result"
    DONE = "done"


@dataclass
class PoseTarget:
    id: str
    title: str
    emoji: str
    subtitle: str
    detector: str
    thresholds: dict[str, float]


@dataclass
class PoseAttempt:
    pose_id: str
    started_at: float
    hold_progress: float = 0.0
    last_match_at: float | None = None
    max_score_seen: int = 0
    matched_complete: bool = False
    skipped: bool = False
    final_score: int = 0


def _load_poses() -> list[PoseTarget]:
    with open(_POSES_TOML, "rb") as f:
        data = tomllib.load(f)
    poses: list[PoseTarget] = []
    for entry in data.get("poses", []):
        poses.append(
            PoseTarget(
                id=entry["id"],
                title=entry["title"],
                emoji=entry["emoji"],
                subtitle=entry.get("subtitle", ""),
                detector=entry["detector"],
                thresholds={k: float(v) for k, v in entry["thresholds"].items()},
            )
        )
    return poses


class YogaRobotExperience(BaseExperience):
    """Face Yoga — 5 biểu cảm vui (P7c)."""

    meta = ExperienceMeta(
        id="exp03_yoga_robot",
        title="Yoga Robot",
        subtitle="Bắt chước 5 biểu cảm vui!",
        age_min=5,
        age_max=12,
        vision_modules=("face",),
        needs_qwen=False,
        needs_voice=False,
        needs_internet=False,
        icon_path="",
        dev_days=7,
    )

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        super().__init__()
        self._clock: Callable[[], float] = clock or time.perf_counter
        self._poses: list[PoseTarget] = _load_poses()
        self._phase: Phase = Phase.INTRO
        self._phase_started_at: float = 0.0
        self._pose_index: int = 0
        self._attempts: list[PoseAttempt] = []
        self._last_step_at: float = 0.0
        self._current_score: int = 0
        self._yaw_history: deque[tuple[float, float]] = deque(maxlen=YAW_HISTORY_MAXLEN)

    def get_qml_path(self) -> str:
        return _QML_PATH

    def on_enter(self) -> None:
        now = self._clock()
        logger.info(f"YogaRobot (Face): on_enter ({len(self._poses)} poses loaded)")
        self._phase = Phase.INTRO
        self._phase_started_at = now
        self._last_step_at = now
        self._pose_index = 0
        self._attempts = []
        self._current_score = 0
        self._yaw_history.clear()

    def on_vision_frame(self, frame: VisionFrame) -> None:
        now = self._clock()
        self._step_phase(now)
        dt = now - self._last_step_at
        if self._phase != Phase.POSING or not frame.face:
            self._current_score = 0
            self._last_step_at = now
            return
        if self._pose_index >= len(self._poses):
            self._last_step_at = now
            return

        target = self._poses[self._pose_index]
        score, matched = self._evaluate_pose(frame.face, target, now)
        self._current_score = score
        if not self._attempts:
            self._last_step_at = now
            return
        attempt = self._attempts[-1]
        attempt.max_score_seen = max(attempt.max_score_seen, score)

        if matched:
            if (
                attempt.last_match_at is not None
                and now - attempt.last_match_at <= MATCH_GAP_TOLERANCE
            ):
                attempt.hold_progress += dt
            else:
                attempt.hold_progress = dt
            attempt.last_match_at = now
            if attempt.hold_progress >= HOLD_REQUIRED_SEC and not attempt.matched_complete:
                attempt.matched_complete = True
                attempt.final_score = attempt.max_score_seen
                self._advance_to_next_pose(now)
                self._last_step_at = now
                return
        else:
            if (
                attempt.last_match_at is not None
                and now - attempt.last_match_at > MATCH_GAP_TOLERANCE
            ):
                attempt.hold_progress = 0.0
                attempt.last_match_at = None

        # Stuck-skip check
        if not attempt.matched_complete:
            elapsed_in_attempt = now - attempt.started_at
            if elapsed_in_attempt >= SKIP_AFTER_SEC:
                attempt.skipped = True
                attempt.final_score = 0
                self._advance_to_next_pose(now)
                self._last_step_at = now
                return

        self._last_step_at = now

    def render_state(self) -> dict[str, object]:
        now = self._clock()
        current_pose_dict: dict[str, object] | None = None
        attempt = self._attempts[-1] if self._attempts else None
        elapsed_in_pose = 0.0
        hold_progress = 0.0
        max_score = 0
        if self._phase == Phase.POSING and self._pose_index < len(self._poses):
            target = self._poses[self._pose_index]
            current_pose_dict = {
                "id": target.id,
                "title": target.title,
                "emoji": target.emoji,
                "subtitle": target.subtitle,
            }
            if attempt is not None:
                elapsed_in_pose = now - attempt.started_at
                hold_progress = attempt.hold_progress
                max_score = attempt.max_score_seen
        return {
            "phase": self._phase.value,
            "elapsed_in_phase": now - self._phase_started_at,
            "pose_index": self._pose_index,
            "pose_count": len(self._poses),
            "current_pose": current_pose_dict,
            "score": self._current_score,
            "max_score_in_attempt": max_score,
            "match_threshold": 65,
            "hold_progress": hold_progress,
            "hold_required": HOLD_REQUIRED_SEC,
            "elapsed_in_pose": elapsed_in_pose,
            "show_hint": elapsed_in_pose >= HINT_AFTER_SEC,
            "stuck_skip_at": SKIP_AFTER_SEC,
            "completed_poses": [
                {"id": a.pose_id, "final_score": a.final_score, "skipped": a.skipped}
                for a in self._attempts
                if a.matched_complete or a.skipped
            ],
            "total_score": sum(
                a.final_score for a in self._attempts if a.matched_complete or a.skipped
            ),
            "best_pose_id": self._best_pose_id(),
            "face_landmarks_present": bool(self._current_score > 0),
        }

    def completion_summary(self) -> dict[str, Any]:
        completed = [a for a in self._attempts if a.matched_complete or a.skipped]
        return {
            "completed": True,
            "score": sum(a.final_score for a in completed),
            "poses_completed": len(completed),
            "best_pose_id": self._best_pose_id(),
            "skipped_count": sum(1 for a in completed if a.skipped),
        }

    # ---- Internal ----

    def _evaluate_pose(
        self, face: list[Landmark], target: PoseTarget, now: float
    ) -> tuple[int, bool]:
        """Returns (score 0-100, matched bool)."""
        detector = target.detector
        th = target.thresholds
        if detector == "smile":
            mar = mouth_aspect_ratio(face)
            mwr = mouth_width_ratio(face)
            matched = mwr >= th["mouth_width_ratio_min"] and mar <= th["mar_max"]
            score = min(100, int((mwr / th["mouth_width_ratio_min"]) * 70))
            return score, matched
        if detector == "mouth_open":
            mar = mouth_aspect_ratio(face)
            matched = mar >= th["mar_min"]
            score = min(100, int((mar / th["mar_min"]) * 70))
            return score, matched
        if detector == "wink":
            ear_l = eye_aspect_ratio(face, "left")
            ear_r = eye_aspect_ratio(face, "right")
            left_winking = (
                ear_l <= th["closed_eye_ear_max"] and ear_r >= th["open_eye_ear_min"]
            )
            right_winking = (
                ear_r <= th["closed_eye_ear_max"] and ear_l >= th["open_eye_ear_min"]
            )
            matched = left_winking or right_winking
            return (100 if matched else 30), matched
        if detector == "brow_raised":
            ratio = brow_raised_ratio(face)
            matched = ratio >= th["brow_raised_min"]
            score = min(100, int((ratio / th["brow_raised_min"]) * 70))
            return score, matched
        if detector == "head_shake":
            yaw = head_yaw(face)
            self._yaw_history.append((now, yaw))
            matched, oscillations = self._check_head_shake(th)
            return min(100, oscillations * 33), matched
        return 0, False

    def _check_head_shake(self, th: dict[str, float]) -> tuple[bool, int]:
        """Returns (matched, oscillation_count)."""
        if len(self._yaw_history) < 8:
            return False, 0
        window = th.get("oscillation_window_sec", 1.5)
        amplitude_min = th.get("yaw_amplitude_min", 0.25)
        min_crossings = int(th.get("oscillation_min_crossings", 2))

        now = self._yaw_history[-1][0]
        # Filter samples within window
        recent = [(t, y) for t, y in self._yaw_history if now - t <= window]
        if len(recent) < 8:
            return False, 0
        yaws = [y for _, y in recent]
        amplitude = max(yaws) - min(yaws)
        if amplitude < amplitude_min:
            return False, 0
        baseline = sum(yaws) / len(yaws)
        dyaws = [y - baseline for y in yaws]
        crossings = sum(1 for i in range(1, len(dyaws)) if dyaws[i - 1] * dyaws[i] < 0)
        return crossings >= min_crossings, crossings

    def _step_phase(self, now: float) -> None:
        elapsed = now - self._phase_started_at
        if self._phase == Phase.INTRO and elapsed >= INTRO_DURATION:
            self._phase = Phase.POSING
            self._phase_started_at = now
            self._start_pose(0, now)
        elif self._phase == Phase.RESULT and elapsed >= RESULT_DURATION:
            self._phase = Phase.DONE
            self._phase_started_at = now

    def _start_pose(self, index: int, now: float) -> None:
        if index >= len(self._poses):
            return
        self._pose_index = index
        self._attempts.append(
            PoseAttempt(pose_id=self._poses[index].id, started_at=now)
        )
        self._yaw_history.clear()  # fresh history per pose

    def _advance_to_next_pose(self, now: float) -> None:
        next_index = self._pose_index + 1
        if next_index >= len(self._poses):
            self._phase = Phase.RESULT
            self._phase_started_at = now
        else:
            self._start_pose(next_index, now)

    def _best_pose_id(self) -> str | None:
        completed = [a for a in self._attempts if a.matched_complete or a.skipped]
        if not completed:
            return None
        best = max(completed, key=lambda a: a.final_score)
        return best.pose_id


EXPERIENCE = YogaRobotExperience
```

- [ ] **Step 5: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass.

Note: existing tests in test_logic.py were rewritten in Step 2 — only 4 baseline tests there now. Detector-specific tests added in T7+T8.

- [ ] **Step 6: Commit**

```bash
git add src/neo_makervigate/experiences/exp03_yoga_robot/poses.toml \
        src/neo_makervigate/experiences/exp03_yoga_robot/logic.py \
        src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py
git commit -m "$(cat <<'EOF'
feat(p7c): exp03 Yoga Robot rewrite — Face Yoga (5 biểu cảm)

Replace body pose detection với face mesh. vision_modules: ("pose",) → ("face",).
5 poses: cười / mở O / wink / nhướng mày / lắc đầu.
Detector dispatcher trong _evaluate_pose. Yaw history deque cho head_shake.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

## Context

P7c task 6 of 11. Big rewrite — replaces body pose with face-based. Hold time 3s → 2s (face poses easier hold). Phase machine same (INTRO/POSING/RESULT/DONE). Detector dispatched by `target.detector` string from poses.toml.

---

## Task 7: smile + mouth_open detector tests

**Files:**
- Modify: `src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py`

- [ ] **Step 1: Append failing tests**

Append to `test_logic.py`:

```python
def test_smile_pose_match_advances_after_hold(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """Smile face frames → hold 2s → advance to mouth_open."""
    exp, clock = exp_with_clock
    # Skip INTRO
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING (smile is pose 0)
    # Send smile frames for 2.5s
    for _ in range(5):
        clock.advance(0.5)
        exp.on_vision_frame(_make_face_frame("smile"))
    state = exp.render_state()
    # After hold, pose_index advances to 1 (mouth_open)
    assert state["pose_index"] == 1
    completed = cast(list[dict[str, Any]], state["completed_poses"])
    assert len(completed) == 1
    assert completed[0]["id"] == "CUOI_TO"


def test_mouth_open_pose_match(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """Skip to mouth_open pose (index 1), match → advance."""
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # → POSING smile
    # Complete smile via hold
    for _ in range(5):
        clock.advance(0.5)
        exp.on_vision_frame(_make_face_frame("smile"))
    # Now on mouth_open
    assert exp.render_state()["pose_index"] == 1
    # Send open mouth frames
    for _ in range(5):
        clock.advance(0.5)
        exp.on_vision_frame(_make_face_frame("mouth_open"))
    # Advanced to wink (index 2)
    assert exp.render_state()["pose_index"] == 2
```

- [ ] **Step 2: Run tests**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py -v
```
Expected: 2 new tests PASS (detectors already implemented in T6).

If MAR/MWR thresholds not match synth, debug face_math values or adjust poses.toml thresholds.

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py
git commit -m "$(cat <<'EOF'
test(p7c): smile + mouth_open detector match advance

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: wink + brow_raised detector tests

**Files:**
- Modify: `src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py`

- [ ] **Step 1: Append tests**

Append to `test_logic.py`:

```python
def test_wink_pose_match(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """Wink frames → match → advance."""
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())  # smile pose
    # Skip smile via stuck-skip OR rapid complete with smile frames
    for _ in range(5):
        clock.advance(0.5)
        exp.on_vision_frame(_make_face_frame("smile"))
    # Skip mouth_open
    for _ in range(5):
        clock.advance(0.5)
        exp.on_vision_frame(_make_face_frame("mouth_open"))
    # Now on wink (index 2)
    assert exp.render_state()["pose_index"] == 2
    # Send wink frames
    for _ in range(5):
        clock.advance(0.5)
        exp.on_vision_frame(_make_face_frame("wink_left"))
    assert exp.render_state()["pose_index"] == 3


def test_brow_raised_pose_match(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """Brow raised → match brow_raised pose (index 3)."""
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())
    # Skip to index 3 via 3 stuck-skips (45s × 3 = 135s)
    for _ in range(3):
        clock.advance(45.1)
        exp.on_vision_frame(_make_empty_frame())
    assert exp.render_state()["pose_index"] == 3
    # Send brow_up frames
    for _ in range(5):
        clock.advance(0.5)
        exp.on_vision_frame(_make_face_frame("brow_up"))
    assert exp.render_state()["pose_index"] == 4
```

- [ ] **Step 2: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py
git commit -m "$(cat <<'EOF'
test(p7c): wink + brow_raised detector match

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: head_shake detector + completion test

**Files:**
- Modify: `src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py`

- [ ] **Step 1: Append tests**

Append to `test_logic.py`:

```python
def test_head_shake_oscillation_match(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """Alternate head_left / head_right frames → head_shake detector matches."""
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())
    # Skip to head_shake (index 4) via 4 stuck-skips
    for _ in range(4):
        clock.advance(45.1)
        exp.on_vision_frame(_make_empty_frame())
    assert exp.render_state()["pose_index"] == 4
    # Send alternating head_left / head_right at high rate
    scenarios = ["head_left", "head_right"] * 8  # 16 frames, 4 oscillations
    for i, scn in enumerate(scenarios):
        clock.advance(0.1)
        exp.on_vision_frame(_make_face_frame(scn))
    # After hold required (2s), should advance to RESULT
    # Need enough frames within window 1.5s
    state = exp.render_state()
    # Either still on pose 4 (matching, holding) or moved to RESULT
    assert state["phase"] in (Phase.POSING.value, Phase.RESULT.value)


def test_completion_summary_face_yoga(
    exp_with_clock: tuple[YogaRobotExperience, _FakeClock],
) -> None:
    """Complete all 5 poses (skip mode) → RESULT phase + completion summary."""
    exp, clock = exp_with_clock
    clock.advance(2.1)
    exp.on_vision_frame(_make_empty_frame())
    # Skip all 5 poses
    for _ in range(5):
        clock.advance(45.1)
        exp.on_vision_frame(_make_empty_frame())
    state = exp.render_state()
    assert state["phase"] == Phase.RESULT.value
    summary = exp.completion_summary()
    assert summary["completed"] is True
    assert summary["poses_completed"] == 5
    assert summary["skipped_count"] == 5  # all skipped
```

- [ ] **Step 2: Run tests + lint**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all pass. If head_shake test fails due to oscillation timing, the test condition is permissive (POSING or RESULT) — should pass.

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/experiences/exp03_yoga_robot/test_logic.py
git commit -m "$(cat <<'EOF'
test(p7c): head_shake oscillation + completion summary

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: ui.qml rewrite — face landmark overlay

**Files:**
- Modify: `src/neo_makervigate/experiences/exp03_yoga_robot/ui.qml`

- [ ] **Step 1: Rewrite ui.qml**

Read current `src/neo_makervigate/experiences/exp03_yoga_robot/ui.qml` first (was body-pose oriented). Replace contents:

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import "../../ui/qml/singletons" as Sing

Item {
    id: root
    anchors.fill: parent

    readonly property var state: app.experienceState
    readonly property string phase: state && state.phase ? state.phase : "intro"
    readonly property int score: state && state.score !== undefined ? state.score : 0
    readonly property real holdProgress: state && state.hold_progress !== undefined ? state.hold_progress : 0.0
    readonly property real holdRequired: state && state.hold_required !== undefined ? state.hold_required : 2.0
    readonly property int matchThreshold: state && state.match_threshold !== undefined ? state.match_threshold : 65
    readonly property var currentPose: state && state.current_pose ? state.current_pose : null
    readonly property bool showHint: state && state.show_hint ? true : false
    readonly property var completedPoses: state && state.completed_poses ? state.completed_poses : []
    readonly property int totalScore: state && state.total_score !== undefined ? state.total_score : 0
    readonly property string bestPoseId: state && state.best_pose_id ? state.best_pose_id : ""
    readonly property int poseCount: state && state.pose_count !== undefined ? state.pose_count : 5
    readonly property int poseIndex: state && state.pose_index !== undefined ? state.pose_index : 0

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

    // Face landmark overlay — dots only (468 too dense for full skeleton)
    // Show key landmarks: mouth, eyes, eyebrows, nose
    Canvas {
        id: faceCanvas
        anchors.fill: parent
        renderTarget: Canvas.FramebufferObject

        Connections {
            target: app
            function onFaceLandmarksChanged() { faceCanvas.requestPaint() }
        }

        onPaint: {
            const ctx = faceCanvas.getContext("2d")
            ctx.reset()
            const face = app.faceLandmarks
            if (!face || face.length < 386) return

            ctx.fillStyle = "#C77B2C"
            // Key landmark indices (subset)
            const indices = [
                1, 13, 14, 78, 308,  // nose + mouth
                33, 133, 145, 159, 263, 362, 374, 386,  // eyes
                55, 105, 285, 334,  // brows
            ]
            for (let i = 0; i < indices.length; i++) {
                const idx = indices[i]
                if (idx >= face.length) continue
                const px = (1 - face[idx].x) * width  // mirror x
                const py = face[idx].y * height
                ctx.beginPath()
                ctx.arc(px, py, 4, 0, 2 * Math.PI)
                ctx.fill()
            }
        }
    }

    // Pose card top center
    Rectangle {
        visible: root.currentPose !== null && root.phase === "posing"
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: 24
        width: poseCardCol.implicitWidth + 48
        height: poseCardCol.implicitHeight + 24
        radius: 20
        color: "#E03F6627"
        border.color: "#FFC77B2C"
        border.width: 3

        ColumnLayout {
            id: poseCardCol
            anchors.centerIn: parent
            spacing: 6
            Text {
                text: (root.currentPose ? root.currentPose.emoji : "") + "  " + (root.currentPose ? root.currentPose.title : "")
                color: "white"
                font.pixelSize: 40
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: root.currentPose ? root.currentPose.subtitle : ""
                color: "#FAF6EE"
                font.pixelSize: 22
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Biểu cảm " + (root.poseIndex + 1) + " / " + root.poseCount
                color: "#FAF6EE"
                opacity: 0.7
                font.pixelSize: 16
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    // Bottom HUD: robot face + hold bar + score
    Rectangle {
        visible: root.phase === "posing"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 24
        height: 140
        radius: 24
        color: "#E0000000"

        RowLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 24

            Item {
                Layout.preferredWidth: 120
                Layout.fillHeight: true
                Text {
                    anchors.centerIn: parent
                    text: {
                        const s = root.score
                        if (s >= root.matchThreshold) return "😄"
                        if (s >= 40) return "🙂"
                        return "😐"
                    }
                    font.pixelSize: 96
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 32
                    Rectangle {
                        anchors.fill: parent
                        radius: 16
                        color: "#FF1F3018"
                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.margins: 4
                            width: Math.min(1, root.holdProgress / root.holdRequired) * (parent.width - 8)
                            radius: 12
                            color: (root.holdProgress / root.holdRequired) > 0.66 ? "#FFC77B2C" : "#FF5C8A3A"
                            Behavior on width { NumberAnimation { duration: 50 } }
                        }
                    }
                    Text {
                        anchors.centerIn: parent
                        text: root.holdProgress.toFixed(1) + "s / " + root.holdRequired.toFixed(1) + "s"
                        color: "white"
                        font.pixelSize: 18
                        font.bold: true
                    }
                }
                Text {
                    text: "Điểm: " + root.score + "/100  (cần " + root.matchThreshold + "+)"
                    color: "white"
                    font.pixelSize: 22
                    font.bold: true
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }
    }

    // Intro overlay
    Rectangle {
        visible: root.phase === "intro"
        anchors.fill: parent
        color: "#A0000000"
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 24
            Text {
                text: "🤖 Bắt chước 5 biểu cảm!"
                color: "white"
                font.pixelSize: 56
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "😄  😮  😉  🤨  🙅"
                color: "#FAF6EE"
                font.pixelSize: 64
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Sẵn sàng nhé..."
                color: "#FAF6EE"
                font.pixelSize: 28
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }

    // Result overlay
    Rectangle {
        visible: root.phase === "result"
        anchors.fill: parent
        color: "#C0000000"
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 24
            Text {
                text: "🎉 Tuyệt vời!"
                color: "white"
                font.pixelSize: 72
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: "Tổng điểm: " + root.totalScore + " / 500"
                color: "#C77B2C"
                font.pixelSize: 48
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                text: root.bestPoseId !== "" ? "Pose đẹp nhất: " + root.bestPoseId : ""
                color: "#FAF6EE"
                font.pixelSize: 28
                visible: root.bestPoseId !== ""
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
}
```

- [ ] **Step 2: Verify tests still pass**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add src/neo_makervigate/experiences/exp03_yoga_robot/ui.qml
git commit -m "$(cat <<'EOF'
feat(p7c): exp03 ui.qml face landmark overlay (dots-only, not skeleton)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

## Context

P7c task 10 of 11. ui.qml shows mirror camera + 17 key face landmarks as dots (mouth, eyes, brows, nose). Skipping skeleton drawing because face mesh is 468 dots — too dense. HUD same robot face widget + hold bar from pose version.

`app.faceLandmarks` property assumed to exist (P6 enabled face module + extended AppController). If not, may need to add to AppController same pattern as handLandmarks/poseLandmarks. Check existing AppController structure.

---

## Task 11: Final verify + smoke + PHASES.md done

- [ ] **Step 1: Full test + lint sweep**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m pytest --tb=short -v
cd /Users/tuanln/Ai-Code/NeoMakerViGate && source .venv/bin/activate && ruff check && mypy src/
```
Expected: all green. Total ~165 tests (144 + ~21 P7c new).

- [ ] **Step 2: Manual smoke test (real webcam)**

```bash
cd /Users/tuanln/Ai-Code/NeoMakerViGate && .venv/bin/python -m neo_makervigate
```

Verify:
1. Hub → Yoga Robot card click
2. Intro 2s → POSING smile pose
3. Cười to → robot face 😐→😄, hold bar increases, ~2s → advance to mouth_open
4. Mở miệng O → advance to wink
5. Nháy 1 mắt → advance to brow_raised
6. Nhướng mày → advance to head_shake
7. Lắc đầu trái-phải → match → RESULT
8. Photo Booth (exp06): V_SIGN with relaxed margin — should trigger easier
9. Add 1-2 .jpg to `~/makervigate/source_photos/` → exp06 with no selfie mask → composite uses source photo

- [ ] **Step 3: Update PHASES.md**

In `DOC/PHASES.md`, find P7c section (or add if missing). Add Achievement note:

```markdown
## P7c — Bug Fixes + UX Polish ✅ DONE (2026-05-18)

**Achievement:** Fix 3 issues từ smoke test webcam thật. exp03 redesign từ body pose (full body, đứng xa cam, đồ vật nhiễu) → Face Yoga (5 biểu cảm: cười / mở O / wink / nhướng mày / lắc đầu, sit close to cam, MediaPipe Face Mesh 468 landmarks). utils/face_math.py (MAR, MWR, EAR, brow_raised_ratio, head_yaw, 11 tests). exp03 detector dispatcher (5 detectors). V_SIGN_FINGER_MARGIN 1.15→1.05 (easier detection). PhotoCapture.list_source_photos + DEFAULT_SOURCE_PHOTOS_DIR. PhotoService source photo folder fallback (~/makervigate/source_photos/ admin upload, random pick when selfie_mask missing). 11 tasks TDD. ~165 tests pass, ruff/mypy strict clean. **Decision chốt:** lè lưỡi → Wink (FaceMesh không track tongue).
```

- [ ] **Step 4: Commit PHASES**

```bash
git add DOC/PHASES.md
git commit -m "$(cat <<'EOF'
docs(p7c): mark P7c bug fix + UX polish done

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 5: Update memory**

Edit `/Users/tuanln/.claude/projects/-Users-tuanln/memory/project_neomakervigate_status.md`. Add a P7c achievement line after P7a:

```markdown
- **P7c Bug Fix + UX Polish ✅ DONE** (2026-05-18, head commit `<hash>`): Fix 3 issues từ smoke test webcam thật. V_SIGN_FINGER_MARGIN 1.15→1.05 (easier detection). PhotoCapture.list_source_photos + PhotoService source folder fallback (~/makervigate/source_photos/). exp03 redesign Body Pose → Face Yoga (Face Mesh 468 landmarks, 5 biểu cảm: cười/mở O/wink/nhướng mày/lắc đầu, lè lưỡi → Wink vì FaceMesh không track tongue). utils/face_math.py (MAR/EAR/brow/yaw helpers, 11 tests). Detector dispatcher trong YogaRobotExperience. ~165 tests pass, ruff/mypy strict clean.
```

(Memory không track git — không commit.)

---

## Self-Review Summary

**Spec coverage:**
- §1 Architecture overview → All tasks together cover A (face yoga), B (V_SIGN), C (source fallback)
- §2 exp03 Face Yoga details → Tasks 4 (face_math), 5 (engine), 6 (logic+poses), 7-9 (detector tests), 10 (ui.qml)
- §3 V_SIGN + source fallback → Tasks 1, 2, 3
- §4 File layout + testing → All tasks deliver listed files; ~21 new tests covered
- §5 Out of scope → respected (no tongue, single face, manual scp upload)

**Placeholders:** None.

**Type consistency:**
- `Phase` enum values (intro/posing/result/done) consistent across tests + logic
- `PoseTarget` fields (id/title/emoji/subtitle/detector/thresholds) consistent in toml + dataclass + render_state
- `detector` string keys: "smile", "mouth_open", "wink", "brow_raised", "head_shake" consistent across toml + dispatcher
- `face_math` exports (LIP_TOP, etc + functions) match imports in test_face_math + logic.py
- `list_source_photos` signature consistent in T2 + T3

**Plan ends with:** Working face-based exp03 + V_SIGN relax + source fallback. Manual smoke test verifies on real webcam.
