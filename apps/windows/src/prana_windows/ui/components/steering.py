"""The simulated helm: mode switch, rudder scale and steering wheel.

Ported from `control_widget.dart`, `rudder_scale.dart` and `steering_wheel.dart`.
Every control here edits a `SteeringState` and nothing else; there is no path
from this module to a Station.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from prana_windows.ui.components.instruments import ink
from prana_windows.ui.i18n import language, tr
from prana_windows.ui.icons import bind_icon, themed_icon
from prana_windows.ui.simulation import (
    NUDGE_DEGREES,
    ControlMode,
    SteeringState,
    direction,
    rudder_fraction,
)
from prana_windows.ui.theme import theme


def _repolish(widget: QWidget, name: str, value: str) -> None:
    if widget.property(name) == value:
        return
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class ModeSwitch(QWidget):
    """Auto or Manual, as two full-width targets that read as one switch."""

    mode_selected = Signal(object)  # ControlMode

    _ICONS = {ControlMode.AUTO: "autorenew", ControlMode.MANUAL: "hand-back-left-outline"}

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)
        self._title = QLabel()
        self._title.setObjectName("PanelLabel")
        root.addWidget(self._title)

        row = QHBoxLayout()
        row.setSpacing(10)
        self._group = QButtonGroup(self)
        self.buttons: dict[ControlMode, QPushButton] = {}
        for mode in ControlMode:
            button = QPushButton()
            button.setObjectName("ModeButton")
            button.setCheckable(True)
            button.setIconSize(QSize(18, 18))
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, m=mode: self.mode_selected.emit(m))
            self._group.addButton(button)
            self.buttons[mode] = button
            row.addWidget(button, 1)
        root.addLayout(row)

        self._mode = ControlMode.MANUAL
        language.changed.connect(self._retranslate)
        theme.changed.connect(self._paint_icons)
        self._retranslate()
        self.set_mode(ControlMode.MANUAL)

    def set_mode(self, mode: ControlMode) -> None:
        self._mode = mode
        for value, button in self.buttons.items():
            button.setChecked(value is mode)
            _repolish(button, "selected", "true" if value is mode else "false")
        self._paint_icons()

    def _paint_icons(self, *_args) -> None:
        for value, button in self.buttons.items():
            role = "on_accent" if value is self._mode else "text_secondary"
            button.setIcon(themed_icon(self._ICONS[value], role=role, active_role=role))

    def _retranslate(self, *_args) -> None:
        self._title.setText(tr("sim.control"))
        self.buttons[ControlMode.AUTO].setText(tr("sim.auto"))
        self.buttons[ControlMode.MANUAL].setText(tr("sim.manual"))


class RudderBar(QWidget):
    """How far over the helm is, on the +/-180 range the state actually allows."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(16)
        self.angle = 0.0
        theme.changed.connect(self.update)

    def set_angle(self, angle: float) -> None:
        self.angle = angle
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt override
        width = self.width()
        if width <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        track_height = 6.0
        top = (self.height() - track_height) / 2
        middle = width / 2
        fill = ink("accent") if self.isEnabled() else ink("text_muted")

        painter.setBrush(ink("surface_sunken"))
        painter.drawRoundedRect(QRectF(0, top, width, track_height), 3, 3)
        # Quarter marks, so the bar reads as a scale and not a progress bar.
        painter.setBrush(ink("border_strong"))
        for fraction in (0.25, 0.75):
            painter.drawRect(QRectF(width * fraction, top - 3, 1, track_height + 6))

        over = rudder_fraction(self.angle) * middle
        if abs(over) > 0.5:
            painter.setBrush(fill)
            left = middle + over if over < 0 else middle
            painter.drawRoundedRect(QRectF(left, top, abs(over), track_height), 3, 3)

        # Amidships, drawn over the fill so the centre never disappears.
        painter.setBrush(ink("border_strong"))
        painter.drawRect(QRectF(middle - 0.5, top - 4, 1, track_height + 8))
        painter.setBrush(fill)
        marker = min(max(middle + over, 4.0), width - 4.0)
        painter.drawEllipse(QPointF(marker, self.height() / 2), 5, 5)


