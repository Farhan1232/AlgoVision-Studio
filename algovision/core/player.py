"""Playback engine.

Wraps a pre-computed list of :class:`Frame` snapshots and exposes VCR-style
controls.  Because navigation is just an index into the frame list, Play,
Pause, Step, Restart, Reset and Timeline seeking all stay perfectly
synchronized and are fully reversible (PRD 7.1 / 7.6).
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .frames import Frame
from ..config import BASE_FRAME_MS, SPEED_DEFAULT

# Simulated execution-time model (deterministic so timeline seeks are stable).
EXEC_MS_PER_OP = 3.5


def frame_exec_seconds(frame: Frame) -> float:
    return round(frame.op_number * EXEC_MS_PER_OP / 1000.0, 3)


class Player(QObject):
    STATUS_RESET = "Reset"
    STATUS_RUNNING = "Running"
    STATUS_PAUSED = "Paused"
    STATUS_COMPLETED = "Completed"

    frameChanged = pyqtSignal(int)          # emits current index
    statusChanged = pyqtSignal(str)         # emits STATUS_*
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frames: list[Frame] = []
        self._index: int = 0
        self._speed: float = SPEED_DEFAULT
        self._status: str = self.STATUS_RESET

        self._timer = QTimer(self)
        self._timer.setSingleShot(False)
        self._timer.timeout.connect(self._advance)

    # -- setup --------------------------------------------------------------
    def load(self, frames: list[Frame]) -> None:
        """Load a fresh trace and reset to the first frame."""
        self._timer.stop()
        self._frames = frames
        self._index = 0
        self._set_status(self.STATUS_RESET)
        self.frameChanged.emit(self._index)

    # -- queries ------------------------------------------------------------
    @property
    def frames(self) -> list[Frame]:
        return self._frames

    @property
    def index(self) -> int:
        return self._index

    @property
    def count(self) -> int:
        return len(self._frames)

    @property
    def status(self) -> str:
        return self._status

    @property
    def speed(self) -> float:
        return self._speed

    def current(self) -> Frame | None:
        if not self._frames:
            return None
        return self._frames[self._index]

    def is_playing(self) -> bool:
        return self._timer.isActive()

    def at_end(self) -> bool:
        return self._index >= len(self._frames) - 1

    # -- controls -----------------------------------------------------------
    def play(self) -> None:
        if not self._frames or self.at_end():
            return
        self._set_status(self.STATUS_RUNNING)
        self._timer.start(self._interval_ms())

    def pause(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
            self._set_status(self.STATUS_PAUSED)

    def toggle(self) -> None:
        if self.is_playing():
            self.pause()
        else:
            self.play()

    def step(self) -> None:
        """Execute exactly one operation, then pause (PRD 7.1)."""
        self._timer.stop()
        if self.at_end():
            self._set_status(self.STATUS_COMPLETED)
            return
        self._index += 1
        self.frameChanged.emit(self._index)
        if self.at_end():
            self._set_status(self.STATUS_COMPLETED)
            self.finished.emit()
        else:
            self._set_status(self.STATUS_PAUSED)

    def reset(self) -> None:
        """Return to the first (unsorted) frame."""
        self._timer.stop()
        self._index = 0
        self._set_status(self.STATUS_RESET)
        self.frameChanged.emit(self._index)

    def restart(self) -> None:
        """Reset then immediately start playing again (PRD 7.1)."""
        self.reset()
        self.play()

    def seek(self, index: int) -> None:
        """Jump to a recorded operation (Timeline navigation)."""
        if not self._frames:
            return
        self._timer.stop()
        self._index = max(0, min(index, len(self._frames) - 1))
        self.frameChanged.emit(self._index)
        if self.at_end():
            self._set_status(self.STATUS_COMPLETED)
        else:
            self._set_status(self.STATUS_PAUSED)

    def set_speed(self, multiplier: float) -> None:
        self._speed = multiplier
        if self._timer.isActive():
            self._timer.start(self._interval_ms())

    # -- internals ----------------------------------------------------------
    def _interval_ms(self) -> int:
        return max(30, int(BASE_FRAME_MS / self._speed))

    def _advance(self) -> None:
        if self.at_end():
            self._timer.stop()
            self._set_status(self.STATUS_COMPLETED)
            self.finished.emit()
            return
        self._index += 1
        self.frameChanged.emit(self._index)
        if self.at_end():
            self._timer.stop()
            self._set_status(self.STATUS_COMPLETED)
            self.finished.emit()

    def _set_status(self, status: str) -> None:
        if status != self._status:
            self._status = status
            self.statusChanged.emit(status)
