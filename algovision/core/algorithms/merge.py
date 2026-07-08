"""Merge Sort tracer (PRD 6.4).

Shows the divide phase (subarray groups) and the merge phase.  During a merge
the displayed range always equals ``merged-output`` followed by the
not-yet-consumed elements of the two halves, so the visualised array stays a
valid permutation of the input at every frame (no transient duplicates).
"""

from __future__ import annotations

from .base import Recorder, start_frame, finish_frame
from ...theme.palette import STATE_COMPARING, STATE_SWAPPING, STATE_SORTED

NAME = "Merge Sort"


def trace(values: list[int]) -> list:
    rec = Recorder(values)
    n = rec.n
    start_frame(rec, NAME)

    def merge_sort(left: int, right: int) -> None:
        if left >= right:
            return
        mid = (left + right) // 2
        rec.emit(
            active={i: STATE_COMPARING for i in range(left, right + 1)},
            op_type="partition",
            operation_label=f"Dividing indices {left}–{right}",
            title="Dividing the array",
            detail=f"Merge Sort splits indices {left}–{right} into "
                   f"[{left}–{mid}] and [{mid + 1}–{right}].",
            code_lines=(2, 3, 4),
            groups=[(left, mid), (mid + 1, right)],
        )
        merge_sort(left, mid)
        merge_sort(mid + 1, right)
        merge(left, mid, right)

    def merge(left: int, mid: int, right: int) -> None:
        left_part = rec.arr[left:mid + 1]
        right_part = rec.arr[mid + 1:right + 1]
        li = ri = 0
        merged: list[int] = []
        groups = [(left, mid), (mid + 1, right)]

        def render() -> None:
            rest = merged + left_part[li:] + right_part[ri:]
            for idx, val in enumerate(rest):
                rec.arr[left + idx] = val

        while li < len(left_part) and ri < len(right_part):
            base = left + len(merged)
            lpos = base
            rpos = base + (len(left_part) - li)
            a, b = left_part[li], right_part[ri]
            rec.add_comparison()
            rec.emit(
                active={lpos: STATE_COMPARING, rpos: STATE_COMPARING},
                op_type="merge",
                operation_label="Merging Left and Right Subarrays",
                title=f"Merging: comparing {a} and {b}",
                detail=(f"{a} ≤ {b}, so {a} is placed next."
                        if a <= b else
                        f"{b} < {a}, so {b} is placed next."),
                code_lines=(6, 7),
                groups=groups,
            )
            if a <= b:
                merged.append(a)
                li += 1
            else:
                merged.append(b)
                ri += 1
            rec.add_swap()
            render()
            wpos = left + len(merged) - 1
            rec.emit(
                active={wpos: STATE_SWAPPING},
                op_type="merge",
                operation_label=f"Placing {rec.arr[wpos]} at index {wpos}",
                title=f"Placing {rec.arr[wpos]} into position {wpos}",
                detail=f"The smaller front element {rec.arr[wpos]} is written into the merged run.",
                code_lines=(8,),
                groups=groups,
            )

        # drain whichever half remains
        while li < len(left_part):
            merged.append(left_part[li]); li += 1
            rec.add_swap(); render()
            wpos = left + len(merged) - 1
            rec.emit(
                active={wpos: STATE_SWAPPING},
                op_type="merge",
                operation_label=f"Copying remaining {rec.arr[wpos]}",
                title=f"Copying leftover {rec.arr[wpos]} from the left half",
                detail="Remaining elements of the left half are copied in order.",
                code_lines=(9,),
                groups=groups,
            )
        while ri < len(right_part):
            merged.append(right_part[ri]); ri += 1
            rec.add_swap(); render()
            wpos = left + len(merged) - 1
            rec.emit(
                active={wpos: STATE_SWAPPING},
                op_type="merge",
                operation_label=f"Copying remaining {rec.arr[wpos]}",
                title=f"Copying leftover {rec.arr[wpos]} from the right half",
                detail="Remaining elements of the right half are copied in order.",
                code_lines=(9,),
                groups=groups,
            )

        rec.emit(
            active={idx: STATE_SORTED for idx in range(left, right + 1)},
            op_type="merge",
            operation_label=f"Merged indices {left}–{right}",
            title=f"Subarray {left}–{right} merged",
            detail=f"Indices {left}–{right} are now sorted as a single run.",
            code_lines=(5,),
            groups=[(left, right)],
        )

    merge_sort(0, n - 1)
    finish_frame(rec, NAME)
    return rec.frames
