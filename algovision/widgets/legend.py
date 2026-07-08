"""Colour legend chips shown beneath the visualization (PRD 5.3)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame

from ..theme.palette import Theme, STATE_COLORS


class Legend(QWidget):
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._items: list = []
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(2, 2, 2, 2)
        self._lay.setSpacing(14)

    def set_items(self, items: list[tuple[str, str]]) -> None:
        self._items = items
        self._rebuild()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._rebuild()

    def _rebuild(self) -> None:
        while self._lay.count():
            item = self._lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for state_key, label in self._items:
            chip = QWidget()
            row = QHBoxLayout(chip)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            swatch = QFrame()
            swatch.setFixedSize(13, 13)
            color = STATE_COLORS.get(state_key, "#888888")
            swatch.setStyleSheet(f"background:{color}; border-radius:3px;")
            text = QLabel(label)
            text.setStyleSheet(f"color:{self.theme.text_secondary}; font-size:11px;")
            row.addWidget(swatch)
            row.addWidget(text)
            self._lay.addWidget(chip)
        self._lay.addStretch(1)
