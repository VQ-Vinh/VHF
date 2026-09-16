from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import qasync
from PySide6.QtWidgets import QApplication

from prana_core.backend.client import BackendClient
from prana_core.config.schema import AppConfig
from prana_core.console.station_client import OperatorStationClient
from prana_windows.credential_store import WindowsCredentialStore
from prana_windows.settings import load_settings, save_settings
from prana_windows.ui.account import AccountController
from prana_windows.ui.main_window import MainWindow
from prana_windows.ui.icons import phosphor_icon
from prana_windows.ui.i18n import language
from prana_windows.ui.tray import TrayManager
from prana_core.common.logger import get_logger, setup_logger

logger = get_logger(__name__)


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False) or getattr(sys, "_MEIPASS", None) is not None


def _bundle_root() -> Path:
    if _is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        exe_dir = Path(sys.executable).parent.resolve()
        internal = exe_dir / "_internal"
        if (internal / "prana_core").is_dir():
            return internal
        return exe_dir
    return Path(__file__).resolve().parent.parent.parent.parent


def _find_config() -> Path:
    root = _bundle_root()
    candidates = [root / "config" / "default.toml"]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"Config not found (tried {[str(c) for c in candidates]})")


def _load_styles(app: QApplication) -> None:
    root = _bundle_root()
    qss_path = root / "src" / "prana_windows" / "ui" / "resources" / "styles.qss"
    if not qss_path.exists():
        prefix = "" if _is_frozen() else "src"
        qss_path = root / prefix / "prana_windows" / "ui" / "resources" / "styles.qss"
    if qss_path.exists():
        with open(qss_path, encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        logger.warning("Stylesheet not found at %s", qss_path)


def run_app() -> None:
    """Start the fleet operator console.

    The desktop app no longer captures or translates audio on this machine; it
    drives remote Stations over the API. Local capture lives on in the headless
    Windows Station (`prana_windows.station`) and the CLI.
    """
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

    setup_logger(level=config.general.log_level, console_level="WARNING")

    backend = BackendClient(
        config.backend.api_url,
        config.backend.firebase_api_key,
        config.backend.timeout_seconds,
        config.backend.google_oauth_client_id,
        credential_store=WindowsCredentialStore(),
    )
    station_client = OperatorStationClient(backend)
    account = AccountController(backend)
    window = MainWindow(
        config,
        account_controller=account,
        station_client=station_client,
    )
    tray = TrayManager(window)
    window.account_active_changed.connect(tray.set_authenticated)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    window.show()
    window.start_account_flow()

    try:
        with loop:
            loop.run_forever()
    finally:
        # Releases any control lease before the process goes away, so a Station
        # is not pinned to a console that has exited.
        window._teardown_console()
        backend.close()
