"""First executable vertical slice of the experimental pipeline.

Chains: data loading -> dataset manifest verification -> holdout guard ->
causal features -> momentum signals -> next-bar cost-aware backtest -> metrics
-> artifacts. Orchestration lives here (a tested library function); the CLI only
parses arguments, configures logging and calls :func:`run_dev_pipeline`.

Every run (unless disabled) is recorded under ``artifacts/runs/<run_id>/`` via
:class:`perp_lab.tracking.RunTracker`, tying the resolved config, dataset hashes,
git state, environment, seed, metrics, feature metadata, trades and equity to a
single run id.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl

from perp_lab.backtesting.engine import BacktestResult, run_backtest
from perp_lab.config.experiment import ExperimentConfig
from perp_lab.config.models import DataContract, Paths
from perp_lab.data.manifest import read_manifest
from perp_lab.data.providers.base import KLINE_SCHEMA
from perp_lab.data.splits import resolve_holdout_start
from perp_lab.eda.datasets import DataLake, assert_no_holdout
from perp_lab.features.manifest import build_feature_manifest
from perp_lab.features.registry import (
    build_feature_frame,
    feature_columns,
    resolve_feature_set,
    specs_to_metadata,
)
from perp_lab.regimes.models import GMMRegime, KMeansRegime, ThresholdRegime
from perp_lab.regimes.transforms import StandardScaler
from perp_lab.strategies.base import SIDE_COL
from perp_lab.strategies.momentum import MomentumCrossover
from perp_lab.tracking.run import RunTracker, environment_info, git_state
from perp_lab.utils.logging import add_file_logging, get_logger
from perp_lab.utils.seeds import set_global_seed
from perp_lab.utils.timeutils import timeframe_to_timedelta
from perp_lab.validation.walk_forward import (
    WalkForwardFold,
    assert_folds_exclude_holdout,
    generate_walk_forward,
    split_fold,
)

# Regime-input selection: one causal proxy per economic family, in priority
# order. The first family (volatility) also drives the interpretable threshold
# regime's ordering, so a volatility proxy is required to fit regimes.
_VOLATILITY_PREFIXES = ("rvol_", "roll_std_", "atr_")
_REGIME_INPUT_PRIORITY: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("volatility", _VOLATILITY_PREFIXES),
    ("trend", ("momentum_", "ma_distance_", "price_dist_sma_")),
    ("dispersion", ("zscore_",)),
    ("activity", ("rel_volume_", "volume_zscore_")),
)


@dataclass(frozen=True)
class DevPipelineResult:
    """Outcome of one development-pipeline run."""

    symbol: str
    timeframe: str
    n_rows: int
    period_start: datetime | None
    period_end: datetime | None
    dataset_id: str
    synthetic: bool
    result: BacktestResult
    run_id: str
    run_dir: Path | None = None
    artifact_paths: list[str] = field(default_factory=list)

    @property
    def metrics(self) -> dict[str, float]:
        return self.result.metrics


def synthetic_klines(
    n: int,
    *,
    seed: int = 42,
    start: datetime | None = None,
    timeframe: str = "1h",
) -> pl.DataFrame:
    """Deterministic random-walk OHLCV frame for smoke tests (NOT real data).

    Produces the canonical :data:`KLINE_SCHEMA` columns so the same code path as
    real data can be exercised offline. Results from synthetic data must never
    be reported as research findings.
    """
    if n < 2:
        raise ValueError("synthetic_klines needs at least 2 bars.")
    rng = np.random.default_rng(seed)
    start = start or datetime(2020, 1, 1, tzinfo=UTC)
    step = timeframe_to_timedelta(timeframe)
    times = [start + i * step for i in range(n)]

    rets = rng.normal(0.0, 0.01, n)
    close = 10_000.0 * np.exp(np.cumsum(rets))
    open_ = np.concatenate([[close[0]], close[:-1]])
    high = np.maximum(open_, close) * (1.0 + np.abs(rng.normal(0.0, 0.002, n)))
    low = np.minimum(open_, close) * (1.0 - np.abs(rng.normal(0.0, 0.002, n)))
    volume = rng.uniform(100.0, 1000.0, n)
    quote_volume = volume * close
    taker_buy_quote = quote_volume * rng.uniform(0.3, 0.7, n)
    taker_buy_base = volume * rng.uniform(0.3, 0.7, n)
    trade_count = rng.integers(50, 500, n)

    return pl.DataFrame(
        {
            "open_time": times,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "quote_volume": quote_volume,
            "trade_count": trade_count,
            "taker_buy_base": taker_buy_base,
            "taker_buy_quote": taker_buy_quote,
        },
        schema=dict(KLINE_SCHEMA),
    )


def _cutoff_datetime(contract: DataContract) -> datetime:
    c = contract.cutoff_date
    return datetime(c.year, c.month, c.day, tzinfo=UTC)


def _select_regime_inputs(feature_names: Sequence[str]) -> list[str]:
    """Pick one causal proxy per regime family (volatility/trend/dispersion/activity).

    The volatility proxy is placed first so it can drive the interpretable
    threshold regime's ordering; families with no matching feature are skipped.
    """
    chosen: list[str] = []
    for _family, prefixes in _REGIME_INPUT_PRIORITY:
        match = next((n for n in feature_names if n.startswith(prefixes)), None)
        if match is not None and match not in chosen:
            chosen.append(match)
    return chosen


def _fit_fold_regimes(
    feats: pl.DataFrame,
    folds: Sequence[WalkForwardFold],
    feature_names: Sequence[str],
    *,
    seed: int,
    log: logging.Logger,
) -> dict[str, object]:
    """Fit transforms + regime models on the FIRST fold's TRAINING slice only.

    Returns a JSON-serialisable snapshot (fitted parameters + economic
    interpretation) for the run artifact. Nothing here touches validation, test
    or the frozen holdout: it uses ``split_fold(...)['train']`` of fold 0, the
    earliest expanding-window training block. Cluster models that cannot fit
    (too few complete rows) are recorded as skipped rather than fabricated.
    """
    if not folds:
        return {"status": "not_fitted", "reason": "no walk-forward folds generated"}
    inputs = _select_regime_inputs(feature_names)
    has_volatility = bool(inputs) and inputs[0].startswith(_VOLATILITY_PREFIXES)
    if not has_volatility:
        return {
            "status": "not_fitted",
            "reason": "no volatility proxy in the resolved feature set",
            "candidate_inputs": inputs,
        }

    fold0 = folds[0]
    train = split_fold(feats, fold0)["train"]
    input_tuple = tuple(inputs)

    scaler = StandardScaler(input_tuple).fit(train)
    threshold = ThresholdRegime(inputs=input_tuple).fit(train)
    regimes: dict[str, object] = {
        "threshold": {**threshold.params(), "interpretation": threshold.interpretation(train)},
    }
    for name, cls in (("kmeans", KMeansRegime), ("gmm", GMMRegime)):
        try:
            model = cls(inputs=input_tuple, seed=seed).fit(train)
            regimes[name] = {**model.params(), "interpretation": model.interpretation(train)}
        except ValueError as exc:  # insufficient complete training rows
            regimes[name] = {"status": "skipped", "reason": str(exc)}

    log.info(
        "Stage 3b regimes | fitted on fold-0 train (train-only) | inputs=%s | rows=%d",
        inputs,
        train.height,
    )
    return {
        "status": "fitted",
        "fitted_on": "walk_forward_fold_0_train",
        "fold_index": fold0.index,
        "train_start": fold0.train_start.isoformat(),
        "train_end": fold0.train_end.isoformat(),
        "n_train_rows": train.height,
        "regime_inputs": inputs,
        "scaler": scaler.params(),
        "regimes": regimes,
    }


def run_dev_pipeline(
    *,
    contract: DataContract,
    experiment: ExperimentConfig,
    paths: Paths | None = None,
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    fast: int = 24,
    slow: int = 96,
    synthetic: bool = False,
    synthetic_bars: int = 2000,
    write_artifacts: bool = True,
    run_id: str | None = None,
    attach_run_file_log: bool = False,
    repo_root: str | Path = ".",
    logger: logging.Logger | None = None,
) -> DevPipelineResult:
    """Execute the end-to-end development slice and return its result."""
    t0 = time.perf_counter()
    log = logger or get_logger("perp_lab.experiments")
    paths = paths or Paths()
    symbol = symbol.upper()

    tracker: RunTracker | None = None
    if write_artifacts:
        tracker = RunTracker.create(paths.runs_dir, run_id=run_id, prefix="dev")
        if attach_run_file_log:
            add_file_logging(tracker.logs_dir, prefix=f"run_{tracker.run_id}")
    run_identifier = tracker.run_id if tracker else (run_id or "unrecorded")
    log.info(
        "run_id=%s | development pipeline start | asset=%s tf=%s", run_identifier, symbol, timeframe
    )

    # -- Stage 1: configuration + isolation cross-check --------------------- #
    holdout_start = resolve_holdout_start(contract)
    experiment.check_against_contract(
        holdout_start=holdout_start, cutoff=_cutoff_datetime(contract)
    )
    set_global_seed(experiment.random_seed)
    folds = generate_walk_forward(experiment)
    assert_folds_exclude_holdout(folds, holdout_start)
    log.info(
        "Stage 1/6 config | seed=%d | development ends %s | purge=%d embargo=%d bars | "
        "walk-forward folds=%d (holdout excluded)",
        experiment.random_seed,
        experiment.periods.development_end_exclusive.date(),
        experiment.purge_bars,
        experiment.embargo_bars,
        len(folds),
    )

    # -- Stage 2: data loading + manifest verification + holdout guard ------ #
    dataset_manifests: dict[str, object] = {}
    if synthetic:
        log.warning("SYNTHETIC SMOKE MODE | %d bars — NOT a research result", synthetic_bars)
        frame = synthetic_klines(synthetic_bars, seed=experiment.random_seed, timeframe=timeframe)
        dataset_id, sha = "synthetic", None
        dataset_manifests["synthetic"] = {"row_count": frame.height, "sha256": None}
    else:
        lake = DataLake(contract, paths)
        key = f"{symbol}:{timeframe}_development"
        if not lake.available().get(key, False):
            log.error("Missing processed development data for %s. Run 'perp-lab download'.", key)
            raise FileNotFoundError(f"No processed data for {key}.")
        loaded = lake.load_klines(symbol, timeframe, partition="development")
        frame, dataset_id, sha = loaded.frame, loaded.dataset_id, loaded.sha256
        manifest_path = paths.manifests_dir / f"{dataset_id}.json"
        if manifest_path.exists():
            man = read_manifest(manifest_path)
            dataset_manifests[dataset_id] = {
                "sha256": man.data_sha256,
                "row_count": man.row_count,
                "period_start": str(man.period_start),
                "period_end": str(man.period_end),
            }
            if man.row_count != frame.height:
                log.warning("Manifest row_count %d != loaded rows %d", man.row_count, frame.height)
            log.info("Manifest verified | sha256=%s | rows=%d", man.data_sha256[:12], man.row_count)
        else:
            dataset_manifests[dataset_id] = {"sha256": sha, "row_count": frame.height}
            log.warning("No manifest found for %s (hash unverified)", dataset_id)

    log.info(
        "Stage 2/6 data | %s %s | rows=%d | [%s .. %s]",
        symbol,
        timeframe,
        frame.height,
        frame["open_time"].min(),
        frame["open_time"].max(),
    )
    assert_no_holdout(frame, holdout_start)
    log.info("Holdout guard PASSED | no timestamp >= %s", holdout_start)

    # -- Stage 3: causal features (config-driven engine) -------------------- #
    specs = resolve_feature_set(experiment.features.feature_set, ensure_sma=(fast, slow))
    feats, resolved = build_feature_frame(frame, specs, holdout_start=holdout_start)
    feat_meta = specs_to_metadata(resolved)
    feature_manifest = build_feature_manifest(
        resolved, symbol=symbol, timeframe=timeframe, dataset_id=dataset_id
    )
    feature_names = feature_columns(resolved)
    null_counts = {name: int(feats[name].null_count()) for name in feature_names}
    inf_counts = {
        name: int(feats[name].is_infinite().sum() or 0)
        for name in feature_names
        if feats[name].dtype.is_float()
    }
    total_inf = sum(inf_counts.values())
    log.info(
        "Stage 3/6 features | %d specs -> %d columns: %s",
        len(resolved),
        len(feature_names),
        ", ".join(feature_names),
    )
    log.info("Warm-up/null counts | %s", null_counts)
    if total_inf:  # pragma: no cover - guarded builders make this unreachable
        log.error("Non-finite feature values detected | %s", inf_counts)
        raise ValueError("Features produced infinities; refusing to pass them to the strategy.")
    log.info("Infinity check PASSED | 0 non-finite values across %d columns", len(feature_names))

    # -- Stage 4: momentum signals ------------------------------------------ #
    strategy = MomentumCrossover(fast=fast, slow=slow, direction="both")
    signals = strategy.signals(feats)
    counts = signals[SIDE_COL].value_counts().sort(SIDE_COL)
    side_dist = dict(zip(counts[SIDE_COL].to_list(), counts["count"].to_list(), strict=False))
    log.info("Stage 4/6 signals | %s | side distribution %s", strategy.name, side_dist)

    # -- Stage 5: next-bar cost-aware backtest ------------------------------ #
    fee = experiment.costs.fee_bps_per_side
    slip = experiment.costs.slippage.baseline_bps
    log.info(
        "Stage 5/6 backtest | execution=%s (signal@close t -> fill@open t+1) | "
        "fee=%.2f bps/side slippage=%.2f bps/side (provisional=%s)",
        experiment.strategies.execution,
        fee,
        slip,
        experiment.costs.provisional,
    )
    result = run_backtest(
        signals,
        feats,
        timeframe=timeframe,
        fee_bps_per_side=fee,
        slippage_bps_per_side=slip,
        days_per_year=experiment.annualization_days,
    )
    for name in (
        "n_bars",
        "total_return",
        "ann_return",
        "ann_volatility",
        "sharpe",
        "sortino",
        "max_drawdown",
        "calmar",
        "hit_rate",
        "exposure",
        "turnover",
        "n_trades",
    ):
        if name in result.metrics:
            log.info("    metric | %-15s = %.6g", name, result.metrics[name])

    # -- Stage 6: artifacts (run contract) ---------------------------------- #
    artifact_paths: list[str] = []
    if tracker is not None:
        fitted_objects = _fit_fold_regimes(
            feats, folds, feature_names, seed=experiment.random_seed, log=log
        )
        artifact_paths = _write_run_contract(
            tracker,
            experiment=experiment,
            result=result,
            feat_meta=feat_meta,
            feature_manifest=feature_manifest,
            walk_forward_folds=[f.to_dict() for f in folds],
            fitted_objects=fitted_objects,
            strategy_params=strategy.params(),
            null_counts=null_counts,
            dataset_manifests=dataset_manifests,
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy.name,
            dataset_id=dataset_id,
            synthetic=synthetic,
            repo_root=repo_root,
            elapsed_s=time.perf_counter() - t0,
            log=log,
        )

    elapsed = time.perf_counter() - t0
    log.info(
        "run_id=%s | DONE | status=success | trades=%s | elapsed=%.2fs",
        run_identifier,
        result.metrics.get("n_trades", "n/a"),
        elapsed,
    )

    start_ts = frame["open_time"].min()
    end_ts = frame["open_time"].max()
    return DevPipelineResult(
        symbol=symbol,
        timeframe=timeframe,
        n_rows=frame.height,
        period_start=start_ts if isinstance(start_ts, datetime) else None,
        period_end=end_ts if isinstance(end_ts, datetime) else None,
        dataset_id=dataset_id,
        synthetic=synthetic,
        result=result,
        run_id=run_identifier,
        run_dir=tracker.run_dir if tracker else None,
        artifact_paths=artifact_paths,
    )


def _write_run_contract(
    tracker: RunTracker,
    *,
    experiment: ExperimentConfig,
    result: BacktestResult,
    feat_meta: list[dict[str, object]],
    feature_manifest: dict[str, object],
    walk_forward_folds: list[dict[str, object]],
    fitted_objects: dict[str, object],
    strategy_params: dict[str, object],
    null_counts: dict[str, int],
    dataset_manifests: dict[str, object],
    symbol: str,
    timeframe: str,
    strategy_name: str,
    dataset_id: str,
    synthetic: bool,
    repo_root: str | Path,
    elapsed_s: float,
    log: logging.Logger,
) -> list[str]:
    """Write the stable ``artifacts/runs/<run_id>/`` contract and a figure."""
    gs = git_state(repo_root)
    ledger = result.ledger
    trade_records = result.trades()
    trades = (
        trade_records
        if trade_records.height > 0
        else ledger.filter(pl.col("net_return") != 0.0).select(
            "open_time", "position", "net_return", "cost"
        )
    )

    metrics_payload = {
        "run_id": tracker.run_id,
        "symbol": symbol,
        "timeframe": timeframe,
        "synthetic": synthetic,
        "strategy": strategy_name,
        "strategy_params": strategy_params,
        "seed": experiment.random_seed,
        "git_commit": gs["commit"],
        "git_dirty": gs["dirty"],
        "dataset_id": dataset_id,
        "execution": experiment.strategies.execution,
        "cost_bps_per_side": result.cost_bps_per_side,
        "costs_provisional": experiment.costs.provisional,
        "funding_applied": result.funding_applied,
        "n_walk_forward_folds": len(walk_forward_folds),
        "metrics": result.metrics,
        "elapsed_seconds": round(elapsed_s, 3),
    }

    paths_written = [
        tracker.write_yaml("resolved_config.yaml", experiment.model_dump(mode="json")),
        tracker.write_json("dataset_manifests.json", dataset_manifests),
        tracker.write_json("environment.json", environment_info()),
        tracker.write_json("git_state.json", gs),
        tracker.write_json("feature_metadata.json", {"features": feat_meta, "nulls": null_counts}),
        tracker.write_json("feature_manifest.json", feature_manifest),
        tracker.write_json(
            "walk_forward.json",
            {
                "scheme": experiment.walk_forward.scheme,
                "purge_bars": experiment.purge_bars,
                "embargo_bars": experiment.embargo_bars,
                "n_folds": len(walk_forward_folds),
                "folds": walk_forward_folds,
            },
        ),
        tracker.write_json("fitted_objects.json", fitted_objects),
        tracker.write_json("metrics.json", metrics_payload),
        tracker.write_parquet("equity.parquet", ledger),
        tracker.write_parquet("trades.parquet", trades),
    ]

    fig_path = _equity_figure(tracker, ledger, symbol, timeframe, strategy_name, synthetic)
    paths_written.append(fig_path)

    out = [str(p) for p in paths_written]
    log.info("Stage 6/6 artifacts | run_dir=%s | %d files", tracker.run_dir, len(out))
    return out


def _equity_figure(
    tracker: RunTracker,
    ledger: pl.DataFrame,
    symbol: str,
    timeframe: str,
    strategy_name: str,
    synthetic: bool,
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tag = "synthetic" if synthetic else "development"
    fig, ax = plt.subplots(figsize=(11, 4.5), constrained_layout=True)
    ax.plot(ledger["open_time"].to_numpy(), ledger["equity"].to_numpy(), color="#D55E00", lw=1.0)
    ax.set_title(f"{strategy_name} net-of-cost equity | {symbol} {timeframe} ({tag})")
    ax.set_xlabel("UTC")
    ax.set_ylabel("equity (start = 1.0)")
    ax.grid(True, alpha=0.3)
    out_path = tracker.figures_dir / f"equity_{symbol}_{timeframe}.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path
