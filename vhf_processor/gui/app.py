from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import qasync
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from vhf_processor.config.schema import AppConfig
from vhf_processor.gui.main_window import MainWindow
from vhf_processor.gui.tray import TrayManager
from vhf_processor.pipeline.orchestrator import PipelineOrchestrator
from vhf_processor.utils.logger import get_logger, setup_logger

logger = get_logger(__name__)

def _bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        exe_dir = Path(sys.executable).parent.resolve()
        internal = exe_dir / "_internal"
        if (internal / "vhf_processor").is_dir():
            return internal
        return exe_dir
    return Path(__file__).parent.parent.parent.resolve()


def _find_config() -> Path:
    root = _bundle_root()
    candidates = [
        root / "vhf_processor" / "config" / "default.toml",
        root.parent / "vhf_processor" / "config" / "default.toml",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"Config not found (tried {[str(c) for c in candidates]})")


def _load_styles(app: QApplication) -> None:
    qss_path = _bundle_root() / "vhf_processor" / "gui" / "resources" / "styles.qss"
    if qss_path.exists():
        with open(qss_path, encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def run_gui(
    capture_mode: str = "device",
    device_index: int = -1,
    target_language: str = "en",
) -> None:
    config = AppConfig.from_toml(_find_config())
    config.resolve_paths()
    config.audio.capture_mode = capture_mode
    if device_index >= 0:
        config.audio.device_index = device_index
    config.translation.target_language = target_language

    setup_logger(level=config.general.log_level, console_level="WARNING")

    app = QApplication([])
    app.setApplicationName("PRANA ELEX")
    app.setOrganizationName("PRANA")
    _load_styles(app)

    orchestrator = PipelineOrchestrator(config)
    window = MainWindow(config, orchestrator)
    tray = TrayManager(window)

    orchestrator.on_result = lambda r: QTimer.singleShot(0, lambda: window._on_result(r))
    orchestrator.on_detected_language = lambda c: QTimer.singleShot(0, lambda: window._on_detected_language(c))

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    def start_pipeline():
        for attempt in range(2):
            try:
                orchestrator.start()
                tray.set_pipeline_running(True)
                window._set_status("running", f"Device: {config.audio.device_index}")
                return
            except Exception as e:
                if attempt == 0 and config.audio.device_index >= 0:
                    logger.warning("Device %d failed, falling back to auto", config.audio.device_index)
                    config.audio.device_index = -1
                else:
                    logger.error("Pipeline start failed", exc_info=e)
                    window._set_status("error", str(e))
                    return

    loop.call_soon(start_pipeline)
    window.show()

    try:
        with loop:
            loop.run_forever()
    finally:
        orchestrator.stop()
