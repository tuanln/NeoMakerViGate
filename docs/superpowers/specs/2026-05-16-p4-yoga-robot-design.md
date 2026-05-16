# P4 — exp03 Yoga Robot Design

**Phase:** 4 (NeoMakerViGate — pose-based gameplay)
**Plugin id:** `exp03_yoga_robot`
**Created:** 2026-05-16
**Status:** Design approved, ready for implementation plan

## Mục tiêu

Game pose-tracking thứ hai: trẻ bắt chước 5 tư thế yoga theo phong cách robot. MediaPipe Pose 33 landmarks → joint-angle scoring → hold 3s → next pose → tổng kết. Chứng minh kiến trúc plugin generalize sang Pose module (sau Hands ở P3).

## Quyết định thiết kế chốt với user (2026-05-16 brainstorm)

| Quyết định | Lựa chọn | Lý do |
|---|---|---|
| 5 poses | Classic: T / Tree / Star / Y / Cactus | Kid-friendly, dễ detect, khác biệt rõ qua góc khớp |
| Matching algorithm | Joint-angle similarity (6-8 góc) | Robust với scale + vị trí, dễ test với mock landmarks |
| Hold UX | Bar progress + happy-face robot 😐→🙂→😄 | Tín hiệu rõ + vui cho trẻ |
| Stuck handling | Hint ở 15s + skip ở 45s | Mềm hơn, không bỏ trẻ stuck |
| Camera/overlay | Mirror cam + Canvas skeleton (giống P3) | Reuse pattern, code nhanh |

## 1. Architecture overview

```
VisionWorker (QThread)
    → webcam → MediaPipe Pose (33 landmarks)
        → SignalBus.vision_frame_ready
            ├→ GestureDetector.feed (existing từ P3)
            ├→ ExperienceManager._on_vision_frame
            │       └→ instance.on_vision_frame(frame)
            │              [YogaRobotExperience: extract angles,
            │               compute score, advance state machine]
            └→ AppController.QTimer (30Hz)
                    → instance.render_state() → experienceState dict
                        → QML binding update

ExperienceManager.load("exp03_yoga_robot")
    → set_active_modules(["pose"])     # switch từ Hands → Pose
    → instance.on_enter()
```

**Module mới:**
- `utils/landmark_math.py` (~80 LOC) — joint angle math + pose similarity scoring
- `experiences/exp03_yoga_robot/logic.py` (rewrite, ~300 LOC) — YogaRobotExperience
- `experiences/exp03_yoga_robot/ui.qml` (rewrite, ~250 LOC) — game UI
- `experiences/exp03_yoga_robot/poses.toml` — 5 pose definitions
- `experiences/exp03_yoga_robot/test_logic.py` — ~12 tests
- `experiences/exp03_yoga_robot/_gen_assets.py` + `assets/pose_locked.wav` + `assets/pose_skipped.wav`
- `tests/unit/test_landmark_math.py` — ~8 tests

**Module reused:**
- `core/vision_engine.py` `set_active_modules(["pose"])` — đã implement ở P1
- `core/gesture_detector.py` — không cần extend (T_POSE detection YAGNI; YogaRobotExperience tự compute pose match)
- `services/app_controller.py` — `experienceState` + 30Hz polling từ P3
- `services/experience_manager.py` — auto-unload trên Phase.DONE từ P3

## 2. Poses + matching algorithm

**poses.toml** (loaded khi `on_enter`):

```toml
[[poses]]
id = "T_POSE"
title = "Chữ T"
emoji = "✝️"
subtitle = "Dang tay sang ngang như chữ T"
[poses.angles]
left_shoulder = 90
right_shoulder = 90
left_elbow = 180
right_elbow = 180
left_hip = 180
right_hip = 180
[poses.tolerance]
shoulder = 20
elbow = 15
hip = 15

[[poses]]
id = "TREE_POSE"
title = "Cây Đứng"
emoji = "🌳"
subtitle = "Co 1 chân, tay giơ lên trời"
[poses.angles]
left_shoulder = 170
right_shoulder = 170
left_elbow = 160
right_elbow = 160
left_hip = 180
right_hip = 90
left_knee = 180
right_knee = 45
[poses.tolerance]
shoulder = 25
elbow = 25
hip = 25
knee = 30

[[poses]]
id = "STAR_POSE"
title = "Ngôi Sao"
emoji = "⭐"
subtitle = "Dang tay + chân như chữ X"
[poses.angles]
left_shoulder = 135
right_shoulder = 135
left_elbow = 180
right_elbow = 180
left_hip = 135
right_hip = 135
[poses.tolerance]
shoulder = 20
elbow = 15
hip = 20

[[poses]]
id = "Y_POSE"
title = "Chữ Y"
emoji = "🙌"
subtitle = "Hai tay giơ lên thành chữ V"
[poses.angles]
left_shoulder = 160
right_shoulder = 160
left_elbow = 175
right_elbow = 175
left_hip = 180
right_hip = 180
[poses.tolerance]
shoulder = 20
elbow = 15
hip = 15

[[poses]]
id = "CACTUS_POSE"
title = "Xương Rồng"
emoji = "🌵"
subtitle = "Tay co 90° hai bên đầu"
[poses.angles]
left_shoulder = 90
right_shoulder = 90
left_elbow = 90
right_elbow = 90
left_hip = 180
right_hip = 180
[poses.tolerance]
shoulder = 20
elbow = 20
hip = 15
```

