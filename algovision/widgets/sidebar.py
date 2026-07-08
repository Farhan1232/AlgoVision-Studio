"""Navigation + Control panel (PRD Section 3 Navigation Panel, 7.1, 7.2, 7.4)."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QButtonGroup,
    QPushButton, QSlider, QComboBox, QScrollArea, QSizePolicy
)

from ..theme.palette import Theme
from ..core import registry
from ..config import (
    ARRAY_SIZE_MIN, ARRAY_SIZE_MAX, ARRAY_SIZE_DEFAULT,
    SPEED_CHOICES, SPEED_LABELS, SPEED_DEFAULT, SHORTCUTS,
)
from .common import section_label


def _control_button(icon: str, label: str, key: str = "") -> QPushButton:
    btn = QPushButton()
    btn.setProperty("variant", "control")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    hb = QHBoxLayout(btn)
    hb.setContentsMargins(10, 6, 10, 6)
    hb.setSpacing(8)
    lead = QLabel(f"{icon}  {label}")
    lead.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    hb.addWidget(lead)
    hb.addStretch(1)
    if key:
        kb = QLabel(key)
        kb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        kb.setStyleSheet("color:rgba(150,160,180,0.9); font-size:10px;")
        hb.addWidget(kb)
    return btn


class Sidebar(QScrollArea):
    algorithmSelected = pyqtSignal(str)
    modeChanged = pyqtSignal(str)
    controlTriggered = pyqtSignal(str)     # play/pause/step/restart/reset
    randomRequested = pyqtSignal()
    shuffleRequested = pyqtSignal()
    sizeChanged = pyqtSignal(int)
    speedChanged = pyqtSignal(float)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("Sidebar")
        self.setFixedWidth(238)

        body = QWidget()
        body.setObjectName("Sidebar")
        self.setWidget(body)
        v = QVBoxLayout(body)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(6)

        # --- ALGORITHMS ----------------------------------------------------
        v.addWidget(section_label("Algorithms"))
        self.algo_group = QButtonGroup(self)
        self.algo_group.setExclusive(True)
        self._algo_buttons: dict[str, QPushButton] = {}
        for info in registry.all_algorithms():
            rb = QPushButton(info.short)
            rb.setProperty("variant", "nav")
            rb.setCheckable(True)
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            self.algo_group.addButton(rb)
            self._algo_buttons[info.key] = rb
            rb.clicked.connect(lambda _, k=info.key: self.algorithmSelected.emit(k))
            v.addWidget(rb)
        v.addSpacing(8)

        # --- MODES ---------------------------------------------------------
        v.addWidget(section_label("Modes"))
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.btn_single = QPushButton("📈  Single Algorithm")
        self.btn_compare = QPushButton("🔀  Compare Algorithms")
        for b, m in ((self.btn_single, "single"), (self.btn_compare, "compare")):
            b.setProperty("variant", "mode")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.mode_group.addButton(b)
            b.clicked.connect(lambda _, mode=m: self.modeChanged.emit(mode))
            v.addWidget(b)
        self.btn_single.setChecked(True)
        v.addSpacing(8)

        # --- CONTROLS ------------------------------------------------------
        v.addWidget(section_label("Controls"))
        self.btn_play = _control_button("▶", "Play", SHORTCUTS["play"])
        self.btn_pause = _control_button("⏸", "Pause", SHORTCUTS["pause"])
        self.btn_step = _control_button("⏭", "Step", SHORTCUTS["step"])
        self.btn_restart = _control_button("↻", "Restart", SHORTCUTS["restart"])
        self.btn_reset = _control_button("⭯", "Reset", SHORTCUTS["reset"])
        self.btn_random = _control_button("🎲", "Random Array")
        self.btn_shuffle = _control_button("🔀", "Shuffle Array")
        self.btn_play.clicked.connect(lambda: self.controlTriggered.emit("play"))
        self.btn_pause.clicked.connect(lambda: self.controlTriggered.emit("pause"))
        self.btn_step.clicked.connect(lambda: self.controlTriggered.emit("step"))
        self.btn_restart.clicked.connect(lambda: self.controlTriggered.emit("restart"))
        self.btn_reset.clicked.connect(lambda: self.controlTriggered.emit("reset"))
        self.btn_random.clicked.connect(self.randomRequested)
        self.btn_shuffle.clicked.connect(self.shuffleRequested)
        for b in (self.btn_play, self.btn_pause, self.btn_step, self.btn_restart,
                  self.btn_reset, self.btn_random, self.btn_shuffle):
            v.addWidget(b)
        v.addSpacing(8)

        # --- ARRAY CONFIGURATION ------------------------------------------
        v.addWidget(section_label("Array Configuration"))
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Array Size"))
        size_row.addStretch(1)
        self.size_value = QLabel(str(ARRAY_SIZE_DEFAULT))
        self.size_value.setProperty("role", "value")
        size_row.addWidget(self.size_value)
        v.addLayout(size_row)

        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(ARRAY_SIZE_MIN, ARRAY_SIZE_MAX)
        self.size_slider.setValue(ARRAY_SIZE_DEFAULT)
        self.size_slider.valueChanged.connect(self._on_size)
        v.addWidget(self.size_slider)
        range_row = QHBoxLayout()
        lo = QLabel(str(ARRAY_SIZE_MIN)); lo.setProperty("role", "muted")
        hi = QLabel(str(ARRAY_SIZE_MAX)); hi.setProperty("role", "muted")
        range_row.addWidget(lo); range_row.addStretch(1); range_row.addWidget(hi)
        v.addLayout(range_row)

        v.addSpacing(6)
        v.addWidget(QLabel("Animation Speed"))
        self.speed_combo = QComboBox()
        for spd in SPEED_CHOICES:
            self.speed_combo.addItem(SPEED_LABELS[spd], spd)
        self.speed_combo.setCurrentIndex(SPEED_CHOICES.index(SPEED_DEFAULT))
        self.speed_combo.currentIndexChanged.connect(
            lambda i: self.speedChanged.emit(float(self.speed_combo.itemData(i))))
        v.addWidget(self.speed_combo)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(0, len(SPEED_CHOICES) - 1)
        self.speed_slider.setValue(SPEED_CHOICES.index(SPEED_DEFAULT))
        self.speed_slider.valueChanged.connect(self._on_speed_slider)
        v.addWidget(self.speed_slider)
        tick_row = QHBoxLayout()
        for spd in SPEED_CHOICES:
            lbl = QLabel(f"{spd:g}x"); lbl.setProperty("role", "muted")
            lbl.setStyleSheet("font-size:9px;")
            tick_row.addWidget(lbl)
            if spd != SPEED_CHOICES[-1]:
                tick_row.addStretch(1)
        v.addLayout(tick_row)

        v.addStretch(1)

        # controls that must lock while running (PRD 7.2)
        self._lockable = [
            *self._algo_buttons.values(),
            self.btn_single, self.btn_compare,
            self.btn_random, self.btn_shuffle,
            self.size_slider,
        ]

    # -- external control ---------------------------------------------------
    def select_algorithm(self, key: str) -> None:
        if key in self._algo_buttons:
            self._algo_buttons[key].blockSignals(True)
            self._algo_buttons[key].setChecked(True)
            self._algo_buttons[key].blockSignals(False)

    def set_mode(self, mode: str) -> None:
        (self.btn_single if mode == "single" else self.btn_compare).setChecked(True)

    def current_size(self) -> int:
        return self.size_slider.value()

    def current_speed(self) -> float:
        return float(self.speed_combo.currentData())

    def set_speed(self, multiplier: float) -> None:
        if multiplier in SPEED_CHOICES:
            idx = SPEED_CHOICES.index(multiplier)
            self.speed_combo.setCurrentIndex(idx)
            self.speed_slider.blockSignals(True)
            self.speed_slider.setValue(idx)
            self.speed_slider.blockSignals(False)

    def set_size(self, size: int) -> None:
        self.size_slider.blockSignals(True)
        self.size_slider.setValue(size)
        self.size_value.setText(str(size))
        self.size_slider.blockSignals(False)

    def set_running_locked(self, locked: bool) -> None:
        """Disable configuration controls while an algorithm is executing."""
        for w in self._lockable:
            w.setEnabled(not locked)
        self.speed_combo.setEnabled(True)   # speed always adjustable (PRD 7.2)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme

    # -- internal -----------------------------------------------------------
    def _on_size(self, value: int) -> None:
        self.size_value.setText(str(value))
        self.sizeChanged.emit(value)

    def _on_speed_slider(self, idx: int) -> None:
        spd = SPEED_CHOICES[idx]
        self.speed_combo.setCurrentIndex(idx)   # triggers speedChanged
