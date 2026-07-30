"""End-to-end ingestion using an in-memory provider (no network)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import cast

import polars as pl

from perp_lab.config.models import ContractSpec, DataContract, HoldoutSpec, Paths
from perp_lab.data.download import run_ingestion
from perp_lab.data.manifest import read_manifest
from perp_lab.data.providers.base import ExchangeDataProvider, empty_funding


class FakeProvider(ExchangeDataProvider):
    name = "fake"

    def __init__(self, klines: pl.DataFrame) -> None:
        self._klines = klines

    def _clip(self, start: datetime, end: datetime) -> pl.DataFrame:
        return self._klines.filter(
            (pl.col("open_time") >= start) & (pl.col("open_time") < end)
        ).sort("open_time")

    def fetch_klines(self, symbol, timeframe, start, end):
        return self._clip(start, end)

    def fetch_mark_klines(self, symbol, timeframe, start, end):
        return self._clip(start, end)

    def fetch_funding(self, symbol, start, end):
        return empty_funding()


def _contract() -> DataContract:
    return DataContract(
        symbols=(ContractSpec(symbol="BTCUSDT", listing_date=date(2021, 1, 1)),),
        cutoff_date=date(2021, 1, 4),
        holdout=HoldoutSpec(start=date(2021, 1, 3)),
        aux_streams=("fundingRate",),
    )


def test_run_ingestion_creates_layers_and_manifests(tmp_path, make_klines):
    # Three days of 5-minute bars.
    klines = make_klines(n=288 * 3, start=datetime(2021, 1, 1, tzinfo=UTC))
    contract = _contract()
    paths = Paths(data_root=tmp_path / "data", reports_root=tmp_path / "reports")

    manifests = run_ingestion(contract, paths, FakeProvider(klines), repo_root=tmp_path)

    # Base 5m validated file exists.
    assert (paths.validated_dir / "BTCUSDT" / "5m.parquet").exists()

    # Derived timeframes split into development + holdout.
    for tf in contract.derived_timeframes:
        for partition in ("development", "holdout"):
            assert (paths.processed_dir / "BTCUSDT" / f"{tf}_{partition}.parquet").exists()

    # A manifest per dataset file, all with content hashes.
    ids = {m.dataset_id for m in manifests}
    assert "binance_um_BTCUSDT_klines_5m" in ids
    assert "binance_um_BTCUSDT_klines_1h_development" in ids
    assert "binance_um_BTCUSDT_klines_1h_holdout" in ids
    assert all(m.data_sha256 for m in manifests)


def test_holdout_partition_starts_at_holdout_boundary(tmp_path, make_klines):
    klines = make_klines(n=288 * 3, start=datetime(2021, 1, 1, tzinfo=UTC))
    contract = _contract()
    paths = Paths(data_root=tmp_path / "data", reports_root=tmp_path / "reports")
    run_ingestion(contract, paths, FakeProvider(klines), repo_root=tmp_path)

    dev = pl.read_parquet(paths.processed_dir / "BTCUSDT" / "1h_development.parquet")
    hold = pl.read_parquet(paths.processed_dir / "BTCUSDT" / "1h_holdout.parquet")
    boundary = datetime(2021, 1, 3, tzinfo=UTC)
    assert cast(datetime, dev["open_time"].max()) < boundary
    assert cast(datetime, hold["open_time"].min()) >= boundary


def test_manifest_files_are_loadable(tmp_path, make_klines):
    klines = make_klines(n=288 * 3, start=datetime(2021, 1, 1, tzinfo=UTC))
    contract = _contract()
    paths = Paths(data_root=tmp_path / "data", reports_root=tmp_path / "reports")
    run_ingestion(contract, paths, FakeProvider(klines), repo_root=tmp_path)

    loaded = read_manifest(paths.manifests_dir / "binance_um_BTCUSDT_klines_5m.json")
    assert loaded.symbol == "BTCUSDT"
    assert loaded.row_count == 288 * 3
