"""Speed, depth and heading across the top of the Control tab.

Ported from `control/presentation/widgets/instruments/` in the Flutter app.
Painted colours are read from the theme at paint time, never baked in.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from prana_windows.ui.i18n import language, tr
from prana_windows.ui.icons import GlyphLabel
from prana_windows.ui.simulation import TelemetrySnapshot, compass_point
from prana_windows.ui.theme import theme, token


def ink(name: str, alpha: float = 1.0) -> QColor:
    """A theme token as a QColor, optionally translucent."""
    colour = QColor(token(name))
    colour.setAlphaF(alpha)
    return colour


class InstrumentCell(QFrame):
    """One reading: a caption, a large number and its unit."""

    def __init__(self, icon: str, parent=None):
        super().__init__(parent)
        self.setObjectName("InstrumentCell")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(6)

        caption = QHBoxLayout()
        caption.setSpacing(6)
        caption.addWidget(GlyphLabel(icon, role="accent", size=14))
        self._label = QLabel()
        self._label.setObjectName("InstrumentLabel")
        caption.addWidget(self._label, 1)
        layout.addLayout(caption)

        reading = QHBoxLayout()
        reading.setSpacing(4)
        self._value = QLabel("—")
        self._value.setObjectName("InstrumentValue")
        reading.addWidget(self._value, 0, Qt.AlignBaseline)
        self._unit = QLabel()
        self._unit.setObjectName("InstrumentUnit")
        reading.addWidget(self._unit, 0, Qt.AlignBaseline)
        reading.addStretch(1)
        layout.addLayout(reading)
        layout.addStretch(1)

    def set_label(self, text: str) -> None:
        self._label.setText(text.upper())

    def set_reading(self, value: str, unit: str) -> None:
        self._value.setText(value)
        self._unit.setText(unit)
        self._unit.setVisible(bool(unit))

    def value_text(self) -> str:
        return self._value.text()

    def unit_text(self) -> str:
        return self._unit.text()


class InstrumentStrip(QWidget):
    """Three cells of one size; one row while they fit, stacked otherwise."""

    MINIMUM_CELL = 88
    GAP = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.speed = InstrumentCell("speedometer")
        self.depth = InstrumentCell("format-vertical-align-bottom")
        self.heading = InstrumentCell("compass-outline")
        self._cells = (self.speed, self.depth, self.heading)
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(self.GAP)
        self._one_row: bool | None = None
        self.set_one_row(True)
        language.changed.connect(self._retranslate)
        self._retranslate()
        self.set_snapshot(None)

    @classmethod
    def fits_one_row(cls, width: int) -> bool:
        return width >= cls.MINIMUM_CELL * 3 + cls.GAP * 2

    def set_one_row(self, one_row: bool) -> None:
        if one_row == self._one_row:
            return
        self._one_row = one_row
        for cell in self._cells:
            self._grid.removeWidget(cell)
        for index, cell in enumerate(self._cells):
            if one_row:
                self._grid.addWidget(cell, 0, index)
                self._grid.setColumnStretch(index, 1)
            else:
                self._grid.addWidget(cell, index, 0)
                self._grid.setColumnStretch(index, 1 if index == 0 else 0)

    def is_one_row(self) -> bool:
        return bool(self._one_row)

    def set_snapshot(self, sample: TelemetrySnapshot | None) -> None:
        if sample is None:
            for cell in self._cells:
                cell.set_reading("—", "")
            return
        self.speed.set_reading(f"{sample.speed_knots:.1f}", "KT")
        self.depth.set_reading(f"{sample.depth_metres:.1f}", "M")
        # Three digits, as a bearing is written: 034, not 34. The point only;
        # nothing here knows whether the heading is true or magnetic.
        degrees = math.floor(sample.heading_degrees + 0.5) % 360
        self.heading.set_reading(f"{degrees:03d}°", compass_point(sample.heading_degrees))

    def _retranslate(self, *_args) -> None:
        self.speed.set_label(tr("sim.speed"))
        self.depth.set_label(tr("sim.depth"))
        self.heading.set_label(tr("sim.heading"))


class CompassRose(QWidget):
    """Heading on a fixed card with a turning needle, so north is found at a glance."""

    def __init__(self, size: int = 48, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.degrees: float | None = None
        theme.changed.connect(self.update)

    def set_degrees(self, degrees: float | None) -> None:
        if degrees != self.degrees:
            self.degrees = degrees
            self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        centre = QPointF(self.width() / 2, self.height() / 2)
        radius = min(self.width(), self.height()) / 2 - 1
        if radius <= 0:
            return

        # The backdrop keeps the card legible over the chart grid.
        painter.setPen(Qt.NoPen)
        painter.setBrush(ink("surface", 0.86))
        painter.drawEllipse(centre, radius + 1, radius + 1)
        painter.setBrush(ink("surface_sunken", 0.45))
        painter.setPen(QPen(ink("border"), 1))
        painter.drawEllipse(centre, radius, radius)

        for angle in range(0, 360, 15):
            principal = angle % 45 == 0
            length = radius * (0.16 if principal else 0.09)
            radians = math.radians(angle)
            unit = QPointF(math.sin(radians), -math.cos(radians))
            painter.setPen(QPen(ink("text_muted", 0.55), 1.6 if principal else 1))
            painter.drawLine(centre + unit * (radius - length), centre + unit * (radius - 2))

        font = QFont(self.font())
        font.setPixelSize(max(6, round(radius * 0.24)))
        font.setWeight(QFont.Bold)
        painter.setFont(font)
        painter.setPen(ink("text_secondary"))
        for angle, letter in ((0, "N"), (90, "E"), (180, "S"), (270, "W")):
            radians = math.radians(angle)
            at = centre + QPointF(math.sin(radians), -math.cos(radians)) * (radius * 0.68)
            painter.drawText(QRectF(at.x() - 8, at.y() - 8, 16, 16), Qt.AlignCenter, letter)

        if self.degrees is None:
            return
        painter.save()
        painter.translate(centre)
        painter.rotate(self.degrees)
        painter.setPen(Qt.NoPen)
        reach = radius * 0.58
        head = QPainterPath(QPointF(0, -reach))
        head.lineTo(radius * 0.09, 0)
        head.lineTo(-radius * 0.09, 0)
        head.closeSubpath()
        painter.setBrush(ink("accent"))
        painter.drawPath(head)
        tail = QPainterPath(QPointF(0, reach * 0.62))
        tail.lineTo(radius * 0.07, 0)
        tail.lineTo(-radius * 0.07, 0)
        tail.closeSubpath()
        painter.setBrush(ink("text_muted", 0.35))
        painter.drawPath(tail)
        painter.restore()
        painter.setBrush(ink("accent"))
        painter.drawEllipse(centre, radius * 0.06, radius * 0.06)


__all__ = ["CompassRose", "InstrumentCell", "InstrumentStrip", "ink"]
