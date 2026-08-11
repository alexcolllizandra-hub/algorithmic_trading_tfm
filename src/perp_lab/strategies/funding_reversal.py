"""Post-extreme-funding reversal (Gate S1 family).

Economic hypothesis
-------------------
An extreme funding rate is a *positioning* observation, not a price observation:
it says one side of the book is crowded enough to pay to stay there. The
hypothesis is that crowding resolves -- through de-leveraging or liquidation --
within a bounded horizon after the extreme is published, producing a short-lived
drift **against** the paying side.

Relation to the rejected ``funding`` family
-------------------------------------------
Gate R3 rejected ``FundingTilt``, which holds a *continuous* stance driven by a
funding z-score and exits on a band. This family is an **event** strategy: it
triggers on a trailing percentile extreme, holds for a fixed number of bars, and
then flattens regardless of what funding does next. The economic claim is
different (transient unwind after an extreme, not persistent carry), the trade
population is different (bounded, non-overlapping episodes), and the exit is
governed by the clock rather than by the signal. It is not a re-parameterisation
of a rejected family.

Causality
---------
``funding_rate`` reaches each bar through a backward as-of join on the
publication timestamp, so bar *t* only sees rates already published at or before
its open. The percentile threshold is a trailing rolling quantile over past and
current bars only. Execution is next bar.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from perp_lab.strategies.base import SIDE_COL, validate_direction
from perp_lab.strategies.filters import apply_regime_gate
from perp_lab.strategies.timed_exit import evolve_timed_positions

FUNDING_COL = "funding_rate"


@dataclass(frozen=True)
class FundingReversal:
    """Fade a trailing-percentile funding extreme for a bounded holding period."""

    rank_window: int
    extreme_pct: float
    holding_bars: int
    min_abs_rate: float = 0.0
    direction: str = "both"
    regime_gate: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.rank_window <= 1:
            raise ValueError("rank_window must exceed 1 bar for a percentile to exist.")
        if not 0.5 < self.extreme_pct < 1.0:
            raise ValueError(
                f"extreme_pct ({self.extreme_pct}) must lie in (0.5, 1.0): the upper and lower "
                "tails are defined symmetrically as pct and 1 - pct."
            )
        if self.holding_bars < 1:
            raise ValueError("holding_bars must be at least one bar.")
        if self.min_abs_rate < 0:
            raise ValueError("min_abs_rate must be non-negative.")
        validate_direction(self.direction)

    @property
    def name(self) -> str:
        return (
            f"funding_reversal_{self.rank_window}_{self.extreme_pct:g}"
            f"_h{self.holding_bars}_{self.direction}"
        )

    def params(self) -> dict[str, object]:
        return {
            "family": "funding_reversal",
            "rank_window": self.rank_window,
            "extreme_pct": self.extreme_pct,
            "holding_bars": self.holding_bars,
            "min_abs_rate": self.min_abs_rate,
            "direction": self.direction,
            "regime_gate": list(self.regime_gate) if self.regime_gate else None,
            "funding_role": "feature_only",
            "funding_cashflow_note": (
                "funding paid or received is charged by the backtester, never here"
            ),
        }

    def required_features(self) -> tuple[str, ...]:
        return (FUNDING_COL,)

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        for column in ("open_time", FUNDING_COL):
            if column not in features.columns:
                raise ValueError(
                    f"FundingReversal requires a {column!r} column, attached causally by a "
                    "backward as-of join on the publication timestamp."
                )
        feats = features.sort("open_time")
        w = self.rank_window
        rate = pl.col(FUNDING_COL).cast(pl.Float64)
        prepared = feats.select(
            "open_time",
            rate.alias("rate"),
            rate.rolling_quantile(quantile=self.extreme_pct, window_size=w, min_samples=w).alias(
                "upper"
            ),
            rate.rolling_quantile(
                quantile=1.0 - self.extreme_pct, window_size=w, min_samples=w
            ).alias("lower"),
        )

        values = prepared["rate"].to_numpy().astype(float)
        upper = prepared["upper"].to_numpy().astype(float)
        lower = prepared["lower"].to_numpy().astype(float)
        valid = (
            np.isfinite(values)
            & np.isfinite(upper)
            & np.isfinite(lower)
            & (np.abs(values) >= self.min_abs_rate)
        )

        # Funding at the top of its trailing distribution means longs are paying,
        # so the reversal trade is short, and symmetrically for the lower tail.
        short_event = valid & (values >= upper)
        long_event = valid & (values <= lower)

        if self.direction == "long":
            short_event = np.zeros_like(short_event)
        elif self.direction == "short":
            long_event = np.zeros_like(long_event)

        side = evolve_timed_positions(long_event, short_event, self.holding_bars)
        if self.regime_gate is not None:
            side = apply_regime_gate(side, feats, self.regime_gate)
        return prepared.select("open_time").with_columns(pl.Series(SIDE_COL, side, dtype=pl.Int8))
