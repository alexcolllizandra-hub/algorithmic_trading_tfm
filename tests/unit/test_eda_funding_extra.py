"""Funding runs, autocorrelation and leak-free future-return relation."""

from __future__ import annotations

from datetime import datetime, timedelta

import polars as pl
import pytest

from perp_lab.eda.funding import (
    funding_autocorr,
    funding_future_return_relation,
    funding_sign_runs,
)


def _funding(rates: list[float]) -> pl.DataFrame:
    base = datetime(2021, 1, 1)
    times = pl.Series(
        [base + timedelta(hours=8 * i) for i in range(len(rates))], dtype=pl.Datetime("ms", "UTC")
    )
    return pl.DataFrame(
        {"funding_time": times, "funding_interval_hours": [8.0] * len(rates), "funding_rate": rates}
    )


def test_sign_runs_lengths():
    # +, +, -, -, -, + -> positive runs {2,1}; negative run {3}.
    runs = funding_sign_runs(_funding([1e-4, 2e-4, -1e-4, -2e-4, -3e-4, 1e-4]))
    pos = runs.filter(pl.col("sign") == "positive").row(0, named=True)
    neg = runs.filter(pl.col("sign") == "negative").row(0, named=True)
    assert pos["n_runs"] == 2
    assert pos["mean_len"] == pytest.approx(1.5)
    assert neg["n_runs"] == 1
    assert neg["max_len"] == 3


def test_autocorr_keys():
    out = funding_autocorr(_funding([1e-4, 2e-4, 1.5e-4, 1.2e-4, 1.8e-4, 1.1e-4]), lags=(1, 3))
    assert set(out) == {"acf_lag1", "acf_lag3"}


def test_future_return_relation_is_leak_free():
    base = datetime(2021, 1, 1)
    n = 50
    bars = pl.DataFrame(
        {
            "open_time": pl.Series(
                [base + timedelta(hours=i) for i in range(n)], dtype=pl.Datetime("ms", "UTC")
            ),
            "close": [100.0 + i for i in range(n)],
        }
    )
    funding = _funding([1e-4] * 12)
    rel = funding_future_return_relation(bars, funding, horizons=(1, 3))
    # For horizon h, forward returns exist for at most n-h rows.
    for r in rel.iter_rows(named=True):
        assert r["n"] <= n - r["horizon_bars"]
