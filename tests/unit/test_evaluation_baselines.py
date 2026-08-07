"""Tests for evaluating baselines on a strategy's own out-of-sample ledger.

The comparison is only fair if the baselines see identical bars, identical costs
and the identical execution convention. These tests pin that down.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.backtesting.engine import run_backtest
from perp_lab.evaluation.baselines import (
    baselines_on_ledger,
    realised_cost_rate,
    strategy_versus_baselines,
)

FEE_BPS = 4.0
SLIP_BPS = 1.0


def _ledger(n: int = 600) -> pl.DataFrame:
    t0 = datetime(2022, 1, 1, tzinfo=UTC)
    times = [t0 + timedelta(hours=i) for i in range(n)]
    price = [100.0 * (1.0 + 0.002 * i + 0.03 * np.sin(i / 9.0)) for i in range(n)]
    prices = pl.DataFrame({"open_time": times, "open": price})
    sides = [1 if np.sin(i / 23.0) > 0 else 0 for i in range(n)]
    signals = pl.DataFrame({"open_time": times, "side": sides})
    return run_backtest(
        signals,
        prices,
        timeframe="1h",
        fee_bps_per_side=FEE_BPS,
        slippage_bps_per_side=SLIP_BPS,
    ).ledger


def test_realised_cost_rate_recovers_the_configured_bps() -> None:
    """Baselines are charged the run's own rate, so that rate must be exact."""
    rate = realised_cost_rate(_ledger())
    assert rate == pytest.approx((FEE_BPS + SLIP_BPS) / 1e4, rel=1e-9)


def test_flat_baseline_earns_and_costs_nothing() -> None:
    out = baselines_on_ledger(_ledger(), timeframe="1h")["flat"]
    assert out["total_return"] == pytest.approx(0.0)
    assert out["total_cost"] == pytest.approx(0.0)


def test_always_long_matches_the_market_less_one_entry_cost() -> None:
    ledger = _ledger()
    market = ledger["oo_return"].to_numpy()
    out = baselines_on_ledger(ledger, timeframe="1h")["always_long"]
    assert out["exposure"] == pytest.approx(1.0)
    assert out["total_cost"] == pytest.approx((FEE_BPS + SLIP_BPS) / 1e4, rel=1e-9)
    # Buy-and-hold return must track the compounded market return closely.
    buy_hold = float(np.prod(1.0 + market) - 1.0)
    assert out["total_return"] == pytest.approx(buy_hold, rel=0.02)


def test_every_baseline_is_evaluated_on_the_same_number_of_bars() -> None:
    ledger = _ledger()
    for metrics in baselines_on_ledger(ledger, timeframe="1h").values():
        assert metrics["n_bars"] == float(ledger.height)


def test_baselines_are_deterministic_including_the_random_one() -> None:
    ledger = _ledger()
    a = baselines_on_ledger(ledger, timeframe="1h", seed=11)
    b = baselines_on_ledger(ledger, timeframe="1h", seed=11)
    assert a == b
    c = baselines_on_ledger(ledger, timeframe="1h", seed=12)
    assert a["random_entry"] != c["random_entry"]


def test_random_entry_pays_for_its_turnover() -> None:
    """A coin-flip baseline trades constantly; the cost model must punish that."""
    out = baselines_on_ledger(_ledger(), timeframe="1h")["random_entry"]
    assert out["total_cost"] > 0.0
    assert out["total_return"] < 0.0


def test_comparison_reports_the_strategy_alongside_the_baselines() -> None:
    ledger = _ledger()
    result = strategy_versus_baselines(ledger, timeframe="1h")
    assert result["n_bars"] == ledger.height
    assert set(result["baselines"]) == {
        "flat",
        "always_long",
        "ma_crossover_24_96",
        "momentum_24",
        "mean_reversion_z48",
        "random_entry",
    }
    # The strategy's reported total return must equal its own ledger, untouched.
    expected = float(np.prod(1.0 + ledger["net_return"].to_numpy()) - 1.0)
    assert result["strategy"]["total_return"] == pytest.approx(expected, rel=1e-9)


def test_baselines_never_see_a_cheaper_cost_than_the_strategy() -> None:
    ledger = _ledger()
    result = strategy_versus_baselines(ledger, timeframe="1h")
    rate = result["cost_rate_per_unit_turnover"]
    for name, metrics in result["baselines"].items():
        if metrics["total_cost"] == 0.0:
            continue
        implied = metrics["total_cost"] / metrics["turnover"]
        assert implied == pytest.approx(rate, rel=1e-9), f"{name} was charged a different rate"


def test_ledger_without_market_returns_is_rejected() -> None:
    ledger = _ledger().drop("oo_return")
    with pytest.raises(ValueError, match="oo_return"):
        baselines_on_ledger(ledger, timeframe="1h")
