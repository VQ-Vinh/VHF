from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import qasync
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from prana_elex.backend.client import BackendClient
from prana_elex.config.schema import AppConfig
from prana_elex.config.user_settings import load_settings, save_settings
from prana_elex.pipeline.events import event_bus
from prana_elex.pipeline.orchestrator import PipelineState
from prana_elex.ui.account import AccountController
from prana_elex.ui.main_window import MainWindow
from prana_elex.ui.icons import phosphor_icon
from prana_elex.ui.i18n import language
from prana_elex.ui.tray import TrayManager
from prana_elex.common.logger import get_logger, setup_logger

logger = get_logger(__name__)


class _EventBusBridge(QObject):
    result_ready = Signal(object)
    language_detected = Signal(str)
    state_changed = Signal(object, str)
    error_occurred = Signal(str)
    access_denied = Signal(str, str)
    quota_exhausted = Signal(str, str, str)
    pipeline_started = Signal()

    def __init__(self):
        super().__init__()
        event_bus.on("result_ready", self.result_ready.emit)
        event_bus.on("language_detected", self.language_detected.emit)
        event_bus.on("state_changed", self.state_changed.emit)
        event_bus.on("error_occurred", self.error_occurred.emit)
        event_bus.on("access_denied", self.access_denied.emit)
        event_bus.on("quota_exhausted", self.quota_exhausted.emit)
        event_bus.on("pipeline_started", self.pipeline_started.emit)


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False) or getattr(sys, "_MEIPASS", None) is not None


def _bundle_root() -> Path:
    if _is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        exe_dir = Path(sys.executable).parent.resolve()
        internal = exe_dir / "_internal"
        if (internal / "prana_elex").is_dir():
            return internal
        return exe_dir
    return Path(__file__).resolve().parent.parent.parent.parent


def _find_config() -> Path:
    root = _bundle_root()
    candidates = []
    profile_dir = root / "config" if _is_frozen() else root / "config" / "profiles"
    if sys.platform.startswith("linux"):
        candidates.append(profile_dir / "raspberry-pi.toml")
    if sys.platform == "win32":
        candidates.append(profile_dir / "windows-device.toml")
    candidates.append(root / "config" / "default.toml")
    if not _is_frozen():
        candidates.append(root / "src" / "prana_elex" / "config" / "default.toml")
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"Config not found (tried {[str(c) for c in candidates]})")


def _load_styles(app: QApplication) -> None:
    root = _bundle_root()
    qss_path = root / "src" / "prana_elex" / "ui" / "resources" / "styles.qss"
    if not qss_path.exists():
        prefix = "" if _is_frozen() else "src"
        qss_path = root / prefix / "prana_elex" / "ui" / "resources" / "styles.qss"
    if qss_path.exists():
        with open(qss_path, encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        logger.warning("Stylesheet not found at %s", qss_path)


def run_app(
    capture_mode: str = "device",
    device_index: int = -1,
    target_language: str = "en",
) -> None:
    config = AppConfig.from_toml(_find_config())

    app = QApplication([])

    app.setApplicationName("PRANA ELEX")
    app.setOrganizationName("PRANA")
    app.setWindowIcon(
        phosphor_icon(
            "ph.radio",
            color="#087F8C",
            active_color="#087F8C",
            scale_factor=0.9,
        )
    )
    _load_styles(app)

    settings = load_settings()
    language.set_locale(settings.get("ui_locale", "en"))
    language.changed.connect(lambda locale: save_settings(ui_locale=locale))
    data_value = settings.get("data_dir", "").strip()
    config.audio.capture_mode = capture_mode
    if device_index >= 0:
        config.audio.device_index = device_index
    config.translation.target_language = target_language

    setup_logger(level=config.general.log_level, console_level="WARNING")

    backend = BackendClient(
        config.backend.api_url,
        config.backend.firebase_api_key,
        config.backend.timeout_seconds,
        config.backend.google_oauth_client_id,
    )
    account = AccountController(backend)
    bridge = _EventBusBridge()
    window = MainWindow(
        config,
        account_controller=account,
        data_root=data_value,
        require_installer_data=_is_frozen() and sys.platform == "win32",
    )
    tray = TrayManager(window)

    bridge.result_ready.connect(window._on_result)
    bridge.language_detected.connect(window._on_detected_language)
    bridge.state_changed.connect(window._on_state_changed)
    bridge.state_changed.connect(tray._on_state_changed)
    bridge.error_occurred.connect(window._on_error)
    bridge.access_denied.connect(window.on_access_denied)
    bridge.quota_exhausted.connect(window.on_quota_exhausted)
    window.account_active_changed.connect(tray.set_authenticated)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    window.show()
    window.start_account_flow()

    try:
        with loop:
            loop.run_forever()
    finally:
        if window._orchestrator:
            window._orchestrator.shutdown()
        backend.close()
