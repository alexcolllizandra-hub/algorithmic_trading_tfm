"""Command-line entry point for perp-lab operations.

Examples
--------
uv run perp-lab download --config configs/data_contract.yaml
uv run perp-lab validate --config configs/data_contract.yaml
uv run perp-lab pipeline development --config configs/experiment.yaml
uv run perp-lab pipeline development --synthetic   # offline smoke run (not a research result)
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from perp_lab.config import load_data_contract, load_experiment_config, load_settings
from perp_lab.data.download import run_ingestion
from perp_lab.data.providers.binance_vision import BinanceVisionBulkProvider
from perp_lab.experiments.pipeline import run_dev_pipeline
from perp_lab.search.config import load_search_config
from perp_lab.search.runner import run_search
from perp_lab.utils.logging import add_file_logging, get_logger
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


def cmd_pipeline(args: argparse.Namespace) -> int:
    """Run a bounded pipeline stage end to end (currently: development)."""
    if args.stage != "development":
        _log.error("Unknown pipeline stage %r (only 'development' is available).", args.stage)
        return 2
    experiment = load_experiment_config(args.config)
    contract = load_data_contract(args.data_contract)
    settings = load_settings()
    try:
        res = run_dev_pipeline(
            contract=contract,
            experiment=experiment,
            paths=settings.paths,
            symbol=args.symbol,
            timeframe=args.timeframe,
            fast=args.fast,
            slow=args.slow,
            synthetic=args.synthetic,
            synthetic_bars=args.synthetic_bars,
            write_artifacts=True,
            attach_run_file_log=True,
            logger=_log,
        )
    except FileNotFoundError:
        _log.error("Aborting: required market data is not available locally.")
        return 1
    _log.info(
        "pipeline development complete | run_id=%s | %s %s | rows=%d | Sharpe=%.4f | equity=%.4f",
        res.run_id,
        res.symbol,
        res.timeframe,
        res.n_rows,
        res.metrics.get("sharpe", float("nan")),
        res.result.final_equity,
    )
    return 0


def cmd_data_audit(args: argparse.Namespace) -> int:
    """Audit dataset provenance/authenticity and persist a report."""
    from perp_lab.data.provenance import audit_all, write_report

    contract = load_data_contract(args.config)
    settings = load_settings()
    report = audit_all(contract, settings.paths, repo_root=".")
    json_path, md_path = write_report(report, args.out_dir)
    _log.info(
        "data audit | datasets=%d real=%d synthetic=%d issues=%d",
        report["n_datasets"],
        report["n_real_historical"],
        report["n_synthetic_fixture"],
        report["n_with_issues"],
    )
    _log.info("report written to %s and %s", json_path, md_path)
    for a in report["datasets"]:
        _log.info(
            "  %s | %s | rows=%s | %s..%s | checksum=%s | issues=%s",
            a["dataset_id"],
            a["classification"],
            a["row_count_actual"],
            a["min_timestamp"],
            a["max_timestamp"],
            a["checksum_matches"],
            a["issues"] or "none",
        )
    return 1 if report["n_with_issues"] else 0


def cmd_search(args: argparse.Namespace) -> int:
    """Run Random Search and/or the Genetic Algorithm from a search config."""
    cfg = load_search_config(args.config)
    updates: dict[str, object] = {}
    if args.algorithm:
        updates["algorithm"] = args.algorithm
    if args.family:
        updates["family"] = args.family
    if updates:
        cfg = cfg.model_copy(update=updates)
    settings = load_settings()
    try:
        res = run_search(
            cfg,
            paths=settings.paths,
            write_artifacts=True,
            attach_run_file_log=True,
            logger=_log,
        )
    except FileNotFoundError:
        _log.error("Aborting: required market data is not available locally.")
        return 1
    _log.info("search complete | run_id=%s | run_dir=%s", res.run_id, res.run_dir)
    for name, m in res.summary["methods"].items():
        agg = m["aggregate_test"]
        _log.info(
            "  %s | evaluated=%d feasible=%d best_val_fitness=%s mean_OOS_test_sharpe=%s",
            name,
            m["counters"]["evaluated"],
            m["n_feasible"],
            m["best_fitness"],
            agg.get("mean_test_sharpe"),
        )
    _log.info("Best out-of-sample method: %s", res.summary.get("best_out_of_sample_method"))
    _log.warning("%s", res.summary["warning"])
    return 0


def cmd_search_summary(args: argparse.Namespace) -> int:
    """Print the machine-readable summary and human report of a search run."""
    run_dir = Path(args.run_dir)
    summary_path = run_dir / "comparison_summary.json"
    if not summary_path.exists():
        _log.error("No comparison_summary.json under %s", run_dir)
        return 1
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    print(json.dumps(summary, indent=2))
    report = run_dir / "comparison_report.md"
    if report.exists():
        print("\n" + report.read_text(encoding="utf-8"))
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    """Launch the read-only Streamlit Research Dashboard (default port 8501)."""
    import importlib.util
    import subprocess
    import sys

    if importlib.util.find_spec("streamlit") is None:
        _log.error(
            "Streamlit is not installed. Install the dashboard extra with: "
            "uv sync --extra dev --extra dashboard"
        )
        return 1

    from perp_lab import dashboard

    app_path = Path(dashboard.__file__).parent / "app.py"
    env = os.environ.copy()
    env["PERP_LAB_RUNS_DIR"] = str(args.runs_dir)
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(args.port),
        "--server.headless",
        "true" if args.headless else "false",
    ]
    _log.info("Launching dashboard on http://localhost:%d | runs_dir=%s", args.port, args.runs_dir)
    return subprocess.call(cmd, env=env)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="perp-lab", description="perp-lab operations.")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--log-dir", default="logs", type=Path, help="Directory for run logs.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_dl = sub.add_parser("download", parents=[common], help="Download and process the contract.")
    p_dl.add_argument("--config", default="configs/data_contract.yaml", type=Path)
    p_dl.add_argument("--no-checksum", action="store_true", help="Skip checksum verification.")
    p_dl.set_defaults(func=cmd_download)

    p_val = sub.add_parser("validate", parents=[common], help="Run the data-quality report.")
    p_val.add_argument("--config", default="configs/data_contract.yaml", type=Path)
    p_val.set_defaults(func=cmd_validate)

    p_pipe = sub.add_parser(
        "pipeline", parents=[common], help="Run a bounded modelling pipeline stage end to end."
    )
    p_pipe.add_argument("stage", choices=["development"], help="Pipeline stage to run.")
    p_pipe.add_argument("--config", default="configs/experiment.yaml", type=Path)
    p_pipe.add_argument("--data-contract", default="configs/data_contract.yaml", type=Path)
    p_pipe.add_argument("--symbol", default="BTCUSDT")
    p_pipe.add_argument("--timeframe", default="1h")
    p_pipe.add_argument("--fast", default=24, type=int, help="Fast moving-average window (bars).")
    p_pipe.add_argument("--slow", default=96, type=int, help="Slow moving-average window (bars).")
    p_pipe.add_argument(
        "--synthetic",
        action="store_true",
        help="Use a deterministic synthetic series (offline smoke test, not a research result).",
    )
    p_pipe.add_argument("--synthetic-bars", default=2000, type=int)
    p_pipe.set_defaults(func=cmd_pipeline)

    p_audit = sub.add_parser(
        "data-audit",
        parents=[common],
        help="Audit dataset provenance/authenticity (REAL_HISTORICAL vs SYNTHETIC_FIXTURE).",
    )
    p_audit.add_argument("--config", default="configs/data_contract.yaml", type=Path)
    p_audit.add_argument("--out-dir", default=Path("reports/data_provenance"), type=Path)
    p_audit.set_defaults(func=cmd_data_audit)

    p_search = sub.add_parser(
        "search",
        parents=[common],
        help="Run Random Search / Genetic Algorithm strategy discovery.",
    )
    p_search.add_argument("--config", default="configs/search_smoke.yaml", type=Path)
    p_search.add_argument(
        "--algorithm",
        choices=["random_search", "genetic_algorithm", "comparison"],
        default=None,
        help="Override the algorithm selected in the config.",
    )
    p_search.add_argument(
        "--family",
        choices=["momentum", "breakout", "mean_reversion"],
        default=None,
        help="Override the strategy family selected in the config.",
    )
    p_search.set_defaults(func=cmd_search)

    p_ssum = sub.add_parser(
        "search-summary", parents=[common], help="Summarise a completed search run directory."
    )
    p_ssum.add_argument("run_dir", type=Path, help="artifacts/runs/<run_id> directory to inspect.")
    p_ssum.set_defaults(func=cmd_search_summary)

    p_dash = sub.add_parser(
        "dashboard",
        parents=[common],
        help="Launch the read-only Streamlit Research Dashboard (port 8501).",
    )
    p_dash.add_argument("--port", default=8501, type=int, help="Server port (default 8501).")
    p_dash.add_argument(
        "--runs-dir",
        default=Path("artifacts/runs"),
        type=Path,
        help="Directory containing search run artifacts.",
    )
    p_dash.add_argument(
        "--headless",
        action="store_true",
        help="Run Streamlit headless (do not open a browser automatically).",
    )
    p_dash.set_defaults(func=cmd_dashboard)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    log_path = add_file_logging(getattr(args, "log_dir", "logs"))
    _log.info("perp-lab %s | logging to %s", args.command, log_path)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
