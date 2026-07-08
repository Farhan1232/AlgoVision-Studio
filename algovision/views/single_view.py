"""Single Algorithm workspace (PRD Sections 3, 5, 8).

Composes the Sorting Visualization (Numbered Block View + optional Heap Tree
View), Explanation Panel, Timeline, Statistics Dashboard, Code Viewer and
Algorithm Insights, all driven by one :class:`Player`.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSplitter, QSizePolicy
)

from ..theme.palette import Theme
from ..core import registry
from ..core.registry import AlgorithmInfo
from ..core.player import Player
from ..widgets import (
    ArrayView, HeapTreeView, CodeViewer, StatsDashboard,
    InsightsPanel, ExplanationPanel, Timeline, Legend,
)
from ..widgets.common import card, card_with_title


class SingleView(QWidget):
    statusChanged = pyqtSignal(str)
    finished = pyqtSignal()
    editArrayRequested = pyqtSignal()

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.info: AlgorithmInfo | None = None
        self.original: list[int] = []

        self.player = Player(self)
        self.player.frameChanged.connect(self._on_frame)
        self.player.statusChanged.connect(self._on_status)
        self.player.finished.connect(self.finished)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        root.addWidget(self._build_header())
        root.addWidget(self._build_visualization(), 5)
        root.addWidget(self.explanation)
        root.addWidget(self._build_timeline_card())
        root.addWidget(self._build_bottom(), 4)

    # -- construction -------------------------------------------------------
    def _build_header(self) -> QWidget:
        c = card()
        lay = QHBoxLayout(c)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(12)

        self.title = QLabel("VISUALIZATION")
        self.title.setProperty("role", "title")
        self.badge = QLabel("Reset")
        self.badge.setProperty("role", "badge-reset")
        self.steps = QLabel("Step 0 / 0"); self.steps.setProperty("role", "muted")
        self.phase = QLabel(""); self.phase.setProperty("role", "muted")
        self.operation = QLabel(""); self.operation.setProperty("role", "muted")

        lay.addWidget(self.title)
        lay.addWidget(self.badge)
        lay.addWidget(self.steps)
        lay.addWidget(self.phase)
        lay.addWidget(self.operation)
        lay.addStretch(1)

        self.dataset_lbl = QLabel("Dataset:")
        self.dataset_lbl.setProperty("role", "muted")
        self.dataset_val = QLabel("Custom Array"); self.dataset_val.setProperty("role", "ok")
        self.size_lbl = QLabel("Size:"); self.size_lbl.setProperty("role", "muted")
        self.size_val = QLabel("0"); self.size_val.setProperty("role", "value")
        self.edit_btn = QPushButton("✎  Edit Array")
        self.edit_btn.setProperty("variant", "primary")
        self.edit_btn.clicked.connect(self.editArrayRequested)
        for w in (self.dataset_lbl, self.dataset_val, self.size_lbl, self.size_val, self.edit_btn):
            lay.addWidget(w)
        return c

    def _build_visualization(self) -> QWidget:
        self.viz_card = card()
        outer = QVBoxLayout(self.viz_card)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(8)

        head = QHBoxLayout()
        self.array_title = QLabel("ARRAY VIEW")
        self.array_title.setProperty("role", "section")
        self.tree_title = QLabel("HEAP TREE VIEW (MAX HEAP)")
        self.tree_title.setProperty("role", "section")
        head.addWidget(self.array_title)
        head.addStretch(1)
        head.addWidget(self.tree_title)
        outer.addLayout(head)

        self.array_view = ArrayView(self.theme)
        self.heap_view = HeapTreeView(self.theme)
        self.array_view.setMinimumHeight(200)
        self.heap_view.setMinimumHeight(200)
        self.array_view.blockClicked.connect(self._cross_highlight)
        self.heap_view.nodeClicked.connect(self._cross_highlight)

        self.viz_split = QSplitter(Qt.Orientation.Horizontal)
        self.viz_split.addWidget(self.array_view)
        self.viz_split.addWidget(self.heap_view)
        self.viz_split.setSizes([560, 440])
        outer.addWidget(self.viz_split, 1)

        self.legend = Legend(self.theme)
        outer.addWidget(self.legend)

        self.explanation = ExplanationPanel(self.theme)
        return self.viz_card

    def _build_timeline_card(self) -> QWidget:
        frame, lay = card_with_title("Timeline")
        lay.setContentsMargins(14, 8, 14, 10)
        self.timeline = Timeline(self.theme)
        self.timeline.seekRequested.connect(self.player.seek)
        lay.addWidget(self.timeline)
        self._timeline_card = frame
        return frame

    def _build_bottom(self) -> QWidget:
        container = QWidget()
        container.setMinimumHeight(240)
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        stats_card, stats_lay = card_with_title("Statistics")
        self.stats = StatsDashboard(self.theme)
        stats_lay.addWidget(self.stats)

        self.code_card, code_lay = card_with_title("Code Viewer")
        self.code = CodeViewer(self.theme)
        code_lay.addWidget(self.code)

        insights_card, ins_lay = card_with_title("Algorithm Insights")
        self.insights = InsightsPanel(self.theme)
        ins_lay.addWidget(self.insights)

        row.addWidget(stats_card, 3)
        row.addWidget(self.code_card, 4)
        row.addWidget(insights_card, 4)
        return container

    # -- data / lifecycle ---------------------------------------------------
    def load(self, info: AlgorithmInfo, dataset: list[int], dataset_label: str = "Custom Array") -> None:
        self.info = info
        self.original = list(dataset)
        frames = info.trace(list(dataset))
        self.player.load(frames)

        self.title.setText(f"{info.name.upper()} VISUALIZATION")
        self.code.set_code(info.pseudocode)
        self.insights.set_info(info)
        self.legend.set_items(info.legend)
        self.dataset_val.setText(dataset_label)
        self.size_val.setText(str(len(dataset)))
        self.array_title.setText("ARRAY VIEW (LEVEL ORDER)" if info.uses_heap_tree else "ARRAY VIEW")

        is_heap = info.uses_heap_tree
        self.heap_view.setVisible(is_heap)
        self.tree_title.setVisible(is_heap)
        self.stats.clear()
        self.timeline.configure(self.player.count, 0)
        self._on_frame(0)

    # -- playback delegation ------------------------------------------------
    def play(self):
        self.player.play()

    def pause(self):
        self.player.pause()

    def step(self):
        self.player.step()

    def restart(self):
        self.player.restart()

    def reset(self):
        self.player.reset()

    def set_speed(self, mult: float):
        self.player.set_speed(mult)

    def is_completed(self) -> bool:
        return self.player.status == Player.STATUS_COMPLETED

    def final_frame(self):
        return self.player.frames[-1] if self.player.frames else None

    # -- rendering ----------------------------------------------------------
    def _on_frame(self, index: int) -> None:
        frame = self.player.current()
        if frame is None:
            return
        self.array_view.render(frame)
        if self.info and self.info.uses_heap_tree:
            self.heap_view.render(frame)
        self.stats.update_from(frame, self.player.count)
        self.code.highlight(frame.code_lines)
        self.explanation.update_from(frame)
        self.timeline.update_current(index, frame.op_number, frame.operation_label)

        self.steps.setText(f"Step {frame.op_number} / {self.player.count}")
        if self.info and self.info.uses_heap_tree and frame.phase:
            self.phase.setText(f"Phase: {frame.phase}")
            self.phase.setVisible(True)
        else:
            self.phase.setVisible(False)
        self.operation.setText(f"Operation: {frame.operation_label}" if frame.operation_label else "")

    def _on_status(self, status: str) -> None:
        self.badge.setText(status)
        self.badge.setProperty("role", f"badge-{status.lower()}")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)
        self.statusChanged.emit(status)

    def _cross_highlight(self, index: int) -> None:
        self.array_view.set_highlight(index)
        if self.info and self.info.uses_heap_tree:
            self.heap_view.set_highlight(index)

    # -- theme --------------------------------------------------------------
    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        for w in (self.array_view, self.heap_view, self.code, self.stats,
                  self.insights, self.explanation, self.timeline, self.legend):
            w.set_theme(theme)
