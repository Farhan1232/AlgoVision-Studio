"""Edit Array dialog - custom input / random / shuffle / clear (PRD 7.3)."""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox
)

from ..theme.palette import Theme
from ..core import dataset
from ..resources import asset
from ..config import VALUE_MIN, VALUE_MAX, ARRAY_SIZE_MIN, CUSTOM_MAX_ELEMENTS

_SAMPLES_PATH = asset("sample_datasets.json")


def _load_samples() -> list[dict]:
    try:
        data = json.loads(_SAMPLES_PATH.read_text(encoding="utf-8"))
        return data.get("samples", [])
    except Exception:
        return []


class EditArrayDialog(QDialog):
    def __init__(self, theme: Theme, current: list[int], size: int, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._size = size
        self._result: list[int] | None = None
        self.setWindowTitle("Edit Array")
        self.setMinimumWidth(460)

        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(10)

        v.addWidget(QLabel("Custom Array Input"))
        hint = QLabel(
            f"Comma-separated positive integers ({VALUE_MIN}–{VALUE_MAX}). "
            f"{ARRAY_SIZE_MIN}–{CUSTOM_MAX_ELEMENTS} values. e.g. 64, 34, 25, 12, 22, 11, 90")
        hint.setProperty("role", "muted")
        hint.setWordWrap(True)
        v.addWidget(hint)

        self.edit = QLineEdit(", ".join(map(str, current)))
        v.addWidget(self.edit)

        # sample dataset presets (PRD deliverable: sample datasets)
        samples = _load_samples()
        if samples:
            sample_row = QHBoxLayout()
            lbl = QLabel("Sample datasets:")
            lbl.setProperty("role", "muted")
            self.sample_combo = QComboBox()
            self.sample_combo.addItem("— Choose a sample —", None)
            for s in samples:
                self.sample_combo.addItem(s["name"], s["values"])
            self.sample_combo.currentIndexChanged.connect(self._on_sample)
            sample_row.addWidget(lbl)
            sample_row.addWidget(self.sample_combo, 1)
            v.addLayout(sample_row)

        self.msg = QLabel("")
        self.msg.setWordWrap(True)
        v.addWidget(self.msg)

        gen_row = QHBoxLayout()
        self.btn_random = QPushButton("🎲  Random")
        self.btn_shuffle = QPushButton("🔀  Shuffle")
        self.btn_clear = QPushButton("🗑  Clear")
        for b in (self.btn_random, self.btn_shuffle, self.btn_clear):
            b.setProperty("variant", "ghost")
            gen_row.addWidget(b)
        gen_row.addStretch(1)
        v.addLayout(gen_row)
        self.btn_random.clicked.connect(self._on_random)
        self.btn_shuffle.clicked.connect(self._on_shuffle)
        self.btn_clear.clicked.connect(lambda: self.edit.setText(""))

        act_row = QHBoxLayout()
        act_row.addStretch(1)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setProperty("variant", "ghost")
        self.btn_apply = QPushButton("Apply Array")
        self.btn_apply.setProperty("variant", "primary")
        act_row.addWidget(self.btn_cancel)
        act_row.addWidget(self.btn_apply)
        v.addLayout(act_row)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_apply.clicked.connect(self._on_apply)

    def _values_from_field(self) -> list[int]:
        return dataset.parse_custom_input(self.edit.text())

    def _on_sample(self, idx: int):
        vals = self.sample_combo.itemData(idx)
        if vals:
            self.edit.setText(", ".join(map(str, vals)))
            self._clear_error()

    def _on_random(self):
        vals = dataset.random_dataset(self._size)
        self.edit.setText(", ".join(map(str, vals)))
        self._clear_error()

    def _on_shuffle(self):
        try:
            vals = self._values_from_field()
        except dataset.ValidationError:
            vals = dataset.random_dataset(self._size)
        self.edit.setText(", ".join(map(str, dataset.shuffle_dataset(vals))))
        self._clear_error()

    def _on_apply(self):
        try:
            self._result = self._values_from_field()
            self.accept()
        except dataset.ValidationError as exc:
            self._show_error(str(exc))

    def result_dataset(self) -> list[int] | None:
        return self._result

    def _show_error(self, text: str):
        self.msg.setText(f"⚠  {text}")
        self.msg.setStyleSheet(f"color:{self.theme.danger};")
        self.edit.setProperty("state", "error")
        self.edit.style().unpolish(self.edit); self.edit.style().polish(self.edit)

    def _clear_error(self):
        self.msg.setText("")
        self.edit.setProperty("state", "")
        self.edit.style().unpolish(self.edit); self.edit.style().polish(self.edit)
