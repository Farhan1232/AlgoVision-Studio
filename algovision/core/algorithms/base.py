"""Shared helpers for the sorting algorithm tracers.

Each algorithm module exposes ``trace(values) -> list[Frame]``.  The first
frame is always the untouched input (everything ``default``) and the last frame
is the fully sorted array (everything ``sorted``) with a "Sorting Completed"
label, so the visualization, statistics and explanation panels all agree on the
final state.
"""

from __future__ import annotations

from ..frames import Recorder, Frame


def start_frame(rec: Recorder, algo_name: str, total_passes: int | None = None) -> None:
    """Emit the initial 'ready' frame (array untouched)."""
    rec.emit(
        op_type="start",
        operation_label="Ready",
        title="Ready to sort",
        detail=f"{algo_name} will process {rec.n} elements. Press Play to begin.",
        code_lines=(0,),
        pass_number=0 if total_passes else None,
        total_passes=total_passes,
        status="Running",
    )


def finish_frame(rec: Recorder, algo_name: str) -> None:
    """Mark every element sorted and emit the completion frame."""
    rec.mark_sorted(*range(rec.n))
    rec.emit(
        op_type="done",
        operation_label="Sorting Completed",
        title="Sorting Completed",
        detail=f"{algo_name} finished. The array is now fully sorted.",
        code_lines=(),
        status="Completed",
    )


def fmt_list(values: list[int]) -> str:
    return "[" + ", ".join(str(v) for v in values) + "]"


__all__ = ["Recorder", "Frame", "start_frame", "finish_frame", "fmt_list"]
