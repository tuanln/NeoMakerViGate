# Plugin Guide — Viết một experience plugin mới

> Cập nhật P2 (2026-05-15). Áp dụng cho `experience_base.Experience` Protocol + `ExperienceManager` watchdog hiện hành.

NeoMakerViGate là một bộ thí nghiệm vision tracking, mỗi trải nghiệm (experience) là một plugin độc lập. Tài liệu này hướng dẫn sinh viên Maker thêm trải nghiệm mới mà không phải sửa core.

## TL;DR — Cấu trúc một plugin

```
src/neo_makervigate/experiences/
└── exp08_your_game/
    ├── __init__.py       # rỗng — chỉ để Python coi là package
    ├── logic.py          # class YourExperience + biến module EXPERIENCE = YourExperience
    ├── ui.qml            # giao diện game
    ├── assets/           # sprite, âm thanh, font… (optional)
    └── test_logic.py     # pytest scoring + state transitions
```

Tên thư mục **phải** match prefix `exp` để `registry.discover_experiences()` phát hiện ra, và **phải** trùng `meta.id`. Quy ước: `expNN_short_name` (NN 2 chữ số).

## 1. Viết `logic.py`

```python
# src/neo_makervigate/experiences/exp08_your_game/logic.py
from __future__ import annotations

from pathlib import Path

from neo_makervigate.core.models import ExperienceMeta, VisionFrame
from neo_makervigate.experiences.experience_base import BaseExperience

_QML_PATH = (Path(__file__).parent / "ui.qml").as_posix()


class YourExperience(BaseExperience):
    """Mô tả ngắn gameplay — 1 câu."""

    meta = ExperienceMeta(
        id="exp08_your_game",            # phải khớp tên thư mục
        title="Tên Việt",                 # hiện trên thẻ Hub
        subtitle="English Name",          # subtitle thẻ Hub
        age_min=4,
        age_max=10,
        vision_modules=("hands",),        # "hands" | "pose" | "face" | "selfie"
        needs_qwen=False,
        needs_voice=False,
        needs_internet=False,
        icon_path="",                     # path tới icon trong assets (optional)
        dev_days=3,                       # ước lượng dev solo
    )

    def __init__(self) -> None:
        super().__init__()
        self._score = 0

    def get_qml_path(self) -> str:
        return _QML_PATH

    def on_enter(self) -> None:
        """Gọi khi user chọn từ Hub. Load asset nặng ở đây."""
        self._score = 0

    def on_vision_frame(self, frame: VisionFrame) -> None:
        """Gọi mỗi frame webcam. NHẸ — phải < 500ms."""
        if frame.hands:
            # cập nhật state...
            pass

    def on_gesture(self, gesture: str) -> None:
        """Gọi khi GestureDetector phát hiện cử chỉ tên (vd "WAVE", "V_SIGN")."""
        if gesture == "WAVE":
            self._score += 1

    def on_exit(self) -> None:
        """Gọi khi user bấm Back hoặc watchdog ngắt. Dọn dẹp asset."""

    def render_state(self) -> dict[str, object]:
        """Trả state cho QML qua AppController. Đẩy mỗi vài frame, không phải mỗi frame."""
        return {"score": self._score}


EXPERIENCE = YourExperience  # ← bắt buộc, registry tìm biến này
```

### Đường tắt: `BaseExperience` là gì?

`BaseExperience` là helper class mặc định no-op mọi callback trừ `meta` và `get_qml_path()`. Nếu plugin của bạn chỉ cần Hands + scoring, override 3-4 method là đủ. Tự implement Protocol `Experience` trực tiếp cũng được nhưng phải viết đủ 7 method.

## 2. Viết `ui.qml`

```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../ui/qml/singletons" as Sing

Rectangle {
    color: Sing.NeoConstants.background

    // Bind state từ AppController:
    //   app.handLandmarks    — list[list[{x, y}]] normalized 0-1
    //   app.poseLandmarks    — list[{x, y, visibility}]
    //   app.faceLandmarks    — list[{x, y}]
    //   app.lastGesture      — str (WAVE | V_SIGN | …)
    //   app.visionFps        — float
    //   app.currentExperience — str (id plugin đang active)

    Text {
        anchors.centerIn: parent
        text: "Score: " + (app.handLandmarks.length > 0 ? "✋" : "")
        font.pixelSize: 48
        color: Sing.NeoConstants.tre
    }

    // Camera live view (nếu cần):
    Image {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: 320; height: 180
        source: "image://camera/latest?t=" + Date.now()  // bust cache
        cache: false
        fillMode: Image.PreserveAspectFit
    }
}
```

QML của plugin được load bởi `ExperienceContainerPage` qua `Loader`. Nút **← Hub** và badge **Cử chỉ** đã có sẵn ở container — không cần tự thêm.

Color palette + sizing dùng `NeoConstants` singleton (xem `ui/qml/singletons/NeoConstants.qml`): `tre`, `de`, `gach`, `song`, `background`, `surface`, `cardWidth`, `cardHeight`, `animFast`, `fontTitle`…

## 3. `vision_modules` — chọn module nào?

`ExperienceManager.load()` tự gọi `worker.set_active_modules(meta.vision_modules)`. Chỉ load module thật sự cần — tiết kiệm CPU + RAM trên NEO One ARM64 2GB.

