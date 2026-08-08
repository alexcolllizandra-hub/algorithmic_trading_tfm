"""Tests that outer-fold search cannot leak validation metrics across folds."""

from __future__ import annotations

from search_helpers import build_env

from perp_lab.config.models import Paths
from perp_lab.search.config import GASettings, ObjectiveOverride, SearchRunConfig, WalkForwardOverride
from perp_lab.search.evaluator import CandidateEvaluator, single_fold_bundle
from perp_lab.search.random_search import run_random_search
from perp_lab.search.runner import _fold_seed, run_search


def _fold_evaluator(env, fold_index: int) -> CandidateEvaluator:
    bundle = single_fold_bundle(env.bundle, fold_index)
    return CandidateEvaluator(
        bundle,
        env.space,
        timeframe="1h",
        fee_bps_per_side=env.exp.costs.fee_bps_per_side,
        slippage_bps_per_side=env.exp.costs.slippage.baseline_bps,
        days_per_year=env.exp.annualization_days,
        require_funding=False,
        objective_cfg=env.objective_cfg,
    )


def test_single_fold_evaluator_scores_one_validation_slice() -> None:
    env = build_env(seed=11)
    ev0 = _fold_evaluator(env, 0)
    out = run_random_search(ev0, env.space, budget=8, seed=_fold_seed(11, 0))
    assert out.counters.evaluated == 8
    assert all(len(c.fold_metrics) == 1 for c in out.candidates)


def test_multi_fold_evaluator_still_scores_all_validation_slices() -> None:
    env = build_env(seed=11)
    out = run_random_search(env.evaluator, env.space, budget=8, seed=5)
    n_folds = len(env.bundle.folds)
    assert all(len(c.fold_metrics) == n_folds for c in out.candidates)


def test_fold_zero_search_is_deterministic_and_independent() -> None:
    env = build_env(seed=11)
    ev0 = _fold_evaluator(env, 0)
    seed = _fold_seed(11, 0)
    out1 = run_random_search(ev0, env.space, budget=12, seed=seed)
    out2 = run_random_search(_fold_evaluator(env, 0), env.space, budget=12, seed=seed)
    assert out1.best is not None and out2.best is not None
    assert out1.best.candidate_id == out2.best.candidate_id
    assert out1.best.fitness == out2.best.fitness


def test_runner_uses_independent_per_outer_fold_protocol(tmp_path) -> None:
    cfg = SearchRunConfig(
        family="mean_reversion",
        algorithm="random_search",
        symbol="BTCUSDT",
        timeframe="1h",
        seed=7,
        regime_model="threshold",
        require_funding=True,
        synthetic=True,
        synthetic_bars=1000,
        label="test_fold_isolation",
        ga=GASettings(population_size=3, generations=2, elitism=1, tournament_size=3),
        walk_forward_override=WalkForwardOverride(
            initial_train_days=25,
            validation_days=7,
            test_days=7,
            step_days=7,
            max_folds=2,
        ),
        objective=ObjectiveOverride(
            min_trades_total=1, min_trades_per_fold=0, max_drawdown_limit=0.99
        ),
    )
    res = run_search(cfg, paths=Paths(artifacts_root=tmp_path / "artifacts"), write_artifacts=True)
    assert res.summary["search_protocol"] == "independent_per_outer_fold"
    n_folds = res.summary["n_folds"]
    assert len(res.fold_outcomes["random_search"]) == n_folds
    for fold_outcome in res.fold_outcomes["random_search"]:
        assert fold_outcome.counters.evaluated <= cfg.budget
        assert all(len(c.fold_metrics) == 1 for c in fold_outcome.candidates)
    assert len(res.fold_winners["random_search"]) == n_folds


def test_runner_budget_is_per_outer_fold(tmp_path) -> None:
    cfg = SearchRunConfig(
        family="mean_reversion",
        algorithm="comparison",
        symbol="BTCUSDT",
        timeframe="1h",
        seed=3,
        regime_model="threshold",
        require_funding=True,
        synthetic=True,
        synthetic_bars=900,
        label="test_fold_budget",
        ga=GASettings(population_size=5, generations=1, elitism=1, tournament_size=3),
        walk_forward_override=WalkForwardOverride(
            initial_train_days=20,
            validation_days=7,
            test_days=7,
            step_days=7,
            max_folds=2,
        ),
        objective=ObjectiveOverride(
            min_trades_total=1, min_trades_per_fold=0, max_drawdown_limit=0.99
        ),
    )
    res = run_search(cfg, paths=Paths(artifacts_root=tmp_path / "artifacts"), write_artifacts=False)
    n_folds = res.summary["n_folds"]
    total_budget = res.summary["total_budget_per_method"]
    assert total_budget == cfg.budget * n_folds
    for outcome in res.outcomes.values():
        assert outcome.counters.evaluated <= total_budget
