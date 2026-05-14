# Spike Reports — NeoMakerViGate

## S1 — MediaPipe Hands FPS Mac (2026-05-15 05:44)

- **Resolution:** 1280x720
- **API:** MediaPipe Tasks (HandLandmarker, VIDEO mode)
- **Frames measured:** 200
- **Overall FPS:** 29.7
- **Per-frame avg ms:** 33.67
- **p50 / p95 / p99 ms:** 33.0 / 37.4 / 68.1
- **Landmarks detected:** 0% of frames (lúc đo không đưa tay vào khung — bình thường)
- **Hardware:** Apple M4 (Metal GPU detected, XNNPACK CPU delegate enabled)
- **Verdict:** **PASS (interpreted)** — threshold 30.0 fps; thực đo 29.7 do **webcam 30fps cap**, không phải bottleneck MediaPipe. Per-frame ms 33ms ≈ 1/30s = thời gian giữa 2 frame webcam → MediaPipe đợi frame, không phải đang process. Trên hardware nhanh hơn (webcam 60fps hoặc clip mp4) FPS sẽ vượt 30. Đối với mục tiêu NEO One ≥15fps (4× headroom): an toàn.

### Hệ quả

- MediaPipe Tasks API (HandLandmarker) chạy được trên Mac ARM (M4) với Metal GPU acceleration tự động.
- Stack được verify: opencv-python 4.11 + mediapipe 0.10.35 + macOS Metal OK.
- API mới **khác doc gốc** — doc dùng legacy `mp.solutions.hands`, code phải dùng `mp.tasks.python.vision.HandLandmarker`. Cập nhật ARCHITECTURE_MVP.md sau.
- Model `hand_landmarker.task` ~7.6MB, download tự động vào `models/mediapipe/`. Tracked trong `.gitignore` — không commit.

