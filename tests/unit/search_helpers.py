"""Shared, fast fixtures for the search unit tests.

Builds a small synthetic development frame, a handful of leakage-safe
walk-forward folds and a bound :class:`CandidateEvaluator`, so individual tests
of Random Search / the GA / the objective run in well under a second.
"""

from __future__ import annotations

from dataclasses import dataclass

from perp_lab.config import load_experiment_config
from perp_lab.config.experiment import ExperimentConfig
from perp_lab.experiments.pipeline import synthetic_klines
from perp_lab.search.evaluator import CandidateEvaluator, FoldsBundle, build_folds_data
from perp_lab.search.objective import ObjectiveConfig
from perp_lab.search.registry import build_search_space
from perp_lab.search.space import SearchSpace
from perp_lab.utils.timeutils import timeframe_to_timedelta
from perp_lab.validation.walk_forward import generate_folds


@dataclass
class Env:
    exp: ExperimentConfig
    space: SearchSpace
    bundle: FoldsBundle
    evaluator: CandidateEvaluator
    objective_cfg: ObjectiveConfig


def build_env(
    *,
    family: str = "mean_reversion",
    n_bars: int = 1400,
    seed: int = 11,
    timeframe: str = "1h",
    regime_model: str = "threshold",
    max_folds: int = 3,
) -> Env:
    exp = load_experiment_config("configs/experiment.yaml")
    frame = synthetic_klines(n_bars, seed=seed, timeframe=timeframe)
    step = timeframe_to_timedelta(timeframe)
    start = frame["open_time"].min()
    end = frame["open_time"].max()
    dev_end = end + step  # type: ignore[operator]
    holdout_start = dev_end
    folds = generate_folds(
        start,  # type: ignore[arg-type]
        dev_end,  # type: ignore[arg-type]
        initial_train_days=30,
        validation_days=7,
        test_days=7,
        step_days=7,
        purge=exp.purge_bars * step,
        embargo=exp.embargo_bars * step,
        purge_bars=exp.purge_bars,
        embargo_bars=exp.embargo_bars,
        max_folds=max_folds,
    )
    bundle = build_folds_data(
        frame,
        folds,
        exp=exp,
        family=family,
        symbol="BTCUSDT",
        timeframe=timeframe,
        regime_model=regime_model,
        seed=seed,
        funding=None,
        holdout_start=holdout_start,  # type: ignore[arg-type]
    )
    space = build_search_space(exp, family)
    objective_cfg = ObjectiveConfig.from_experiment(
        exp, overrides={"min_trades_total": 1, "min_trades_per_fold": 0}
    )
    evaluator = CandidateEvaluator(
        bundle,
        space,
        timeframe=timeframe,
        fee_bps_per_side=exp.costs.fee_bps_per_side,
        slippage_bps_per_side=exp.costs.slippage.baseline_bps,
        days_per_year=exp.annualization_days,
        require_funding=False,
        objective_cfg=objective_cfg,
    )
    return Env(
        exp=exp, space=space, bundle=bundle, evaluator=evaluator, objective_cfg=objective_cfg
    )
