"""Algorithm registry: display metadata, pseudocode, educational insights and
the trace function for each of the six supported algorithms (PRD Section 6/8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .algorithms import bubble, selection, insertion, merge, quick, heap
from ..theme.palette import LEGEND_STANDARD, LEGEND_PIVOT, LEGEND_SELECTED, LEGEND_HEAP


@dataclass(frozen=True)
class AlgorithmInfo:
    key: str
    name: str
    short: str                       # nav-panel label
    trace: Callable[[list[int]], list]
    pseudocode: list[str]
    legend: list
    # Algorithm Insights (PRD 8.2)
    overview: str
    working_principle: str
    best: str
    average: str
    worst: str
    space: str
    stable: bool
    in_place: bool
    advantages: str
    limitations: str
    applications: str
    best_used_for: str
    key_idea: str
    uses_heap_tree: bool = False


# --------------------------------------------------------------------------- #
_ALGORITHMS: dict[str, AlgorithmInfo] = {}


def _register(info: AlgorithmInfo) -> None:
    _ALGORITHMS[info.key] = info


_register(AlgorithmInfo(
    key="bubble",
    name="Bubble Sort",
    short="Bubble Sort",
    trace=bubble.trace,
    pseudocode=[
        "for i = 0 to n-2",
        "  swapped = false",
        "  for j = 0 to n-2-i",
        "    if arr[j] > arr[j+1]",
        "      swap(arr[j], arr[j+1])",
        "      swapped = true",
        "  if not swapped",
        "    break",
    ],
    legend=LEGEND_STANDARD,
    overview="Bubble Sort repeatedly steps through the list, compares adjacent "
             "elements and swaps them if they are in the wrong order.",
    working_principle="Adjacent comparisons push the largest unsorted value to "
                      "the end of the array on every pass.",
    best="O(n)", average="O(n²)", worst="O(n²)", space="O(1)",
    stable=True, in_place=True,
    advantages="Simple to understand and implement; detects an already-sorted "
               "array early via the swapped flag.",
    limitations="Very slow on large datasets because of its quadratic time.",
    applications="Teaching, tiny datasets, and nearly-sorted data.",
    best_used_for="Small or nearly-sorted datasets and educational demos.",
    key_idea="Bubble adjacent out-of-order pairs until no swaps remain.",
))

_register(AlgorithmInfo(
    key="selection",
    name="Selection Sort",
    short="Selection Sort",
    trace=selection.trace,
    pseudocode=[
        "for i = 0 to n-2",
        "  minIndex = i",
        "  for j = i+1 to n-1",
        "    if arr[j] < arr[minIndex]",
        "      minIndex = j",
        "  if minIndex != i",
        "    swap(arr[i], arr[minIndex])",
    ],
    legend=LEGEND_SELECTED,
    overview="Selection Sort repeatedly selects the smallest remaining element "
             "and moves it to the front of the unsorted region.",
    working_principle="Scan the unsorted region for the minimum, then swap it "
                      "into its final position.",
    best="O(n²)", average="O(n²)", worst="O(n²)", space="O(1)",
    stable=False, in_place=True,
    advantages="Performs the minimum possible number of swaps (at most n-1).",
    limitations="Always quadratic in comparisons, even on sorted input; not stable.",
    applications="Situations where writes/swaps are expensive.",
    best_used_for="Small datasets where minimising swaps matters.",
    key_idea="Select the minimum each pass and place it in order.",
))

_register(AlgorithmInfo(
    key="insertion",
    name="Insertion Sort",
    short="Insertion Sort",
    trace=insertion.trace,
    pseudocode=[
        "for i = 1 to n-1",
        "  key = arr[i]",
        "  j = i - 1",
        "  while j >= 0 and arr[j] > key",
        "    arr[j+1] = arr[j]",
        "    j = j - 1",
        "  arr[j+1] = key",
    ],
    legend=LEGEND_SELECTED,
    overview="Insertion Sort builds the sorted array one element at a time by "
             "inserting each new value into its correct place.",
    working_principle="Shift larger elements of the sorted region to the right "
                      "to open a slot, then drop the key in.",
    best="O(n)", average="O(n²)", worst="O(n²)", space="O(1)",
    stable=True, in_place=True,
    advantages="Fast on small or nearly-sorted data; stable; sorts online.",
    limitations="Quadratic time on large, randomly ordered datasets.",
    applications="Small arrays and as the base case of hybrid sorts.",
    best_used_for="Small or nearly-sorted datasets and streaming input.",
    key_idea="Insert each element into the growing sorted prefix.",
))

_register(AlgorithmInfo(
    key="merge",
    name="Merge Sort",
    short="Merge Sort",
    trace=merge.trace,
    pseudocode=[
        "mergeSort(arr, left, right):",
        "  if left >= right: return",
        "  mid = (left + right) / 2",
        "  mergeSort(arr, left, mid)",
        "  mergeSort(arr, mid+1, right)",
        "  merge(arr, left, mid, right)",
        "merge: compare fronts of both halves",
        "  copy the smaller element back",
        "  copy any remaining elements",
    ],
    legend=LEGEND_STANDARD,
    overview="Merge Sort is a divide-and-conquer algorithm that divides the "
             "array into halves, sorts them, and merges them.",
    working_principle="Recursively split until single elements remain, then "
                      "merge sorted runs back together.",
    best="O(n log n)", average="O(n log n)", worst="O(n log n)", space="O(n)",
    stable=True, in_place=False,
    advantages="Guaranteed O(n log n); stable; predictable performance.",
    limitations="Requires O(n) extra memory for merging.",
    applications="Large datasets, external sorting, linked lists.",
    best_used_for="Large datasets or when consistent performance is required.",
    key_idea="Divide the array, sort the halves, then merge them in order.",
))

_register(AlgorithmInfo(
    key="quick",
    name="Quick Sort",
    short="Quick Sort",
    trace=quick.trace,
    pseudocode=[
        "quickSort(arr, low, high):",
        "  if low >= high: return",
        "  pivot = arr[high]",
        "  i = low - 1",
        "  for j = low to high-1",
        "    if arr[j] < pivot",
        "      i = i + 1",
        "      swap(arr[i], arr[j])",
        "  swap(arr[i+1], arr[high])",
        "  quickSort(arr, low, i)",
        "  quickSort(arr, i+2, high)",
    ],
    legend=LEGEND_PIVOT,
    overview="Quick Sort partitions the array around a pivot so smaller values "
             "go left and larger values go right, then recurses.",
    working_principle="Choose a pivot, partition around it, then sort each "
                      "partition recursively.",
    best="O(n log n)", average="O(n log n)", worst="O(n²)", space="O(log n)",
    stable=False, in_place=True,
    advantages="Very fast in practice; sorts in place with low overhead.",
    limitations="Worst-case O(n²) on poor pivots; not stable.",
    applications="General-purpose in-memory sorting; standard library sorts.",
    best_used_for="General-purpose fast in-place sorting.",
    key_idea="Partition around a pivot, then recurse on each side.",
))

_register(AlgorithmInfo(
    key="heap",
    name="Heap Sort",
    short="Heap Sort",
    trace=heap.trace,
    pseudocode=[
        "heapSort(arr):",
        "  n = arr.length",
        "  buildMaxHeap(arr, n)",
        "  for i = n-1 downto 1",
        "    swap(arr[0], arr[i])",
        "    heapSize = heapSize - 1",
        "    heapify(arr, 0, heapSize)",
    ],
    legend=LEGEND_HEAP,
    overview="Heap Sort builds a max heap and repeatedly extracts the maximum.",
    working_principle="Build a max heap, then swap the root to the end and "
                      "re-heapify the shrinking heap.",
    best="O(n log n)", average="O(n log n)", worst="O(n log n)", space="O(1)",
    stable=False, in_place=True,
    advantages="Guaranteed O(n log n) with O(1) extra space.",
    limitations="Poor cache locality; not stable; slower constant factors than Quick Sort.",
    applications="Priority queues and systems needing worst-case guarantees.",
    best_used_for="Large datasets where consistent performance is required.",
    key_idea="Build a max heap, then repeatedly swap the root with the last "
             "element and heapify.",
    uses_heap_tree=True,
))


# --------------------------------------------------------------------------- #
def get(key: str) -> AlgorithmInfo:
    return _ALGORITHMS[key]


def all_algorithms() -> list[AlgorithmInfo]:
    from ..config import ALGO_ORDER
    return [_ALGORITHMS[k] for k in ALGO_ORDER]


def keys() -> list[str]:
    from ..config import ALGO_ORDER
    return list(ALGO_ORDER)
