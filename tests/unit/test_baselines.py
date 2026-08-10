"""Tests for the fixed reference baselines.

Baselines must be causal, deterministic and parameter-frozen: they exist to give
searched strategies something honest to beat, so any tuning would defeat them.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from perp_lab.backtesting.engine import run_backtest
from perp_lab.strategies.base import SIDE_COL
from perp_lab.strategies.baselines import (
    AlwaysLong,
    FixedCrossover,
    FixedMeanReversion,
    FixedMomentum,
    Flat,
    RandomEntry,
    baseline_feature_requirements,
    default_baselines,
)


def _frame(n: int = 200) -> pl.DataFrame:
    t0 = datetime(2021, 1, 1, tzinfo=UTC)
    times = [t0 + timedelta(hours=i) for i in range(n)]
    close = [100.0 + 10.0 * (i % 20) for i in range(n)]
    df = pl.DataFrame(
        {
            "open_time": times,
            "open": close,
            "high": [c + 1 for c in close],
            "low": [c - 1 for c in close],
            "close": close,
            "volume": [1000.0] * n,
        }
    )
    return df.with_columns(
        pl.col("close").rolling_mean(24).alias("sma_24"),
        pl.col("close").rolling_mean(96).alias("sma_96"),
        (pl.col("close") / pl.col("close").shift(24) - 1.0).alias("momentum_24"),
        (
            (pl.col("close") - pl.col("close").rolling_mean(48)) / pl.col("close").rolling_std(48)
        ).alias("zscore_48"),
    )


def test_flat_never_takes_a_position() -> None:
    out = Flat().signals(_frame())
    assert out[SIDE_COL].abs().sum() == 0


def test_always_long_holds_one_unit_every_bar() -> None:
    out = AlwaysLong().signals(_frame())
    assert out[SIDE_COL].to_list() == [1] * out.height


def test_always_long_still_pays_the_entry_cost() -> None:
    """Buy-and-hold on a perpetual is not free: the entry is charged once."""
    df = _frame(50)
    signals = AlwaysLong().signals(df)
    res = run_backtest(signals, df, timeframe="1h", fee_bps_per_side=4.0, slippage_bps_per_side=1.0)
    assert float(res.ledger["cost"].sum()) == pytest.approx(5.0 / 1e4)
    assert float(res.ledger["turnover"].sum()) == pytest.approx(1.0)


def test_crossover_rejects_fast_not_below_slow() -> None:
    with pytest.raises(ValueError, match="must be <"):
        FixedCrossover(fast=96, slow=24)


def test_sides_are_always_in_the_valid_domain() -> None:
    df = _frame()
    for strat in default_baselines().values():
        out = strat.signals(df)  # type: ignore[attr-defined]
        assert set(out[SIDE_COL].unique().to_list()) <= {-1, 0, 1}
        assert out.height == df.height
        assert out["open_time"].to_list() == df["open_time"].to_list()


def test_warmup_rows_are_flat_not_null() -> None:
    """Null feature inputs during warm-up must produce a flat position, not a null."""
    df = _frame()
    for strat in (FixedCrossover(), FixedMomentum(), FixedMeanReversion()):
        out = strat.signals(df)
        assert out[SIDE_COL].null_count() == 0
        assert out[SIDE_COL][0] == 0


def test_random_entry_is_reproducible_and_respects_exposure() -> None:
    df = _frame(2000)
    a = RandomEntry(seed=7, exposure=0.5).signals(df)
    b = RandomEntry(seed=7, exposure=0.5).signals(df)
    assert a.equals(b)
    c = RandomEntry(seed=8, exposure=0.5).signals(df)
    assert not a.equals(c)
    share = float((a[SIDE_COL] != 0).mean())  # type: ignore[arg-type]
    assert 0.45 < share < 0.55


def test_random_entry_rejects_impossible_exposure() -> None:
    with pytest.raises(ValueError, match="exposure"):
        RandomEntry(exposure=1.5)


def test_baselines_are_deterministic_across_calls() -> None:
    df = _frame()
    for strat in default_baselines().values():
        assert strat.signals(df).equals(strat.signals(df))  # type: ignore[attr-defined]


def test_baseline_signals_use_no_future_information() -> None:
    """Truncation invariance: past signals cannot change when the future is cut off."""
    df = _frame(300)
    cut = 200
    for strat in (FixedCrossover(), FixedMomentum(), FixedMeanReversion(), Flat(), AlwaysLong()):
        full = strat.signals(df).head(cut)
        truncated = strat.signals(df.head(cut))
        assert full.equals(truncated), f"{strat.name} leaked future information"


def test_declared_feature_requirements_cover_the_suite() -> None:
    required = baseline_feature_requirements()
    assert "sma_24" in required and "sma_96" in required
    assert "momentum_24" in required and "zscore_48" in required
    df = _frame()
    for col in required:
        assert col in df.columns
