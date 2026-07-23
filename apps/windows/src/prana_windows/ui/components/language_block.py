from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel

from prana_core.common.languages import LANGUAGE_NAMES
from prana_windows.ui.icons import phosphor_icon
from prana_windows.ui.i18n import language, tr


class LanguageBlock(QFrame):
    language_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LanguageCard")
        self.setFixedHeight(96)
        self._suppress_signal = False
        self._detected_code = ""

        layout = QGridLayout(self)
        layout.setContentsMargins(28, 14, 28, 14)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(6)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 1)

        self._input_label = QLabel()
        self._input_label.setObjectName("LangLabel")
        layout.addWidget(self._input_label, 0, 0)

        self._input_box = QFrame()
        self._input_box.setObjectName("LanguageInputBox")
        self._input_box.setFixedHeight(40)
        input_value_layout = QHBoxLayout(self._input_box)
        input_value_layout.setContentsMargins(12, 0, 12, 0)
        self._input_lang = QLabel()
        self._input_lang.setObjectName("LangValue")
        self._input_lang.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        input_value_layout.addWidget(self._input_lang)
        layout.addWidget(self._input_box, 1, 0)

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
        layout.addWidget(direction, 1, 1, alignment=Qt.AlignCenter)

        self._output_label = QLabel()
        self._output_label.setObjectName("LangLabel")
        layout.addWidget(self._output_label, 0, 2)
        self._output_combo = QComboBox()
        self._output_combo.setFixedHeight(40)
        self._output_combo.addItems(LANGUAGE_NAMES.values())
        self._output_combo.setCurrentText(LANGUAGE_NAMES.get("en", "English"))
        self._output_combo.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self._output_combo, 1, 2)

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
