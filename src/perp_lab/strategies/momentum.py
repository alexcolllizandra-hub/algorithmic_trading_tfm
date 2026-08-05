"""Momentum / trend-following baseline: moving-average crossover."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from perp_lab.strategies.base import SIDE_COL, apply_direction, validate_direction
from perp_lab.strategies.filters import apply_regime_gate, apply_trend_gate


@dataclass(frozen=True)
class MomentumCrossover:
    """Long/short when a fast SMA is above/below a slow SMA.

    The target position at the close of bar *t* is ``+1`` when
    ``sma_fast_t > sma_slow_t``, ``-1`` when below, and ``0`` while either
    moving average is still warming up. ``direction`` restricts the sign to
    long-only or short-only if desired. The engine executes this position at the
    open of bar *t+1* (handled by the backtester).

    Optional causal filters (both off by default, preserving the base
    behaviour): a **trend gate** (only take longs when ``close > sma(trend_ma)``
    and mirror for shorts) and a **regime gate** (only hold when the bar's regime
    label is in ``regime_gate``).
    """

    fast: int
    slow: int
    direction: str = "both"
    trend_filter_ma: int | None = None
    regime_gate: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.fast <= 0 or self.slow <= 0:
            raise ValueError("Moving-average windows must be positive.")
        if self.fast >= self.slow:
            raise ValueError(f"fast ({self.fast}) must be < slow ({self.slow}).")
        if self.trend_filter_ma is not None and self.trend_filter_ma <= 0:
            raise ValueError("trend_filter_ma must be a positive window.")
        validate_direction(self.direction)

    @property
    def name(self) -> str:
        return f"momentum_crossover_{self.fast}_{self.slow}_{self.direction}"

    def params(self) -> dict[str, object]:
        return {
            "family": "momentum",
            "fast": self.fast,
            "slow": self.slow,
            "direction": self.direction,
            "trend_filter_ma": self.trend_filter_ma,
            "regime_gate": list(self.regime_gate) if self.regime_gate else None,
        }

    def required_features(self) -> tuple[str, ...]:
        cols = [f"sma_{self.fast}", f"sma_{self.slow}"]
        if self.trend_filter_ma is not None:
            cols.append(f"sma_{self.trend_filter_ma}")
        return tuple(cols)

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        fast_col, slow_col = f"sma_{self.fast}", f"sma_{self.slow}"
        missing = [c for c in (fast_col, slow_col) if c not in features.columns]
        if missing:
            raise ValueError(
                f"Missing feature columns {missing}; build them with the feature engine."
            )

        raw = (
            pl.when(pl.col(fast_col).is_null() | pl.col(slow_col).is_null())
            .then(pl.lit(0))
            .when(pl.col(fast_col) > pl.col(slow_col))
            .then(pl.lit(1))
            .when(pl.col(fast_col) < pl.col(slow_col))
            .then(pl.lit(-1))
            .otherwise(pl.lit(0))
        )
        feats = features.sort("open_time")
        out = feats.select(
            "open_time", apply_direction(raw, self.direction).cast(pl.Int8).alias(SIDE_COL)
        )

        if self.trend_filter_ma is None and self.regime_gate is None:
            return out

        side = out[SIDE_COL].to_numpy().copy()
        if self.trend_filter_ma is not None:
            side = apply_trend_gate(side, feats, f"sma_{self.trend_filter_ma}")
        if self.regime_gate is not None:
            side = apply_regime_gate(side, feats, self.regime_gate)
        return out.with_columns(pl.Series(SIDE_COL, side, dtype=pl.Int8))
