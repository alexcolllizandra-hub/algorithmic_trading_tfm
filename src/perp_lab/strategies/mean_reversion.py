"""Mean-reversion baseline strategy (rolling price z-score).

Fade extreme deviations of price from its trailing mean: go **short** when the
z-score rises above ``+entry_z`` and **long** when it falls below ``-entry_z``.
Close the position when the z-score reverts inside ``+/-exit_z`` (or reverses on
an opposite extreme). The z-score is a causal feature (``zscore_{w}``) computed
from trailing mean/std; execution of the target position is next-bar.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from perp_lab.strategies.base import SIDE_COL, evolve_positions, validate_direction
from perp_lab.strategies.filters import apply_regime_gate


@dataclass(frozen=True)
class MeanReversion:
    zscore_window: int
    entry_z: float
    exit_z: float
    direction: str = "both"
    regime_gate: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.zscore_window <= 0:
            raise ValueError("zscore_window must be a positive number of bars.")
        if self.entry_z <= 0:
            raise ValueError("entry_z must be strictly positive.")
        if self.exit_z < 0:
            raise ValueError("exit_z must be >= 0.")
        if self.exit_z >= self.entry_z:
            raise ValueError(f"exit_z ({self.exit_z}) must be < entry_z ({self.entry_z}).")
        validate_direction(self.direction)

    @property
    def name(self) -> str:
        return f"mean_reversion_{self.zscore_window}_{self.entry_z}_{self.exit_z}_{self.direction}"

    @property
    def zscore_col(self) -> str:
        return f"zscore_{self.zscore_window}"

    def params(self) -> dict[str, object]:
        return {
            "family": "mean_reversion",
            "zscore_window": self.zscore_window,
            "entry_z": self.entry_z,
            "exit_z": self.exit_z,
            "direction": self.direction,
            "regime_gate": list(self.regime_gate) if self.regime_gate else None,
        }

    def required_features(self) -> tuple[str, ...]:
        return (self.zscore_col,)

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        if self.zscore_col not in features.columns:
            raise ValueError(
                f"Missing feature column {self.zscore_col!r}; build it with the feature engine."
            )
        feats = features.sort("open_time")
        z = feats[self.zscore_col].cast(pl.Float64).to_numpy().astype(float)
        valid = np.isfinite(z)

        long_entry = valid & (z <= -self.entry_z)  # price cheap -> buy
        short_entry = valid & (z >= self.entry_z)  # price rich -> sell
        exit_flat = valid & (np.abs(z) <= self.exit_z)

        if self.direction == "long":
            short_entry = np.zeros_like(short_entry)
        elif self.direction == "short":
            long_entry = np.zeros_like(long_entry)

        side = evolve_positions(long_entry, short_entry, exit_flat)
        if self.regime_gate is not None:
            side = apply_regime_gate(side, feats, self.regime_gate)
        return feats.select("open_time").with_columns(pl.Series(SIDE_COL, side, dtype=pl.Int8))
