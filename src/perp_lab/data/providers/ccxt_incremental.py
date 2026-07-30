"""Incremental market data via CCXT.

This provider is used ONLY to append the most recent candles that are not yet
in the ``data.binance.vision`` archive (the archive lags real time by ~1 day).
For bulk history use :class:`BinanceVisionBulkProvider`.

CCXT OHLCV lacks quote volume / trade count / taker breakdown, so those
canonical columns are filled with nulls for the incremental tail; the data
quality report reports this coverage gap.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import polars as pl

from perp_lab.data.providers.base import (
    FUNDING_SCHEMA,
    KLINE_SCHEMA,
    ExchangeDataProvider,
    empty_funding,
    empty_klines,
)
from perp_lab.utils.timeutils import TIMEFRAME_TO_MS, utc_to_ms


class CcxtIncrementalProvider(ExchangeDataProvider):
    """Fetch recent klines/funding through CCXT public endpoints."""

    name = "ccxt_incremental"

    def __init__(self, exchange_id: str = "binanceusdm", page_limit: int = 1500) -> None:
        self.exchange_id = exchange_id
        self.page_limit = page_limit
        self._exchange: Any | None = None

    def _exchange_or_create(self) -> Any:
        if self._exchange is None:
            import ccxt  # imported lazily so tests need not have network

            self._exchange = getattr(ccxt, self.exchange_id)({"enableRateLimit": True})
        return self._exchange

    def fetch_klines(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pl.DataFrame:
        exchange = self._exchange_or_create()
        market = _to_ccxt_symbol(symbol)
        step = TIMEFRAME_TO_MS[timeframe]
        since = utc_to_ms(start)
        end_ms = utc_to_ms(end)
        rows: list[list[float]] = []
        while since < end_ms:
            batch = exchange.fetch_ohlcv(
                market, timeframe=timeframe, since=since, limit=self.page_limit
            )
            if not batch:
                break
            rows.extend(batch)
            since = int(batch[-1][0]) + step
            if len(batch) < self.page_limit:
                break

        if not rows:
            return empty_klines()
        df = pl.DataFrame(
            rows, schema=["open_time", "open", "high", "low", "close", "volume"], orient="row"
        )
        return (
            df.with_columns(
                pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC")),
                pl.lit(None, dtype=pl.Float64).alias("quote_volume"),
                pl.lit(None, dtype=pl.Int64).alias("trade_count"),
                pl.lit(None, dtype=pl.Float64).alias("taker_buy_base"),
                pl.lit(None, dtype=pl.Float64).alias("taker_buy_quote"),
            )
            .unique(subset=["open_time"], keep="first")
            .filter(
                (pl.col("open_time") >= start.astimezone(UTC))
                & (pl.col("open_time") < end.astimezone(UTC))
            )
            .sort("open_time")
            .select(list(KLINE_SCHEMA.keys()))
        )

    def fetch_mark_klines(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pl.DataFrame:
        raise NotImplementedError(
            "Mark-price klines are sourced from the bulk archive; the "
            "incremental provider does not implement them."
        )

    def fetch_funding(self, symbol: str, start: datetime, end: datetime) -> pl.DataFrame:
        exchange = self._exchange_or_create()
        market = _to_ccxt_symbol(symbol)
        since = utc_to_ms(start)
        end_ms = utc_to_ms(end)
        records: list[dict[str, Any]] = []
        while since < end_ms:
            batch = exchange.fetch_funding_rate_history(market, since=since, limit=1000)
            if not batch:
                break
            records.extend(batch)
            since = int(batch[-1]["timestamp"]) + 1
            if len(batch) < 1000:
                break

        if not records:
            return empty_funding()
        df = pl.DataFrame(
            {
                "funding_time": [int(r["timestamp"]) for r in records],
                "funding_rate": [float(r["fundingRate"]) for r in records],
            }
        )
        return (
            df.with_columns(
                pl.col("funding_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC")),
                pl.lit(None, dtype=pl.Int64).alias("funding_interval_hours"),
            )
            .unique(subset=["funding_time"], keep="first")
            .filter(
                (pl.col("funding_time") >= start.astimezone(UTC))
                & (pl.col("funding_time") < end.astimezone(UTC))
            )
            .sort("funding_time")
            .select(list(FUNDING_SCHEMA.keys()))
        )


def _to_ccxt_symbol(symbol: str) -> str:
    """Map ``BTCUSDT`` to the CCXT unified symbol ``BTC/USDT:USDT``."""
    symbol = symbol.upper()
    if symbol.endswith("USDT"):
        base = symbol[:-4]
        return f"{base}/USDT:USDT"
    raise ValueError(f"Cannot map symbol {symbol!r} to a CCXT USDT-M market.")
