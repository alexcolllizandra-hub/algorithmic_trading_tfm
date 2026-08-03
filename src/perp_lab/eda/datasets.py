"""Development-safe data loading for the EDA notebooks.

This module is the single entry point notebooks use to read market data. It
enforces the research-integrity contract: when the ``development`` partition is
requested, every returned frame is strictly before the holdout start, and a
guard raises if any holdout timestamp leaks in. Notebooks stay thin: they load
through :class:`DataLake`, call tested ``perp_lab.eda`` functions, and narrate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

import polars as pl

from perp_lab.config.models import DataContract, Paths
from perp_lab.data.splits import resolve_holdout_start

Partition = str  # "development" | "holdout" | "full"


class HoldoutLeakageError(RuntimeError):
    """Raised when holdout data appears in a development frame."""


@dataclass(frozen=True)
class LoadedDataset:
    """A loaded frame together with its provenance and holdout status."""

    frame: pl.DataFrame
    dataset_id: str
    sha256: str | None
    partition: Partition
    time_col: str
    holdout_excluded: bool

    @property
    def n_rows(self) -> int:
        return self.frame.height

    @property
    def period_start(self) -> datetime | None:
        if self.frame.height == 0:
            return None
        return self.frame.select(pl.col(self.time_col).min()).item()

    @property
    def period_end(self) -> datetime | None:
        if self.frame.height == 0:
            return None
        return self.frame.select(pl.col(self.time_col).max()).item()


def assert_no_holdout(
    df: pl.DataFrame, holdout_start: datetime, *, time_col: str = "open_time"
) -> None:
    """Raise :class:`HoldoutLeakageError` if any timestamp is >= holdout start."""
    if df.height == 0:
        return
    max_t = df.select(pl.col(time_col).max()).item()
    if max_t is not None and max_t >= holdout_start:
        raise HoldoutLeakageError(
            f"Holdout leakage: max {time_col}={max_t} >= holdout_start={holdout_start}."
        )


class DataLake:
    """Read validated/processed parquet with development-safe defaults."""

    def __init__(self, contract: DataContract, paths: Paths | None = None) -> None:
        self.contract = contract
        self.paths = paths or Paths()
        self.holdout_start = resolve_holdout_start(contract)

    # -- provenance ---------------------------------------------------------- #
    def manifest_hash(self, dataset_id: str) -> str | None:
        path = self.paths.manifests_dir / f"{dataset_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("data_sha256")

    def _partition_filter(
        self, df: pl.DataFrame, partition: Partition, time_col: str
    ) -> tuple[pl.DataFrame, bool]:
        if partition == "development":
            return df.filter(pl.col(time_col) < self.holdout_start), True
        if partition == "holdout":
            return df.filter(pl.col(time_col) >= self.holdout_start), False
        return df, False

    # -- klines -------------------------------------------------------------- #
    def load_klines(
        self,
        symbol: str,
        timeframe: str,
        *,
        partition: Partition = "development",
    ) -> LoadedDataset:
        """Load OHLCV klines for a symbol/timeframe and partition.

        For derived timeframes (15m, 1h) the pre-split processed partition is
        read directly. For the 5m base the validated file is filtered to the
        requested partition on load.
        """
        symbol = symbol.upper()
        exch, mkt = self.contract.exchange, self.contract.market_type

        if timeframe in self.contract.derived_timeframes and partition in {
            "development",
            "holdout",
        }:
            path = self.paths.processed_dir / symbol / f"{timeframe}_{partition}.parquet"
            dataset_id = f"{exch}_{mkt}_{symbol}_klines_{timeframe}_{partition}"
            frame = pl.read_parquet(path).sort("open_time")
            holdout_excluded = partition == "development"
        else:
            path = self.paths.validated_dir / symbol / f"{timeframe}.parquet"
            dataset_id = f"{exch}_{mkt}_{symbol}_klines_{timeframe}"
            frame = pl.read_parquet(path).sort("open_time")
            frame, holdout_excluded = self._partition_filter(frame, partition, "open_time")

        if holdout_excluded:
            assert_no_holdout(frame, self.holdout_start, time_col="open_time")
        return LoadedDataset(
            frame=frame,
            dataset_id=dataset_id,
            sha256=self.manifest_hash(dataset_id),
            partition=partition,
            time_col="open_time",
            holdout_excluded=holdout_excluded,
        )

    # -- funding ------------------------------------------------------------- #
    def load_funding(self, symbol: str, *, partition: Partition = "development") -> LoadedDataset:
        symbol = symbol.upper()
        exch, mkt = self.contract.exchange, self.contract.market_type
        path = self.paths.validated_dir / symbol / "fundingRate.parquet"
        dataset_id = f"{exch}_{mkt}_{symbol}_fundingRate"
        frame = pl.read_parquet(path).sort("funding_time")
        frame, holdout_excluded = self._partition_filter(frame, partition, "funding_time")
        if holdout_excluded:
            assert_no_holdout(frame, self.holdout_start, time_col="funding_time")
        return LoadedDataset(
            frame=frame,
            dataset_id=dataset_id,
            sha256=self.manifest_hash(dataset_id),
            partition=partition,
            time_col="funding_time",
            holdout_excluded=holdout_excluded,
        )

    # -- mark price ---------------------------------------------------------- #
    def load_mark(self, symbol: str, *, partition: Partition = "development") -> LoadedDataset:
        symbol = symbol.upper()
        exch, mkt = self.contract.exchange, self.contract.market_type
        tf = self.contract.base_timeframe
        path = self.paths.validated_dir / symbol / f"markPrice_{tf}.parquet"
        dataset_id = f"{exch}_{mkt}_{symbol}_markPriceKlines_{tf}"
        frame = pl.read_parquet(path).sort("open_time")
        frame, holdout_excluded = self._partition_filter(frame, partition, "open_time")
        if holdout_excluded:
            assert_no_holdout(frame, self.holdout_start, time_col="open_time")
        return LoadedDataset(
            frame=frame,
            dataset_id=dataset_id,
            sha256=self.manifest_hash(dataset_id),
            partition=partition,
            time_col="open_time",
            holdout_excluded=holdout_excluded,
        )

    def available(self) -> dict[str, bool]:
        """Report which validated/processed files currently exist on disk."""
        status: dict[str, bool] = {}
        for spec in self.contract.symbols:
            sym = spec.symbol
            status[f"{sym}:5m"] = (self.paths.validated_dir / sym / "5m.parquet").exists()
            for tf in self.contract.derived_timeframes:
                status[f"{sym}:{tf}_development"] = (
                    self.paths.processed_dir / sym / f"{tf}_development.parquet"
                ).exists()
            status[f"{sym}:fundingRate"] = (
                self.paths.validated_dir / sym / "fundingRate.parquet"
            ).exists()
            status[f"{sym}:markPrice"] = (
                self.paths.validated_dir / sym / "markPrice_5m.parquet"
            ).exists()
        return status


def utc(year: int, month: int, day: int) -> datetime:
    """Convenience constructor for a tz-aware UTC midnight datetime."""
    return datetime(year, month, day, tzinfo=UTC)
