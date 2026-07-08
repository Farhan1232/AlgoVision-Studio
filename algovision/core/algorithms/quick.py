"""Quick Sort tracer (PRD 6.5) - Lomuto partition with last element as pivot."""

from __future__ import annotations

from .base import Recorder, start_frame, finish_frame
from ...theme.palette import (
    STATE_COMPARING,
    STATE_SWAPPING,
    STATE_PIVOT,
    STATE_SELECTED,
    STATE_SORTED as STATE_SORTED_HL,
)

NAME = "Quick Sort"


def trace(values: list[int]) -> list:
    rec = Recorder(values)
    n = rec.n
    start_frame(rec, NAME)

    def quick_sort(low: int, high: int) -> None:
        if low > high:
            return
        if low == high:
            rec.mark_sorted(low)
            return
        p = partition(low, high)
        rec.mark_sorted(p)
        rec.emit(
            active={p: STATE_SORTED_HL},
            op_type="partition",
            operation_label=f"Pivot {rec.arr[p]} placed at {p}",
            title=f"Pivot {rec.arr[p]} is in its final position",
            detail=f"Everything left of index {p} is smaller and everything right is larger.",
            code_lines=(8,),
        )
        quick_sort(low, p - 1)
        quick_sort(p + 1, high)

    def partition(low: int, high: int) -> int:
        pivot = rec.arr[high]
        rec.emit(
            active={high: STATE_PIVOT},
            op_type="partition",
            operation_label=f"Partitioning Around Pivot {pivot}",
            title=f"Choosing pivot {pivot}",
            detail=f"Quick Sort partitions indices {low}–{high} around the pivot {pivot}.",
            code_lines=(2, 3),
        )
        i = low - 1
        for j in range(low, high):
            a = rec.arr[j]
            rec.add_comparison()
            rec.emit(
                active={high: STATE_PIVOT, j: STATE_COMPARING,
                        **({i: STATE_SELECTED} if i >= low else {})},
                op_type="compare",
                operation_label=f"Comparing {a} with pivot {pivot}",
                title=f"Comparing {a} with pivot {pivot}",
                detail=(f"{a} < {pivot}, so it belongs in the left partition."
                        if a < pivot else
                        f"{a} ≥ {pivot}, so it stays in the right partition."),
                code_lines=(4, 5),
            )
            if a < pivot:
                i += 1
                if i != j:
                    x, y = rec.arr[i], rec.arr[j]
                    rec.swap(i, j)
                    rec.emit(
                        active={high: STATE_PIVOT, i: STATE_SWAPPING, j: STATE_SWAPPING},
                        op_type="swap",
                        operation_label=f"Swapping {x} and {y}",
                        title=f"Swapping {x} and {y}",
                        detail=f"{y} is smaller than the pivot, so it moves into the left partition.",
                        code_lines=(6, 7),
                    )
        # move pivot into place
        x, y = rec.arr[i + 1], rec.arr[high]
        if i + 1 != high:
            rec.swap(i + 1, high)
            rec.emit(
                active={i + 1: STATE_SWAPPING, high: STATE_SWAPPING},
                op_type="swap",
                operation_label=f"Placing pivot {pivot}",
                title=f"Placing pivot {pivot} between the partitions",
                detail=f"The pivot {pivot} swaps into index {i + 1}, its final sorted position.",
                code_lines=(8,),
            )
        return i + 1

    quick_sort(0, n - 1)
    finish_frame(rec, NAME)
    return rec.frames
