"""Fair-comparison runner: Random Search vs the Genetic Algorithm.

Executes one or both algorithms under matched conditions (identical folds,
family, parameter-space version, budget, seeds, objective, costs and funding
requirement), selects each fold's winner on **validation** only, scores those
winners once on **test**, and writes a machine-readable + human-readable
comparison to a run-specific artifact directory.

**Temporal contract (ADR 0012).** Search is run *independently inside every outer
walk-forward fold*. Each fold gets its own evaluator, built from a bundle holding
only that fold, its own RNG streams and its own full effective budget, so a
candidate's fitness is a function of that fold's validation window alone. Nothing
computed on a later fold can reach an earlier fold's selection. Within a fold the
order is strict and irreversible: search on validation, **freeze** the winner
(recording a fingerprint of the selection), then score it once on that fold's
test slice. The test result is never fed back into fitness, ranking or any
subsequent decision.

The comparison metric is the aggregated **out-of-sample test** performance of the
fold winners -- never the in-sample or validation score, and never the frozen
holdout.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from perp_lab.backtesting.engine import BacktestResult
from perp_lab.config import Paths, load_data_contract, load_experiment_config
from perp_lab.config.experiment import ExperimentConfig
from perp_lab.config.models import DataContract
from perp_lab.data.splits import resolve_holdout_start
from perp_lab.eda.datasets import DataLake, HoldoutLeakageError
from perp_lab.experiments.pipeline import synthetic_klines
from perp_lab.regimes.models import REGIME_COL, REGIME_NAME_COL
from perp_lab.search.candidate import Candidate, CandidateStatus
from perp_lab.search.config import SearchRunConfig
from perp_lab.search.evaluator import (
    CandidateEvaluator,
    FoldsBundle,
    build_folds_data,
    single_fold_bundle,
)
from perp_lab.search.genetic_algorithm import run_genetic_algorithm
from perp_lab.search.objective import ObjectiveConfig
from perp_lab.search.outcome import Counters, SearchOutcome
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

# Identifies the temporal contract a set of artifacts was produced under. Results
# from a different protocol describe a different experiment and must never be
# pooled with these; see ADR 0012.
SEARCH_PROTOCOL = "independent_search_per_outer_fold"
ARTIFACT_SCHEMA_VERSION = 2

ENGINE_NAMES = ("random_search", "genetic_algorithm")

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
class FoldEngineOutcome:
    """One engine's complete, isolated search inside one outer fold."""

    fold_index: int
    engine: str
    outcome: SearchOutcome
    winner: dict[str, Any]
    # Kept from the single test evaluation so artifact writing never re-runs it.
    test_result: BacktestResult | None
    seconds: float


@dataclass
class SearchRunResult:
    run_id: str
    run_dir: Path | None
    summary: dict[str, Any]
    outcomes: dict[str, SearchOutcome]
    fold_winners: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    artifact_paths: list[str] = field(default_factory=list)
    # The primary structure: one independent search per (engine, outer fold).
    # ``outcomes`` is the merged, report-oriented view of the same runs.
    fold_outcomes: dict[str, list[FoldEngineOutcome]] = field(default_factory=dict)


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


def _load_reference_bars(
    cfg: SearchRunConfig,
    exp: ExperimentConfig,
    contract: DataContract,
    paths: Paths,
    *,
    seed: int,
    log: logging.Logger,
) -> pl.DataFrame | None:
    """Load the second asset for a cross-asset family, from development only.

    Returns ``None`` for every other family, so no run pays for data it does not
    use. The holdout guard is applied to the reference exactly as it is to the
    traded asset: a cross-asset strategy could otherwise read the frozen partition
    through the back door of its reference symbol.
    """
    reference_map = exp.strategies.families.cross_asset.reference_symbol
    reference_symbol = reference_map.get(cfg.symbol)
    if cfg.family != "BTC_ETH_confirmation" or reference_symbol is None:
        return None

    if cfg.synthetic:
        # A second synthetic series, correlated with neither the first nor the
        # market. Smoke data only; it proves the wiring, never a result.
        return synthetic_klines(cfg.synthetic_bars, seed=seed + 1, timeframe=cfg.timeframe)

    lake = DataLake(contract, paths)
    key = f"{reference_symbol}:{cfg.timeframe}_development"
    if not lake.available().get(key, False):
        raise FileNotFoundError(
            f"Family {cfg.family!r} trades {cfg.symbol} confirmed by {reference_symbol}, but no "
            f"processed development data exists for {key}; run 'perp-lab download'."
        )
    _assert_partition_before_holdout(
        paths,
        f"{contract.exchange}_{contract.market_type}_{reference_symbol}"
        f"_klines_{cfg.timeframe}_development",
        holdout_start=resolve_holdout_start(contract),
        log=log,
    )
    loaded = lake.load_klines(reference_symbol, cfg.timeframe, partition="development")
    log.info(
        "cross-asset reference | %s confirmed by %s | %d bars",
        cfg.symbol,
        reference_symbol,
        loaded.frame.height,
    )
    return loaded.frame


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


