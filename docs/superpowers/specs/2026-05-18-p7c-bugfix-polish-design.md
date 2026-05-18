# P7c — Smoke Test Bug Fixes + UX Polish Design

**Phase:** 7c (NeoMakerViGate — post P7a webcam smoke feedback)
**Created:** 2026-05-18
**Status:** Design approved, ready for implementation plan

## Mục tiêu

Fix 3 issues phát hiện trong user smoke test webcam thật (P7a):
1. **exp03 noise** — pose detection bị nhiễu từ đồ vật, phải đứng xa cam
2. **exp06 V_SIGN không trigger** — giơ chữ V không chụp được
3. **Ảnh xấu** — composite quality + need fallback từ folder ảnh có sẵn

## Quyết định chốt với user (2026-05-18 brainstorm)

| Issue | Decision | Note |
|---|---|---|
| exp03 noise | **Redesign Face Yoga** (Face Mesh, sit close to cam) | Major: switch vision_modules pose → face |
| 5 face poses | **Cười to / Mở miệng O / Wink / Nhướng mày / Lắc đầu** | Lè lưỡi → Wink (FaceMesh không track tongue) |
| V_SIGN | **Relax FINGER_MARGIN 1.15 → 1.05** | 1-line tune, accept slight false positive |
| Photo source | **Source folder fallback** | `~/makervigate/source_photos/` admin upload |

## 1. Architecture overview

3 issues — 3 sub-changes, independent:

### A. exp03 Face Yoga (major redesign)
- `core/vision_engine.py`: enable face module in `read()` (already has `_create_detector("face")` from P1)
- `utils/face_math.py` (NEW): MAR, EAR, brow_raised_ratio, head_yaw helpers
- `experiences/exp03_yoga_robot/logic.py`: rewrite — vision_modules `("pose",)` → `("face",)`, new detector dispatcher
- `experiences/exp03_yoga_robot/poses.toml`: rewrite 5 face poses with detector + thresholds
- `experiences/exp03_yoga_robot/ui.qml`: face landmark overlay instead of pose skeleton (smaller, head area)
- `test_logic.py`: rewrite face-based

### B. exp06 V_SIGN relax
- `core/gesture_detector.py`: `V_SIGN_FINGER_MARGIN = 1.15` → `1.05`
- Existing tests still pass (synth data 2× ratio, easy margin)

### C. Photo source folder fallback
- `core/photo_capture.py`: + `list_source_photos()` + `DEFAULT_SOURCE_PHOTOS_DIR`
- `services/photo_service.py`: try live composite first, fallback to random source photo if selfie_mask missing
- `~/makervigate/source_photos/` admin loads .jpg/.png pre-prepared

## 2. exp03 Face Yoga details

### MediaPipe Face Mesh 468 landmarks — key indices

```python
# Mouth
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
```

### `utils/face_math.py` API

```python
def mouth_aspect_ratio(landmarks: list[Landmark]) -> float:
    """MAR = vertical_lip_open / horizontal_lip_width.
    Closed mouth: ~0.05. Open O: ~0.55+. Wide smile: ~0.20."""

def mouth_width_ratio(landmarks: list[Landmark]) -> float:
    """mouth_width / face_temple_width. Smile pulls corners → larger ratio.
    Neutral: ~0.35. Smile: ~0.45+."""

def eye_aspect_ratio(landmarks: list[Landmark], side: Literal["left", "right"]) -> float:
    """EAR = vertical / horizontal. Open: ~0.30. Closed: ~0.05."""

def brow_raised_ratio(landmarks: list[Landmark]) -> float:
    """(eye_top_Y - brow_Y) / face_height. Normal: ~0.05. Raised: 0.085+."""

def head_yaw(landmarks: list[Landmark]) -> float:
    """Approximation: (dist(nose, left_temple) - dist(nose, right_temple)) / face_width.
    Range -1 (full left) to +1 (full right). Forward: ~0."""
```

### `poses.toml` rewrite

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

### Detector dispatcher trong `logic.py`