**Algorithm (`utils/landmark_math.py`):**

```python
def compute_joint_angle(a: Landmark, b: Landmark, c: Landmark) -> float:
    """Góc tại b giữa hai đoạn ba và bc. Trả về độ (0-180)."""
    # v1 = a - b, v2 = c - b
    # cos = (v1·v2) / (|v1| |v2|)
    # return degrees(acos(clamp(cos, -1, 1)))

def extract_pose_angles(landmarks: list[Landmark]) -> dict[str, float]:
    """8 joint angles từ MediaPipe Pose 33 landmarks.

    MediaPipe Pose indices:
        SHOULDER_L=11, SHOULDER_R=12
        ELBOW_L=13, ELBOW_R=14
        WRIST_L=15, WRIST_R=16
        HIP_L=23, HIP_R=24
        KNEE_L=25, KNEE_R=26
        ANKLE_L=27, ANKLE_R=28

    Returns dict với keys: {left|right}_{shoulder|elbow|hip|knee}.
    """

def pose_similarity_score(
    current: dict[str, float],
    target: dict[str, float],
    tolerance: dict[str, float],  # keys: shoulder/elbow/hip/knee
) -> float:
    """Score 0-100. Mỗi joint:
        diff = abs(current[joint] - target[joint])
        group = joint.split("_")[1]  # "shoulder" | "elbow" | "hip" | "knee"
        joint_score = max(0, 100 - 100 * diff / (2 * tolerance[group]))
    Return mean over all keys in target.
    """
```

**Thresholds (module constants, tunable):**

```python
MATCH_THRESHOLD = 65          # score >= 65 → "matching"
HOLD_REQUIRED_SEC = 3.0       # phải giữ score >= threshold trong 3s liên tục
MATCH_GAP_TOLERANCE = 0.3     # cho phép gap 0.3s không match mà không reset hold
HINT_AFTER_SEC = 15.0         # sau 15s chưa match → hiện hint silhouette
SKIP_AFTER_SEC = 45.0         # sau 45s → bỏ qua pose, ghi 0 điểm
```

## 3. Game state machine + entity

**Phases:**

```
INTRO (2s) → POSING (max 45s × 5 = 225s) → RESULT (3s) → DONE → auto-unload
```

- **INTRO**: banner "Bắt chước Robot 5 tư thế!" + preview 5 emojis. Pose detection chưa active.
- **POSING**: chia thành 5 sub-attempts (pose_index 0-4). Mỗi pose tối đa 45s.
  - Sub-state `WAITING`: score < threshold. UI hiện target card + bar = 0.
  - Sub-state `MATCHING`: score ≥ threshold. Hold bar tăng dần.
  - Hold đạt 3s liên tục → pose hoàn thành, ghi `final_score = max_score_seen`, advance.
  - 45s không match → skip với `final_score = 0`.
  - 15s không match → bật `show_hint = True` cho UI hiện silhouette gợi ý.
- **RESULT** (3s): hiện tổng điểm 0-500 + best pose.
- **DONE**: emit completion → ExperienceManager auto-unload (từ P3).

**Dataclasses:**

```python
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
    target_angles: dict[str, float]
    tolerance: dict[str, float]

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
```

**`on_vision_frame` logic:**

