from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout

from prana_elex.ai.gemini.prompts import LANGUAGE_NAMES
from prana_elex.ui.icons import phosphor_icon


class LanguageBlock(QFrame):
    language_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LanguageCard")
        self.setFixedHeight(84)
        self._suppress_signal = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 12, 28, 12)
        layout.setSpacing(20)

        input_block = QVBoxLayout()
        input_block.setSpacing(6)
        input_label = QLabel("INPUT LANGUAGE")
        input_label.setObjectName("LangLabel")
        self._input_lang = QLabel("Detecting…")
        self._input_lang.setObjectName("LangValue")
        input_block.addWidget(input_label)
        input_block.addWidget(self._input_lang)
        layout.addLayout(input_block, 1)

        direction = QLabel()
        direction.setObjectName("LanguageDirection")
        direction.setAlignment(Qt.AlignCenter)
        direction.setFixedWidth(32)
        direction.setPixmap(
            phosphor_icon(
                "ph.arrow-right",
                color="#4D4D60",
                active_color="#4D4D60",
            ).pixmap(QSize(18, 18))
        )
        direction.setToolTip("Detected language to output language")
        layout.addWidget(direction)

        output_block = QVBoxLayout()
        output_block.setSpacing(6)
        output_label = QLabel("OUTPUT LANGUAGE")
        output_label.setObjectName("LangLabel")
        self._output_combo = QComboBox()
        self._output_combo.addItems(LANGUAGE_NAMES.values())
        self._output_combo.setCurrentText(LANGUAGE_NAMES.get("en", "English"))
        self._output_combo.setCursor(Qt.PointingHandCursor)
        output_block.addWidget(output_label)
        output_block.addWidget(self._output_combo)
        layout.addLayout(output_block, 1)

        self._output_combo.currentTextChanged.connect(self._on_lang_changed)

    def set_detected_language(self, code: str) -> None:
        name = LANGUAGE_NAMES.get(code, code.upper())
        self._input_lang.setText(name)

    def set_target_language(self, code: str) -> None:
        name = LANGUAGE_NAMES.get(code)
        if name:
            self._suppress_signal = True
            self._output_combo.setCurrentText(name)
            self._suppress_signal = False

    def get_target_language(self) -> str:
        text = self._output_combo.currentText()
        for code, name in LANGUAGE_NAMES.items():
            if name == text:
                return code
        return "en"

    def _on_lang_changed(self) -> None:
        if not self._suppress_signal:
            self.language_changed.emit(self.get_target_language())
