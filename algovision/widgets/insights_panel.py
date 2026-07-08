"""Algorithm Insights panel (PRD 8.2) - static reference info per algorithm."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea
)

from ..theme.palette import Theme
from ..core.registry import AlgorithmInfo


class InsightsPanel(QWidget):
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._info: AlgorithmInfo | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.body = QWidget()
        self.vbox = QVBoxLayout(self.body)
        self.vbox.setContentsMargins(2, 2, 8, 2)
        self.vbox.setSpacing(9)
        self.scroll.setWidget(self.body)
        outer.addWidget(self.scroll)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        if self._info:
            self.set_info(self._info)

    def set_info(self, info: AlgorithmInfo) -> None:
        self._info = info
        t = self.theme
        while self.vbox.count():
            it = self.vbox.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        def block(icon: str, label: str, value_html: str):
            w = QWidget()
            row = QHBoxLayout(w)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            ic = QLabel(icon)
            ic.setFixedWidth(18)
            ic.setAlignment(Qt.AlignmentFlag.AlignTop)
            text = QLabel()
            text.setTextFormat(Qt.TextFormat.RichText)
            text.setWordWrap(True)
            text.setText(
                f"<span style='color:{t.text_primary}; font-weight:600'>{label}</span>"
                f"<br><span style='color:{t.text_secondary}'>{value_html}</span>"
            )
            row.addWidget(ic)
            row.addWidget(text, 1)
            self.vbox.addWidget(w)

        ok = t.success
        bad = t.danger
        acc = t.accent
        yes_no = lambda b: (f"<span style='color:{ok}'>Yes</span>" if b
                            else f"<span style='color:{bad}'>No</span>")

        block("ℹ️", "Overview", info.overview)
        block("⚙️", "Working Principle", info.working_principle)
        block("⏱️", "Time Complexity",
              f"Best <span style='color:{acc}'>{info.best}</span> · "
              f"Average <span style='color:{acc}'>{info.average}</span> · "
              f"Worst <span style='color:{acc}'>{info.worst}</span>")
        block("🧠", "Space Complexity", f"<span style='color:{ok}'>{info.space}</span>")
        block("🔒", "Stable", yes_no(info.stable))
        block("📦", "In-place Sorting", yes_no(info.in_place))
        block("✅", "Advantages", info.advantages)
        block("⚠️", "Limitations", info.limitations)
        block("🏷️", "Typical Applications", info.applications)
        block("🎯", "Best Used For", info.best_used_for)
        block("💡", "Key Idea", info.key_idea)
        self.vbox.addStretch(1)
