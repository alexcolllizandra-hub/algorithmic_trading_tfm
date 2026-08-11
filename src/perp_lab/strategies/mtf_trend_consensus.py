"""Multi-horizon trend consensus (Gate S1 family).

Economic hypothesis
-------------------
Directional drift in perpetual futures is only worth trading when it is visible
at **several separated horizons at once**. A single fast/slow crossover -- the
``momentum`` family rejected at Gate R2 -- fires on any local sign change and
therefore spends most of its turnover on noise. Requiring *k of n* horizons to
agree, and requiring the agreement to be strong relative to recent volatility,
is a materially different filter on the same raw drift: it trades far less
often, and only when the drift is coherent across time scales.

Falsification
-------------
If drift is a scale-free artefact of return autocorrelation, agreement across
horizons adds no information and net performance is indistinguishable from the
rejected single-horizon momentum family after costs.

Causality
---------
Every input is ``momentum_{h} = ln(P_t / P_{t-h})``, a past-only feature
available at the close of bar *t*; the position is executed next bar by the
backtester. The volatility scale is a trailing standard deviation of past
returns (``roll_std_{w}``); no full-sample statistic is used.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from perp_lab.strategies.base import SIDE_COL, evolve_positions, validate_direction
from perp_lab.strategies.filters import apply_regime_gate


@dataclass(frozen=True)
class MultiHorizonTrendConsensus:
    """Hold a position only while ``min_agreement`` horizons share a sign.

    ``min_strength`` is expressed in units of the trailing return standard
    deviation over ``strength_window`` bars, so the threshold means the same
    thing in a quiet market and in a squeeze.
    """

    horizons: tuple[int, ...]
    min_agreement: int
    min_strength: float
    strength_window: int
    exit_agreement: int
    direction: str = "both"
    regime_gate: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if len(self.horizons) < 2:
            raise ValueError("horizons must contain at least two separated look-backs.")
        if len(set(self.horizons)) != len(self.horizons):
            raise ValueError(f"horizons must be distinct, got {self.horizons}.")
        if any(h <= 0 for h in self.horizons):
            raise ValueError("every horizon must be a positive number of bars.")
        if not 1 <= self.min_agreement <= len(self.horizons):
            raise ValueError(
                f"min_agreement ({self.min_agreement}) must lie in "
                f"[1, {len(self.horizons)}] for horizons {self.horizons}."
            )
        if not 1 <= self.exit_agreement <= self.min_agreement:
            raise ValueError(
                f"exit_agreement ({self.exit_agreement}) must lie in "
                f"[1, min_agreement={self.min_agreement}]; an exit threshold above the "
                "entry threshold closes the position on the bar that opened it."
            )
        if self.min_strength < 0:
            raise ValueError("min_strength must be non-negative.")
        if self.strength_window <= 1:
            raise ValueError("strength_window must exceed 1 bar for a deviation to exist.")
        validate_direction(self.direction)

    @property
    def name(self) -> str:
        horizons = "-".join(str(h) for h in self.horizons)
        return f"mtf_consensus_{horizons}_k{self.min_agreement}_{self.direction}"

    @property
    def strength_col(self) -> str:
        return f"roll_std_{self.strength_window}"

    def momentum_cols(self) -> tuple[str, ...]:
        return tuple(f"momentum_{h}" for h in self.horizons)

    def params(self) -> dict[str, object]:
        return {
            "family": "mtf_trend_consensus",
            "horizons": list(self.horizons),
            "min_agreement": self.min_agreement,
            "min_strength": self.min_strength,
            "strength_window": self.strength_window,
            "exit_agreement": self.exit_agreement,
            "direction": self.direction,
            "regime_gate": list(self.regime_gate) if self.regime_gate else None,
        }

    def required_features(self) -> tuple[str, ...]:
        return (*self.momentum_cols(), self.strength_col)

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        missing = [c for c in self.required_features() if c not in features.columns]
        if missing:
            raise ValueError(
                f"Missing feature columns {missing}; build them with the feature engine."
            )
        feats = features.sort("open_time")

        scale = feats[self.strength_col].cast(pl.Float64).to_numpy().astype(float)
        # A horizon-h move is compared against the volatility accumulated over h
        # bars, otherwise long horizons would clear any fixed threshold trivially.
        columns = [feats[c].cast(pl.Float64).to_numpy().astype(float) for c in self.momentum_cols()]
        stacked = np.vstack(columns)
        horizons = np.asarray(self.horizons, dtype=float).reshape(-1, 1)
        expected = scale.reshape(1, -1) * np.sqrt(horizons)

        finite = np.isfinite(stacked) & np.isfinite(expected) & (expected > 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            normalised = np.where(finite, stacked / np.where(expected > 0, expected, np.nan), 0.0)
        normalised = np.nan_to_num(normalised, nan=0.0, posinf=0.0, neginf=0.0)

        strong_up = finite & (normalised >= self.min_strength)
        strong_down = finite & (normalised <= -self.min_strength)
        n_up = strong_up.sum(axis=0)
        n_down = strong_down.sum(axis=0)

        # A bar is only usable once every horizon has left its warm-up.
        usable = finite.all(axis=0)
        long_entry = usable & (n_up >= self.min_agreement)
        short_entry = usable & (n_down >= self.min_agreement)
        exit_flat = usable & (n_up < self.exit_agreement) & (n_down < self.exit_agreement)

        if self.direction == "long":
            short_entry = np.zeros_like(short_entry)
        elif self.direction == "short":
            long_entry = np.zeros_like(long_entry)

        side = evolve_positions(long_entry, short_entry, exit_flat)
        if self.regime_gate is not None:
            side = apply_regime_gate(side, feats, self.regime_gate)
        return feats.select("open_time").with_columns(pl.Series(SIDE_COL, side, dtype=pl.Int8))
