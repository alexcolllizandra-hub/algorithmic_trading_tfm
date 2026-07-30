"""Command-line entry point for Phase 1 data operations.

Examples
--------
uv run perp-lab download --config configs/data_contract.yaml
uv run perp-lab validate --config configs/data_contract.yaml
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from perp_lab.config import load_data_contract, load_settings
from perp_lab.data.download import run_ingestion
from perp_lab.data.providers.binance_vision import BinanceVisionBulkProvider
from perp_lab.utils.logging import get_logger
from perp_lab.utils.seeds import set_global_seed
from perp_lab.validation.quality import quality_report

_log = get_logger("perp_lab.cli")


def cmd_download(args: argparse.Namespace) -> int:
    contract = load_data_contract(args.config)
    settings = load_settings()
    set_global_seed(settings.seed)
    provider = BinanceVisionBulkProvider(
        market_type=contract.market_type,
        cache_dir=settings.paths.raw_dir,
        verify_checksums=not args.no_checksum,
    )
    with provider:
        manifests = run_ingestion(contract, settings.paths, provider)
    _log.info("Wrote %d dataset manifests to %s", len(manifests), settings.paths.manifests_dir)
    for m in manifests:
        _log.info(
            "  %s: %d rows [%s .. %s]", m.dataset_id, m.row_count, m.period_start, m.period_end
        )
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    contract = load_data_contract(args.config)
    settings = load_settings()
    paths = settings.paths
    end = datetime(
        contract.cutoff_date.year, contract.cutoff_date.month, contract.cutoff_date.day, tzinfo=UTC
    )

    reports = []
    for spec in contract.symbols:
        start = datetime(
            spec.listing_date.year, spec.listing_date.month, spec.listing_date.day, tzinfo=UTC
        )
        base_path = paths.validated_dir / spec.symbol / f"{contract.base_timeframe}.parquet"
        if base_path.exists():
            df = pl.read_parquet(base_path)
            reports.append(
                quality_report(
                    df,
                    symbol=spec.symbol,
                    timeframe=contract.base_timeframe,
                    start=start,
                    end=end,
                ).model_dump()
            )
        else:
            _log.warning("Missing %s; run 'perp-lab download' first.", base_path)

    if not reports:
        _log.error("No datasets found to validate.")
        return 1

    table = pl.DataFrame(reports)
    out = paths.tables_dir / "quality_report.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    table.write_csv(out)
    _log.info("Quality report written to %s", out)
    print(table)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="perp-lab", description="Phase 1 data operations.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_dl = sub.add_parser("download", help="Download and process the data contract.")
    p_dl.add_argument("--config", default="configs/data_contract.yaml", type=Path)
    p_dl.add_argument("--no-checksum", action="store_true", help="Skip checksum verification.")
    p_dl.set_defaults(func=cmd_download)

    p_val = sub.add_parser("validate", help="Run the data-quality report.")
    p_val.add_argument("--config", default="configs/data_contract.yaml", type=Path)
    p_val.set_defaults(func=cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
