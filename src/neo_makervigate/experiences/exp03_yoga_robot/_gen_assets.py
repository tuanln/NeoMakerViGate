"""One-shot WAV generator cho exp03 Yoga Robot.

Chạy: `.venv/bin/python -m neo_makervigate.experiences.exp03_yoga_robot._gen_assets`

Sinh 2 file:
- pose_locked.wav  — chuông xác nhận khi pose hold đủ 3s
- pose_skipped.wav — buzz nhẹ khi skip do stuck 45s
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io import wavfile

SAMPLE_RATE = 22050
ASSETS_DIR = Path(__file__).parent / "assets"


def _envelope(n: int, attack: float = 0.02, release: float = 0.3) -> np.ndarray[tuple[int], np.dtype[np.float64]]:
    env: np.ndarray[tuple[int], np.dtype[np.float64]] = np.ones(n, dtype=np.float64)
    a = int(attack * n)
    r = int(release * n)
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if r > 0:
        env[-r:] = np.linspace(1, 0, r) ** 2
    return env


def _save(name: str, signal: np.ndarray[tuple[int], np.dtype[np.float64]]) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    peak = float(np.max(np.abs(signal)))
    if peak > 0:
        signal = signal / peak * 0.8
    pcm = (signal * 32767).astype(np.int16)
    wavfile.write(ASSETS_DIR / name, SAMPLE_RATE, pcm)
    print(f"Wrote {ASSETS_DIR / name} ({len(signal) / SAMPLE_RATE:.2f}s)")


def gen_pose_locked() -> None:
    """Chuông xác nhận — ascending arpeggio C5-E5-G5 ngắn (0.45s)."""
    notes_hz = [523.25, 659.25, 783.99]
    note_dur = 0.15
    samples_per_note = int(SAMPLE_RATE * note_dur)
    parts = []
    for hz in notes_hz:
        t = np.linspace(0, note_dur, samples_per_note, endpoint=False)
        sig = np.sin(2 * np.pi * hz * t) * _envelope(samples_per_note, attack=0.01, release=0.3)
        parts.append(sig)
    signal = np.concatenate(parts)
    _save("pose_locked.wav", signal)


def gen_pose_skipped() -> None:
    """Buzz xuống tone — descending major third A4 → F4 (0.4s)."""
    duration = 0.4
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    freq_start = 440.0
    freq_end = 349.23
    freq = np.linspace(freq_start, freq_end, len(t))
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    signal = np.sin(phase) * _envelope(len(t), attack=0.01, release=0.4)
    _save("pose_skipped.wav", signal)


def main() -> None:
    gen_pose_locked()
    gen_pose_skipped()


if __name__ == "__main__":
    main()
