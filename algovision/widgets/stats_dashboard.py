"""Statistics Dashboard (PRD 8.1) - live execution metrics."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QGridLayout
)

from ..theme.palette import Theme
from ..core.frames import Frame
from ..core.player import frame_exec_seconds


class StatsDashboard(QWidget):
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._value_labels: dict[str, QLabel] = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(7)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(7)
        self._grid = grid
        self._row = 0

        for key in ["Comparisons", "Swaps", "Execution Time",
                    "Current Operation", "Current Pass", "Steps Executed"]:
            self._add_row(key)

        lay.addLayout(grid)

        # progress
        prog_lbl = QLabel("Progress")
        prog_lbl.setProperty("role", "muted")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress_pct = QLabel("0%")
        self.progress_pct.setProperty("role", "value")

        prow = QHBoxLayout()
        prow.addWidget(prog_lbl)
        prow.addStretch(1)
        prow.addWidget(self.progress_pct)
        lay.addSpacing(2)
        lay.addLayout(prow)
        lay.addWidget(self.progress)
        lay.addStretch(1)

    def _add_row(self, key: str) -> None:
        k = QLabel(key)
        k.setProperty("role", "muted")
        v = QLabel("—")
        v.setProperty("role", "value")
        v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        v.setWordWrap(True)
        self._grid.addWidget(k, self._row, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._grid.addWidget(v, self._row, 1)
        self._grid.setColumnStretch(1, 1)
        self._value_labels[key] = v
        self._row += 1

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme

    def clear(self) -> None:
        for v in self._value_labels.values():
            v.setText("—")
        self.progress.setValue(0)
        self.progress_pct.setText("0%")

    def update_from(self, frame: Frame, total_frames: int) -> None:
        if frame is None:
            return
        v = self._value_labels
        v["Comparisons"].setText(str(frame.comparisons))
        v["Swaps"].setText(str(frame.swaps))
        v["Execution Time"].setText(f"{frame_exec_seconds(frame):.3f} s")
        v["Current Operation"].setText(frame.operation_label or "—")
        if frame.pass_number is not None and frame.total_passes:
            v["Current Pass"].setText(f"{frame.pass_number} / {frame.total_passes}")
        else:
            v["Current Pass"].setText("—")
        v["Steps Executed"].setText(f"{frame.op_number} / {total_frames}")

        # dynamic extra stats (e.g. Heapify Calls) added on demand
        for key, val in frame.extra_stats.items():
            if key not in v:
                self._add_row(key)
            v[key].setText(str(val))

        pct = int(round(100 * frame.op_number / max(1, total_frames)))
        self.progress.setValue(pct)
        self.progress_pct.setText(f"{pct}%")
