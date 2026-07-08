"""Bubble Sort tracer (PRD 6.1)."""

from __future__ import annotations

from .base import Recorder, start_frame, finish_frame
from ...theme.palette import STATE_COMPARING, STATE_SWAPPING

NAME = "Bubble Sort"


def trace(values: list[int]) -> list:
    rec = Recorder(values)
    n = rec.n
    total_passes = max(1, n - 1)
    start_frame(rec, NAME, total_passes)

    for i in range(n - 1):
        swapped = False
        current_pass = i + 1
        for j in range(0, n - i - 1):
            a, b = rec.arr[j], rec.arr[j + 1]
            rec.add_comparison()
            rec.emit(
                active={j: STATE_COMPARING, j + 1: STATE_COMPARING},
                op_type="compare",
                operation_label=f"Comparing {a} and {b}",
                title=f"Currently Comparing {a} and {b}",
                detail=(
                    "Bubble Sort compares adjacent elements. "
                    + (f"Since {a} > {b}, the two elements will swap."
                       if a > b else
                       f"Since {a} ≤ {b}, they are already in order.")
                ),
                code_lines=(2, 3),
                pass_number=current_pass,
                total_passes=total_passes,
            )
            if a > b:
                rec.swap(j, j + 1)
                swapped = True
                rec.emit(
                    active={j: STATE_SWAPPING, j + 1: STATE_SWAPPING},
                    op_type="swap",
                    operation_label=f"Swapping {a} and {b}",
                    title=f"Swapping {a} and {b}",
                    detail=f"{a} was greater than {b}, so the two elements are swapped.",
                    code_lines=(4, 5),
                    pass_number=current_pass,
                    total_passes=total_passes,
                )
        # the last element of this pass is now in its final place
        rec.mark_sorted(n - i - 1)
        rec.emit(
            active={},
            op_type="sorted",
            operation_label=f"Position {n - i - 1} sorted",
            title=f"Pass {current_pass} complete",
            detail=f"The largest remaining value {rec.arr[n - i - 1]} has bubbled "
                   f"to its final position.",
            code_lines=(6, 7),
            pass_number=current_pass,
            total_passes=total_passes,
        )
        if not swapped:
            # already sorted - mark everything remaining
            rec.mark_sorted(*range(n - i - 1))
            break

    finish_frame(rec, NAME)
    return rec.frames