def _select_fold_winner(
    outcome: SearchOutcome, *, min_trades_per_fold: int
) -> tuple[Candidate | None, float]:
    """Pick a fold's winner from its own VALIDATION results only.

    The outcome belongs to a single-fold search, so every candidate carries
    exactly one validation record: the one for this fold. No test metric, and no
    other fold's metric, is reachable from here.
    """
    best: Candidate | None = None
    best_val = float("-inf")
    for cand in outcome.feasible_candidates():
        if not cand.fold_metrics:
            continue
        m = cand.fold_metrics[0]
        if float(m.get("n_trades", 0.0)) < min_trades_per_fold:
            continue
        val_sharpe = float(m.get("sharpe", float("-inf")))
        if val_sharpe > best_val:
            best_val, best = val_sharpe, cand
    return best, best_val


def _freeze_winner(candidate: Candidate | None, *, fold_index: int, val_sharpe: float) -> dict:
    """Seal a fold's selection **before** its test slice is ever touched.

    The fingerprint covers the identity and parameters of the selected candidate.
    Recording it prior to the test evaluation is what makes "the strategy was
    chosen without seeing its out-of-sample data" an auditable fact rather than a
    claim: any later change to the winner would change this hash.
    """
    if candidate is None:
        return {
            "fold": fold_index,
            "winner": None,
            "reason": "no feasible candidate",
            "selection_basis": "validation_only",
        }
    params = {k: _js(v) for k, v in candidate.active_params.items()}
    payload = json.dumps(
        {"fold": fold_index, "candidate_id": candidate.candidate_id, "params": params},
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "fold": fold_index,
        "winner": candidate.candidate_id,
        "val_sharpe": val_sharpe,
        "params": params,
        "selection_basis": "validation_only",
        "selection_fingerprint": hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16],
        "frozen_before_test": True,
    }


