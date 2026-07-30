"""Shared test fixtures: deterministic synthetic klines."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.data.providers.base import KLINE_SCHEMA
from perp_lab.utils.timeutils import TIMEFRAME_TO_MS

KlineFactory = Callable[..., pl.DataFrame]


def _make_klines(
    n: int = 288,
    start: datetime = datetime(2021, 1, 1, tzinfo=UTC),
    timeframe: str = "5m",
    seed: int = 0,
) -> pl.DataFrame:
    step = TIMEFRAME_TO_MS[timeframe]
    times = [start + timedelta(milliseconds=step * i) for i in range(n)]
    rng = np.random.default_rng(seed)

    close = np.abs(100 + np.cumsum(rng.normal(0, 1, n))) + 1.0
    open_ = np.concatenate([[close[0]], close[:-1]])
    high = np.maximum(open_, close) + rng.random(n)
    low = np.clip(np.minimum(open_, close) - rng.random(n), 0.01, None)
    volume = rng.random(n) * 10 + 1.0

    df = pl.DataFrame(
        {
            "open_time": times,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "quote_volume": volume * close,
            "trade_count": (volume * 10).astype(np.int64),
            "taker_buy_base": volume / 2,
            "taker_buy_quote": (volume * close) / 2,
        }
    )
    return df.select(
        pl.col("open_time").cast(pl.Datetime("ms", "UTC")),
        pl.col("open").cast(pl.Float64),
        pl.col("high").cast(pl.Float64),
        pl.col("low").cast(pl.Float64),
        pl.col("close").cast(pl.Float64),
        pl.col("volume").cast(pl.Float64),
        pl.col("quote_volume").cast(pl.Float64),
        pl.col("trade_count").cast(pl.Int64),
        pl.col("taker_buy_base").cast(pl.Float64),
        pl.col("taker_buy_quote").cast(pl.Float64),
    ).select(list(KLINE_SCHEMA.keys()))


@pytest.fixture
def make_klines() -> KlineFactory:
    """Return a factory producing deterministic synthetic klines."""
    return _make_klines


@pytest.fixture
def klines_5m() -> pl.DataFrame:
    """One day of 5-minute klines (288 bars) starting 2021-01-01 UTC."""
    return _make_klines(n=288)
