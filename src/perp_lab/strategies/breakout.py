"""Breakout (Donchian-channel) baseline strategy.

Enter long when the close breaks **above** the rolling high channel, short when
it breaks **below** the rolling low channel. The channel is built from *previous*
bars only -- the current bar is excluded (``shift(1)``) so the break is measured
against information available strictly before the bar's own close. Optional
``confirmation_bars`` require several consecutive breaking closes. The position
is exited when the close re-enters the channel (or reverses on an opposite
break); execution of the resulting target position is next-bar (backtester).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from perp_lab.strategies.base import SIDE_COL, evolve_positions, validate_direction
from perp_lab.strategies.filters import apply_regime_gate


@dataclass(frozen=True)
class Breakout:
    channel_window: int
    confirmation_bars: int = 1
    direction: str = "both"
    regime_gate: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.channel_window <= 0:
            raise ValueError("channel_window must be a positive number of bars.")
        if self.confirmation_bars < 1:
            raise ValueError("confirmation_bars must be >= 1.")
        validate_direction(self.direction)

    @property
    def name(self) -> str:
        return f"breakout_{self.channel_window}_{self.confirmation_bars}_{self.direction}"

    def params(self) -> dict[str, object]:
        return {
            "family": "breakout",
            "channel_window": self.channel_window,
            "confirmation_bars": self.confirmation_bars,
            "direction": self.direction,
            "regime_gate": list(self.regime_gate) if self.regime_gate else None,
        }

    def required_features(self) -> tuple[str, ...]:
        # Uses raw OHLC (always present); no feature-engine columns required.
        return ()

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        needed = ("open_time", "high", "low", "close")
        missing = [c for c in needed if c not in features.columns]
        if missing:
            raise ValueError(f"Breakout requires columns {missing}.")
        feats = features.sort("open_time")

        w, c = self.channel_window, self.confirmation_bars
        upper_prev = pl.col("high").rolling_max(window_size=w, min_samples=w).shift(1)
        lower_prev = pl.col("low").rolling_min(window_size=w, min_samples=w).shift(1)
        prepared = feats.select(
            "open_time",
            "close",
            upper_prev.alias("__upper"),
            lower_prev.alias("__lower"),
        )
        close = prepared["close"].to_numpy().astype(float)
        upper = prepared["__upper"].to_numpy().astype(float)
        lower = prepared["__lower"].to_numpy().astype(float)
        valid = np.isfinite(upper) & np.isfinite(lower)

        break_up = valid & (close > upper)
        break_dn = valid & (close < lower)
        # Require `c` consecutive breaking closes (confirmation).
        long_entry = _consecutive(break_up, c)
        short_entry = _consecutive(break_dn, c)
        # Exit: the close is back inside the previous channel.
        exit_flat = valid & (close <= upper) & (close >= lower)

        if self.direction == "long":
            short_entry = np.zeros_like(short_entry)
        elif self.direction == "short":
            long_entry = np.zeros_like(long_entry)

        side = evolve_positions(long_entry, short_entry, exit_flat)
        if self.regime_gate is not None:
            side = apply_regime_gate(side, feats, self.regime_gate)
        return prepared.select("open_time").with_columns(pl.Series(SIDE_COL, side, dtype=pl.Int8))


def _consecutive(flags: np.ndarray, k: int) -> np.ndarray:
    """Boolean array: ``True`` where ``flags`` was True for the last ``k`` bars."""
    if k <= 1:
        return flags.astype(bool)
    run = np.zeros(flags.shape[0], dtype=int)
    count = 0
    for t in range(flags.shape[0]):
        count = count + 1 if flags[t] else 0
        run[t] = count
    return run >= k
