"""Headless correctness tests for the tracing engine.

Run:  .venv/bin/python -m tests.test_core
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from algovision.core import registry  # noqa: E402
from algovision.theme.palette import STATE_COLORS  # noqa: E402


def check_algorithm(info, values):
    frames = info.trace(list(values))
    expected = sorted(values)

    # 1. final frame must equal python's sorted()
    final = frames[-1]
    assert final.values == expected, (
        f"{info.name} did not sort correctly on {values}\n"
        f"  got: {final.values}\n  exp: {expected}"
    )
    # 2. multiset preserved on every frame (no lost/duplicated elements)
    base = sorted(values)
    for k, fr in enumerate(frames):
        assert sorted(fr.values) == base, f"{info.name} frame {k} lost elements"
        assert len(fr.states) == len(values), f"{info.name} frame {k} bad states len"
        for s in fr.states:
            assert s in STATE_COLORS, f"{info.name} unknown state {s!r}"
    # 3. final frame all sorted + completed
    assert final.status == "Completed"
    assert all(s == "sorted" for s in final.states), f"{info.name} not all green at end"
    # 4. counters monotonic non-decreasing
    prev_c = prev_s = 0
    for fr in frames:
        assert fr.comparisons >= prev_c and fr.swaps >= prev_s, \
            f"{info.name} counters went backwards"
        prev_c, prev_s = fr.comparisons, fr.swaps
    return len(frames), final.comparisons, final.swaps


def main():
    rng = random.Random(20260708)
    algos = registry.all_algorithms()
    print(f"{'Algorithm':<16}{'frames':>8}{'comps':>8}{'swaps':>8}   status")
    print("-" * 52)

    datasets = [
        [64, 34, 25, 12, 22, 11, 90, 2, 70, 45],   # reference dataset
        [5, 4, 3, 2, 1],                            # reverse
        [1, 2, 3, 4, 5],                            # already sorted
        [7, 7, 7, 7],                               # all equal
        [42],                                       # single
        [rng.randint(1, 1000) for _ in range(100)],  # max size
    ]

    total_ok = 0
    for info in algos:
        per = []
        for ds in datasets:
            nf, c, s = check_algorithm(info, ds)
            per.append((nf, c, s))
        ref = per[0]
        print(f"{info.name:<16}{ref[0]:>8}{ref[1]:>8}{ref[2]:>8}   OK ({len(datasets)} datasets)")
        total_ok += 1

    print("-" * 52)
    print(f"All {total_ok} algorithms passed on {len(datasets)} datasets each.")


if __name__ == "__main__":
    main()
