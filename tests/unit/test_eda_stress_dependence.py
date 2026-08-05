"""Tests for extreme-tail dependence diagnostics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.eda.stress_dependence import (
    coexceedance_summary,
    conditional_exceedance,
    normal_vs_stress_correlation,
    rolling_tail_dependence,
)


def _pair(a: np.ndarray, b: np.ndarray) -> tuple[pl.DataFrame, pl.DataFrame]:
    t0 = datetime(2021, 1, 1, tzinfo=UTC)
    times = [t0 + timedelta(hours=i) for i in range(a.size)]
    left = pl.DataFrame({"open_time": times, "log_return": a})
    right = pl.DataFrame({"open_time": times, "log_return": b})
    return left, right


def test_conditional_exceedance_comonotonic() -> None:
    rng = np.random.default_rng(0)
    a = rng.normal(size=1000)
    left, right = _pair(a, a.copy())  # identical series -> perfect tail co-movement
    res = conditional_exceedance(left, right, quantile=0.05, tail="lower")
    assert res["p_right_given_left"] == pytest.approx(1.0)
    assert res["p_left_given_right"] == pytest.approx(1.0)
    assert res["lift"] > 1.0  # far above independence


def test_conditional_exceedance_upper_tail() -> None:
    rng = np.random.default_rng(1)
    a = rng.normal(size=800)
    left, right = _pair(a, a.copy())
    res = conditional_exceedance(left, right, quantile=0.05, tail="upper")
    assert res["p_right_given_left"] == pytest.approx(1.0)


def test_conditional_exceedance_invalid_tail() -> None:
    left, right = _pair(np.zeros(50), np.zeros(50))
    with pytest.raises(ValueError, match="tail"):
        conditional_exceedance(left, right, tail="sideways")


def test_conditional_exceedance_empty_when_short() -> None:
    left, right = _pair(np.zeros(5), np.zeros(5))
    assert conditional_exceedance(left, right) == {}


def test_coexceedance_summary_columns_and_ratio() -> None:
    rng = np.random.default_rng(2)
    a = rng.normal(size=2000)
    left, right = _pair(a, a.copy())
    table = coexceedance_summary(left, right, quantiles=(0.05, 0.01))
    assert table.height == 2
    assert set(table.columns) == {
        "quantile",
        "n",
        "joint_lower",
        "joint_upper",
        "lower_ratio",
        "upper_ratio",
        "p_right_given_left_lower",
        "p_left_given_right_lower",
    }
    # Identical series: joint lower ~= quantile, so ratio ~= 1/quantile >> 1.
    row = table.filter(pl.col("quantile") == 0.05).row(0, named=True)
    assert row["lower_ratio"] > 10.0
    assert row["p_right_given_left_lower"] == pytest.approx(1.0, abs=0.05)


def test_normal_vs_stress_correlation_keys_and_bounds() -> None:
    rng = np.random.default_rng(3)
    a = rng.normal(size=1000)
    b = 0.5 * a + rng.normal(size=1000) * 0.5
    left, right = _pair(a, b)
    res = normal_vs_stress_correlation(left, right, stress_quantile=0.10)
    for key in ("corr_all", "corr_calm", "corr_stress", "corr_stress_left"):
        assert -1.0 <= res[key] <= 1.0
    assert res["n_stress"] + res["n_calm"] == res["n_all"]


def test_rolling_tail_dependence_windows() -> None:
    rng = np.random.default_rng(4)
    a = rng.normal(size=1000)
    left, right = _pair(a, a.copy())
    out = rolling_tail_dependence(left, right, window=200, step=100, quantile=0.05)
    assert out.height >= 1
    assert set(out.columns) == {"window_end", "n", "joint_lower", "lower_ratio"}
    assert (out["lower_ratio"] > 1.0).all()  # identical series co-exceed strongly


def test_rolling_tail_dependence_empty_when_short() -> None:
    left, right = _pair(np.zeros(50), np.zeros(50))
    out = rolling_tail_dependence(left, right, window=200, step=100)
    assert out.height == 0