class SteeringWheel(QWidget):
    """A wheel that turns under the mouse, against a bezel that does not."""

    changed = Signal()
    MAX_DIAMETER = 280

    def __init__(self, state: SteeringState, parent=None):
        super().__init__(parent)
        self.state = state
        self._dragging = False
        policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setMinimumSize(160, 160)
        self.setMaximumHeight(self.MAX_DIAMETER)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.OpenHandCursor)
        theme.changed.connect(self.update)

    def hasHeightForWidth(self) -> bool:  # noqa: N802 - Qt override
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802 - Qt override
        return min(width, self.MAX_DIAMETER)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override
        return QSize(self.MAX_DIAMETER, self.MAX_DIAMETER)

    def diameter(self) -> float:
        return min(self.width(), self.height(), self.MAX_DIAMETER)

    def _bearing(self, point: QPointF) -> float:
        return math.atan2(point.y() - self.height() / 2, point.x() - self.width() / 2)

    def _in_hub(self, point: QPointF) -> bool:
        centre = QPointF(self.width() / 2, self.height() / 2)
        offset = point - centre
        return math.hypot(offset.x(), offset.y()) < self.diameter() * 0.12

    def end_drag(self) -> None:
        self._dragging = False
        self.state.end_drag()

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        point = event.position()
        if event.button() != Qt.LeftButton or not self.state.manual or self._in_hub(point):
            return
        self._dragging = True
        self.state.begin_drag(self._bearing(point))
        self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self._dragging:
            self.state.drag(self._bearing(event.position()))
            self.changed.emit()

    def mouseReleaseEvent(self, _event) -> None:  # noqa: N802 - Qt override
        self.end_drag()
        self.setCursor(Qt.OpenHandCursor)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        step = {Qt.Key_Left: -NUDGE_DEGREES, Qt.Key_Right: NUDGE_DEGREES}.get(event.key())
        if step is None or not self.state.manual:
            super().keyPressEvent(event)
            return
        self.state.adjust(step)
        self.changed.emit()

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.end_drag()
        super().hideEvent(event)

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        radius = self.diameter() * 0.38
        enabled = self.isEnabled()
        angle = self.state.angle
        # The wheel is furniture, not a readout, so it takes the muted ink;
        # full-strength text made it the brightest thing on a dark bridge.
        wheel_ink = ink("text_muted") if enabled else ink("text_muted", 0.45)
        live = ink("accent") if enabled else ink("text_muted", 0.45)

        painter.translate(self.width() / 2, self.height() / 2)

        # Fixed bezel: what the angle is read against.
        painter.setPen(Qt.NoPen)
        painter.setBrush(ink("surface_sunken", 0.55))
        painter.drawEllipse(QPointF(0, 0), radius * 1.28, radius * 1.28)
        for degrees in range(0, 360, 15):
            major = degrees % 45 == 0
            radians = math.radians(degrees - 90)
            unit = QPointF(math.cos(radians), math.sin(radians))
            pen = QPen(ink("border_strong"), 1.6 if major else 1)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(unit * (radius * (1.16 if major else 1.20)), unit * (radius * 1.26))

        if abs(angle) > 0.5:
            pen = QPen(ink("accent", 0.75) if enabled else ink("text_muted", 0.34), 3)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            r = radius * 1.22
            # Qt measures arcs anticlockwise from three o'clock in 1/16 degree.
            painter.drawArc(QRectF(-r, -r, 2 * r, 2 * r), 90 * 16, round(-angle * 16))

        index = QPainterPath(QPointF(0, -radius * 1.34))
        index.lineTo(-4.5, -radius * 1.44)
        index.lineTo(4.5, -radius * 1.44)
        index.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(live)
        painter.drawPath(index)

        painter.rotate(angle)
        spoke = QPen(wheel_ink, radius * 0.075)
        spoke.setCapStyle(Qt.RoundCap)
        painter.setPen(spoke)
        for i in range(8):
            radians = i * math.pi / 4
            painter.drawLine(QPointF(0, 0), QPointF(math.cos(radians), math.sin(radians)) * radius)
        painter.setPen(QPen(wheel_ink, radius * 0.11))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(0, 0), radius, radius)

        # Handles, with a longer king spoke so the wheel reads as turned.
        for i in range(8):
            radians = i * math.pi / 4 - math.pi / 2
            king = i == 0
            unit = QPointF(math.cos(radians), math.sin(radians))
            handle = QPen(live if king else wheel_ink, radius * (0.11 if king else 0.08))
            handle.setCapStyle(Qt.RoundCap)
            painter.setPen(handle)
            painter.drawLine(unit * radius, unit * (radius * (1.16 if king else 1.10)))

        painter.setPen(Qt.NoPen)
        painter.setBrush(live)
        painter.drawEllipse(QPointF(0, 0), radius * 0.22, radius * 0.22)
        painter.setBrush(ink("surface_sunken"))
        painter.drawEllipse(QPointF(0, 0), radius * 0.10, radius * 0.10)


