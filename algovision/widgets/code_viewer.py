"""Code Viewer (PRD 8.3) - pseudocode with synchronized line highlighting."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame
)

from ..theme.palette import Theme


class CodeViewer(QWidget):
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._lines: list[str] = []
        self._row_widgets: list[tuple[QFrame, QLabel, QLabel]] = []
        self._active: set[int] = set()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.container = QWidget()
        self.vbox = QVBoxLayout(self.container)
        self.vbox.setContentsMargins(4, 4, 4, 4)
        self.vbox.setSpacing(2)
        self.vbox.addStretch(1)
        self.scroll.setWidget(self.container)
        outer.addWidget(self.scroll)

    def set_code(self, lines: list[str]) -> None:
        self._lines = lines
        self._active = set()
        # clear
        for frame, _, _ in self._row_widgets:
            frame.deleteLater()
        self._row_widgets = []
        # insert before the trailing stretch
        for idx, text in enumerate(lines):
            row = QFrame()
            row.setProperty("codeRow", True)
            hb = QHBoxLayout(row)
            hb.setContentsMargins(8, 3, 8, 3)
            hb.setSpacing(10)
            num = QLabel(str(idx + 1))
            num.setFixedWidth(20)
            num.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            code = QLabel(text)
            code.setTextFormat(Qt.TextFormat.PlainText)
            hb.addWidget(num)
            hb.addWidget(code, 1)
            self.vbox.insertWidget(self.vbox.count() - 1, row)
            self._row_widgets.append((row, num, code))
        self._restyle()

    def highlight(self, line_indices) -> None:
        self._active = set(line_indices or ())
        self._restyle()
        # scroll the first highlighted line into view
        for idx in sorted(self._active):
            if 0 <= idx < len(self._row_widgets):
                self.scroll.ensureWidgetVisible(self._row_widgets[idx][0], 0, 40)
                break

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._restyle()

    def _restyle(self) -> None:
        t = self.theme
        mono = "font-family:'Consolas','DejaVu Sans Mono',monospace; font-size:12px;"
        for idx, (row, num, code) in enumerate(self._row_widgets):
            if idx in self._active:
                row.setStyleSheet(
                    f"background:{t.accent_soft}; border-left:3px solid {t.accent_2};"
                    " border-radius:4px;")
                num.setStyleSheet(f"color:{t.accent_2}; {mono} font-weight:bold;")
                code.setStyleSheet(f"color:{t.text_primary}; {mono} font-weight:bold;")
            else:
                row.setStyleSheet("background:transparent; border-left:3px solid transparent;")
                num.setStyleSheet(f"color:{t.text_muted}; {mono}")
                code.setStyleSheet(f"color:{t.text_secondary}; {mono}")
