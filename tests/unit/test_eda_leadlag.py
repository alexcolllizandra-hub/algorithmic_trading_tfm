"""Cross-correlation and tail co-exceedance tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.eda.leadlag import cross_correlation, peak_lag, tail_coexceedance


def _returns(values: list[float]) -> pl.DataFrame:
    start = datetime(2021, 1, 1, tzinfo=UTC)
    times = [start + timedelta(minutes=5 * i) for i in range(len(values))]
    return pl.DataFrame({"open_time": times, "log_return": values}).with_columns(
        pl.col("open_time").cast(pl.Datetime("ms", "UTC"))
    )


def test_identical_series_peaks_at_lag_zero():
    rng = np.random.default_rng(0)
    vals = rng.normal(0, 1, 500).tolist()
    df = _returns(vals)
    cc = cross_correlation(df, df, max_lag=5)
    # Lag 0 correlation of a series with itself is 1.
    lag0 = cc.filter(pl.col("lag") == 0)["cross_corr"].item()
    assert lag0 == pytest.approx(1.0, abs=1e-9)
    assert peak_lag(cc)["lag"] == 0.0


def test_lagged_series_detects_lead():
    rng = np.random.default_rng(1)
    base = rng.normal(0, 1, 600)
    # Convention: lag k>0 correlates left[t] with right[t-k]. Make right the
    # leader and left a one-step-delayed copy (left[t] = right[t-1]); the peak
    # then sits at lag +1.
    right = _returns(base.tolist())
    left_vals = np.concatenate([[0.0], base[:-1]]).tolist()
    left = _returns(left_vals)
    cc = cross_correlation(left, right, max_lag=5)
    assert peak_lag(cc)["lag"] == 1.0


def test_cross_correlation_too_short_returns_empty():
    df = _returns([0.1, -0.2])
    assert cross_correlation(df, df, max_lag=3).height == 0


def test_tail_coexceedance_perfect_dependence():
    rng = np.random.default_rng(2)
    vals = rng.normal(0, 1, 1000).tolist()
    df = _returns(vals)
    out = tail_coexceedance(df, df, quantile=0.05)
    # Identical series => whenever one is in the tail, so is the other.
    assert out["lower_exceedance_ratio"] == pytest.approx(1.0 / 0.05, rel=0.15)
    assert out["upper_exceedance_ratio"] == pytest.approx(1.0 / 0.05, rel=0.15)
