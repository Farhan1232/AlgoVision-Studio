"""Presentation Mode (PRD 7.8).

A distraction-free fullscreen surface that mirrors the *live* single-algorithm
player, so entering/leaving it never interrupts the running algorithm.  It keeps
the playback controls required for classroom use and adds keyboard shortcuts.

The layout mirrors ``presentation-mode.png``: a top bar (brand · PRESENTATION
MODE pill · Press [Esc] to exit), a big visualization with a centred operation
title, a full-width live explanation, a right rail of Live Statistics /
Algorithm Info / Dataset Info cards, and a bottom bar of key-cap keyboard
shortcuts plus the animation-speed stepper.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout,
    QScrollArea, QSizePolicy, QProgressBar
)

from ..theme.palette import Theme
from ..theme import scale as uiscale
from ..core.player import frame_exec_seconds
from ..widgets import ArrayView, HeapTreeView, ExplanationPanel
from ..widgets.common import card, section_label
from ..config import APP_NAME, APP_TAGLINE
from ..resources import assets_dir

ASSETS = assets_dir()

# small leading icon per Live-Statistics row (matches the reference)
_STAT_ICONS = {
    "Comparisons": "📊",
    "Swaps / Moves": "🔀",
    "Execution Time": "⏱️",
    "Current Operation": "🔄",
    "Progress": "📈",
    "Steps Executed": "🔢",
}


class PresentationView(QWidget):
    exitRequested = pyqtSignal()
    controlTriggered = pyqtSignal(str)
    speedDelta = pyqtSignal(int)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.source = None
        self._stat_texts: list[tuple[QLabel, QLabel]] = []
        self._stat_sections: list[QLabel] = []
        self._keycaps: list[QLabel] = []
        self._progress = None
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

        # "Press [Esc] to exit" with Esc rendered as a key-cap chip
        esc_row = QHBoxLayout(); esc_row.setSpacing(7)
        self._esc_pre = QLabel("Press"); self._esc_pre.setProperty("role", "muted")
        self.esc_cap = QLabel("Esc")
        self._keycaps.append(self.esc_cap)
        self._esc_post = QLabel("to exit"); self._esc_post.setProperty("role", "muted")
        esc_row.addWidget(self._esc_pre); esc_row.addWidget(self.esc_cap)
        esc_row.addWidget(self._esc_post)
        top.addLayout(esc_row)
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

        # header row: algorithm name / step line (left) + centred operation title
        # framed by decorative rules (right), exactly like the reference.
        head = QHBoxLayout()
        name_col = QVBoxLayout(); name_col.setSpacing(2)
        self.algo_name = QLabel("Algorithm")
        self.stepline = QLabel("")
        self.stepline.setStyleSheet(f"color:{theme.accent_2}; font-weight:600;")
        name_col.addWidget(self.algo_name)
        name_col.addWidget(self.stepline)
        head.addLayout(name_col)

        op_group = QHBoxLayout(); op_group.setSpacing(12)
        self._rule_l = QFrame(); self._rule_l.setFixedHeight(2)
        self._rule_r = QFrame(); self._rule_r.setFixedHeight(2)
        self.op_title = QLabel("")
        self.op_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        op_group.addWidget(self._rule_l, 1)
        op_group.addWidget(self.op_title)
        op_group.addWidget(self._rule_r, 1)
        head.addLayout(op_group, 1)
        left.addLayout(head)

        self.array = ArrayView(theme)
        self.array.setMinimumHeight(260)
        self.heap = HeapTreeView(theme)
        viz = QHBoxLayout()
        viz.addWidget(self.array, 3)
        viz.addWidget(self.heap, 2)
        left.addLayout(viz, 5)
        self.explanation = ExplanationPanel(theme)
        self.explanation.setMinimumHeight(96)
        self.explanation.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        left.addWidget(self.explanation, 0)
        # The visualization column is the star of the classroom view, so it
        # takes the majority of the width.
        body.addLayout(left, 7)

        # right: live stats + info, inside a scroll area so the panels adapt to
        # any laptop height (they scroll instead of overflowing on short screens).
        # The three cards are spread across the full column height so the panel
        # feels substantial on a projector rather than clustered at the top.
        self.stats_card, self._stat_labels = self._stat_block(
            "Live Statistics",
            ["Comparisons", "Swaps / Moves", "Execution Time", "Current Operation",
             "Progress", "Steps Executed"],
            section_icon="📈", row_icons=True, with_progress=True)
        self.info_card, self._info_labels = self._stat_block(
            "Algorithm Info",
            ["Time Complexity", "Space Complexity", "Stable", "In-Place"],
            section_icon="🔀")
        self.data_card, self._data_labels = self._stat_block(
            "Dataset Info", ["Type", "Size", "Range"], section_icon="🗂️")

        side_body = QWidget()
        self.side = QVBoxLayout(side_body)
        self.side.setContentsMargins(0, 0, 6, 0)
        self.side.setSpacing(16)
        self.side.addWidget(self.stats_card)
        self.side.addStretch(1)
        self.side.addWidget(self.info_card)
        self.side.addStretch(1)
        self.side.addWidget(self.data_card)
        self.side.addStretch(1)

        side_scroll = QScrollArea()
        side_scroll.setWidgetResizable(True)
        side_scroll.setFrameShape(QFrame.Shape.NoFrame)
        side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        side_scroll.setWidget(side_body)
        side_scroll.setMinimumWidth(375)
        side_scroll.setStyleSheet("background: transparent;")
        body.addWidget(side_scroll, 2)
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
        self.op_title.setStyleSheet(
            f"color:{t.accent_2}; font-size:{uiscale.fs(17)}px; font-weight:700;")
        for r in (self._rule_l, self._rule_r):
            r.setStyleSheet(f"background:{t.accent_2}; border:none; max-height:2px; "
                            "border-radius:1px;")
        self.speed_val.setFixedWidth(uiscale.sp(48))
        for b in self._speed_btns:
            b.setFixedWidth(uiscale.sp(34))
        # key-cap chips (Esc + all bottom-bar shortcuts) styled like keycaps
        cap_css = (f"border:1px solid {t.border}; border-radius:{uiscale.sp(6)}px; "
                   f"padding:{uiscale.sp(3)}px {uiscale.sp(10)}px; background:{t.card_bg}; "
                   f"color:{t.text_primary}; font-weight:700; font-size:{uiscale.fs(12)}px;")
        for cap in self._keycaps:
            cap.setStyleSheet(cap_css)
        # classroom-readable statistics: larger key/value fonts than the app default
        for kl, vl in self._stat_texts:
            kl.setStyleSheet(f"color:{t.text_secondary}; font-size:{uiscale.fs(14)}px;")
            vl.setStyleSheet(
                f"color:{t.text_primary}; font-weight:700; font-size:{uiscale.fs(15)}px;")
        for sec in self._stat_sections:
            sec.setStyleSheet(
                f"color:{t.accent}; font-size:{uiscale.fs(12)}px; "
                f"font-weight:700; letter-spacing:1px;")

    def apply_scale(self, s: float) -> None:
        self._restyle()

    def _stat_block(self, title, keys, section_icon="", row_icons=False,
                    with_progress=False):
        c = card()
        v = QVBoxLayout(c)
        v.setContentsMargins(18, 15, 18, 15)
        v.setSpacing(11)
        sec = section_label((section_icon + "  " + title) if section_icon else title)
        v.addWidget(sec)
        labels = {}
        for k in keys:
            row = QHBoxLayout(); row.setSpacing(9)
            if row_icons:
                ic = QLabel(_STAT_ICONS.get(k, "•"))
                ic.setFixedWidth(20)
                row.addWidget(ic)
            kl = QLabel(k); kl.setProperty("role", "muted")
            vl = QLabel("—"); vl.setProperty("role", "value")
            vl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            # keys are kept compact; the "Current Operation" value is shown in a
            # concise form (see _render) so no value ever overflows the rail.
            kl.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
            row.addWidget(kl); row.addStretch(1); row.addWidget(vl)
            v.addLayout(row)
            labels[k] = vl
            self._stat_texts.append((kl, vl))
            # the reference shows a thin progress bar directly under "Progress"
            if with_progress and k == "Progress":
                self._progress = QProgressBar()
                self._progress.setRange(0, 100); self._progress.setValue(0)
                self._progress.setTextVisible(False)
                self._progress.setFixedHeight(8)
                v.addWidget(self._progress)
        self._stat_sections.append(sec)
        return c, labels

    def _key_chip(self, key: str, label: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(7)
        cap = QLabel(key)
        cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._keycaps.append(cap)
        lab = QLabel(label); lab.setProperty("role", "muted")
        h.addWidget(cap); h.addWidget(lab)
        return w

    def _controls(self):
        c = card()
        h = QHBoxLayout(c)
        h.setContentsMargins(16, 10, 16, 10)
        h.setSpacing(12)

        sc_lbl = QLabel("KEYBOARD SHORTCUTS")
        sc_lbl.setProperty("role", "section")
        h.addWidget(sc_lbl)
        shortcuts = [
            ("Space", "Play / Pause"), ("→", "Next Step"), ("←", "Previous Step"),
            ("F", "Fast Forward"), ("S", "Slow Motion"), ("R", "Restart"),
            ("Esc", "Exit"),
        ]
        for key, label in shortcuts:
            h.addWidget(self._key_chip(key, label))

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
        self.op_title.setText(frame.operation_label or "")
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
        # concise current-operation (matches the reference's short "Merging"
        # style and never overflows the narrow rail); full text on hover.
        if frame.phase:
            cur_short = frame.phase
        elif frame.op_type and frame.op_type != "info":
            cur_short = frame.op_type.replace("_", " ").title()
        else:
            cur_short = frame.operation_label or "—"
        if len(cur_short) > 20:
            cur_short = cur_short[:19] + "…"
        sl["Current Operation"].setText(cur_short)
        sl["Current Operation"].setToolTip(frame.operation_label or "")
        sl["Progress"].setText(f"{pct}%")
        sl["Steps Executed"].setText(f"{frame.op_number} / {s.player.count}")
        if self._progress is not None:
            self._progress.setValue(pct)

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


class _CompareColumn(QWidget):
    """One algorithm's classroom column inside the comparison presentation.

    Mirrors a single ``_Mini`` side of Comparison Mode: a big header with the
    algorithm name / step line / status badge, a large Numbered Block View, a
    live explanation, a Live-Statistics strip and a compact Algorithm-Info line.
    """

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.info = None
        self._stat_texts: list[tuple[QLabel, QLabel]] = []
        self._sections: list[QLabel] = []

        c = card()
        v = QVBoxLayout(c)
        v.setContentsMargins(18, 14, 18, 14)
        v.setSpacing(9)

        head = QHBoxLayout()
        name_col = QVBoxLayout(); name_col.setSpacing(2)
        self.name = QLabel("Algorithm")
        self.stepline = QLabel("")
        name_col.addWidget(self.name)
        name_col.addWidget(self.stepline)
        head.addLayout(name_col)
        head.addStretch(1)
        self.badge = QLabel("Reset"); self.badge.setProperty("role", "badge-reset")
        head.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignTop)
        v.addLayout(head)

        self.op_title = QLabel("")
        self.op_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.op_title)

        self.array = ArrayView(theme)
        self.array.setMinimumHeight(210)
        v.addWidget(self.array, 1)

        self.explanation = ExplanationPanel(theme)
        self.explanation.setMinimumHeight(78)
        self.explanation.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        v.addWidget(self.explanation)

        # Live Statistics strip (per algorithm)
        stats = card()
        sv = QVBoxLayout(stats)
        sv.setContentsMargins(16, 12, 16, 12)
        sv.setSpacing(9)
        self._stats_sec = section_label("📈  Live Statistics")
        self._sections.append(self._stats_sec)
        sv.addWidget(self._stats_sec)
        self._stat_labels = {}
        for k in ("Comparisons", "Swaps / Moves", "Execution Time",
                  "Current Operation", "Progress", "Steps Executed"):
            row = QHBoxLayout(); row.setSpacing(9)
            ic = QLabel(_STAT_ICONS.get(k, "•")); ic.setFixedWidth(20)
            row.addWidget(ic)
            kl = QLabel(k); kl.setProperty("role", "muted")
            vl = QLabel("—"); vl.setProperty("role", "value")
            vl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            kl.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
            row.addWidget(kl); row.addStretch(1); row.addWidget(vl)
            sv.addLayout(row)
            self._stat_labels[k] = vl
            self._stat_texts.append((kl, vl))
            if k == "Progress":
                self.progress = QProgressBar()
                self.progress.setRange(0, 100); self.progress.setValue(0)
                self.progress.setTextVisible(False)
                self.progress.setFixedHeight(8)
                sv.addWidget(self.progress)
        v.addWidget(stats)

        # Algorithm Info strip (per algorithm)
        info_c = card()
        iv = QVBoxLayout(info_c)
        iv.setContentsMargins(16, 12, 16, 12)
        iv.setSpacing(9)
        self._info_sec = section_label("🔀  Algorithm Info")
        self._sections.append(self._info_sec)
        iv.addWidget(self._info_sec)
        self._info_labels = {}
        for k in ("Time Complexity", "Space Complexity", "Stable", "In-Place"):
            row = QHBoxLayout(); row.setSpacing(9)
            kl = QLabel(k); kl.setProperty("role", "muted")
            vl = QLabel("—"); vl.setProperty("role", "value")
            vl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(kl); row.addStretch(1); row.addWidget(vl)
            iv.addLayout(row)
            self._info_labels[k] = vl
            self._stat_texts.append((kl, vl))
        v.addWidget(info_c)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(c)

    def set_info(self, info) -> None:
        self.info = info
        self.name.setText(info.name)
        il = self._info_labels
        il["Time Complexity"].setText(info.average)
        il["Space Complexity"].setText(info.space)
        il["Stable"].setText("Yes" if info.stable else "No")
        il["In-Place"].setText("Yes" if info.in_place else "No")

    def render_frame(self, frame, total: int, done: bool, winner: bool) -> None:
        if frame is None:
            return
        self.array.render(frame)
        self.op_title.setText(("🏆  " if winner else "") + (frame.operation_label or ""))
        self.stepline.setText(f"Step {frame.op_number} / {total}")
        self.explanation.update_from(frame)

        pct = int(round(100 * frame.op_number / max(1, total)))
        sl = self._stat_labels
        sl["Comparisons"].setText(str(frame.comparisons))
        sl["Swaps / Moves"].setText(str(frame.swaps))
        sl["Execution Time"].setText(f"{frame_exec_seconds(frame):.3f} s")
        if frame.phase:
            cur_short = frame.phase
        elif frame.op_type and frame.op_type != "info":
            cur_short = frame.op_type.replace("_", " ").title()
        else:
            cur_short = frame.operation_label or "—"
        if len(cur_short) > 20:
            cur_short = cur_short[:19] + "…"
        sl["Current Operation"].setText(cur_short)
        sl["Current Operation"].setToolTip(frame.operation_label or "")
        sl["Progress"].setText(f"{pct}%")
        sl["Steps Executed"].setText(f"{frame.op_number} / {total}")
        self.progress.setValue(pct)

        status = "Completed" if done else ("Running" if frame.op_number > 0 else "Reset")
        self.badge.setText(status)
        self.badge.setProperty("role", f"badge-{status.lower()}")
        self.badge.style().unpolish(self.badge); self.badge.style().polish(self.badge)

    def restyle(self) -> None:
        t = self.theme
        winner = "🏆" in self.op_title.text()
        self.name.setStyleSheet(
            f"font-size:{uiscale.fs(24)}px; font-weight:800; color:{t.text_primary};")
        self.stepline.setStyleSheet(f"color:{t.accent_2}; font-weight:600;")
        self.op_title.setStyleSheet(
            f"color:{t.success if winner else t.accent_2}; "
            f"font-size:{uiscale.fs(16)}px; font-weight:700;")
        for kl, vl in self._stat_texts:
            kl.setStyleSheet(f"color:{t.text_secondary}; font-size:{uiscale.fs(14)}px;")
            vl.setStyleSheet(
                f"color:{t.text_primary}; font-weight:700; font-size:{uiscale.fs(15)}px;")
        for sec in self._sections:
            sec.setStyleSheet(
                f"color:{t.accent}; font-size:{uiscale.fs(12)}px; "
                f"font-weight:700; letter-spacing:1px;")

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.restyle()
        for w in (self.array, self.explanation):
            w.set_theme(theme)


class ComparisonPresentationView(QWidget):
    """Fullscreen classroom surface that mirrors the *live* Comparison Mode.

    Reflects the active Comparison state: two algorithms running on the same
    dataset under the shared clock, each with its own Live Statistics and
    Algorithm Info, plus a shared winner banner - the comparison analogue of
    :class:`PresentationView`.
    """

    exitRequested = pyqtSignal()
    controlTriggered = pyqtSignal(str)
    speedDelta = pyqtSignal(int)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.source = None
        self._keycaps: list[QLabel] = []
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 18, 28, 16)
        root.setSpacing(10)

        # top bar: brand · pill · Esc  (mirrors PresentationView)
        top = QHBoxLayout()
        brand = QHBoxLayout(); brand.setSpacing(10)
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

        self.pill = QLabel("🖥️  COMPARISON · PRESENTATION MODE")
        self.pill.setProperty("variant", "present-pill")
        top.addWidget(self.pill)
        top.addStretch(1)

        esc_row = QHBoxLayout(); esc_row.setSpacing(7)
        self._esc_pre = QLabel("Press"); self._esc_pre.setProperty("role", "muted")
        self.esc_cap = QLabel("Esc"); self._keycaps.append(self.esc_cap)
        self._esc_post = QLabel("to exit"); self._esc_post.setProperty("role", "muted")
        esc_row.addWidget(self._esc_pre); esc_row.addWidget(self.esc_cap)
        esc_row.addWidget(self._esc_post)
        top.addLayout(esc_row)
        root.addLayout(top)

        tagline = QLabel("Two algorithms · same dataset · compared side by side.")
        tagline.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        tagline.setProperty("role", "muted")
        root.addWidget(tagline)

        # two algorithm columns
        body = QHBoxLayout(); body.setSpacing(18)
        self.left = _CompareColumn(theme)
        self.right = _CompareColumn(theme)
        body.addWidget(self.left, 1)
        body.addWidget(self.right, 1)
        root.addLayout(body, 1)

        # shared winner / summary banner
        self.summary = QLabel("Run the comparison to see which algorithm wins.")
        self.summary.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.summary.setProperty("role", "muted")
        root.addWidget(self.summary)

        root.addWidget(self._controls())
        self._restyle()

    def _key_chip(self, key: str, label: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0); h.setSpacing(7)
        cap = QLabel(key); cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._keycaps.append(cap)
        lab = QLabel(label); lab.setProperty("role", "muted")
        h.addWidget(cap); h.addWidget(lab)
        return w

    def _controls(self):
        c = card()
        h = QHBoxLayout(c)
        h.setContentsMargins(16, 10, 16, 10); h.setSpacing(12)
        sc_lbl = QLabel("KEYBOARD SHORTCUTS"); sc_lbl.setProperty("role", "section")
        h.addWidget(sc_lbl)
        for key, label in [
            ("Space", "Play / Pause"), ("→", "Next Step"), ("←", "Previous Step"),
            ("F", "Fast Forward"), ("S", "Slow Motion"), ("R", "Restart"),
            ("Esc", "Exit"),
        ]:
            h.addWidget(self._key_chip(key, label))
        h.addStretch(1)
        spd_lbl = QLabel("ANIMATION SPEED"); spd_lbl.setProperty("role", "section")
        h.addWidget(spd_lbl)
        minus = QPushButton("–")
        self.speed_val = QLabel("1.0x"); self.speed_val.setProperty("role", "value")
        self.speed_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plus = QPushButton("+")
        self._speed_btns = (minus, plus)
        for b in (minus, plus):
            b.setProperty("variant", "ghost")
        minus.clicked.connect(lambda: self.speedDelta.emit(-1))
        plus.clicked.connect(lambda: self.speedDelta.emit(1))
        h.addWidget(minus); h.addWidget(self.speed_val); h.addWidget(plus)
        return c

    def _restyle(self) -> None:
        t = self.theme
        self._brand_title.setStyleSheet(
            f"font-size:{uiscale.fs(18)}px; font-weight:800; color:{t.text_primary};")
        self._brand_sub.setStyleSheet(
            f"color:{t.text_muted}; font-size:{uiscale.fs(10)}px; letter-spacing:1px;")
        self.pill.setStyleSheet(
            f"color:{t.accent_2}; font-size:{uiscale.fs(15)}px; font-weight:800; "
            f"border:1px solid {t.border}; border-radius:{uiscale.sp(10)}px; "
            f"padding:{uiscale.sp(8)}px {uiscale.sp(22)}px; background:{t.card_bg};")
        self.summary.setStyleSheet(
            f"color:{t.text_primary}; font-size:{uiscale.fs(15)}px; font-weight:700;")
        self.speed_val.setFixedWidth(uiscale.sp(48))
        for b in self._speed_btns:
            b.setFixedWidth(uiscale.sp(34))
        cap_css = (f"border:1px solid {t.border}; border-radius:{uiscale.sp(6)}px; "
                   f"padding:{uiscale.sp(3)}px {uiscale.sp(10)}px; background:{t.card_bg}; "
                   f"color:{t.text_primary}; font-weight:700; font-size:{uiscale.fs(12)}px;")
        for cap in self._keycaps:
            cap.setStyleSheet(cap_css)
        self.left.restyle()
        self.right.restyle()

    def apply_scale(self, s: float) -> None:
        self._restyle()
        for col in (self.left, self.right):
            for w in (col.array, col.explanation):
                if hasattr(w, "apply_scale"):
                    w.apply_scale(s)

    # -- binding to the live compare view -----------------------------------
    def bind(self, source) -> None:
        """Mirror an existing CompareView's shared clock + both algorithms."""
        self.source = source
        self.left.set_info(source.left.info)
        self.right.set_info(source.right.info)
        source.rendered.connect(self._render)
        pos, total = source.position()
        self._render(pos, total)

    def _render(self, pos: int, total: int) -> None:
        s = self.source
        if s is None:
            return
        # (re)sync the algorithm names/info in case the pair changed
        if s.left.info is not None:
            self.left.set_info(s.left.info)
        if s.right.info is not None:
            self.right.set_info(s.right.info)

        fa = fb = None
        a_done = b_done = False
        if s.left.frames:
            ia = min(pos, len(s.left.frames) - 1)
            fa = s.left.frames[ia]
            a_done = pos >= len(s.left.frames) - 1
        if s.right.frames:
            ib = min(pos, len(s.right.frames) - 1)
            fb = s.right.frames[ib]
            b_done = pos >= len(s.right.frames) - 1

        both_done = bool(s.left.frames and s.right.frames and a_done and b_done)
        win_a = win_b = False
        if both_done and fa is not None and fb is not None:
            ta, tb = frame_exec_seconds(fa), frame_exec_seconds(fb)
            a_ops = fa.comparisons + fa.swaps
            b_ops = fb.comparisons + fb.swaps
            if (ta, a_ops) < (tb, b_ops):
                win_a = True
            elif (tb, b_ops) < (ta, a_ops):
                win_b = True

        self.left.render_frame(fa, len(s.left.frames) or 1, a_done, win_a)
        self.right.render_frame(fb, len(s.right.frames) or 1, b_done, win_b)

        if both_done:
            if win_a:
                self.summary.setText(f"🏆  {s.left.info.name} finished more efficiently")
            elif win_b:
                self.summary.setText(f"🏆  {s.right.info.name} finished more efficiently")
            else:
                self.summary.setText("Both algorithms performed equally.")
        else:
            self.summary.setText(
                f"{s.left.info.name} vs {s.right.info.name}  ·  same dataset, shared clock")

        # keep winner colouring in sync with the just-updated titles
        self.left.restyle(); self.right.restyle()
        self.speed_val.setText(f"{s._speed:g}x")

    # -- keyboard -----------------------------------------------------------
    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key.Key_Escape:
            self.exitRequested.emit()
        elif k == Qt.Key.Key_Space:
            self.controlTriggered.emit("toggle")
        elif k == Qt.Key.Key_Right:
            self.controlTriggered.emit("step")
        elif k == Qt.Key.Key_Left:
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
        self.left.set_theme(theme)
        self.right.set_theme(theme)
