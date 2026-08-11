"""BTC-ETH relative-value spread reversion (Gate S1 family).

Economic hypothesis
-------------------
BTC and ETH perpetuals share a dominant common factor. When one leg runs ahead
of the other over a short window without a change in that common factor, the
dislocation is a *relative* mispricing rather than news, and it reverts. The
traded object is the target leg alone, taken against its own recent
outperformance or underperformance versus the reference leg.

Relation to the rejected ``BTC_ETH_confirmation`` family
--------------------------------------------------------
Gate R3 rejected ``CrossAssetConfirmation``, which uses the peer as a
**directional filter**: trade the target in the direction it is already moving,
but only when the peer agrees. This family takes the opposite economic view and
a different object: it trades the *difference* between the legs, entering
against the leg that moved more. Agreement between the assets is a
**precondition** here (a spread only exists while the legs are coupled), not a
signal. Same two assets, different claim.

Causality
---------
``xasset_rel_momentum_{w}`` is built from an exact join on ``open_time`` and
past-only log-price differences on both legs, and ``xasset_corr_{w}`` from
trailing returns. Neither reads a peer bar that closes after the decision bar.
Execution is next bar.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from perp_lab.strategies.base import SIDE_COL, evolve_positions, validate_direction
from perp_lab.strategies.filters import apply_regime_gate


@dataclass(frozen=True)
class CrossAssetSpreadReversion:
    """Fade the target leg's relative move against its reference leg."""

    lookback: int
    entry_spread: float
    exit_spread: float
    min_corr: float | None = None
    corr_window: int | None = None
    target_symbol: str = ""
    reference_symbol: str = ""
    direction: str = "both"
    regime_gate: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.lookback <= 0:
            raise ValueError("lookback must be a positive number of bars.")
        if self.entry_spread <= 0:
            raise ValueError("entry_spread must be strictly positive.")
        if self.exit_spread < 0:
            raise ValueError("exit_spread must be non-negative.")
        if self.exit_spread >= self.entry_spread:
            raise ValueError(
                f"exit_spread ({self.exit_spread}) must be < entry_spread "
                f"({self.entry_spread}); otherwise a position closes on the bar that opened it."
            )
        if (self.min_corr is None) != (self.corr_window is None):
            raise ValueError(
                "min_corr and corr_window must be set together: a correlation floor without "
                "a window has no column to read, and a window without a floor is inert."
            )
        if self.min_corr is not None and not -1.0 <= self.min_corr <= 1.0:
            raise ValueError("min_corr must lie in [-1, 1].")
        if self.corr_window is not None and self.corr_window < 2:
            raise ValueError("corr_window must be at least 2 bars.")
        if self.target_symbol and self.target_symbol == self.reference_symbol:
            raise ValueError(
                f"{self.target_symbol} cannot be its own reference leg; there is no spread."
            )
        validate_direction(self.direction)

    @property
    def name(self) -> str:
        return (
            f"xasset_spread_rev_{self.lookback}_{self.entry_spread:g}"
            f"_{self.exit_spread:g}_{self.direction}"
        )

    @property
    def spread_col(self) -> str:
        return f"xasset_rel_momentum_{self.lookback}"

    @property
    def corr_col(self) -> str | None:
        return None if self.corr_window is None else f"xasset_corr_{self.corr_window}"

    def params(self) -> dict[str, object]:
        return {
            "family": "xasset_spread_reversion",
            "lookback": self.lookback,
            "entry_spread": self.entry_spread,
            "exit_spread": self.exit_spread,
            "min_corr": self.min_corr,
            "corr_window": self.corr_window,
            "target_symbol": self.target_symbol,
            "reference_symbol": self.reference_symbol,
            "direction": self.direction,
            "regime_gate": list(self.regime_gate) if self.regime_gate else None,
        }

    def required_features(self) -> tuple[str, ...]:
        corr = self.corr_col
        return (self.spread_col,) if corr is None else (self.spread_col, corr)

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        missing = [c for c in self.required_features() if c not in features.columns]
        if missing:
            raise ValueError(
                f"Missing feature columns {missing}; the reference leg must be supplied to the "
                "feature engine as a peer frame. This family cannot degrade to a single-asset "
                "strategy: the second leg is the hypothesis."
            )
        feats = features.sort("open_time")
        spread = feats[self.spread_col].cast(pl.Float64).to_numpy().astype(float)
        valid = np.isfinite(spread)

        corr_col = self.corr_col
        if corr_col is not None and self.min_corr is not None:
            corr = feats[corr_col].cast(pl.Float64).to_numpy().astype(float)
            # Below the floor the legs are not co-moving, so the "spread" is two
            # unrelated series and reversion has no mechanism to rely on.
            valid = valid & np.isfinite(corr) & (corr >= self.min_corr)

        short_entry = valid & (spread >= self.entry_spread)  # target ran ahead -> sell it
        long_entry = valid & (spread <= -self.entry_spread)  # target lagged -> buy it
        exit_flat = valid & (np.abs(spread) <= self.exit_spread)

        if self.direction == "long":
            short_entry = np.zeros_like(short_entry)
        elif self.direction == "short":
            long_entry = np.zeros_like(long_entry)

        side = evolve_positions(long_entry, short_entry, exit_flat)
        if self.regime_gate is not None:
            side = apply_regime_gate(side, feats, self.regime_gate)
        return feats.select("open_time").with_columns(pl.Series(SIDE_COL, side, dtype=pl.Int8))