| module    | trả gì trong `frame`                         | dùng cho                |
|-----------|----------------------------------------------|-------------------------|
| `hands`   | `frame.hands` — tới 2 tay × 21 landmarks     | exp01, gesture vẫy/V    |
| `pose`    | `frame.pose` — 33 landmarks toàn thân        | exp03 yoga, T-pose      |
| `face`    | `frame.face` — face mesh landmarks           | smile, head tilt        |
| `selfie`  | seg mask (P5) cho photo composite            | exp06 photo booth       |

## 4. Lifecycle + tín hiệu

`ExperienceManager` connect các signal sau (xem `utils/signal_bus.py`):

| SignalBus signal           | → method plugin              |
|----------------------------|------------------------------|
| `vision_frame_ready`       | `on_vision_frame(frame)`     |
| `gesture_detected`         | `on_gesture(name)`           |
| `qwen_response_ready`      | `on_qwen_response(text)`     |

Khi plugin **load**:
1. `cls()` instantiate
2. `instance.on_enter()`
3. `worker.set_active_modules(meta.vision_modules)`
4. `experience_started` signal phát đi

Khi **unload** (user Back / watchdog / crash):
1. `instance.on_exit()`
2. `experience_ended` signal phát đi với `summary` dict

## 5. Watchdog — đừng làm chậm `on_vision_frame`

`ExperienceManager` đo thời gian mỗi lần gọi `on_vision_frame()`. Nếu > **500ms** liên tiếp **6 frame**, manager tự `unload({"watchdog": True})` và quay về Hub. Quy tắc:

- **Không** mở file / network trong `on_vision_frame`.
- Tính toán nặng (Qwen, scoring AI) → đẩy vào QThread riêng hoặc gọi `signal_bus.qwen_request.emit(...)`.
- Cache kết quả landmark filter, đừng tính lại mỗi frame.

Nếu plugin raise Exception, manager log + unload({"crash": True, "error": str(e)}) — app không crash theo.

## 6. Viết `test_logic.py`

Plugin logic phải test được **không cần** QML hay webcam thật:

```python
# src/neo_makervigate/experiences/exp08_your_game/test_logic.py
from datetime import datetime
from neo_makervigate.core.models import Landmark, VisionFrame
from neo_makervigate.experiences.exp08_your_game.logic import YourExperience


def test_initial_score_zero(qapp) -> None:
    exp = YourExperience()
    exp.on_enter()
    assert exp.render_state()["score"] == 0


def test_wave_increments_score(qapp) -> None:
    exp = YourExperience()
    exp.on_enter()
    exp.on_gesture("WAVE")
    exp.on_gesture("WAVE")
    assert exp.render_state()["score"] == 2


def test_frame_without_hands_noop(qapp) -> None:
    exp = YourExperience()
    exp.on_enter()
    frame = VisionFrame(timestamp=datetime.now(), width=640, height=360)
    exp.on_vision_frame(frame)  # không crash
```

Fixture `qapp` đã có sẵn ở `tests/conftest.py` — chạy `pytest` từ root.

## 7. Đăng ký Hub

**Không cần làm gì.** `registry.discover_experiences()` scan `experiences/exp*/logic.py` lúc app boot và đăng ký mọi class có `EXPERIENCE`. Sau khi tạo thư mục + `logic.py` đúng convention, restart app là plugin xuất hiện trên Hub.

Để **tạm tắt** một plugin mà không xoá code: đổi tên thư mục thành `_expNN_…` (prefix underscore) — `startswith("exp")` filter sẽ bỏ qua.

## 8. Quy tắc nội bộ

- **KHÔNG** import từ plugin khác. Mỗi plugin độc lập, tái dùng qua `core/`, `utils/`, `services/`.
- **KHÔNG** import `QtWidgets` — toàn app dùng `QtQuick` / `QGuiApplication`.
- **KHÔNG** lưu state vào module-level global — manager re-instantiate plugin mỗi lần load.
- **CÓ THỂ** đọc file trong `assets/` từ `on_enter`, nhưng chỉ load lazy ở frame đầu nếu file > 1MB.
- Logging: dùng `loguru.logger`, không `print()`.

## 9. Smoke test plugin mới

Sau khi viết xong:

```bash
# Headless test logic
.venv/bin/python -m pytest src/neo_makervigate/experiences/exp08_your_game/test_logic.py -v

# Lint
.venv/bin/ruff check src/neo_makervigate/experiences/exp08_your_game/
.venv/bin/mypy src/neo_makervigate/experiences/exp08_your_game/

# Live test với simulator (không cần webcam)
NEO_MAKERVIGATE_VISION=simulator .venv/bin/python -m neo_makervigate
```

Tại Hub bấm vào thẻ của plugin mình → nếu lifecycle OK sẽ chuyển sang Container và load `ui.qml`.

## Tham khảo

- `experiences/exp01_wave_cricket/` — Hands + WAVE gesture (P3)
- `experiences/exp03_yoga_robot/` — Pose + cosine similarity (P4)
- `experiences/exp06_photo_booth/` — Selfie seg + Qwen caption (P6)
- `DOC/ARCHITECTURE.md` §5 — Plugin Architecture chi tiết
