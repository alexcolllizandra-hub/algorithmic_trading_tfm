"""Deterministic Random Search over a shared :class:`SearchSpace`.

Fair-budget definition (identical for the GA): the *budget* caps the number of
**unique objective evaluations** (candidate backtests). Proposals that fail
parameter/family validation (``invalid``) and repeats of an already-seen
candidate (``duplicate``) do **not** consume the budget; they are counted
separately. A candidate that is backtested but violates a hard constraint still
counts as one evaluation (it consumed the objective).
"""

from __future__ import annotations

from perp_lab.search.candidate import Candidate, CandidateStatus
from perp_lab.search.evaluator import CandidateEvaluator
from perp_lab.search.outcome import Counters, SearchOutcome
from perp_lab.search.space import SearchSpace

ALGORITHM = "random_search"
VERSION = "1.0.0"


def _best(candidates: list[Candidate]) -> Candidate | None:
    feasible = [c for c in candidates if c.status == CandidateStatus.EVALUATED]
    if not feasible:
        return None
    return max(feasible, key=lambda c: c.fitness if c.fitness is not None else float("-inf"))


def run_random_search(
    evaluator: CandidateEvaluator,
    space: SearchSpace,
    *,
    budget: int,
    seed: int,
    max_attempts_factor: int = 200,
) -> SearchOutcome:
    """Sample, de-duplicate and evaluate candidates until the budget is spent."""
    import numpy as np

    rng = np.random.default_rng(seed)
    counters = Counters()
    seen: set[str] = set()
    candidates: list[Candidate] = []
    convergence: list[float] = []
    best_so_far = float("-inf")

    max_attempts = max(budget * max_attempts_factor, budget + 1)
    attempts = 0
    while counters.evaluated < budget and attempts < max_attempts:
        attempts += 1
        counters.proposed += 1
        values = space.sample(rng)
        ok, _reason = space.is_valid(values)
        if not ok:
            counters.invalid += 1
            continue
        cid = space.candidate_hash(values)
        if cid in seen:
            counters.duplicate += 1
            continue
        seen.add(cid)
        candidate = Candidate.create(space, values, seed=seed, step=counters.evaluated)
        evaluator.evaluate(candidate)
        counters.evaluated += 1
        candidates.append(candidate)
        if candidate.status == CandidateStatus.EVALUATED and candidate.fitness is not None:
            best_so_far = max(best_so_far, candidate.fitness)
        convergence.append(best_so_far)

    return SearchOutcome(
        algorithm=ALGORITHM,
        version=VERSION,
        seed=seed,
        budget=budget,
        candidates=candidates,
        counters=counters,
        convergence=convergence,
        best=_best(candidates),
        extra={"attempts": attempts, "space_exhausted": attempts >= max_attempts},
    )
