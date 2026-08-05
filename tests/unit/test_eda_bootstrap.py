"""Tests for the moving-block bootstrap confidence intervals."""

from __future__ import annotations

import numpy as np

from perp_lab.eda.bootstrap import (
    bootstrap_ci,
    bootstrap_diff_ci,
    mean_stat,
    median_stat,
    moving_block_bootstrap,
    sharpe_stat,
    vol_stat,
)


def test_point_statistics_match_numpy() -> None:
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert mean_stat(x) == 3.0
    assert median_stat(x) == 3.0
    assert vol_stat(x) == float(np.std(x, ddof=1))


def test_sharpe_stat_zero_variance_is_nan() -> None:
    x = np.full(50, 0.01)
    assert np.isnan(sharpe_stat(8760)(x))


def test_moving_block_bootstrap_is_deterministic_and_sized() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=500)
    a = moving_block_bootstrap(x, mean_stat, block=24, n_boot=200, seed=7)
    b = moving_block_bootstrap(x, mean_stat, block=24, n_boot=200, seed=7)
    assert a.size == 200
    assert np.array_equal(a, b)  # same seed -> identical resamples
    c = moving_block_bootstrap(x, mean_stat, block=24, n_boot=200, seed=8)
    assert not np.array_equal(a, c)  # different seed -> different resamples


def test_bootstrap_ci_brackets_estimate() -> None:
    rng = np.random.default_rng(1)
    x = rng.normal(loc=0.5, scale=1.0, size=1000)
    ci = bootstrap_ci(x, mean_stat, block=24, n_boot=400, seed=3)
    assert ci["ci_low"] < ci["estimate"] < ci["ci_high"]
    assert ci["estimate"] == float(np.mean(x))
    assert ci["n"] == 1000.0


def test_bootstrap_ci_empty_when_series_too_short() -> None:
    assert bootstrap_ci(np.arange(10.0), mean_stat, block=24) == {}


def test_bootstrap_ci_drops_non_finite() -> None:
    x = np.concatenate([np.full(300, 0.1), [np.nan, np.inf]])
    ci = bootstrap_ci(x, mean_stat, block=12, n_boot=100, seed=2)
    assert ci["n"] == 300.0


def test_bootstrap_diff_ci_detects_positive_difference() -> None:
    rng = np.random.default_rng(4)
    a = rng.normal(loc=1.0, scale=0.5, size=800)  # clearly larger mean
    b = rng.normal(loc=0.0, scale=0.5, size=800)
    res = bootstrap_diff_ci(a, b, mean_stat, block=24, n_boot=400, seed=5)
    assert res["estimate"] > 0.0
    assert 0.0 <= res["prob_positive"] <= 1.0
    assert res["prob_positive"] > 0.9  # difference positive in most resamples
    assert res["ci_low"] < res["estimate"] < res["ci_high"]


def test_bootstrap_diff_ci_empty_when_short() -> None:
    assert bootstrap_diff_ci(np.arange(10.0), np.arange(10.0), mean_stat, block=24) == {}
