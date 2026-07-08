"""Timeline Navigation (PRD 7.6).

A custom-painted horizontal strip of recorded operations.  It scales cleanly
from 10 to several-thousand operations (single paint pass, no per-op widgets),
highlights the executed region, and lets the user click or drag to jump to any
previously executed operation.  Each entry is an "Operation" (PRD wording).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from ..theme.palette import Theme


class _Track(QWidget):
    seekRequested = pyqtSignal(int)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._total = 1
        self._current = 0
        self.setMinimumHeight(46)
        self.setStyleSheet("background: transparent;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def configure(self, total: int, current: int) -> None:
        self._total = max(1, total)
        self._current = current
        self.update()

    def set_current(self, current: int) -> None:
        self._current = current
        self.update()

    # painting ----------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.theme
        w = self.width()
        h = self.height()
        pad = 10
        track_h = 10
        y = (h - track_h) / 2
        track_w = w - 2 * pad

        # base track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(t.border)))
        p.drawRoundedRect(QRectF(pad, y, track_w, track_h), 5, 5)

        # executed portion
        frac = self._current / max(1, self._total - 1) if self._total > 1 else 1.0
        filled = track_w * frac
        p.setBrush(QBrush(QColor(t.accent_2)))
        p.drawRoundedRect(QRectF(pad, y, max(track_h, filled), track_h), 5, 5)

        # operation ticks (only when sparse enough to read)
        if self._total <= 60:
            p.setPen(QPen(QColor(t.canvas_bg), 1))
            for i in range(self._total):
                x = pad + track_w * (i / max(1, self._total - 1))
                p.drawLine(int(x), int(y), int(x), int(y + track_h))

        # playhead
        px = pad + filled
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(t.accent)))
        p.drawEllipse(QRectF(px - 8, y + track_h / 2 - 8, 16, 16))
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(QRectF(px - 3, y + track_h / 2 - 3, 6, 6))
        p.end()

    # interaction --------------------------------------------------------
    def _pos_to_index(self, x: float) -> int:
        pad = 10
        track_w = self.width() - 2 * pad
        frac = (x - pad) / max(1, track_w)
        frac = min(1.0, max(0.0, frac))
        return round(frac * (self._total - 1))

    def mousePressEvent(self, e):
        self.seekRequested.emit(self._pos_to_index(e.position().x()))

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self.seekRequested.emit(self._pos_to_index(e.position().x()))


class Timeline(QWidget):
    seekRequested = pyqtSignal(int)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._total = 1

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        header = QHBoxLayout()
        self.op_label = QLabel("Operation 1")
        self.op_label.setStyleSheet(f"color:{theme.accent}; font-weight:700;")
        self.op_detail = QLabel("")
        self.op_detail.setProperty("role", "muted")
        header.addWidget(self.op_label)
        header.addSpacing(8)
        header.addWidget(self.op_detail, 1)

        self.prev_btn = QPushButton("‹ Prev")
        self.next_btn = QPushButton("Next ›")
        for b in (self.prev_btn, self.next_btn):
            b.setProperty("variant", "ghost")
            b.setFixedHeight(26)
        self.prev_btn.clicked.connect(self._go_prev)
        self.next_btn.clicked.connect(self._go_next)
        header.addWidget(self.prev_btn)
        header.addWidget(self.next_btn)
        lay.addLayout(header)

        self.track = _Track(theme)
        self.track.seekRequested.connect(self.seekRequested)
        lay.addWidget(self.track)

    def configure(self, total: int, current: int) -> None:
        self._total = total
        self.track.configure(total, current)

    def update_current(self, index: int, op_number: int, label: str) -> None:
        self.track.set_current(index)
        self.op_label.setText(f"Operation {op_number}")
        self.op_detail.setText(label or "")

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.track.theme = theme
        self.op_label.setStyleSheet(f"color:{theme.accent}; font-weight:700;")
        self.track.update()

    def _go_prev(self):
        self.seekRequested.emit(max(0, self.track._current - 1))

    def _go_next(self):
        self.seekRequested.emit(min(self._total - 1, self.track._current + 1))
