"""Selection Sort tracer (PRD 6.2)."""

from __future__ import annotations

from .base import Recorder, start_frame, finish_frame
from ...theme.palette import STATE_COMPARING, STATE_SWAPPING, STATE_SELECTED

NAME = "Selection Sort"


def trace(values: list[int]) -> list:
    rec = Recorder(values)
    n = rec.n
    total_passes = max(1, n - 1)
    start_frame(rec, NAME, total_passes)

    for i in range(n - 1):
        current_pass = i + 1
        min_idx = i
        rec.emit(
            active={i: STATE_SELECTED},
            op_type="select",
            operation_label="Selecting Minimum Element",
            title=f"Scanning for the minimum from index {i}",
            detail=f"Selection Sort looks for the smallest value in the "
                   f"unsorted region starting at index {i}.",
            code_lines=(1,),
            pass_number=current_pass,
            total_passes=total_passes,
        )
        for j in range(i + 1, n):
            a, b = rec.arr[j], rec.arr[min_idx]
            rec.add_comparison()
            rec.emit(
                active={min_idx: STATE_SELECTED, j: STATE_COMPARING},
                op_type="compare",
                operation_label=f"Comparing {a} and {b}",
                title=f"Comparing {a} with current minimum {b}",
                detail=(f"{a} < {b}, so index {j} becomes the new minimum."
                        if a < b else
                        f"{a} ≥ {b}, so the current minimum stays at index {min_idx}."),
                code_lines=(2, 3),
                pass_number=current_pass,
                total_passes=total_passes,
            )
            if a < b:
                min_idx = j
                rec.emit(
                    active={min_idx: STATE_SELECTED},
                    op_type="select",
                    operation_label=f"New minimum {rec.arr[min_idx]}",
                    title=f"New minimum found: {rec.arr[min_idx]}",
                    detail=f"Index {min_idx} now holds the smallest value seen so far.",
                    code_lines=(3, 4),
                    pass_number=current_pass,
                    total_passes=total_passes,
                )
        if min_idx != i:
            a, b = rec.arr[i], rec.arr[min_idx]
            rec.swap(i, min_idx)
            rec.emit(
                active={i: STATE_SWAPPING, min_idx: STATE_SWAPPING},
                op_type="swap",
                operation_label=f"Swapping {a} and {b}",
                title=f"Swapping {a} and {b}",
                detail=f"The minimum {b} moves into position {i}, its final place.",
                code_lines=(5, 6),
                pass_number=current_pass,
                total_passes=total_passes,
            )
        rec.mark_sorted(i)
        rec.emit(
            active={},
            op_type="sorted",
            operation_label=f"Position {i} sorted",
            title=f"Position {i} finalised",
            detail=f"{rec.arr[i]} is now in its correct sorted position.",
            code_lines=(),
            pass_number=current_pass,
            total_passes=total_passes,
        )

    finish_frame(rec, NAME)
    return rec.frames
