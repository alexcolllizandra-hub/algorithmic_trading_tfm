"""Tests for the out-of-sample robustness battery.

The battery must reproduce the original run exactly at neutral settings, degrade
monotonically as costs rise, and never fabricate a ledger it was not given.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.backtesting.engine import run_backtest
from perp_lab.evaluation.robustness import (
    RobustnessBattery,
    block_bootstrap_ci,
    concentration_analysis,
    drop_best_trades,
    reconstruct_bar_returns,
    stress_costs,
    stress_execution_delay,
)


def _run(n: int = 400) -> pl.DataFrame:
    """A backtest over a deterministic oscillating price path."""
    t0 = datetime(2021, 1, 1, tzinfo=UTC)
    times = [t0 + timedelta(hours=i) for i in range(n)]
    price = [100.0 * (1.0 + 0.05 * np.sin(i / 7.0)) for i in range(n)]
    prices = pl.DataFrame({"open_time": times, "open": price})
    sides = [1 if np.sin(i / 11.0) > 0 else -1 for i in range(n)]
    signals = pl.DataFrame({"open_time": times, "side": sides})
    return run_backtest(
        signals, prices, timeframe="1h", fee_bps_per_side=4.0, slippage_bps_per_side=1.0
    ).ledger


def test_neutral_cost_stress_reproduces_the_original_net_returns() -> None:
    """A 1x multiplier must be an identity, otherwise every stressed number is suspect."""
    ledger = _run()
    report = stress_costs(ledger, timeframe="1h", fee_multiplier=1.0, slippage_multiplier=1.0)
    original = ledger["net_return"].to_numpy()
    recomputed = (
        ledger["gross_return"].to_numpy()
        - ledger["fee"].to_numpy()
        - ledger["slippage"].to_numpy()
        - ledger["funding"].to_numpy()
    )
    assert np.allclose(original, recomputed)
    assert report.metrics["total_return"] == pytest.approx(
        float(np.prod(1.0 + original) - 1.0), rel=1e-9
    )


def test_higher_costs_never_improve_the_result() -> None:
    ledger = _run()
    totals = [
        stress_costs(ledger, timeframe="1h", fee_multiplier=m, slippage_multiplier=m).metrics[
            "total_return"
        ]
        for m in (1.0, 1.5, 2.0, 3.0)
    ]
    assert totals == sorted(totals, reverse=True)


def test_reconstructed_bar_returns_match_the_backtester() -> None:
    """gross_return / position must equal the reconstructed open-to-open return."""
    ledger = _run()
    market = reconstruct_bar_returns(ledger)
    pos = ledger["position"].to_numpy()
    gross = ledger["gross_return"].to_numpy()
    live = pos != 0
    assert np.allclose(gross[live], (pos * market)[live], atol=1e-12)


def test_execution_delay_shifts_exposure_and_costs_nothing_extra_at_zero() -> None:
    ledger = _run()
    zero = stress_execution_delay(ledger, timeframe="1h", delay_bars=0)
    assert zero.metrics["total_return"] == pytest.approx(
        float(np.prod(1.0 + ledger["net_return"].to_numpy()) - 1.0), rel=1e-6
    )


def test_execution_delay_rejects_negative_delay() -> None:
    with pytest.raises(ValueError, match="delay_bars"):
        stress_execution_delay(_run(), timeframe="1h", delay_bars=-1)


def test_execution_delay_changes_the_result() -> None:
    ledger = _run()
    base = stress_execution_delay(ledger, timeframe="1h", delay_bars=0).metrics["total_return"]
    late = stress_execution_delay(ledger, timeframe="1h", delay_bars=2).metrics["total_return"]
    assert base != pytest.approx(late)


def test_battery_requires_a_complete_ledger() -> None:
    ledger = _run().drop("slippage")
    with pytest.raises(ValueError, match="missing columns"):
        stress_costs(ledger, timeframe="1h")


def test_block_bootstrap_is_deterministic_and_brackets_the_estimate() -> None:
    rng = np.random.default_rng(0)
    r = rng.normal(0.0005, 0.01, size=2000)
    stat = lambda x: float(x.mean())  # noqa: E731
    a = block_bootstrap_ci(r, stat, block_size=24, n_resamples=300, seed=1)
    b = block_bootstrap_ci(r, stat, block_size=24, n_resamples=300, seed=1)
    assert a == b
    assert a["ci_low"] < a["point_estimate"] < a["ci_high"]


def test_block_bootstrap_widens_with_larger_blocks_on_dependent_data() -> None:
    """Serial dependence must not be washed out; bigger blocks preserve more of it."""
    rng = np.random.default_rng(0)
    noise = rng.normal(0.0, 0.01, size=4000)
    r = np.zeros_like(noise)
    for i in range(1, r.size):  # strongly autocorrelated series
        r[i] = 0.9 * r[i - 1] + noise[i]
    stat = lambda x: float(x.mean())  # noqa: E731
    small = block_bootstrap_ci(r, stat, block_size=1, n_resamples=400, seed=3)
    large = block_bootstrap_ci(r, stat, block_size=200, n_resamples=400, seed=3)
    assert large["bootstrap_std"] > small["bootstrap_std"]


def test_block_bootstrap_handles_empty_input() -> None:
    assert block_bootstrap_ci(np.array([]), lambda x: float(x.mean()), block_size=10) == {}


def test_dropping_best_trades_lowers_the_total() -> None:
    trades = np.array([0.5, 0.01, -0.02, 0.03, -0.01, 0.02])
    out = drop_best_trades(trades, k=1)
    assert out["k_removed"] == 1.0
    assert out["total_return_without_best"] < out["total_return_all"]
    assert out["n_trades_kept"] == 5.0


def test_dropping_more_trades_than_exist_is_clamped() -> None:
    out = drop_best_trades(np.array([0.1, 0.2]), k=99)
    assert out["n_trades_kept"] == 0.0


def test_concentration_flags_a_single_dominant_trade() -> None:
    trades = np.array([1.0] + [0.001] * 50)
    out = concentration_analysis(trades)
    assert out["top1_profit_share"] > 0.9
    assert out["n_trades"] == 51.0


def test_battery_produces_one_report_per_scenario() -> None:
    ledger = _run()
    battery = RobustnessBattery(ledger=ledger, timeframe="1h")
    reports = battery.run(cost_multipliers=(1.0, 2.0), slippage_multipliers=(1.0, 5.0), delays=(1,))
    scenarios = [r.scenario for r in reports]
    assert scenarios.count("cost_stress") == 3  # 2 cost multipliers + 1 slippage-only
    assert scenarios.count("execution_delay") == 1
    assert all(isinstance(r.to_dict(), dict) for r in reports)
