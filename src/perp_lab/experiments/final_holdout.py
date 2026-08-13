"""Phase H: the single, recorded opening of the frozen holdout.

Every other path in this codebase refuses holdout data on purpose. This module is
the one sanctioned exception, and it exists because the protocol requires the
holdout to be opened exactly once, on a candidate that was frozen before it was
read (`docs/roadmap/phase_gates.md`, Gate H; ADR 0006).

What makes the opening legitimate is not this code but the commit that precedes
it: the candidate, its parameters and the selection rule are recorded in
`docs/methodology/final_holdout_evaluation.md` and committed before any holdout
row is touched. This module only executes that frozen decision and records what
it did -- timestamp, git state, resolved configuration, dataset hashes and the
selection fingerprints of the parameters it was handed.

The evaluation mirrors the walk-forward test path exactly. Features are built
causally over the continuous timeline, the regime model is fitted on development
data only and then applied forward, and the backtest runs with the frozen cost
model. The one difference from a search fold is the window: the test slice is
``[holdout_start, cutoff)`` instead of a fold's own block.

The module supports evaluating on the development partition as well. That is a
**smoke test of the machinery, not a research result**: those bars trained and
selected the very parameters being replayed, so its numbers mean nothing and are
labelled accordingly. It exists so that a one-shot, irreversible operation is not
also the first time the code runs.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
import polars as pl

from perp_lab.backtesting.engine import run_backtest
from perp_lab.backtesting.metrics import performance_metrics
from perp_lab.config.experiment import ExperimentConfig
from perp_lab.config.models import DataContract, Paths
from perp_lab.data.splits import resolve_holdout_start
from perp_lab.eda.datasets import DataLake
from perp_lab.features.registry import (
    FeatureContext,
    build_feature_frame,
    feature_columns,
    resolve_feature_set,
)
from perp_lab.search.evaluator import (
    _make_regime_model,
    _regime_feature_items,
    _select_regime_inputs,
)
from perp_lab.search.registry import build_search_space
from perp_lab.strategies.base import Strategy

Partition = Literal["development", "holdout"]


class FinalEvaluationError(RuntimeError):
    """Raised when the frozen record is not complete enough to be replayed."""


@dataclass(frozen=True)
class FrozenParameters:
    """One seed's sealed winning configuration, as the search wrote it."""

    seed: int
    run_dir: str
    candidate_id: str
    fingerprint: str
    fold: int
    params: dict[str, Any]


@dataclass(frozen=True)
class FrozenCandidate:
    """The single candidate the holdout is opened on."""

    family: str
    symbol: str
    timeframe: str
    engine: str
    fold: int
    members: tuple[FrozenParameters, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "engine": self.engine,
            "fold": self.fold,
            "n_members": len(self.members),
            "members": [
                {
                    "seed": m.seed,
                    "run_dir": m.run_dir,
                    "candidate_id": m.candidate_id,
                    "selection_fingerprint": m.fingerprint,
                    "params": m.params,
                }
                for m in self.members
            ],
        }


def load_frozen_candidate(
    run_dirs: dict[int, Path], *, family: str, symbol: str, timeframe: str, engine: str
) -> FrozenCandidate:
    """Read each seed's **last** fold winner, as the search sealed it.

    The last fold is the only selection that could have been carried into the
    holdout window: every earlier one was superseded before the window began.
    A winner that was not sealed before its own test slice was scored is refused
    rather than used, because its provenance cannot be trusted.
    """
    members: list[FrozenParameters] = []
    folds_seen: set[int] = set()
    for seed in sorted(run_dirs):
        run_dir = run_dirs[seed]
        path = run_dir / f"{engine}_fold_winners.json"
        if not path.exists():
            raise FinalEvaluationError(f"No frozen winners for seed {seed} at {path}")
        winners = json.loads(path.read_text(encoding="utf-8"))
        sealed = [w for w in winners if w.get("winner")]
        if not sealed:
            raise FinalEvaluationError(f"Seed {seed} sealed no winner in any fold")
        last = max(sealed, key=lambda w: int(w["fold"]))
        if not last.get("frozen_before_test"):
            raise FinalEvaluationError(
                f"Seed {seed} fold {last['fold']} was not frozen before its test slice"
            )
        folds_seen.add(int(last["fold"]))
        members.append(
            FrozenParameters(
                seed=seed,
                run_dir=run_dir.name,
                candidate_id=str(last["winner"]),
                fingerprint=str(last.get("selection_fingerprint", "")),
                fold=int(last["fold"]),
                params=dict(last["params"]),
            )
        )
    if len(folds_seen) != 1:
        raise FinalEvaluationError(
            f"Seeds disagree on the last fold ({sorted(folds_seen)}); the candidate "
            "would not be a single frozen object."
        )
    return FrozenCandidate(
        family=family,
        symbol=symbol,
        timeframe=timeframe,
        engine=engine,
        fold=folds_seen.pop(),
        members=tuple(members),
    )


