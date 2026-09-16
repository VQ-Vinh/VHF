from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from prana_core.console.models import StationSummary
from prana_windows.ui.i18n import language, tr


class StationRow(QFrame):
    """One Station in the fleet list."""

    attach_requested = Signal(str)

    def __init__(self, station: StationSummary, parent=None):
        super().__init__(parent)
        self.setObjectName("StationRow")
        self._station = station

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        info = QVBoxLayout()
        info.setSpacing(2)
        self._name = QLabel()
        self._name.setObjectName("StationRowName")
        self._detail = QLabel()
        self._detail.setObjectName("StationRowDetail")
        self._detail.setWordWrap(True)
        info.addWidget(self._name)
        info.addWidget(self._detail)
        layout.addLayout(info, stretch=1)

        self._lease = QLabel()
        self._lease.setObjectName("StationRowLease")
        layout.addWidget(self._lease, 0, Qt.AlignVCenter)

        self._status = QLabel()
        self._status.setObjectName("StationRowStatus")
        layout.addWidget(self._status, 0, Qt.AlignVCenter)

        self._attach = QPushButton()
        self._attach.setObjectName("PrimaryButton")
        self._attach.setCursor(Qt.PointingHandCursor)
        self._attach.clicked.connect(
            lambda: self.attach_requested.emit(self._station.station_id)
        )
        layout.addWidget(self._attach, 0, Qt.AlignVCenter)

        language.changed.connect(self._retranslate)
        self._retranslate()

    def station_id(self) -> str:
        return self._station.station_id

    def update_station(self, station: StationSummary) -> None:
        self._station = station
        self._retranslate()

    def _retranslate(self, *_args) -> None:
        station = self._station
        online = station.is_online_at(datetime.now(timezone.utc))
        self._name.setText(station.name or station.station_id[:8])
        owner = station.owner_email or station.owner_uid or "—"
        self._detail.setText(
            f"{station.station_id[:8]}  ·  {station.platform}  ·  "
            f"{tr('fleet.owner')}: {owner}  ·  {station.capture_state.upper()}"
        )
        self._status.setText(tr("fleet.online") if online else tr("fleet.offline"))
        self._status.setProperty("online", "true" if online else "false")
        lease = station.control_lease
        held = lease is not None and lease.is_active_at(datetime.now(timezone.utc))
        self._lease.setText(lease.holder_label if held and lease else "")
        self._lease.setVisible(bool(held))
        self._attach.setText(tr("fleet.attach"))
        for widget in (self._status, self._lease):
            widget.style().unpolish(widget)
            widget.style().polish(widget)


__all__ = ["StationRow"]
