from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from prana_windows.ui.icons import GlyphLabel


class SimNotice(QFrame):
    """A standing caution about the simulation, not a transient error.

    Amber rather than the error red, as on the phone
    (`control/presentation/widgets/sim_notice.dart`): nothing has gone wrong, the
    panel simply is not a navigation instrument, and colouring it as a fault
    would teach the crew to ignore real faults.
    """

    def __init__(self, icon: str, parent=None):
        super().__init__(parent)
        self.setObjectName("SimNotice")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        layout.addWidget(GlyphLabel(icon, role="warn_icon", size=16), 0, Qt.AlignTop)
        self._text = QLabel()
        self._text.setObjectName("SimNoticeText")
        self._text.setWordWrap(True)
        layout.addWidget(self._text, 1)

    def set_text(self, text: str) -> None:
        self._text.setText(text)

    def text(self) -> str:
        return self._text.text()


__all__ = ["SimNotice"]
