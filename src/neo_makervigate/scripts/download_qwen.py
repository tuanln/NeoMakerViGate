"""Download Qwen 2.5-VL-2B GGUF model files for local inference.

Usage: python -m neo_makervigate.scripts.download_qwen
Downloads to ~/makervigate/models/qwen/ (~1.5GB total).
"""

from __future__ import annotations

import urllib.request

from loguru import logger

from neo_makervigate.core.qwen_client import (
    DEFAULT_MMPROJ_NAME,
    DEFAULT_MODEL_NAME,
    MODELS_DIR,
)

URLS = {
    DEFAULT_MODEL_NAME: (
        "https://huggingface.co/bartowski/Qwen2.5-VL-2B-Instruct-GGUF/"
        "resolve/main/Qwen2.5-VL-2B-Instruct-Q4_K_M.gguf"
    ),
    DEFAULT_MMPROJ_NAME: (
        "https://huggingface.co/bartowski/Qwen2.5-VL-2B-Instruct-GGUF/"
        "resolve/main/mmproj-Qwen2.5-VL-2B-Instruct-f16.gguf"
    ),
}


def main() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in URLS.items():
        out = MODELS_DIR / name
        if out.exists():
            logger.info(f"Already exists: {out.name} ({out.stat().st_size // 1024 // 1024} MB)")
            continue
        logger.info(f"Downloading {name}...")
        logger.info(f"  from {url}")
        logger.info(f"  to   {out}")
        urllib.request.urlretrieve(url, out)
        logger.info(f"  done: {out.stat().st_size // 1024 // 1024} MB")
    logger.info("All Qwen models ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
