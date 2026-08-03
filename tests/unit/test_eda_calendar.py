"""Monthly calendar aggregates."""

from __future__ import annotations

from datetime import datetime

import polars as pl
import pytest

from perp_lab.eda.calendar import monthly_returns, monthly_volatility, to_year_month_matrix


def _two_months() -> pl.DataFrame:
    # Jan: two +ln(1.1) steps; Feb: two -ln(1.1) steps.
    import math

    up = math.log(1.1)
    times = [datetime(2021, 1, 1), datetime(2021, 1, 2), datetime(2021, 2, 1), datetime(2021, 2, 2)]
    return pl.DataFrame(
        {
            "open_time": pl.Series(times, dtype=pl.Datetime("ms", "UTC")),
            "log_return": [up, up, -up, -up],
        }
    )


def test_monthly_returns_compound_correctly():
    mr = monthly_returns(_two_months())
    jan = mr.filter(pl.col("month") == 1).row(0, named=True)
    feb = mr.filter(pl.col("month") == 2).row(0, named=True)
    # exp(2*ln1.1)-1 = 1.21-1 = 21%; exp(-2*ln1.1)-1 = 1/1.21-1 ~ -17.36%.
    assert jan["return_pct"] == pytest.approx(21.0, abs=1e-6)
    assert feb["return_pct"] == pytest.approx((1 / 1.21 - 1) * 100, abs=1e-6)


def test_monthly_volatility_and_matrix():
    mv = monthly_volatility(_two_months(), timeframe="1h")
    assert mv.height == 2
    mat, years = to_year_month_matrix(mv, "ann_vol")
    assert years == [2021]
    assert mat.shape == (1, 12)
