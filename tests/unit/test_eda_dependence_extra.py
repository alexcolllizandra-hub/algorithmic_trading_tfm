"""Extended cross-asset dependence: Spearman, conditional, bootstrap CI."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.eda.correlation import (
    block_bootstrap_corr_ci,
    correlation_by_sign,
    correlation_by_vol_regime,
    spearman_correlation,
)


def _pair(a: list[float], b: list[float]) -> tuple[pl.DataFrame, pl.DataFrame]:
    n = len(a)
    base = datetime(2021, 1, 1)
    times = pl.Series(
        [base + timedelta(minutes=i) for i in range(n)], dtype=pl.Datetime("ms", "UTC")
    )
    left = pl.DataFrame({"open_time": times, "log_return": a})
    right = pl.DataFrame({"open_time": times, "log_return": b})
    return left, right


def test_spearman_identical_is_one():
    a = [0.1, -0.2, 0.3, -0.4, 0.5, 0.05]
    left, right = _pair(a, a)
    assert spearman_correlation(left, right) == pytest.approx(1.0)


def test_block_bootstrap_ci_brackets_point_estimate():
    rng = np.random.default_rng(0)
    a = list(rng.standard_normal(400))
    b = list(np.array(a) + rng.standard_normal(400) * 0.01)  # near-perfect corr
    left, right = _pair(a, b)
    out = block_bootstrap_corr_ci(left, right, block=10, n_boot=200)
    assert out["corr"] > 0.95
    assert out["ci_low"] <= out["corr"] <= out["ci_high"]


def test_correlation_by_sign_returns_two_conditions():
    rng = np.random.default_rng(1)
    a = list(rng.standard_normal(200))
    b = list(rng.standard_normal(200))
    left, right = _pair(a, b)
    out = correlation_by_sign(left, right)
    assert set(out["condition"].to_list()) == {"left_positive", "left_negative"}


def test_correlation_by_vol_regime_has_three_buckets():
    rng = np.random.default_rng(2)
    a = list(rng.standard_normal(120))
    b = list(rng.standard_normal(120))
    left, right = _pair(a, b)
    out = correlation_by_vol_regime(left, right, vol_window=5)
    assert out["vol_regime"].to_list() == ["low", "medium", "high"]