class SteeringPanel(QWidget):
    """Angle readout, rudder scale, wheel and the nudge buttons around it."""

    changed = Signal()

    def __init__(self, state: SteeringState, parent=None):
        super().__init__(parent)
        self.state = state
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QHBoxLayout()
        self._title = QLabel()
        self._title.setObjectName("PanelLabel")
        header.addWidget(self._title, 1)
        self.chip = QLabel()
        self.chip.setObjectName("SteeringStateChip")
        header.addWidget(self.chip)
        root.addLayout(header)

        card = QFrame()
        card.setObjectName("ControlPanel")
        body = QVBoxLayout(card)
        body.setContentsMargins(16, 16, 16, 16)
        body.setSpacing(14)

        reading = QHBoxLayout()
        reading.setSpacing(12)
        reading.addStretch(1)
        self.angle = QLabel()
        self.angle.setObjectName("SteeringAngle")
        reading.addWidget(self.angle, 0, Qt.AlignVCenter)
        self.direction = QLabel()
        self.direction.setObjectName("DirectionPill")
        reading.addWidget(self.direction, 0, Qt.AlignVCenter)
        reading.addStretch(1)
        body.addLayout(reading)

        scale = QVBoxLayout()
        scale.setSpacing(6)
        labels = QHBoxLayout()
        self._port = QLabel()
        self._port.setObjectName("RudderLabel")
        zero = QLabel("0")
        zero.setObjectName("RudderLabel")
        self._starboard = QLabel()
        self._starboard.setObjectName("RudderLabel")
        self._starboard.setAlignment(Qt.AlignRight)
        labels.addWidget(self._port, 1)
        labels.addWidget(zero)
        labels.addWidget(self._starboard, 1)
        scale.addLayout(labels)
        self.rudder = RudderBar()
        scale.addWidget(self.rudder)
        body.addLayout(scale)

        self.auto_note = QLabel()
        self.auto_note.setObjectName("SteeringAutoNote")
        self.auto_note.setAlignment(Qt.AlignCenter)
        self.auto_note.setWordWrap(True)
        body.addWidget(self.auto_note)

        self.wheel = SteeringWheel(state)
        self.wheel.changed.connect(self._changed)
        body.addWidget(self.wheel)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.left = QPushButton()
        self.left.setObjectName("NudgeButton")
        bind_icon(self.left, "rotate-left", role="text_secondary")
        self.left.clicked.connect(lambda: self._act(lambda: state.adjust(-NUDGE_DEGREES)))
        self.center = QPushButton()
        self.center.setObjectName("CenterButton")
        bind_icon(self.center, "adjust", role="accent")
        self.center.clicked.connect(lambda: self._act(state.center))
        self.right = QPushButton()
        self.right.setObjectName("NudgeButton")
        bind_icon(self.right, "rotate-right", role="text_secondary")
        self.right.clicked.connect(lambda: self._act(lambda: state.adjust(NUDGE_DEGREES)))
        for button in (self.left, self.center, self.right):
            button.setCursor(Qt.PointingHandCursor)
        # Nudges are icon-only, so their glyph carries the whole target.
        self.left.setIconSize(QSize(22, 22))
        self.right.setIconSize(QSize(22, 22))
        self.center.setIconSize(QSize(18, 18))
        buttons.addWidget(self.left)
        buttons.addWidget(self.center, 1)
        buttons.addWidget(self.right)
        body.addLayout(buttons)
        root.addWidget(card)

        language.changed.connect(self.refresh)
        self.refresh()

    def _act(self, action) -> None:
        action()
        self._changed()

    def _changed(self) -> None:
        self.refresh()
        self.changed.emit()

    def refresh(self, *_args) -> None:
        manual = self.state.manual
        angle = self.state.angle
        self._title.setText(tr("sim.wheel"))
        self.chip.setText((tr("sim.manual") if manual else tr("sim.auto")).upper())
        _repolish(self.chip, "manual", "true" if manual else "false")
        # Whole degrees, rounded away from zero like Dart, and never "-0°".
        whole = int(math.copysign(math.floor(abs(angle) + 0.5), angle))
        self.angle.setText(f"{whole}°")
        self.direction.setText(tr(f"sim.{direction(angle)}"))
        self._port.setText(tr("sim.left").upper())
        self._starboard.setText(tr("sim.right").upper())
        self.auto_note.setText(tr("sim.auto_note"))
        self.auto_note.setVisible(not manual)
        self.center.setText(tr("sim.center"))
        self.left.setToolTip(tr("sim.left"))
        self.right.setToolTip(tr("sim.right"))
        for widget in (self.angle, self.rudder, self.wheel, self.left, self.center, self.right):
            widget.setEnabled(manual)
        if not manual:
            self.wheel.end_drag()
        self.rudder.set_angle(angle)
        self.wheel.update()


__all__ = ["ModeSwitch", "RudderBar", "SteeringPanel", "SteeringWheel"]
