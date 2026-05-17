"""Qwen 2.5-VL local client cho caption generation.

Protocol-based: dễ swap LocalBackend (llama-cpp-python) ↔ APIBackend (DashScope).
P6 chỉ implement LocalBackend.

Model: Qwen 2.5-VL-2B-Instruct quantized Q4_K_M (~1GB RAM).
"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from loguru import logger
from PIL import Image


@runtime_checkable
class QwenClient(Protocol):
    """Interface mọi backend phải implement."""

    def describe_image(
        self,
        image_path: Path,
        prompt: str,
        max_tokens: int = 80,
    ) -> str: ...

    def is_ready(self) -> bool: ...


MODELS_DIR = Path.home() / "makervigate" / "models" / "qwen"
DEFAULT_MODEL_NAME = "qwen2.5-vl-2b-instruct-q4_k_m.gguf"
DEFAULT_MMPROJ_NAME = "qwen2.5-vl-2b-instruct-mmproj-f16.gguf"
DEFAULT_CONTEXT_SIZE = 2048


class QwenLocalBackend:
    """llama-cpp-python backend chạy Qwen 2.5-VL local trên CPU.

    Model loaded lazy lần đầu describe_image() — process boot không block.
    """

    def __init__(
        self,
        model_path: Path | None = None,
        mmproj_path: Path | None = None,
        n_ctx: int = DEFAULT_CONTEXT_SIZE,
    ) -> None:
        self._model_path = model_path or (MODELS_DIR / DEFAULT_MODEL_NAME)
        self._mmproj_path = mmproj_path or (MODELS_DIR / DEFAULT_MMPROJ_NAME)
        self._n_ctx = n_ctx
        self._llm: Any = None

    def is_ready(self) -> bool:
        return self._model_path.exists() and self._mmproj_path.exists()

    def _ensure_loaded(self) -> None:
        if self._llm is not None:
            return
        if not self.is_ready():
            raise FileNotFoundError(
                f"Qwen model not found at {self._model_path}. "
                "Run: python -m neo_makervigate.scripts.download_qwen"
            )
        from llama_cpp import Llama
        from llama_cpp.llama_chat_format import Qwen25VLChatHandler

        chat_handler = Qwen25VLChatHandler(clip_model_path=str(self._mmproj_path))
        self._llm = Llama(
            model_path=str(self._model_path),
            chat_handler=chat_handler,
            n_ctx=self._n_ctx,
            n_gpu_layers=0,
            verbose=False,
        )
        logger.info(f"Qwen loaded: {self._model_path.name}")

    def describe_image(
        self,
        image_path: Path,
        prompt: str,
        max_tokens: int = 80,
    ) -> str:
        self._ensure_loaded()
        if self._llm is None:
            raise RuntimeError("Qwen model failed to load")

        img = Image.open(image_path).convert("RGB")
        img.thumbnail((512, 512))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        data_uri = f"data:image/jpeg;base64,{b64}"

        response = self._llm.create_chat_completion(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_uri}},
                    {"type": "text", "text": prompt},
                ],
            }],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        text: str = response["choices"][0]["message"]["content"].strip()
        return text
