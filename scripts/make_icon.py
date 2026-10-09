"""Draw a simple resolution-independent application glyph using the existing Qt dependency."""
from pathlib import Path
import struct
import sys
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QApplication


def main():
    app = QApplication.instance() or QApplication([])
    frames = []
    for size in (16, 24, 32, 48, 64, 128, 256):
        image = QImage(size, size, QImage.Format.Format_RGBA8888)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(size / 256, size / 256)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#182331"))
        painter.drawRoundedRect(QRectF(0, 0, 256, 256), 48, 48)
        painter.setBrush(QColor("#42cdbf"))
        for x, y, r in ((61, 73, 20), (135, 66, 29), (179, 125, 18), (81, 132, 13)):
            painter.drawEllipse(QRectF(x - r, y - r, 2 * r, 2 * r))
        painter.setPen(QPen(QColor("#f4f8fc"), 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        painter.drawLine(53, 199, 203, 199)
        painter.drawLine(53, 180, 53, 218)
        painter.drawLine(203, 180, 203, 218)
        painter.end()
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        frames.append((size, bytes(data)))
    out = bytearray(struct.pack("<HHH", 0, 1, len(frames)))
    offset = 6 + 16 * len(frames)
    for size, data in frames:
        out.extend(struct.pack("<BBBBHHII", 0 if size == 256 else size, 0 if size == 256 else size, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    out.extend(b"".join(data for size, data in frames))
    (Path(__file__).resolve().parents[1] / "packaging" / "microscale.ico").write_bytes(out)


if __name__ == "__main__":
    main()