```python
def on_vision_frame(self, frame):
    now = self._clock()
    self._step_phase(now)
    if self._phase != Phase.POSING or not frame.pose:
        self._last_step_at = now
        return

    angles = extract_pose_angles(frame.pose)
    target = self._poses[self._pose_index]
    score = pose_similarity_score(angles, target.target_angles, target.tolerance)
    attempt = self._current_attempt
    attempt.max_score_seen = max(attempt.max_score_seen, int(score))
    self._current_score = int(score)

    elapsed = now - attempt.started_at
    dt = now - self._last_step_at

    if score >= MATCH_THRESHOLD:
        if (attempt.last_match_at is not None
                and now - attempt.last_match_at <= MATCH_GAP_TOLERANCE):
            attempt.hold_progress += dt
        elif attempt.last_match_at is None:
            attempt.hold_progress = dt  # start fresh
        else:
            attempt.hold_progress = dt  # gap too big, restart
        attempt.last_match_at = now
        if attempt.hold_progress >= HOLD_REQUIRED_SEC:
            attempt.matched_complete = True
            attempt.final_score = attempt.max_score_seen
            self._advance_to_next_pose(now)
    else:
        if (attempt.last_match_at is not None
                and now - attempt.last_match_at > MATCH_GAP_TOLERANCE):
            attempt.hold_progress = 0.0
            attempt.last_match_at = None

    # Stuck check (only if not already complete)
    if not attempt.matched_complete and elapsed >= SKIP_AFTER_SEC:
        attempt.skipped = True
        attempt.final_score = 0
        self._advance_to_next_pose(now)

    self._last_step_at = now
```

**Scoring:**
- Mỗi pose: `final_score` = max score observed trong attempt (0-100), hoặc 0 nếu skip.
- Total: sum 5 pose scores = 0-500.
- Best pose: pose có `final_score` cao nhất.

## 4. Data flow + render_state schema + UI

**`render_state()` schema:**

```python
{
    "phase": "intro" | "posing" | "result" | "done",
    "elapsed_in_phase": float,
    "pose_index": int,                 # 0-4 trong POSING
    "pose_count": 5,
    "current_pose": {                  # None khi không POSING
        "id": "T_POSE",
        "title": "Chữ T",
        "emoji": "✝️",
        "subtitle": "Dang tay sang ngang như chữ T",
        "target_angles": dict[str, float],
    } | None,
    "score": int,                      # current frame 0-100
    "max_score_in_attempt": int,
    "match_threshold": 65,
    "hold_progress": float,            # 0.0-3.0
    "hold_required": 3.0,
    "elapsed_in_pose": float,
    "show_hint": bool,                 # True khi elapsed_in_pose >= 15
    "stuck_skip_at": 45.0,
    "completed_poses": [               # poses xong (đầy đủ hoặc skipped)
        {"id": "T_POSE", "final_score": 87, "skipped": False},
        ...
    ],
    "total_score": int,
    "best_pose_id": str | None,
    "pose_landmarks_present": bool,    # cho UI fallback khi không thấy người
}
```

**QML UI layout (`ui.qml`):**

- Camera mirror background (Image + Scale flip, reuse P3 pattern, 33Hz refresh Timer)
- Canvas pose skeleton overlay — 33 landmarks + ~25 connection lines (shoulder-elbow-wrist, hip-knee-ankle, spine, torso edges)
- Pose card top center: emoji 80px + title 36px + subtitle 18px
- Bottom HUD:
  - Robot face widget (left): 😐 (score<40) / 🙂 (40-64) / 😄 (≥65), font 96px
  - Hold progress bar (right): Rectangle với width binding to `hold_progress / hold_required * 100%`, color tween green→orange theo progress
  - Score number realtime
- Intro overlay: full-screen Rectangle với 5 emoji preview row + "Sẵn sàng nhé..."
- Hint overlay (visible khi `show_hint = True`): semi-transparent Rectangle với silhouette pose target được vẽ từ `target_angles` (Canvas lines)
- Result overlay: total score + best pose card
- Audio: SoundEffect cho pose_locked (mỗi pose complete), pose_skipped (mỗi skip), end_fanfare (reuse từ exp01)

## 5. File layout + Testing strategy

**File layout:**

```
src/neo_makervigate/
├── utils/
│   └── landmark_math.py             # MỚI
├── experiences/exp03_yoga_robot/
│   ├── __init__.py                  # giữ
│   ├── logic.py                     # REWRITE
│   ├── ui.qml                       # REWRITE
│   ├── poses.toml                   # MỚI
│   ├── test_logic.py                # MỚI
│   ├── _gen_assets.py               # MỚI
│   └── assets/
│       ├── pose_locked.wav          # MỚI
│       └── pose_skipped.wav         # MỚI

tests/unit/
└── test_landmark_math.py            # MỚI

DOC/PHASES.md                        # mark P4 done cuối phase
```

**Testing strategy (TDD):**

### `tests/unit/test_landmark_math.py` (~8 tests)

