"""Numbered Block View (PRD Section 5).

A Matplotlib canvas that draws each array element as a rounded block containing
its value, with a fixed Position Indicator (index) beneath it.  Block size and
font scale automatically with the array length so the whole array is always
visible without scrolling (PRD 5.1 / 5.6).
"""

from __future__ import annotations

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch

from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from ..theme.palette import Theme, STATE_COLORS, STATE_DEFAULT, STATE_DISABLED
from ..core.frames import Frame


class ArrayView(QWidget):
    blockClicked = pyqtSignal(int)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._frame: Frame | None = None
        self._highlight: int | None = None
        self._step = 1.0
        self._width = 1.0

        self.figure = Figure(figsize=(6, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.canvas.mpl_connect("button_press_event", self._on_click)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.canvas)
        self._apply_bg()

        # Matplotlib text is sized in fixed points, but the canvas shrinks when
        # the window is compressed - so the font (and thus the block values)
        # must be recomputed on every resize, not only on a frame change, or the
        # values overflow their blocks on a short/narrow window.  Debounced so a
        # continuous drag doesn't redraw on every pixel.
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(45)
        self._resize_timer.timeout.connect(self._rerender)

    def resizeEvent(self, e):  # noqa: N802
        super().resizeEvent(e)
        self._resize_timer.start()

    def _rerender(self) -> None:
        if self._frame is not None:
            self.render(self._frame)

    # -- public API ---------------------------------------------------------
    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._apply_bg()
        if self._frame is not None:
            self.render(self._frame)

    def set_highlight(self, index: int | None) -> None:
        self._highlight = index
        if self._frame is not None:
            self.render(self._frame)

    def render(self, frame: Frame) -> None:
        self._frame = frame
        self.ax.clear()
        self.ax.axis("off")
        if frame is None or not frame.values:
            self.canvas.draw_idle()
            return

        values = frame.values
        states = frame.states
        n = len(values)

        # geometry ----------------------------------------------------------
        gap = 0.18 if n <= 30 else (0.12 if n <= 60 else 0.07)
        width = 1.0
        step = width + gap
        self._step = step
        self._width = width
        total = n * step
        self.ax.set_xlim(-0.4, total + 0.4)
        self.ax.set_ylim(-1.15, 1.75)

        # font sizing scales down for larger arrays / wider numbers
        if n <= 15:
            base_fs = 15
        elif n <= 30:
            base_fs = 12
        elif n <= 50:
            base_fs = 9.5
        elif n <= 75:
            base_fs = 7.5
        else:
            base_fs = 6.0

        max_digits = max((len(str(v)) for v in values), default=1)
        if max_digits >= 4:
            base_fs *= 0.78
        elif max_digits == 3:
            base_fs *= 0.9

        # Cap the font to the *physical* block width so the value always fits
        # inside its block instead of overlapping its neighbours.  This matters
        # on a compressed window and in the narrow Comparison-Mode workspaces,
        # where each block is only a few pixels wide (PRD 5.6 - "blocks never
        # overlap").  Recomputed on every resize via resizeEvent above.
        canvas_px = max(1, self.canvas.width())
        step_px = canvas_px / max(1, n)           # pixels per block+gap
        block_px = step_px * (width / step)       # pixels of the block itself
        # a digit is ~0.6*fontsize wide (points); keep max_digits within ~88%
        # of the block, converting points<->pixels via the figure dpi.
        max_fs = (0.88 * block_px * 72.0 / self.figure.dpi) / (0.6 * max_digits)
        base_fs = max(4.0, min(base_fs, max_fs))

        idx_digits = max(1, len(str(n - 1)))
        idx_cap = (0.9 * step_px * 72.0 / self.figure.dpi) / (0.6 * idx_digits)
        idx_fs = max(4.5, min(base_fs * 0.62, idx_cap))
        # When the array is so dense that consecutive index labels would collide,
        # show only every Nth index (plus the last) instead of an unreadable
        # smear - the Position Indicator stays legible (PRD 5.6).
        idx_label_px = idx_digits * 0.6 * idx_fs * self.figure.dpi / 72.0
        idx_stride = max(1, int(round((idx_label_px + 3.0) / max(1.0, step_px))))
        radius = 0.14 if n <= 40 else 0.08

        # Heap Sort: positions past the heap boundary are "out of heap" (gray)
        boundary = frame.heap_size

        for i, (val, st) in enumerate(zip(values, states)):
            x = i * step
            if boundary is not None and i >= boundary and st == STATE_DEFAULT:
                st = STATE_DISABLED
            color = STATE_COLORS.get(st, STATE_COLORS[STATE_DEFAULT])
            box = FancyBboxPatch(
                (x, 0.0), width, 1.0,
                boxstyle=f"round,pad=0,rounding_size={radius}",
                linewidth=0, facecolor=color, edgecolor="none",
                mutation_aspect=1.0, zorder=2,
            )
            self.ax.add_patch(box)
            if self._highlight == i:
                ring = FancyBboxPatch(
                    (x - 0.04, -0.04), width + 0.08, 1.08,
                    boxstyle=f"round,pad=0,rounding_size={radius}",
                    linewidth=2.4, facecolor="none",
                    edgecolor=self.theme.accent_2, zorder=4,
                )
                self.ax.add_patch(ring)
            # value inside the block
            self.ax.text(
                x + width / 2, 0.5, str(val),
                ha="center", va="center", color=self.theme.block_text,
                fontsize=base_fs, fontweight="bold", zorder=3,
            )
            # fixed Position Indicator (index) beneath the block - thinned out
            # on very dense arrays so the labels stay readable (see idx_stride)
            if i % idx_stride == 0 or i == n - 1:
                self.ax.text(
                    x + width / 2, -0.42, str(i),
                    ha="center", va="center", color=self.theme.block_index_text,
                    fontsize=idx_fs, zorder=3,
                )

        # merge-sort group brackets ----------------------------------------
        if frame.groups:
            for (lo, hi) in frame.groups:
                if lo > hi:
                    continue
                x0 = lo * step - gap / 2
                x1 = hi * step + width + gap / 2
                y = 1.28
                self.ax.plot([x0, x0, x1, x1], [y - 0.12, y, y, y - 0.12],
                             color=self.theme.accent_2, linewidth=1.6, zorder=1)
                self.ax.text((x0 + x1) / 2, y + 0.12,
                             f"[{lo}–{hi}]" if lo != hi else f"[{lo}]",
                             ha="center", va="bottom",
                             color=self.theme.accent_2, fontsize=idx_fs)

        self.figure.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.02)
        self.canvas.draw_idle()

    # -- internals ----------------------------------------------------------
    def _on_click(self, event) -> None:
        if event.inaxes != self.ax or self._frame is None or event.xdata is None:
            return
        i = int(event.xdata // self._step)
        if 0 <= i < len(self._frame.values):
            self.blockClicked.emit(i)

    def _apply_bg(self) -> None:
        self.figure.patch.set_facecolor(self.theme.canvas_bg)
        self.ax.set_facecolor(self.theme.canvas_bg)
        self.canvas.draw_idle()
