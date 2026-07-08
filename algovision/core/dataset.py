"""Dataset generation, shuffling and custom-input validation (PRD 7.3)."""

from __future__ import annotations

import random

from ..config import VALUE_MIN, VALUE_MAX, CUSTOM_MAX_ELEMENTS, ARRAY_SIZE_MIN


class ValidationError(ValueError):
    """Raised with a human-readable message when custom input is invalid."""


def random_dataset(size: int, seed: int | None = None) -> list[int]:
    rng = random.Random(seed)
    return [rng.randint(VALUE_MIN, VALUE_MAX) for _ in range(size)]


def shuffle_dataset(values: list[int], seed: int | None = None) -> list[int]:
    out = list(values)
    random.Random(seed).shuffle(out)
    return out


def parse_custom_input(text: str) -> list[int]:
    """Parse & validate comma-separated positive integers (PRD 7.3).

    Raises :class:`ValidationError` with a clear message on any problem;
    never returns a partially-valid list.
    """
    raw = text.strip()
    if not raw:
        raise ValidationError("Input is empty. Enter comma-separated integers, e.g. 64, 34, 25.")

    tokens = [tok.strip() for tok in raw.split(",")]
    values: list[int] = []
    for tok in tokens:
        if tok == "":
            raise ValidationError("Empty value found. Remove extra commas between numbers.")
        if "." in tok:
            raise ValidationError(f"'{tok}' is a decimal. Only whole numbers are allowed.")
        if tok.startswith("-"):
            raise ValidationError(f"'{tok}' is negative. Only positive integers are allowed.")
        if not tok.isdigit():
            raise ValidationError(f"'{tok}' is not a valid integer.")
        value = int(tok)
        if value < VALUE_MIN:
            raise ValidationError(f"{value} is below the minimum of {VALUE_MIN}.")
        if value > VALUE_MAX:
            raise ValidationError(f"{value} exceeds the maximum of {VALUE_MAX}.")
        values.append(value)

    if len(values) < ARRAY_SIZE_MIN:
        raise ValidationError(
            f"At least {ARRAY_SIZE_MIN} values are required (got {len(values)})."
        )
    if len(values) > CUSTOM_MAX_ELEMENTS:
        raise ValidationError(
            f"Too many values: {len(values)}. The maximum dataset size is "
            f"{CUSTOM_MAX_ELEMENTS} elements."
        )
    return values
