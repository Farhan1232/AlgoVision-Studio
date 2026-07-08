"""Heap Sort tracer (PRD 6.6).

Emits ``heap_size`` and ``phase`` on every frame so the Binary Heap Tree View
can render exactly the nodes that are still part of the heap, and highlight the
root / comparisons / swaps in sync with the Numbered Block View.
"""

from __future__ import annotations

from .base import Recorder, start_frame, finish_frame
from ...theme.palette import (
    STATE_COMPARING,
    STATE_SWAPPING,
    STATE_SELECTED,   # root / max (purple)
)

NAME = "Heap Sort"

PHASE_BUILD = "Build Max Heap"
PHASE_EXTRACT = "Extract Max"


def trace(values: list[int]) -> list:
    rec = Recorder(values)
    n = rec.n
    rec.set_extra("Heapify Calls", 0)
    start_frame(rec, NAME)

    heap_size = n

    def heapify(size: int, root: int, phase: str) -> None:
        rec.bump_extra("Heapify Calls")
        largest = root
        left = 2 * root + 1
        right = 2 * root + 2

        active = {root: STATE_SELECTED}
        child_txt = []
        if left < size:
            active[left] = STATE_COMPARING
            child_txt.append(str(rec.arr[left]))
        if right < size:
            active[right] = STATE_COMPARING
            child_txt.append(str(rec.arr[right]))
        rec.add_comparison(len(child_txt))
        rec.emit(
            active=active,
            op_type="heapify",
            operation_label=f"Heapifying Node {root}",
            title=f"Heapify at index {root} (value {rec.arr[root]}).",
            detail=(f"Comparing with children {' and '.join(child_txt)}. "
                    "Ensuring the subtree satisfies the max-heap property."
                    if child_txt else
                    f"Node {root} is a leaf; nothing to compare."),
            code_lines=(6,) if phase == PHASE_EXTRACT else (2,),
            phase=phase,
            heap_size=size,
        )

        if left < size and rec.arr[left] > rec.arr[largest]:
            largest = left
        if right < size and rec.arr[right] > rec.arr[largest]:
            largest = right

        if largest != root:
            a, b = rec.arr[root], rec.arr[largest]
            rec.swap(root, largest)
            rec.emit(
                active={root: STATE_SWAPPING, largest: STATE_SWAPPING},
                op_type="swap",
                operation_label=f"Swapping {a} and {b}",
                title=f"Swapping {a} and {b}",
                detail=f"Child {b} is larger than parent {a}, so they swap to restore the heap.",
                code_lines=(4,) if phase == PHASE_EXTRACT else (2,),
                phase=phase,
                heap_size=size,
            )
            heapify(size, largest, phase)

    # --- Phase 1: build max heap ------------------------------------------
    rec.emit(
        op_type="phase",
        operation_label="Build Max Heap",
        title="Building the max heap",
        detail="Heap Sort first rearranges the array into a max heap so the "
               "largest value sits at the root.",
        code_lines=(2,),
        phase=PHASE_BUILD,
        heap_size=heap_size,
    )
    for i in range(n // 2 - 1, -1, -1):
        heapify(heap_size, i, PHASE_BUILD)

    # --- Phase 2: repeatedly extract the maximum --------------------------
    rec.emit(
        active={0: STATE_SELECTED},
        op_type="phase",
        operation_label="Extract Max",
        title="Extracting the maximum",
        detail="The root (largest value) is swapped to the end, the heap shrinks, "
               "and the root is heapified again.",
        code_lines=(3,),
        phase=PHASE_EXTRACT,
        heap_size=heap_size,
    )
    for i in range(n - 1, 0, -1):
        a, b = rec.arr[0], rec.arr[i]
        rec.emit(
            active={0: STATE_SELECTED, i: STATE_COMPARING},
            op_type="heapify",
            operation_label=f"Extract Max ({a})",
            title=f"Root {a} is the current maximum",
            detail=f"Swap the root {a} with the last heap element {b} to lock {a} in place.",
            code_lines=(3, 4),
            phase=PHASE_EXTRACT,
            heap_size=heap_size,
        )
        rec.swap(0, i)
        heap_size -= 1
        rec.emit(
            active={0: STATE_SWAPPING},
            op_type="swap",
            operation_label=f"Swapping {a} and {b}",
            title=f"{a} moves to its final position (index {i})",
            detail=f"The heap now covers indices 0–{heap_size - 1}; index {i} leaves the heap.",
            code_lines=(4, 5),
            phase=PHASE_EXTRACT,
            heap_size=heap_size,
        )
        if heap_size > 1:
            heapify(heap_size, 0, PHASE_EXTRACT)

    finish_frame(rec, NAME)
    return rec.frames
