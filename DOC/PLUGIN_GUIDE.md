# Plugin Guide — Viết một experience plugin mới

> **Phase 2 deliverable** — tài liệu này hoàn thiện ở P2. Phase 0 chỉ là placeholder.

## TL;DR

```
src/neo_makervigate/experiences/
└── exp08_your_game/
    ├── __init__.py       # rỗng
    ├── logic.py          # class YourExperience + biến EXPERIENCE = YourExperience
    ├── ui.qml            # giao diện game
    ├── assets/           # sprite, âm thanh
    └── test_logic.py     # pytest scoring + state transitions
```

## Checklist tối thiểu

1. `logic.py` export `EXPERIENCE` là class implement `experience_base.Experience` Protocol
2. `meta.id` = tên thư mục (vd `"exp08_your_game"`)
3. `meta.vision_modules` chỉ liệt kê module thực sự cần (tránh full Pose nếu chỉ cần Hands)
4. `ui.qml` chỉ phụ thuộc QML singletons + properties expose qua `render_state()`
5. `test_logic.py` test ít nhất scoring + state khi không có vision input

Chi tiết đầy đủ sẽ viết ở P2 sau khi `experience_base.Experience` ổn định.
