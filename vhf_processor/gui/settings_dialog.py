from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from vhf_processor.gemini.prompt_builder import LANGUAGE_NAMES


def _device_label(d: dict) -> str:
    inp = d.get("inputs", 0)
    out = d.get("outputs", 0)
    sr = int(d.get("sr", 0))
    return f"[{d['index']}] {d['name']}  ({inp}in/{out}out, {sr}Hz)"


def _loopback_label(d: dict) -> str:
    return f"[{d['index']}] {d['name']}  (loopback, {int(d.get('sr', 0))}Hz)"


class SettingsDialog(QDialog):
    def __init__(
        self,
        current_device: int,
        current_mode: str,
        current_lang: str,
        devices: list[dict],
        loopback_devices: list[dict],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(520, 380)
        self.setObjectName("SettingsDialog")

        self._devices = devices
        self._loopback_devices = loopback_devices

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(12)

        mode_label = QLabel("Capture Mode")
        mode_label.setObjectName("SettingsLabel")
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["device", "loopback"])
        self._mode_combo.setCurrentText(current_mode)
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        form.addRow(mode_label, self._mode_combo)

        dev_label = QLabel("Device")
        dev_label.setObjectName("SettingsLabel")
        self._device_combo = QComboBox()
        self._device_combo.setMinimumWidth(340)
        self._populate_devices(current_mode, current_device)
        form.addRow(dev_label, self._device_combo)

        lang_label = QLabel("Target Language")
        lang_label.setObjectName("SettingsLabel")
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(LANGUAGE_NAMES.values())
        current_name = LANGUAGE_NAMES.get(current_lang, "English")
        self._lang_combo.setCurrentText(current_name)
        form.addRow(lang_label, self._lang_combo)

        layout.addLayout(form)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _on_mode_changed(self, mode: str):
        self._populate_devices(mode, None)

    def _populate_devices(self, mode: str, selected_index: int | None):
        self._device_combo.clear()
        if mode == "loopback":
            items = self._loopback_devices or []
            for d in items:
                self._device_combo.addItem(_loopback_label(d), d["index"])
        else:
            items = [d for d in self._devices if d.get("inputs", 0) > 0]
            for d in items:
                self._device_combo.addItem(_device_label(d), d["index"])

        if selected_index is not None:
            idx = self._device_combo.findData(selected_index)
            if idx >= 0:
                self._device_combo.setCurrentIndex(idx)

    def get_values(self) -> tuple:
        mode = self._mode_combo.currentText()
        device = self._device_combo.currentData()
        if device is None:
            device = -1
        lang_text = self._lang_combo.currentText()
        lang = "en"
        for code, name in LANGUAGE_NAMES.items():
            if name == lang_text:
                lang = code
                break
        return mode, device, lang
