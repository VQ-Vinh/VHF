from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QApplication


class TrayManager:
    def __init__(self, main_window, parent=None):
        self._main_window = main_window
        self._tray = QSystemTrayIcon(parent)
        self._tray.setIcon(QIcon.fromTheme("media-record"))
        self._tray.setToolTip("PRANA ELEX \u2014 VHF Marine Radio")

        menu = QMenu()
        show_action = QAction("Show/Hide")
        show_action.triggered.connect(self._toggle_window)
        menu.addAction(show_action)

        self._start_stop_action = QAction("Stop")
        self._start_stop_action.triggered.connect(self._toggle_pipeline)
        menu.addAction(self._start_stop_action)

        menu.addSeparator()

        quit_action = QAction("Exit")
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

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
        if orc and orc._running:
            orc.stop()
            self._start_stop_action.setText("Start")
        else:
            orc.start()
            self._start_stop_action.setText("Stop")

    def set_pipeline_running(self, running: bool):
        self._start_stop_action.setText("Stop" if running else "Start")
