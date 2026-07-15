from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from prana_elex.config.user_settings import get_credentials_path, save_settings


REQUIRED_CREDENTIAL_FIELDS = {"type", "project_id", "private_key", "client_email"}


def validate_credentials(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or data.get("type") != "service_account":
        raise ValueError("The selected JSON is not a Google service-account key.")
    missing = sorted(REQUIRED_CREDENTIAL_FIELDS - data.keys())
    if missing:
        raise ValueError(f"The service-account JSON is missing: {', '.join(missing)}")


class FirstRunDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PRANA ELEX - First Run")
        self.setMinimumWidth(640)

        layout = QVBoxLayout(self)
        title = QLabel("Choose where PRANA ELEX stores data and select your Google Cloud credentials.")
        title.setWordWrap(True)
        layout.addWidget(title)

        form = QFormLayout()
        self._data_dir = QLineEdit(str(Path.home() / "PRANA_ELEX_Data"))
        data_row = QHBoxLayout()
        data_row.addWidget(self._data_dir)
        data_browse = QPushButton("Browse...")
        data_browse.clicked.connect(self._browse_data)
        data_row.addWidget(data_browse)
        form.addRow("Data folder", data_row)

        self._credentials = QLineEdit()
        credentials_row = QHBoxLayout()
        credentials_row.addWidget(self._credentials)
        credentials_browse = QPushButton("Browse...")
        credentials_browse.clicked.connect(self._browse_credentials)
        credentials_row.addWidget(credentials_browse)
        form.addRow("Service-account JSON", credentials_row)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save and Continue")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _browse_data(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select data folder", self._data_dir.text())
        if selected:
            self._data_dir.setText(selected)

    def _browse_credentials(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self, "Select Google service-account JSON", str(Path.home()), "JSON files (*.json)"
        )
        if selected:
            self._credentials.setText(selected)

    def _save(self) -> None:
        try:
            data_dir = Path(self._data_dir.text().strip()).expanduser()
            source = Path(self._credentials.text().strip()).expanduser()
            if not self._data_dir.text().strip():
                raise ValueError("Please choose a data folder.")
            if not source.is_file():
                raise ValueError("Please select a service-account JSON file.")
            validate_credentials(source)
            data_dir.mkdir(parents=True, exist_ok=True)

            destination = get_credentials_path()
            destination.parent.mkdir(parents=True, exist_ok=True)
            if sys.platform.startswith("linux"):
                destination.parent.chmod(0o700)
            if source.resolve() != destination.resolve():
                shutil.copy2(source, destination)
            if sys.platform.startswith("linux"):
                destination.chmod(0o600)
            save_settings(str(data_dir.resolve()), str(destination.resolve()))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            QMessageBox.critical(self, "Cannot save settings", str(exc))
            return
        self.accept()
