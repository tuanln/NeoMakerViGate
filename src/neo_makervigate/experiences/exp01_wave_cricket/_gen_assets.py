"""One-shot generator cho WAV assets exp01.

Chạy: `.venv/bin/python -m neo_makervigate.experiences.exp01_wave_cricket._gen_assets`

Sinh procedurally bằng numpy để không phụ thuộc asset ngoài + reproducible.
Commit cả script này + 3 file WAV để repo self-contained.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io import wavfile

SAMPLE_RATE = 22050
ASSETS_DIR = Path(__file__).parent / "assets"


def _envelope(n: int, attack: float = 0.05, release: float = 0.3) -> np.ndarray[tuple[int], np.dtype[np.float64]]:
    """Linear attack + exponential release envelope."""
    env = np.ones(n)
    a = int(attack * n)
    r = int(release * n)
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if r > 0:
        env[-r:] = np.linspace(1, 0, r) ** 2
    return env


def _save(name: str, signal: np.ndarray[tuple[int], np.dtype[np.float64]]) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    # Normalize to int16 range
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.8
    pcm = (signal * 32767).astype(np.int16)
    wavfile.write(ASSETS_DIR / name, SAMPLE_RATE, pcm)
    print(f"Wrote {ASSETS_DIR / name} ({len(signal) / SAMPLE_RATE:.2f}s)")


def gen_cricket_chirp() -> None:
    """Tiếng dế ríu rít — burst 3 chirp ngắn."""
    duration = 0.6
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # Chirp: 2.8kHz + 3.2kHz mix
    chirp = 0.5 * np.sin(2 * np.pi * 2800 * t) + 0.5 * np.sin(2 * np.pi * 3200 * t)
    # Amplitude modulation 30Hz để giống cánh dế
    am = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 30 * t))
    signal = chirp * am * _envelope(len(t), attack=0.02, release=0.4)
    _save("cricket_chirp.wav", signal)


def gen_score_ting() -> None:
    """Ting score — bell-like."""
    duration = 0.4
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # Bell: 880Hz + 1760Hz + 2640Hz harmonics, exp decay
    decay = np.exp(-4 * t)
    signal = (
        0.6 * np.sin(2 * np.pi * 880 * t)
        + 0.3 * np.sin(2 * np.pi * 1760 * t)
        + 0.1 * np.sin(2 * np.pi * 2640 * t)
    ) * decay
    signal *= _envelope(len(t), attack=0.005, release=0.5)
    _save("score_ting.wav", signal)


def gen_end_fanfare() -> None:
    """Fanfare kết thúc — 3 nốt arpeggio C5-E5-G5."""
    notes_hz = [523.25, 659.25, 783.99]  # C5, E5, G5
    note_dur = 0.25
    samples_per_note = int(SAMPLE_RATE * note_dur)
    parts = []
    for hz in notes_hz:
        t = np.linspace(0, note_dur, samples_per_note, endpoint=False)
        sig = np.sin(2 * np.pi * hz * t) * _envelope(samples_per_note, attack=0.02, release=0.3)
        parts.append(sig)
    signal = np.concatenate(parts)
    # Add final sustain on G5
    t_sus = np.linspace(0, 0.5, int(SAMPLE_RATE * 0.5), endpoint=False)
    sus = (
        np.sin(2 * np.pi * 783.99 * t_sus)
        * _envelope(len(t_sus), attack=0.01, release=0.7)
    )
    signal = np.concatenate([signal, sus])
    _save("end_fanfare.wav", signal)


def main() -> None:
    gen_cricket_chirp()
    gen_score_ting()
    gen_end_fanfare()


if __name__ == "__main__":
    main()
