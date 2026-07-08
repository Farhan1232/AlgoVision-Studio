"""Explanation Panel (PRD 8.5) - live plain-language description of the step."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel

from ..theme.palette import Theme
from ..core.frames import Frame
from .common import info_box


class ExplanationPanel(QWidget):
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self.box = info_box()
        row = QHBoxLayout(self.box)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(12)

        self.icon = QLabel("ℹ️")
        self.icon.setStyleSheet("font-size:18px;")
        self.icon.setAlignment(Qt.AlignmentFlag.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        self.title = QLabel("Ready")
        self.title.setWordWrap(True)
        self.detail = QLabel("Select an algorithm and press Play to begin.")
        self.detail.setWordWrap(True)
        self.detail.setProperty("role", "muted")
        text_col.addWidget(self.title)
        text_col.addWidget(self.detail)

        row.addWidget(self.icon)
        row.addLayout(text_col, 1)
        lay.addWidget(self.box)
        self._restyle()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._restyle()

    def update_from(self, frame: Frame) -> None:
        if frame is None:
            return
        self.title.setText(frame.explanation_title or frame.operation_label or "—")
        self.detail.setText(frame.explanation_detail or "")

    def _restyle(self) -> None:
        t = self.theme
        self.title.setStyleSheet(f"color:{t.accent_2}; font-weight:700; font-size:14px;")
        self.detail.setStyleSheet(f"color:{t.text_secondary};")
