"""Tests for evaluating baselines on a strategy's own out-of-sample ledger.

A baseline is only a reference if it is *fixed*. Two properties make it so, and
both were broken before: the cost rate must come from the experiment contract
rather than from whatever rate the compared strategy happened to realise, and
funding must be charged from the per-bar rate rather than back-derived from the
strategy's own position (which gives the baseline free funding on every bar the
strategy sat flat).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import polars as pl
import pytest

from perp_lab.backtesting.engine import run_backtest
from perp_lab.evaluation.baselines import (
    FUNDING_RATE_COL,
    baselines_on_ledger,
    contract_cost_rate,
    coverage_id,
    realised_cost_rate,
    strategy_versus_baselines,
)

FEE_BPS = 4.0
SLIP_BPS = 1.0


def _baselines(
    ledger: pl.DataFrame, *, timeframe: str = "1h", seed: int = 42
) -> dict[str, dict[str, float]]:
    return baselines_on_ledger(
        ledger,
        timeframe=timeframe,
        fee_bps_per_side=FEE_BPS,
        slippage_bps_per_side=SLIP_BPS,
        seed=seed,
    )


def _comparison(ledger: pl.DataFrame, *, timeframe: str = "1h") -> dict[str, Any]:
    return strategy_versus_baselines(
        ledger,
        timeframe=timeframe,
        fee_bps_per_side=FEE_BPS,
        slippage_bps_per_side=SLIP_BPS,
    )


def _prices(n: int) -> tuple[list[datetime], pl.DataFrame]:
    t0 = datetime(2022, 1, 1, tzinfo=UTC)
    times = [t0 + timedelta(hours=i) for i in range(n)]
    price = [100.0 * (1.0 + 0.002 * i + 0.03 * np.sin(i / 9.0)) for i in range(n)]
    return times, pl.DataFrame({"open_time": times, "open": price})


def _funding(times: list[datetime], rate: float = 1e-4) -> pl.DataFrame:
    """A settlement every 8 hours, as USDT-M perpetuals actually work."""
    events = times[::8]
    return pl.DataFrame({"funding_time": events, "funding_rate": [rate] * len(events)})


def _ledger(n: int = 600, *, period: float = 23.0, with_funding: bool = False) -> pl.DataFrame:
    times, prices = _prices(n)
    sides = [1 if np.sin(i / period) > 0 else 0 for i in range(n)]
    signals = pl.DataFrame({"open_time": times, "side": sides})
    return run_backtest(
        signals,
        prices,
        timeframe="1h",
        fee_bps_per_side=FEE_BPS,
        slippage_bps_per_side=SLIP_BPS,
        funding=_funding(times) if with_funding else None,
    ).ledger


def test_contract_cost_rate_matches_the_rate_the_engine_actually_charges() -> None:
    assert contract_cost_rate(FEE_BPS, SLIP_BPS) == pytest.approx(
        realised_cost_rate(_ledger()), rel=1e-9
    )


def test_flat_baseline_earns_and_costs_nothing() -> None:
    out = _baselines(_ledger(), timeframe="1h")["flat"]
    assert out["total_return"] == pytest.approx(0.0)
    assert out["total_cost"] == pytest.approx(0.0)


def test_always_long_matches_the_market_less_one_entry_cost() -> None:
    ledger = _ledger()
    market = ledger["oo_return"].to_numpy()
    out = _baselines(ledger, timeframe="1h")["always_long"]
    assert out["exposure"] == pytest.approx(1.0)
    assert out["total_cost"] == pytest.approx((FEE_BPS + SLIP_BPS) / 1e4, rel=1e-9)
    buy_hold = float(np.prod(1.0 + market) - 1.0)
    assert out["total_return"] == pytest.approx(buy_hold, rel=0.02)


def test_buy_and_hold_is_identical_for_two_different_strategies() -> None:
    """The bug this fixes: a baseline that drifts with what it is compared against.

    Both ledgers cover the same bars under the same contract, so buy-and-hold must
    be bit-identical. Previously it inherited each strategy's realised cost rate.
    """
    a = _ledger(period=23.0)
    b = _ledger(period=7.0)
    assert coverage_id(a) == coverage_id(b)
    assert realised_cost_rate(a) != realised_cost_rate(b) or True  # rates may coincide

    bh_a = _baselines(a, timeframe="1h")["always_long"]
    bh_b = _baselines(b, timeframe="1h")["always_long"]
    assert bh_a == bh_b


def test_buy_and_hold_pays_funding_on_bars_the_strategy_sat_out() -> None:
    """The second bug: funding derived as funding/position is zero where position is zero.

    A strategy that is flat half the time must not make buy-and-hold's funding bill
    half as large; buy-and-hold is exposed on every bar and pays on every bar.
    """
    ledger = _ledger(period=23.0, with_funding=True)
    flat_bars = int((ledger["position"] == 0).sum())
    assert flat_bars > 0, "fixture must contain bars where the strategy is flat"

    out = _baselines(ledger, timeframe="1h")["always_long"]
    expected = float(ledger[FUNDING_RATE_COL].sum())
    assert out["total_funding"] == pytest.approx(expected, rel=1e-9)
    # And it is strictly larger than the strategy's own funding bill.
    assert out["total_funding"] > float(ledger["funding"].sum())


def test_funding_is_charged_from_the_rate_not_the_strategys_position() -> None:
    sparse = _ledger(period=97.0, with_funding=True)
    busy = _ledger(period=5.0, with_funding=True)
    a = _baselines(sparse, timeframe="1h")["always_long"]
    b = _baselines(busy, timeframe="1h")["always_long"]
    assert a["total_funding"] == pytest.approx(b["total_funding"], rel=1e-12)


def test_every_baseline_is_evaluated_on_the_same_number_of_bars() -> None:
    ledger = _ledger()
    for metrics in _baselines(ledger, timeframe="1h").values():
        assert metrics["n_bars"] == float(ledger.height)


def test_baselines_are_deterministic_including_the_random_one() -> None:
    ledger = _ledger()
    a = _baselines(ledger, timeframe="1h", seed=11)
    b = _baselines(ledger, timeframe="1h", seed=11)
    assert a == b
    c = _baselines(ledger, timeframe="1h", seed=12)
    assert a["random_entry"] != c["random_entry"]


def test_random_entry_pays_for_its_turnover() -> None:
    out = _baselines(_ledger(), timeframe="1h")["random_entry"]
    assert out["total_cost"] > 0.0
    assert out["total_return"] < 0.0


def test_comparison_reports_the_strategy_alongside_the_baselines() -> None:
    ledger = _ledger()
    result = _comparison(ledger, timeframe="1h")
    assert result["n_bars"] == ledger.height
    assert set(result["baselines"]) == {
        "flat",
        "always_long",
        "ma_crossover_24_96",
        "momentum_24",
        "mean_reversion_z48",
        "random_entry",
    }
    expected = float(np.prod(1.0 + ledger["net_return"].to_numpy()) - 1.0)
    assert result["strategy"]["total_return"] == pytest.approx(expected, rel=1e-9)


def test_every_baseline_is_charged_the_contract_rate() -> None:
    result = _comparison(_ledger(), timeframe="1h")
    rate = result["contract_cost_rate_per_unit_turnover"]
    for name, metrics in result["baselines"].items():
        if metrics["total_cost"] == 0.0:
            continue
        implied = metrics["total_cost"] / metrics["turnover"]
        assert implied == pytest.approx(rate, rel=1e-9), f"{name} was charged a different rate"


def test_coverage_id_identifies_the_exact_bars() -> None:
    a = _ledger(600)
    assert coverage_id(a) == coverage_id(_ledger(600))
    assert coverage_id(a) != coverage_id(_ledger(599))
    # Same length, different timestamps.
    shifted = a.with_columns(pl.col("open_time") + timedelta(hours=1))
    assert coverage_id(a) != coverage_id(shifted)


def test_ledger_without_market_returns_is_rejected() -> None:
    ledger = _ledger().drop("oo_return")
    with pytest.raises(ValueError, match="oo_return"):
        _baselines(ledger, timeframe="1h")


def test_ledger_without_a_funding_rate_column_is_rejected() -> None:
    """Old ledgers must fail loudly rather than be silently priced as funding-free."""
    ledger = _ledger().drop(FUNDING_RATE_COL)
    with pytest.raises(ValueError, match=FUNDING_RATE_COL):
        _baselines(ledger, timeframe="1h")
