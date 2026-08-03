"""Funding alignment (leak-free) and dynamics tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from perp_lab.eda.funding import attach_funding, basis_summary, funding_dynamics


def _bars(n: int, start: datetime) -> pl.DataFrame:
    times = [start + timedelta(hours=i) for i in range(n)]
    return pl.DataFrame({"open_time": times, "close": [100.0 + i for i in range(n)]}).with_columns(
        pl.col("open_time").cast(pl.Datetime("ms", "UTC"))
    )


def test_attach_funding_is_backward_and_leak_free():
    start = datetime(2021, 1, 1, tzinfo=UTC)
    bars = _bars(5, start)  # hourly bars t0..t4
    funding = pl.DataFrame(
        {
            "funding_time": [start + timedelta(hours=1), start + timedelta(hours=3)],
            "funding_rate": [0.001, -0.002],
        }
    ).with_columns(pl.col("funding_time").cast(pl.Datetime("ms", "UTC")))

    out = attach_funding(bars, funding)
    rates = out["funding_rate"].to_list()
    # t0: no funding yet -> null; t1,t2 -> 0.001; t3,t4 -> -0.002.
    assert rates[0] is None
    assert rates[1] == pytest.approx(0.001)
    assert rates[2] == pytest.approx(0.001)
    assert rates[3] == pytest.approx(-0.002)
    assert rates[4] == pytest.approx(-0.002)


def test_attach_funding_tolerance_blocks_stale():
    start = datetime(2021, 1, 1, tzinfo=UTC)
    bars = _bars(5, start)
    funding = pl.DataFrame(
        {"funding_time": [start + timedelta(hours=1)], "funding_rate": [0.001]}
    ).with_columns(pl.col("funding_time").cast(pl.Datetime("ms", "UTC")))
    out = attach_funding(bars, funding, tolerance="1h")
    rates = out["funding_rate"].to_list()
    # Only t1 (exact) and t2 (within 1h) keep the value; t3, t4 are too stale.
    assert rates[1] == pytest.approx(0.001)
    assert rates[2] == pytest.approx(0.001)
    assert rates[3] is None
    assert rates[4] is None


def test_funding_dynamics_signs_and_persistence():
    funding = pl.DataFrame({"funding_rate": [0.01, 0.01, -0.01, 0.02]})
    d = funding_dynamics(funding)
    assert d["share_positive"] == pytest.approx(0.75)
    assert d["share_negative"] == pytest.approx(0.25)
    # Sign sequence + + - + has two sign changes across three transitions.
    assert d["sign_change_freq"] == pytest.approx(2.0 / 3.0)


def test_basis_summary_zero_when_prices_match():
    start = datetime(2021, 1, 1, tzinfo=UTC)
    bars = _bars(10, start)
    out = basis_summary(bars, bars)
    assert out["mean_bps"] == pytest.approx(0.0)
