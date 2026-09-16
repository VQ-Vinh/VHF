from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from prana_core.common.logger import get_logger
from prana_windows.ui.i18n import language, tr

logger = get_logger(__name__)


def _create_tray_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#00E5FF"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(4, 4, 56, 56)
    painter.end()
    return QIcon(pixmap)


class TrayManager:
    """Show/hide and quit only.

    The console drives remote Stations, so there is no local pipeline to start
    or stop from here. Start/Stop belongs to the attached Station's workspace,
    where the control lease and the confirmation state are visible.
    """

    def __init__(self, main_window, parent=None):
        self._main_window = main_window
        self._authenticated = False
        self._tray = QSystemTrayIcon(parent)
        self._tray.setIcon(_create_tray_icon())
        self._tray.setToolTip("PRANA ELEX - VHF Marine Radio")

        menu = QMenu()
        self._show_action = QAction(tr("tray.show"))
        self._show_action.triggered.connect(self._toggle_window)
        menu.addAction(self._show_action)
        menu.addSeparator()
        self._quit_action = QAction(tr("tray.exit"))
        self._quit_action.triggered.connect(QApplication.quit)
        menu.addAction(self._quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.show()
        language.changed.connect(self._retranslate)

    def _retranslate(self, *_args) -> None:
        self._show_action.setText(tr("tray.show"))
        self._quit_action.setText(tr("tray.exit"))

    def _toggle_window(self):
        if self._main_window.isVisible():
            self._main_window.hide()
        else:
            self._main_window.show()
            self._main_window.raise_()
            self._main_window.activateWindow()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_window()

    def set_authenticated(self, authenticated: bool) -> None:
        self._authenticated = authenticated
