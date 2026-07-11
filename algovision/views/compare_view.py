"""Algorithm Comparison Mode (PRD 7.5 + 8.4).

Runs two algorithms on the SAME dataset under one shared clock.  Play, Pause,
Step, Restart, Reset, Timeline and Speed affect both sides simultaneously so
the comparison is fair.  A shared Performance Summary highlights the algorithm
that finished more efficiently.

Layout notes (reworked for the 2nd client revision - readability for classroom
use): the Timeline scrubber is integrated into the Performance Summary strip at
the foot of the view, which frees the whole middle band for the educational
panels.  Each side therefore carries a compact header, a scaling Numbered Block
View, a live explanation and a *tall* row of three panels - Statistics, Code
Viewer and Algorithm Insights - so the pseudocode and stats are comfortably
readable without constant scrolling.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QProgressBar, QSizePolicy, QScrollArea, QFrame
)

from ..theme.palette import Theme
from ..theme import scale as uiscale
from ..core import registry
from ..core.player import frame_exec_seconds
from ..config import BASE_FRAME_MS
from ..widgets import ArrayView, CodeViewer, ExplanationPanel, Legend, Timeline
from ..widgets.common import card, card_with_title
from ..theme.palette import LEGEND_STANDARD, STATE_PIVOT, STATE_SELECTED


class _MiniStats(QWidget):
    """Compact *horizontal* live-stats strip for one comparison workspace.

    Laid out as a row of value/label cells plus a thin progress bar, so the
    Statistics panel stays short and the tall Code Viewer / Algorithm Insights
    panels get the full workspace width beneath it.
    """

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._vals: dict[str, QLabel] = {}
        self._keys: list[QLabel] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(7)

        cells = QHBoxLayout()
        cells.setSpacing(10)
        for key in ("Comparisons", "Swaps", "Time"):
            col = QVBoxLayout(); col.setSpacing(1)
            v = QLabel("—")
            v.setStyleSheet(f"font-size:{uiscale.fs(17)}px; font-weight:800; "
                            f"color:{theme.text_primary};")
            k = QLabel(key); k.setProperty("role", "muted")
            k.setStyleSheet(f"font-size:{uiscale.fs(10)}px;")
            col.addWidget(v); col.addWidget(k)
            cells.addLayout(col)
            cells.addStretch(1)
            self._vals[key] = v
            self._keys.append(k)
        lay.addLayout(cells)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100); self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        lay.addWidget(self.progress)

    def clear(self):
        for v in self._vals.values():
            v.setText("—")
        self.progress.setValue(0)

    def update_from(self, frame, total: int):
        if frame is None:
            return
        self._vals["Comparisons"].setText(str(frame.comparisons))
        self._vals["Swaps"].setText(str(frame.swaps))
        self._vals["Time"].setText(f"{frame_exec_seconds(frame):.3f}s")
        self.progress.setValue(int(round(100 * frame.op_number / max(1, total))))

    def apply_scale(self, s: float):
        self.progress.setFixedHeight(uiscale.sp(8))
        for v in self._vals.values():
            v.setStyleSheet(f"font-size:{uiscale.fs(17)}px; font-weight:800; "
                            f"color:{self.theme.text_primary};")
        for k in self._keys:
            k.setStyleSheet(f"font-size:{uiscale.fs(10)}px;")

    def set_theme(self, theme: Theme):
        self.theme = theme
        self.apply_scale(uiscale.get_scale())


class _CompactInsights(QScrollArea):
    """A short, scrollable Algorithm-Insights panel for one comparison side.

    Shows the essentials a learner needs while comparing - overview, the three
    complexity classes, stability and the key takeaway - word-wrapped so it
    reads comfortably at the narrow comparison width.
    """

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._info = None
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("background:transparent;")
        self.body = QWidget()
        self.vbox = QVBoxLayout(self.body)
        self.vbox.setContentsMargins(0, 0, 6, 0)
        self.vbox.setSpacing(7)
        self.setWidget(self.body)

    def set_info(self, info) -> None:
        self._info = info
        t = self.theme
        while self.vbox.count():
            it = self.vbox.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        acc = t.accent
        rows = [
            ("ℹ️", "Overview", info.overview),
            ("⏱️", "Time Complexity",
             f"Best <span style='color:{acc}'>{info.best}</span> · "
             f"Average <span style='color:{acc}'>{info.average}</span> · "
             f"Worst <span style='color:{acc}'>{info.worst}</span>"),
            ("🧠", "Space Complexity", f"<span style='color:{t.success}'>{info.space}</span>"),
            ("🔒", "Stable", ("<span style='color:%s'>Yes</span>" % t.success) if info.stable
             else ("<span style='color:%s'>No</span>" % t.danger)),
            ("🎯", "Best Used For", info.best_used_for),
            ("💡", "Key Idea", info.key_idea),
        ]
        fs = uiscale.fs(11)
        for icon, label, value in rows:
            w = QWidget()
            row = QHBoxLayout(w)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(7)
            ic = QLabel(icon); ic.setFixedWidth(uiscale.sp(16))
            ic.setAlignment(Qt.AlignmentFlag.AlignTop)
            ic.setStyleSheet(f"font-size:{fs}px;")
            text = QLabel()
            text.setTextFormat(Qt.TextFormat.RichText)
            text.setWordWrap(True)
            text.setStyleSheet(f"font-size:{fs}px;")
            text.setText(
                f"<span style='color:{t.text_primary}; font-weight:600'>{label}</span>"
                f"<br><span style='color:{t.text_secondary}'>{value}</span>")
            row.addWidget(ic)
            row.addWidget(text, 1)
            self.vbox.addWidget(w)
        self.vbox.addStretch(1)

    def apply_scale(self, s: float) -> None:
        if self._info:
            self.set_info(self._info)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        if self._info:
            self.set_info(self._info)


class _Mini(QWidget):
    """One comparison workspace: header + array view + stats/code/insights."""

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.frames: list = []
        self.info = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        c = card()
        outer = QVBoxLayout(c)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(8)

        # header - name / badge on the left, step counter on the right; the
        # name elides instead of overlapping the badge or step counter.
        head = QHBoxLayout()
        head.setSpacing(8)
        self.name = QLabel("Algorithm")
        self.name.setStyleSheet(f"font-size:14px; font-weight:700; color:{theme.text_primary};")
        self.name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.badge = QLabel("Reset"); self.badge.setProperty("role", "badge-reset")
        self.steps = QLabel(""); self.steps.setProperty("role", "muted")
        head.addWidget(self.name, 1)
        head.addWidget(self.badge)
        head.addWidget(self.steps)
        outer.addLayout(head)

        # The array is capped in height (Expanding, but Maximum policy) so the
        # tall educational panels below it get the lion's share of the vertical
        # space - this is the fix for the "middle section too compressed"
        # feedback: the Code Viewer / Statistics / Insights now dominate.  The
        # shared colour legend lives once beneath both workspaces (see below).
        self.array = ArrayView(theme)
        self.array.setMinimumHeight(58)
        self.array.setMaximumHeight(120)
        self.array.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        outer.addWidget(self.array)

        self.explanation = ExplanationPanel(theme)
        self.explanation.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.explanation.setMinimumHeight(38)
        self.explanation.setMaximumHeight(56)
        outer.addWidget(self.explanation)

        # Statistics as a short horizontal strip so it doesn't steal width from
        # the two panels that actually need room to be read.
        sc, sl = card_with_title("Statistics")
        sl.setContentsMargins(14, 9, 14, 10)
        self.stats = _MiniStats(theme); sl.addWidget(self.stats)
        sc.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        outer.addWidget(sc)

        # Code Viewer + Algorithm Insights get the full workspace width and the
        # remaining height (firm minimum), so pseudocode lines are shown in full
        # and stats/insights read comfortably - the fix for the "panels too
        # small / constant scrolling" feedback.  The array (a Maximum-policy
        # widget) yields its space to this row first.
        bottom_w = QWidget()
        self._bottom_w = bottom_w
        bottom_w.setMinimumHeight(190)
        bottom_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        bottom = QHBoxLayout(bottom_w)
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(8)
        cc, cl = card_with_title("Code Viewer")
        self.code = CodeViewer(theme); cl.addWidget(self.code, 1)
        ic, il = card_with_title("Algorithm Insights")
        self.insights = _CompactInsights(theme); il.addWidget(self.insights, 1)
        bottom.addWidget(cc, 1)
        bottom.addWidget(ic, 1)
        outer.addWidget(bottom_w, 1)

        lay.addWidget(c)

    def load(self, info) -> None:
        self.info = info
        self.name.setText(info.name)
        self.code.set_code(info.pseudocode)
        self.insights.set_info(info)
        self.stats.clear()

    def set_frames(self, frames: list) -> None:
        self.frames = frames

    def render_at(self, pos: int, total: int) -> None:
        if not self.frames:
            return
        idx = min(pos, len(self.frames) - 1)
        frame = self.frames[idx]
        self.array.render(frame)
        self.stats.update_from(frame, len(self.frames))
        self.code.highlight(frame.code_lines)
        self.explanation.update_from(frame)
        done = idx >= len(self.frames) - 1
        self.steps.setText(f"Step {frame.op_number} / {len(self.frames)}")
        if pos == 0:
            status = "Reset"
        elif done:
            status = "Completed"
        else:
            status = "Running"
        self.badge.setText(status)
        self.badge.setProperty("role", f"badge-{status.lower()}")
        self.badge.style().unpolish(self.badge); self.badge.style().polish(self.badge)

    def set_status(self, status: str) -> None:
        self.badge.setText(status)
        self.badge.setProperty("role", f"badge-{status.lower()}")
        self.badge.style().unpolish(self.badge); self.badge.style().polish(self.badge)

    def apply_scale(self, s: float) -> None:
        self.name.setStyleSheet(
            f"font-size:{uiscale.fs(14)}px; font-weight:700; color:{self.theme.text_primary};")
        self.array.setMinimumHeight(uiscale.sp(58))
        self.array.setMaximumHeight(uiscale.sp(120))
        self.explanation.setMinimumHeight(uiscale.sp(38))
        self.explanation.setMaximumHeight(uiscale.sp(56))
        self._bottom_w.setMinimumHeight(uiscale.sp(190))
        for w in (self.array, self.stats, self.code, self.explanation, self.insights):
            if hasattr(w, "apply_scale"):
                w.apply_scale(s)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.name.setStyleSheet(
            f"font-size:{uiscale.fs(14)}px; font-weight:700; color:{theme.text_primary};")
        for w in (self.array, self.stats, self.code, self.explanation, self.insights):
            w.set_theme(theme)


class CompareView(QWidget):
    statusChanged = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.original: list[int] = []
        self._pos = 0
        self._total = 1
        self._speed = 1.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 8)
        root.setSpacing(7)

        top = QHBoxLayout()
        header = QLabel("COMPARISON MODE")
        header.setProperty("role", "title")
        top.addWidget(header)
        sub = QLabel("Two algorithms · same dataset · shared controls")
        sub.setProperty("role", "muted")
        top.addSpacing(12)
        top.addWidget(sub)
        top.addStretch(1)
        self.combo_a = QComboBox()
        self.combo_b = QComboBox()
        for info in registry.all_algorithms():
            self.combo_a.addItem(info.name, info.key)
            self.combo_b.addItem(info.name, info.key)
        self.combo_a.setCurrentIndex(0)   # bubble
        self.combo_b.setCurrentIndex(1)   # selection
        self.combo_a.currentIndexChanged.connect(self._on_combo)
        self.combo_b.currentIndexChanged.connect(self._on_combo)
        la = QLabel("Left:"); la.setProperty("role", "muted")
        lb = QLabel("Right:"); lb.setProperty("role", "muted")
        top.addWidget(la); top.addWidget(self.combo_a)
        top.addSpacing(10)
        top.addWidget(lb); top.addWidget(self.combo_b)
        root.addLayout(top)

        self.left = _Mini(theme)
        self.right = _Mini(theme)
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self.left, 1)
        row.addWidget(self.right, 1)
        # The two workspaces take almost all of the height so the Statistics /
        # Code Viewer / Insights panels inside them are large and readable.
        root.addLayout(row, 1)

        # one shared colour legend for both workspaces (PRD 5.3 visual language)
        self.legend = Legend(theme)
        self.legend.set_items(
            LEGEND_STANDARD + [(STATE_SELECTED, "Selected"), (STATE_PIVOT, "Pivot")])
        leg_row = QHBoxLayout()
        leg_row.addStretch(1)
        leg_row.addWidget(self.legend)
        leg_row.addStretch(1)
        root.addLayout(leg_row)

        # Performance Summary WITH the shared Timeline integrated at its top
        # (PRD 7.5 - Timeline Navigation affects both sides).  Folding the
        # scrubber in here reclaimed the dedicated timeline band for the panels.
        root.addWidget(self._build_summary())

    def _build_summary(self) -> QWidget:
        frame, lay = card_with_title("Performance Summary & Timeline")
        lay.setContentsMargins(14, 8, 14, 10)
        lay.setSpacing(6)

        # integrated shared timeline scrubber
        self.timeline = Timeline(self.theme, style="bar")
        self.timeline.seekRequested.connect(self.seek)
        lay.addWidget(self.timeline)

        div = QFrame(); div.setProperty("role", "divider"); div.setFixedHeight(1)
        lay.addWidget(div)

        self.summary_grid = QGridLayout()
        self.summary_grid.setHorizontalSpacing(18)
        self.summary_grid.setVerticalSpacing(3)
        holder = QWidget()
        holder.setLayout(self.summary_grid)
        lay.addWidget(holder)
        self._summary_frame = frame
        return frame

    # -- lifecycle ----------------------------------------------------------
    def _on_combo(self, _=0):
        if self.original:
            self.load(self.combo_a.currentData(), self.combo_b.currentData(), self.original)

    def set_dataset(self, dataset: list[int]) -> None:
        self.load(self.combo_a.currentData(), self.combo_b.currentData(), dataset)

    def set_primary(self, key: str) -> None:
        """Align the left algorithm with the single-mode selection."""
        idx = self.combo_a.findData(key)
        if idx >= 0 and idx != self.combo_a.currentIndex():
            self.combo_a.blockSignals(True)
            self.combo_a.setCurrentIndex(idx)
            self.combo_a.blockSignals(False)

    def load(self, key_a: str, key_b: str, dataset: list[int]) -> None:
        self._timer.stop()
        self.original = list(dataset)
        for combo, key in ((self.combo_a, key_a), (self.combo_b, key_b)):
            i = combo.findData(key)
            if i >= 0:
                combo.blockSignals(True); combo.setCurrentIndex(i); combo.blockSignals(False)
        info_a = registry.get(key_a)
        info_b = registry.get(key_b)
        self.left.load(info_a)
        self.right.load(info_b)
        fa = info_a.trace(list(dataset))
        fb = info_b.trace(list(dataset))
        self.left.set_frames(fa)
        self.right.set_frames(fb)
        self._total = max(len(fa), len(fb))
        self._pos = 0
        self.timeline.configure(self._total, 0)
        self._render()
        self._update_summary()
        self.statusChanged.emit("Reset")

    # -- shared clock -------------------------------------------------------
    def play(self):
        if self._pos >= self._total - 1:
            return
        self._timer.start(max(30, int(BASE_FRAME_MS / self._speed)))
        self.statusChanged.emit("Running")

    def pause(self):
        if self._timer.isActive():
            self._timer.stop()
            self.statusChanged.emit("Paused")
            self.left.set_status("Paused"); self.right.set_status("Paused")

    def step(self):
        self._timer.stop()
        self._pos = min(self._total - 1, self._pos + 1)
        self._render()
        if self._pos >= self._total - 1:
            self.statusChanged.emit("Completed"); self.finished.emit()
        else:
            self.statusChanged.emit("Paused")

    def restart(self):
        self._pos = 0
        self._render()
        self.play()

    def reset(self):
        self._timer.stop()
        self._pos = 0
        self._render()
        self.statusChanged.emit("Reset")

    def seek(self, pos: int):
        self._timer.stop()
        self._pos = max(0, min(pos, self._total - 1))
        self._render()
        self.statusChanged.emit("Completed" if self._pos >= self._total - 1 else "Paused")

    def set_speed(self, mult: float):
        self._speed = mult
        if self._timer.isActive():
            self._timer.start(max(30, int(BASE_FRAME_MS / self._speed)))

    def position(self) -> tuple[int, int]:
        return self._pos, self._total

    def _tick(self):
        if self._pos >= self._total - 1:
            self._timer.stop()
            self.statusChanged.emit("Completed")
            self.finished.emit()
            return
        self._pos += 1
        self._render()
        if self._pos >= self._total - 1:
            self._timer.stop()
            self.statusChanged.emit("Completed")
            self.finished.emit()

    def _render(self):
        self.left.render_at(self._pos, self._total)
        self.right.render_at(self._pos, self._total)
        op = min(self._pos + 1, self._total)
        self.timeline.update_current(self._pos, op, f"Operation {op}")

    # -- performance summary ------------------------------------------------
    def _update_summary(self):
        # rebuild the comparison table (Metric | A | B), highlighting the winner.
        # Remove old cells from the layout synchronously (deleteLater alone is
        # async and would stack the previous table's cells on top when the user
        # changes an algorithm from the dropdown).
        while self.summary_grid.count():
            it = self.summary_grid.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        fa = self.left.frames[-1]
        fb = self.right.frames[-1]
        ia, ib = self.left.info, self.right.info
        ta, tb = frame_exec_seconds(fa), frame_exec_seconds(fb)

        a_ops = fa.comparisons + fa.swaps
        b_ops = fb.comparisons + fb.swaps
        if (ta, a_ops) < (tb, b_ops):
            winner, win_a, win_b = ia.name, True, False
        elif (tb, b_ops) < (ta, a_ops):
            winner, win_a, win_b = ib.name, False, True
        else:
            winner, win_a, win_b = "Tie", False, False

        t = self.theme

        fsz = uiscale.fs(12)

        def header(text, win):
            lbl = QLabel((("🏆  " if win else "") + text) +
                         ("   ·  more efficient" if win else ""))
            lbl.setStyleSheet(
                f"font-weight:700; font-size:{fsz}px; "
                f"color:{t.success if win else t.text_primary};")
            return lbl

        def cell(text, win):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            lbl.setStyleSheet(
                f"font-size:{fsz}px; font-weight:600; "
                f"color:{t.success if win else t.text_primary};")
            return lbl

        g = self.summary_grid
        g.addWidget(QLabel(""), 0, 0)
        g.addWidget(header(ia.name, win_a), 0, 1)
        g.addWidget(header(ib.name, win_b), 0, 2)

        rows = [
            ("Comparisons", str(fa.comparisons), str(fb.comparisons)),
            ("Swaps / Moves", str(fa.swaps), str(fb.swaps)),
            ("Execution Time", f"{ta:.3f} s", f"{tb:.3f} s"),
            ("Time Complexity", ia.average, ib.average),
            ("Space Complexity", ia.space, ib.space),
        ]
        for r, (metric, va, vb) in enumerate(rows, start=1):
            m = QLabel(metric); m.setProperty("role", "muted")
            m.setStyleSheet(f"font-size:{fsz}px;")
            g.addWidget(m, r, 0)
            g.addWidget(cell(va, win_a), r, 1)
            g.addWidget(cell(vb, win_b), r, 2)
        g.setColumnStretch(1, 1)
        g.setColumnStretch(2, 1)

    def apply_scale(self, s: float) -> None:
        self.left.apply_scale(s)
        self.right.apply_scale(s)
        self.timeline.apply_scale(s)
        self.legend.apply_scale(s)
        if self.left.frames:
            self._update_summary()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.left.set_theme(theme)
        self.right.set_theme(theme)
        self.timeline.set_theme(theme)
        self.legend.set_theme(theme)
        if self.left.frames:
            self._update_summary()
