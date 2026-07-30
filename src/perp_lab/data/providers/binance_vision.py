"""Bulk historical data from ``data.binance.vision``.

Layout reference (USDT-M futures, ``um``)::

    /data/futures/um/monthly/klines/{SYMBOL}/{tf}/{SYMBOL}-{tf}-{YYYY}-{MM}.zip
    /data/futures/um/daily/klines/{SYMBOL}/{tf}/{SYMBOL}-{tf}-{YYYY}-{MM}-{DD}.zip
    /data/futures/um/monthly/fundingRate/{SYMBOL}/{SYMBOL}-fundingRate-{YYYY}-{MM}.zip
    /data/futures/um/monthly/markPriceKlines/{SYMBOL}/{tf}/{SYMBOL}-markPriceKlines-{tf}-{YYYY}-{MM}.zip

Each ``*.zip`` has a sibling ``*.zip.CHECKSUM`` (SHA-256) which we verify.

Raw zips are cached under ``cache_dir`` (``data/raw`` by default) and reused on
subsequent runs, preserving the immutability guarantee: raw bytes are written
once and never modified.
"""

from __future__ import annotations

import io
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
import polars as pl

from perp_lab.data.providers.base import (
    FUNDING_SCHEMA,
    KLINE_SCHEMA,
    ExchangeDataProvider,
    SchemaDict,
    empty_funding,
    empty_klines,
)
from perp_lab.utils.hashing import sha256_bytes
from perp_lab.utils.logging import get_logger

BASE_URL = "https://data.binance.vision"
_log = get_logger(__name__)

# Raw Binance kline CSV column order (12 columns).
_RAW_KLINE_COLS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "count",
    "taker_buy_volume",
    "taker_buy_quote_volume",
    "ignore",
]


def _month_iter(start: datetime, end: datetime) -> list[tuple[int, int]]:
    """List ``(year, month)`` pairs for every month overlapping ``[start, end)``."""
    months: list[tuple[int, int]] = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def monthly_kline_relpath(
    market_type: str, symbol: str, timeframe: str, year: int, month: int
) -> str:
    """Relative archive path for a monthly kline zip."""
    return (
        f"data/futures/{market_type}/monthly/klines/{symbol}/{timeframe}/"
        f"{symbol}-{timeframe}-{year:04d}-{month:02d}.zip"
    )


def monthly_mark_relpath(
    market_type: str, symbol: str, timeframe: str, year: int, month: int
) -> str:
    """Relative archive path for a monthly mark-price kline zip."""
    return (
        f"data/futures/{market_type}/monthly/markPriceKlines/{symbol}/{timeframe}/"
        f"{symbol}-markPriceKlines-{timeframe}-{year:04d}-{month:02d}.zip"
    )


def monthly_funding_relpath(market_type: str, symbol: str, year: int, month: int) -> str:
    """Relative archive path for a monthly funding-rate zip."""
    return (
        f"data/futures/{market_type}/monthly/fundingRate/{symbol}/"
        f"{symbol}-fundingRate-{year:04d}-{month:02d}.zip"
    )


