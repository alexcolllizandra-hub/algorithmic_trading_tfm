"""Deterministic Random Search over a shared :class:`SearchSpace`.

Fair-budget definition (identical for the GA): the *budget* caps the number of
**unique objective evaluations** (candidate backtests). Proposals that fail
parameter/family validation (``invalid``) and repeats of an already-seen
candidate (``duplicate``) do **not** consume the budget; they are counted
separately. A candidate that is backtested but violates a hard constraint still
counts as one evaluation (it consumed the objective).

This is the baseline engine of the ADR 0009 comparison; ADR 0014 covers the case
where the declared budget exceeds what a finite space can supply.
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
    """Sample, de-duplicate and evaluate candidates until the budget is spent.

    Sampling is rejection-based, so a family whose space is mostly invalid can
    exhaust ``budget * max_attempts_factor`` proposals before spending its
    budget. That is a real outcome, not a bug: it is reported through
    ``termination_reason`` and ``space_exhausted`` rather than retried, because
    silently widening the search would break budget parity with the GA.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    counters = Counters()
    seen: set[str] = set()
    candidates: list[Candidate] = []
    convergence: list[float] = []
    best_so_far = float("-inf")

    # 200x headroom absorbs families with heavy constraint rejection; the
    # budget+1 floor keeps the loop viable when budget is 0 or 1.
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
        # step is the evaluation index, not the proposal index: rejected and
        # duplicate proposals leave no gap, so steps stay comparable to the GA's.
        candidate = Candidate.create(space, values, seed=seed, step=counters.evaluated)
        evaluator.evaluate(candidate)
        counters.evaluated += 1
        candidates.append(candidate)
        if candidate.status == CandidateStatus.EVALUATED and candidate.fitness is not None:
            best_so_far = max(best_so_far, candidate.fitness)
        convergence.append(best_so_far)

    termination = "budget_reached" if counters.evaluated >= budget else "max_attempts"
    return SearchOutcome(
        algorithm=ALGORITHM,
        version=VERSION,
        seed=seed,
        budget=budget,
        candidates=candidates,
        counters=counters,
        convergence=convergence,
        best=_best(candidates),
        extra={
            "attempts": attempts,
            "max_attempts": max_attempts,
            "termination_reason": termination,
            "budget_reached": counters.evaluated == budget,
            "space_exhausted": attempts >= max_attempts,
        },
    )
