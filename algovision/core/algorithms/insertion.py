"""Insertion Sort tracer (PRD 6.3).

Implemented with adjacent shifts so the visualised array is always a valid
permutation of the input (no "held key" hole).  Visually the key slides left
while each larger element shifts one slot to the right to create space, which
is exactly the behaviour the PRD asks the animation to emphasise.
"""

from __future__ import annotations

from .base import Recorder, start_frame, finish_frame
from ...theme.palette import (
    STATE_COMPARING,
    STATE_SWAPPING,
    STATE_SELECTED,
    STATE_SORTED,
)

NAME = "Insertion Sort"


def trace(values: list[int]) -> list:
    rec = Recorder(values)
    n = rec.n
    total_passes = max(1, n - 1)
    start_frame(rec, NAME, total_passes)

    rec.mark_sorted(0)  # first element is a sorted region of size 1
    for i in range(1, n):
        current_pass = i
        key = rec.arr[i]
        rec.emit(
            active={i: STATE_SELECTED},
            op_type="select",
            operation_label=f"Selecting key {key}",
            title=f"Current key element: {key}",
            detail=f"Insertion Sort will insert {key} into the sorted region on its left.",
            code_lines=(1, 2),
            pass_number=current_pass,
            total_passes=total_passes,
        )
        j = i
        while j > 0 and rec.arr[j - 1] > key:
            rec.add_comparison()
            rec.emit(
                active={j - 1: STATE_COMPARING, j: STATE_SELECTED},
                op_type="compare",
                operation_label=f"Comparing {rec.arr[j - 1]} and {key}",
                title=f"Comparing {rec.arr[j - 1]} with key {key}",
                detail=f"Since {rec.arr[j - 1]} > {key}, {rec.arr[j - 1]} shifts right to "
                       f"make space for the key.",
                code_lines=(3,),
                pass_number=current_pass,
                total_passes=total_passes,
            )
            moved = rec.arr[j - 1]
            rec.swap(j - 1, j)   # key slides left, larger element shifts right
            rec.emit(
                active={j - 1: STATE_SWAPPING, j: STATE_SWAPPING},
                op_type="shift",
                operation_label=f"Shifting {moved} right",
                title=f"Shifting {moved} to the right",
                detail=f"{moved} moves one position right; the key {key} slides into index {j - 1}.",
                code_lines=(4, 5),
                pass_number=current_pass,
                total_passes=total_passes,
            )
            j -= 1
        if j > 0:
            # the comparison that stopped the loop (arr[j-1] <= key)
            rec.add_comparison()
        rec.mark_sorted(*range(0, i + 1))
        rec.emit(
            active={j: STATE_SORTED},
            op_type="insert",
            operation_label=f"Inserting {key} into Sorted Region",
            title=f"Inserting {key} into the sorted region",
            detail=f"{key} settles at index {j}; the sorted region now spans indices 0 to {i}.",
            code_lines=(6,),
            pass_number=current_pass,
            total_passes=total_passes,
        )

    finish_frame(rec, NAME)
    return rec.frames
