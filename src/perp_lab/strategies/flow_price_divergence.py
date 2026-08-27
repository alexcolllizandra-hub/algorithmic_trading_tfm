"""Disagreement between aggressive flow and the price it produced (Gate S2).

Economic hypothesis
-------------------
Over any window, cumulative aggressive buying and the price change it causes are
mechanically and strongly *positively* related: lifting the ask moves the price
up. The interesting event is therefore the one that should not happen -- a window
in which aggressors bought heavily and price nonetheless **fell**, or sold
heavily and price nonetheless **rose**.

Such a window says the passive side absorbed everything the aggressors threw at
it without conceding the level. Two readings compete:

* **The absorber was informed.** Someone with a view supplied liquidity into the
  flow and is now positioned; price continues in the direction the absorber
  defended, i.e. *with the price move* and *against* the aggressive flow.
* **The aggressors were early.** The flow reflects information the price has not
  yet reflected, and the move catches up with the flow.

As with ``taker_flow_extreme`` the sign is an estimated parameter (``response``),
not an assumption, and both arms are charged to the multiple-testing ledger.

Relation to ``taker_flow_extreme`` (S2-01)
------------------------------------------
S2-01 fires on the magnitude of accumulated imbalance and never looks at price.
This family ignores magnitude ranking and fires only on a *sign disagreement*
between flow and the contemporaneous move. Because flow and return are positively
related by construction, most of S2-01's triggers have flow and price agreeing
and are therefore invisible here. The overlap is measured, not asserted, in
``tests/unit/test_strategies_s2.py::test_s2_families_trigger_on_different_bars``.

Causality
---------
Both the flow and the move are measured over the same window of bars, lagged by
``flow_lag >= 1`` so the whole window closes before the decision bar. Thresholds
are trailing quantiles. Execution is next bar.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from perp_lab.strategies.base import SIDE_COL, validate_direction
from perp_lab.strategies.filters import apply_regime_gate
from perp_lab.strategies.orderflow import (
    as_float,
    finite,
    flow_imbalance,
    require_flow_columns,
    trailing_upper_quantile,
    window_log_return,
)
from perp_lab.strategies.timed_exit import evolve_timed_positions

RESPONSES = ("follow_absorber", "follow_flow")


@dataclass(frozen=True)
class FlowPriceDivergence:
    """Trade windows where aggressive flow and the price move disagree in sign."""

    window: int
    rank_window: int
    flow_pct: float
    move_pct: float
    holding_bars: int
    response: str
    flow_lag: int = 1
    direction: str = "both"
    regime_gate: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.window < 1:
            raise ValueError("window must be at least one bar.")
        if self.rank_window <= 1:
            raise ValueError("rank_window must exceed 1 bar for a quantile to exist.")
        for label, value in (("flow_pct", self.flow_pct), ("move_pct", self.move_pct)):
            if not 0.5 <= value < 1.0:
                raise ValueError(
                    f"{label} ({value}) must lie in [0.5, 1.0): it ranks an absolute "
                    "magnitude, so it is a one-sided upper tail."
                )
        if self.holding_bars < 1:
            raise ValueError("holding_bars must be at least one bar.")
        if self.response not in RESPONSES:
            raise ValueError(f"response must be one of {RESPONSES}, got {self.response!r}.")
        if self.flow_lag < 1:
            raise ValueError("flow_lag must be >= 1 (contemporaneous flow is not usable).")
        validate_direction(self.direction)

    @property
    def name(self) -> str:
        return (
            f"flow_price_divergence_w{self.window}_r{self.rank_window}"
            f"_{self.flow_pct:g}_{self.move_pct:g}_h{self.holding_bars}"
            f"_{self.response}_{self.direction}"
        )

    def params(self) -> dict[str, object]:
        return {
            "family": "flow_price_divergence",
            "window": self.window,
            "rank_window": self.rank_window,
            "flow_pct": self.flow_pct,
            "move_pct": self.move_pct,
            "holding_bars": self.holding_bars,
            "response": self.response,
            "flow_lag": self.flow_lag,
            "direction": self.direction,
            "regime_gate": list(self.regime_gate) if self.regime_gate else None,
            "trigger": "sign disagreement between windowed taker imbalance and windowed return",
        }

    def required_features(self) -> tuple[str, ...]:
        return ()

    def indicators(self, features: pl.DataFrame) -> pl.DataFrame:
        """Lagged flow, lagged move over the same window, and both thresholds."""
        require_flow_columns(features, "FlowPriceDivergence")
        feats = features.sort("open_time")
        prepared = feats.select(
            "open_time",
            flow_imbalance(self.window, self.flow_lag).alias("imbalance"),
            window_log_return(self.window, self.flow_lag).alias("move"),
        )
        prepared = prepared.with_columns(
            pl.col("imbalance").abs().alias("abs_imbalance"),
            pl.col("move").abs().alias("abs_move"),
        )
        return prepared.with_columns(
            trailing_upper_quantile("abs_imbalance", self.rank_window, self.flow_pct).alias(
                "flow_level"
            ),
            trailing_upper_quantile("abs_move", self.rank_window, self.move_pct).alias(
                "move_level"
            ),
        )

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        feats = features.sort("open_time")
        prepared = self.indicators(feats)

        imbalance = as_float(prepared, "imbalance")
        move = as_float(prepared, "move")
        abs_imbalance = as_float(prepared, "abs_imbalance")
        abs_move = as_float(prepared, "abs_move")
        flow_level = as_float(prepared, "flow_level")
        move_level = as_float(prepared, "move_level")

        valid = finite(imbalance, move, abs_imbalance, abs_move, flow_level, move_level)
        material = valid & (abs_imbalance >= flow_level) & (abs_move >= move_level)
        disagree = material & (np.sign(imbalance) * np.sign(move) < 0)

        # Absorbed selling: aggressors sold, price rose, the passive buyer won.
        absorbed_selling = disagree & (move > 0)
        absorbed_buying = disagree & (move < 0)

        if self.response == "follow_absorber":
            long_event, short_event = absorbed_selling, absorbed_buying
        else:
            long_event, short_event = absorbed_buying, absorbed_selling

        if self.direction == "long":
            short_event = np.zeros_like(short_event)
        elif self.direction == "short":
            long_event = np.zeros_like(long_event)

        side = evolve_timed_positions(long_event, short_event, self.holding_bars)
        if self.regime_gate is not None:
            side = apply_regime_gate(side, feats, self.regime_gate)
        return prepared.select("open_time").with_columns(pl.Series(SIDE_COL, side, dtype=pl.Int8))