def _merge_fold_outcomes(engine: str, fold_outcomes: list[FoldEngineOutcome]) -> SearchOutcome:
    """Collapse a engine's per-fold searches into one reporting view.

    Counters add up, candidates are concatenated (each tagged with the fold whose
    search produced it) and convergence traces are kept separated per fold.
    Fitness values are **not** pooled: they are computed on different validation
    windows and a maximum across them would be a comparison between different
    quantities, so ``best`` is deliberately left unset.
    """
    ordered = sorted(fold_outcomes, key=lambda f: f.fold_index)
    counters = Counters()
    candidates: list[Candidate] = []
    for fo in ordered:
        c = fo.outcome.counters
        counters.proposed += c.proposed
        counters.invalid += c.invalid
        counters.duplicate += c.duplicate
        counters.cached += c.cached
        counters.evaluated += c.evaluated
        candidates.extend(fo.outcome.candidates)
    first = ordered[0].outcome
    return SearchOutcome(
        algorithm=engine,
        version=first.version,
        seed=first.seed,
        budget=first.budget,
        candidates=candidates,
        counters=counters,
        convergence=[],
        best=None,
        extra={
            "protocol": SEARCH_PROTOCOL,
            "n_folds_searched": len(ordered),
            "budget_per_fold": first.budget,
            "seed_per_fold": {str(f.fold_index): f.outcome.seed for f in ordered},
            "convergence_per_fold": {str(f.fold_index): f.outcome.convergence for f in ordered},
            "best_fitness_per_fold": {
                str(f.fold_index): (f.outcome.best.fitness if f.outcome.best else None)
                for f in ordered
            },
            "termination_per_fold": {
                str(f.fold_index): f.outcome.extra.get("termination_reason") for f in ordered
            },
            "seconds_per_fold": {str(f.fold_index): f.seconds for f in ordered},
            "generation_best_per_fold": {
                str(f.fold_index): f.outcome.extra.get("generation_best") for f in ordered
            },
            "diversity_per_fold": {
                str(f.fold_index): f.outcome.extra.get("diversity") for f in ordered
            },
            "lineage_per_fold": {
                str(f.fold_index): f.outcome.extra.get("lineage") for f in ordered
            },
        },
    )


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
        "run_id=%s | %s | family=%s | folds=%d | budget=%d per fold | protocol=%s",
        rid,
        cfg.algorithm,
        cfg.family,
        len(folds),
        cfg.budget,
        SEARCH_PROTOCOL,
    )

    reference_bars = _load_reference_bars(cfg, exp, contract, paths, seed=seed, log=log)
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
        reference_bars=reference_bars,
        reference_symbol=exp.strategies.families.cross_asset.reference_symbol.get(cfg.symbol),
    )
    space = build_search_space(exp, cfg.family, cfg.symbol)
    overrides = cfg.objective.as_overrides() if cfg.objective else None
    objective_cfg = ObjectiveConfig.from_experiment(
        exp, require_funding=cfg.require_funding, overrides=overrides
    )
    fee = exp.costs.fee_bps_per_side
    slip = exp.costs.slippage.baseline_bps

    # The objective is now applied inside a single fold, so the study-level
    # minimum trade count must be expressed per fold. Requiring total/n_folds in
    # every fold guarantees the pooled total still clears the configured floor,
    # whereas demanding the full total inside one validation window would reject
    # nearly every candidate and silently empty the search.
    n_folds = len(bundle.folds)
    fold_objective_cfg = replace(
        objective_cfg,
        min_trades_total=math.ceil(objective_cfg.min_trades_total / n_folds),
    )

    def make_evaluator(fold_bundle: FoldsBundle) -> CandidateEvaluator:
        return CandidateEvaluator(
            fold_bundle,
            space,
            timeframe=cfg.timeframe,
            fee_bps_per_side=fee,
            slippage_bps_per_side=slip,
            days_per_year=exp.annualization_days,
            require_funding=cfg.require_funding,
            objective_cfg=fold_objective_cfg,
            reference_bars=reference_bars,
        )

    engines = [
        name for name in ENGINE_NAMES if cfg.algorithm == "comparison" or cfg.algorithm == name
    ]

    fold_outcomes: dict[str, list[FoldEngineOutcome]] = {name: [] for name in engines}
    fold_engine_seeds: dict[str, dict[str, int]] = {name: {} for name in engines}

    # One independent search environment per outer fold. Every engine receives the
    # SAME full effective budget inside EVERY fold, so the comparison holds at the
    # level where selection actually happens rather than only on average.
    for fd in bundle.folds:
        fold_bundle = single_fold_bundle(bundle, fd.index)
        per_engine: dict[str, SearchOutcome] = {}
        per_engine_ev: dict[str, CandidateEvaluator] = {}
        per_engine_secs: dict[str, float] = {}

        for name in engines:
            ev = make_evaluator(fold_bundle)
            engine_seed = seeds.stream(
                "engine",
                symbol=cfg.symbol,
                timeframe=cfg.timeframe,
                engine=name,
                fold=fd.index,
            )
            fold_engine_seeds[name][str(fd.index)] = engine_seed
            started = time.perf_counter()
            if name == "random_search":
                out = run_random_search(ev, space, budget=cfg.budget, seed=engine_seed)
            else:
                out = run_genetic_algorithm(
                    ev,
                    space,
                    population_size=cfg.ga.population_size,
                    max_generations=cfg.ga.max_generations,
                    crossover_rate=cfg.ga.crossover_rate,
                    mutation_rate=cfg.ga.mutation_rate,
                    elitism=cfg.ga.elitism,
                    tournament_size=cfg.ga.tournament_size,
                    seed=engine_seed,
                    budget=cfg.budget,
                )
            per_engine_secs[name] = time.perf_counter() - started
            for cand in out.candidates:
                cand.fold_index = fd.index
            per_engine[name] = out
            per_engine_ev[name] = ev

        # Parity is checked inside the fold. An engine that searched less here has
        # not been compared at equal effort here, and a run-level average would
        # hide exactly that.
        _assert_budget_parity(per_engine, target=cfg.budget, fold_index=fd.index)

        for name in engines:
            outcome = per_engine[name]
            candidate, val_sharpe = _select_fold_winner(
                outcome, min_trades_per_fold=fold_objective_cfg.min_trades_per_fold
            )
            # Freeze first, evaluate second. The order is the guarantee.
            winner = _freeze_winner(candidate, fold_index=fd.index, val_sharpe=val_sharpe)
            test_result: BacktestResult | None = None
            if candidate is not None:
                test_result = per_engine_ev[name].evaluate_on_test(candidate, fd.index)
                winner["test_metrics"] = {
                    k: float(test_result.metrics.get(k, float("nan"))) for k in _TEST_METRIC_KEYS
                }
            fold_outcomes[name].append(
                FoldEngineOutcome(
                    fold_index=fd.index,
                    engine=name,
                    outcome=outcome,
                    winner=winner,
                    test_result=test_result,
                    seconds=per_engine_secs[name],
                )
            )
        log.info(
            "fold %d/%d searched independently | %s",
            fd.index + 1,
            n_folds,
            {n: per_engine[n].counters.evaluated for n in engines},
        )

    outcomes = {name: _merge_fold_outcomes(name, fold_outcomes[name]) for name in engines}
    fold_winners = {
        name: [fo.winner for fo in sorted(fold_outcomes[name], key=lambda f: f.fold_index)]
        for name in engines
    }
    for name in engines:
        log.info("%s | %s", name, outcomes[name].summary())

    seed_schedule = {
        "base_seed": seed,
        "derivation": (
            "numpy SeedSequence, entropy=base_seed, spawn_key=blake2b(stream label); "
            "reconstructible from base_seed alone"
        ),
        "regime_base": regime_stream,
        # Each fold's search draws from its own stream, so a fold's result cannot
        # depend on how many draws an earlier fold happened to consume.
        "engines_per_fold": fold_engine_seeds,
        "per_fold_regime": {
            str(f.index): seeds.stream(
                "regime", symbol=cfg.symbol, timeframe=cfg.timeframe, fold=f.index
            )
            for f in folds
        },
    }
    summary = _build_summary(
        cfg,
        exp,
        seed,
        folds,
        outcomes,
        fold_winners,
        fold_outcomes,
        objective_cfg=objective_cfg,
        fold_objective_cfg=fold_objective_cfg,
        seed_schedule=seed_schedule,
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
            objective_cfg=fold_objective_cfg,
            outcomes=outcomes,
            fold_outcomes=fold_outcomes,
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
        fold_outcomes=fold_outcomes,
    )


