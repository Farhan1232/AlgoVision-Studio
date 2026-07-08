"""CSV export of the execution summary (PRD 7.10)."""

from __future__ import annotations

import csv
from pathlib import Path

from ..core.registry import AlgorithmInfo
from ..core.frames import Frame
from ..core.player import frame_exec_seconds


def default_filename(info: AlgorithmInfo) -> str:
    name = info.name.replace(" ", "")
    return f"{name}_ExecutionReport.csv"


def build_rows(info: AlgorithmInfo, original: list[int], final_frame: Frame) -> list[list[str]]:
    return [
        ["Field", "Value"],
        ["Algorithm", info.name],
        ["Dataset Size", str(len(original))],
        ["Original Dataset", " ".join(map(str, original))],
        ["Sorted Dataset", " ".join(map(str, final_frame.values))],
        ["Total Comparisons", str(final_frame.comparisons)],
        ["Total Swaps / Movements", str(final_frame.swaps)],
        ["Execution Time (s)", f"{frame_exec_seconds(final_frame):.3f}"],
        ["Best Case", info.best],
        ["Average Case", info.average],
        ["Worst Case", info.worst],
        ["Space Complexity", info.space],
        ["Stable", "Yes" if info.stable else "No"],
        ["In-place", "Yes" if info.in_place else "No"],
        ["Performance Summary",
         f"{info.name} completed {final_frame.comparisons} comparisons and "
         f"{final_frame.swaps} movements in {frame_exec_seconds(final_frame):.3f}s."],
    ]


def export_single(info: AlgorithmInfo, original: list[int],
                  final_frame: Frame, path: str | Path) -> None:
    rows = build_rows(info, original, final_frame)
    _write(rows, path)


def export_comparison(rows_a, rows_b, info_a, info_b, winner: str, path: str | Path) -> None:
    combined: list[list[str]] = [["Metric", info_a.name, info_b.name]]
    a = dict((r[0], r[1]) for r in rows_a)
    b = dict((r[0], r[1]) for r in rows_b)
    for key in ["Dataset Size", "Total Comparisons", "Total Swaps / Movements",
                "Execution Time (s)", "Best Case", "Average Case", "Worst Case",
                "Space Complexity", "Stable", "In-place"]:
        combined.append([key, a.get(key, ""), b.get(key, "")])
    combined.append(["More Efficient", winner, ""])
    _write(combined, path)


def _write(rows: list[list[str]], path: str | Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(rows)
