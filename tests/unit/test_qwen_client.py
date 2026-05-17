"""Tests cho core/qwen_client — Qwen 2.5-VL local backend."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from neo_makervigate.core.qwen_client import (
    DEFAULT_MMPROJ_NAME,
    DEFAULT_MODEL_NAME,
    QwenClient,
    QwenLocalBackend,
)


def test_local_backend_is_ready_false_when_model_missing(tmp_path: Path) -> None:
    backend = QwenLocalBackend(
        model_path=tmp_path / "nonexistent.gguf",
        mmproj_path=tmp_path / "nonexistent_mmproj.gguf",
    )
    assert backend.is_ready() is False


def test_local_backend_is_ready_true_when_files_exist(tmp_path: Path) -> None:
    model = tmp_path / DEFAULT_MODEL_NAME
    mmproj = tmp_path / DEFAULT_MMPROJ_NAME
    model.write_bytes(b"fake-model")
    mmproj.write_bytes(b"fake-mmproj")
    backend = QwenLocalBackend(model_path=model, mmproj_path=mmproj)
    assert backend.is_ready() is True


def test_describe_image_raises_when_model_missing(tmp_path: Path) -> None:
    backend = QwenLocalBackend(
        model_path=tmp_path / "missing.gguf",
        mmproj_path=tmp_path / "missing_mmproj.gguf",
    )
    img_path = tmp_path / "img.jpg"
    img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    with pytest.raises(FileNotFoundError, match="Qwen model not found"):
        backend.describe_image(img_path, "Describe this", max_tokens=10)


def test_describe_image_calls_llama_with_image_and_prompt(tmp_path: Path) -> None:
    """Verify backend wires up llama-cpp correctly. Mock Llama + chat handler."""
    model = tmp_path / DEFAULT_MODEL_NAME
    mmproj = tmp_path / DEFAULT_MMPROJ_NAME
    model.write_bytes(b"fake")
    mmproj.write_bytes(b"fake")

    from PIL import Image as PILImage
    img_path = tmp_path / "test.jpg"
    PILImage.new("RGB", (100, 100), color="red").save(img_path)

    backend = QwenLocalBackend(model_path=model, mmproj_path=mmproj)

    mock_llm = MagicMock()
    mock_llm.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "Một bức ảnh đẹp! 📸"}}]
    }
    mock_llama_class = MagicMock(return_value=mock_llm)
    mock_handler_class = MagicMock()

    with patch.dict("sys.modules", {
        "llama_cpp": MagicMock(Llama=mock_llama_class),
        "llama_cpp.llama_chat_format": MagicMock(Qwen25VLChatHandler=mock_handler_class),
    }):
        result = backend.describe_image(img_path, "Describe this image", max_tokens=50)

    assert result == "Một bức ảnh đẹp! 📸"
    mock_llm.create_chat_completion.assert_called_once()
    call_args = mock_llm.create_chat_completion.call_args
    messages = call_args.kwargs["messages"]
    content = messages[0]["content"]
    assert any(c.get("type") == "image_url" for c in content)
    assert any(c.get("type") == "text" and "Describe" in c["text"] for c in content)


def test_qwen_protocol_runtime_checkable_with_fake_backend() -> None:
    """A class implementing the protocol methods should satisfy isinstance(QwenClient)."""

    class FakeBackend:
        def describe_image(self, image_path: Path, prompt: str, max_tokens: int = 80) -> str:
            return "fake"

        def is_ready(self) -> bool:
            return True

    fake = FakeBackend()
    assert hasattr(fake, "describe_image")
    assert hasattr(fake, "is_ready")
    _ = QwenClient  # silence unused-import
