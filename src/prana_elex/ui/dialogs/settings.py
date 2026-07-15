from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


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
        self.setWindowTitle("Settings")
        self.setFixedSize(520, 440)
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

        self._autostart_checkbox = None
        if autostart_enabled is not None:
            self._autostart_checkbox = QCheckBox("Start PRANA ELEX when I log in")
            self._autostart_checkbox.setChecked(autostart_enabled)
            form.addRow("Autostart", self._autostart_checkbox)

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
        return mode, device

    def get_autostart_enabled(self) -> bool | None:
        if self._autostart_checkbox is None:
            return None
        return self._autostart_checkbox.isChecked()
