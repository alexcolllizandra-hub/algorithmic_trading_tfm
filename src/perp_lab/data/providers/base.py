"""Provider interface and canonical dataframe schemas.

Every provider returns Polars DataFrames with the same canonical schema so the
rest of the pipeline is agnostic to the data source. Timestamps are tz-aware
UTC and label the **open** of each bar.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

import polars as pl

# Canonical kline schema (also used for mark-price klines).
# Values may be dtype instances (e.g. Datetime) or dtype classes (e.g. Float64).
SchemaDict = dict[str, "pl.DataType | type[pl.DataType]"]

KLINE_SCHEMA: SchemaDict = {
    "open_time": pl.Datetime("ms", "UTC"),
    "open": pl.Float64,
    "high": pl.Float64,
    "low": pl.Float64,
    "close": pl.Float64,
    "volume": pl.Float64,
    "quote_volume": pl.Float64,
    "trade_count": pl.Int64,
    "taker_buy_base": pl.Float64,
    "taker_buy_quote": pl.Float64,
}

# Canonical funding-rate schema.
FUNDING_SCHEMA: SchemaDict = {
    "funding_time": pl.Datetime("ms", "UTC"),
    "funding_interval_hours": pl.Int64,
    "funding_rate": pl.Float64,
}

KLINE_COLUMNS: tuple[str, ...] = tuple(KLINE_SCHEMA.keys())
FUNDING_COLUMNS: tuple[str, ...] = tuple(FUNDING_SCHEMA.keys())


def empty_klines() -> pl.DataFrame:
    """Return an empty dataframe with the canonical kline schema."""
    return pl.DataFrame(schema=KLINE_SCHEMA)


def empty_funding() -> pl.DataFrame:
    """Return an empty dataframe with the canonical funding schema."""
    return pl.DataFrame(schema=FUNDING_SCHEMA)


class ExchangeDataProvider(ABC):
    """Abstract source of perpetual-futures market data.

    Implementations must return canonical, UTC-indexed, de-duplicated and
    chronologically sorted dataframes covering ``[start, end)`` (end exclusive).
    """

    name: str

    @abstractmethod
    def fetch_klines(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pl.DataFrame:
        """Return OHLCV klines with the :data:`KLINE_SCHEMA` schema."""

    @abstractmethod
    def fetch_mark_klines(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pl.DataFrame:
        """Return mark-price klines with the :data:`KLINE_SCHEMA` schema."""

    @abstractmethod
    def fetch_funding(self, symbol: str, start: datetime, end: datetime) -> pl.DataFrame:
        """Return funding-rate observations with the :data:`FUNDING_SCHEMA`."""
