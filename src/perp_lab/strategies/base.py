"""Strategy interface shared by all baseline and discovered strategies."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import polars as pl

# Column holding the target position decided at each bar's close.
SIDE_COL = "side"

_VALID_DIRECTIONS = ("long", "short", "both")


def validate_direction(direction: str) -> str:
    if direction not in _VALID_DIRECTIONS:
        raise ValueError(f"direction must be one of {_VALID_DIRECTIONS}, got {direction!r}.")
    return direction


def apply_direction(side: pl.Expr, direction: str) -> pl.Expr:
    """Constrain a raw {-1,0,1} side expression to the allowed direction."""
    if direction == "long":
        return pl.max_horizontal(side, pl.lit(0))
    if direction == "short":
        return pl.min_horizontal(side, pl.lit(0))
    return side


@runtime_checkable
class Strategy(Protocol):
    """A strategy maps a causal feature frame to a target-position frame.

    ``signals`` must return a frame with ``open_time`` and an integer
    :data:`SIDE_COL` column. The side at row *t* uses only information available
    at the close of bar *t*; warm-up rows (null inputs) are flat (0).
    """

    name: str

    def signals(self, features: pl.DataFrame) -> pl.DataFrame: ...
