"""Generate deterministic PRANA ELEX Windows installer artwork."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPainterPath, QPen


ROOT = Path(__file__).resolve().parent
NAVY = QColor("#12343F")
NAVY_LIGHT = QColor("#1C4652")
TEAL = QColor("#00A2AD")
WHITE = QColor("#FFFFFF")
MUTED = QColor("#A9C5CC")


def _font(size: int, weight: QFont.Weight = QFont.Weight.DemiBold) -> QFont:
    font = QFont("Segoe UI", size)
    font.setWeight(weight)
    return font


def _draw_mark(painter: QPainter, rect: QRectF, *, show_subtitle: bool = False) -> None:
    radius = rect.width() * 0.20
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(NAVY)
    painter.drawRoundedRect(rect, radius, radius)

    accent = QRectF(
        rect.left() + rect.width() * 0.10,
        rect.top() + rect.height() * 0.10,
        rect.width() * 0.80,
        rect.height() * 0.12,
    )
    painter.setBrush(TEAL)
    painter.drawRoundedRect(accent, accent.height() / 2, accent.height() / 2)

    painter.setPen(WHITE)
    font = _font(max(10, int(rect.width() * 0.30)), QFont.Weight.Bold)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, rect.width() * 0.012)
    painter.setFont(font)
    painter.drawText(rect.adjusted(0, rect.height() * 0.05, 0, 0), Qt.AlignmentFlag.AlignCenter, "PE")

    if show_subtitle:
        painter.setPen(MUTED)
        painter.setFont(_font(max(7, int(rect.width() * 0.075)), QFont.Weight.Medium))
        painter.drawText(
            rect.adjusted(0, rect.height() * 0.62, 0, 0),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            "PRANA ELEX",
        )


def _image(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    margin = max(1, round(size * 0.04))
    _draw_mark(painter, QRectF(margin, margin, size - margin * 2, size - margin * 2))
    painter.end()
    return image


def _png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise RuntimeError("Qt could not encode PNG artwork")
    return bytes(data)


def _write_icon(path: Path) -> None:
    sizes = (16, 32, 48, 64, 256)
    frames = [(size, _png_bytes(_image(size))) for size in sizes]
    header_size = 6 + 16 * len(frames)
    offset = header_size
    entries = []
    payload = []
    for size, png in frames:
        dimension = 0 if size == 256 else size
        entries.append(
            struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(png), offset)
        )
        payload.append(png)
        offset += len(png)
    path.write_bytes(struct.pack("<HHH", 0, 1, len(frames)) + b"".join(entries) + b"".join(payload))


def _write_banner(path: Path) -> None:
    width, height = 430, 824
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(NAVY)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(NAVY_LIGHT)
    painter.drawEllipse(QPointF(width * 0.12, height * 0.23), width * 0.72, width * 0.72)

    wave = QPainterPath()
    wave.moveTo(0, height * 0.72)
    wave.cubicTo(width * 0.28, height * 0.61, width * 0.62, height * 0.82, width, height * 0.66)
    wave.lineTo(width, height)
    wave.lineTo(0, height)
    wave.closeSubpath()
    painter.setBrush(TEAL)
    painter.drawPath(wave)

    _draw_mark(painter, QRectF(74, 92, 282, 282), show_subtitle=False)
    painter.setPen(WHITE)
    title = _font(28, QFont.Weight.Bold)
    title.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.2)
    painter.setFont(title)
    painter.drawText(QRectF(38, 420, width - 76, 56), Qt.AlignmentFlag.AlignCenter, "PRANA ELEX")

    painter.setPen(MUTED)
    subtitle = _font(12, QFont.Weight.Medium)
    subtitle.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.3)
    painter.setFont(subtitle)
    painter.drawText(
        QRectF(42, 484, width - 84, 70),
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        "MARINE VHF\nTRANSCRIPTION & TRANSLATION",
    )

    painter.setPen(QPen(QColor("#D7F1F3"), 2))
    painter.drawLine(90, 584, width - 90, 584)
    painter.setPen(WHITE)
    painter.setFont(_font(11, QFont.Weight.Medium))
    painter.drawText(
        QRectF(45, 610, width - 90, 100),
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        "Secure desktop client\nPowered by PRANA API",
    )
    painter.end()
    if not image.save(str(path), "PNG"):
        raise RuntimeError("Qt could not save installer banner")


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    ROOT.mkdir(parents=True, exist_ok=True)
    _write_icon(ROOT / "prana-elex.ico")
    _write_banner(ROOT / "wizard-banner.png")
    logo = _image(116)
    if not logo.save(str(ROOT / "wizard-logo.png"), "PNG"):
        raise RuntimeError("Qt could not save installer logo")
    print(f"Generated installer assets in {ROOT}")
    app.quit()


if __name__ == "__main__":
    main()