class BudgetParityError(RuntimeError):
    """An engine did not spend exactly the configured effective budget."""


def _assert_budget_parity(
    outcomes: dict[str, SearchOutcome], *, target: int, fold_index: int
) -> None:
    """Fail the fold unless every engine spent exactly the configured budget in it.

    Parity has to hold where selection happens. Two engines that each spend the
    right total across the run but differ inside a given fold were not compared at
    equal effort on the decision that fold made, and averaging conceals it.
    """
    short = {
        name: {
            "target": target,
            "consumed": o.counters.evaluated,
            "proposed": o.counters.proposed,
            "invalid": o.counters.invalid,
            "duplicate": o.counters.duplicate,
            "cached": o.counters.cached,
            "termination_reason": o.extra.get("termination_reason"),
        }
        for name, o in outcomes.items()
        if o.counters.evaluated != target
    }
    if short:
        raise BudgetParityError(
            f"In outer fold {fold_index} every engine must spend exactly {target} unique "
            f"objective evaluations. These did not: {short}. Raise ga.max_generations, "
            "widen the search space, or lower effective_budget."
        )


def _budget_report(
    fold_outcomes: dict[str, list[FoldEngineOutcome]], *, target: int, n_folds: int
) -> dict[str, Any]:
    """Everything needed to audit that the comparison was run at equal budget."""
    per_engine: dict[str, Any] = {}
    for name, folds in fold_outcomes.items():
        ordered = sorted(folds, key=lambda f: f.fold_index)
        per_fold = {
            str(f.fold_index): {
                "target": target,
                "consumed": f.outcome.counters.evaluated,
                "proposed": f.outcome.counters.proposed,
                "invalid": f.outcome.counters.invalid,
                "duplicate": f.outcome.counters.duplicate,
                "cached": f.outcome.counters.cached,
                "attempts": f.outcome.extra.get("attempts"),
                "generations_run": f.outcome.extra.get("generations_run"),
                "termination_reason": f.outcome.extra.get("termination_reason"),
                "seconds": round(f.seconds, 4),
            }
            for f in ordered
        }
        per_engine[name] = {
            "budget_per_fold": target,
            "n_folds_searched": len(ordered),
            "total_unique_evaluations": sum(f.outcome.counters.evaluated for f in ordered),
            "total_seconds": round(sum(f.seconds for f in ordered), 4),
            "reached_target_in_every_fold": all(
                f.outcome.counters.evaluated == target for f in ordered
            ),
            "per_fold": per_fold,
        }
    totals = {name: payload["total_unique_evaluations"] for name, payload in per_engine.items()}
    return {
        "effective_budget_per_fold": target,
        "n_folds": n_folds,
        "per_engine": per_engine,
        "total_evaluations_per_engine": totals,
        "equal_effective_budget": len(set(totals.values())) <= 1,
        "all_engines_reached_target": all(
            payload["reached_target_in_every_fold"] for payload in per_engine.values()
        ),
        "parity_level": "per outer fold",
        "definition": (
            "budget counts UNIQUE, VALID, NON-CACHED objective evaluations and is "
            "spent in full INSIDE EVERY outer fold. Invalid proposals, duplicates and "
            "cache hits do not consume it. Each engine generates until it reaches the "
            "configured target in that fold or hits its explicit attempt cap, in which "
            "case the run fails rather than reporting a short search as complete."
        ),
    }


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


