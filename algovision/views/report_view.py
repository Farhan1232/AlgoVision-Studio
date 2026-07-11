"""Performance Report (PRD 8.4).

Generated when an algorithm finishes.  Shows the execution summary, the
initial→sorted transformation, a comparison of all six algorithms on the same
dataset (with the most efficient highlighted), an execution-overview chart and
the algorithm insights.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QScrollArea,
    QSizePolicy
)

from ..theme.palette import Theme, STATE_COLORS, STATE_SORTED, STATE_DEFAULT
from ..core import registry
from ..core.player import frame_exec_seconds
from ..widgets.common import card, card_with_title


class _Canvas(FigureCanvas):
    def __init__(self, theme: Theme, height=2.6, min_h=140):
        self.fig = Figure(figsize=(4, height), dpi=100)
        super().__init__(self.fig)
        self.theme = theme
        self.ax = self.fig.add_subplot(111)
        # Expand to fill the panel but allow shrinking, so the report packs
        # into the window with minimal scrolling instead of forcing a fixed
        # (tall) canvas height.
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(min_h)
        self._bg()

    def _bg(self):
        self.fig.patch.set_facecolor(self.theme.card_bg)
        self.ax.set_facecolor(self.theme.card_bg)


class ReportView(QScrollArea):
    runAgainRequested = pyqtSignal()
    backRequested = pyqtSignal()
    exportRequested = pyqtSignal()

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWidgetResizable(True)
        self.info = None
        self.original: list[int] = []
        self.frames: list = []

        self.body = QWidget()
        self.setWidget(self.body)
        self.v = QVBoxLayout(self.body)
        self.v.setContentsMargins(16, 10, 16, 10)
        self.v.setSpacing(8)

    # -- build --------------------------------------------------------------
    def show_report(self, info, original: list[int], frames: list) -> None:
        self.info = info
        self.original = list(original)
        self.frames = frames
        while self.v.count():
            it = self.v.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        final = frames[-1]

        # title + at-a-glance metadata strip
        head = QHBoxLayout()
        title = QLabel("PERFORMANCE REPORT")
        title.setProperty("role", "title")
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self._meta_strip(info, original))
        hw = QWidget(); hw.setLayout(head)
        self.v.addWidget(hw)

        # summary tiles (Execution Summary)
        self.v.addWidget(self._summary_tiles(info, final))

        # Two balanced columns so the four analysis panels fit the window with
        # minimal scrolling (reworked for the 2nd client revision):
        #   left  = Array Transformation  +  Execution Overview
        #   right = Performance Comparison +  Algorithm Insights
        cols = QHBoxLayout(); cols.setSpacing(12)
        left = QVBoxLayout(); left.setSpacing(8)
        left.addWidget(self._transformation(original, final), 3)
        left.addWidget(self._execution_overview(frames), 4)
        right = QVBoxLayout(); right.setSpacing(8)
        right.addWidget(self._comparison_chart(original), 4)
        right.addWidget(self._insights_block(info), 3)
        lw = QWidget(); lw.setLayout(left)
        rw = QWidget(); rw.setLayout(right)
        cols.addWidget(lw, 1)
        cols.addWidget(rw, 1)
        cw = QWidget(); cw.setLayout(cols)
        self.v.addWidget(cw, 1)

    def _meta_strip(self, info, original) -> QWidget:
        t = self.theme
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(16)
        items = [
            ("Algorithm", info.name, t.accent_2),
            ("Dataset", "Custom Array", t.text_primary),
            ("Size", str(len(original)), t.text_primary),
            ("Value Range", "1 – 1000", t.text_primary),
        ]
        for label, value, col in items:
            cell = QVBoxLayout(); cell.setSpacing(0)
            k = QLabel(label); k.setProperty("role", "muted")
            k.setStyleSheet("font-size:10px;")
            val = QLabel(str(value))
            val.setStyleSheet(f"font-size:13px; font-weight:700; color:{col};")
            cell.addWidget(k); cell.addWidget(val)
            cw = QWidget(); cw.setLayout(cell)
            h.addWidget(cw)
        return w

    def _tile(self, label, value, sub="", color=None):
        c = card()
        v = QVBoxLayout(c)
        v.setContentsMargins(14, 8, 14, 8)
        v.setSpacing(2)
        lab = QLabel(label); lab.setProperty("role", "muted")
        val = QLabel(str(value))
        val.setStyleSheet(f"font-size:20px; font-weight:800; color:{color or self.theme.accent_2};")
        v.addWidget(lab); v.addWidget(val)
        if sub:
            s = QLabel(sub); s.setProperty("role", "muted"); v.addWidget(s)
        return c

    def _summary_tiles(self, info, final):
        w = QWidget()
        g = QGridLayout(w)
        g.setSpacing(10)
        g.setContentsMargins(0, 0, 0, 0)
        tiles = [
            ("Comparisons", final.comparisons, "", self.theme.accent_2),
            ("Swaps / Moves", final.swaps, "", self.theme.warning),
            ("Execution Time", f"{frame_exec_seconds(final):.3f} s", "", self.theme.success),
            ("Space Complexity", info.space, "Memory", self.theme.accent),
            ("Stable", "Yes" if info.stable else "No",
             "Stable Algorithm" if info.stable else "Not Stable", self.theme.success),
            ("In-place", "Yes" if info.in_place else "No", "", self.theme.accent),
        ]
        for i, (lab, val, sub, col) in enumerate(tiles):
            g.addWidget(self._tile(lab, val, sub, col), 0, i)
            g.setColumnStretch(i, 1)
        return w

    def _transformation(self, original, final):
        frame, lay = card_with_title("Array Transformation (Initial → Sorted)")
        canvas = _Canvas(self.theme, height=1.35, min_h=104)
        ax = canvas.ax
        ax.clear(); ax.axis("off")
        n = len(original)
        for i, val in enumerate(original):
            ax.text(i, 1.6, str(val), ha="center", va="center", color="#fff",
                    fontsize=max(6, 12 - n // 12),
                    bbox=dict(boxstyle="round,pad=0.3", fc=STATE_COLORS[STATE_DEFAULT], ec="none"))
        ax.text(-0.9, 1.6, "Initial", ha="right", va="center", color=self.theme.text_secondary, fontsize=9)
        for i, val in enumerate(final.values):
            ax.text(i, 0.4, str(val), ha="center", va="center", color="#fff",
                    fontsize=max(6, 12 - n // 12),
                    bbox=dict(boxstyle="round,pad=0.3", fc=STATE_COLORS[STATE_SORTED], ec="none"))
        ax.text(-0.9, 0.4, "Sorted", ha="right", va="center", color=self.theme.text_secondary, fontsize=9)
        ax.set_xlim(-2, n); ax.set_ylim(0, 2)
        canvas._bg()
        canvas.draw_idle()
        lay.addWidget(canvas)
        return frame

    def _comparison_chart(self, original):
        frame, lay = card_with_title("Performance Comparison (all algorithms, same dataset)")
        results = []
        for info in registry.all_algorithms():
            f = info.trace(list(original))[-1]
            results.append((info.name, f.comparisons, f.swaps, frame_exec_seconds(f)))

        canvas = _Canvas(self.theme, height=1.95, min_h=175)
        ax = canvas.ax
        ax.clear()
        names = [r[0] for r in results]
        comps = [r[1] for r in results]
        y = range(len(names))
        winner_idx = min(range(len(results)), key=lambda i: (results[i][3], results[i][1] + results[i][2]))
        colors = [self.theme.success if i == winner_idx else self.theme.accent_2 for i in range(len(results))]
        ax.barh(list(y), comps, color=colors, height=0.6)
        ax.set_yticks(list(y))
        ax.set_yticklabels(names, color=self.theme.text_secondary, fontsize=9)
        ax.invert_yaxis()
        ax.tick_params(colors=self.theme.text_muted, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(self.theme.border)
        ax.set_xlabel("Comparisons", color=self.theme.text_secondary, fontsize=9)
        # headroom on the right so the compact annotations never clip
        ax.set_xlim(0, max(comps) * 1.6 if comps else 1)
        for i, r in enumerate(results):
            ax.text(r[1], i, f"  {r[1]} · {r[2]}sw · {r[3]:.2f}s",
                    va="center", color=self.theme.text_secondary, fontsize=7.5)
        canvas.fig.subplots_adjust(left=0.24, right=0.99, top=0.95, bottom=0.18)
        canvas._bg()
        canvas.draw_idle()
        lay.addWidget(canvas)
        note = QLabel(f"🏆 Most efficient on this dataset: <b>{results[winner_idx][0]}</b>")
        note.setTextFormat(Qt.TextFormat.RichText)
        note.setStyleSheet(f"color:{self.theme.success};")
        lay.addWidget(note)
        return frame

    def _execution_overview(self, frames):
        frame, lay = card_with_title("Execution Overview")
        canvas = _Canvas(self.theme, height=1.9, min_h=140)
        ax = canvas.ax
        ax.clear()
        xs = [f.op_number for f in frames]
        comps = [f.comparisons for f in frames]
        swaps = [f.swaps for f in frames]
        ax.plot(xs, comps, color=self.theme.accent_2, linewidth=2, label="Comparisons")
        ax.plot(xs, swaps, color=self.theme.warning, linewidth=2, label="Swaps / Moves")
        ax.fill_between(xs, comps, color=self.theme.accent_2, alpha=0.12)
        ax.tick_params(colors=self.theme.text_muted, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(self.theme.border)
        ax.set_xlabel("Operation", color=self.theme.text_secondary, fontsize=9)
        leg = ax.legend(facecolor=self.theme.card_bg, edgecolor=self.theme.border,
                        labelcolor=self.theme.text_secondary, fontsize=8)
        canvas.fig.subplots_adjust(left=0.1, right=0.97, top=0.95, bottom=0.18)
        canvas._bg()
        canvas.draw_idle()
        lay.addWidget(canvas)
        return frame

    def _insights_block(self, info):
        frame, lay = card_with_title("Algorithm Insights")
        t = self.theme
        rows = [
            ("Overview", info.overview),
            ("Time Complexity", f"Best {info.best} · Average {info.average} · Worst {info.worst}"),
            ("Space Complexity", info.space),
            ("Stable", "Yes" if info.stable else "No"),
            ("Best Used For", info.best_used_for),
            ("Key Takeaway", info.key_idea),
        ]
        for label, value in rows:
            r = QLabel(f"<b style='color:{t.text_primary}'>{label}:</b> "
                       f"<span style='color:{t.text_secondary}'>{value}</span>")
            r.setTextFormat(Qt.TextFormat.RichText)
            r.setWordWrap(True)
            lay.addWidget(r)
        lay.addStretch(1)
        return frame

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        if self.info:
            self.show_report(self.info, self.original, self.frames)
