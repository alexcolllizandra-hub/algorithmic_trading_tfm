"""Pandera (Polars) schemas for structural validation.

These enforce column presence, dtypes and simple per-column ranges. Richer,
cross-column and temporal checks (OHLC consistency, gaps, duplicates, extreme
moves) live in :mod:`perp_lab.validation.quality` because they produce a
report rather than a pass/fail assertion.
"""

from __future__ import annotations

import pandera.polars as pa
import polars as pl

_UTC_MS = pl.Datetime(time_unit="ms", time_zone="UTC")

KLINE_SCHEMA = pa.DataFrameSchema(
    {
        "open_time": pa.Column(_UTC_MS),
        "open": pa.Column(pl.Float64, pa.Check.gt(0)),
        "high": pa.Column(pl.Float64, pa.Check.gt(0)),
        "low": pa.Column(pl.Float64, pa.Check.gt(0)),
        "close": pa.Column(pl.Float64, pa.Check.gt(0)),
        "volume": pa.Column(pl.Float64, pa.Check.ge(0)),
        "quote_volume": pa.Column(pl.Float64, pa.Check.ge(0), nullable=True),
        "trade_count": pa.Column(pl.Int64, pa.Check.ge(0), nullable=True),
        "taker_buy_base": pa.Column(pl.Float64, pa.Check.ge(0), nullable=True),
        "taker_buy_quote": pa.Column(pl.Float64, pa.Check.ge(0), nullable=True),
    },
    strict=True,
    ordered=False,
)

FUNDING_SCHEMA = pa.DataFrameSchema(
    {
        "funding_time": pa.Column(_UTC_MS),
        "funding_interval_hours": pa.Column(pl.Int64, pa.Check.gt(0), nullable=True),
        "funding_rate": pa.Column(pl.Float64),
    },
    strict=True,
    ordered=False,
)


def validate_klines(df: pl.DataFrame) -> pl.DataFrame:
    """Structurally validate klines; raises ``pandera.errors.SchemaError``."""
    return KLINE_SCHEMA.validate(df)


def validate_funding(df: pl.DataFrame) -> pl.DataFrame:
    """Structurally validate funding data; raises on failure."""
    return FUNDING_SCHEMA.validate(df)
