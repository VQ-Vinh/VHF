from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from prana_elex.ui.i18n import language, tr


def _device_label(d: dict) -> str:
    inp = d.get("inputs", 0)
    out = d.get("outputs", 0)
    sr = int(d.get("sr", 0)) if d.get("sr") else 0
    return f"[{d['index']}] {d['name']}  ({inp}in/{out}out, {sr}Hz)"


def _loopback_label(d: dict) -> str:
    sr = int(d.get("sr", 0)) if d.get("sr") else 0
    return f"[{d['index']}] {d['name']}  (loopback, {sr}Hz)"


class SettingsDialog(QDialog):
    def __init__(
        self,
        current_device: int,
        current_mode: str,
        devices: list[dict],
        loopback_devices: list[dict],
        autostart_enabled: bool | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("settings.title"))
        self.setMinimumSize(620, 440)
        self.resize(680, 500)
        self.setObjectName("SettingsDialog")

        self._devices = devices
        self._loopback_devices = loopback_devices
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        self._language_heading = QLabel(tr("settings.language"))
        self._language_heading.setObjectName("SettingsSectionTitle")
        layout.addWidget(self._language_heading)
        self._language_group = QGroupBox()
        language_form = QFormLayout(self._language_group)
        language_form.setVerticalSpacing(12)
        self._language_combo = QComboBox()
        self._language_combo.addItem(tr("common.english"), "en")
        self._language_combo.addItem(tr("common.vietnamese"), "vi")
        self._language_combo.setCurrentIndex(0 if language.locale == "en" else 1)
        self._language_combo.currentIndexChanged.connect(
            lambda: language.set_locale(self._language_combo.currentData())
        )
        language_form.addRow(tr("settings.language"), self._language_combo)
        layout.addWidget(self._language_group)

        layout.addSpacing(6)
        self._audio_heading = QLabel(tr("settings.audio"))
        self._audio_heading.setObjectName("SettingsSectionTitle")
        layout.addWidget(self._audio_heading)
        self._audio_group = QGroupBox()
        form = QFormLayout(self._audio_group)
        form.setSpacing(12)

        self._mode_label = QLabel(tr("settings.capture_mode"))
        self._mode_label.setObjectName("SettingsLabel")
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["device", "loopback"])
        self._mode_combo.setCurrentText(current_mode)
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        form.addRow(self._mode_label, self._mode_combo)

        self._device_label = QLabel(tr("settings.device"))
        self._device_label.setObjectName("SettingsLabel")
        self._device_combo = QComboBox()
        self._device_combo.setMinimumWidth(340)
        self._populate_devices(current_mode, current_device)
        form.addRow(self._device_label, self._device_combo)

        self._autostart_checkbox = None
        if autostart_enabled is not None:
            self._autostart_checkbox = QCheckBox(tr("settings.autostart"))
            self._autostart_checkbox.setChecked(autostart_enabled)
            form.addRow("Autostart", self._autostart_checkbox)

        layout.addWidget(self._audio_group)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        self._cancel_button = QPushButton(tr("common.cancel"))
        self._cancel_button.clicked.connect(self.reject)
        self._save_button = QPushButton(tr("common.save"))
        self._save_button.setObjectName("PrimaryButton")
        self._save_button.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(self._cancel_button)
        btn_layout.addWidget(self._save_button)
        layout.addLayout(btn_layout)
        language.changed.connect(self._retranslate)

    def _retranslate(self, *_args) -> None:
        self.setWindowTitle(tr("settings.title"))
        self._language_heading.setText(tr("settings.language"))
        self._audio_heading.setText(tr("settings.audio"))
        self._mode_label.setText(tr("settings.capture_mode"))
        self._device_label.setText(tr("settings.device"))
        if self._autostart_checkbox:
            self._autostart_checkbox.setText(tr("settings.autostart"))
        self._cancel_button.setText(tr("common.cancel"))
        self._save_button.setText(tr("common.save"))

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
        return mode, device

    def get_autostart_enabled(self) -> bool | None:
        if self._autostart_checkbox is None:
            return None
        return self._autostart_checkbox.isChecked()
