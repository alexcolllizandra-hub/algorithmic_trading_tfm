"""Common candidate representation shared by Random Search and the GA.

A :class:`Candidate` is a fully self-describing, reproducible record of one
strategy configuration and its evaluation outcome. Given its serialized form
plus the family's :class:`~perp_lab.search.space.SearchSpace`, the exact strategy
can be rebuilt and re-evaluated deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from perp_lab.search.space import ParamValue, SearchSpace


class CandidateStatus(StrEnum):
    PROPOSED = "proposed"
    INVALID = "invalid"  # failed parameter/family validation (not evaluated)
    DUPLICATE = "duplicate"  # already-seen hash (not re-evaluated)
    EVALUATED = "evaluated"  # backtested, feasible objective
    FAILED = "failed"  # backtested but violated a hard constraint / non-finite


@dataclass
class Candidate:
    """One strategy configuration and (optionally) its evaluation outcome."""

    candidate_id: str
    family: str
    space_version: str
    params: dict[str, ParamValue]
    active_params: dict[str, ParamValue]
    seed: int
    step: int  # RS proposal index or GA generation
    parent_ids: tuple[str, ...] = ()
    status: CandidateStatus = CandidateStatus.PROPOSED
    failure_reason: str | None = None
    objective_components: dict[str, float] = field(default_factory=dict)
    fitness: float | None = None
    fold_metrics: list[dict[str, float]] = field(default_factory=list)
    eval_seconds: float | None = None
    # The outer fold whose isolated search produced this candidate. Fitness is
    # only comparable to other candidates carrying the same value.
    fold_index: int | None = None

    @classmethod
    def create(
        cls,
        space: SearchSpace,
        values: dict[str, ParamValue],
        *,
        seed: int,
        step: int,
        parent_ids: tuple[str, ...] = (),
    ) -> Candidate:
        return cls(
            candidate_id=space.candidate_hash(values),
            family=space.family,
            space_version=space.version,
            params=dict(values),
            active_params=space.active_params(values),
            seed=seed,
            step=step,
            parent_ids=parent_ids,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "family": self.family,
            "space_version": self.space_version,
            "params": {k: _to_jsonable(v) for k, v in self.params.items()},
            "active_params": {k: _to_jsonable(v) for k, v in self.active_params.items()},
            "seed": self.seed,
            "step": self.step,
            "parent_ids": list(self.parent_ids),
            "status": self.status.value,
            "failure_reason": self.failure_reason,
            "objective_components": self.objective_components,
            "fitness": self.fitness,
            "fold_metrics": self.fold_metrics,
            "eval_seconds": self.eval_seconds,
            "fold_index": self.fold_index,
        }

    def ledger_row(self) -> dict[str, Any]:
        """Flat row for the tabular candidate ledger (Parquet/CSV)."""
        val_sharpes = [float(m.get("sharpe", float("nan"))) for m in self.fold_metrics]
        return {
            "candidate_id": self.candidate_id,
            "family": self.family,
            "fold_index": self.fold_index,
            "status": self.status.value,
            "fitness": self.fitness,
            "failure_reason": self.failure_reason,
            "step": self.step,
            "n_parents": len(self.parent_ids),
            "eval_seconds": self.eval_seconds,
            "n_active_params": len(self.active_params),
            "mean_val_sharpe": (
                float(sum(val_sharpes) / len(val_sharpes)) if val_sharpes else None
            ),
            "params_json": _canonical_params(self.active_params),
            **{f"obj_{k}": v for k, v in self.objective_components.items()},
        }


def _to_jsonable(value: ParamValue) -> Any:
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    return value


def _canonical_params(active: dict[str, ParamValue]) -> str:
    import json

    return json.dumps(
        {k: _to_jsonable(v) for k, v in active.items()}, sort_keys=True, separators=(",", ":")
    )