```python
def test_compute_joint_angle_straight_line_returns_180()
def test_compute_joint_angle_right_angle_returns_90()
def test_compute_joint_angle_acute_45()
def test_compute_joint_angle_degenerate_zero_length_returns_180()
def test_extract_pose_angles_returns_8_joint_keys()
def test_extract_pose_angles_t_pose_match()
def test_pose_similarity_score_perfect_match_returns_100()
def test_pose_similarity_score_off_by_2tol_returns_around_0()
def test_pose_similarity_score_off_by_tol_returns_around_50()
```

Helper `make_pose_landmarks(angles_dict, scale=1.0)` sinh 33 landmark coords từ angle spec.

### `experiences/exp03_yoga_robot/test_logic.py` (~12 tests)

```python
def test_meta_correct()
def test_initial_phase_is_intro()
def test_poses_toml_loaded_5_poses()
def test_intro_transitions_to_posing_after_2s()
def test_posing_starts_at_pose_index_0()
def test_no_match_keeps_pose_active()
def test_match_increments_hold_progress()
def test_match_lost_resets_hold_progress_after_gap_tolerance()
def test_match_held_3s_advances_to_next_pose()
def test_stuck_45s_skips_pose_with_score_0()
def test_show_hint_true_at_15s()
def test_all_5_poses_completed_transitions_to_result()
def test_total_score_sums_pose_scores()
def test_best_pose_id_is_max()
def test_completion_summary_has_total_score()
def test_render_state_schema_complete()
```

Time control via `FakeClock`. Landmark inputs via `make_pose_landmarks()` helper.

### Smoke test thủ công

1. `python -m neo_makervigate` → vào exp03
2. Splash → Hub → click thẻ Yoga Robot
3. Intro 2s — preview 5 emojis ✓
4. Pose 1 (Chữ T): đứng tay ngang → robot face 😐→🙂→😄, hold bar tăng → 3s → pose_locked sfx → pose 2
5. Pose 2 (Cây): khó hơn → đợi 15s thấy hint silhouette
6. Pose 3-5: tương tự
7. Result: tổng điểm 0-500 + best pose
8. Auto về Hub sau 3s
9. Vào lại exp03 — không leak

**Verify:**
- `set_active_modules(["pose"])` switch từ Hands → Pose, model lazy-load < 1s
- FPS gameplay ≥ 30 trên Mac M4
- Hub → Yoga → Hub 5 lần không leak (tracemalloc)

### Exit criteria mapping

| PHASES.md §P4 criteria | Cách verify |
|---|---|
| Cosine similarity unit test pass với mock landmarks | `test_landmark_math.py` — 9 tests cho compute_joint_angle, extract, score |
| `set_active_modules` Hands→Pose mượt < 1s | Smoke test: thời gian từ click Yoga đến frame Pose đầu tiên |
| Game hoàn thành 5 pose không crash | Smoke test: full playthrough |

(Note: spec dùng joint-angle similarity chứ không phải cosine — quyết định chốt trong brainstorm dựa trên robustness. Test name có thể đổi thành "joint angle similarity" cho khớp implementation.)

## 6. Risk + mitigation

| Risk | Mitigation |
|---|---|
| Mock landmarks khó test joint angles chính xác | `make_pose_landmarks(angles_dict)` sinh tọa độ chuẩn từ spec; round-trip test verify |
| Pose model lazy-load delay khi switch experience | Pre-warm trong `on_enter()` qua dummy `detect_for_video()` — không block UI |
| Tỷ lệ cơ thể trẻ vs người lớn → angle sai | Joint angles độc lập scale (chỉ 3 điểm), không cần normalize toàn pose |
| MediaPipe Pose fail detect ở viền frame | Plugin handle `frame.pose == []` (no-op score), không crash |
| 45s skip có thể quá ngắn cho trẻ nhỏ | Tunable constant trong logic.py, điều chỉnh sau pilot |
| Hold bar ngắn 3s có thể chưa kịp với trẻ chậm | Tunable constant, có thể nới lên 5s |

## 7. Out of scope

- **T_POSE discrete gesture trong GestureDetector** — YAGNI cho P4 (YogaRobotExperience tự compute pose match). Có thể thêm ở phase sau nếu cần.
- **Pose ghost overlay nâng cao** — Section 4 mô tả hint silhouette qua Canvas lines vẽ từ target_angles. Không cần SVG/PNG asset.
- **Animated transitions giữa các pose** — không. Just instant swap.
- **Difficulty levels** — fixed thresholds cho MVP.
- **Per-pose audio cue khác nhau** — 1 file pose_locked.wav cho mọi pose, 1 file pose_skipped.wav cho mọi skip.
- **Save best score local** — không (consistent với exp01).
- **NEO One ARM perf tuning** — P7.

---

Liên quan: [[2026-05-15-p3-wave-cricket-design]] — reuse pattern Python-driven gameplay + AppController polling.