def _protocol_record(
    cfg: SearchRunConfig,
    n_folds: int,
    objective_cfg: ObjectiveConfig,
    fold_objective_cfg: ObjectiveConfig,
) -> dict[str, Any]:
    """The temporal contract these artifacts were produced under (ADR 0012)."""
    return {
        "protocol": SEARCH_PROTOCOL,
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "adr": "0012-outer-fold-contamination-in-candidate-search",
        "description": (
            "Search runs independently inside every outer walk-forward fold. A "
            "candidate's fitness is computed on that fold's validation window alone, "
            "so no chronologically later fold can influence an earlier selection. "
            "Each fold's winner is frozen (fingerprinted) on validation before its "
            "test slice is evaluated once."
        ),
        "fitness_scope": "single outer fold validation window",
        "selection_scope": "single outer fold validation window",
        "test_usage": "scored once per fold, after freezing; never an input to search",
        "budget_per_fold": cfg.budget,
        "n_folds": n_folds,
        "total_unique_evaluations_per_engine": cfg.budget * n_folds,
        "dispersion_penalty_source": (
            "standard deviation of Sharpe across contiguous sub-blocks WITHIN the "
            "fold's validation window; across-fold spread is unobservable inside an "
            "isolated fold"
        ),
        "stability_blocks": fold_objective_cfg.stability_blocks,
        "min_trades_total_configured": objective_cfg.min_trades_total,
        "min_trades_total_per_fold": fold_objective_cfg.min_trades_total,
        "min_trades_total_rescaling": (
            "ceil(min_trades_total / n_folds), so the pooled total across folds still "
            "clears the configured study-level floor"
        ),
        "supersedes": "pooled-across-folds fitness (contaminated; results not poolable)",
    }


