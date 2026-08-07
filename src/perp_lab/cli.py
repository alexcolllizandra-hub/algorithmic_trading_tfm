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
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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


def _contract_payload(cfg: Any) -> dict[str, Any]:
    """The methodological contract a study is bound to.

    Kept separate from the search configuration in the run's identity so a
    refusal to resume can say *which* of the two moved.
    """
    exp = load_experiment_config(cfg.experiment_config)
    contract = load_data_contract(cfg.data_contract)
    return {
        "experiment": exp.model_dump(mode="json"),
        "data_contract": contract.model_dump(mode="json"),
    }


def _development_dataset_hashes(cfg: Any, symbols: tuple[str, ...]) -> dict[str, str]:
    """SHA-256 of the development partitions the study is allowed to read.

    Only development manifests are consulted. Reaching for a holdout manifest to
    "complete" the record would be exactly the access this project forbids.
    """
    from perp_lab.config import Paths

    manifests_dir = Path(Paths().data_root) / "manifests"
    out: dict[str, str] = {}
    if not manifests_dir.exists():
        return out
    for symbol in symbols:
        for path in sorted(manifests_dir.glob(f"*{symbol}*development*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            digest = payload.get("sha256") or payload.get("content_sha256")
            if digest:
                out[path.stem] = str(digest)
    return out


def cmd_multi_seed(args: argparse.Namespace) -> int:
    """Run the frozen experiment across many seeds and assets, with resume."""
    from perp_lab.evaluation.multi_seed import analyse_study
    from perp_lab.experiments.multi_seed import resolve_seeds, run_multi_seed
    from perp_lab.search.config import load_search_config
    from perp_lab.tracking.journal import atomic_write_json

    cfg = load_search_config(args.config)
    seeds = resolve_seeds(args.base_seed, args.n_seeds)
    symbols = tuple(s.strip().upper() for s in args.symbols.split(","))

    _log.info(
        "multi-seed study | symbols=%s | %d seeds | %d units | budget=%d",
        list(symbols),
        len(seeds),
        len(symbols) * len(seeds),
        cfg.budget,
    )
    result = run_multi_seed(
        cfg,
        symbols=symbols,
        seeds=seeds,
        study_dir=args.study_dir,
        resume=not args.no_resume,
        contract_payload=_contract_payload(cfg),
        dataset_hashes=_development_dataset_hashes(cfg, symbols),
        logger=_log,
    )

    analysis = analyse_study(result.units, metric=args.metric)
    atomic_write_json(result.study_dir / "multi_seed_analysis.json", analysis)

    print(f"\nStudy: {result.study_id}")
    print(f"Units: {len(result.plan)} ({result.resumed} resumed from checkpoint)")

    print(
        f"\n{'symbol | engine':<38}{'seeds':>7}{'positive':>10}{'mean':>10}{'sd':>9}"
        f"{'min':>9}{'max':>9}"
    )
    print("-" * 92)
    for key, row in analysis["seed_stability"].items():
        sd = row["sd_across_seeds"]
        print(
            f"{key.replace('|', ' | '):<38}{row['n_seeds']:>7}"
            f"{row['n_seeds_positive']:>10}{row['mean_across_seeds']:>10.3f}"
            f"{(sd if sd is not None else float('nan')):>9.3f}"
            f"{row['min']:>9.3f}{row['max']:>9.3f}"
        )

    vd = analysis["variance_decomposition"]
    print("\nVariance decomposition (these are different questions, not one error bar)")
    print("-" * 92)
    for engine in ("random_search", "genetic_algorithm"):
        if engine not in vd:
            continue
        payload = vd[engine]
        print(
            f"  {engine:<22} seed sd (same data) = "
            f"{payload['seed_variability']['mean_sd_within_symbol_fold']}"
        )
        print(
            f"  {'':<22} fold sd (market)    = {payload['fold_level_mean']['sd']}"
            f"   over {payload['fold_level_mean']['n_folds']} folds"
        )
    if "seed_to_fold_sd_ratio" in vd:
        print(f"  seed/fold sd ratio: {vd['seed_to_fold_sd_ratio']['values']}")

    paired = analysis["paired_rs_vs_ga"]
    if paired and "mean_difference_ga_minus_rs" in paired:
        print("\nPaired GA - RS comparison")
        print("-" * 92)
        print(f"  cells (symbol x seed x fold) : {paired['n_cells_symbol_seed_fold']}")
        print(
            f"  independent units used       : {paired['n_independent_units_used']} "
            f"({paired['unit_of_inference']})"
        )
        print(f"  mean difference              : {paired['mean_difference_ga_minus_rs']:.4f}")
        if "ci_low" in paired:
            print(
                f"  95% CI                       : "
                f"[{paired['ci_low']:.4f}, {paired['ci_high']:.4f}]"
            )
            print(f"  effect size (Cohen's dz)     : {paired['effect_size_cohens_dz']:.3f}")
        print(
            f"  folds favouring GA / RS      : {paired['n_folds_favouring_ga']} / "
            f"{paired['n_folds_favouring_rs']}"
        )
        print(f"\n  VERDICT: {paired['verdict']}")

    print(f"\n{analysis['caveat']}")
    print(f"\nWritten: {result.study_dir}")
    return 0


def cmd_study_robustness(args: argparse.Namespace) -> int:
    """Baselines, temporal bootstrap and cost stress for every unit of a study."""
    from perp_lab.config import load_experiment_config
    from perp_lab.evaluation.study_robustness import analyse_study_robustness
    from perp_lab.tracking.journal import Checkpoint, atomic_write_json

    study_dir = Path(args.study_dir)
    checkpoint = Checkpoint(study_dir)
    units = checkpoint.results()
    if not units:
        _log.error("No completed units under %s", study_dir)
        return 1

    # Baselines are priced at the CONTRACT cost rate, never at whatever rate a
    # particular strategy happened to realise, so they stay a fixed reference.
    exp = load_experiment_config(args.experiment_config)
    _log.info("Analysing %d units (this re-prices every OOS ledger)", len(units))
    payload = analyse_study_robustness(
        units,
        timeframe=args.timeframe,
        fee_bps_per_side=exp.costs.fee_bps_per_side,
        slippage_bps_per_side=exp.costs.slippage.baseline_bps,
        resamples=args.resamples,
    )
    atomic_write_json(study_dir / "study_robustness.json", payload)

    print(f"\nRobustness across seeds ({len(payload['per_run'])} run/engine combinations)")
    header = (
        f"{'symbol | engine':<38}{'seeds':>7}{'positive':>10}{'>B&H':>7}"
        f"{'2x cost':>9}{'CI>0':>7}{'median ret':>12}{'B&H ret':>11}"
    )
    print(header)
    print("-" * len(header))

    def _num(value: float | None, width: int) -> str:
        return f"{value:>{width}.4f}" if value is not None else f"{'n/a':>{width}}"

    for group, row in sorted(payload["by_symbol_and_engine"].items()):
        print(
            f"{group.replace('|', ' | '):<38}{row['n_seeds']:>7}{row['n_positive']:>10}"
            f"{row['n_beat_buy_and_hold']:>7}{row['n_survive_double_costs']:>9}"
            f"{row['n_bootstrap_ci_excludes_zero']:>7}"
            f"{_num(row['median_total_return'], 12)}"
            f"{_num(row['median_buy_and_hold_return'], 11)}"
        )
    print(f"\n{payload['method_note']}")
    print(f"\nWritten: {study_dir / 'study_robustness.json'}")
    return 0


def cmd_study_status(args: argparse.Namespace) -> int:
    """Report the live progress of a multi-seed study without disturbing it."""
    from perp_lab.tracking.journal import Checkpoint, Journal

    study_dir = Path(args.study_dir)
    if not study_dir.exists():
        _log.error("No study directory at %s", study_dir)
        return 1

    journal = Journal(study_dir)
    status = journal.read_status()
    if not status:
        print(f"No status.json yet under {study_dir}")
        return 0

    print(f"Study      : {study_dir.name}")
    print(f"State      : {status.get('state')}  (phase: {status.get('phase')})")
    print(
        f"Progress   : {status.get('completed')}/{status.get('total')} "
        f"({100 * (status.get('progress') or 0):.1f}%)"
    )
    print(f"Elapsed    : {status.get('elapsed_seconds')}s")
    print(f"Per unit   : {status.get('seconds_per_unit')}s")
    print(f"ETA        : {status.get('eta_seconds')}s")
    print(f"Updated    : {status.get('updated_at')}")

    try:
        checkpoint = Checkpoint(study_dir)
    except ValueError as exc:
        print(f"\nCheckpoint problem: {exc}")
        return 1
    print(f"\nCompleted units ({len(checkpoint.completed_keys())}):")
    for key in checkpoint.completed_keys():
        unit = checkpoint.result(key) or {}
        evaluated = {n: v.get("evaluated") for n, v in (unit.get("engines") or {}).items()}
        print(f"  {key:<28} run_id={unit.get('run_id')}  evaluated={evaluated}")

    if args.events:
        print("\nRecent events:")
        for event in journal.read_events()[-args.events :]:
            print(f"  {event.get('ts')}  {event.get('kind'):<16} {event.get('unit', '')}")
    return 0


def cmd_feature_catalogue(args: argparse.Namespace) -> int:
    """Print the causal feature registry: kinds, families, packs and proxy flags."""
    from perp_lab.features.spec import catalogue, catalogue_counts, kinds_in_packs, proxy_kinds

    rows = catalogue()
    if args.pack:
        allowed = set(kinds_in_packs([args.pack]))
        rows = [r for r in rows if r["kind"] in allowed]

    if args.json:
        print(json.dumps({"counts": catalogue_counts(), "features": rows}, indent=2))
        return 0

    counts = catalogue_counts()
    print(f"Feature kinds registered: {counts['total_kinds']['kinds']}")
    print("\nBy pack (cumulative packs: core < extended < experimental)")
    for pack, n in counts["by_pack"].items():
        print(f"  {pack:<14} {n:>3}")
    print("\nBy family")
    for family, n in counts["by_family"].items():
        print(f"  {family:<14} {n:>3}")

    print(f"\n{'kind':<22}{'family':<14}{'pack':<14}{'proxy':<7}availability")
    print("-" * 100)
    for r in rows:
        print(
            f"{r['kind']:<22}{r['family']:<14}{r['pack']:<14}"
            f"{'yes' if r['is_proxy'] else '-':<7}{r['availability']}"
        )

    proxies = proxy_kinds()
    if proxies:
        print("\nProxies (approximations, never observed quantities):")
        for kind in proxies:
            note = next(r["proxy_note"] for r in catalogue() if r["kind"] == kind)
            print(f"  {kind}: {note}")
    print(
        "\nNote: these are feature *kinds* (information sources), not columns. "
        "A parameterised kind expands into many columns; counting columns would "
        "overstate the number of independent signals."
    )
    return 0


def cmd_temporal_geometry(args: argparse.Namespace) -> int:
    """Print every walk-forward fold implied by the experiment contract."""
    from perp_lab.validation.walk_forward import generate_walk_forward

    exp = load_experiment_config(args.config)
    folds = generate_walk_forward(exp, strict=True)

    if args.json:
        print(json.dumps([f.to_dict() for f in folds], indent=2, default=str))
        return 0

    print(
        f"Development period : {exp.periods.development_start:%Y-%m-%d} -> "
        f"{exp.periods.development_end_exclusive:%Y-%m-%d} (exclusive)"
    )
    print(f"Frozen holdout     : {exp.periods.holdout_start:%Y-%m-%d} onwards -- NOT accessed")
    print(f"Decision timeframe : {exp.timeframes.primary}")
    print(f"Purge / embargo    : {exp.purge_bars} / {exp.embargo_bars} bars")
    print(f"Folds generated    : {len(folds)}\n")
    header = f"{'fold':<6}{'train_start':<13}{'train_end':<13}{'val_start':<13}"
    print(header + f"{'val_end':<13}{'test_start':<13}{'test_end':<13}")
    print("-" * 85)
    for f in folds:
        print(
            f"{f.index:<6}{f.train_start:%Y-%m-%d}   {f.train_end:%Y-%m-%d}   "
            f"{f.val_start:%Y-%m-%d}   {f.val_end:%Y-%m-%d}   "
            f"{f.test_start:%Y-%m-%d}   {f.test_end:%Y-%m-%d}"
        )
    if folds:
        span_days = (folds[-1].test_end - folds[0].test_start).days
        dev_days = (exp.periods.development_end_exclusive - exp.periods.development_start).days
        print(
            f"\nConcatenated OOS test span: {folds[0].test_start:%Y-%m-%d} -> "
            f"{folds[-1].test_end:%Y-%m-%d} ({span_days} days, "
            f"{100 * span_days / dev_days:.1f}% of the development period)"
        )
        assert folds[-1].test_end <= exp.periods.holdout_start, "fold crosses the holdout"
        print("Holdout isolation  : OK (no fold boundary reaches the holdout start)")
    return 0


def cmd_robustness(args: argparse.Namespace) -> int:
    """Run the cost/slippage/execution-delay battery on a run's OOS ledger."""
    import polars as pl

    from perp_lab.evaluation.robustness import RobustnessBattery

    run_dir = Path(args.run_dir)
    pattern = args.pattern.format(method=args.method)
    ledgers = list(run_dir.glob(pattern))
    if not ledgers:
        _log.error("No ledger artifacts matching %r under %s", pattern, run_dir)
        return 1

    # Sort by fold *number*: lexicographic order would put fold10 before fold2 and
    # silently concatenate the out-of-sample evidence out of chronological order.
    def _fold_index(path: Path) -> int:
        match = re.search(r"fold(\d+)", path.name)
        return int(match.group(1)) if match else -1

    ledgers.sort(key=_fold_index)
    ledger = pl.concat([pl.read_parquet(p) for p in ledgers], how="vertical_relaxed")
    times = ledger["open_time"].to_list()
    if times != sorted(times):
        _log.error("Concatenated ledger is not chronologically ordered; refusing to analyse.")
        return 1
    _log.info(
        "Loaded %d fold ledger(s) for %s, %d bars, %s -> %s",
        len(ledgers),
        args.method,
        ledger.height,
        times[0],
        times[-1],
    )

    from perp_lab.config import load_experiment_config
    from perp_lab.evaluation.baselines import strategy_versus_baselines
    from perp_lab.evaluation.robustness import block_bootstrap_ci

    # Baselines are priced at the contract rate so they stay a fixed reference,
    # identical for every strategy compared over the same bars.
    exp = load_experiment_config(args.experiment_config)
    battery = RobustnessBattery(ledger=ledger, timeframe=args.timeframe)
    reports = battery.run()
    comparison = strategy_versus_baselines(
        ledger,
        timeframe=args.timeframe,
        fee_bps_per_side=exp.costs.fee_bps_per_side,
        slippage_bps_per_side=exp.costs.slippage.baseline_bps,
    )

    net = ledger["net_return"].cast(pl.Float64).to_numpy()
    bootstrap = {
        f"block_{b}": block_bootstrap_ci(
            net,
            lambda x: float(x.mean() / x.std(ddof=1)) if x.std(ddof=1) > 0 else 0.0,
            block_size=b,
            n_resamples=args.resamples,
            seed=args.seed,
        )
        for b in (24, 168, 720)  # one day, one week, one month of hourly bars
    }

    out_dir = run_dir / "robustness"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"battery_{args.method}.json").write_text(
        json.dumps(battery.to_dict(), indent=2), encoding="utf-8"
    )
    (out_dir / f"baselines_{args.method}.json").write_text(
        json.dumps(comparison, indent=2), encoding="utf-8"
    )
    (out_dir / f"bootstrap_{args.method}.json").write_text(
        json.dumps(bootstrap, indent=2), encoding="utf-8"
    )

    print(f"\n{'scenario':<20}{'parameters':<44}{'total_return':>14}{'sharpe':>10}")
    print("-" * 88)
    for r in reports:
        params = ", ".join(f"{k}={v}" for k, v in r.params.items())
        print(
            f"{r.scenario:<20}{params:<44}"
            f"{r.metrics.get('total_return', float('nan')):>14.4f}"
            f"{r.metrics.get('sharpe', float('nan')):>10.2f}"
        )

    print(
        f"\n{'baseline (same bars, same costs)':<38}{'total_return':>14}{'sharpe':>10}"
        f"{'max_dd':>10}{'exposure':>10}"
    )
    print("-" * 82)
    strat = comparison["strategy"]
    print(
        f"{'>> SEARCHED STRATEGY':<38}{strat.get('total_return', float('nan')):>14.4f}"
        f"{strat.get('sharpe', float('nan')):>10.2f}{strat.get('max_drawdown', float('nan')):>10.2f}"
        f"{strat.get('exposure', float('nan')):>10.2f}"
    )
    for name, m in comparison["baselines"].items():
        print(
            f"{name:<38}{m.get('total_return', float('nan')):>14.4f}"
            f"{m.get('sharpe', float('nan')):>10.2f}{m.get('max_drawdown', float('nan')):>10.2f}"
            f"{m.get('exposure', float('nan')):>10.2f}"
        )

    print(
        f"\n{'block bootstrap of per-bar Sharpe ratio':<40}{'estimate':>10}{'ci_low':>10}"
        f"{'ci_high':>10}{'P(<=0)':>9}"
    )
    print("-" * 79)
    for label, ci in bootstrap.items():
        if not ci:
            continue
        print(
            f"{label + ' bars':<40}{ci['point_estimate']:>10.4f}{ci['ci_low']:>10.4f}"
            f"{ci['ci_high']:>10.4f}{ci['share_non_positive']:>9.2f}"
        )

    print(f"\nWritten: {out_dir}")
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

    p_ms = sub.add_parser(
        "multi-seed",
        parents=[common],
        help="Run the frozen experiment across many seeds and assets (checkpointed).",
    )
    p_ms.add_argument("--config", default="configs/search_development_eth.yaml", type=Path)
    p_ms.add_argument("--symbols", default="BTCUSDT,ETHUSDT", help="Comma-separated symbols.")
    p_ms.add_argument("--n-seeds", default=10, type=int)
    p_ms.add_argument("--base-seed", default=42, type=int, help="The only seed that is recorded.")
    p_ms.add_argument("--study-dir", default=None, type=Path, help="Resume into this directory.")
    p_ms.add_argument("--no-resume", action="store_true", help="Ignore an existing checkpoint.")
    p_ms.add_argument("--metric", default="test_sharpe")
    p_ms.set_defaults(func=cmd_multi_seed)

    p_sr = sub.add_parser(
        "study-robustness",
        parents=[common],
        help="Baselines, bootstrap and cost stress for every unit of a multi-seed study.",
    )
    p_sr.add_argument("study_dir", type=Path)
    p_sr.add_argument("--timeframe", default="1h")
    p_sr.add_argument("--experiment-config", default="configs/experiment.yaml", type=Path)
    p_sr.add_argument("--resamples", default=500, type=int)
    p_sr.set_defaults(func=cmd_study_robustness)

    p_st = sub.add_parser(
        "study-status", parents=[common], help="Show progress of a multi-seed study."
    )
    p_st.add_argument("study_dir", type=Path)
    p_st.add_argument("--events", default=0, type=int, help="Also print the last N events.")
    p_st.set_defaults(func=cmd_study_status)

    p_cat = sub.add_parser(
        "feature-catalogue",
        parents=[common],
        help="Print the causal feature registry (kinds, families, packs, proxies).",
    )
    p_cat.add_argument(
        "--pack",
        choices=["core", "extended", "experimental"],
        default=None,
        help="Restrict the listing to the kinds admitted by this pack (cumulative).",
    )
    p_cat.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    p_cat.set_defaults(func=cmd_feature_catalogue)

    p_geo = sub.add_parser(
        "temporal-geometry",
        parents=[common],
        help="Print every walk-forward fold implied by the experiment contract.",
    )
    p_geo.add_argument("--config", default="configs/experiment.yaml", type=Path)
    p_geo.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    p_geo.set_defaults(func=cmd_temporal_geometry)

    p_rob = sub.add_parser(
        "robustness",
        parents=[common],
        help="Run the cost/slippage/execution-delay battery over a run's OOS ledgers.",
    )
    p_rob.add_argument("run_dir", type=Path, help="artifacts/runs/<run_id> directory.")
    p_rob.add_argument("--experiment-config", default="configs/experiment.yaml", type=Path)
    p_rob.add_argument(
        "--method",
        choices=["random_search", "genetic_algorithm"],
        default="random_search",
        help="Which search engine's out-of-sample ledgers to analyse.",
    )
    p_rob.add_argument(
        "--pattern",
        default="{method}_fold*_test_equity.parquet",
        help="Glob for the per-fold out-of-sample ledgers inside the run directory.",
    )
    p_rob.add_argument("--timeframe", default="1h")
    p_rob.add_argument("--resamples", default=1000, type=int, help="Bootstrap resamples.")
    p_rob.add_argument("--seed", default=42, type=int, help="Bootstrap seed.")
    p_rob.set_defaults(func=cmd_robustness)

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
