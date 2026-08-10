"""Funding-rate strategies for USDT-M perpetual futures.

Two completely different things share the word "funding" in this codebase, and
conflating them is the fastest way to produce a strategy that looks profitable
and is not:

* **Funding as a feature** -- the published rate, read here as a *signal* about
  positioning. That is what this module uses. It is attached to each bar by a
  backward as-of join, so bar *t* sees the latest rate whose publication
  timestamp is at or before that bar's open. A forward fill would let a rate
  settle before it was announced.
* **Funding as a cashflow** -- the amount actually paid or received for holding a
  position across a settlement. That belongs to the backtester and is charged
  there, once, in the single ledger implementation. This module never adds a
  cashflow; if it did, the same funding would be counted twice.

A strategy in this family therefore has an unusual property worth stating: when
it shorts into positive funding it earns the carry *through the backtester's
funding column*, not through anything computed here.

Proxy warning
-------------
The related ``basis`` feature is a **mark-index** basis, not a spot basis. No
independent spot price is ingested at this data tier, and the index is itself an
exchange construct. It is a proxy and is labelled as one in the feature registry;
it must never be reported as an observed spot basis.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from perp_lab.strategies.base import SIDE_COL, evolve_positions, validate_direction
from perp_lab.strategies.filters import apply_regime_gate

FUNDING_COL = "funding_rate"

# fade: take the opposite side of whoever is paying (short when funding is high).
# follow: read persistent funding as a trend signal and take the paying side.
STANCES = ("fade", "follow")


@dataclass(frozen=True)
class FundingTilt:
    """Trade a standardised funding rate against its own recent history.

    The raw rate is not comparable across regimes -- 0.01% per 8h is extreme in a
    quiet market and unremarkable in a squeeze -- so it is standardised by a
    trailing mean and standard deviation computed from past bars only.
    """

    signal_window: int
    entry_z: float
    exit_z: float
    stance: str = "fade"
    min_abs_rate: float = 0.0
    direction: str = "both"
    regime_gate: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.signal_window <= 1:
            raise ValueError("signal_window must be > 1 bar for a standard deviation to exist.")
        if self.entry_z <= 0:
            raise ValueError("entry_z must be strictly positive.")
        if self.exit_z < 0:
            raise ValueError("exit_z must be non-negative.")
        if self.exit_z >= self.entry_z:
            raise ValueError(
                f"exit_z ({self.exit_z}) must be < entry_z ({self.entry_z}): an exit band at or "
                "outside the entry band closes a position on the bar that opened it."
            )
        if self.min_abs_rate < 0:
            raise ValueError("min_abs_rate must be non-negative.")
        if self.stance not in STANCES:
            raise ValueError(f"stance must be one of {STANCES}, got {self.stance!r}.")
        validate_direction(self.direction)

    @property
    def name(self) -> str:
        return f"funding_{self.stance}_{self.signal_window}_{self.entry_z:g}_{self.direction}"

    def params(self) -> dict[str, object]:
        return {
            "family": "funding",
            "signal_window": self.signal_window,
            "entry_z": self.entry_z,
            "exit_z": self.exit_z,
            "stance": self.stance,
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

    def standardised_funding(self, features: pl.DataFrame) -> pl.DataFrame:
        """The trailing z-score of the funding rate, from past bars only."""
        for column in ("open_time", FUNDING_COL):
            if column not in features.columns:
                raise ValueError(
                    f"FundingTilt requires a {column!r} column. The funding feature must be "
                    "attached causally (backward as-of join on the publication timestamp); "
                    "it is never forward-filled from a later settlement."
                )
        feats = features.sort("open_time")
        w = self.signal_window
        rate = pl.col(FUNDING_COL).cast(pl.Float64)
        mean = rate.rolling_mean(window_size=w, min_samples=w)
        sd = rate.rolling_std(window_size=w, min_samples=w)
        return feats.select(
            "open_time",
            rate.alias("rate"),
            pl.when(sd > 0).then((rate - mean) / sd).otherwise(None).alias("z"),
        )

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        prepared = self.standardised_funding(features)
        z = prepared["z"].to_numpy().astype(float)
        rate = prepared["rate"].to_numpy().astype(float)
        valid = np.isfinite(z) & np.isfinite(rate) & (np.abs(rate) >= self.min_abs_rate)

        high = valid & (z >= self.entry_z)
        low = valid & (z <= -self.entry_z)
        if self.stance == "fade":
            # Funding is high: longs are paying, so take the other side.
            long_entry, short_entry = low, high
        else:
            long_entry, short_entry = high, low

        if self.direction == "long":
            short_entry = np.zeros_like(short_entry)
        elif self.direction == "short":
            long_entry = np.zeros_like(long_entry)

        exit_flat = valid & (np.abs(z) <= self.exit_z)

        side = evolve_positions(long_entry, short_entry, exit_flat)
        if self.regime_gate is not None:
            side = apply_regime_gate(side, features.sort("open_time"), self.regime_gate)
        return prepared.select("open_time").with_columns(pl.Series(SIDE_COL, side, dtype=pl.Int8))
