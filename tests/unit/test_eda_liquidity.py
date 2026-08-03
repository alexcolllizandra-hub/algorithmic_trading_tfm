"""Liquidity/activity proxy calculations."""

from __future__ import annotations

from datetime import datetime, timedelta

import polars as pl
import pytest

from perp_lab.eda.liquidity import add_liquidity_proxies, zero_return_fraction


def _ohlcv(n: int = 30) -> pl.DataFrame:
    times = [datetime(2021, 1, 1) + timedelta(hours=h) for h in range(n)]
    close = [100.0 + i for i in range(n)]
    return pl.DataFrame(
        {
            "open_time": pl.Series(times, dtype=pl.Datetime("ms", "UTC")),
            "open": close,
            "high": [c + 2 for c in close],
            "low": [c - 2 for c in close],
            "close": close,
            "volume": [10.0] * n,
            "quote_volume": [1000.0 * (i + 1) for i in range(n)],
            "trade_count": [100] * n,
            "taker_buy_base": [6.0] * n,
            "taker_buy_quote": [600.0] * n,
        }
    ).with_columns((pl.col("close").log() - pl.col("close").log().shift(1)).alias("log_return"))


def test_liquidity_proxy_columns_and_values():
    out = add_liquidity_proxies(_ohlcv(), window=5)
    assert {
        "dollar_volume",
        "log_dollar_volume",
        "rel_volume",
        "hl_range",
        "atr_over_price",
        "amihud_illiq",
        "taker_buy_ratio",
    } <= set(out.columns)
    # taker_buy_ratio = 6/10 = 0.6 everywhere.
    assert out["taker_buy_ratio"].drop_nulls().to_list()[0] == pytest.approx(0.6)
    # hl_range = (high-low)/close = 4/close; at first bar close=100 -> 0.04.
    assert out["hl_range"][0] == pytest.approx(4.0 / 100.0)
    # dollar_volume equals quote_volume.
    assert out["dollar_volume"][0] == pytest.approx(1000.0)


def test_zero_return_fraction():
    df = pl.DataFrame({"log_return": [0.0, 0.0, 0.1, -0.1, None]})
    # Non-null returns: [0,0,0.1,-0.1] -> 2/4 zero.
    assert zero_return_fraction(df) == pytest.approx(0.5)
