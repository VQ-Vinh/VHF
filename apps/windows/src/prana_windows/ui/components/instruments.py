"""Speed, depth and heading across the top of the Control tab.

Ported from `control/presentation/widgets/instruments/` in the Flutter app.
Painted colours are read from the theme at paint time, never baked in.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
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

        # The unit sits on the number's baseline, as on the phone. QHBoxLayout
        # ignores Qt.AlignBaseline, so both labels are bottom-aligned and the
        # unit is lifted by the difference in descent; see _align_baselines.
        reading = QHBoxLayout()
        reading.setSpacing(4)
        self._value = QLabel("—")
        self._value.setObjectName("InstrumentValue")
        self._value.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        reading.addWidget(self._value, 0, Qt.AlignBottom)
        self._unit = QLabel()
        self._unit.setObjectName("InstrumentUnit")
        self._unit.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        reading.addWidget(self._unit, 0, Qt.AlignBottom)
        reading.addStretch(1)
        layout.addLayout(reading)
        layout.addStretch(1)
        self._align_baselines()

    def _align_baselines(self) -> None:
        self._value.ensurePolished()
        self._unit.ensurePolished()
        lift = QFontMetrics(self._value.font()).descent() - QFontMetrics(self._unit.font()).descent()
        self._unit.setContentsMargins(0, 0, 0, max(0, lift))

    def event(self, event) -> bool:  # noqa: A003 - Qt override
        # The stylesheet sets both fonts, and a theme or style change re-sets them.
        if event.type() in (QEvent.StyleChange, QEvent.FontChange, QEvent.Polish) and hasattr(self, "_unit"):
            self._align_baselines()
        return super().event(event)

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
        radius = min(self.width(), self.height()) / 2 - 3
        if radius <= 0:
            return

        # A soft drop and an opaque bezel lift the instrument off the chart grid.
        painter.setPen(Qt.NoPen)
        painter.setBrush(ink("navy", 0.22))
        painter.drawEllipse(centre + QPointF(0, radius * 0.05), radius + 1, radius + 1)
        bezel = QLinearGradient(0, centre.y() - radius, 0, centre.y() + radius)
        bezel.setColorAt(0.0, ink("surface"))
        bezel.setColorAt(1.0, ink("border_strong"))
        painter.setBrush(bezel)
        painter.setPen(QPen(ink("border_strong"), 1))
        painter.drawEllipse(centre, radius, radius)

        card = radius * 0.84
        face = QRadialGradient(centre, card)
        face.setColorAt(0.0, ink("surface"))
        face.setColorAt(1.0, ink("surface_sunken"))
        painter.setBrush(face)
        painter.setPen(QPen(ink("border"), 1))
        painter.drawEllipse(centre, card, card)

        # North is the fixed red mark on the bezel that the card is read from.
        mark = QPainterPath(centre + QPointF(0, -card + 1))
        mark.lineTo(centre + QPointF(-radius * 0.1, -radius + 1))
        mark.lineTo(centre + QPointF(radius * 0.1, -radius + 1))
        mark.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(ink("compass_north"))
        painter.drawPath(mark)

        # Graduations: every 5 degrees when there is room for them, longer at
        # 10 and 30, longest at the four cardinal points.
        step = 5 if card >= 24 else 10
        for angle in range(0, 360, step):
            if angle % 90 == 0:
                length, width, colour = 0.20, 1.6, ink("text_secondary")
            elif angle % 30 == 0:
                length, width, colour = 0.14, 1.2, ink("text_muted")
            elif angle % 10 == 0:
                length, width, colour = 0.09, 1.0, ink("text_muted", 0.75)
            else:
                length, width, colour = 0.05, 0.8, ink("text_muted", 0.5)
            if angle == 0:
                colour = ink("compass_north")
            radians = math.radians(angle)
            unit = QPointF(math.sin(radians), -math.cos(radians))
            painter.setPen(QPen(colour, width))
            painter.drawLine(centre + unit * (card * (1 - length)), centre + unit * (card - 1.5))

        # An eight-point rose under everything that moves, faceted light and
        # dark so it reads as relief. Faint, so the needle stays the reading.
        painter.save()
        painter.translate(centre)
        for angle in range(0, 360, 45):
            cardinal = angle % 90 == 0
            reach = card * (0.50 if cardinal else 0.34)
            half = card * (0.12 if cardinal else 0.08)
            painter.save()
            painter.rotate(angle)
            left = QPainterPath(QPointF(0, -reach))
            left.lineTo(-half, -half)
            left.lineTo(0, 0)
            left.closeSubpath()
            right = QPainterPath(QPointF(0, -reach))
            right.lineTo(half, -half)
            right.lineTo(0, 0)
            right.closeSubpath()
            painter.setBrush(ink("border_strong", 0.55 if cardinal else 0.4))
            painter.drawPath(left)
            painter.setBrush(ink("text_muted", 0.45 if cardinal else 0.3))
            painter.drawPath(right)
            painter.restore()
        painter.restore()

        font = QFont(self.font())
        font.setPixelSize(max(7, round(card * 0.3)))
        font.setWeight(QFont.Black)
        painter.setFont(font)
        box = card * 0.4
        for angle, letter in ((0, "N"), (90, "E"), (180, "S"), (270, "W")):
            radians = math.radians(angle)
            at = centre + QPointF(math.sin(radians), -math.cos(radians)) * (card * 0.62)
            painter.setPen(ink("compass_north") if letter == "N" else ink("text_secondary"))
            painter.drawText(QRectF(at.x() - box / 2, at.y() - box / 2, box, box), Qt.AlignCenter, letter)

        if self.degrees is not None:
            # A faceted lozenge: the lit half and the shaded half meet on the
            # centreline, so the needle reads as a solid pointer at a glance.
            painter.save()
            painter.translate(centre)
            painter.rotate(self.degrees)
            reach = card * 0.80
            tail = card * 0.52
            half = card * 0.13
            outline = QPen(ink("surface", 0.8), 0.8)
            for points, brush in (
                (((0, -reach), (-half, 0), (0, 0)), ink("accent")),
                (((0, -reach), (half, 0), (0, 0)), ink("accent_hover")),
                (((0, tail), (-half, 0), (0, 0)), ink("text_muted", 0.55)),
                (((0, tail), (half, 0), (0, 0)), ink("text_muted", 0.8)),
            ):
                path = QPainterPath(QPointF(*points[0]))
                for point in points[1:]:
                    path.lineTo(QPointF(*point))
                path.closeSubpath()
                painter.setPen(outline)
                painter.setBrush(brush)
                painter.drawPath(path)
            painter.restore()

        pivot = card * 0.11
        painter.setPen(QPen(ink("accent"), max(1.0, pivot * 0.35)))
        painter.setBrush(ink("surface"))
        painter.drawEllipse(centre, pivot, pivot)
        painter.setPen(Qt.NoPen)
        painter.setBrush(ink("accent"))
        painter.drawEllipse(centre, pivot * 0.4, pivot * 0.4)


__all__ = ["CompassRose", "InstrumentCell", "InstrumentStrip", "ink"]
