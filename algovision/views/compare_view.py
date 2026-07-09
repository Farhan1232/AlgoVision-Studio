"""Algorithm Comparison Mode (PRD 7.5 + 8.4).

Runs two algorithms on the SAME dataset under one shared clock.  Play, Pause,
Step, Restart, Reset, Timeline and Speed affect both sides simultaneously so
the comparison is fair.  A shared Performance Summary highlights the algorithm
that finished more efficiently.

Layout notes: every panel is sized to stay fully visible without scrolling -
each side has a compact header (no overlapping text), a scaling Numbered Block
View, a live stats strip and a synchronized Code Viewer, and both sides share a
Timeline scrubber and Performance Summary beneath them.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QProgressBar, QSizePolicy
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
    """Compact live-stats strip for one comparison workspace.

    Shows the two comparison counters plus a thin progress bar; overall
    position is also reflected by the shared Timeline scrubber below.
    """

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._labels: dict[str, QLabel] = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(3)
        grid.setColumnStretch(1, 1)
        for r, key in enumerate(["Comparisons", "Swaps"]):
            k = QLabel(key); k.setProperty("role", "muted")
            v = QLabel("—"); v.setProperty("role", "value")
            v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(k, r, 0)
            grid.addWidget(v, r, 1)
            self._labels[key] = v
        lay.addLayout(grid)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100); self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        lay.addWidget(self.progress)
        lay.addStretch(1)

    def clear(self):
        for v in self._labels.values():
            v.setText("—")
        self.progress.setValue(0)

    def update_from(self, frame, total: int):
        if frame is None:
            return
        self._labels["Comparisons"].setText(str(frame.comparisons))
        self._labels["Swaps"].setText(str(frame.swaps))
        self.progress.setValue(int(round(100 * frame.op_number / max(1, total))))

    def apply_scale(self, s: float):
        self.progress.setFixedHeight(uiscale.sp(10))

    def set_theme(self, theme: Theme):
        self.theme = theme


class _Mini(QWidget):
    """One comparison workspace: header + array view + stats + code."""

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
        outer.setSpacing(7)

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

        # The array is the ONLY vertically-flexible element in a workspace, so
        # when the window is short it shrinks (matplotlib just redraws smaller)
        # instead of colliding with the panels below it.  The shared colour
        # legend lives once beneath both workspaces (see CompareView), keeping
        # each workspace compact and overlap-proof.
        self.array = ArrayView(theme)
        self.array.setMinimumHeight(44)
        self.array.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        outer.addWidget(self.array, 1)
        # Adaptive height: shows the full two-line explanation when there is
        # room (large windows) and compresses gracefully on short screens - the
        # array (the Expanding element) absorbs the difference first.
        self.explanation = ExplanationPanel(theme)
        self.explanation.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.explanation.setMinimumHeight(38)
        self.explanation.setMaximumHeight(70)
        outer.addWidget(self.explanation)

        bottom_w = QWidget()
        self._bottom_w = bottom_w
        bottom_w.setFixedHeight(102)
        bottom = QHBoxLayout(bottom_w)
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(8)
        sc, sl = card_with_title("Statistics")
        self.stats = _MiniStats(theme); sl.addWidget(self.stats)
        cc, cl = card_with_title("Code Viewer")
        self.code = CodeViewer(theme); cl.addWidget(self.code)
        bottom.addWidget(sc, 2); bottom.addWidget(cc, 3)
        outer.addWidget(bottom_w)

        lay.addWidget(c)

    def load(self, info) -> None:
        self.info = info
        self.name.setText(info.name)
        self.code.set_code(info.pseudocode)
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
        self.array.setMinimumHeight(uiscale.sp(44))
        self.explanation.setMinimumHeight(uiscale.sp(38))
        self.explanation.setMaximumHeight(uiscale.sp(70))
        self._bottom_w.setFixedHeight(uiscale.sp(102))
        for w in (self.array, self.stats, self.code, self.explanation):
            if hasattr(w, "apply_scale"):
                w.apply_scale(s)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.name.setStyleSheet(
            f"font-size:{uiscale.fs(14)}px; font-weight:700; color:{theme.text_primary};")
        for w in (self.array, self.stats, self.code, self.explanation):
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
        root.addLayout(row, 3)

        # one shared colour legend for both workspaces (PRD 5.3 visual language)
        self.legend = Legend(theme)
        self.legend.set_items(
            LEGEND_STANDARD + [(STATE_SELECTED, "Selected"), (STATE_PIVOT, "Pivot")])
        leg_row = QHBoxLayout()
        leg_row.addStretch(1)
        leg_row.addWidget(self.legend)
        leg_row.addStretch(1)
        root.addLayout(leg_row)

        # shared timeline (PRD 7.5 - Timeline Navigation affects both sides).
        # Plain card - the Timeline widget carries its own "Operation N" label.
        tl_card = card()
        tl_lay = QVBoxLayout(tl_card)
        tl_lay.setContentsMargins(14, 6, 14, 8)
        tl_lay.setSpacing(2)
        self.timeline = Timeline(theme, style="bar")
        self.timeline.seekRequested.connect(self.seek)
        tl_lay.addWidget(self.timeline)
        root.addWidget(tl_card)

        root.addWidget(self._build_summary())

    def _build_summary(self) -> QWidget:
        frame, lay = card_with_title("Performance Summary")
        lay.setContentsMargins(14, 6, 14, 8)
        lay.setSpacing(4)
        self.summary_grid = QGridLayout()
        self.summary_grid.setHorizontalSpacing(18)
        self.summary_grid.setVerticalSpacing(2)
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
