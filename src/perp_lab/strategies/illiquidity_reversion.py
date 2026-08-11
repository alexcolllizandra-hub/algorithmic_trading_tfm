"""Reversion after an illiquidity-scaled price move (Gate S2 family).

Economic hypothesis
-------------------
Not every price move carries the same information. A move delivered on heavy
traded value is the market agreeing on a new level; the same move delivered on
thin value is somebody paying for immediacy against a shallow book. The
hypothesis is that the *second* kind is transitory: liquidity providers who
absorbed the impatient order are compensated when the price returns, and the
compensation is the tradable part.

The measurement is Amihud's ratio -- absolute return per unit of traded value --
which Brauneis, Mestel, Riordan & Theissen (2021, *Journal of Banking & Finance*
124, 106041) validate against order-book ground truth in crypto and find among
the best low-frequency proxies for liquidity *levels*. Because the level of the
ratio is instrument- and epoch-specific, it is never compared to a constant: the
trigger is its own trailing quantile.

Relation to the rejected ``mean_reversion`` family
--------------------------------------------------
Gate R3 rejected ``MeanReversion``, which fires on the trailing z-score of price
alone. This family conditions on a *different variable* and, crucially, on a
different subset of bars: a large move on heavy volume triggers the R3 family and
is deliberately **ignored** here, while a modest move on unusually thin volume is
invisible to the R3 family and is exactly what this one trades. The two trigger
sets are near-disjoint by construction, and
``tests/unit/test_strategies_s2.py::test_illiquidity_reversion_is_materially_different_from_mean_reversion``
measures that overlap rather than asserting it in prose. The economic claim also
differs: R3 claimed prices oscillate around a trailing mean; this claims that the
*compensation for supplying immediacy* is recoverable.

Exit
----
The exit is governed by the signal, not the clock: the position is closed once
illiquidity has normalised back below a lower trailing quantile, i.e. once the
condition that motivated the trade no longer holds. A stale position is closed by
the ``max_holding_bars`` safety cap, which exists so a permanently elevated
illiquidity regime cannot produce an unbounded hold.

Causality
---------
Both the move and the traded value are measured over bars strictly before the
decision bar (``flow_lag >= 1``). Quantiles are trailing. Execution is next bar.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from perp_lab.strategies.base import SIDE_COL, evolve_positions, validate_direction
from perp_lab.strategies.filters import apply_regime_gate
from perp_lab.strategies.orderflow import (
    amihud_impact,
    as_float,
    finite,
    require_flow_columns,
    trailing_upper_quantile,
    window_log_return,
)


@dataclass(frozen=True)
class IlliquidityReversion:
    """Fade a price move whose impact per unit of traded value is extreme."""

    impact_window: int
    rank_window: int
    entry_pct: float
    exit_pct: float
    max_holding_bars: int
    flow_lag: int = 1
    min_abs_move: float = 0.0
    direction: str = "both"
    regime_gate: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.impact_window < 1:
            raise ValueError("impact_window must be at least one bar.")
        if self.rank_window <= 1:
            raise ValueError("rank_window must exceed 1 bar for a quantile to exist.")
        if not 0.5 < self.entry_pct < 1.0:
            raise ValueError(
                f"entry_pct ({self.entry_pct}) must lie in (0.5, 1.0): it selects the "
                "illiquid upper tail of the impact distribution."
            )
        if not 0.0 < self.exit_pct < self.entry_pct:
            raise ValueError(
                f"exit_pct ({self.exit_pct}) must be positive and strictly below entry_pct "
                f"({self.entry_pct}); otherwise the position closes on the bar it opens."
            )
        if self.max_holding_bars < 1:
            raise ValueError("max_holding_bars must be at least one bar.")
        if self.flow_lag < 1:
            raise ValueError("flow_lag must be >= 1 (contemporaneous volume is not usable).")
        if self.min_abs_move < 0:
            raise ValueError("min_abs_move must be non-negative.")
        validate_direction(self.direction)

    @property
    def name(self) -> str:
        return (
            f"illiquidity_reversion_w{self.impact_window}_r{self.rank_window}"
            f"_{self.entry_pct:g}_{self.exit_pct:g}_m{self.max_holding_bars}_{self.direction}"
        )

    def params(self) -> dict[str, object]:
        return {
            "family": "illiquidity_reversion",
            "impact_window": self.impact_window,
            "rank_window": self.rank_window,
            "entry_pct": self.entry_pct,
            "exit_pct": self.exit_pct,
            "max_holding_bars": self.max_holding_bars,
            "flow_lag": self.flow_lag,
            "min_abs_move": self.min_abs_move,
            "direction": self.direction,
            "regime_gate": list(self.regime_gate) if self.regime_gate else None,
            "impact_measure": "Amihud: |window log return| / window quote volume",
            "proxy_note": (
                "a low-frequency proxy for illiquidity, not an order-book depth measurement"
            ),
        }

    def required_features(self) -> tuple[str, ...]:
        return ()

    def indicators(self, features: pl.DataFrame) -> pl.DataFrame:
        """Lagged Amihud impact, the move that produced it, and both quantiles."""
        require_flow_columns(features, "IlliquidityReversion")
        feats = features.sort("open_time")
        prepared = feats.select(
            "open_time",
            amihud_impact(self.impact_window, self.flow_lag).alias("impact"),
            window_log_return(self.impact_window, self.flow_lag).alias("move"),
        )
        return prepared.with_columns(
            trailing_upper_quantile("impact", self.rank_window, self.entry_pct).alias(
                "entry_level"
            ),
            trailing_upper_quantile("impact", self.rank_window, self.exit_pct).alias("exit_level"),
        )

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        feats = features.sort("open_time")
        prepared = self.indicators(feats)

        impact = as_float(prepared, "impact")
        move = as_float(prepared, "move")
        entry_level = as_float(prepared, "entry_level")
        exit_level = as_float(prepared, "exit_level")

        valid = finite(impact, move, entry_level, exit_level)
        fires = valid & (impact >= entry_level) & (np.abs(move) >= self.min_abs_move)

        # Fade the move that the thin book produced.
        long_entry = fires & (move < 0)
        short_entry = fires & (move > 0)
        # Close once illiquidity has normalised; warm-up bars close nothing.
        exit_flat = valid & (impact <= exit_level)

        if self.direction == "long":
            short_entry = np.zeros_like(short_entry)
        elif self.direction == "short":
            long_entry = np.zeros_like(long_entry)

        side = evolve_positions(long_entry, short_entry, exit_flat)
        side = _cap_holding(side, self.max_holding_bars)
        if self.regime_gate is not None:
            side = apply_regime_gate(side, feats, self.regime_gate)
        return prepared.select("open_time").with_columns(pl.Series(SIDE_COL, side, dtype=pl.Int8))


def _cap_holding(side: np.ndarray, max_bars: int) -> np.ndarray:
    """Flatten any run of identical non-zero sides longer than ``max_bars``.

    The cap is a risk control, not a signal: it can only remove exposure. A new
    position may open on the next bar only if the side changes, so the cap cannot
    be gamed into re-entering the same trade every ``max_bars`` bars.
    """
    capped = side.copy()
    held = 0
    previous = 0
    suppressing = False
    for t in range(capped.shape[0]):
        current = int(side[t])
        if current == 0:
            held, previous, suppressing = 0, 0, False
            continue
        if current != previous:
            held, previous, suppressing = 1, current, False
        else:
            held += 1
        if suppressing or held > max_bars:
            suppressing = True
            capped[t] = 0
    return capped.astype(np.int8)
