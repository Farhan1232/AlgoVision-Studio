"""Frame model + Recorder.

An algorithm run is captured as an ordered list of :class:`Frame` snapshots.
Because every frame is a *complete* description of the world at one operation,
the playback engine and Timeline can jump to any frame and restore the exact
state of every panel (PRD 7.6 Timeline Navigation, 5.5 Synchronization).

The :class:`Recorder` is the little helper each algorithm implementation uses.
The algorithm mutates ``recorder.arr`` and calls ``recorder.emit(...)`` at every
meaningful operation; the recorder snapshots the array + counters into a Frame.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..theme.palette import (
    STATE_DEFAULT,
    STATE_SORTED,
)


@dataclass
class Frame:
    """Immutable snapshot of one recorded operation."""

    # --- array state -------------------------------------------------------
    values: list[int]                       # value at each position
    states: list[str]                       # visual-language state per position

    # --- running statistics -----------------------------------------------
    comparisons: int = 0
    swaps: int = 0
    op_number: int = 0                      # 1-based operation index
    extra_stats: dict = field(default_factory=dict)  # e.g. {"Heapify Calls": 6}

    # --- textual / educational content ------------------------------------
    op_type: str = "info"                   # compare/swap/insert/merge/...
    operation_label: str = ""               # "Comparing 34 and 25"
    explanation_title: str = ""             # "Currently Comparing 34 and 25"
    explanation_detail: str = ""            # educational sentence

    # --- pseudocode sync ---------------------------------------------------
    code_lines: tuple[int, ...] = ()        # 0-based line indices to highlight

    # --- pass / phase ------------------------------------------------------
    pass_number: Optional[int] = None
    total_passes: Optional[int] = None
    phase: Optional[str] = None             # heap/merge phase label

    # --- structure hints ---------------------------------------------------
    groups: Optional[list[tuple[int, int]]] = None   # merge subarray ranges
    heap_size: Optional[int] = None                  # heap boundary for tree view
    status: str = "Running"                          # Running/Paused/Completed/Reset

    def copy_values(self) -> list[int]:
        return list(self.values)


class Recorder:
    """Builds a list of Frames while an algorithm executes."""

    def __init__(self, values: list[int]):
        self.arr: list[int] = list(values)
        self.n: int = len(values)
        self.frames: list[Frame] = []
        self.comparisons: int = 0
        self.swaps: int = 0
        self.sorted_positions: set[int] = set()
        self._extra: dict = {}

    # -- statistics helpers -------------------------------------------------
    def add_comparison(self, count: int = 1) -> None:
        self.comparisons += count

    def add_swap(self, count: int = 1) -> None:
        self.swaps += count

    def bump_extra(self, key: str, amount: int = 1) -> None:
        self._extra[key] = self._extra.get(key, 0) + amount

    def set_extra(self, key: str, value) -> None:
        self._extra[key] = value

    def mark_sorted(self, *indices: int) -> None:
        for i in indices:
            self.sorted_positions.add(i)

    # -- the core snapshot --------------------------------------------------
    def emit(
        self,
        *,
        active: Optional[dict[int, str]] = None,
        op_type: str = "info",
        operation_label: str = "",
        title: str = "",
        detail: str = "",
        code_lines: tuple[int, ...] = (),
        pass_number: Optional[int] = None,
        total_passes: Optional[int] = None,
        phase: Optional[str] = None,
        groups: Optional[list[tuple[int, int]]] = None,
        heap_size: Optional[int] = None,
        status: str = "Running",
    ) -> None:
        """Record one Frame.

        ``active`` maps position -> state colour for the elements that are
        currently highlighted.  Everything else is ``sorted`` (if the position
        is in ``sorted_positions``) or ``default``.
        """
        states = []
        for i in range(self.n):
            if active and i in active:
                states.append(active[i])
            elif i in self.sorted_positions:
                states.append(STATE_SORTED)
            else:
                states.append(STATE_DEFAULT)

        frame = Frame(
            values=list(self.arr),
            states=states,
            comparisons=self.comparisons,
            swaps=self.swaps,
            op_number=len(self.frames) + 1,
            extra_stats=dict(self._extra),
            op_type=op_type,
            operation_label=operation_label,
            explanation_title=title,
            explanation_detail=detail,
            code_lines=tuple(code_lines),
            pass_number=pass_number,
            total_passes=total_passes,
            phase=phase,
            groups=groups,
            heap_size=heap_size,
            status=status,
        )
        self.frames.append(frame)

    # -- convenience --------------------------------------------------------
    def swap(self, i: int, j: int) -> None:
        self.arr[i], self.arr[j] = self.arr[j], self.arr[i]
        self.add_swap()
