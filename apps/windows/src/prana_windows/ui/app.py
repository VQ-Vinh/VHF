from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import qasync
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from prana_core.backend.client import BackendClient
from prana_core.config.schema import AppConfig
from prana_core.console.station_client import OperatorStationClient
from prana_windows.credential_store import WindowsCredentialStore
from prana_windows.settings import load_settings, save_settings
from prana_windows.ui.account import AccountController
from prana_windows.ui.main_window import MainWindow
from prana_windows.ui.brand import app_icon, resource
from prana_windows.ui.i18n import language
from prana_windows.ui.theme import load_qss, theme
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


def _load_fonts() -> None:
    """Register the brand faces shared with the Flutter app.

    Archivo carries console captions and headings, Roboto Mono carries states
    and numerals -- the same split `console_palette.dart` makes. Every QSS font
    list ends in a system face, so a missing file degrades instead of breaking.
    """
    for path in sorted(resource("fonts").glob("*.ttf")):
        if QFontDatabase.addApplicationFont(str(path)) == -1:
            logger.warning("Could not load font %s", path.name)


def _load_styles(app: QApplication, initial_theme: str = "light") -> None:
    """Bind the stylesheet template to the theme manager.

    The stylesheet is a `string.Template`; the theme supplies the tokens and
    re-applies it whenever the theme changes. Re-applying to a live
    QApplication restyles widgets already on screen, so nothing is rebuilt.
    """
    root = _bundle_root()
    qss_path = root / "src" / "prana_windows" / "ui" / "resources" / "styles.qss"
    if not qss_path.exists():
        prefix = "" if _is_frozen() else "src"
        qss_path = root / prefix / "prana_windows" / "ui" / "resources" / "styles.qss"
    if qss_path.exists():
        theme.bind(app, load_qss(qss_path), initial_theme)
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
    app.setWindowIcon(app_icon())
    settings = load_settings()
    language.set_locale(settings.get("ui_locale", "en"))
    language.changed.connect(lambda locale: save_settings(ui_locale=locale))
    theme.changed.connect(lambda name: save_settings(ui_theme=name))
    _load_fonts()
    _load_styles(app, settings.get("ui_theme", "light"))

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
