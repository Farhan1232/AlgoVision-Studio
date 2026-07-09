"""Global UI scale factor for proportional responsiveness.

The whole interface is designed at a reference size (REF_W x REF_H) and then
scaled up or down to the current window size.  Every font size, padding,
spacing and fixed dimension is expressed through :func:`fs` / :func:`sp`, which
multiply by the live scale factor.  The main window recomputes the factor on
every resize and re-applies the stylesheet + per-widget styling, so text and
spacing shrink to keep everything visible on small screens and grow on large
displays - without internal scrolling.
"""

from __future__ import annotations

# Reference design size (scale == 1.0 here).
REF_W = 1360
REF_H = 860

# Clamp so text never becomes unreadable or absurdly large.
MIN_SCALE = 0.62
MAX_SCALE = 1.30

_scale = 1.0


def compute_scale(width: int, height: int) -> float:
    """Scale that keeps the whole layout fitting the given window size.

    Uses the smaller of the width/height ratios so both dimensions fit, then
    clamps to a sensible readable range.
    """
    s = min(width / REF_W, height / REF_H)
    return max(MIN_SCALE, min(MAX_SCALE, s))


def set_scale(s: float) -> None:
    global _scale
    _scale = s


def get_scale() -> float:
    return _scale


def fs(px: float) -> int:
    """Scaled font size in px (never below a legible floor)."""
    return max(7, round(px * _scale))


def sp(px: float) -> int:
    """Scaled spacing / fixed dimension in px."""
    return max(1, round(px * _scale))
