"""Presentation Mode (PRD 7.8).

A distraction-free fullscreen surface that mirrors the *live* single-algorithm
player, so entering/leaving it never interrupts the running algorithm.  It keeps
the playback controls required for classroom use and adds keyboard shortcuts.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout,
    QScrollArea
)

from ..theme.palette import Theme
from ..theme import scale as uiscale
from ..core.player import frame_exec_seconds
from ..widgets import ArrayView, HeapTreeView, ExplanationPanel
from ..widgets.common import card, section_label
from ..config import APP_NAME, APP_TAGLINE
from ..resources import assets_dir

ASSETS = assets_dir()


class PresentationView(QWidget):
    exitRequested = pyqtSignal()
    controlTriggered = pyqtSignal(str)
    speedDelta = pyqtSignal(int)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.source = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 18, 28, 16)
        root.setSpacing(10)

        # top bar: logo + title (left) · PRESENTATION MODE pill (center) · Esc
        top = QHBoxLayout()
        brand = QHBoxLayout()
        brand.setSpacing(10)
        logo = ASSETS / "logo.png"
        if logo.exists():
            lg = QLabel()
            lg.setPixmap(QPixmap(str(logo)).scaledToHeight(
                36, Qt.TransformationMode.SmoothTransformation))
            brand.addWidget(lg)
        brand_col = QVBoxLayout(); brand_col.setSpacing(0)
        self._brand_title = QLabel(APP_NAME)
        self._brand_sub = QLabel(APP_TAGLINE); self._brand_sub.setProperty("role", "muted")
        brand_col.addWidget(self._brand_title); brand_col.addWidget(self._brand_sub)
        brand.addLayout(brand_col)
        top.addLayout(brand)
        top.addStretch(1)

        self.pill = QLabel("🖥️  PRESENTATION MODE")
        self.pill.setProperty("variant", "present-pill")
        top.addWidget(self.pill)
        top.addStretch(1)

        self.esc_hint = QLabel("Press  Esc  to exit")
        self.esc_hint.setProperty("role", "muted")
        top.addWidget(self.esc_hint)
        root.addLayout(top)

        tagline = QLabel("Focus on learning. Engage your audience.")
        tagline.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        tagline.setProperty("role", "muted")
        root.addWidget(tagline)

        body = QHBoxLayout()
        body.setSpacing(18)

        # left: big visualization
        left = QVBoxLayout()
        left.setSpacing(8)
        head = QHBoxLayout()
        name_col = QVBoxLayout(); name_col.setSpacing(2)
        self.algo_name = QLabel("Algorithm")
        self.stepline = QLabel("")
        self.stepline.setStyleSheet(f"color:{theme.accent_2}; font-weight:600;")
        name_col.addWidget(self.algo_name)
        name_col.addWidget(self.stepline)
        head.addLayout(name_col)
        head.addStretch(1)
        self.subtitle = QLabel("")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        head.addWidget(self.subtitle, 1)
        left.addLayout(head)

        self.array = ArrayView(theme)
        self.heap = HeapTreeView(theme)
        viz = QHBoxLayout()
        viz.addWidget(self.array, 3)
        viz.addWidget(self.heap, 2)
        left.addLayout(viz, 1)
        self.explanation = ExplanationPanel(theme)
        left.addWidget(self.explanation)
        body.addLayout(left, 3)

        # right: live stats + info, inside a scroll area so the panels adapt to
        # any laptop height (they scroll instead of overflowing on short screens)
        self.stats_card, self._stat_labels = self._stat_block(
            "Live Statistics",
            ["Comparisons", "Swaps / Moves", "Execution Time", "Current Operation",
             "Progress", "Steps Executed"])
        self.info_card, self._info_labels = self._stat_block(
            "Algorithm Info",
            ["Time Complexity", "Space Complexity", "Stable", "In-Place"])
        self.data_card, self._data_labels = self._stat_block(
            "Dataset Info", ["Type", "Size", "Range"])

        side_body = QWidget()
        self.side = QVBoxLayout(side_body)
        self.side.setContentsMargins(0, 0, 6, 0)
        self.side.setSpacing(12)
        self.side.addWidget(self.stats_card)
        self.side.addWidget(self.info_card)
        self.side.addWidget(self.data_card)
        self.side.addStretch(1)

        side_scroll = QScrollArea()
        side_scroll.setWidgetResizable(True)
        side_scroll.setFrameShape(QFrame.Shape.NoFrame)
        side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        side_scroll.setWidget(side_body)
        side_scroll.setMinimumWidth(300)
        side_scroll.setStyleSheet("background: transparent;")
        body.addWidget(side_scroll, 1)
        root.addLayout(body, 1)

        # bottom controls
        root.addWidget(self._controls())
        self._restyle()

    def _restyle(self) -> None:
        """(Re)apply all scale-dependent inline styles for the current theme."""
        t = self.theme
        self._brand_title.setStyleSheet(
            f"font-size:{uiscale.fs(18)}px; font-weight:800; color:{t.text_primary};")
        self._brand_sub.setStyleSheet(
            f"color:{t.text_muted}; font-size:{uiscale.fs(10)}px; letter-spacing:1px;")
        self.pill.setStyleSheet(
            f"color:{t.accent_2}; font-size:{uiscale.fs(15)}px; font-weight:800; "
            f"border:1px solid {t.border}; border-radius:{uiscale.sp(10)}px; "
            f"padding:{uiscale.sp(8)}px {uiscale.sp(22)}px; background:{t.card_bg};")
        self.algo_name.setStyleSheet(
            f"font-size:{uiscale.fs(28)}px; font-weight:800; color:{t.text_primary};")
        self.stepline.setStyleSheet(f"color:{t.accent_2}; font-weight:600;")
        self.subtitle.setStyleSheet(
            f"color:{t.accent_2}; font-size:{uiscale.fs(16)}px; font-weight:700;")
        self.speed_val.setFixedWidth(uiscale.sp(48))
        for b in self._speed_btns:
            b.setFixedWidth(uiscale.sp(34))

    def apply_scale(self, s: float) -> None:
        self._restyle()

    def _stat_block(self, title, keys):
        c = card()
        v = QVBoxLayout(c)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        v.addWidget(section_label(title))
        labels = {}
        for k in keys:
            row = QHBoxLayout()
            kl = QLabel(k); kl.setProperty("role", "muted")
            vl = QLabel("—"); vl.setProperty("role", "value")
            vl.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(kl); row.addStretch(1); row.addWidget(vl)
            v.addLayout(row)
            labels[k] = vl
        return c, labels

    def _controls(self):
        c = card()
        h = QHBoxLayout(c)
        h.setContentsMargins(16, 8, 16, 8)
        h.setSpacing(10)

        specs = [("▶ Play", "play"), ("⏸ Pause", "pause"), ("⏭ Step", "step"),
                 ("↻ Restart", "restart"), ("⭯ Reset", "reset")]
        for label, key in specs:
            b = QPushButton(label)
            b.setProperty("variant", "ghost")
            b.clicked.connect(lambda _, k=key: self.controlTriggered.emit(k))
            h.addWidget(b)

        h.addSpacing(18)
        sc_lbl = QLabel("KEYBOARD SHORTCUTS")
        sc_lbl.setProperty("role", "section")
        h.addWidget(sc_lbl)
        hint = QLabel("Space Play/Pause   →/← Step   S/F Speed   R Restart   Esc Exit")
        hint.setProperty("role", "muted")
        h.addWidget(hint)

        h.addStretch(1)
        spd_lbl = QLabel("ANIMATION SPEED")
        spd_lbl.setProperty("role", "section")
        h.addWidget(spd_lbl)
        minus = QPushButton("–")
        self.speed_val = QLabel("1.0x")
        self.speed_val.setProperty("role", "value")
        self.speed_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plus = QPushButton("+")
        self._speed_btns = (minus, plus)
        for b in (minus, plus):
            b.setProperty("variant", "ghost")
        minus.clicked.connect(lambda: self.speedDelta.emit(-1))
        plus.clicked.connect(lambda: self.speedDelta.emit(1))
        h.addWidget(minus); h.addWidget(self.speed_val); h.addWidget(plus)
        return c

    # -- binding to the live single-view player -----------------------------
    def bind(self, source) -> None:
        """Mirror an existing SingleView's player + info."""
        self.source = source
        source.player.frameChanged.connect(self._render)
        self._render(source.player.index)

    def _render(self, _index=0) -> None:
        s = self.source
        if s is None or s.info is None:
            return
        frame = s.player.current()
        if frame is None:
            return
        info = s.info
        self.algo_name.setText(info.name)
        self.subtitle.setText(frame.operation_label)
        self.stepline.setText(
            f"Step {frame.op_number} / {s.player.count}" +
            (f"  ·  Pass {frame.pass_number} / {frame.total_passes}"
             if frame.pass_number and frame.total_passes else ""))
        self.array.render(frame)
        self.heap.setVisible(info.uses_heap_tree)
        if info.uses_heap_tree:
            self.heap.render(frame)
        self.explanation.update_from(frame)

        pct = int(round(100 * frame.op_number / max(1, s.player.count)))
        sl = self._stat_labels
        sl["Comparisons"].setText(str(frame.comparisons))
        sl["Swaps / Moves"].setText(str(frame.swaps))
        sl["Execution Time"].setText(f"{frame_exec_seconds(frame):.3f} s")
        sl["Current Operation"].setText(frame.operation_label or "—")
        sl["Progress"].setText(f"{pct}%")
        sl["Steps Executed"].setText(f"{frame.op_number} / {s.player.count}")

        il = self._info_labels
        il["Time Complexity"].setText(info.average)
        il["Space Complexity"].setText(info.space)
        il["Stable"].setText("Yes" if info.stable else "No")
        il["In-Place"].setText("Yes" if info.in_place else "No")

        dl = self._data_labels
        dl["Type"].setText(s.dataset_val.text())
        dl["Size"].setText(str(len(s.original)))
        dl["Range"].setText("1 – 1000")

        self.speed_val.setText(f"{s.player.speed:g}x")

    # -- keyboard -----------------------------------------------------------
    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key.Key_Escape:
            self.exitRequested.emit()
        elif k == Qt.Key.Key_Space:
            self.controlTriggered.emit("toggle")
        elif k in (Qt.Key.Key_Right,):
            self.controlTriggered.emit("step")
        elif k in (Qt.Key.Key_Left,):
            self.controlTriggered.emit("prev")
        elif k == Qt.Key.Key_R:
            self.controlTriggered.emit("restart")
        elif k == Qt.Key.Key_F:
            self.speedDelta.emit(1)
        elif k == Qt.Key.Key_S:
            self.speedDelta.emit(-1)
        else:
            super().keyPressEvent(e)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._restyle()
        for w in (self.array, self.heap, self.explanation):
            w.set_theme(theme)
