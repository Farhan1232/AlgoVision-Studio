"""Code Viewer (PRD 8.3) - pseudocode with synchronized line highlighting."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame
)

from ..theme.palette import Theme
from ..theme import scale as uiscale


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
        # Long pseudocode lines word-wrap onto the next line (see below) instead
        # of running off the right edge, so nothing is ever clipped - the fix for
        # the "Code Viewer clips long pseudocode" feedback.  Only vertical
        # scrolling remains (PRD 8.3 "scrollable pseudocode for longer algorithms").
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
        # clear - remove from the layout immediately (deleteLater alone is async
        # and would leave the previous algorithm's code visible until the next
        # event-loop pass, stacking two algorithms' pseudocode).
        for frame, _, _ in self._row_widgets:
            self.vbox.removeWidget(frame)
            frame.setParent(None)
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
            # Wrap long lines so the whole statement is always visible in narrow
            # panels (e.g. Comparison Mode) rather than being cut off on the right.
            code.setWordWrap(True)
            code.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            num.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            hb.setAlignment(num, Qt.AlignmentFlag.AlignTop)
            hb.addWidget(num)
            hb.addWidget(code, 1)
            self.vbox.insertWidget(self.vbox.count() - 1, row)
            self._row_widgets.append((row, num, code))
        self._restyle()

    def highlight(self, line_indices) -> None:
        self._active = set(line_indices or ())
        self._restyle()
        # scroll the first highlighted line into view (vertically only)
        for idx in sorted(self._active):
            if 0 <= idx < len(self._row_widgets):
                self.scroll.ensureWidgetVisible(self._row_widgets[idx][0], 0, 40)
                break
        # Keep the code left-aligned: ensureWidgetVisible can nudge the view
        # sideways in a narrow panel (e.g. Comparison Mode), which would show
        # only the right half of each line.  Pin the horizontal scroll to 0 so
        # every line always reads from its start.
        self.scroll.horizontalScrollBar().setValue(0)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._restyle()

    def apply_scale(self, s: float) -> None:
        self._restyle()

    def _restyle(self) -> None:
        t = self.theme
        mono = ("font-family:'Consolas','DejaVu Sans Mono',monospace; "
                f"font-size:{uiscale.fs(12)}px;")
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
