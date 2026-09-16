from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from prana_core.console.models import ControlLease, StationSummary, TranslationResult
from prana_core.console.command_phase import CommandState
from prana_windows.ui.components.chat_feed import ChatFeed
from prana_windows.ui.components.control_bar import ControlBar
from prana_windows.ui.components.lease_banner import LeaseBanner
from prana_windows.ui.components.tx_panel import TxPanel
from prana_windows.ui.i18n import language, tr


class StationWorkspacePage(QWidget):
    """Live VHF plus controls for the one attached Station."""

    back_requested = Signal()
    take_control_requested = Signal()
    force_control_requested = Signal()
    release_control_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StationWorkspacePage")
        self._station: StationSummary | None = None
        self._shown_request_ids: set[str] = set()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(28, 14, 28, 10)
        header.setSpacing(12)
        self._back = QPushButton()
        self._back.setCursor(Qt.PointingHandCursor)
        self._back.clicked.connect(self.back_requested)
        header.addWidget(self._back)
        self._title = QLabel()
        self._title.setObjectName("WorkspaceTitle")
        header.addWidget(self._title, stretch=1)
        self._owner = QLabel()
        self._owner.setObjectName("WorkspaceOwner")
        header.addWidget(self._owner)
        self._rx = QLabel()
        self._rx.setObjectName("RxLabel")
        header.addWidget(self._rx)
        root.addLayout(header)

        self.lease_banner = LeaseBanner()
        self.lease_banner.take_requested.connect(self.take_control_requested)
        self.lease_banner.force_requested.connect(self.force_control_requested)
        self.lease_banner.release_requested.connect(self.release_control_requested)
        root.addWidget(self.lease_banner)

        self.control_bar = ControlBar()
        root.addWidget(self.control_bar)

        self._message = QLabel()
        self._message.setObjectName("WorkspaceMessage")
        self._message.setWordWrap(True)
        self._message.setVisible(False)
        root.addWidget(self._message)

        self.chat = ChatFeed()
        root.addWidget(self.chat, stretch=1)

        self.tx_panel = TxPanel()
        root.addWidget(self.tx_panel)

        language.changed.connect(self._retranslate)
        self._retranslate()

    # -- state ------------------------------------------------------------

    def reset(self) -> None:
        self.chat.clear()
        self.chat.set_state("stopped")
        self._shown_request_ids.clear()
        self._station = None
        self.set_message("")

    def set_station(self, station: StationSummary) -> None:
        self._station = station
        self.control_bar.set_station(station)
        self._retranslate()

        online = station.is_online_at(datetime.now(timezone.utc))
        if not online:
            self.chat.set_state("stopped")
        elif station.capture_state == "recording":
            self.chat.set_state("recording")
        elif station.desired.running:
            self.chat.set_state("listening")
        else:
            self.chat.set_state("stopped")
        self.chat.set_gcs_status(
            enabled=True,
            ready=online,
            error=station.last_error,
            retry_queue=0,
            last_upload_ok=None if station.last_error is None else False,
        )

    def set_state(self, state: CommandState) -> None:
        self.control_bar.set_state(state)

    def set_lease(self, lease: ControlLease | None, operator_uid: str) -> None:
        self.lease_banner.set_operator_uid(operator_uid)
        self.lease_banner.set_lease(lease)

    def set_results(self, results: list[TranslationResult]) -> None:
        """Append only what the feed has not already shown.

        The live endpoint returns the whole local day on every 2s poll, so the
        page tracks request ids rather than rebuilding the feed and losing the
        operator's scroll position.
        """
        for result in results:
            key = result.request_id or f"{result.session_id}:{result.sequence}"
            if key in self._shown_request_ids:
                continue
            self._shown_request_ids.add(key)
            self.chat.add_message(
                source=result.language,
                transcript=result.transcript,
                translation=result.translation,
                timestamp=result.timestamp,
                confidence=result.confidence,
            )

    def set_message(self, message: str) -> None:
        self._message.setText(message)
        self._message.setVisible(bool(message))

    def holder_label(self) -> str:
        return self.lease_banner.holder_label()

    def station_name(self) -> str:
        station = self._station
        return station.name if station else ""

    def owner_email(self) -> str:
        station = self._station
        return (station.owner_email or station.owner_uid) if station else ""

    def _retranslate(self, *_args) -> None:
        self._back.setText(tr("station.back"))
        station = self._station
        if station is None:
            self._title.setText("")
            self._owner.setText("")
            self._rx.setText(tr("header.rx_off"))
            return
        self._title.setText(tr("station.attached", name=station.name or station.station_id[:8]))
        self._owner.setText(f"{tr('fleet.owner')}: {station.owner_email or station.owner_uid}")
        online = station.is_online_at(datetime.now(timezone.utc))
        if not online:
            self._rx.setText(tr("fleet.offline"))
        elif station.capture_state == "recording":
            self._rx.setText(tr("header.rx_receiving"))
        elif station.desired.running:
            self._rx.setText(tr("header.rx_active"))
        else:
            self._rx.setText(tr("header.rx_off"))


__all__ = ["StationWorkspacePage"]
