"""Unit tests for the search objective and hard constraints."""

from __future__ import annotations

import math

from perp_lab.search.objective import FAILURE_PENALTY, ObjectiveConfig, aggregate_objective


def _cfg(**over: object) -> ObjectiveConfig:
    base: dict[str, object] = {
        "w_sharpe": 1.0,
        "w_max_drawdown": 0.5,
        "w_turnover": 0.2,
        "w_fold_instability": 0.3,
        "w_complexity": 0.1,
        "min_trades_total": 4,
        "min_trades_per_fold": 1,
        "max_drawdown_limit": 0.5,
        "require_funding": False,
    }
    base.update(over)
    return ObjectiveConfig(**base)  # type: ignore[arg-type]


def _fold(sharpe: float, dd: float, trades: float, tpb: float = 0.05) -> dict[str, float]:
    return {
        "sharpe": sharpe,
        "max_drawdown": dd,
        "n_trades": trades,
        "turnover_per_bar": tpb,
    }


def test_exact_score_computation() -> None:
    cfg = _cfg()
    folds = [_fold(1.0, -0.1, 5, 0.1), _fold(2.0, -0.2, 5, 0.1)]
    res = aggregate_objective(folds, n_active_params=3, cfg=cfg, funding_applied=False)
    assert res.feasible
    mean_sharpe = 1.5
    instability = math.sqrt(((1.0 - 1.5) ** 2 + (2.0 - 1.5) ** 2) / 2)
    mean_dd = 0.15
    mean_tpb = 0.1
    complexity = 1.0
    expected = (
        1.0 * mean_sharpe - 0.5 * mean_dd - 0.2 * mean_tpb - 0.3 * instability - 0.1 * complexity
    )
    assert res.fitness == expected
    assert res.components["mean_val_sharpe"] == mean_sharpe


def test_insufficient_total_trades_fails() -> None:
    cfg = _cfg(min_trades_total=100)
    res = aggregate_objective(
        [_fold(1.0, -0.1, 5)], n_active_params=2, cfg=cfg, funding_applied=False
    )
    assert not res.feasible
    assert res.fitness == FAILURE_PENALTY
    assert "min_trades_total" in (res.reason or "")


def test_per_fold_trade_floor_fails() -> None:
    cfg = _cfg(min_trades_total=1, min_trades_per_fold=3)
    res = aggregate_objective(
        [_fold(1.0, -0.1, 5), _fold(1.0, -0.1, 1)],
        n_active_params=2,
        cfg=cfg,
        funding_applied=False,
    )
    assert not res.feasible
    assert "per_fold" in (res.reason or "")


def test_excessive_drawdown_fails() -> None:
    cfg = _cfg(min_trades_total=1, max_drawdown_limit=0.2)
    res = aggregate_objective(
        [_fold(1.0, -0.9, 5)], n_active_params=2, cfg=cfg, funding_applied=False
    )
    assert not res.feasible
    assert "drawdown" in (res.reason or "")


def test_non_finite_metric_fails() -> None:
    cfg = _cfg(min_trades_total=1)
    res = aggregate_objective(
        [_fold(float("inf"), -0.1, 5)], n_active_params=2, cfg=cfg, funding_applied=False
    )
    assert not res.feasible
    assert "non-finite" in (res.reason or "")


def test_missing_required_funding_fails() -> None:
    cfg = _cfg(min_trades_total=1, require_funding=True)
    res = aggregate_objective(
        [_fold(1.0, -0.1, 5)], n_active_params=2, cfg=cfg, funding_applied=False
    )
    assert not res.feasible
    assert "funding" in (res.reason or "")
    ok = aggregate_objective(
        [_fold(1.0, -0.1, 5)], n_active_params=2, cfg=cfg, funding_applied=True
    )
    assert ok.feasible


def test_fold_instability_penalises_variance() -> None:
    cfg = _cfg(
        min_trades_total=1, w_fold_instability=1.0, w_max_drawdown=0, w_turnover=0, w_complexity=0
    )
    stable = aggregate_objective(
        [_fold(1.0, -0.1, 5), _fold(1.0, -0.1, 5)],
        n_active_params=2,
        cfg=cfg,
        funding_applied=False,
    )
    volatile = aggregate_objective(
        [_fold(0.0, -0.1, 5), _fold(2.0, -0.1, 5)],
        n_active_params=2,
        cfg=cfg,
        funding_applied=False,
    )
    # Same mean sharpe (1.0) but the volatile one is penalised for instability.
    assert stable.fitness > volatile.fitness


def test_empty_folds_fail() -> None:
    res = aggregate_objective([], n_active_params=2, cfg=_cfg(), funding_applied=False)
    assert not res.feasible
    assert res.fitness == FAILURE_PENALTY
