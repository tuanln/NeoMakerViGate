"""Generate 4 background PNGs cho Photo Booth procedurally via Pillow.

Chạy: python -m neo_makervigate.experiences.exp06_photo_booth._gen_assets
Output: backgrounds/{san_dinh,luy_tre,san_fgc,sao_hoa}.png (1280x720)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ASSETS_DIR = Path(__file__).parent / "backgrounds"
WIDTH = 1280
HEIGHT = 720


def _gradient_bg(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    """Fast gradient via numpy."""
    arr = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for c in range(3):
        col = np.linspace(top[c], bottom[c], HEIGHT, dtype=np.float32)
        arr[:, :, c] = np.tile(col[:, None], (1, WIDTH)).astype(np.uint8)
    return Image.fromarray(arr)


def gen_san_dinh() -> None:
    """Sân Đình — sky blue top, brown/red ground, simplified dinh silhouette."""
    img = _gradient_bg((135, 206, 235), (139, 90, 60))
    draw = ImageDraw.Draw(img)
    draw.polygon([(440, 280), (840, 280), (640, 180)], fill=(178, 34, 34))
    draw.rectangle([(480, 280), (800, 520)], fill=(160, 100, 60))
    for x in [520, 620, 720]:
        draw.rectangle([(x, 320), (x + 30, 520)], fill=(218, 165, 32))
    draw.rectangle([(615, 400), (665, 520)], fill=(101, 67, 33))
    draw.text((40, 40), "San Dinh", fill=(255, 255, 255))
    img.save(ASSETS_DIR / "san_dinh.png")
    print(f"Wrote {ASSETS_DIR / 'san_dinh.png'}")


def gen_luy_tre() -> None:
    """Lũy Tre — green hues, vertical bamboo strokes."""
    img = _gradient_bg((180, 220, 140), (60, 130, 40))
    draw = ImageDraw.Draw(img)
    for x in range(80, WIDTH, 90):
        draw.rectangle([(x, 100), (x + 18, HEIGHT)], fill=(85, 140, 60))
        for ny in range(150, HEIGHT, 90):
            draw.rectangle([(x - 2, ny), (x + 20, ny + 4)], fill=(45, 95, 30))
    draw.text((40, 40), "Luy Tre", fill=(255, 255, 255))
    img.save(ASSETS_DIR / "luy_tre.png")
    print(f"Wrote {ASSETS_DIR / 'luy_tre.png'}")


def gen_san_fgc() -> None:
    """Sân FGC — modern store, white + orange + blue."""
    img = _gradient_bg((230, 240, 255), (200, 210, 230))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(200, 100), (1080, 600)], fill=(255, 255, 255))
    draw.rectangle([(200, 100), (1080, 200)], fill=(247, 135, 36))
    for i, color in enumerate([(0, 100, 200), (247, 135, 36), (0, 150, 80)]):
        draw.rectangle([(280 + i * 200, 130), (380 + i * 200, 170)], fill=color)
    for x in range(220, 1060, 180):
        draw.rectangle([(x, 230), (x + 160, 580)], fill=(170, 200, 230))
    draw.text((40, 40), "San FGC", fill=(50, 50, 50))
    img.save(ASSETS_DIR / "san_fgc.png")
    print(f"Wrote {ASSETS_DIR / 'san_fgc.png'}")


def gen_sao_hoa() -> None:
    """Sao Hỏa — Mars surface, red/orange terrain, dark sky with stars."""
    img = _gradient_bg((30, 10, 40), (180, 80, 40))
    draw = ImageDraw.Draw(img)
    rng = np.random.default_rng(seed=42)
    for _ in range(80):
        sx = int(rng.integers(0, WIDTH))
        sy = int(rng.integers(0, HEIGHT // 2))
        draw.ellipse([(sx, sy), (sx + 2, sy + 2)], fill=(255, 255, 255))
    horizon_y = HEIGHT // 2 + 50
    for x in range(0, WIDTH, 60):
        peak = int(rng.integers(20, 80))
        draw.polygon(
            [(x, horizon_y), (x + 30, horizon_y - peak), (x + 60, horizon_y)],
            fill=(140, 60, 30),
        )
    draw.text((40, 40), "Sao Hoa", fill=(255, 255, 255))
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