```python
def _evaluate_pose(self, face: list[Landmark], target: PoseTarget) -> tuple[int, bool]:
    """Returns (score 0-100, matched bool)."""
    detector = target.detector
    th = target.thresholds
    if detector == "smile":
        mar = mouth_aspect_ratio(face)
        mwr = mouth_width_ratio(face)
        matched = mwr >= th["mouth_width_ratio_min"] and mar <= th["mar_max"]
        score = min(100, int((mwr / th["mouth_width_ratio_min"]) * 70))
    elif detector == "mouth_open":
        mar = mouth_aspect_ratio(face)
        matched = mar >= th["mar_min"]
        score = min(100, int((mar / th["mar_min"]) * 70))
    elif detector == "wink":
        ear_l = eye_aspect_ratio(face, "left")
        ear_r = eye_aspect_ratio(face, "right")
        left_winking = ear_l <= th["closed_eye_ear_max"] and ear_r >= th["open_eye_ear_min"]
        right_winking = ear_r <= th["closed_eye_ear_max"] and ear_l >= th["open_eye_ear_min"]
        matched = left_winking or right_winking
        score = 100 if matched else 30
    elif detector == "brow_raised":
        ratio = brow_raised_ratio(face)
        matched = ratio >= th["brow_raised_min"]
        score = min(100, int((ratio / th["brow_raised_min"]) * 70))
    elif detector == "head_shake":
        yaw = head_yaw(face)
        self._yaw_history.append((self._clock(), yaw))
        matched, oscillations = self._check_head_shake(th)
        score = min(100, oscillations * 33)
    else:
        matched, score = False, 0
    return score, matched
```

**Hold logic:** Giữ pose 2s liên tục (dễ hơn 3s pose-based vì face poses cố định hơn).

**`_yaw_history`** deque maxlen=60 (~2s @ 30fps) for head_shake oscillation tracking.

### `vision_modules` change

```python
meta = ExperienceMeta(
    id="exp03_yoga_robot",
    title="Yoga Robot",
    subtitle="Bắt chước 5 biểu cảm vui!",
    age_min=5,
    age_max=12,
    vision_modules=("face",),  # CHANGED from ("pose",)
    needs_qwen=False,
    needs_voice=False,
    needs_internet=False,
    icon_path="",
    dev_days=7,
)
```

## 3. V_SIGN relax + Photo source fallback

### V_SIGN relax

Single constant change `core/gesture_detector.py`:

```python
V_SIGN_FINGER_MARGIN = 1.05  # was 1.15
```

Existing tests (3) still pass — synth V-pose data has 2× tip/pip ratio, easy margin.

**Risk:** Slight false positive (OK-sign 👌 might trigger). Cooldown 0.4s prevents spam. Acceptable trade-off for detection success rate.

### Photo source folder fallback

**Setup:** `~/makervigate/source_photos/` admin uploads .jpg/.png pre-prepared photos.

**`core/photo_capture.py` extend:**

```python
DEFAULT_SOURCE_PHOTOS_DIR = Path.home() / "makervigate" / "source_photos"


def list_source_photos(source_dir: Path = DEFAULT_SOURCE_PHOTOS_DIR) -> list[Path]:
    """Liệt kê .jpg/.png trong source_photos/. Empty nếu không có."""
    if not source_dir.exists():
        return []
    return sorted(
        [p for p in source_dir.iterdir()
         if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    )
```

**`services/photo_service.py` extend `_on_capture_request`:**

After existing live composite attempt fails:

```python
# Fallback to source photo if no composite AND background provided
if composite_path is None and bg_path_str:
    source_photos = list_source_photos()
    if source_photos:
        import random
        source_pick = random.choice(source_photos)
        try:
            source_frame = cv2.imread(str(source_pick))
            if source_frame is not None:
                mask = np.ones(source_frame.shape[:2], dtype=np.float32)
                composite_path = self._capture.save_composite(
                    source_frame, mask, bg_path, photo_dir,
                )
                logger.info(f"Used source photo fallback: {source_pick.name}")
        except Exception as e:
            logger.warning(f"Source photo fallback failed: {e}")
```

**Notes:**
- Source photos assumed opaque (full mask = 1.0). If admin wants alpha/transparency, future enhancement.
- Caption (Qwen) runs on composite (live OR source) — neutral re what's in image.
- For pilot phase: admin loads 5-10 photos manually via `scp`.

## 4. File layout + Testing

### Files

