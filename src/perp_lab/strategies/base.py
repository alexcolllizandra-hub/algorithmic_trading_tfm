"""Common strategy interface shared by all baseline and discovered strategies.

A *strategy* maps a **causal feature frame** to a **target-position frame**
indexed by timestamp. It is responsible only for *signal generation* (what
position to hold, decided at each bar's close); *execution* (the next-bar fill,
costs and funding) is the backtester's job. This separation keeps strategies
pure, deterministic and independently testable.

Every concrete strategy:

* validates incompatible parameter combinations at construction time;
* exposes ``params()`` so the exact configuration is recorded for each run;
* declares ``required_features()`` so the engine can guarantee the columns it
  reads exist before signalling;
* returns a frame with ``open_time`` and an integer :data:`SIDE_COL` in
  ``{-1, 0, +1}`` where warm-up rows (null inputs) are flat (0).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
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


def evolve_positions(
    long_entry: np.ndarray,
    short_entry: np.ndarray,
    exit_flat: np.ndarray,
) -> np.ndarray:
    """Deterministic O(n) position state machine for stateful strategies.

    Given per-bar boolean *entry* and *exit* conditions (all decided at the bar's
    close), evolve a held position in ``{-1, 0, +1}``:

    * from **flat**: a long/short entry opens the position (long takes
      precedence if both fire);
    * while **in a position**: an *opposite* entry **reverses** it directly
      (+1 -> -1 or -1 -> +1, generating two units of turnover downstream); an
      exit condition (and no opposite entry) closes it to flat; otherwise the
      position is held.

    Returns an ``int8`` array of held positions aligned to the input bars.
    """
    n = long_entry.shape[0]
    pos = np.zeros(n, dtype=np.int8)
    current = 0
    for t in range(n):
        le = bool(long_entry[t])
        se = bool(short_entry[t])
        ex = bool(exit_flat[t])
        if current == 0:
            if le:
                current = 1
            elif se:
                current = -1
        elif current == 1:
            if se:
                current = -1
            elif ex:
                current = 0
        else:  # current == -1
            if le:
                current = 1
            elif ex:
                current = 0
        pos[t] = current
    return pos


@runtime_checkable
class Strategy(Protocol):
    """Structural type implemented by every strategy (baseline or discovered)."""

    name: str

    def params(self) -> dict[str, object]: ...

    def required_features(self) -> tuple[str, ...]: ...

    def signals(self, features: pl.DataFrame) -> pl.DataFrame: ...
