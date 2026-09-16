from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from prana_core.console.models import StationSummary
from prana_windows.ui.brand import BrandMark
from prana_windows.ui.components.station_row import StationRow
from prana_windows.ui.components.theme_toggle import ThemeToggle
from prana_windows.ui.i18n import language, tr
from prana_windows.ui.icons import bind_icon


class FleetPage(QWidget):
    """The Station list an operator starts from."""

    attach_requested = Signal(str)
    filter_changed = Signal(str, bool)
    refresh_requested = Signal()
    account_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FleetPage")
        self._rows: dict[str, StationRow] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(14)

        header = QHBoxLayout()
        # Every Flutter header carries the mark before its title
        # (apps/android/lib/core/responsive.dart); the fleet page is the
        # desktop's home screen, so it does the same.
        header.addWidget(BrandMark(36), 0, Qt.AlignTop)
        header.addSpacing(8)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self._title = QLabel()
        self._title.setObjectName("FleetTitle")
        self._subtitle = QLabel()
        self._subtitle.setObjectName("FleetSubtitle")
        self._subtitle.setWordWrap(True)
        titles.addWidget(self._title)
        titles.addWidget(self._subtitle)
        header.addLayout(titles, stretch=1)

        self._locale = QComboBox()
        self._locale.setObjectName("LocaleSelector")
        self._locale.addItem("EN", "en")
        self._locale.addItem("VI", "vi")
        self._locale.setCurrentIndex(0 if language.locale == "en" else 1)
        self._locale.currentIndexChanged.connect(
            lambda: language.set_locale(self._locale.currentData())
        )
        header.addWidget(self._locale, 0, Qt.AlignTop)
        header.addWidget(ThemeToggle(), 0, Qt.AlignTop)

        self._account = QPushButton()
        self._account.setObjectName("SettingsButton")
        self._account.setFixedSize(36, 36)
        bind_icon(self._account, "account-circle-outline", role="text_secondary")
        self._account.setIconSize(QSize(20, 20))
        self._account.setCursor(Qt.PointingHandCursor)
        self._account.clicked.connect(self.account_requested)
        header.addWidget(self._account, 0, Qt.AlignTop)
        root.addLayout(header)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        self._search = QLineEdit()
        self._search.setObjectName("FleetSearch")
        self._search.setClearButtonEnabled(True)
        # Debounced: each keystroke would otherwise be a fleet-wide query.
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(350)
        self._debounce.timeout.connect(self._emit_filter)
        self._search.textChanged.connect(lambda: self._debounce.start())
        self._search.returnPressed.connect(self._emit_filter)
        controls.addWidget(self._search, stretch=1)

        self._online_only = QCheckBox()
        self._online_only.toggled.connect(self._emit_filter)
        controls.addWidget(self._online_only)

        self._refresh = QPushButton()
        self._refresh.clicked.connect(self.refresh_requested)
        controls.addWidget(self._refresh)
        root.addLayout(controls)

        self._search_hint = QLabel()
        self._search_hint.setObjectName("FleetSearchHint")
        self._search_hint.setWordWrap(True)
        root.addWidget(self._search_hint)

        self._message = QLabel()
        self._message.setObjectName("FleetMessage")
        self._message.setWordWrap(True)
        self._message.setVisible(False)
        root.addWidget(self._message)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("FleetScroll")
        self._scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("FleetScrollContent")
        self._list = QVBoxLayout(content)
        self._list.setContentsMargins(0, 0, 8, 0)
        self._list.setSpacing(8)
        self._empty = QLabel()
        self._empty.setObjectName("FleetEmpty")
        self._empty.setAlignment(Qt.AlignCenter)
        self._list.addWidget(self._empty)
        self._list.addStretch()
        self._scroll.setWidget(content)
        root.addWidget(self._scroll, stretch=1)

        language.changed.connect(self._retranslate)
        self._retranslate()

    def _emit_filter(self) -> None:
        self._debounce.stop()
        self.filter_changed.emit(self._search.text().strip(), self._online_only.isChecked())

    def _retranslate(self, *_args) -> None:
        self._title.setText(tr("fleet.title"))
        self._subtitle.setText(tr("fleet.subtitle"))
        self._search.setPlaceholderText(tr("fleet.search"))
        self._search_hint.setText(tr("fleet.search_hint"))
        self._online_only.setText(tr("fleet.online_only"))
        self._refresh.setText(tr("common.refresh"))
        self._empty.setText(tr("fleet.empty"))
        index = self._locale.findData(language.locale)
        if index >= 0 and index != self._locale.currentIndex():
            self._locale.blockSignals(True)
            self._locale.setCurrentIndex(index)
            self._locale.blockSignals(False)
        for row in self._rows.values():
            row._retranslate()

    def set_stations(self, stations: list[StationSummary]) -> None:
        """Reconcile rows in place so the list does not flicker every 10s."""
        seen = set()
        for position, station in enumerate(stations):
            seen.add(station.station_id)
            row = self._rows.get(station.station_id)
            if row is None:
                row = StationRow(station)
                row.attach_requested.connect(self.attach_requested)
                self._rows[station.station_id] = row
            else:
                row.update_station(station)
            current = self._list.indexOf(row)
            if current != position:
                if current >= 0:
                    self._list.takeAt(current)
                self._list.insertWidget(position, row)
        for station_id in list(self._rows):
            if station_id not in seen:
                row = self._rows.pop(station_id)
                self._list.removeWidget(row)
                row.deleteLater()
        self._empty.setVisible(not stations)

    def set_message(self, message: str) -> None:
        self._message.setText(message)
        self._message.setVisible(bool(message))

    def set_loading(self, loading: bool) -> None:
        self._refresh.setEnabled(not loading)
        self._refresh.setText(tr("fleet.loading") if loading else tr("common.refresh"))


__all__ = ["FleetPage"]
