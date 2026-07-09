"""Statistics Dashboard (PRD 8.1) - live execution metrics.

Shows every field required by PRD 8.1: Selected Algorithm, Dataset Size,
Current Operation, Current Pass, Comparisons, Swaps, Execution Time, Progress
and Current Status, plus any algorithm-specific extra stats (e.g. Heapify
Calls) and the running Steps Executed counter.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QGridLayout,
    QScrollArea
)

from ..theme.palette import Theme
from ..core.frames import Frame
from ..core.player import frame_exec_seconds

# Fixed field order (PRD 8.1).  Extra per-algorithm stats (e.g. Heapify Calls)
# are appended live after these.
_FIELDS = [
    "Selected Algorithm",
    "Dataset Size",
    "Current Status",
    "Comparisons",
    "Swaps",
    "Execution Time",
    "Current Operation",
    "Current Pass",
    "Steps Executed",
]


class StatsDashboard(QWidget):
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._value_labels: dict[str, QLabel] = {}
        self._extra_rows: dict[str, tuple[QLabel, QLabel]] = {}
        self._algo_name = "—"
        self._dataset_size = 0
        self._status = "Reset"

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        # The metric rows live in a scroll area so that on short windows they
        # scroll internally instead of overlapping; on normal/large windows
        # everything is visible at once with no scrollbar.  The progress bar is
        # pinned below the scroll area so it stays visible during playback.
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(1, 1)
        self._grid = grid
        self._row = 0

        for key in _FIELDS:
            self._add_row(key)

        body_lay.addLayout(grid)
        body_lay.addStretch(1)
        self._scroll.setWidget(body)
        lay.addWidget(self._scroll, 1)

        # progress (pinned below the scrollable metrics) --------------------
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

        # baseline values
        self._value_labels["Selected Algorithm"].setText(self._algo_name)
        self._value_labels["Current Status"].setText(self._status)

    # -- construction -------------------------------------------------------
    def _add_row(self, key: str, extra: bool = False) -> None:
        k = QLabel(key)
        k.setProperty("role", "muted")
        v = QLabel("—")
        v.setProperty("role", "value")
        v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        v.setWordWrap(True)
        self._grid.addWidget(k, self._row, 0,
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._grid.addWidget(v, self._row, 1)
        self._value_labels[key] = v
        if extra:
            self._extra_rows[key] = (k, v)
        self._row += 1

    def _clear_extra_rows(self) -> None:
        """Remove algorithm-specific rows (e.g. Heapify Calls) so they don't
        linger after switching to an algorithm that doesn't report them."""
        for key, (k, v) in self._extra_rows.items():
            for w in (k, v):
                self._grid.removeWidget(w)
                w.setParent(None)
                w.deleteLater()
            self._value_labels.pop(key, None)
            self._row -= 1
        self._extra_rows = {}

    # -- external state -----------------------------------------------------
    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._apply_status_style()

    def apply_scale(self, s: float) -> None:
        from ..theme import scale as uiscale
        self._grid.setVerticalSpacing(uiscale.sp(6))
        self._grid.setHorizontalSpacing(uiscale.sp(10))
        self._apply_status_style()

    def set_meta(self, algo_name: str, dataset_size: int) -> None:
        """Static context that does not depend on the current frame."""
        self._clear_extra_rows()
        self._algo_name = algo_name
        self._dataset_size = dataset_size
        self._value_labels["Selected Algorithm"].setText(algo_name)
        self._value_labels["Dataset Size"].setText(str(dataset_size))

    def set_status(self, status: str) -> None:
        self._status = status
        self._value_labels["Current Status"].setText(status)
        self._apply_status_style()

    def _apply_status_style(self) -> None:
        colors = {
            "Running": self.theme.accent_2,
            "Completed": self.theme.success,
            "Paused": self.theme.warning,
            "Reset": self.theme.text_secondary,
        }
        c = colors.get(self._status, self.theme.text_primary)
        self._value_labels["Current Status"].setStyleSheet(
            f"color:{c}; font-weight:700;")

    def clear(self) -> None:
        for key, v in self._value_labels.items():
            if key == "Selected Algorithm":
                v.setText(self._algo_name)
            elif key == "Dataset Size":
                v.setText(str(self._dataset_size))
            elif key == "Current Status":
                v.setText(self._status)
            else:
                v.setText("—")
        self.progress.setValue(0)
        self.progress_pct.setText("0%")

    # -- live update --------------------------------------------------------
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

        # dynamic extra stats (e.g. Heapify Calls) appended after fixed fields
        for key, val in frame.extra_stats.items():
            if key not in v:
                self._add_row(key, extra=True)
            v[key].setText(str(val))

        pct = int(round(100 * frame.op_number / max(1, total_frames)))
        self.progress.setValue(pct)
        self.progress_pct.setText(f"{pct}%")
