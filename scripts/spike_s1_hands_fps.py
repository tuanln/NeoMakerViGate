"""Spike S1 — đo FPS MediaPipe Hands trên webcam Mac.

Pass criteria: ≥30 fps ở 720p, qua 200 khung hình ổn định.

Chạy:
    .venv/bin/python scripts/spike_s1_hands_fps.py

Output:
    - In ra FPS trung bình, p50, p95, p99
    - Lưu báo cáo vào DOC/SPIKES.md (append)
    - Tự tải hand_landmarker.task nếu chưa có (~9MB)
"""

from __future__ import annotations

import statistics
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

FRAMES_TO_MEASURE = 200
WARMUP_FRAMES = 20
WEBCAM_INDEX = 0
TARGET_W, TARGET_H = 1280, 720

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)
MODEL_PATH = (
    Path(__file__).parent.parent / "models" / "mediapipe" / "hand_landmarker.task"
)


def ensure_model() -> Path:
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 1_000_000:
        return MODEL_PATH
    print(f"Downloading hand_landmarker.task → {MODEL_PATH}")
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print(f"  ↳ {MODEL_PATH.stat().st_size / 1024:.0f} KB")
    return MODEL_PATH


def main() -> int:
    print("=== Spike S1 — MediaPipe Hands FPS ===")
    print(f"Target: ≥30 fps tại {TARGET_W}x{TARGET_H}")
    print(f"Frames: {WARMUP_FRAMES} warmup + {FRAMES_TO_MEASURE} measured")
    print()

    model_path = ensure_model()

    cap = cv2.VideoCapture(WEBCAM_INDEX)
    if not cap.isOpened():
        print(f"[!] Không mở được webcam index {WEBCAM_INDEX}")
        return 1

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, TARGET_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_H)
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Webcam actual resolution: {actual_w}x{actual_h}")

    options = mp_vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=mp_vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    detector = mp_vision.HandLandmarker.create_from_options(options)

    def process_frame(frame_bgr, timestamp_ms: int):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        return detector.detect_for_video(mp_image, timestamp_ms)

    # Dùng một đồng hồ chung — timestamp_ms phải đơn điệu tăng giữa warmup + measure
    clock_start = time.perf_counter()

    def now_ms() -> int:
        return int((time.perf_counter() - clock_start) * 1000)

    # Warmup
    print(f"Warmup {WARMUP_FRAMES} frames...")
    for _ in range(WARMUP_FRAMES):
        ret, frame = cap.read()
        if not ret:
            print("[!] Webcam read fail trong warmup")
            return 1
        _ = process_frame(frame, now_ms())

    # Measure
    print(f"Measuring {FRAMES_TO_MEASURE} frames...")
    durations_ms: list[float] = []
    landmarks_detected_frames = 0
    t_start = time.perf_counter()
    for i in range(FRAMES_TO_MEASURE):
        t0 = time.perf_counter()
        ret, frame = cap.read()
        if not ret:
            print(f"[!] Webcam read fail tại frame {i}")
            break
        result = process_frame(frame, now_ms())
        t1 = time.perf_counter()
        durations_ms.append((t1 - t0) * 1000)
        if result.hand_landmarks:
            landmarks_detected_frames += 1
    total_seconds = time.perf_counter() - t_start

    cap.release()
    detector.close()

    # Stats
    avg_ms = statistics.mean(durations_ms)
    p50 = statistics.median(durations_ms)
    sorted_ms = sorted(durations_ms)
    p95 = sorted_ms[int(0.95 * len(sorted_ms))]
    p99 = sorted_ms[int(0.99 * len(sorted_ms))]
    avg_fps = 1000.0 / avg_ms
    overall_fps = len(durations_ms) / total_seconds

    print()
    print("=== Results ===")
    print(f"Frames measured:     {len(durations_ms)}")
    print(f"Total time:          {total_seconds:.2f}s")
    print(f"Overall FPS:         {overall_fps:.1f}")
    print(f"Per-frame FPS avg:   {avg_fps:.1f}")
    print(f"Per-frame ms avg:    {avg_ms:.2f}")
    print(f"Per-frame ms p50:    {p50:.2f}")
    print(f"Per-frame ms p95:    {p95:.2f}")
    print(f"Per-frame ms p99:    {p99:.2f}")
    print(
        f"Frames w/ landmarks: {landmarks_detected_frames} "
        f"({100 * landmarks_detected_frames / len(durations_ms):.0f}%)"
    )
    print()
    pass_threshold = 30.0
    verdict = "PASS" if overall_fps >= pass_threshold else "FAIL"
    print(f"Verdict: {verdict} (threshold {pass_threshold} fps)")

    # Append to SPIKES.md
    spikes_path = Path(__file__).parent.parent / "DOC" / "SPIKES.md"
    spikes_path.parent.mkdir(exist_ok=True)
    is_new_file = not spikes_path.exists()
    header = "# Spike Reports — NeoMakerViGate\n\n" if is_new_file else ""
    entry = f"""## S1 — MediaPipe Hands FPS Mac ({datetime.now().strftime("%Y-%m-%d %H:%M")})

- **Resolution:** {actual_w}x{actual_h}
- **API:** MediaPipe Tasks (HandLandmarker, VIDEO mode)
- **Frames measured:** {len(durations_ms)}
- **Overall FPS:** {overall_fps:.1f}
- **Per-frame avg ms:** {avg_ms:.2f}
- **p50 / p95 / p99 ms:** {p50:.1f} / {p95:.1f} / {p99:.1f}
- **Landmarks detected:** {100 * landmarks_detected_frames / len(durations_ms):.0f}% of frames
- **Verdict:** **{verdict}** (threshold {pass_threshold} fps)

"""
    with spikes_path.open("a", encoding="utf-8") as f:
        if header:
            f.write(header)
        f.write(entry)
    print(f"Report appended to {spikes_path}")

    return 0 if overall_fps >= pass_threshold else 2


if __name__ == "__main__":
    sys.exit(main())
