"""Momentum / trend-following baseline: moving-average crossover."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from perp_lab.strategies.base import SIDE_COL, apply_direction, validate_direction


@dataclass(frozen=True)
class MomentumCrossover:
    """Long/short when a fast SMA is above/below a slow SMA.

    The target position at the close of bar *t* is ``+1`` when
    ``sma_fast_t > sma_slow_t``, ``-1`` when below, and ``0`` while either
    moving average is still warming up. ``direction`` restricts the sign to
    long-only or short-only if desired. The engine executes this position at the
    open of bar *t+1* (handled by the backtester).
    """

    fast: int
    slow: int
    direction: str = "both"

    def __post_init__(self) -> None:
        if self.fast <= 0 or self.slow <= 0:
            raise ValueError("Moving-average windows must be positive.")
        if self.fast >= self.slow:
            raise ValueError(f"fast ({self.fast}) must be < slow ({self.slow}).")
        validate_direction(self.direction)

    @property
    def name(self) -> str:
        return f"momentum_crossover_{self.fast}_{self.slow}_{self.direction}"

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        fast_col, slow_col = f"sma_{self.fast}", f"sma_{self.slow}"
        missing = [c for c in (fast_col, slow_col) if c not in features.columns]
        if missing:
            raise ValueError(f"Missing feature columns {missing}; build them with build_features.")

        raw = (
            pl.when(pl.col(fast_col).is_null() | pl.col(slow_col).is_null())
            .then(pl.lit(0))
            .when(pl.col(fast_col) > pl.col(slow_col))
            .then(pl.lit(1))
            .when(pl.col(fast_col) < pl.col(slow_col))
            .then(pl.lit(-1))
            .otherwise(pl.lit(0))
        )
        return features.sort("open_time").select(
            "open_time", apply_direction(raw, self.direction).cast(pl.Int8).alias(SIDE_COL)
        )
