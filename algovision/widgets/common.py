"""Small reusable widget factory helpers."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget, QHBoxLayout


def card(parent=None) -> QFrame:
    f = QFrame(parent)
    f.setProperty("role", "card")
    return f


def info_box(parent=None) -> QFrame:
    f = QFrame(parent)
    f.setProperty("role", "info")
    return f


def section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setProperty("role", "section")
    return lbl


def title_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("role", "title")
    return lbl


def muted(text: str = "") -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("role", "muted")
    return lbl


def hline() -> QFrame:
    f = QFrame()
    f.setProperty("role", "divider")
    f.setFixedHeight(1)
    return f


def card_with_title(title: str):
    """Return (frame, body_layout) where body_layout is where to add content."""
    frame = card()
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(14, 12, 14, 12)
    outer.setSpacing(8)
    outer.addWidget(title_label(title))
    return frame, outer


def kv_row(key: str, value_widget: QWidget) -> QWidget:
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    k = muted(key)
    lay.addWidget(k)
    lay.addStretch(1)
    lay.addWidget(value_widget)
    return row