@dataclass
class EvaluationSlices:
    """The causally-built frames the evaluation runs on."""

    fit: pl.DataFrame
    evaluate: pl.DataFrame
    funding: pl.DataFrame | None
    regime_inputs: list[str]
    dataset_hashes: dict[str, Any]


def build_slices(
    candidate: FrozenCandidate,
    *,
    partition: Partition,
    exp: ExperimentConfig,
    contract: DataContract,
    paths: Paths,
    regime_seed: int,
) -> EvaluationSlices:
    """Build features over the continuous timeline and split at the boundary.

    Features are computed on development and evaluation bars **together**, in one
    causal pass, so that a rolling window at the first evaluation bar carries the
    history that actually preceded it rather than restarting from nothing. This
    is the same treatment a search fold gets, where features are built over the
    whole development timeline before the fold is sliced out.

    ``build_feature_frame`` is called without a holdout guard here. That is the
    single deliberate exception in the codebase, and it is only reachable from
    this module.
    """
    lake = DataLake(contract, paths)
    holdout_start = resolve_holdout_start(contract)

    development = lake.load_klines(candidate.symbol, candidate.timeframe, partition="development")
    hashes: dict[str, Any] = {
        development.dataset_id: {
            "sha256": development.sha256,
            "rows": development.frame.height,
            "role": "feature history and regime fit",
        }
    }

    if partition == "holdout":
        evaluated = lake.load_klines(candidate.symbol, candidate.timeframe, partition="holdout")
        bars = pl.concat([development.frame, evaluated.frame]).sort("open_time")
        hashes[evaluated.dataset_id] = {
            "sha256": evaluated.sha256,
            "rows": evaluated.frame.height,
            "role": "EVALUATION - the frozen holdout",
        }
        boundary = holdout_start
    else:
        bars = development.frame
        # Mirror the geometry without leaving the development partition: the last
        # stretch of development stands in for the evaluation window.
        cutoff = bars["open_time"].max()
        assert isinstance(cutoff, datetime)
        boundary = holdout_start.replace(year=holdout_start.year - 1)
        if boundary >= cutoff:
            raise FinalEvaluationError("Development partition is too short for a smoke test.")

    if bars["open_time"].n_unique() != bars.height:
        raise FinalEvaluationError("Development and evaluation bars overlap in time.")

    funding: pl.DataFrame | None = None
    fund_dev = lake.load_funding(candidate.symbol, partition="development")
    frames = [fund_dev.frame]
    hashes[fund_dev.dataset_id] = {"sha256": fund_dev.sha256, "rows": fund_dev.frame.height}
    if partition == "holdout":
        fund_hold = lake.load_funding(candidate.symbol, partition="holdout")
        frames.append(fund_hold.frame)
        hashes[fund_hold.dataset_id] = {
            "sha256": fund_hold.sha256,
            "rows": fund_hold.frame.height,
        }
    funding = pl.concat(frames).sort(
        "funding_time" if "funding_time" in frames[0].columns else "open_time"
    )

    space = build_search_space(exp, candidate.family, candidate.symbol)
    specs = resolve_feature_set([*space.feature_items, *_regime_feature_items(exp)])
    context = FeatureContext(funding=funding)
    feats, resolved = build_feature_frame(bars, specs, holdout_start=None, context=context)

    regime_inputs = _select_regime_inputs(feature_columns(resolved))
    if not regime_inputs:
        raise FinalEvaluationError("No volatility proxy available to fit the regime model.")

    fit = feats.filter(pl.col("open_time") < boundary)
    evaluate = feats.filter(pl.col("open_time") >= boundary)
    if evaluate.height == 0:
        raise FinalEvaluationError("The evaluation window contains no bars.")

    model = _make_regime_model("threshold", tuple(regime_inputs), regime_seed)
    model.fit(fit)
    return EvaluationSlices(
        fit=fit,
        evaluate=model.attach(evaluate),
        funding=funding,
        regime_inputs=regime_inputs,
        dataset_hashes=hashes,
    )


