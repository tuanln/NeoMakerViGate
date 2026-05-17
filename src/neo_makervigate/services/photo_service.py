"""PhotoService — orchestrate flow chụp ảnh + sinh QR.

Listens: SignalBus.photo_capture_requested(dict)
Emits: SignalBus.photo_captured(PhotoResult)

Sequence:
  1. Lấy frame từ VisionWorker.latest_frame_bgr (P1 API)
  2. PhotoCapture: tạo photo_id + folder + lưu original.jpg
  3. ShareService: build URL + sinh qr.png
  4. LRU cleanup nếu storage > 200MB
  5. emit photo_captured(PhotoResult)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from neo_makervigate.core.models import PhotoResult
from neo_makervigate.core.photo_capture import DEFAULT_PHOTOS_DIR, PhotoCapture
from neo_makervigate.utils.signal_bus import SignalBus
from neo_makervigate.utils.storage import cleanup_if_over_limit

if TYPE_CHECKING:
    from neo_makervigate.core.vision_worker import VisionWorker
    from neo_makervigate.services.share_service import ShareService


class PhotoService:
    def __init__(
        self,
        worker: VisionWorker,
        share: ShareService,
        photos_base: Path = DEFAULT_PHOTOS_DIR,
    ) -> None:
        self._worker = worker
        self._share = share
        self._photos_base = photos_base
        self._capture = PhotoCapture(base_dir=photos_base)
        SignalBus.instance().photo_capture_requested.connect(self._on_capture_request)

    def _on_capture_request(self, params: object) -> None:
        if isinstance(params, dict):
            exp_id_raw = params.get("experience_id", "")
            experience_id = str(exp_id_raw) if exp_id_raw is not None else ""
        else:
            experience_id = ""
        bus = SignalBus.instance()
        frame = self._worker.latest_frame_bgr
        if frame is None:
            logger.warning("PhotoService: no frame available")
            bus.photo_captured.emit(PhotoResult(
                success=False,
                photo_id="",
                experience_id=experience_id,
                error_message="No webcam frame available",
            ))
            return

        try:
            photo_id = self._capture.make_photo_id(experience_id)
            photo_dir = self._capture.make_photo_dir(photo_id)
            original_path = self._capture.save_original(frame, photo_dir)

            # Optional composite (P6 — exp06 Photo Booth)
            composite_path: Path | None = None
            bg_path_str = params.get("background_path") if isinstance(params, dict) else None
            if bg_path_str:
                bg_path = Path(str(bg_path_str))
                latest_vf = getattr(self._worker, "latest_vision_frame", None)
                if latest_vf is not None and getattr(latest_vf, "selfie_mask", None) is not None:
                    try:
                        composite_path = self._capture.save_composite(
                            frame, latest_vf.selfie_mask, bg_path, photo_dir,
                        )
                    except Exception as e:
                        logger.warning(f"Composite failed, falling back to original: {e}")
                else:
                    logger.warning("background_path provided but no selfie_mask available")

            filename = "composite.jpg" if composite_path is not None else "original.jpg"
            url = self._share.make_share_url(photo_id, filename=filename)
            qr_path = self._share.make_qr(url, photo_dir)
            cleanup_if_over_limit(self._photos_base)

            result = PhotoResult(
                success=True,
                photo_id=photo_id,
                original_path=original_path,
                composite_path=composite_path,
                qr_path=qr_path,
                download_url=url,
                experience_id=experience_id,
            )
            logger.info(f"Photo captured: {photo_id} → {url}")
            bus.photo_captured.emit(result)
        except Exception as e:
            logger.exception(f"PhotoService capture failed: {e}")
            bus.photo_captured.emit(PhotoResult(
                success=False,
                photo_id="",
                experience_id=experience_id,
                error_message=str(e),
            ))
