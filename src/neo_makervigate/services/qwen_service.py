"""QwenService — QThread wrapper for QwenClient.

Listens: SignalBus.qwen_request_started(dict)
Emits:   SignalBus.qwen_response_ready(str) — caption text
         SignalBus.qwen_failed(str) — error message

Inference can take 4-8s; QThread keeps UI responsive.
"""

from __future__ import annotations

import queue
from pathlib import Path
from typing import Any

from loguru import logger
from PyQt6.QtCore import QThread

from neo_makervigate.core.qwen_client import QwenClient
from neo_makervigate.utils.signal_bus import SignalBus


class _QwenWorker(QThread):
    """Background thread chạy inference."""

    def __init__(self, client: QwenClient) -> None:
        super().__init__()
        self._client = client
        self._queue: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self._running = False

    def enqueue(self, request: dict[str, Any]) -> None:
        self._queue.put(request)

    def stop(self) -> None:
        self._running = False
        self._queue.put(None)
        self.wait(3000)

    def run(self) -> None:
        self._running = True
        bus = SignalBus.instance()
        while self._running:
            item = self._queue.get()
            if item is None:
                break
            try:
                image_path = Path(str(item["image_path"]))
                prompt = str(item["prompt"])
                max_tokens = int(item.get("max_tokens", 80))
                text = self._client.describe_image(image_path, prompt, max_tokens)
                bus.qwen_response_ready.emit(text)
            except Exception as e:
                logger.exception(f"Qwen inference failed: {e}")
                bus.qwen_failed.emit(str(e))


class QwenService:
    """Facade — instantiate at app boot, holds reference to QThread worker."""

    def __init__(self, client: QwenClient) -> None:
        self._client = client
        self._worker = _QwenWorker(client)
        self._worker.start()
        SignalBus.instance().qwen_request_started.connect(self._on_request)

    def _on_request(self, params: object) -> None:
        if not isinstance(params, dict):
            logger.warning(f"QwenService: invalid params type {type(params)}")
            return
        self._worker.enqueue(dict(params))

    def stop(self) -> None:
        self._worker.stop()
