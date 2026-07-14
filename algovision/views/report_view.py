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

from PyQt6.QtCore import Qt, pyqtSignal, QRect, QSize, QPoint
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QScrollArea,
    QSizePolicy, QLayout
)

from ..theme.palette import Theme, STATE_COLORS, STATE_SORTED, STATE_DEFAULT
from ..theme import scale as uiscale
from ..core import registry
from ..core.player import frame_exec_seconds
from ..widgets.common import card, card_with_title


class FlowLayout(QLayout):
    """A layout that arranges its children left-to-right and wraps to the next
    row when it runs out of width.  Used for the Initial/Sorted array blocks in
    the Performance Report so they stay fully visible (wrapping onto more rows)
    at any array size and window width - never overlapping or clipping."""

    def __init__(self, parent=None, margin=0, spacing=6):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self._spacing = spacing
        self._items: list = []

    def addItem(self, item):  # noqa: N802
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):  # noqa: N802
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):  # noqa: N802
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self):  # noqa: N802
        return True

    def heightForWidth(self, width):  # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):  # noqa: N802
        return self.minimumSize()

    def minimumSize(self):  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        x = rect.x() + m.left()
        y = rect.y() + m.top()
        line_height = 0
        right = rect.right() - m.right()
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + self._spacing
            if next_x - self._spacing > right and line_height > 0:
                x = rect.x() + m.left()
                y = y + line_height + self._spacing
                next_x = x + hint.width() + self._spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + m.bottom()


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
        # what the report currently shows, so a theme switch rebuilds the right
        # variant (single-algorithm vs comparison)
        self._report_mode = "single"
        self._cmp = None  # (info_a, info_b, original, frames_a, frames_b)

        self.body = QWidget()
        self.setWidget(self.body)
        self.v = QVBoxLayout(self.body)
        self.v.setContentsMargins(16, 10, 16, 10)
        self.v.setSpacing(8)

    # -- build --------------------------------------------------------------
    def _clear(self) -> None:
        while self.v.count():
            it = self.v.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

    def show_report(self, info, original: list[int], frames: list) -> None:
        self.info = info
        self.original = list(original)
        self.frames = frames
        self._report_mode = "single"
        self._clear()

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

    def _blocks_row(self, values, color) -> QWidget:
        """A wrapping grid of numbered blocks (one per array element).  Uses a
        FlowLayout so the blocks reflow onto more rows as the array grows or the
        window narrows - they never overlap or get clipped (fixes the collapsed
        Initial/Sorted arrays feedback)."""
        holder = QWidget()
        flow = FlowLayout(holder, margin=0, spacing=uiscale.sp(5))
        n = len(values)
        # block size shrinks a little for big arrays but stays readable
        side = 34 if n <= 20 else (28 if n <= 40 else (23 if n <= 70 else 19))
        fs = uiscale.fs(13 if n <= 20 else (11 if n <= 40 else (9 if n <= 70 else 8)))
        for val in values:
            b = QLabel(str(val))
            b.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b.setFixedSize(uiscale.sp(side), uiscale.sp(side))
            b.setStyleSheet(
                f"background:{color}; color:#ffffff; border-radius:{uiscale.sp(6)}px; "
                f"font-size:{fs}px; font-weight:700;")
            flow.addWidget(b)
        return holder

    def _transformation(self, original, final):
        frame, lay = card_with_title("Array Transformation (Initial → Sorted)")
        init_lbl = QLabel("Initial Array"); init_lbl.setProperty("role", "muted")
        lay.addWidget(init_lbl)
        lay.addWidget(self._blocks_row(original, STATE_COLORS[STATE_DEFAULT]))
        arrow = QLabel("↓"); arrow.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        arrow.setStyleSheet(f"color:{self.theme.accent_2}; font-size:{uiscale.fs(16)}px;")
        lay.addWidget(arrow)
        sorted_lbl = QLabel("Sorted Array"); sorted_lbl.setProperty("role", "muted")
        lay.addWidget(sorted_lbl)
        lay.addWidget(self._blocks_row(final.values, STATE_COLORS[STATE_SORTED]))
        lay.addStretch(1)
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

    # -- comparison report (PRD 8.4) ---------------------------------------
    def show_comparison_report(self, info_a, info_b, original: list[int],
                               frames_a: list, frames_b: list) -> None:
        """Side-by-side report for Comparison Mode: both algorithms on the same
        dataset, comparing comparisons, swaps, execution time, time complexity
        and space complexity, with the more efficient one highlighted."""
        self._report_mode = "compare"
        self._cmp = (info_a, info_b, list(original), frames_a, frames_b)
        self.info = info_a
        self.original = list(original)
        self.frames = frames_a
        self._clear()

        fa, fb = frames_a[-1], frames_b[-1]
        ta, tb = frame_exec_seconds(fa), frame_exec_seconds(fb)
        a_ops, b_ops = fa.comparisons + fa.swaps, fb.comparisons + fb.swaps
        if (ta, a_ops) < (tb, b_ops):
            winner = info_a.name
        elif (tb, b_ops) < (ta, a_ops):
            winner = info_b.name
        else:
            winner = "Tie"

        # title + meta
        head = QHBoxLayout()
        title = QLabel("PERFORMANCE REPORT · COMPARISON")
        title.setProperty("role", "title")
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self._cmp_meta_strip(info_a, info_b, original))
        hw = QWidget(); hw.setLayout(head)
        self.v.addWidget(hw)

        banner = QLabel(
            (f"🏆 More efficient on this dataset: <b>{winner}</b>")
            if winner != "Tie" else "Both algorithms performed equally on this dataset.")
        banner.setTextFormat(Qt.TextFormat.RichText)
        banner.setStyleSheet(
            f"color:{self.theme.success}; font-size:{uiscale.fs(13)}px; font-weight:700;")
        self.v.addWidget(banner)

        # two balanced columns
        cols = QHBoxLayout(); cols.setSpacing(12)
        left = QVBoxLayout(); left.setSpacing(8)
        left.addWidget(self._cmp_table(info_a, info_b, fa, fb, ta, tb, winner), 0)
        left.addWidget(self._transformation(original, fa), 1)
        right = QVBoxLayout(); right.setSpacing(8)
        right.addWidget(self._execution_overview_compare(info_a, info_b, frames_a, frames_b), 1)
        right.addWidget(self._comparison_chart(original), 1)
        lw = QWidget(); lw.setLayout(left)
        rw = QWidget(); rw.setLayout(right)
        cols.addWidget(lw, 1)
        cols.addWidget(rw, 1)
        cw = QWidget(); cw.setLayout(cols)
        self.v.addWidget(cw, 1)

    def _cmp_meta_strip(self, info_a, info_b, original) -> QWidget:
        t = self.theme
        w = QWidget()
        h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(16)
        items = [
            ("Comparison", f"{info_a.name}  vs  {info_b.name}", t.accent_2),
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
            cwid = QWidget(); cwid.setLayout(cell)
            h.addWidget(cwid)
        return w

    def _cmp_table(self, info_a, info_b, fa, fb, ta, tb, winner) -> QWidget:
        frame, lay = card_with_title("Performance Comparison")
        t = self.theme
        g = QGridLayout(); g.setHorizontalSpacing(uiscale.sp(16))
        g.setVerticalSpacing(uiscale.sp(7))
        fsz = uiscale.fs(12.5)

        def hdr(text, win):
            lbl = QLabel(("🏆 " if win else "") + text)
            lbl.setStyleSheet(f"font-weight:800; font-size:{fsz}px; "
                              f"color:{t.success if win else t.text_primary};")
            return lbl

        def cell(text, win):
            lbl = QLabel(str(text))
            lbl.setStyleSheet(f"font-size:{fsz}px; font-weight:600; "
                              f"color:{t.success if win else t.text_primary};")
            return lbl

        win_a = winner == info_a.name
        win_b = winner == info_b.name
        g.addWidget(QLabel(""), 0, 0)
        g.addWidget(hdr(info_a.name, win_a), 0, 1)
        g.addWidget(hdr(info_b.name, win_b), 0, 2)
        rows = [
            ("Total Comparisons", str(fa.comparisons), str(fb.comparisons)),
            ("Total Swaps / Moves", str(fa.swaps), str(fb.swaps)),
            ("Execution Time", f"{ta:.3f} s", f"{tb:.3f} s"),
            ("Time Complexity", info_a.average, info_b.average),
            ("Space Complexity", info_a.space, info_b.space),
            ("Stable", "Yes" if info_a.stable else "No", "Yes" if info_b.stable else "No"),
            ("In-place", "Yes" if info_a.in_place else "No", "Yes" if info_b.in_place else "No"),
        ]
        for r, (metric, va, vb) in enumerate(rows, start=1):
            m = QLabel(metric); m.setProperty("role", "muted")
            m.setStyleSheet(f"font-size:{fsz}px;")
            g.addWidget(m, r, 0)
            g.addWidget(cell(va, win_a), r, 1)
            g.addWidget(cell(vb, win_b), r, 2)
        g.setColumnStretch(0, 2); g.setColumnStretch(1, 2); g.setColumnStretch(2, 2)
        holder = QWidget(); holder.setLayout(g)
        lay.addWidget(holder)
        return frame

    def _execution_overview_compare(self, info_a, info_b, frames_a, frames_b) -> QWidget:
        frame, lay = card_with_title("Execution Overview (Comparisons)")
        canvas = _Canvas(self.theme, height=1.9, min_h=150)
        ax = canvas.ax
        ax.clear()
        ax.plot([f.op_number for f in frames_a], [f.comparisons for f in frames_a],
                color=self.theme.accent_2, linewidth=2, label=info_a.name)
        ax.plot([f.op_number for f in frames_b], [f.comparisons for f in frames_b],
                color=self.theme.warning, linewidth=2, label=info_b.name)
        ax.tick_params(colors=self.theme.text_muted, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(self.theme.border)
        ax.set_xlabel("Operation", color=self.theme.text_secondary, fontsize=9)
        ax.legend(facecolor=self.theme.card_bg, edgecolor=self.theme.border,
                  labelcolor=self.theme.text_secondary, fontsize=8)
        canvas.fig.subplots_adjust(left=0.1, right=0.97, top=0.95, bottom=0.18)
        canvas._bg()
        canvas.draw_idle()
        lay.addWidget(canvas)
        return frame

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        if self._report_mode == "compare" and self._cmp:
            self.show_comparison_report(*self._cmp)
        elif self.info:
            self.show_report(self.info, self.original, self.frames)
