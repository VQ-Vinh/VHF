"""The offline position chart and the card around it.

Ported from `map_widget.dart` and `gps_position_card.dart`. Deliberately a
coordinate instrument, not a geographic basemap: nothing on it may look like
something a navigator could steer by.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from prana_windows.ui.components.instruments import CompassRose, ink
from prana_windows.ui.components.sim_notice import SimNotice
from prana_windows.ui.i18n import language, tr
from prana_windows.ui.simulation import (
    CHART_DIVISIONS,
    CHART_INSET,
    TelemetrySnapshot,
    chart_division_metres,
    chart_point,
    format_dms,
    track_segments,
)
from prana_windows.ui.theme import theme


class ChartView(QWidget):
    """Grid, track and vessel, twice as wide as it is tall."""

    def __init__(self, parent=None):
        super().__init__(parent)
        policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setMinimumHeight(120)
        self.sample: TelemetrySnapshot | None = None
        self.track: list[tuple[float, float]] = []
        self.compass = CompassRose(72, self)
        theme.changed.connect(self.update)

    def hasHeightForWidth(self) -> bool:  # noqa: N802 - Qt override
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802 - Qt override
        return max(120, width // 2)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override
        return QSize(480, 240)

    def set_data(self, sample: TelemetrySnapshot | None, track: list[tuple[float, float]]) -> None:
        self.sample = sample
        self.track = track
        self.compass.set_degrees(None if sample is None else sample.heading_degrees)
        self.compass.setVisible(sample is not None)
        self.update()

    def vessel_point(self) -> QPointF | None:
        if self.sample is None:
            return None
        x, y = chart_point(self.sample.latitude, self.sample.longitude, self.width(), self.height())
        return QPointF(x, y)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.compass.move(self.width() - self.compass.width() - 8, 8)
        super().resizeEvent(event)

    def _badge(self, painter: QPainter, at: QPointF, text: str, pixel_size: int) -> None:
        font = QFont(self.font())
        font.setPixelSize(pixel_size)
        font.setWeight(QFont.Bold)
        metrics = QFontMetrics(font)
        rect = QRectF(at.x(), at.y(), metrics.horizontalAdvance(text) + 14, metrics.height() + 8)
        painter.setPen(Qt.NoPen)
        painter.setBrush(ink("surface", 0.86))
        painter.drawRoundedRect(rect, 6, 6)
        painter.setFont(font)
        painter.setPen(ink("text"))
        painter.drawText(rect, Qt.AlignCenter, text)

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width, height = self.width(), self.height()
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, width, height), 10, 10)
        painter.setClipPath(clip)
        painter.fillRect(self.rect(), ink("surface_sunken"))

        painter.setPen(QPen(ink("border"), 1))
        span_w, span_h = width - CHART_INSET * 2, height - CHART_INSET * 2
        for i in range(CHART_DIVISIONS + 1):
            x = CHART_INSET + span_w * i / CHART_DIVISIONS
            y = CHART_INSET + span_h * i / CHART_DIVISIONS
            painter.drawLine(QPointF(x, 0), QPointF(x, height))
            painter.drawLine(QPointF(0, y), QPointF(width, y))

        self._badge(painter, QPointF(10, 10), "↑ N", 12)
        self._scale_bar(painter, span_w)

        point = self.vessel_point()
        if point is None:
            return
        pen = QPen(ink("accent", 0.55), 2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        for segment in track_segments(self.track, width, height):
            path = QPainterPath(QPointF(*segment[0]))
            for x, y in segment[1:]:
                path.lineTo(x, y)
            painter.drawPath(path)

        painter.setPen(Qt.NoPen)
        painter.setBrush(ink("surface"))
        painter.drawEllipse(point, 19, 19)
        painter.setPen(QPen(ink("accent", 0.35), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(point, 19, 19)
        painter.save()
        painter.translate(point)
        painter.rotate(self.sample.heading_degrees)
        vessel = QPainterPath(QPointF(0, -14))
        vessel.lineTo(10, 12)
        vessel.lineTo(0, 7)
        vessel.lineTo(-10, 12)
        vessel.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(ink("accent"))
        painter.drawPath(vessel)
        painter.restore()

    def _scale_bar(self, painter: QPainter, span_width: float) -> None:
        length = span_width / CHART_DIVISIONS
        left, bottom = 12.0, self.height() - 14.0
        pen = QPen(ink("text"), 2)
        pen.setCapStyle(Qt.SquareCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(left, bottom), QPointF(left + length, bottom))
        for x in (left, left + length):
            painter.drawLine(QPointF(x, bottom - 4), QPointF(x, bottom))
        font = QFont(self.font())
        font.setPixelSize(10)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        latitude = None if self.sample is None else self.sample.latitude
        painter.drawText(QPointF(left, bottom - 7), f"{math.floor(chart_division_metres(latitude) + 0.5)} m")


class GpsPositionCard(QWidget):
    """The chart with the fix above it and when and where it came from below."""

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)
        self._title = QLabel()
        self._title.setObjectName("PanelLabel")
        root.addWidget(self._title)

        card = QFrame()
        card.setObjectName("ControlPanel")
        body = QVBoxLayout(card)
        body.setContentsMargins(12, 12, 12, 12)
        body.setSpacing(10)

        coordinates = QHBoxLayout()
        coordinates.setSpacing(16)
        self.latitude = QLabel("—")
        self.latitude.setObjectName("GpsCoordinate")
        self.longitude = QLabel("—")
        self.longitude.setObjectName("GpsCoordinate")
        coordinates.addWidget(self.latitude)
        coordinates.addWidget(self.longitude)
        coordinates.addStretch(1)
        body.addLayout(coordinates)

        self.chart = ChartView()
        body.addWidget(self.chart)

        fields = QGridLayout()
        fields.setHorizontalSpacing(16)
        fields.setVerticalSpacing(3)
        self._updated_label = QLabel()
        self._updated_label.setObjectName("FieldLabel")
        self.updated = QLabel("—")
        self.updated.setObjectName("FieldValue")
        self._source_label = QLabel()
        self._source_label.setObjectName("FieldLabel")
        # The readings are generated on this machine. Naming a real receiver
        # here would be the one lie a navigator cannot check from the screen.
        self.source = QLabel("—")
        self.source.setObjectName("FieldValue")
        fields.addWidget(self._updated_label, 0, 0)
        fields.addWidget(self.updated, 1, 0)
        fields.addWidget(self._source_label, 0, 1)
        fields.addWidget(self.source, 1, 1)
        fields.setColumnStretch(0, 1)
        fields.setColumnStretch(1, 1)
        body.addLayout(fields)

        self.notice = SimNotice("alert-outline")
        body.addWidget(self.notice)
        root.addWidget(card)

        self._sample: TelemetrySnapshot | None = None
        language.changed.connect(self._retranslate)
        self._retranslate()

    def set_data(self, sample: TelemetrySnapshot | None, track: list[tuple[float, float]]) -> None:
        self._sample = sample
        self.chart.set_data(sample, track)
        if sample is None:
            self.latitude.setText("—")
            self.longitude.setText("—")
            self.updated.setText("—")
        else:
            self.latitude.setText(format_dms(sample.latitude, positive="N", negative="S"))
            self.longitude.setText(format_dms(sample.longitude, positive="E", negative="W"))
            self.updated.setText(sample.timestamp.astimezone().strftime("%H:%M:%S"))
        self._retranslate()

    def _retranslate(self, *_args) -> None:
        self._title.setText(tr("sim.gps_position"))
        self._updated_label.setText(tr("sim.updated_at").upper())
        self._source_label.setText(tr("sim.source").upper())
        self.source.setText("—" if self._sample is None else tr("sim.source_simulated").upper())
        self.notice.set_text(tr("sim.map_notice"))


__all__ = ["ChartView", "GpsPositionCard"]
