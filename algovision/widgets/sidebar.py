"""Navigation + Control panel (PRD Section 3 Navigation Panel, 7.1, 7.2, 7.4)."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QButtonGroup,
    QPushButton, QSlider, QComboBox, QScrollArea, QSizePolicy, QLineEdit
)

from ..theme.palette import Theme
from ..theme import scale as uiscale
from ..core import registry, dataset
from ..config import (
    ARRAY_SIZE_MIN, ARRAY_SIZE_MAX, ARRAY_SIZE_DEFAULT,
    SPEED_CHOICES, SPEED_LABELS, SPEED_DEFAULT, SHORTCUTS,
    VALUE_MIN, VALUE_MAX,
)
from .common import section_label


def _control_button(icon: str, label: str, key: str = "") -> QPushButton:
    btn = QPushButton()
    btn.setProperty("variant", "control")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    hb = QHBoxLayout(btn)
    hb.setContentsMargins(10, 4, 10, 4)
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
    customArraySubmitted = pyqtSignal(list)   # validated list[int]

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # No vertical scrolling: the sidebar auto-scales its own text/spacing so
        # every control fits on one screen (see apply_scale).
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("Sidebar")
        self.setFixedWidth(238)

        body = QWidget()
        body.setObjectName("Sidebar")
        self.setWidget(body)
        self._body = body
        v = QVBoxLayout(body)
        self._v = v
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(4)

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
        v.addSpacing(5)

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
        v.addSpacing(5)

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
        v.addSpacing(5)

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
        self._tick_labels = []
        tick_row = QHBoxLayout()
        for spd in SPEED_CHOICES:
            lbl = QLabel(f"{spd:g}x"); lbl.setProperty("role", "muted")
            lbl.setStyleSheet("font-size:9px;")
            self._tick_labels.append(lbl)
            tick_row.addWidget(lbl)
            if spd != SPEED_CHOICES[-1]:
                tick_row.addStretch(1)
        v.addLayout(tick_row)

        # --- CUSTOM ARRAY (in-sidebar, available in every mode, PRD 7.3) ---
        v.addSpacing(5)
        v.addWidget(section_label("Custom Array"))
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("e.g. 64, 34, 25, 12, 22")
        self.custom_input.returnPressed.connect(self._on_apply_custom)
        v.addWidget(self.custom_input)

        self.custom_msg = QLabel("")
        self.custom_msg.setWordWrap(True)
        self.custom_msg.setStyleSheet("font-size:10px;")
        self.custom_msg.setVisible(False)
        v.addWidget(self.custom_msg)

        cust_row = QHBoxLayout()
        cust_row.setSpacing(6)
        self.btn_apply = QPushButton("Apply Array")
        self.btn_apply.setProperty("variant", "primary")
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setProperty("variant", "ghost")
        self.btn_apply.clicked.connect(self._on_apply_custom)
        self.btn_clear.clicked.connect(self._on_clear_custom)
        cust_row.addWidget(self.btn_apply, 1)
        cust_row.addWidget(self.btn_clear)
        v.addLayout(cust_row)

        v.addStretch(1)

        # controls that must lock while running (PRD 7.2)
        self._lockable = [
            *self._algo_buttons.values(),
            self.btn_single, self.btn_compare,
            self.btn_random, self.btn_shuffle,
            self.size_slider,
            self.custom_input, self.btn_apply, self.btn_clear,
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

    def set_dataset_text(self, values: list[int]) -> None:
        """Reflect the current dataset in the custom-array input field."""
        self.custom_input.blockSignals(True)
        self.custom_input.setText(", ".join(map(str, values)))
        self.custom_input.blockSignals(False)
        self._clear_custom_error()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme

    def apply_scale(self, s: float, avail: int | None = None) -> None:
        """Scale the sidebar to fit its available height WITHOUT scrolling.

        Everything (fonts, paddings, spacing, width) shrinks together until all
        controls fit on one screen.  Uses a calibrated linear model of the
        content height, ``content(x) ~= A*x + B``, to solve for the largest
        scale that fits, capped by the global scale.
        """
        if avail is None:
            avail = self.height()
        # Calibrated for the current set of sidebar controls:
        # content(x) ~= A*x + B (px).
        A, B = 434.0, 270.0
        s_fit = (avail - B) / A if avail > B else 0.42
        s_eff = max(0.42, min(s, s_fit * 0.98))
        self._style_at(s_eff)

    def _style_at(self, s: float) -> None:
        """Apply a sidebar-scoped stylesheet + scaled spacing at scale ``s``."""
        def f(v):
            return max(7, round(v * s))

        def p(v):
            return max(1, round(v * s))

        self.setFixedWidth(max(150, round(238 * s)))
        self._v.setContentsMargins(p(14), p(10), p(14), p(10))
        self._v.setSpacing(p(3))
        t = self.theme
        self.setStyleSheet(f"""
            #Sidebar {{ background-color:{t.sidebar_bg}; border-right:1px solid {t.border}; }}
            QLabel {{ font-size:{f(12)}px; }}
            QLabel[role="section"] {{ font-size:{f(10)}px; }}
            QPushButton[variant="nav"], QPushButton[variant="mode"],
            QPushButton[variant="control"] {{
                padding:{p(4)}px {p(9)}px; font-size:{f(12)}px; border-radius:{p(7)}px;
            }}
            QPushButton[variant="control"] QLabel {{ font-size:{f(12)}px; }}
            QPushButton[variant="primary"], QPushButton[variant="ghost"] {{
                padding:{p(4)}px {p(8)}px; font-size:{f(11)}px; border-radius:{p(6)}px;
            }}
            QComboBox, QLineEdit {{ padding:{p(3)}px {p(8)}px; font-size:{f(11)}px; }}
        """)
        for lbl in getattr(self, "_tick_labels", []):
            lbl.setStyleSheet(f"font-size:{f(9)}px;")
        col = self.theme.danger if self.custom_msg.text() else self.theme.text_secondary
        self.custom_msg.setStyleSheet(f"font-size:{f(9)}px; color:{col};")

    # -- custom array -------------------------------------------------------
    def _on_apply_custom(self) -> None:
        try:
            values = dataset.parse_custom_input(self.custom_input.text())
        except dataset.ValidationError as exc:
            self._show_custom_error(str(exc))
            return
        self._clear_custom_error()
        self.customArraySubmitted.emit(values)

    def _on_clear_custom(self) -> None:
        # Clears the input field only; the active dataset is preserved so the
        # visualization never drops below the minimum supported size.
        self.custom_input.clear()
        self._clear_custom_error()

    def _show_custom_error(self, text: str) -> None:
        self.custom_msg.setText(f"⚠  {text}")
        self.custom_msg.setStyleSheet(f"font-size:10px; color:{self.theme.danger};")
        self.custom_msg.setVisible(True)
        self.custom_input.setProperty("state", "error")
        self.custom_input.style().unpolish(self.custom_input)
        self.custom_input.style().polish(self.custom_input)

    def _clear_custom_error(self) -> None:
        self.custom_msg.setVisible(False)
        self.custom_msg.setText("")
        self.custom_input.setProperty("state", "")
        self.custom_input.style().unpolish(self.custom_input)
        self.custom_input.style().polish(self.custom_input)

    # -- internal -----------------------------------------------------------
    def _on_size(self, value: int) -> None:
        self.size_value.setText(str(value))
        self.sizeChanged.emit(value)

    def _on_speed_slider(self, idx: int) -> None:
        spd = SPEED_CHOICES[idx]
        self.speed_combo.setCurrentIndex(idx)   # triggers speedChanged