```
src/neo_makervigate/
├── utils/
│   └── face_math.py                  # MỚI (~120 LOC)
├── core/
│   ├── gesture_detector.py           # SỬA: V_SIGN_FINGER_MARGIN 1.15→1.05
│   └── photo_capture.py              # SỬA: + list_source_photos
├── services/
│   └── photo_service.py              # SỬA: source folder fallback
└── experiences/exp03_yoga_robot/
    ├── logic.py                      # REWRITE: face-based (~280 LOC)
    ├── poses.toml                    # REWRITE: 5 face poses + detector + thresholds
    ├── ui.qml                        # SỬA: face landmark overlay (head area)
    └── test_logic.py                 # REWRITE: face tests (~15)

tests/unit/
├── test_face_math.py                 # MỚI (~10 tests)
├── test_gesture_detector.py          # SỬA (verify margin 1.05 still passes)
└── test_photo_service.py             # SỬA: + 2 source fallback tests

DOC/PHASES.md                         # SỬA: P7c done note
```

Total ~10-12 files, ~500 LOC.

### Test strategy (~30 new tests)

**`test_face_math.py` (~10):**
- `test_mar_open_mouth_high` (synth landmarks vertical gap → MAR ≥ 0.5)
- `test_mar_closed_mouth_low` (~0.05)
- `test_mouth_width_ratio_smile` (wide corners)
- `test_ear_open_eye_around_03`
- `test_ear_closed_eye_below_01`
- `test_brow_raised_ratio_normal_vs_raised`
- `test_head_yaw_facing_forward_zero`
- `test_head_yaw_facing_left_positive`
- `test_head_yaw_facing_right_negative`
- `test_helpers_with_short_landmarks_list_no_crash`

**`exp03/test_logic.py` REWRITE (~15):**
- Meta, intro, transitions (4 tests)
- `test_smile_pose_match_advances_after_hold`
- `test_mouth_open_pose_match`
- `test_wink_pose_match_either_side`
- `test_brow_raised_pose_match`
- `test_head_shake_oscillation_match`
- `test_no_face_keeps_pose_active`
- `test_wrong_pose_does_not_advance`
- `test_stuck_45s_skips_pose`
- `test_show_hint_at_15s`
- `test_completion_summary_face_yoga`

Helper `make_face_landmarks(scenario="smile"|"o_mouth"|"wink_left"|"brow_up"|...)` synth 468 landmarks.

**`test_gesture_detector.py` UPDATE:** Just re-run — synth V-pose has 2× ratio, still passes 1.05.

**`test_photo_service.py` UPDATE (~2):**
- `test_capture_fallback_to_source_when_no_selfie_mask`
- `test_capture_no_source_no_mask_returns_original_only`

### Smoke test manual

1. Webcam thật
2. Hub → Yoga Robot → 5 face poses (cười, há O, wink, nhướng mày, lắc đầu) — sit close to camera
3. exp06 V_SIGN — verify relax 1.05 makes V detect easier
4. `~/makervigate/source_photos/` add 1-2 .jpg → exp06 → verify fallback path if selfie module fail

### Risks

| Risk | Mitigation |
|---|---|
| Face Mesh model URL fail (like selfie P1 bug) | `ensure_model("face")` runs at exp03 first load; verify URL works post-fix |
| MAR/EAR thresholds calibrated for adults | Tunable in poses.toml after pilot |
| Head shake noise from talking | yaw_amplitude_min threshold filter (0.25 normalized) |
| Source photo PNG transparency edges | Assume opaque crops; alpha handling future |
| V_SIGN relax causes OK-sign trigger | Cooldown 0.4s; acceptable |
| `source_photos/` not user-discoverable | Document in DEPLOY_NEO_ONE.md + TEACHER_MANUAL.md (P7c also updates) |
| head_shake unbounded yaw history | deque maxlen=60 |

## 5. Out of scope

- Tongue detection — replaced by Wink
- Multi-face support — first face only
- Source photo admin upload UI — manual scp for pilot
- Source photo auto-mask (selfie seg on source) — assume opaque
- Live mouth/eye preview overlay — pose card text enough
- Per-age threshold tuning — fixed MVP
- Configurable head_shake sensitivity per child — fixed
- Source photo metadata (caption hints, age tags) — future

---

Liên quan: [[2026-05-16-p4-yoga-robot-design]] (previous body-based exp03 superseded), [[2026-05-17-p6-photo-booth-qwen-design]] (V_SIGN current), [[2026-05-16-p5-photo-share-design]] (PhotoCapture extension).
