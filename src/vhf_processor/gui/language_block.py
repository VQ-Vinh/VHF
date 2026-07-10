from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from vhf_processor.gemini.prompt_builder import LANGUAGE_NAMES


class LanguageBlock(QFrame):
    language_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LanguageCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        input_block = QVBoxLayout()
        input_label = QLabel("INPUT \u00B7 AUTO-DETECT")
        input_label.setObjectName("LangLabel")
        self._input_lang = QLabel("---")
        self._input_lang.setObjectName("LangValue")
        input_block.addWidget(input_label)
        input_block.addWidget(self._input_lang)
        layout.addLayout(input_block)

        layout.addStretch()

        self._swap_btn = QPushButton("\u21BB")
        self._swap_btn.setObjectName("SwapButton")
        layout.addWidget(self._swap_btn)

        layout.addStretch()

        output_block = QVBoxLayout()
        output_label = QLabel("OUTPUT \u00B7 CHOSEN")
        output_label.setObjectName("LangLabel")
        self._output_combo = QComboBox()
        self._output_combo.addItems(LANGUAGE_NAMES.values())
        self._output_combo.setCurrentText(LANGUAGE_NAMES.get("en", "English"))
        output_block.addWidget(output_label)
        output_block.addWidget(self._output_combo)
        layout.addLayout(output_block)

        self._output_combo.currentTextChanged.connect(self._on_lang_changed)

    def set_detected_language(self, code: str) -> None:
        name = LANGUAGE_NAMES.get(code, code.upper())
        self._input_lang.setText(name)

    def set_target_language(self, code: str) -> None:
        name = LANGUAGE_NAMES.get(code)
        if name:
            self._output_combo.setCurrentText(name)

    def get_target_language(self) -> str:
        text = self._output_combo.currentText()
        for code, name in LANGUAGE_NAMES.items():
            if name == text:
                return code
        return "en"

    def _on_lang_changed(self):
        self.language_changed.emit(self.get_target_language())
