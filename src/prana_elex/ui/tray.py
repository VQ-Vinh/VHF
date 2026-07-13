from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from prana_elex.core.pipeline.orchestrator import PipelineState
from prana_elex.core.utils.logger import get_logger

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
    def __init__(self, main_window, parent=None):
        self._main_window = main_window
        self._tray = QSystemTrayIcon(parent)
        self._tray.setIcon(_create_tray_icon())
        self._tray.setToolTip("PRANA ELEX \u2014 VHF Marine Radio")

        menu = QMenu()
        show_action = QAction("Show/Hide")
        show_action.triggered.connect(self._toggle_window)
        menu.addAction(show_action)

        self._start_stop_action = QAction("Start")
        self._start_stop_action.triggered.connect(self._toggle_pipeline)
        menu.addAction(self._start_stop_action)

        menu.addSeparator()

        quit_action = QAction("Exit")
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def _on_state_changed(self, state: PipelineState, message: str):
        if state == PipelineState.RUNNING:
            self._start_stop_action.setText("Stop")
        else:
            self._start_stop_action.setText("Start")

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

    def _toggle_pipeline(self):
        orc = self._main_window._orchestrator
        if orc is None:
            return
        if orc.state == PipelineState.RUNNING:
            orc.stop()
        else:
            try:
                orc.start()
            except Exception as e:
                logger.error("Pipeline start failed from tray", exc_info=e)
                self._main_window._set_status("error", str(e))

    def set_pipeline_running(self, running: bool):
        self._start_stop_action.setText("Stop" if running else "Start")
