"""Phase 0 minimal app — QApplication + QML SplashScreen.

Sẽ extend từ Phase 1 với VisionEngine, từ Phase 2 với ExperienceManager + Hub.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine

from neo_makervigate import __version__
from neo_makervigate.config.settings import load_settings
from neo_makervigate.utils.logging_config import setup_logging
from neo_makervigate.utils.signal_bus import SignalBus

QML_ROOT = Path(__file__).parent / "ui" / "qml"


def run(argv: list[str]) -> int:
    """Boot ứng dụng. Trả về exit code Qt."""
    setup_logging()
    from loguru import logger

    logger.info(f"NeoMakerViGate v{__version__} starting")

    settings = load_settings()
    logger.info(f"Loaded config: app.name={settings.app_name}, debug={settings.debug}")

    # SignalBus instance — singleton dùng xuyên suốt
    bus = SignalBus.instance()
    _ = bus  # giữ reference để garbage collector không thu hồi

    app = QGuiApplication(argv)
    app.setApplicationName("NeoMakerViGate")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Maker Viet x De Foundation")

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_ROOT))

    main_qml = QML_ROOT / "MainWindow.qml"
    if not main_qml.exists():
        logger.error(f"MainWindow.qml not found at {main_qml}")
        return 1

    engine.load(QUrl.fromLocalFile(str(main_qml)))
    if not engine.rootObjects():
        logger.error("Failed to load MainWindow.qml — check QML errors above")
        return 1

    logger.info("QML engine loaded, entering event loop")
    return app.exec()


if __name__ == "__main__":
    sys.exit(run(sys.argv))
