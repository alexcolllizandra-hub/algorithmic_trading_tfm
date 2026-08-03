"""Parkinson and Garman-Klass estimator tests with closed-form values."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from perp_lab.eda.volatility import garman_klass_volatility, parkinson_volatility

_ONE_OVER_4LN2 = 1.0 / (4.0 * math.log(2.0))
_GK_C = 2.0 * math.log(2.0) - 1.0


def _ohlc(n: int, o: float, h: float, low: float, c: float) -> pl.DataFrame:
    start = datetime(2021, 1, 1, tzinfo=UTC)
    times = [start + timedelta(minutes=5 * i) for i in range(n)]
    return pl.DataFrame(
        {
            "open_time": times,
            "open": [o] * n,
            "high": [h] * n,
            "low": [low] * n,
            "close": [c] * n,
        }
    ).with_columns(pl.col("open_time").cast(pl.Datetime("ms", "UTC")))


def test_parkinson_constant_range_matches_formula():
    df = _ohlc(4, o=100.0, h=110.0, low=100.0, c=105.0)
    out = parkinson_volatility(df, window=2)
    expected = math.sqrt(_ONE_OVER_4LN2 * math.log(110.0 / 100.0) ** 2)
    # First bar lacks a full window; subsequent bars equal the constant value.
    assert out["parkinson_vol_2"].to_list()[-1] == pytest.approx(expected)


def test_garman_klass_open_equals_close_matches_formula():
    df = _ohlc(4, o=100.0, h=110.0, low=100.0, c=100.0)  # close == open => co term 0
    out = garman_klass_volatility(df, window=2)
    expected = math.sqrt(0.5 * math.log(110.0 / 100.0) ** 2)
    assert out["garman_klass_vol_2"].to_list()[-1] == pytest.approx(expected)


def test_garman_klass_uses_gk_constant():
    # Sanity check that the OC term is subtracted with the GK constant.
    df = _ohlc(3, o=100.0, h=110.0, low=90.0, c=105.0)
    out = garman_klass_volatility(df, window=2)
    hl = math.log(110.0 / 90.0) ** 2
    co = math.log(105.0 / 100.0) ** 2
    expected = math.sqrt(max(0.0, 0.5 * hl - _GK_C * co))
    assert out["garman_klass_vol_2"].to_list()[-1] == pytest.approx(expected)
