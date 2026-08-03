"""Rolling distribution moments against hand-computed values."""

from __future__ import annotations

from datetime import datetime

import polars as pl
import pytest

from perp_lab.eda.rolling import rolling_moments


def _frame(returns: list[float]) -> pl.DataFrame:
    times = [datetime(2021, 1, 1, h) for h in range(len(returns))]
    return pl.DataFrame(
        {"open_time": pl.Series(times, dtype=pl.Datetime("ms", "UTC")), "log_return": returns}
    )


def test_rolling_moments_window_three():
    # Window [1,2,3]: pop std = sqrt(2/3); skew = 0; excess kurtosis = -1.5.
    df = _frame([1.0, 2.0, 3.0, 4.0, 5.0])
    out = rolling_moments(df, window=3)
    first = out.filter(pl.col("rolling_vol").is_not_null()).row(0, named=True)
    assert first["rolling_vol"] == pytest.approx((2 / 3) ** 0.5, rel=1e-9)
    assert first["rolling_skew"] == pytest.approx(0.0, abs=1e-9)
    assert first["rolling_kurt"] == pytest.approx(-1.5, rel=1e-9)


def test_rolling_moments_annualised_scales_vol():
    df = _frame([0.01, -0.01, 0.02, -0.02, 0.015, -0.015])
    plain = rolling_moments(df, window=3)
    ann = rolling_moments(df, window=3, timeframe="1h")
    p = plain.filter(pl.col("rolling_vol").is_not_null())["rolling_vol"][0]
    a = ann.filter(pl.col("rolling_vol").is_not_null())["rolling_vol"][0]
    assert a > p  # annualisation factor for 1h is sqrt(365*24) >> 1
