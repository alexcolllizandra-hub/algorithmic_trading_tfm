"""Properties the Monte Carlo module must hold, pinned on synthetic ledgers."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from perp_lab.evaluation.montecarlo import (
    PROP_FIRM_PRESETS,
    PropFirmRules,
    bar_net_returns,
    breakeven_multiplier,
    coin_flip_pass_probability,
    cost_multiplier_sweep,
    iid_trade_bootstrap,
    null_circular_shifts,
    path_metrics,
    percentile_of,
    permutation_paths,
    prop_firm_pass_probability,
    stationary_bar_bootstrap,
    suggest_block_length,
)


@pytest.fixture()
def ledger() -> pl.DataFrame:
    rng = np.random.default_rng(7)
    n = 2000
    position = np.zeros(n)
    # Sparse block exposure, like the event families under study.
    for start in range(50, n - 60, 200):
        position[start : start + 30] = 1.0 if (start // 200) % 2 == 0 else -1.0
    oo = rng.normal(0.0, 0.004, size=n)
    turnover = np.abs(np.diff(position, prepend=0.0))
    fee = 0.0004 * turnover
    slippage = 0.0001 * turnover
    funding_rate = rng.normal(0.0, 1e-5, size=n)
    gross = position * oo
    return pl.DataFrame(
        {
            "position": position,
            "oo_return": oo,
            "gross_return": gross,
            "fee": fee,
            "slippage": slippage,
            "funding": position * funding_rate,
            "funding_rate_in_bar": funding_rate,
        }
    )


def test_same_seed_same_distributions(ledger: pl.DataFrame) -> None:
    r = bar_net_returns(ledger)
    a = stationary_bar_bootstrap(r, block_length=24, n_resamples=50, seed=9)
    b = stationary_bar_bootstrap(r, block_length=24, n_resamples=50, seed=9)
    for key in a:
        assert np.array_equal(a[key], b[key])


def test_permutation_keeps_total_return_and_moves_drawdown() -> None:
    trades = np.array([0.05, -0.02, 0.03, -0.04, 0.01, 0.02, -0.01, 0.04])
    real_total = path_metrics(trades)["total_return"]
    perm = permutation_paths(trades, n_resamples=200, seed=3)
    assert np.allclose(perm["total_return"], real_total, atol=1e-12)
    assert perm["max_drawdown"].std() > 0, "sequencing must move the drawdown"


def test_iid_bootstrap_moves_total_return() -> None:
    trades = np.array([0.05, -0.02, 0.03, -0.04, 0.01, 0.02, -0.01, 0.04])
    boot = iid_trade_bootstrap(trades, n_resamples=200, seed=3)
    assert boot["total_return"].std() > 0


def test_null_shifts_preserve_exposure_and_price_costs(ledger: pl.DataFrame) -> None:
    out = null_circular_shifts(ledger, n_shifts=40, seed=11)
    assert out["exposure_share"] == pytest.approx(
        float((ledger["position"].to_numpy() != 0).mean())
    )
    assert 0.0 <= out["real_percentile"]["total_return"] <= 1.0
    assert len(out["null"]["total_return"]) == 40
    # Rotation must not manufacture edge on average: null mean near zero gross.
    assert abs(out["null"]["total_return"].mean()) < 0.2


def test_cost_sweep_is_monotone_and_finds_breakeven(ledger: pl.DataFrame) -> None:
    sweep = cost_multiplier_sweep(ledger, multipliers=(0.0, 1.0, 2.0, 4.0, 8.0))
    totals = sweep.sort("multiplier")["total_return"].to_numpy()
    assert np.all(np.diff(totals) <= 1e-12), "more cost can never help"
    if totals[0] > 0 > totals[-1]:
        be = breakeven_multiplier(sweep)
        assert be is not None and 0.0 < be < 8.0


def test_percentile_of_bounds() -> None:
    d = np.array([1.0, 2.0, 3.0, 4.0])
    assert percentile_of(0.0, d) == 0.0
    assert percentile_of(4.0, d) == 1.0
    assert percentile_of(2.5, d) == 0.5


def test_block_length_suggestion_is_bounded() -> None:
    rng = np.random.default_rng(1)
    iid = rng.normal(size=4000)
    out = suggest_block_length(iid)
    assert 6 <= out["block_length"] <= 168


def test_prop_firm_rules_pass_and_breach() -> None:
    rules = PropFirmRules(
        profit_target=0.05,
        max_total_drawdown=0.10,
        max_daily_loss=0.05,
        max_days=10,
        bars_per_day=4,
    )
    winner = np.full(200, 0.002)
    out = prop_firm_pass_probability(winner, rules=rules, block_length=8, n_paths=30, seed=5)
    assert out["pass_phase1"] == 1.0 and out["pass_both"] == 1.0

    loser = np.full(200, -0.02)
    out = prop_firm_pass_probability(loser, rules=rules, block_length=8, n_paths=30, seed=5)
    assert out["pass_phase1"] == 0.0


def test_presets_carry_source_and_rules() -> None:
    for name, preset in PROP_FIRM_PRESETS.items():
        assert isinstance(preset["rules"], PropFirmRules), name
        assert preset["source"].startswith("https://"), name
        assert preset["retrieved"], name


def test_coin_flip_is_deterministic_and_bounded(ledger: pl.DataFrame) -> None:
    rules = PropFirmRules(
        profit_target=0.02,
        max_total_drawdown=0.10,
        max_daily_loss=0.05,
        max_days=5,
        bars_per_day=4,
    )
    a = coin_flip_pass_probability(ledger, rules=rules, n_paths=60, seed=13)
    b = coin_flip_pass_probability(ledger, rules=rules, n_paths=60, seed=13)
    assert a == b
    assert 0.0 <= a["pass_both"] <= a["pass_phase1"] <= 1.0
