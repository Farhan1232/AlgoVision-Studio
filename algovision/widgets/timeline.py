"""Timeline Navigation (PRD 7.6).

Two presentations, one behaviour: every entry is an *Operation* the user can
jump to, replay from, or continue execution from.

* ``style="bar"``   - a compact custom-painted horizontal scrubber that scales
  from 10 to several-thousand operations (single paint pass, click/drag to seek).
  Used as the shared timeline beneath Comparison Mode.
* ``style="milestones"`` - a vertical list of checkpoint operations with a
  Completed / In Progress / Pending status, matching the reference "TIMELINE"
  panel.  Clicking a checkpoint seeks to that operation.  Used in the Single
  view's bottom row.  A thin scrubber underneath still allows fine seeking to
  *any* recorded operation (PRD 7.6).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QScrollArea
)

from ..theme.palette import Theme
from ..theme import scale as uiscale


def build_milestones(frames: list, max_items: int = 7) -> list[tuple[int, str]]:
    """Derive a short list of (frame index, label) checkpoints from a run.

    Prefers algorithm *phases* (Heap/Merge), then *passes*, and otherwise
    evenly samples the recorded operations.  Always ends on the final
    "Array Sorted" operation so the panel reads as a progress checklist.
    """
    if not frames:
        return []
    last = len(frames) - 1
    milestones: list[tuple[int, str]] = []

    phases = [(i, f.phase) for i, f in enumerate(frames) if f.phase]
    passes = [(i, f.pass_number) for i, f in enumerate(frames)
              if f.pass_number is not None]

    if phases:
        seen = None
        for i, ph in phases:
            if ph != seen:
                milestones.append((i, ph))
                seen = ph
    elif passes and len({p for _, p in passes}) <= max_items:
        seen = None
        for i, p in passes:
            if p != seen:
                milestones.append((i, f"Pass {p}"))
                seen = p
    else:
        # even sampling of the operation stream
        count = min(max_items - 1, last) if last > 0 else 1
        count = max(1, count)
        for k in range(count):
            idx = round(k * last / count)
            f = frames[idx]
            label = (f.phase or (f.op_type.replace("_", " ").title()
                                 if f.op_type and f.op_type != "info" else "Processing"))
            milestones.append((idx, label))

    # collapse to <= max_items keeping first + evenly spaced
    if len(milestones) > max_items:
        step = len(milestones) / max_items
        milestones = [milestones[int(k * step)] for k in range(max_items)]

    # ensure the final "sorted" checkpoint is present
    if not milestones or milestones[-1][0] != last:
        milestones.append((last, "Array Sorted"))
    return milestones


class _Track(QWidget):
    """Horizontal scrubber - click or drag to seek to any operation."""

    seekRequested = pyqtSignal(int)

    def __init__(self, theme: Theme, parent=None, compact: bool = False):
        super().__init__(parent)
        self.theme = theme
        self._total = 1
        self._current = 0
        self.setMinimumHeight(20 if compact else 40)
        self.setStyleSheet("background: transparent;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def configure(self, total: int, current: int) -> None:
        self._total = max(1, total)
        self._current = current
        self.update()

    def set_current(self, current: int) -> None:
        self._current = current
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.theme
        w, h = self.width(), self.height()
        pad = 8
        track_h = 8
        y = (h - track_h) / 2
        track_w = w - 2 * pad

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(t.border)))
        p.drawRoundedRect(QRectF(pad, y, track_w, track_h), 4, 4)

        frac = self._current / max(1, self._total - 1) if self._total > 1 else 1.0
        filled = track_w * frac
        p.setBrush(QBrush(QColor(t.accent_2)))
        p.drawRoundedRect(QRectF(pad, y, max(track_h, filled), track_h), 4, 4)

        if self._total <= 60:
            p.setPen(QPen(QColor(t.canvas_bg), 1))
            for i in range(self._total):
                x = pad + track_w * (i / max(1, self._total - 1))
                p.drawLine(int(x), int(y), int(x), int(y + track_h))

        px = pad + filled
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(t.accent)))
        p.drawEllipse(QRectF(px - 7, y + track_h / 2 - 7, 14, 14))
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(QRectF(px - 2.5, y + track_h / 2 - 2.5, 5, 5))
        p.end()

    def _pos_to_index(self, x: float) -> int:
        pad = 8
        track_w = self.width() - 2 * pad
        frac = (x - pad) / max(1, track_w)
        frac = min(1.0, max(0.0, frac))
        return round(frac * (self._total - 1))

    def mousePressEvent(self, e):
        self.seekRequested.emit(self._pos_to_index(e.position().x()))

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self.seekRequested.emit(self._pos_to_index(e.position().x()))


class _Milestone(QPushButton):
    """One clickable checkpoint row in the vertical milestone timeline."""

    def __init__(self, ordinal: int, label: str, index: int, theme: Theme, parent=None):
        super().__init__(parent)
        self.index = index
        self.theme = theme
        self.setProperty("variant", "milestone")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._state = "pending"
        self._ordinal = ordinal
        row = QHBoxLayout(self)
        row.setContentsMargins(uiscale.sp(8), uiscale.sp(4), uiscale.sp(8), uiscale.sp(4))
        row.setSpacing(uiscale.sp(9))
        self._row = row

        self.marker = QLabel(str(ordinal))
        self.marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.marker.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(self.marker)

        self.title = QLabel(label)
        self.title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.title.setWordWrap(False)
        row.addWidget(self.title, 1)

        self.status = QLabel("Pending")
        self.status.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(self.status)
        self.set_state("pending")

    def rescale(self) -> None:
        self._row.setContentsMargins(uiscale.sp(8), uiscale.sp(4), uiscale.sp(8), uiscale.sp(4))
        self._row.setSpacing(uiscale.sp(9))
        self.set_state(self._state)

    def set_state(self, state: str) -> None:
        """state in {'completed','current','pending'}."""
        self._state = state
        t = self.theme
        d = uiscale.sp(22)
        r = d // 2
        self.marker.setFixedSize(d, d)
        fs = uiscale.fs(10)
        if state == "completed":
            self.marker.setText("✓")
            self.marker.setStyleSheet(
                f"background:{t.success}; color:#FFFFFF; border-radius:{r}px; font-weight:700;")
            self.title.setStyleSheet(f"color:{t.text_primary};")
            self.status.setText("Completed")
            self.status.setStyleSheet(f"color:{t.text_muted}; font-size:{fs}px;")
        elif state == "current":
            self.marker.setText(str(self._ordinal))
            self.marker.setStyleSheet(
                f"background:{t.accent}; color:#FFFFFF; border-radius:{r}px; font-weight:700;")
            self.title.setStyleSheet(f"color:{t.text_primary}; font-weight:600;")
            self.status.setText("In Progress")
            self.status.setStyleSheet(f"color:{t.accent}; font-size:{fs}px; font-weight:600;")
        else:
            self.marker.setText(str(self._ordinal))
            self.marker.setStyleSheet(
                f"background:transparent; color:{t.text_muted}; "
                f"border:1px solid {t.border}; border-radius:{r}px;")
            self.title.setStyleSheet(f"color:{t.text_secondary};")
            self.status.setText("Pending")
            self.status.setStyleSheet(f"color:{t.text_muted}; font-size:{fs}px;")


class Timeline(QWidget):
    seekRequested = pyqtSignal(int)

    def __init__(self, theme: Theme, parent=None, style: str = "bar"):
        super().__init__(parent)
        self.theme = theme
        self.style_kind = style
        self._total = 1
        self._current = 0
        self._milestones: list[_Milestone] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self._root = lay

        # header (Operation N + detail) -------------------------------------
        header = QHBoxLayout()
        header.setSpacing(8)
        self.op_label = QLabel("Operation 1")
        self.op_label.setStyleSheet(f"color:{theme.accent}; font-weight:700;")
        self.op_detail = QLabel("")
        self.op_detail.setProperty("role", "muted")
        self.op_detail.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        header.addWidget(self.op_label)
        if style == "bar":
            header.addWidget(self.op_detail, 1)   # room for detail beside header
        else:
            header.addStretch(1)                  # narrow column: milestones carry detail

        self.prev_btn = QPushButton("‹")
        self.next_btn = QPushButton("›")
        for b in (self.prev_btn, self.next_btn):
            b.setProperty("variant", "ghost")
            b.setFixedSize(26, 24)
        self.prev_btn.setToolTip("Previous operation")
        self.next_btn.setToolTip("Next operation")
        self.prev_btn.clicked.connect(self._go_prev)
        self.next_btn.clicked.connect(self._go_next)
        header.addWidget(self.prev_btn)
        header.addWidget(self.next_btn)
        lay.addLayout(header)

        # milestone list (vertical style only).  Lives in a scroll area so a
        # short window scrolls the checkpoints internally instead of letting the
        # rows overlap; the header above and the scrubber below stay pinned.
        self._mile_box = QVBoxLayout()
        self._mile_box.setSpacing(2)
        if style == "milestones":
            self._mile_scroll = QScrollArea()
            self._mile_scroll.setWidgetResizable(True)
            self._mile_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            self._mile_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            mbody = QWidget()
            mbody_lay = QVBoxLayout(mbody)
            mbody_lay.setContentsMargins(0, 0, 0, 0)
            mbody_lay.setSpacing(0)
            mbody_lay.addLayout(self._mile_box)
            mbody_lay.addStretch(1)
            self._mile_scroll.setWidget(mbody)
            lay.addWidget(self._mile_scroll, 1)
        else:
            lay.addLayout(self._mile_box)

        # scrubber ----------------------------------------------------------
        self.track = _Track(theme, compact=(style == "milestones"))
        self.track.seekRequested.connect(self.seekRequested)
        lay.addWidget(self.track)

    # -- configuration ------------------------------------------------------
    def configure(self, total: int, current: int) -> None:
        self._total = total
        self._current = current
        self.track.configure(total, current)

    def set_milestones(self, milestones: list[tuple[int, str]]) -> None:
        """milestones: list of (operation index, short label)."""
        for m in self._milestones:
            self._mile_box.removeWidget(m)
            m.setParent(None)
            m.deleteLater()
        self._milestones = []
        if self.style_kind != "milestones":
            return
        for ordinal, (index, label) in enumerate(milestones, start=1):
            m = _Milestone(ordinal, label, index, self.theme)
            m.clicked.connect(lambda _=False, i=index: self.seekRequested.emit(i))
            self._mile_box.addWidget(m)
            self._milestones.append(m)
        self._refresh_milestone_states()

    def _refresh_milestone_states(self) -> None:
        for i, m in enumerate(self._milestones):
            nxt = self._milestones[i + 1].index if i + 1 < len(self._milestones) else self._total
            if self._current >= nxt:
                m.set_state("completed")
            elif self._current >= m.index:
                m.set_state("current")
            else:
                m.set_state("pending")

    # -- live update --------------------------------------------------------
    def update_current(self, index: int, op_number: int, label: str) -> None:
        self._current = index
        self.track.set_current(index)
        self.op_label.setText(f"Operation {op_number}")
        self.op_detail.setText(label or "")
        self._refresh_milestone_states()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.track.theme = theme
        self.op_label.setStyleSheet(f"color:{theme.accent}; font-weight:700;")
        for m in self._milestones:
            m.theme = theme
        self._refresh_milestone_states()
        self.track.update()

    def apply_scale(self, s: float) -> None:
        self.prev_btn.setFixedSize(uiscale.sp(26), uiscale.sp(24))
        self.next_btn.setFixedSize(uiscale.sp(26), uiscale.sp(24))
        self._root.setSpacing(uiscale.sp(6))
        self.track.setMinimumHeight(uiscale.sp(20) if self.style_kind == "milestones"
                                    else uiscale.sp(40))
        for m in self._milestones:
            m.rescale()
        self.track.update()

    def _go_prev(self):
        self.seekRequested.emit(max(0, self._current - 1))

    def _go_next(self):
        self.seekRequested.emit(min(self._total - 1, self._current + 1))