def evaluate_candidate(
    candidate: FrozenCandidate, slices: EvaluationSlices, *, exp: ExperimentConfig
) -> dict[str, Any]:
    """Replay every frozen member once and combine them as the study measured them.

    Each member is scored exactly as a fold winner was: its strategy is built from
    the sealed parameters and backtested on the evaluation frame with the frozen
    cost model. The members are then averaged per bar, which is the same
    equal-weight combination the study-level accounting used to define a family's
    performance.
    """
    space = build_search_space(exp, candidate.family, candidate.symbol)
    frame = slices.evaluate
    per_member: list[dict[str, Any]] = []
    ledgers: list[pl.DataFrame] = []

    for member in candidate.members:
        strategy: Strategy = space.build(member.params)  # type: ignore[assignment]
        if getattr(strategy, "consumes_reference_bars", False):
            raise FinalEvaluationError(
                f"{candidate.family} consumes reference bars; this path does not load them."
            )
        result = run_backtest(
            strategy.signals(frame),
            frame,
            timeframe=candidate.timeframe,
            fee_bps_per_side=exp.costs.fee_bps_per_side,
            slippage_bps_per_side=exp.costs.slippage.baseline_bps,
            days_per_year=exp.annualization_days,
            asset=candidate.symbol,
            funding=slices.funding,
            # R3 ran this family with funding required; keeping that makes a
            # missing holdout funding frame an error instead of a silent zero.
            require_funding=True,
        )
        if not result.funding_applied:
            raise FinalEvaluationError("Funding was not applied; the cost model would differ.")
        ledgers.append(
            result.ledger.select(
                "open_time", "net_return", "position", "turnover", "cost", "funding"
            )
        )
        per_member.append(
            {
                "seed": member.seed,
                "selection_fingerprint": member.fingerprint,
                "metrics": {k: float(v) for k, v in result.metrics.items()},
            }
        )

    combined = (
        pl.concat(ledgers)
        .group_by("open_time")
        .agg(
            pl.col("net_return").mean(),
            pl.col("position").mean(),
            pl.col("turnover").mean(),
            pl.col("cost").mean(),
            pl.col("funding").mean(),
        )
        .sort("open_time")
    )
    metrics = performance_metrics(
        combined["net_return"].to_numpy().astype(float),
        timeframe=candidate.timeframe,
        positions=combined["position"].to_numpy().astype(float),
        turnover=combined["turnover"].to_numpy().astype(float),
        days_per_year=exp.annualization_days,
    )
    return {
        "combined": metrics,
        "costs_paid": {
            "fees_and_slippage": float(combined["cost"].sum()),
            "funding": float(combined["funding"].sum()),
            "total": float(combined["cost"].sum()) + float(combined["funding"].sum()),
        },
        "per_member": per_member,
        "n_bars": combined.height,
        "window": {
            "start": str(combined["open_time"].min()),
            "end": str(combined["open_time"].max()),
        },
    }


def buy_and_hold(frame: pl.DataFrame, *, timeframe: str, days_per_year: int) -> dict[str, float]:
    """The same window, held long, for context. Not a benchmark the candidate had to beat."""
    close = frame.sort("open_time")["close"].cast(pl.Float64).to_numpy().astype(float)
    returns = np.diff(close) / close[:-1]
    return performance_metrics(
        returns,
        timeframe=timeframe,
        positions=np.ones(returns.size),
        days_per_year=days_per_year,
    )


def git_state(root: Path) -> dict[str, Any]:
    """The commit this evaluation ran from, and whether the tree was clean."""

    def run(*args: str) -> str:
        return subprocess.run(
            args, cwd=root, capture_output=True, text=True, check=False
        ).stdout.strip()

    status = run("git", "status", "--porcelain")
    return {
        "commit": run("git", "rev-parse", "HEAD"),
        "branch": run("git", "rev-parse", "--abbrev-ref", "HEAD"),
        "worktree_clean": status == "",
        "dirty_paths": [line[3:] for line in status.splitlines()] if status else [],
    }


def provenance(
    candidate: FrozenCandidate,
    slices: EvaluationSlices,
    *,
    root: Path,
    partition: Partition,
    exp: ExperimentConfig,
) -> dict[str, Any]:
    """Everything Gate H requires to be on the record when the holdout is opened."""
    return {
        "opened_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "partition_evaluated": partition,
        "is_research_result": partition == "holdout",
        "git": git_state(root),
        "candidate": candidate.to_dict(),
        "dataset_hashes": slices.dataset_hashes,
        "regime": {
            "model": "threshold",
            "inputs": slices.regime_inputs,
            "fitted_on": "development partition only",
            "fit_bars": slices.fit.height,
        },
        "costs": {
            "fee_bps_per_side": exp.costs.fee_bps_per_side,
            "slippage_bps_per_side": exp.costs.slippage.baseline_bps,
            "funding_treatment": exp.costs.funding.treatment,
            "provisional": exp.costs.provisional,
        },
        "annualization_days": exp.annualization_days,
    }