def _build_summary(
    cfg: SearchRunConfig,
    exp: ExperimentConfig,
    seed: int,
    folds: list[WalkForwardFold],
    outcomes: dict[str, SearchOutcome],
    fold_winners: dict[str, list[dict[str, Any]]],
    fold_outcomes: dict[str, list[FoldEngineOutcome]],
    *,
    objective_cfg: ObjectiveConfig,
    fold_objective_cfg: ObjectiveConfig,
    seed_schedule: dict[str, Any] | None = None,
) -> dict[str, Any]:
    methods: dict[str, Any] = {}
    for name, outcome in outcomes.items():
        per_fold_best = outcome.extra.get("best_fitness_per_fold", {})
        values = [v for v in per_fold_best.values() if v is not None and np.isfinite(v)]
        methods[name] = {
            **outcome.summary(),
            # Validation fitness is computed on a different window in each fold, so
            # the only defensible scalar is an average over folds, not a maximum.
            "best_fitness": float(np.mean(values)) if values else None,
            "best_fitness_semantics": "mean over folds of each fold's best validation fitness",
            "best_fitness_per_fold": per_fold_best,
            "seconds_per_fold": outcome.extra.get("seconds_per_fold"),
            "aggregate_test": _aggregate_test(fold_winners[name]),
        }
    budget_parity = _budget_report(fold_outcomes, target=cfg.budget, n_folds=len(folds))
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
        "search_protocol": SEARCH_PROTOCOL,
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "protocol": _protocol_record(cfg, len(folds), objective_cfg, fold_objective_cfg),
        "walk_forward_coverage": _coverage(cfg, exp, folds),
        "budget_parity": budget_parity,
        "fair_budget": (
            "budget caps UNIQUE objective evaluations and is spent in full inside "
            "EVERY outer fold; invalid/duplicate/cached excluded"
        ),
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
    fold_outcomes: dict[str, list[FoldEngineOutcome]],
    fold_winners: dict[str, list[dict[str, Any]]],
    summary: dict[str, Any],
    repo_root: str | Path,
    log: logging.Logger,
) -> list[str]:
    gs = git_state(repo_root)
    written: list[Path] = [
        tracker.write_yaml("resolved_experiment_config.yaml", exp.model_dump(mode="json")),
        tracker.write_json("search_config.json", cfg.model_dump(mode="json")),
        tracker.write_json("search_protocol.json", summary["protocol"]),
        tracker.write_json(
            "algorithms.json",
            {
                name: {
                    "version": o.version,
                    "budget_per_fold": o.budget,
                    "seed_per_fold": o.extra.get("seed_per_fold"),
                    "protocol": SEARCH_PROTOCOL,
                }
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
        # Convergence is recorded per fold. A single concatenated trace would splice
        # together fitness values measured on different validation windows, which is
        # not a curve of anything.
        written.append(
            tracker.write_json(
                f"{name}_convergence.json",
                {
                    "protocol": SEARCH_PROTOCOL,
                    "per_fold": outcome.extra.get("convergence_per_fold", {}),
                },
            )
        )
        if outcome.algorithm == "genetic_algorithm":
            written.append(
                tracker.write_json("ga_lineage.json", outcome.extra.get("lineage_per_fold", {}))
            )
            written.append(
                tracker.write_json(
                    "ga_diversity.json",
                    {
                        "protocol": SEARCH_PROTOCOL,
                        "generation_best_per_fold": outcome.extra.get("generation_best_per_fold"),
                        "diversity_per_fold": outcome.extra.get("diversity_per_fold"),
                    },
                )
            )

    # Fold-winner TEST outputs (positions/trades/equity) for EVERY method, taken
    # from the single evaluation performed after the winner was frozen. Re-running
    # the backtest here would be a second, unaccounted contact with the fold's
    # out-of-sample data.
    fold_by_index = {fd.index: fd for fd in bundle.folds}
    for method, per_fold in fold_outcomes.items():
        for fo in sorted(per_fold, key=lambda f: f.fold_index):
            if fo.test_result is None:
                continue
            tag = f"{method}_fold{fo.fold_index}"
            ledger = _with_regime(fo.test_result.ledger, fold_by_index[fo.fold_index].test)
            written.append(tracker.write_parquet(f"{tag}_test_equity.parquet", ledger))
            trades = fo.test_result.trades()
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
        f"- Budget per outer fold (unique evaluations): {summary['budget']}"
        f"  |  Folds: {summary['n_folds']}",
        f"- Search protocol: `{summary['search_protocol']}` (ADR 0012)",
        f"- Comparison metric: {summary['comparison_metric']}",
        f"- Fair budget: {summary['fair_budget']}",
        "",
        f"> {summary['warning']}",
        "",
        "Each outer fold was searched independently: fitness never crosses folds and "
        "every fold's winner was frozen on validation before its test slice was scored.",
        "",
        "## Methods",
        "",
        "| method | evaluations (all folds) | feasible | mean best val fitness | "
        "mean OOS test sharpe |",
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
