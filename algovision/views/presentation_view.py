"""Presentation Mode (PRD 7.8).

A distraction-free fullscreen surface that mirrors the *live* single-algorithm
player, so entering/leaving it never interrupts the running algorithm.  It keeps
the playback controls required for classroom use and adds keyboard shortcuts.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout
)

from ..theme.palette import Theme
from ..core.player import frame_exec_seconds
from ..widgets import ArrayView, HeapTreeView, ExplanationPanel
from ..widgets.common import card, section_label


class PresentationView(QWidget):
    exitRequested = pyqtSignal()
    controlTriggered = pyqtSignal(str)
    speedDelta = pyqtSignal(int)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.source = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 20)
        root.setSpacing(14)

        # top bar
        top = QHBoxLayout()
        badge = QLabel("🖥️  PRESENTATION MODE")
        badge.setStyleSheet(f"color:{theme.accent_2}; font-size:16px; font-weight:800;")
        self.esc_hint = QLabel("Press  Esc  to exit")
        self.esc_hint.setProperty("role", "muted")
        top.addStretch(1); top.addWidget(badge); top.addStretch(1); top.addWidget(self.esc_hint)
        root.addLayout(top)

        body = QHBoxLayout()
        body.setSpacing(18)

        # left: big visualization
        left = QVBoxLayout()
        left.setSpacing(10)
        self.algo_name = QLabel("Algorithm")
        self.algo_name.setStyleSheet(f"font-size:30px; font-weight:800; color:{theme.text_primary};")
        self.subtitle = QLabel("")
        self.subtitle.setStyleSheet(f"color:{theme.accent_2}; font-size:15px; font-weight:600;")
        self.stepline = QLabel("")
        self.stepline.setProperty("role", "muted")
        head = QHBoxLayout()
        head.addWidget(self.stepline); head.addStretch(1); head.addWidget(self.subtitle)
        left.addWidget(self.algo_name)
        left.addLayout(head)

        self.array = ArrayView(theme)
        self.heap = HeapTreeView(theme)
        viz = QHBoxLayout()
        viz.addWidget(self.array, 3)
        viz.addWidget(self.heap, 2)
        left.addLayout(viz, 1)
        self.explanation = ExplanationPanel(theme)
        left.addWidget(self.explanation)
        body.addLayout(left, 3)

        # right: live stats + info
        self.side = QVBoxLayout()
        self.side.setSpacing(12)
        self.stats_card, self._stat_labels = self._stat_block(
            "Live Statistics",
            ["Comparisons", "Swaps / Moves", "Execution Time", "Current Operation",
             "Progress", "Steps Executed"])
        self.info_card, self._info_labels = self._stat_block(
            "Algorithm Info",
            ["Time Complexity", "Space Complexity", "Stable", "In-Place"])
        self.data_card, self._data_labels = self._stat_block(
            "Dataset Info", ["Type", "Size", "Range"])
        self.side.addWidget(self.stats_card)
        self.side.addWidget(self.info_card)
        self.side.addWidget(self.data_card)
        self.side.addStretch(1)
        body.addLayout(self.side, 1)
        root.addLayout(body, 1)

        # bottom controls
        root.addWidget(self._controls())

    def _stat_block(self, title, keys):
        c = card()
        v = QVBoxLayout(c)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        v.addWidget(section_label(title))
        labels = {}
        for k in keys:
            row = QHBoxLayout()
            kl = QLabel(k); kl.setProperty("role", "muted")
            vl = QLabel("—"); vl.setProperty("role", "value")
            vl.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(kl); row.addStretch(1); row.addWidget(vl)
            v.addLayout(row)
            labels[k] = vl
        return c, labels

    def _controls(self):
        c = card()
        h = QHBoxLayout(c)
        h.setContentsMargins(14, 8, 14, 8)
        h.setSpacing(8)
        specs = [("▶ Play", "play"), ("⏸ Pause", "pause"), ("⏭ Step", "step"),
                 ("↻ Restart", "restart"), ("⭯ Reset", "reset")]
        for label, key in specs:
            b = QPushButton(label)
            b.setProperty("variant", "ghost")
            b.clicked.connect(lambda _, k=key: self.controlTriggered.emit(k))
            h.addWidget(b)
        h.addStretch(1)
        hint = QLabel("Space Play/Pause   →/← Step   S/F Speed   R Restart   Esc Exit")
        hint.setProperty("role", "muted")
        h.addWidget(hint)
        minus = QPushButton("–"); plus = QPushButton("+")
        for b in (minus, plus):
            b.setProperty("variant", "ghost"); b.setFixedWidth(34)
        minus.clicked.connect(lambda: self.speedDelta.emit(-1))
        plus.clicked.connect(lambda: self.speedDelta.emit(1))
        h.addWidget(minus); h.addWidget(plus)
        return c

    # -- binding to the live single-view player -----------------------------
    def bind(self, source) -> None:
        """Mirror an existing SingleView's player + info."""
        self.source = source
        source.player.frameChanged.connect(self._render)
        self._render(source.player.index)

    def _render(self, _index=0) -> None:
        s = self.source
        if s is None or s.info is None:
            return
        frame = s.player.current()
        if frame is None:
            return
        info = s.info
        self.algo_name.setText(info.name)
        self.subtitle.setText(frame.operation_label)
        self.stepline.setText(
            f"Step {frame.op_number} / {s.player.count}" +
            (f"  ·  Pass {frame.pass_number} / {frame.total_passes}"
             if frame.pass_number and frame.total_passes else ""))
        self.array.render(frame)
        self.heap.setVisible(info.uses_heap_tree)
        if info.uses_heap_tree:
            self.heap.render(frame)
        self.explanation.update_from(frame)

        pct = int(round(100 * frame.op_number / max(1, s.player.count)))
        sl = self._stat_labels
        sl["Comparisons"].setText(str(frame.comparisons))
        sl["Swaps / Moves"].setText(str(frame.swaps))
        sl["Execution Time"].setText(f"{frame_exec_seconds(frame):.3f} s")
        sl["Current Operation"].setText(frame.operation_label or "—")
        sl["Progress"].setText(f"{pct}%")
        sl["Steps Executed"].setText(f"{frame.op_number} / {s.player.count}")

        il = self._info_labels
        il["Time Complexity"].setText(info.average)
        il["Space Complexity"].setText(info.space)
        il["Stable"].setText("Yes" if info.stable else "No")
        il["In-Place"].setText("Yes" if info.in_place else "No")

        dl = self._data_labels
        dl["Type"].setText(s.dataset_val.text())
        dl["Size"].setText(str(len(s.original)))
        dl["Range"].setText("1 – 1000")

    # -- keyboard -----------------------------------------------------------
    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key.Key_Escape:
            self.exitRequested.emit()
        elif k == Qt.Key.Key_Space:
            self.controlTriggered.emit("toggle")
        elif k in (Qt.Key.Key_Right,):
            self.controlTriggered.emit("step")
        elif k in (Qt.Key.Key_Left,):
            self.controlTriggered.emit("prev")
        elif k == Qt.Key.Key_R:
            self.controlTriggered.emit("restart")
        elif k == Qt.Key.Key_F:
            self.speedDelta.emit(1)
        elif k == Qt.Key.Key_S:
            self.speedDelta.emit(-1)
        else:
            super().keyPressEvent(e)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        for w in (self.array, self.heap, self.explanation):
            w.set_theme(theme)
