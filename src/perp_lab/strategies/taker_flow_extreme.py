"""Taker-flow pressure extreme, held over a multi-hour horizon (Gate S2 family).

Economic hypothesis
-------------------
An extreme accumulation of one-sided *aggressive* volume is an observation about
who is demanding immediacy. Two mechanisms compete and the literature does not
settle which dominates on this instrument:

* **Continuation.** Aggressive flow carries private information, so price keeps
  drifting in the direction of the pressure while the information is absorbed.
* **Reversal.** Aggressive flow is impatient, uninformed demand that pays the
  spread and pushes price away from fair value; liquidity providers who took the
  other side are compensated as it comes back.

Kim & Hansen report *positive* predictability from quarter-hour opening order
imbalance on Binance USDT-M perpetuals at 4-12 hour horizons; Chordia, Roll &
Subrahmanyam report a *negative* coefficient on **lagged** order imbalance in
equities. The response sign is therefore an estimated parameter (``response``),
never an assumption, and both arms are inside the same declared search space so
the multiple-testing ledger charges for both.

Why the horizon is part of the hypothesis
-----------------------------------------
Pindza (2026) shows that these same features, at a five-minute rebalance with
correct purging and VIP-0 costs, deliver net Sharpe ratios of -10 to -18 purely
through turnover of 124-204x notional per day. The claim under test here is not
"flow predicts returns" in the abstract but "flow predicts returns *by enough,
and for long enough*, to survive a round trip". Holding periods are therefore
restricted to multi-hour values and the exit is governed by the clock.

Relation to earlier families
----------------------------
No R2, R3 or S1 family reads the aggressor side. ``funding_reversal`` (S1-02)
also fires on a trailing percentile extreme and also exits on a clock, but the
variable it ranks is the *published funding rate* -- an eight-hourly positioning
observation about who pays whom -- whereas this family ranks *realised aggressive
volume* within the bar window. The two trigger on different data at different
frequencies; the shared exit mechanism is deliberate so that S1 and S2 event
families remain comparable.

Causality
---------
All flow inputs are lagged by ``flow_lag >= 1`` bars, per the frozen rule in
``docs/methodology/experimental_design.md``. Thresholds are trailing rolling
quantiles over past and current bars only. Execution is next bar.
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
)
from perp_lab.strategies.timed_exit import evolve_timed_positions

RESPONSES = ("continuation", "reversal")


@dataclass(frozen=True)
class TakerFlowExtreme:
    """Trade an extreme of accumulated taker imbalance for a bounded horizon."""

    flow_window: int
    rank_window: int
    extreme_pct: float
    holding_bars: int
    response: str
    flow_lag: int = 1
    min_abs_imbalance: float = 0.0
    direction: str = "both"
    regime_gate: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.flow_window < 1:
            raise ValueError("flow_window must be at least one bar.")
        if self.rank_window <= 1:
            raise ValueError("rank_window must exceed 1 bar for a percentile to exist.")
        if not 0.5 < self.extreme_pct < 1.0:
            raise ValueError(
                f"extreme_pct ({self.extreme_pct}) must lie in (0.5, 1.0): it ranks the "
                "absolute imbalance, so it is a one-sided upper tail."
            )
        if self.holding_bars < 1:
            raise ValueError("holding_bars must be at least one bar.")
        if self.response not in RESPONSES:
            raise ValueError(f"response must be one of {RESPONSES}, got {self.response!r}.")
        if self.flow_lag < 1:
            raise ValueError(
                "flow_lag must be >= 1: taker volume is known only at the bar's close and "
                "the frozen methodology forbids contemporaneous use."
            )
        if not 0.0 <= self.min_abs_imbalance < 1.0:
            raise ValueError("min_abs_imbalance must lie in [0, 1).")
        validate_direction(self.direction)

    @property
    def name(self) -> str:
        return (
            f"taker_flow_extreme_w{self.flow_window}_r{self.rank_window}"
            f"_{self.extreme_pct:g}_h{self.holding_bars}_{self.response}_{self.direction}"
        )

    def params(self) -> dict[str, object]:
        return {
            "family": "taker_flow_extreme",
            "flow_window": self.flow_window,
            "rank_window": self.rank_window,
            "extreme_pct": self.extreme_pct,
            "holding_bars": self.holding_bars,
            "response": self.response,
            "flow_lag": self.flow_lag,
            "min_abs_imbalance": self.min_abs_imbalance,
            "direction": self.direction,
            "regime_gate": list(self.regime_gate) if self.regime_gate else None,
            "flow_measure": "taker quote-volume imbalance (aggressor side reported by Binance)",
            "not_ofi_note": (
                "this is trade imbalance, not Cont-Kukanov-Stoikov order-flow imbalance; "
                "limit-order arrivals and cancellations are not in the data"
            ),
        }

    def required_features(self) -> tuple[str, ...]:
        # Built from raw kline columns; no feature-engine columns are read.
        return ()

    def indicators(self, features: pl.DataFrame) -> pl.DataFrame:
        """Lagged imbalance and its trailing extreme threshold (causal)."""
        require_flow_columns(features, "TakerFlowExtreme")
        feats = features.sort("open_time")
        with_flow = feats.select(
            "open_time",
            flow_imbalance(self.flow_window, self.flow_lag).alias("imbalance"),
        )
        return with_flow.with_columns(
            pl.col("imbalance").abs().alias("abs_imbalance")
        ).with_columns(
            trailing_upper_quantile("abs_imbalance", self.rank_window, self.extreme_pct).alias(
                "threshold"
            )
        )

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        feats = features.sort("open_time")
        prepared = self.indicators(feats)

        imbalance = as_float(prepared, "imbalance")
        magnitude = as_float(prepared, "abs_imbalance")
        threshold = as_float(prepared, "threshold")

        fires = (
            finite(imbalance, magnitude, threshold)
            & (magnitude >= threshold)
            & (magnitude >= self.min_abs_imbalance)
        )
        buy_pressure = fires & (imbalance > 0)
        sell_pressure = fires & (imbalance < 0)

        if self.response == "continuation":
            long_event, short_event = buy_pressure, sell_pressure
        else:
            long_event, short_event = sell_pressure, buy_pressure

        if self.direction == "long":
            short_event = np.zeros_like(short_event)
        elif self.direction == "short":
            long_event = np.zeros_like(long_event)

        side = evolve_timed_positions(long_event, short_event, self.holding_bars)
        if self.regime_gate is not None:
            side = apply_regime_gate(side, feats, self.regime_gate)
        return prepared.select("open_time").with_columns(pl.Series(SIDE_COL, side, dtype=pl.Int8))
