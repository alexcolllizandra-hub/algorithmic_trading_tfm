"""Intraday session seasonality (Gate S1 family).

Economic hypothesis
-------------------
Perpetual futures trade continuously, but the humans and institutions behind the
flow do not. Session opens, the daily settlement cycle and the 8-hour funding
timestamps concentrate hedging and rebalancing into recurring windows of the UTC
day. The hypothesis is that a *calendar* window -- not a price pattern -- carries
a small, repeatable drift that survives costs at a low trade frequency.

Why this is a distinct hypothesis
---------------------------------
No family evaluated at Gate R3 conditions on the clock. This one contains no
price predictor at all: the entry is a timestamp and the exit is a bar count. If
it works, the explanation is flow periodicity; if it fails, no price-based
family is implicated.

Causality
---------
The hour of a bar is known at the bar's open, before any of its prices are
observed. The optional trend gate uses ``sma_{w}``, a past-only feature.
Execution is next bar, so the position is entered at the open of the bar after
the trigger hour. Note that the *entry hour* is chosen by the search inside each
outer fold's validation window, never on the fold's test slice.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from perp_lab.strategies.base import SIDE_COL, validate_direction
from perp_lab.strategies.filters import apply_regime_gate, trend_masks
from perp_lab.strategies.timed_exit import evolve_timed_positions

SIDE_MODES = ("long", "short")


@dataclass(frozen=True)
class IntradaySeasonality:
    """Enter at a fixed UTC hour and hold for a fixed number of bars."""

    entry_hour: int
    holding_bars: int
    side_mode: str
    trend_filter_ma: int | None = None
    direction: str = "both"
    regime_gate: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.entry_hour <= 23:
            raise ValueError(f"entry_hour ({self.entry_hour}) must lie in [0, 23] UTC.")
        if self.holding_bars < 1:
            raise ValueError("holding_bars must be at least one bar.")
        if self.side_mode not in SIDE_MODES:
            raise ValueError(f"side_mode must be one of {SIDE_MODES}, got {self.side_mode!r}.")
        if self.trend_filter_ma is not None and self.trend_filter_ma <= 0:
            raise ValueError("trend_filter_ma must be a positive number of bars.")
        validate_direction(self.direction)
        if self.direction != "both" and self.direction != self.side_mode:
            raise ValueError(
                f"direction={self.direction!r} forbids every trade this strategy can take "
                f"(side_mode={self.side_mode!r}); the combination is empty by construction."
            )

    @property
    def name(self) -> str:
        return f"intraday_h{self.entry_hour:02d}_{self.side_mode}_hold{self.holding_bars}"

    @property
    def trend_col(self) -> str | None:
        return None if self.trend_filter_ma is None else f"sma_{self.trend_filter_ma}"

    def params(self) -> dict[str, object]:
        return {
            "family": "intraday_seasonality",
            "entry_hour": self.entry_hour,
            "holding_bars": self.holding_bars,
            "side_mode": self.side_mode,
            "trend_filter_ma": self.trend_filter_ma,
            "direction": self.direction,
            "regime_gate": list(self.regime_gate) if self.regime_gate else None,
        }

    def required_features(self) -> tuple[str, ...]:
        return () if self.trend_col is None else (self.trend_col,)

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        if "open_time" not in features.columns:
            raise ValueError("IntradaySeasonality requires an 'open_time' column.")
        trend_col = self.trend_col
        if trend_col is not None and trend_col not in features.columns:
            raise ValueError(
                f"Missing feature column {trend_col!r}; build it with the feature engine."
            )
        feats = features.sort("open_time")
        hours = feats.select(pl.col("open_time").dt.hour().alias("hour"))["hour"]
        fires = (hours.to_numpy() == self.entry_hour).astype(bool)

        long_event = fires if self.side_mode == "long" else np.zeros_like(fires)
        short_event = fires if self.side_mode == "short" else np.zeros_like(fires)

        if trend_col is not None:
            long_ok, short_ok = trend_masks(feats, trend_col)
            long_event = long_event & long_ok
            short_event = short_event & short_ok

        side = evolve_timed_positions(long_event, short_event, self.holding_bars)
        if self.regime_gate is not None:
            side = apply_regime_gate(side, feats, self.regime_gate)
        return feats.select("open_time").with_columns(pl.Series(SIDE_COL, side, dtype=pl.Int8))
