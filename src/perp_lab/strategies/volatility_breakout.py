"""Volatility-scaled breakout.

A fixed-width channel treats a 2% move in a calm market and a 2% move in a
turbulent one as the same event. This family scales the breakout threshold by
recent volatility, so "a large move" means large *relative to how much this asset
has been moving lately*.

The computation is deliberately split into three stages, because breakout
strategies are where look-ahead most often hides:

1. **Threshold** -- a reference level and a volatility unit, both computed from
   bars strictly before the decision bar. Every rolling window here is followed by
   ``shift(1)``: a rolling maximum that includes the current bar's own high is
   trivially never exceeded by the current bar, and the resulting strategy is a
   fiction.
2. **Signal** -- comparing the decision bar's close against that threshold. The
   close is the only current-bar value used, and it is the last thing known about
   the bar.
3. **Execution** -- not done here at all. The backtester fills the resulting
   target position at the *next* bar's open, so a signal is never executed at the
   price that produced it.

Variants are kept few and interpretable: an entry multiple, an exit rule and an
optional trailing-volatility floor. Adding a cross product of every plausible
smoothing and quantile would inflate the search space far faster than it would
add economic content.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from perp_lab.strategies.base import SIDE_COL, evolve_positions, validate_direction
from perp_lab.strategies.filters import apply_regime_gate

EXIT_MODES = ("reenter_level", "opposite_break", "volatility_stop")


@dataclass(frozen=True)
class VolatilityBreakout:
    """Break of a prior extreme by a multiple of recent true-range volatility.

    Parameters
    ----------
    level_window:
        Bars of the prior high/low channel. Excludes the decision bar.
    atr_window:
        Bars of the average true range that sets the volatility unit.
    entry_atr:
        How many volatility units beyond the prior extreme a close must reach.
    exit_atr:
        Used by ``volatility_stop``: how many units the price may retrace from the
        best level seen during the trade before the position is closed. Must be
        smaller than ``entry_atr`` -- an exit threshold at or beyond the entry
        threshold would close a position on the bar that opened it.
    """

    level_window: int
    atr_window: int
    entry_atr: float
    exit_atr: float = 1.0
    exit_mode: str = "reenter_level"
    min_atr_pct: float | None = None
    direction: str = "both"
    regime_gate: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.level_window <= 0:
            raise ValueError("level_window must be a positive number of bars.")
        if self.atr_window <= 0:
            raise ValueError("atr_window must be a positive number of bars.")
        if self.entry_atr <= 0:
            raise ValueError(
                "entry_atr must be strictly positive; a zero threshold is not a break."
            )
        if self.exit_atr <= 0:
            raise ValueError("exit_atr must be strictly positive.")
        if self.exit_mode not in EXIT_MODES:
            raise ValueError(f"exit_mode must be one of {EXIT_MODES}, got {self.exit_mode!r}.")
        if self.exit_mode == "volatility_stop" and self.exit_atr >= self.entry_atr:
            raise ValueError(
                f"exit_atr ({self.exit_atr}) must be < entry_atr ({self.entry_atr}): a stop at or "
                "beyond the entry threshold closes the position on the bar that opened it."
            )
        if self.min_atr_pct is not None and not 0.0 <= self.min_atr_pct < 1.0:
            raise ValueError("min_atr_pct is a quantile in [0, 1).")
        validate_direction(self.direction)

    @property
    def name(self) -> str:
        return (
            f"volbreak_{self.level_window}_{self.atr_window}_"
            f"{self.entry_atr:g}_{self.exit_mode}_{self.direction}"
        )

    def params(self) -> dict[str, object]:
        return {
            "family": "volatility_breakout",
            "level_window": self.level_window,
            "atr_window": self.atr_window,
            "entry_atr": self.entry_atr,
            "exit_atr": self.exit_atr,
            "exit_mode": self.exit_mode,
            "min_atr_pct": self.min_atr_pct,
            "direction": self.direction,
            "regime_gate": list(self.regime_gate) if self.regime_gate else None,
        }

    def required_features(self) -> tuple[str, ...]:
        # Built from raw OHLC; no engine feature columns are read.
        return ()

    # -- stage 1: threshold ------------------------------------------------- #

    def thresholds(self, features: pl.DataFrame) -> pl.DataFrame:
        """Reference levels and volatility unit, from bars strictly before each bar.

        Exposed separately so the causality of the threshold can be tested without
        going through signal generation.
        """
        needed = ("open_time", "high", "low", "close")
        missing = [c for c in needed if c not in features.columns]
        if missing:
            raise ValueError(f"VolatilityBreakout requires columns {missing}.")
        feats = features.sort("open_time")

        prev_close = pl.col("close").shift(1)
        true_range = pl.max_horizontal(
            pl.col("high") - pl.col("low"),
            (pl.col("high") - prev_close).abs(),
            (pl.col("low") - prev_close).abs(),
        )
        w, a = self.level_window, self.atr_window
        out = feats.with_columns(true_range.alias("__tr")).with_columns(
            # shift(1) everywhere: the decision bar contributes nothing to its own
            # threshold.
            pl.col("high").rolling_max(window_size=w, min_samples=w).shift(1).alias("upper_level"),
            pl.col("low").rolling_min(window_size=w, min_samples=w).shift(1).alias("lower_level"),
            pl.col("__tr").rolling_mean(window_size=a, min_samples=a).shift(1).alias("atr"),
        )
        if self.min_atr_pct is not None:
            # A trailing quantile of the volatility unit itself, again excluding the
            # decision bar. An expanding quantile over the whole sample would be a
            # full-sample statistic feeding a trading decision.
            floor_window = max(self.atr_window * 10, 100)
            out = out.with_columns(
                pl.col("atr")
                .rolling_quantile(
                    quantile=self.min_atr_pct,
                    window_size=floor_window,
                    min_samples=floor_window,
                )
                .alias("atr_floor")
            )
        else:
            out = out.with_columns(pl.lit(None, dtype=pl.Float64).alias("atr_floor"))
        return out.select("open_time", "close", "upper_level", "lower_level", "atr", "atr_floor")

    # -- stage 2: signal ---------------------------------------------------- #

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        prepared = self.thresholds(features)
        close = prepared["close"].to_numpy().astype(float)
        upper = prepared["upper_level"].to_numpy().astype(float)
        lower = prepared["lower_level"].to_numpy().astype(float)
        atr = prepared["atr"].to_numpy().astype(float)

        valid = np.isfinite(upper) & np.isfinite(lower) & np.isfinite(atr) & (atr > 0)
        if self.min_atr_pct is not None:
            floor = prepared["atr_floor"].to_numpy().astype(float)
            valid = valid & np.isfinite(floor) & (atr >= floor)

        long_trigger = upper + self.entry_atr * atr
        short_trigger = lower - self.entry_atr * atr
        long_entry = valid & (close > long_trigger)
        short_entry = valid & (close < short_trigger)

        if self.direction == "long":
            short_entry = np.zeros_like(short_entry)
        elif self.direction == "short":
            long_entry = np.zeros_like(long_entry)

        exit_flat = self._exits(close, upper, lower, atr, valid, long_entry, short_entry)

        side = evolve_positions(long_entry, short_entry, exit_flat)
        if self.regime_gate is not None:
            side = apply_regime_gate(side, features.sort("open_time"), self.regime_gate)
        return prepared.select("open_time").with_columns(pl.Series(SIDE_COL, side, dtype=pl.Int8))

    def _exits(
        self,
        close: np.ndarray,
        upper: np.ndarray,
        lower: np.ndarray,
        atr: np.ndarray,
        valid: np.ndarray,
        long_entry: np.ndarray,
        short_entry: np.ndarray,
    ) -> np.ndarray:
        if self.exit_mode == "opposite_break":
            # Only a break the other way closes the position; evolve_positions
            # already reverses on an opposite entry, so no separate exit fires.
            return np.zeros_like(valid)
        if self.exit_mode == "reenter_level":
            # Price is back inside the prior channel: the break did not hold.
            return valid & (close <= upper) & (close >= lower)
        return _volatility_stop(close, atr, valid, long_entry, short_entry, self.exit_atr)


def _volatility_stop(
    close: np.ndarray,
    atr: np.ndarray,
    valid: np.ndarray,
    long_entry: np.ndarray,
    short_entry: np.ndarray,
    exit_atr: float,
) -> np.ndarray:
    """Trailing stop at ``exit_atr`` volatility units from the trade's best close.

    Written as an explicit forward pass because a trailing stop depends on the
    path taken since entry, which no fixed-window rolling expression can express.
    Every value it reads is from the current bar or earlier.
    """
    n = close.shape[0]
    out = np.zeros(n, dtype=bool)
    position = 0
    extreme = np.nan
    for t in range(n):
        if position == 0:
            if valid[t] and long_entry[t]:
                position, extreme = 1, close[t]
            elif valid[t] and short_entry[t]:
                position, extreme = -1, close[t]
            continue

        if position == 1:
            extreme = max(extreme, close[t])
            if valid[t] and close[t] <= extreme - exit_atr * atr[t]:
                out[t] = True
                position, extreme = 0, np.nan
            elif short_entry[t]:
                position, extreme = -1, close[t]
        else:
            extreme = min(extreme, close[t])
            if valid[t] and close[t] >= extreme + exit_atr * atr[t]:
                out[t] = True
                position, extreme = 0, np.nan
            elif long_entry[t]:
                position, extreme = 1, close[t]
    return out
