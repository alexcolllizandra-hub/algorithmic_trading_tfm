"""BTC-ETH confirmation: trade one asset only when the other agrees.

This is the only family with an explicit dependency on a second asset, and that
dependency is treated as a first-class part of the specification rather than as
an extra column that happens to be present in the frame. The target symbol, the
reference symbol and the alignment rule are all recorded in ``params()``, because
"ETH confirmed by BTC" and "ETH confirmed by BTC lagged two hours" are different
strategies and a run must be able to say which one it was.

Why cross-asset alignment is dangerous
--------------------------------------
Joining two assets on equal timestamps looks obviously safe and usually is not.
Bars are labelled by their **open** time and are left-closed, so the BTC bar
labelled 12:00 covers 12:00-13:00 and is not complete until 13:00. A decision
taken at the close of ETH's 12:00 bar therefore cannot use BTC's 12:00 bar: at
that instant it is the bar currently being formed, and its close is the very
value being predicted.

The join here consequently requires ``reference_timestamp <= decision_timestamp -
one bar``, enforced by an as-of join onto a reference frame shifted by at least
one bar. ``reference_lag`` can delay it further, never less.

Both directions of the dependency are equally forbidden: BTC confirmed by a
later ETH bar is the same error with the symbols exchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from perp_lab.strategies.base import SIDE_COL, evolve_positions, validate_direction
from perp_lab.strategies.filters import apply_regime_gate

# The reference bar must be complete before the decision bar closes, so the
# smallest admissible lag is one bar.
MIN_REFERENCE_LAG = 1

CONFIRMATION_MODES = ("agree", "lead_lag", "divergence")


@dataclass(frozen=True)
class CrossAssetConfirmation:
    """Momentum on the target, gated by the reference asset's own momentum.

    Parameters
    ----------
    target_symbol, reference_symbol:
        Recorded explicitly. The reference is never the target.
    reference_lag:
        Bars by which the reference series is delayed before the join. At least
        :data:`MIN_REFERENCE_LAG`, so the reference bar is closed before the
        decision bar closes.
    mode:
        ``agree`` requires the reference to move the same way; ``lead_lag`` takes
        the reference's move as the signal itself; ``divergence`` trades the
        target against a reference that moved the other way.
    """

    lookback: int
    entry_threshold: float
    reference_threshold: float
    target_symbol: str
    reference_symbol: str
    reference_lag: int = MIN_REFERENCE_LAG
    mode: str = "agree"
    exit_threshold: float = 0.0
    direction: str = "both"
    regime_gate: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.lookback <= 0:
            raise ValueError("lookback must be a positive number of bars.")
        if self.entry_threshold <= 0:
            raise ValueError("entry_threshold must be strictly positive.")
        if self.reference_threshold < 0:
            raise ValueError("reference_threshold must be non-negative.")
        if self.exit_threshold < 0:
            raise ValueError("exit_threshold must be non-negative.")
        if self.exit_threshold >= self.entry_threshold:
            raise ValueError(
                f"exit_threshold ({self.exit_threshold}) must be < entry_threshold "
                f"({self.entry_threshold}); otherwise entry and exit fire on the same bar."
            )
        if self.reference_lag < MIN_REFERENCE_LAG:
            raise ValueError(
                f"reference_lag must be >= {MIN_REFERENCE_LAG}: bars are labelled by open time "
                "and are left-closed, so the reference bar sharing the decision bar's timestamp "
                "is still being formed and its close is not knowable."
            )
        if self.target_symbol == self.reference_symbol:
            raise ValueError(
                "reference_symbol must differ from target_symbol; an asset confirming itself "
                "is a single-asset strategy wearing a cross-asset label."
            )
        if self.mode not in CONFIRMATION_MODES:
            raise ValueError(f"mode must be one of {CONFIRMATION_MODES}, got {self.mode!r}.")
        validate_direction(self.direction)

    @property
    def name(self) -> str:
        return (
            f"xconf_{self.target_symbol}_by_{self.reference_symbol}_"
            f"{self.lookback}_{self.mode}_lag{self.reference_lag}_{self.direction}"
        )

    def params(self) -> dict[str, object]:
        return {
            "family": "BTC_ETH_confirmation",
            "lookback": self.lookback,
            "entry_threshold": self.entry_threshold,
            "reference_threshold": self.reference_threshold,
            "exit_threshold": self.exit_threshold,
            "target_symbol": self.target_symbol,
            "reference_symbol": self.reference_symbol,
            "reference_lag": self.reference_lag,
            "mode": self.mode,
            "direction": self.direction,
            "regime_gate": list(self.regime_gate) if self.regime_gate else None,
            "alignment_rule": (
                "backward as-of join of the reference onto the target, with the "
                f"reference delayed by {self.reference_lag} bar(s); the join "
                "guarantees reference_timestamp <= decision_timestamp - "
                f"{self.reference_lag} bar(s)"
            ),
        }

    def required_features(self) -> tuple[str, ...]:
        return ()

    def align_reference(self, target: pl.DataFrame, reference: pl.DataFrame) -> pl.DataFrame:
        """Join the reference's trailing return onto the target, causally.

        Returned frame carries ``reference_time``, the timestamp of the reference
        bar actually used, so the alignment can be asserted from the output rather
        than trusted.
        """
        for frame, what in ((target, "target"), (reference, "reference")):
            for column in ("open_time", "close"):
                if column not in frame.columns:
                    raise ValueError(f"{what} frame requires a {column!r} column.")

        ref = reference.sort("open_time").select(
            "open_time",
            (pl.col("close") / pl.col("close").shift(self.lookback) - 1.0).alias("__ref_return"),
        )
        # Delay the reference by whole bars BEFORE the join. Shifting the payload
        # rather than the timestamps keeps the recorded reference_time equal to the
        # bar whose data is used, so the lag is visible in the output.
        ref = ref.with_columns(
            pl.col("open_time").shift(self.reference_lag).alias("__ref_source_time"),
        ).select(
            pl.col("open_time").alias("__ref_join_time"),
            pl.col("__ref_return").shift(self.reference_lag).alias("reference_return"),
            pl.col("__ref_source_time").alias("reference_time"),
        )

        tgt = target.sort("open_time").select(
            "open_time",
            "close",
            (pl.col("close") / pl.col("close").shift(self.lookback) - 1.0).alias("target_return"),
        )
        return tgt.join_asof(
            ref, left_on="open_time", right_on="__ref_join_time", strategy="backward"
        ).drop("__ref_join_time")

    def signals(
        self, features: pl.DataFrame, reference: pl.DataFrame | None = None
    ) -> pl.DataFrame:
        if reference is None:
            raise ValueError(
                "CrossAssetConfirmation needs the reference asset's bars. This family is an "
                "explicit cross-asset dependency, not a column that may or may not be present."
            )
        aligned = self.align_reference(features, reference)

        tgt = aligned["target_return"].to_numpy().astype(float)
        ref = aligned["reference_return"].to_numpy().astype(float)
        valid = np.isfinite(tgt) & np.isfinite(ref)

        if self.mode == "lead_lag":
            # The reference's move is the signal; the target's own move is ignored.
            long_entry = valid & (ref >= self.entry_threshold)
            short_entry = valid & (ref <= -self.entry_threshold)
            exit_flat = valid & (np.abs(ref) <= self.exit_threshold)
        else:
            up = valid & (tgt >= self.entry_threshold)
            down = valid & (tgt <= -self.entry_threshold)
            ref_up = ref >= self.reference_threshold
            ref_down = ref <= -self.reference_threshold
            if self.mode == "agree":
                long_entry, short_entry = up & ref_up, down & ref_down
            else:  # divergence
                long_entry, short_entry = up & ref_down, down & ref_up
            exit_flat = valid & (np.abs(tgt) <= self.exit_threshold)

        if self.direction == "long":
            short_entry = np.zeros_like(short_entry)
        elif self.direction == "short":
            long_entry = np.zeros_like(long_entry)

        side = evolve_positions(long_entry, short_entry, exit_flat)
        if self.regime_gate is not None:
            side = apply_regime_gate(side, features.sort("open_time"), self.regime_gate)
        return aligned.select("open_time").with_columns(pl.Series(SIDE_COL, side, dtype=pl.Int8))
