"""Tests for breakout, mean-reversion, shared filters and momentum trend gate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.strategies.base import evolve_positions
from perp_lab.strategies.breakout import Breakout
from perp_lab.strategies.mean_reversion import MeanReversion
from perp_lab.strategies.momentum import MomentumCrossover


def _frame(close: list[float], **extra: list[float]) -> pl.DataFrame:
    n = len(close)
    t = [datetime(2021, 1, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(n)]
    data = {
        "open_time": t,
        "open": close,
        "high": extra.get("high", [c + 0.5 for c in close]),
        "low": extra.get("low", [c - 0.5 for c in close]),
        "close": close,
    }
    for k, v in extra.items():
        data[k] = v
    return pl.DataFrame(data)


# --------------------------------------------------------------------------- #
# State machine
# --------------------------------------------------------------------------- #
def test_evolve_positions_reversal_and_exit() -> None:
    le = np.array([True, False, False, False, False])
    se = np.array([False, False, True, False, False])
    ex = np.array([False, False, False, True, False])
    pos = evolve_positions(le, se, ex)
    # long at 0, hold at 1, reverse to short at 2, exit to flat at 3, stay flat.
    assert pos.tolist() == [1, 1, -1, 0, 0]


# --------------------------------------------------------------------------- #
# Breakout
# --------------------------------------------------------------------------- #
def test_breakout_uses_previous_channel_not_current_bar() -> None:
    # Flat then a jump. With channel_window=3 the breakout must trigger on the
    # bar AFTER the level is exceeded relative to the PRIOR channel, never using
    # the current bar's own high in its channel.
    close = [10, 10, 10, 10, 20, 20, 20, 20]
    highs = [c + 0.1 for c in close]
    lows = [c - 0.1 for c in close]
    df = _frame([float(c) for c in close], high=highs, low=lows)
    sig = Breakout(channel_window=3, confirmation_bars=1).signals(df)
    sides = sig["side"].to_list()
    # First 3 bars are warm-up (channel null) -> flat.
    assert sides[0] == 0
    # The breakout to long appears once close (20) exceeds the previous 3-bar
    # high channel (~10.1); it cannot appear before the jump bar.
    assert 1 in sides
    assert sides[3] == 0  # still inside the flat channel before the jump


def test_breakout_confirmation_requires_consecutive_breaks() -> None:
    close = [10, 10, 10, 10, 20, 12, 20, 20, 20]
    df = _frame([float(c) for c in close])
    one = Breakout(channel_window=3, confirmation_bars=1).signals(df)["side"].to_list()
    three = Breakout(channel_window=3, confirmation_bars=3).signals(df)["side"].to_list()
    # More confirmation never produces MORE long bars than 1-bar confirmation.
    assert sum(s == 1 for s in three) <= sum(s == 1 for s in one)


def test_breakout_direction_long_only_has_no_shorts() -> None:
    rng = np.random.default_rng(1)
    close = list(100 + np.cumsum(rng.normal(0, 1, 80)))
    df = _frame([float(c) for c in close])
    sides = Breakout(channel_window=5, direction="long").signals(df)["side"].to_list()
    assert min(sides) >= 0


def test_breakout_invalid_params() -> None:
    with pytest.raises(ValueError):
        Breakout(channel_window=0)
    with pytest.raises(ValueError):
        Breakout(channel_window=5, confirmation_bars=0)


# --------------------------------------------------------------------------- #
# Mean reversion
# --------------------------------------------------------------------------- #
def test_mean_reversion_fades_extremes() -> None:
    n = 20
    z = [0.0] * n
    z[5] = 3.0  # rich -> should go short
    z[6] = 2.5
    z[7] = 0.05  # revert within exit band -> flat
    z[12] = -3.0  # cheap -> long
    z[13] = -0.05  # exit
    df = _frame([100.0] * n).with_columns(pl.Series("zscore_5", z))
    sides = MeanReversion(zscore_window=5, entry_z=2.0, exit_z=0.5).signals(df)["side"].to_list()
    assert sides[5] == -1  # short the rich extreme
    assert sides[7] == 0  # exit inside the band
    assert sides[12] == 1  # long the cheap extreme


def test_mean_reversion_requires_exit_below_entry() -> None:
    with pytest.raises(ValueError, match=r"exit_z .* < entry_z"):
        MeanReversion(zscore_window=10, entry_z=1.0, exit_z=1.5)


def test_mean_reversion_direction_short_only() -> None:
    n = 20
    z = [0.0] * n
    z[5] = -3.0  # would be a long, but short-only disallows it
    df = _frame([100.0] * n).with_columns(pl.Series("zscore_5", z))
    sides = (
        MeanReversion(zscore_window=5, entry_z=2.0, exit_z=0.5, direction="short")
        .signals(df)["side"]
        .to_list()
    )
    assert max(sides) <= 0


# --------------------------------------------------------------------------- #
# Filters: momentum trend + regime gate
# --------------------------------------------------------------------------- #
def test_momentum_trend_gate_blocks_counter_trend() -> None:
    n = 30
    close = [100.0 + i for i in range(n)]  # rising
    df = _frame(close)
    # Build SMAs the strategy needs.
    df = df.with_columns(
        pl.col("close").rolling_mean(3, min_samples=3).alias("sma_3"),
        pl.col("close").rolling_mean(6, min_samples=6).alias("sma_6"),
        pl.col("close").rolling_mean(4, min_samples=4).alias("sma_4"),
    )
    base = MomentumCrossover(fast=3, slow=6).signals(df)["side"].to_list()
    gated = MomentumCrossover(fast=3, slow=6, trend_filter_ma=4).signals(df)["side"].to_list()
    # Trend gate can only remove exposure, never add it.
    assert all(abs(g) <= abs(b) for g, b in zip(gated, base, strict=True))


def test_regime_gate_flattens_disallowed_regimes() -> None:
    n = 12
    close = [100.0 + i for i in range(n)]
    df = _frame(close).with_columns(
        pl.col("close").rolling_mean(2, min_samples=2).alias("sma_2"),
        pl.col("close").rolling_mean(4, min_samples=4).alias("sma_4"),
        pl.Series("regime", ["high"] * 6 + ["low"] * 6),
    )
    gated = MomentumCrossover(fast=2, slow=4, regime_gate=("low",)).signals(df)["side"].to_list()
    # First half is "high" regime -> flattened to 0.
    assert all(s == 0 for s in gated[:6])
