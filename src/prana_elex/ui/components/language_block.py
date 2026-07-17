from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout

from prana_elex.common.languages import LANGUAGE_NAMES
from prana_elex.ui.icons import phosphor_icon
from prana_elex.ui.i18n import language, tr


class LanguageBlock(QFrame):
    language_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LanguageCard")
        self.setFixedHeight(96)
        self._suppress_signal = False
        self._detected_code = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 14, 28, 14)
        layout.setSpacing(20)

        input_block = QVBoxLayout()
        input_block.setSpacing(6)
        self._input_label = QLabel()
        self._input_label.setObjectName("LangLabel")
        self._input_lang = QLabel()
        self._input_lang.setObjectName("LangValue")
        input_block.addWidget(self._input_label)
        input_block.addWidget(self._input_lang)
        layout.addLayout(input_block, 1)

        direction = QLabel()
        direction.setObjectName("LanguageDirection")
        direction.setAlignment(Qt.AlignCenter)
        direction.setFixedWidth(32)
        direction.setPixmap(
            phosphor_icon(
                "ph.arrow-right",
                color="#007B87",
                active_color="#005E68",
            ).pixmap(QSize(18, 18))
        )
        direction.setToolTip("Detected language to output language")
        layout.addWidget(direction)

        output_block = QVBoxLayout()
        output_block.setSpacing(6)
        self._output_label = QLabel()
        self._output_label.setObjectName("LangLabel")
        self._output_combo = QComboBox()
        self._output_combo.addItems(LANGUAGE_NAMES.values())
        self._output_combo.setCurrentText(LANGUAGE_NAMES.get("en", "English"))
        self._output_combo.setCursor(Qt.PointingHandCursor)
        output_block.addWidget(self._output_label)
        output_block.addWidget(self._output_combo)
        layout.addLayout(output_block, 1)

        self._output_combo.currentTextChanged.connect(self._on_lang_changed)
        language.changed.connect(self._retranslate)
        self._retranslate()

    def _retranslate(self, *_args) -> None:
        target = self.get_target_language()
        self._input_label.setText(tr("language.input"))
        self._output_label.setText(tr("language.output"))
        names = self._names()
        self._suppress_signal = True
        self._output_combo.clear()
        self._output_combo.addItems(names.values())
        self._output_combo.setCurrentText(names.get(target, target))
        self._suppress_signal = False
        self._input_lang.setText(names.get(self._detected_code, self._detected_code.upper()) if self._detected_code else tr("language.detecting"))

    @staticmethod
    def _names() -> dict[str, str]:
        if language.locale == "vi":
            return {"vi": "Tiếng Việt", "en": "Tiếng Anh", "zh": "Tiếng Trung",
                    "ja": "Tiếng Nhật", "ko": "Tiếng Hàn"}
        return LANGUAGE_NAMES

    def set_detected_language(self, code: str) -> None:
        self._detected_code = code
        name = self._names().get(code, code.upper())
        self._input_lang.setText(name)

    def set_target_language(self, code: str) -> None:
        name = self._names().get(code)
        if name:
            self._suppress_signal = True
            self._output_combo.setCurrentText(name)
            self._suppress_signal = False

    def get_target_language(self) -> str:
        text = self._output_combo.currentText()
        for names in (LANGUAGE_NAMES, {"vi": "Tiếng Việt", "en": "Tiếng Anh", "zh": "Tiếng Trung",
                                          "ja": "Tiếng Nhật", "ko": "Tiếng Hàn"}):
            for code, name in names.items():
                if name == text:
                    return code
        return "en"

    def _on_lang_changed(self) -> None:
        if not self._suppress_signal:
            self.language_changed.emit(self.get_target_language())
