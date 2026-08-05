"""Transparent, component-wise objective and hard constraints.

The objective rewards risk-adjusted **validation** performance and penalises
fragile or impractical candidates. Every raw component is stored separately so a
scalar fitness can always be explained in the thesis. Hard constraints turn a
candidate into an explicit *failure* with a deterministic penalty -- invalid,
non-finite or under-traded candidates are never silently converted into an
attractive score.

The objective is computed on per-fold **validation** metrics only. Test/holdout
metrics are never passed here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from perp_lab.config.experiment import ExperimentConfig

# Deterministic penalty assigned to any candidate that fails a hard constraint.
FAILURE_PENALTY = -1.0e9


@dataclass(frozen=True)
class ObjectiveConfig:
    """Weights + hard constraints for the search objective."""

    w_sharpe: float
    w_max_drawdown: float
    w_turnover: float
    w_fold_instability: float
    w_complexity: float
    min_trades_total: int
    min_trades_per_fold: int
    max_drawdown_limit: float | None  # e.g. 0.6 => reject candidates worse than -60%
    require_funding: bool

    @classmethod
    def from_experiment(
        cls,
        exp: ExperimentConfig,
        *,
        require_funding: bool = False,
        max_drawdown_limit: float | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> ObjectiveConfig:
        w = exp.fitness.weights
        c = exp.fitness.constraints
        o = overrides or {}
        return cls(
            w_sharpe=float(o.get("w_sharpe", w.sharpe)),
            w_max_drawdown=float(o.get("w_max_drawdown", w.max_drawdown_penalty)),
            w_turnover=float(o.get("w_turnover", w.turnover_penalty)),
            w_fold_instability=float(o.get("w_fold_instability", w.fold_instability_penalty)),
            w_complexity=float(o.get("w_complexity", w.complexity_penalty)),
            min_trades_total=int(o.get("min_trades_total", c.min_trades_total)),
            min_trades_per_fold=int(o.get("min_trades_per_fold", c.min_trades_per_fold)),
            max_drawdown_limit=o.get("max_drawdown_limit", max_drawdown_limit),
            require_funding=require_funding,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "weights": {
                "sharpe": self.w_sharpe,
                "max_drawdown_penalty": self.w_max_drawdown,
                "turnover_penalty": self.w_turnover,
                "fold_instability_penalty": self.w_fold_instability,
                "complexity_penalty": self.w_complexity,
            },
            "constraints": {
                "min_trades_total": self.min_trades_total,
                "min_trades_per_fold": self.min_trades_per_fold,
                "max_drawdown_limit": self.max_drawdown_limit,
                "require_funding": self.require_funding,
            },
            "failure_penalty": FAILURE_PENALTY,
        }


@dataclass(frozen=True)
class ObjectiveResult:
    fitness: float
    components: dict[str, float]
    feasible: bool
    reason: str | None


def _mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return float(math.sqrt(sum((v - m) ** 2 for v in values) / len(values)))


def aggregate_objective(
    fold_val_metrics: list[dict[str, float]],
    *,
    n_active_params: int,
    cfg: ObjectiveConfig,
    funding_applied: bool,
) -> ObjectiveResult:
    """Aggregate per-fold validation metrics into a scalar fitness + components.

    Returns an infeasible result (fitness = :data:`FAILURE_PENALTY`) when a hard
    constraint is violated, recording the reason.
    """
    if not fold_val_metrics:
        return ObjectiveResult(FAILURE_PENALTY, {}, False, "no validation folds evaluated")

    if cfg.require_funding and not funding_applied:
        return ObjectiveResult(
            FAILURE_PENALTY, {}, False, "funding required but not applied in backtest"
        )

    sharpes = [float(m.get("sharpe", 0.0)) for m in fold_val_metrics]
    drawdowns = [abs(float(m.get("max_drawdown", 0.0))) for m in fold_val_metrics]
    trades = [float(m.get("n_trades", 0.0)) for m in fold_val_metrics]
    turnovers_pb = [float(m.get("turnover_per_bar", 0.0)) for m in fold_val_metrics]

    # Hard constraint: all metrics must be finite.
    flat = sharpes + drawdowns + trades + turnovers_pb
    if any(not math.isfinite(x) for x in flat):
        return ObjectiveResult(FAILURE_PENALTY, {}, False, "non-finite validation metric")

    total_trades = sum(trades)
    if total_trades < cfg.min_trades_total:
        return ObjectiveResult(
            FAILURE_PENALTY,
            {},
            False,
            f"total trades {int(total_trades)} < min_trades_total {cfg.min_trades_total}",
        )
    if any(t < cfg.min_trades_per_fold for t in trades):
        return ObjectiveResult(
            FAILURE_PENALTY,
            {},
            False,
            f"a fold had < min_trades_per_fold {cfg.min_trades_per_fold} trades",
        )
    worst_dd = max(drawdowns) if drawdowns else 0.0
    if cfg.max_drawdown_limit is not None and worst_dd > cfg.max_drawdown_limit:
        return ObjectiveResult(
            FAILURE_PENALTY,
            {},
            False,
            f"worst drawdown {worst_dd:.3f} exceeds limit {cfg.max_drawdown_limit}",
        )

    mean_sharpe = _mean(sharpes)
    instability = _std(sharpes)
    mean_dd = _mean(drawdowns)
    mean_turnover = _mean(turnovers_pb)
    # Complexity: number of active parameters beyond the family's minimum (2).
    complexity = max(n_active_params - 2, 0)

    components = {
        "mean_val_sharpe": mean_sharpe,
        "fold_instability": instability,
        "mean_val_drawdown": mean_dd,
        "mean_val_turnover_per_bar": mean_turnover,
        "complexity": float(complexity),
        "total_val_trades": total_trades,
    }
    fitness = (
        cfg.w_sharpe * mean_sharpe
        - cfg.w_max_drawdown * mean_dd
        - cfg.w_turnover * mean_turnover
        - cfg.w_fold_instability * instability
        - cfg.w_complexity * float(complexity)
    )
    return ObjectiveResult(float(fitness), components, True, None)