class BinanceVisionBulkProvider(ExchangeDataProvider):
    """Download and parse bulk market data from ``data.binance.vision``."""

    name = "binance_vision"

    def __init__(
        self,
        market_type: str = "um",
        base_url: str = BASE_URL,
        cache_dir: str | Path | None = None,
        timeout: float = 60.0,
        verify_checksums: bool = True,
        max_retries: int = 3,
        retry_backoff: float = 2.0,
    ) -> None:
        self.market_type = market_type
        self.base_url = base_url.rstrip("/")
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.timeout = timeout
        self.verify_checksums = verify_checksums
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self._client: httpx.Client | None = None

    # -- lifecycle ----------------------------------------------------------- #
    def _client_or_create(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout, follow_redirects=True)
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> BinanceVisionBulkProvider:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -- download primitives ------------------------------------------------- #
    def _get(self, url: str) -> bytes | None:
        """GET raw bytes; return ``None`` for 404, retry on transient errors."""
        client = self._client_or_create()
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = client.get(url)
            except httpx.HTTPError as exc:  # pragma: no cover - network
                last_exc = exc
                time.sleep(self.retry_backoff * attempt)
                continue
            if resp.status_code == 404:
                return None
            if resp.status_code == 200:
                return resp.content
            time.sleep(self.retry_backoff * attempt)
        if last_exc is not None:  # pragma: no cover - network
            raise last_exc
        raise RuntimeError(f"Failed to download {url} after {self.max_retries} tries.")

    def _download_zip(self, relpath: str) -> bytes | None:
        """Return raw zip bytes for ``relpath`` (cached), or ``None`` if absent."""
        if self.cache_dir is not None:
            cached = self.cache_dir / relpath
            if cached.exists():
                return cached.read_bytes()

        url = f"{self.base_url}/{relpath}"
        content = self._get(url)
        if content is None:
            return None

        if self.verify_checksums:
            checksum = self._get(f"{url}.CHECKSUM")
            if checksum is not None:
                expected = checksum.decode().split()[0].strip().lower()
                actual = sha256_bytes(content).lower()
                if expected != actual:
                    raise ValueError(
                        f"Checksum mismatch for {relpath}: expected {expected}, got {actual}."
                    )

        if self.cache_dir is not None:
            cached = self.cache_dir / relpath
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_bytes(content)
        return content

    @staticmethod
    def _read_inner_csv(zip_bytes: bytes) -> bytes:
        """Return the single CSV member of a Binance zip archive."""
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise ValueError("Zip archive has no CSV member.")
            return zf.read(names[0])

    # -- parsing ------------------------------------------------------------- #
    @staticmethod
    def _has_header(csv_bytes: bytes) -> bool:
        head = csv_bytes[:64].lstrip()
        return head[:9].lower() == b"open_time" or head[:9].lower() == b"calc_time"

    def _parse_klines(self, csv_bytes: bytes) -> pl.DataFrame:
        raw = pl.read_csv(
            csv_bytes,
            has_header=self._has_header(csv_bytes),
            new_columns=_RAW_KLINE_COLS,
            infer_schema_length=0,  # read as strings, cast explicitly below
        )
        return raw.select(
            pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC")),
            pl.col("open").cast(pl.Float64),
            pl.col("high").cast(pl.Float64),
            pl.col("low").cast(pl.Float64),
            pl.col("close").cast(pl.Float64),
            pl.col("volume").cast(pl.Float64),
            pl.col("quote_volume").cast(pl.Float64),
            pl.col("count").cast(pl.Int64).alias("trade_count"),
            pl.col("taker_buy_volume").cast(pl.Float64).alias("taker_buy_base"),
            pl.col("taker_buy_quote_volume").cast(pl.Float64).alias("taker_buy_quote"),
        )

    def _parse_funding(self, csv_bytes: bytes) -> pl.DataFrame:
        cols = ["calc_time", "funding_interval_hours", "last_funding_rate"]
        raw = pl.read_csv(
            csv_bytes,
            has_header=self._has_header(csv_bytes),
            new_columns=cols,
            infer_schema_length=0,
        )
        return raw.select(
            pl.col("calc_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC")).alias("funding_time"),
            pl.col("funding_interval_hours").cast(pl.Int64),
            pl.col("last_funding_rate").cast(pl.Float64).alias("funding_rate"),
        )

    # -- public API ---------------------------------------------------------- #
    def _fetch_kline_like(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        *,
        mark: bool,
    ) -> pl.DataFrame:
        symbol = symbol.upper()
        frames: list[pl.DataFrame] = []
        for year, month in _month_iter(start, end):
            relpath = (
                monthly_mark_relpath(self.market_type, symbol, timeframe, year, month)
                if mark
                else monthly_kline_relpath(self.market_type, symbol, timeframe, year, month)
            )
            zip_bytes = self._download_zip(relpath)
            if zip_bytes is None:
                _log.warning("Missing archive %s", relpath)
                continue
            frames.append(self._parse_klines(self._read_inner_csv(zip_bytes)))

        if not frames:
            return empty_klines()
        return _finalize(pl.concat(frames), "open_time", start, end, KLINE_SCHEMA)

    def fetch_klines(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pl.DataFrame:
        return self._fetch_kline_like(symbol, timeframe, start, end, mark=False)

    def fetch_mark_klines(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pl.DataFrame:
        return self._fetch_kline_like(symbol, timeframe, start, end, mark=True)

    def fetch_funding(self, symbol: str, start: datetime, end: datetime) -> pl.DataFrame:
        symbol = symbol.upper()
        frames: list[pl.DataFrame] = []
        for year, month in _month_iter(start, end):
            relpath = monthly_funding_relpath(self.market_type, symbol, year, month)
            zip_bytes = self._download_zip(relpath)
            if zip_bytes is None:
                _log.warning("Missing funding archive %s", relpath)
                continue
            frames.append(self._parse_funding(self._read_inner_csv(zip_bytes)))

        if not frames:
            return empty_funding()
        return _finalize(pl.concat(frames), "funding_time", start, end, FUNDING_SCHEMA)


def _finalize(
    df: pl.DataFrame,
    time_col: str,
    start: datetime,
    end: datetime,
    schema: SchemaDict,
) -> pl.DataFrame:
    """De-duplicate, sort, clip to ``[start, end)`` and order columns."""
    start_utc = start.astimezone(UTC) if start.tzinfo else start.replace(tzinfo=UTC)
    end_utc = end.astimezone(UTC) if end.tzinfo else end.replace(tzinfo=UTC)
    return (
        df.unique(subset=[time_col], keep="first")
        .filter((pl.col(time_col) >= start_utc) & (pl.col(time_col) < end_utc))
        .sort(time_col)
        .select(list(schema.keys()))
    )
