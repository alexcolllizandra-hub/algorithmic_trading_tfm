"""Ingestion orchestration: raw -> validated -> processed (+ manifests).

Pipeline per symbol::

    bulk 5m klines  --> validated/{sym}/5m.parquet         (+ manifest)
                    --> processed/{sym}/{15m,1h}.parquet    (+ manifests)
    funding rate    --> validated/{sym}/fundingRate.parquet (+ manifest)

Each processed timeframe is additionally split into a development partition and
a frozen holdout partition, each with its own manifest and content hash.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from perp_lab.config.models import ContractSpec, DataContract, Paths
from perp_lab.data.bars import resample_klines
from perp_lab.data.manifest import DatasetManifest, write_manifest
from perp_lab.data.providers.base import ExchangeDataProvider
from perp_lab.data.splits import resolve_holdout_start, split_by_holdout
from perp_lab.utils.logging import get_logger

_log = get_logger(__name__)


def dataset_id(
    exchange: str,
    market_type: str,
    symbol: str,
    stream: str,
    timeframe: str | None = None,
    partition: str | None = None,
) -> str:
    """Stable identifier used for parquet filenames and manifest keys."""
    parts = [exchange, market_type, symbol, stream]
    if timeframe:
        parts.append(timeframe)
    if partition:
        parts.append(partition)
    return "_".join(parts)


def _contract_bounds(contract: DataContract, spec: ContractSpec) -> tuple[datetime, datetime]:
    start = datetime(
        spec.listing_date.year, spec.listing_date.month, spec.listing_date.day, tzinfo=UTC
    )
    end = datetime(
        contract.cutoff_date.year,
        contract.cutoff_date.month,
        contract.cutoff_date.day,
        tzinfo=UTC,
    )
    return start, end


def ingest_symbol(
    provider: ExchangeDataProvider,
    contract: DataContract,
    spec: ContractSpec,
    paths: Paths,
    *,
    repo_root: str | Path = ".",
) -> list[DatasetManifest]:
    """Ingest one contract end to end. Returns the manifests produced."""
    manifests: list[DatasetManifest] = []
    start, end = _contract_bounds(contract, spec)
    holdout_start = resolve_holdout_start(contract)

    _log.info(
        "Fetching %s %s base klines [%s, %s)", spec.symbol, contract.base_timeframe, start, end
    )
    base = provider.fetch_klines(spec.symbol, contract.base_timeframe, start, end)

    # Validated 5m base.
    base_dir = paths.validated_dir / spec.symbol
    manifests.append(
        write_manifest(
            base,
            data_path=base_dir / f"{contract.base_timeframe}.parquet",
            manifests_dir=paths.manifests_dir,
            dataset_id=dataset_id(
                contract.exchange,
                contract.market_type,
                spec.symbol,
                "klines",
                contract.base_timeframe,
            ),
            source=provider.name,
            exchange=contract.exchange,
            market_type=contract.market_type,
            symbol=spec.symbol,
            stream="klines",
            timeframe=contract.base_timeframe,
            repo_root=repo_root,
            notes="Base timeframe downloaded directly from source.",
        )
    )

    # Derived timeframes, each split into development + frozen holdout.
    for tf in contract.derived_timeframes:
        bars = resample_klines(base, contract.base_timeframe, tf, drop_incomplete=True)
        split = split_by_holdout(bars, holdout_start)
        for partition, frame in (("development", split.development), ("holdout", split.holdout)):
            manifests.append(
                write_manifest(
                    frame,
                    data_path=paths.processed_dir / spec.symbol / f"{tf}_{partition}.parquet",
                    manifests_dir=paths.manifests_dir,
                    dataset_id=dataset_id(
                        contract.exchange,
                        contract.market_type,
                        spec.symbol,
                        "klines",
                        tf,
                        partition,
                    ),
                    source=provider.name,
                    exchange=contract.exchange,
                    market_type=contract.market_type,
                    symbol=spec.symbol,
                    stream="klines",
                    timeframe=tf,
                    repo_root=repo_root,
                    notes=(
                        f"Built from {contract.base_timeframe}. Partition={partition}. "
                        f"Holdout starts {holdout_start.isoformat()} and is frozen."
                    ),
                )
            )

    # Funding rate (auxiliary stream).
    if "fundingRate" in contract.aux_streams:
        funding = provider.fetch_funding(spec.symbol, start, end)
        manifests.append(
            write_manifest(
                funding,
                data_path=base_dir / "fundingRate.parquet",
                manifests_dir=paths.manifests_dir,
                dataset_id=dataset_id(
                    contract.exchange, contract.market_type, spec.symbol, "fundingRate"
                ),
                source=provider.name,
                exchange=contract.exchange,
                market_type=contract.market_type,
                symbol=spec.symbol,
                stream="fundingRate",
                timeframe=None,
                time_col="funding_time",
                repo_root=repo_root,
                notes="Funding-rate observations (8h nominal interval).",
            )
        )

    return manifests


def run_ingestion(
    contract: DataContract,
    paths: Paths,
    provider: ExchangeDataProvider,
    *,
    repo_root: str | Path = ".",
) -> list[DatasetManifest]:
    """Ingest every contract in the data contract."""
    paths.ensure()
    all_manifests: list[DatasetManifest] = []
    for spec in contract.symbols:
        all_manifests.extend(ingest_symbol(provider, contract, spec, paths, repo_root=repo_root))
    return all_manifests
