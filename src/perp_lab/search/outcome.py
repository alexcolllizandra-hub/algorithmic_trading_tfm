"""Shared result containers for the search algorithms."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from perp_lab.search.candidate import Candidate, CandidateStatus


@dataclass
class Counters:
    """Exact candidate accounting shared by Random Search and the GA."""

    proposed: int = 0
    invalid: int = 0
    duplicate: int = 0
    cached: int = 0
    evaluated: int = 0  # unique objective evaluations (the budgeted quantity)

    def to_dict(self) -> dict[str, int]:
        return {
            "proposed": self.proposed,
            "invalid": self.invalid,
            "duplicate": self.duplicate,
            "cached": self.cached,
            "evaluated": self.evaluated,
        }


@dataclass
class SearchOutcome:
    """One algorithm's full result: unique candidates, counters, convergence."""

    algorithm: str
    version: str
    seed: int
    budget: int
    candidates: list[Candidate]
    counters: Counters
    convergence: list[float]
    best: Candidate | None
    extra: dict[str, Any] = field(default_factory=dict)

    def feasible_candidates(self) -> list[Candidate]:
        return [c for c in self.candidates if c.status == CandidateStatus.EVALUATED]

    def summary(self) -> dict[str, Any]:
        feasible = self.feasible_candidates()
        return {
            "algorithm": self.algorithm,
            "version": self.version,
            "seed": self.seed,
            "budget": self.budget,
            "counters": self.counters.to_dict(),
            "n_unique_candidates": len(self.candidates),
            "n_feasible": len(feasible),
            "best_fitness": self.best.fitness if self.best else None,
            "best_candidate_id": self.best.candidate_id if self.best else None,
        }
