"""Algorithm Comparison Mode (PRD 7.5 + 8.4).

Runs two algorithms on the SAME dataset under one shared clock.  Play, Pause,
Step, Restart, Reset, Timeline and Speed affect both sides simultaneously so
the comparison is fair.  A shared Performance Summary highlights the algorithm
that finished more efficiently.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QComboBox
)

from ..theme.palette import Theme
from ..core import registry
from ..core.player import frame_exec_seconds
from ..config import BASE_FRAME_MS
from ..widgets import ArrayView, CodeViewer, StatsDashboard, ExplanationPanel, Legend
from ..widgets.common import card, card_with_title, title_label


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
        outer.setContentsMargins(12, 10, 12, 12)
        outer.setSpacing(8)

        head = QHBoxLayout()
        self.name = title_label("Algorithm")
        self.badge = QLabel("Reset"); self.badge.setProperty("role", "badge-reset")
        self.steps = QLabel(""); self.steps.setProperty("role", "muted")
        head.addWidget(self.name); head.addWidget(self.badge)
        head.addStretch(1); head.addWidget(self.steps)
        outer.addLayout(head)

        self.array = ArrayView(theme)
        self.array.setMinimumHeight(150)
        outer.addWidget(self.array, 4)
        self.legend = Legend(theme)
        outer.addWidget(self.legend)
        self.explanation = ExplanationPanel(theme)
        outer.addWidget(self.explanation)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        sc, sl = card_with_title("Statistics")
        self.stats = StatsDashboard(theme); sl.addWidget(self.stats)
        cc, cl = card_with_title("Code Viewer")
        self.code = CodeViewer(theme); cl.addWidget(self.code)
        bottom.addWidget(sc, 1); bottom.addWidget(cc, 1)
        outer.addLayout(bottom, 2)

        lay.addWidget(c)

    def load(self, info) -> None:
        self.info = info
        self.name.setText(info.name)
        self.code.set_code(info.pseudocode)
        self.legend.set_items(info.legend)
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
        status = "Completed" if done else ("Running" if pos < total else "Completed")
        self.badge.setText(status)
        self.badge.setProperty("role", f"badge-{status.lower()}")
        self.badge.style().unpolish(self.badge); self.badge.style().polish(self.badge)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        for w in (self.array, self.stats, self.code, self.explanation, self.legend):
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
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        top = QHBoxLayout()
        header = QLabel("COMPARISON MODE")
        header.setProperty("role", "title")
        top.addWidget(header)
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
        top.addWidget(QLabel("Left:"))
        top.addWidget(self.combo_a)
        top.addSpacing(10)
        top.addWidget(QLabel("Right:"))
        top.addWidget(self.combo_b)
        root.addLayout(top)
        sub = QLabel("Two algorithms run simultaneously on the same dataset with shared controls.")
        sub.setProperty("role", "muted")
        root.addWidget(sub)

        self.left = _Mini(theme)
        self.right = _Mini(theme)
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self.left, 1)
        row.addWidget(self.right, 1)
        root.addLayout(row, 1)

        root.addWidget(self._build_summary())

    def _build_summary(self) -> QWidget:
        frame, lay = card_with_title("Performance Summary")
        self.summary_row = QHBoxLayout()
        self.summary_row.setSpacing(20)
        holder = QWidget()
        holder.setLayout(self.summary_row)
        lay.addWidget(holder)
        self._summary_frame = frame
        self.winner_label = QLabel("")
        self.winner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.winner_label)
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

    # -- performance summary ------------------------------------------------
    def _update_summary(self):
        while self.summary_row.count():
            it = self.summary_row.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        fa = self.left.frames[-1]
        fb = self.right.frames[-1]
        ia, ib = self.left.info, self.right.info
        ta, tb = frame_exec_seconds(fa), frame_exec_seconds(fb)

        def tile(info, frame, t, winner):
            w = card()
            v = QVBoxLayout(w)
            v.setContentsMargins(12, 10, 12, 10)
            name = QLabel(("🏆  " if winner else "") + info.name)
            name.setStyleSheet(
                f"font-weight:700; color:{self.theme.success if winner else self.theme.text_primary};")
            v.addWidget(name)
            v.addWidget(QLabel(f"Comparisons: {frame.comparisons}"))
            v.addWidget(QLabel(f"Swaps / Moves: {frame.swaps}"))
            v.addWidget(QLabel(f"Execution Time: {t:.3f} s"))
            v.addWidget(QLabel(f"Time Complexity: {info.average}"))
            v.addWidget(QLabel(f"Space Complexity: {info.space}"))
            return w

        # more efficient = lower execution time, tie-break on total operations
        a_ops = fa.comparisons + fa.swaps
        b_ops = fb.comparisons + fb.swaps
        if (ta, a_ops) < (tb, b_ops):
            win_a, win_b, winner = True, False, ia.name
        elif (tb, b_ops) < (ta, a_ops):
            win_a, win_b, winner = False, True, ib.name
        else:
            win_a = win_b = False
            winner = "Tie"

        self.summary_row.addWidget(tile(ia, fa, ta, win_a))
        self.summary_row.addWidget(tile(ib, fb, tb, win_b))
        self.winner_label.setText(
            f"More efficient on this dataset: <b style='color:{self.theme.success}'>{winner}</b>")
        self.winner_label.setTextFormat(Qt.TextFormat.RichText)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.left.set_theme(theme)
        self.right.set_theme(theme)
        if self.left.frames:
            self._update_summary()
