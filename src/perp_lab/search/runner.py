"""Fair-comparison runner: Random Search vs the Genetic Algorithm.

Executes one or both algorithms under matched conditions (identical folds,
family, parameter-space version, budget, seeds, objective, costs and funding
requirement), selects each fold's winner on **validation** only, scores those
winners once on **test**, and writes a machine-readable + human-readable
comparison to a run-specific artifact directory.

The comparison metric is the aggregated **out-of-sample test** performance of the
fold winners -- never the in-sample or validation score, and never the frozen
holdout.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from perp_lab.config import Paths, load_data_contract, load_experiment_config
from perp_lab.config.experiment import ExperimentConfig
from perp_lab.config.models import DataContract
from perp_lab.data.splits import resolve_holdout_start
from perp_lab.eda.datasets import DataLake, HoldoutLeakageError
from perp_lab.experiments.pipeline import synthetic_klines
from perp_lab.regimes.models import REGIME_COL, REGIME_NAME_COL
from perp_lab.search.candidate import Candidate, CandidateStatus
from perp_lab.search.config import SearchRunConfig
from perp_lab.search.evaluator import CandidateEvaluator, FoldsBundle, build_folds_data
from perp_lab.search.genetic_algorithm import run_genetic_algorithm
from perp_lab.search.objective import ObjectiveConfig
from perp_lab.search.outcome import SearchOutcome
from perp_lab.search.random_search import run_random_search
from perp_lab.search.registry import SPACE_VERSION, build_search_space
from perp_lab.tracking.run import RunTracker, environment_info, git_state
from perp_lab.utils.logging import add_file_logging, get_logger
from perp_lab.utils.seeds import SeedScheduler, set_global_seed
from perp_lab.utils.timeutils import timeframe_to_timedelta
from perp_lab.validation.walk_forward import (
    WalkForwardFold,
    generate_folds,
    generate_walk_forward,
)

EXPLORATORY_WARNING = (
    "EXPLORATORY RESULT: these metrics come from walk-forward VALIDATION/TEST folds "
    "on the development period only. They are NOT final holdout performance and must "
    "not be reported as the thesis's out-of-sample result."
)

_TEST_METRIC_KEYS = ("sharpe", "total_return", "max_drawdown", "n_trades", "ann_return")


def _synthetic_funding(frame: pl.DataFrame, seed: int, *, interval_hours: int = 8) -> pl.DataFrame:
    """Deterministic, explicitly-labelled synthetic funding fixture (NOT real).

    Funding settles every ``interval_hours`` hours across the bar span with small
    signed rates. Used only for offline smoke tests; never a substitute for real
    funding in a research run.
    """
    rng = np.random.default_rng(seed + 7)
    start = frame["open_time"].min()
    end = frame["open_time"].max()
    assert isinstance(start, datetime) and isinstance(end, datetime)
    times: list[datetime] = []
    t = start
    step = timedelta(hours=interval_hours)
    while t <= end:
        times.append(t)
        t = t + step
    rates = rng.normal(0.0, 1e-4, len(times)).tolist()
    return pl.DataFrame({"funding_time": times, "funding_rate": rates}).with_columns(
        pl.col("funding_time").cast(frame["open_time"].dtype)
    )


@dataclass
class SearchRunResult:
    run_id: str
    run_dir: Path | None
    summary: dict[str, Any]
    outcomes: dict[str, SearchOutcome]
    fold_winners: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    artifact_paths: list[str] = field(default_factory=list)


def _load_data(
    cfg: SearchRunConfig,
    exp: ExperimentConfig,
    contract: DataContract,
    paths: Paths,
    *,
    seed: int,
    log: logging.Logger,
) -> tuple[pl.DataFrame, pl.DataFrame | None, datetime, dict[str, object]]:
    manifests: dict[str, object] = {}
    if cfg.synthetic:
        frame = synthetic_klines(cfg.synthetic_bars, seed=seed, timeframe=cfg.timeframe)
        funding = _synthetic_funding(frame, seed) if cfg.require_funding else None
        manifests["synthetic"] = {
            "row_count": frame.height,
            "sha256": None,
            "funding": funding is not None,
        }
        end = frame["open_time"].max()
        assert isinstance(end, datetime)
        holdout_start = end + timeframe_to_timedelta(cfg.timeframe)
        log.warning("SYNTHETIC SMOKE DATA | %d bars — NOT a research result", frame.height)
        return frame, funding, holdout_start, manifests

    lake = DataLake(contract, paths)
    key = f"{cfg.symbol}:{cfg.timeframe}_development"
    if not lake.available().get(key, False):
        raise FileNotFoundError(
            f"No processed development data for {key}; run 'perp-lab download'."
        )
    holdout_start = resolve_holdout_start(contract)
    _assert_partition_before_holdout(
        paths,
        f"{contract.exchange}_{contract.market_type}_{cfg.symbol}"
        f"_klines_{cfg.timeframe}_development",
        holdout_start=holdout_start,
        log=log,
    )
    loaded = lake.load_klines(cfg.symbol, cfg.timeframe, partition="development")
    frame = loaded.frame
    manifests[loaded.dataset_id] = {"sha256": loaded.sha256, "row_count": frame.height}
    funding = None
    if cfg.require_funding:
        fund = lake.load_funding(cfg.symbol, partition="development")
        funding = fund.frame
        if funding.height == 0:
            raise FileNotFoundError(
                f"Funding required but no development funding rows for {cfg.symbol}. "
                "Refusing to substitute zero funding."
            )
        manifests[fund.dataset_id] = {"sha256": fund.sha256, "row_count": funding.height}
    return frame, funding, holdout_start, manifests


def _assert_partition_before_holdout(
    paths: Paths,
    dataset_id: str,
    *,
    holdout_start: datetime,
    log: logging.Logger,
) -> None:
    """Pre-load guard: prove a development partition ends before the holdout.

    Reads only the committed manifest (metadata, never the frozen rows). Raises
    before any data are read if the requested partition's coverage reaches the
    holdout boundary, so a misconfigured run fails fast and safely.
    """
    manifest_path = paths.manifests_dir / f"{dataset_id}.json"
    if not manifest_path.exists():
        log.warning("no manifest for %s; relying on post-load holdout guard", dataset_id)
        return
    meta = json.loads(manifest_path.read_text(encoding="utf-8"))
    period_end = meta.get("period_end")
    if period_end is None:
        return
    end = datetime.fromisoformat(str(period_end).replace("Z", "+00:00"))
    if end >= holdout_start:
        raise HoldoutLeakageError(
            f"Pre-load guard: development partition '{dataset_id}' period_end={end} "
            f"reaches the frozen holdout start {holdout_start}. Aborting before reading data."
        )


def _build_folds(
    cfg: SearchRunConfig,
    exp: ExperimentConfig,
    frame: pl.DataFrame,
    holdout_start: datetime,
) -> list[WalkForwardFold]:
    step = timeframe_to_timedelta(cfg.timeframe)
    ov = cfg.walk_forward_override
    if ov is not None:
        start = frame["open_time"].min()
        assert isinstance(start, datetime)
        end = frame["open_time"].max()
        assert isinstance(end, datetime)
        dev_end = end + step
        return generate_folds(
            start,
            dev_end,
            initial_train_days=ov.initial_train_days,
            validation_days=ov.validation_days,
            test_days=ov.test_days,
            step_days=ov.step_days,
            purge=exp.purge_bars * step,
            embargo=exp.embargo_bars * step,
            purge_bars=exp.purge_bars,
            embargo_bars=exp.embargo_bars,
            max_folds=ov.max_folds,
        )
    # Without an explicit fold cap the run must cover the whole development
    # period, so the config's min_folds sanity guard is enforced. A capped run is
    # a deliberately bounded pilot and is allowed to emit fewer folds.
    folds = generate_walk_forward(exp, strict=cfg.max_folds is None)
    if cfg.max_folds is not None:
        folds = folds[: cfg.max_folds]
    return folds


def _fold_winners(
    outcome: SearchOutcome,
    evaluator: CandidateEvaluator,
    bundle: FoldsBundle,
    *,
    min_trades_per_fold: int,
) -> list[dict[str, Any]]:
    """Per fold: best VALIDATION sharpe among feasible candidates, then TEST once."""
    winners: list[dict[str, Any]] = []
    feasible = outcome.feasible_candidates()
    for i, fold in enumerate(bundle.folds):
        best: Candidate | None = None
        best_val = float("-inf")
        for cand in feasible:
            if i >= len(cand.fold_metrics):
                continue
            m = cand.fold_metrics[i]
            if float(m.get("n_trades", 0.0)) < min_trades_per_fold:
                continue
            val_sharpe = float(m.get("sharpe", float("-inf")))
            if val_sharpe > best_val:
                best_val, best = val_sharpe, cand
        if best is None:
            winners.append({"fold": fold.index, "winner": None, "reason": "no feasible candidate"})
            continue
        test = evaluator.evaluate_on_test(best, i)
        winners.append(
            {
                "fold": fold.index,
                "winner": best.candidate_id,
                "val_sharpe": best_val,
                "test_metrics": {
                    k: float(test.metrics.get(k, float("nan"))) for k in _TEST_METRIC_KEYS
                },
                "params": {k: _js(v) for k, v in best.active_params.items()},
            }
        )
    return winners


def _js(value: object) -> object:
    return [_js(v) for v in value] if isinstance(value, tuple) else value


def _aggregate_test(winners: list[dict[str, Any]]) -> dict[str, float | int]:
    rows = [w["test_metrics"] for w in winners if w.get("winner") is not None]
    agg: dict[str, float | int] = {"n_fold_winners": len(rows)}
    if not rows:
        return agg
    for k in _TEST_METRIC_KEYS:
        vals = [r[k] for r in rows if r.get(k) is not None and np.isfinite(r[k])]
        agg[f"mean_test_{k}"] = float(np.mean(vals)) if vals else float("nan")
    return agg


def _ledger_frame(candidates: list[Candidate]) -> pl.DataFrame:
    rows = [c.ledger_row() for c in candidates]
    if not rows:
        return pl.DataFrame({"candidate_id": []})
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    columns = {k: [r.get(k) for r in rows] for k in keys}
    return pl.DataFrame(columns)


def run_search(
    cfg: SearchRunConfig,
    *,
    paths: Paths | None = None,
    run_id: str | None = None,
    write_artifacts: bool = True,
    attach_run_file_log: bool = False,
    repo_root: str | Path = ".",
    logger: logging.Logger | None = None,
) -> SearchRunResult:
    """Run Random Search and/or the GA and write the comparison artifacts."""
    log = logger or get_logger("perp_lab.search")
    paths = paths or Paths()
    exp = load_experiment_config(cfg.experiment_config)
    contract = load_data_contract(cfg.data_contract)
    seed = cfg.seed if cfg.seed is not None else exp.random_seed
    set_global_seed(seed)
    # Independent streams per asset / fold / engine, all reconstructible from the
    # single recorded base seed. Giving both engines the same RNG state would not
    # make them comparable; it would only couple them to an arbitrary sequence.
    seeds = SeedScheduler(seed)
    regime_stream = seeds.stream("regime_base", symbol=cfg.symbol, timeframe=cfg.timeframe)
    engine_seeds = {
        name: seeds.stream("engine", symbol=cfg.symbol, timeframe=cfg.timeframe, engine=name)
        for name in ("random_search", "genetic_algorithm")
    }

    tracker: RunTracker | None = None
    if write_artifacts:
        tracker = RunTracker.create(paths.runs_dir, run_id=run_id, prefix=f"search_{cfg.family}")
        if attach_run_file_log:
            add_file_logging(tracker.logs_dir, prefix=f"run_{tracker.run_id}")
    rid = tracker.run_id if tracker else (run_id or "unrecorded")

    frame, funding, holdout_start, manifests = _load_data(
        cfg, exp, contract, paths, seed=seed, log=log
    )
    folds = _build_folds(cfg, exp, frame, holdout_start)
    if len(folds) < 1:
        raise ValueError("Walk-forward geometry produced no folds for this data span.")
    log.info(
        "run_id=%s | %s | family=%s | folds=%d | budget=%d",
        rid,
        cfg.algorithm,
        cfg.family,
        len(folds),
        cfg.budget,
    )

    bundle = build_folds_data(
        frame,
        folds,
        exp=exp,
        family=cfg.family,
        symbol=cfg.symbol,
        timeframe=cfg.timeframe,
        regime_model=cfg.regime_model,
        seed=regime_stream,
        funding=funding,
        holdout_start=holdout_start,
        seeds=seeds,
    )
    space = build_search_space(exp, cfg.family)
    overrides = cfg.objective.as_overrides() if cfg.objective else None
    objective_cfg = ObjectiveConfig.from_experiment(
        exp, require_funding=cfg.require_funding, overrides=overrides
    )
    fee = exp.costs.fee_bps_per_side
    slip = exp.costs.slippage.baseline_bps

    def make_evaluator() -> CandidateEvaluator:
        return CandidateEvaluator(
            bundle,
            space,
            timeframe=cfg.timeframe,
            fee_bps_per_side=fee,
            slippage_bps_per_side=slip,
            days_per_year=exp.annualization_days,
            require_funding=cfg.require_funding,
            objective_cfg=objective_cfg,
        )

    run_rs = cfg.algorithm in ("random_search", "comparison")
    run_ga = cfg.algorithm in ("genetic_algorithm", "comparison")

    outcomes: dict[str, SearchOutcome] = {}
    evaluators: dict[str, CandidateEvaluator] = {}
    fold_winners: dict[str, list[dict[str, Any]]] = {}

    # The GA runs first in a comparison. Its population converges onto genotypes
    # it has already scored, so those proposals hit the evaluator cache and the GA
    # spends FEWER unique objective evaluations than the nominal budget. Random
    # Search never repeats itself and would otherwise receive strictly more
    # evaluations. Capping Random Search at the count the GA actually consumed
    # makes the budgets exactly equal without altering either algorithm: Random
    # Search is a deterministic prefix of its own sequence for a given seed.
    if run_ga:
        ev = make_evaluator()
        outcomes["genetic_algorithm"] = run_genetic_algorithm(
            ev,
            space,
            population_size=cfg.ga.population_size,
            generations=cfg.ga.generations,
            crossover_rate=cfg.ga.crossover_rate,
            mutation_rate=cfg.ga.mutation_rate,
            elitism=cfg.ga.elitism,
            tournament_size=cfg.ga.tournament_size,
            seed=engine_seeds["genetic_algorithm"],
            budget=cfg.budget,
        )
        evaluators["genetic_algorithm"] = ev
        log.info("genetic_algorithm | %s", outcomes["genetic_algorithm"].summary())
    if run_rs:
        rs_budget = cfg.budget
        if run_ga:
            rs_budget = outcomes["genetic_algorithm"].counters.evaluated
            if rs_budget != cfg.budget:
                log.info(
                    "matched budget | GA spent %d of the nominal %d unique evaluations; "
                    "Random Search capped at %d for exact parity",
                    rs_budget,
                    cfg.budget,
                    rs_budget,
                )
        ev = make_evaluator()
        outcomes["random_search"] = run_random_search(
            ev, space, budget=rs_budget, seed=engine_seeds["random_search"]
        )
        evaluators["random_search"] = ev
        log.info("random_search | %s", outcomes["random_search"].summary())

    # Canonical reporting order, independent of execution order.
    order = [n for n in ("random_search", "genetic_algorithm") if n in outcomes]
    outcomes = {n: outcomes[n] for n in order}

    for name, outcome in outcomes.items():
        fold_winners[name] = _fold_winners(
            outcome, evaluators[name], bundle, min_trades_per_fold=objective_cfg.min_trades_per_fold
        )

    seed_schedule = {
        "base_seed": seed,
        "derivation": (
            "numpy SeedSequence, entropy=base_seed, spawn_key=blake2b(stream label); "
            "reconstructible from base_seed alone"
        ),
        "regime_base": regime_stream,
        "engines": engine_seeds,
        "per_fold_regime": {
            str(f.index): seeds.stream(
                "regime", symbol=cfg.symbol, timeframe=cfg.timeframe, fold=f.index
            )
            for f in folds
        },
    }
    summary = _build_summary(
        cfg, exp, seed, folds, bundle, outcomes, fold_winners, seed_schedule=seed_schedule
    )

    artifact_paths: list[str] = []
    if tracker is not None:
        artifact_paths = _write_artifacts(
            tracker,
            cfg=cfg,
            exp=exp,
            seed=seed,
            manifests=manifests,
            bundle=bundle,
            space=space,
            objective_cfg=objective_cfg,
            outcomes=outcomes,
            evaluators=evaluators,
            fold_winners=fold_winners,
            summary=summary,
            repo_root=repo_root,
            log=log,
        )

    return SearchRunResult(
        run_id=rid,
        run_dir=tracker.run_dir if tracker else None,
        summary=summary,
        outcomes=outcomes,
        fold_winners=fold_winners,
        artifact_paths=artifact_paths,
    )


def _coverage(
    cfg: SearchRunConfig, exp: ExperimentConfig, folds: list[WalkForwardFold]
) -> dict[str, Any]:
    """Explicit walk-forward coverage so a run can never be read as a single window.

    Records the concatenated out-of-sample test span and how much of the permitted
    development period it actually covers.
    """
    ov = cfg.walk_forward_override
    geometry = ov if ov is not None else exp.walk_forward
    if ov is not None:
        # A smoke override runs over the loaded frame, not the contract period.
        span_start = folds[0].train_start if folds else exp.periods.development_start
        span_end = folds[-1].test_end if folds else exp.periods.development_end_exclusive
    else:
        span_start = exp.periods.development_start
        span_end = exp.periods.development_end_exclusive
    span_days = (span_end - span_start).days
    oos_days = sum((f.test_end - f.test_start).days for f in folds)
    return {
        "geometry_source": "walk_forward_override" if ov is not None else "experiment_config",
        "scheme": exp.walk_forward.scheme,
        "initial_train_days": geometry.initial_train_days,
        "validation_days": geometry.validation_days,
        "test_days": geometry.test_days,
        "step_days": geometry.step_days,
        "max_folds_cap": cfg.max_folds if ov is None else ov.max_folds,
        "development_start": span_start.isoformat(),
        "development_end_exclusive": span_end.isoformat(),
        "development_days": span_days,
        "n_folds": len(folds),
        "oos_test_start": folds[0].test_start.isoformat() if folds else None,
        "oos_test_end": folds[-1].test_end.isoformat() if folds else None,
        "oos_test_days": oos_days,
        "oos_fraction_of_development": round(oos_days / span_days, 6) if span_days else None,
        "purge_bars": exp.purge_bars,
        "embargo_bars": exp.embargo_bars,
    }


def _with_regime(ledger: pl.DataFrame, test_frame: pl.DataFrame) -> pl.DataFrame:
    """Attach the fold's train-fitted regime label to a persisted OOS ledger.

    The label is produced by a model fitted on that fold's TRAIN slice only, so
    carrying it into the test ledger stays causal. It is needed to report
    out-of-sample performance conditional on market state.
    """
    if REGIME_NAME_COL not in test_frame.columns or "open_time" not in ledger.columns:
        return ledger
    cols = [c for c in (REGIME_COL, REGIME_NAME_COL) if c in test_frame.columns]
    return ledger.join(test_frame.select("open_time", *cols), on="open_time", how="left")


def _build_summary(
    cfg: SearchRunConfig,
    exp: ExperimentConfig,
    seed: int,
    folds: list[WalkForwardFold],
    bundle: FoldsBundle,
    outcomes: dict[str, SearchOutcome],
    fold_winners: dict[str, list[dict[str, Any]]],
    seed_schedule: dict[str, Any] | None = None,
) -> dict[str, Any]:
    methods: dict[str, Any] = {}
    for name, outcome in outcomes.items():
        methods[name] = {
            **outcome.summary(),
            "aggregate_test": _aggregate_test(fold_winners[name]),
            "diversity": outcome.extra.get("diversity"),
        }
    evaluated = {n: o.counters.evaluated for n, o in outcomes.items()}
    budget_parity = {
        "nominal_budget": cfg.budget,
        "evaluated_per_method": evaluated,
        "equal_effective_budget": len(set(evaluated.values())) <= 1,
        "definition": (
            "unique objective evaluations actually consumed; the GA's cache hits on "
            "already-scored genotypes do not count, and Random Search is capped at the "
            "GA's consumed count so both methods spend an identical budget"
        ),
    }
    verdict = None
    if "random_search" in methods and "genetic_algorithm" in methods:
        rs_oos = methods["random_search"]["aggregate_test"].get("mean_test_sharpe")
        ga_oos = methods["genetic_algorithm"]["aggregate_test"].get("mean_test_sharpe")
        if (
            rs_oos is not None
            and ga_oos is not None
            and np.isfinite(rs_oos)
            and np.isfinite(ga_oos)
        ):
            verdict = "genetic_algorithm" if ga_oos > rs_oos else "random_search"
    return {
        "run_kind": "search_comparison",
        "label": cfg.label,
        "family": cfg.family,
        "algorithm": cfg.algorithm,
        "symbol": cfg.symbol,
        "timeframe": cfg.timeframe,
        "seed": seed,
        "seed_schedule": seed_schedule or {"base_seed": seed},
        "budget": cfg.budget,
        "space_version": SPACE_VERSION,
        "n_folds": len(folds),
        "walk_forward_coverage": _coverage(cfg, exp, folds),
        "budget_parity": budget_parity,
        "fair_budget": "budget caps UNIQUE objective evaluations; invalid/duplicate/cached excluded",
        "comparison_metric": "aggregate out-of-sample TEST sharpe of per-fold winners",
        "methods": methods,
        "best_out_of_sample_method": verdict,
        "warning": EXPLORATORY_WARNING,
    }


def _write_artifacts(
    tracker: RunTracker,
    *,
    cfg: SearchRunConfig,
    exp: ExperimentConfig,
    seed: int,
    manifests: dict[str, object],
    bundle: FoldsBundle,
    space: Any,
    objective_cfg: ObjectiveConfig,
    outcomes: dict[str, SearchOutcome],
    evaluators: dict[str, CandidateEvaluator],
    fold_winners: dict[str, list[dict[str, Any]]],
    summary: dict[str, Any],
    repo_root: str | Path,
    log: logging.Logger,
) -> list[str]:
    gs = git_state(repo_root)
    written: list[Path] = [
        tracker.write_yaml("resolved_experiment_config.yaml", exp.model_dump(mode="json")),
        tracker.write_json("search_config.json", cfg.model_dump(mode="json")),
        tracker.write_json(
            "algorithms.json",
            {
                name: {"version": o.version, "seed": o.seed, "budget": o.budget}
                for name, o in outcomes.items()
            },
        ),
        tracker.write_json("dataset_manifests.json", manifests),
        tracker.write_json("feature_manifest.json", bundle.feature_manifest),
        tracker.write_json("search_space.json", space.describe()),
        tracker.write_json("objective.json", objective_cfg.to_dict()),
        tracker.write_json(
            "folds.json",
            {
                "regime_inputs": bundle.regime_inputs,
                "folds": [
                    {**fd.fold.to_dict(), "regime_params": fd.regime_params} for fd in bundle.folds
                ],
            },
        ),
        tracker.write_json("seed_schedule.json", summary["seed_schedule"]),
        tracker.write_json("environment.json", environment_info()),
        tracker.write_json("git_state.json", gs),
        tracker.write_json("warnings.json", {"exploratory": EXPLORATORY_WARNING}),
        tracker.write_json("comparison_summary.json", summary),
    ]

    for name, outcome in outcomes.items():
        written.append(
            tracker.write_parquet(f"{name}_candidates.parquet", _ledger_frame(outcome.candidates))
        )
        failed = [
            {"candidate_id": c.candidate_id, "status": c.status.value, "reason": c.failure_reason}
            for c in outcome.candidates
            if c.status != CandidateStatus.EVALUATED
        ]
        written.append(
            tracker.write_json(
                f"{name}_failed_candidates.json", {"count": len(failed), "candidates": failed}
            )
        )
        written.append(tracker.write_json(f"{name}_fold_winners.json", fold_winners[name]))
        written.append(
            tracker.write_json(
                f"{name}_convergence.json", {"best_fitness_after_each_eval": outcome.convergence}
            )
        )
        if outcome.algorithm == "genetic_algorithm":
            written.append(tracker.write_json("ga_lineage.json", outcome.extra.get("lineage", [])))
            written.append(
                tracker.write_json(
                    "ga_diversity.json",
                    {
                        "generation_best": outcome.extra.get("generation_best"),
                        "diversity": outcome.extra.get("diversity"),
                    },
                )
            )

    # Fold-winner TEST outputs (positions/trades/equity) for EVERY method. Both
    # methods must persist their out-of-sample series, otherwise the concatenated
    # walk-forward OOS evidence can only be rebuilt for one of them and the
    # RS-vs-GA comparison is not auditable at the series level.
    for method, outcome in outcomes.items():
        ev = evaluators[method]
        by_id = {c.candidate_id: c for c in outcome.candidates}
        for w in fold_winners[method]:
            if w.get("winner") is None:
                continue
            cand = by_id[w["winner"]]
            fold_index = int(w["fold"])
            result = ev.evaluate_on_test(cand, fold_index)
            tag = f"{method}_fold{fold_index}"
            ledger = _with_regime(result.ledger, bundle.folds[fold_index].test)
            written.append(tracker.write_parquet(f"{tag}_test_equity.parquet", ledger))
            trades = result.trades()
            if trades.height:
                written.append(tracker.write_parquet(f"{tag}_test_trades.parquet", trades))

    report = _human_report(summary)
    written.append(tracker.path("comparison_report.md"))
    tracker.path("comparison_report.md").write_text(report, encoding="utf-8")

    metrics_payload = {
        "run_id": tracker.run_id,
        "seed": seed,
        "git_commit": gs["commit"],
        "git_dirty": gs["dirty"],
        "summary": summary,
    }
    written.append(tracker.write_json("metrics.json", metrics_payload))

    out = [str(p) for p in written]
    log.info("artifacts | run_dir=%s | %d files", tracker.run_dir, len(out))
    return out


def _human_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Strategy-search comparison report",
        "",
        f"- Label: **{summary['label']}**",
        f"- Family: `{summary['family']}`  |  Algorithm: `{summary['algorithm']}`",
        f"- Symbol/timeframe: {summary['symbol']} {summary['timeframe']}  |  Seed: {summary['seed']}",
        f"- Budget (unique evaluations): {summary['budget']}  |  Folds: {summary['n_folds']}",
        f"- Comparison metric: {summary['comparison_metric']}",
        f"- Fair budget: {summary['fair_budget']}",
        "",
        f"> {summary['warning']}",
        "",
        "## Methods",
        "",
        "| method | evaluated | feasible | best val fitness | mean OOS test sharpe |",
        "|---|---|---|---|---|",
    ]
    for name, m in summary["methods"].items():
        agg = m["aggregate_test"]
        lines.append(
            f"| {name} | {m['counters']['evaluated']} | {m['n_feasible']} | "
            f"{_fmt(m['best_fitness'])} | {_fmt(agg.get('mean_test_sharpe'))} |"
        )
    lines += ["", f"**Best out-of-sample method:** {summary.get('best_out_of_sample_method')}", ""]
    return "\n".join(lines)


def _fmt(x: object) -> str:
    if isinstance(x, int | float) and np.isfinite(float(x)):
        return f"{float(x):.4f}"
    return "n/a"
