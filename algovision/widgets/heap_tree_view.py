"""Binary Heap Tree View (PRD 6.6).

Renders the array as a binary max-heap.  Node colours are driven by the same
frame ``states`` used by the Numbered Block View, so the two views stay
synchronized automatically.  Clicking a node emits :sig:`nodeClicked` so the
parent can cross-highlight the matching array block, and vice versa.
"""

from __future__ import annotations

import math

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from ..theme.palette import Theme, STATE_COLORS, STATE_DEFAULT, STATE_DISABLED
from ..core.frames import Frame


class HeapTreeView(QWidget):
    nodeClicked = pyqtSignal(int)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._frame: Frame | None = None
        self._highlight: int | None = None
        self._node_positions: dict[int, tuple[float, float]] = {}
        self._pick_tol = 0.02

        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.canvas.mpl_connect("button_press_event", self._on_click)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.canvas)
        self._apply_bg()

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
        self._node_positions.clear()
        if frame is None or not frame.values:
            self.canvas.draw_idle()
            return

        values = frame.values
        states = frame.states
        n = len(values)
        boundary = frame.heap_size if frame.heap_size is not None else n

        levels = int(math.floor(math.log2(n))) + 1 if n > 0 else 1
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(-(levels - 1) - 0.55, 0.65)

        # marker diameter (points) and pick tolerance shrink with depth
        diam_pts = max(9.0, 42.0 - 4.2 * levels)
        s = diam_pts ** 2
        node_fs = max(5.5, 15.5 - 1.35 * levels)
        idx_fs = max(4.5, node_fs * 0.6)
        self._pick_tol = (0.06 / (2 ** (levels - 1))) + 0.0008

        def pos(i: int) -> tuple[float, float]:
            depth = int(math.floor(math.log2(i + 1)))
            first = (2 ** depth) - 1
            offset = i - first
            count = 2 ** depth
            return (offset + 0.5) / count, float(-depth)

        # edges
        for i in range(n):
            x, y = pos(i)
            for child in (2 * i + 1, 2 * i + 2):
                if child < n:
                    cx, cy = pos(child)
                    in_heap = child < boundary and i < boundary
                    self.ax.plot([x, cx], [y, cy],
                                 color=self.theme.accent if in_heap else self.theme.divider,
                                 linewidth=1.3 if in_heap else 0.9, zorder=1)

        # nodes (scatter keeps them perfectly round regardless of aspect)
        xs, ys, colors = [], [], []
        hx, hy = [], []
        for i in range(n):
            x, y = pos(i)
            self._node_positions[i] = (x, y)
            st = states[i]
            if i >= boundary and st == STATE_DEFAULT:
                st = STATE_DISABLED
            xs.append(x); ys.append(y)
            colors.append(STATE_COLORS.get(st, STATE_COLORS[STATE_DEFAULT]))
            if self._highlight == i:
                hx.append(x); hy.append(y)

        if hx:
            self.ax.scatter(hx, hy, s=s * 1.5, facecolors="none",
                            edgecolors=self.theme.accent_2, linewidths=2.4, zorder=2)
        self.ax.scatter(xs, ys, s=s, c=colors, edgecolors="none", zorder=3)

        y_off = 0.42
        for i in range(n):
            x, y = self._node_positions[i]
            self.ax.text(x, y, str(values[i]), ha="center", va="center",
                         color="#FFFFFF", fontsize=node_fs, fontweight="bold", zorder=4)
            self.ax.text(x, y + y_off, str(i), ha="center", va="bottom",
                         color=self.theme.text_muted, fontsize=idx_fs, zorder=4)

        self.figure.subplots_adjust(left=0.02, right=0.98, top=0.97, bottom=0.03)
        self.canvas.draw_idle()

    # -- internals ----------------------------------------------------------
    def _on_click(self, event) -> None:
        if event.inaxes != self.ax or not self._node_positions:
            return
        if event.xdata is None or event.ydata is None:
            return
        best, best_d = None, 1e9
        for i, (x, y) in self._node_positions.items():
            d = (event.xdata - x) ** 2 + (event.ydata - y) ** 2
            if d < best_d:
                best, best_d = i, d
        if best is not None and best_d < self._pick_tol:
            self.nodeClicked.emit(best)

    def _apply_bg(self) -> None:
        self.figure.patch.set_facecolor(self.theme.canvas_bg)
        self.ax.set_facecolor(self.theme.canvas_bg)
        self.canvas.draw_idle()
