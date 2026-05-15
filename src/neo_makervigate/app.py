"""Phase 1 app — QApplication + QML + Vision pipeline.

Boot sequence:
    1. setup logging + load settings
    2. init SignalBus
    3. choose VisionSource (engine or simulator) from settings.vision_source
    4. start VisionWorker (QThread) — emits via SignalBus
    5. create AppController, expose to QML as context property `app`
    6. install CameraImageProvider
    7. load MainWindow.qml
    8. exec event loop
    9. on exit: stop worker, release webcam
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine

from neo_makervigate import __version__
from neo_makervigate.config.settings import load_settings
from neo_makervigate.core.vision_engine import VisionEngine, VisionSource
from neo_makervigate.core.vision_simulator import VisionSimulator
from neo_makervigate.core.vision_worker import VisionWorker
from neo_makervigate.experiences.registry import discover_experiences
from neo_makervigate.services.app_controller import AppController
from neo_makervigate.services.experience_manager import ExperienceManager
from neo_makervigate.ui.image_provider import CameraImageProvider
from neo_makervigate.utils.logging_config import setup_logging
from neo_makervigate.utils.signal_bus import SignalBus

QML_ROOT = Path(__file__).parent / "ui" / "qml"


def _create_vision_source(source_type: str) -> VisionSource:
    if source_type == "simulator":
        logger.info("Using VisionSimulator (no webcam)")
        return VisionSimulator(width=1280, height=720)
    logger.info("Using VisionEngine (real webcam)")
    return VisionEngine(webcam_index=0, width=1280, height=720)


def run(argv: list[str]) -> int:
    setup_logging()
    logger.info(f"NeoMakerViGate v{__version__} starting")

    settings = load_settings()
    logger.info(
        f"Config: app={settings.app_name} vision_source={settings.vision_source} "
        f"experiences={settings.enabled_experiences}"
    )

    bus = SignalBus.instance()
    _ = bus  # keep ref

    app = QGuiApplication(argv)
    app.setApplicationName("NeoMakerViGate")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Maker Viet x De Foundation")

    # Vision pipeline
    source = _create_vision_source(settings.vision_source)
    worker = VisionWorker(source, initial_modules=["hands"])

    # Experience plugin registry + manager
    registry = discover_experiences()
    logger.info(f"Discovered {len(registry)} experience plugin(s): {list(registry.keys())}")
    exp_manager = ExperienceManager(registry=registry, worker=worker)

    controller = AppController(experience_manager=exp_manager)

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_ROOT))

    # Expose AppController + VisionWorker (via image provider) to QML
    root_ctx = engine.rootContext()
    if root_ctx is None:
        logger.error("QQmlApplicationEngine.rootContext() returned None")
        return 1
    root_ctx.setContextProperty("app", controller)
    engine.addImageProvider("camera", CameraImageProvider(worker))

    main_qml = QML_ROOT / "MainWindow.qml"
    engine.load(QUrl.fromLocalFile(str(main_qml)))
    if not engine.rootObjects():
        logger.error("MainWindow.qml failed to load")
        return 1

    worker.start()  # QThread.start

    logger.info("Entering event loop")
    exit_code = app.exec()

    logger.info("Shutting down: stopping VisionWorker")
    exp_manager.unload()
    worker.stop()
    return exit_code


def main() -> int:
    return run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
