"""Unit tests for deterministic Random Search."""

from __future__ import annotations

from search_helpers import build_env

from perp_lab.search.candidate import CandidateStatus
from perp_lab.search.random_search import run_random_search


def test_random_search_is_deterministic() -> None:
    e1 = build_env(seed=11)
    e2 = build_env(seed=11)
    out1 = run_random_search(e1.evaluator, e1.space, budget=10, seed=5)
    out2 = run_random_search(e2.evaluator, e2.space, budget=10, seed=5)
    ids1 = [c.candidate_id for c in out1.candidates]
    ids2 = [c.candidate_id for c in out2.candidates]
    assert ids1 == ids2
    assert [c.fitness for c in out1.candidates] == [c.fitness for c in out2.candidates]
    assert out1.convergence == out2.convergence


def test_budget_counts_unique_evaluations_only() -> None:
    env = build_env(seed=7)
    out = run_random_search(env.evaluator, env.space, budget=12, seed=3)
    # Exactly `budget` unique evaluations (space is far larger than 12).
    assert out.counters.evaluated == 12
    assert len(out.candidates) == 12
    # No duplicate objective evaluations.
    assert len({c.candidate_id for c in out.candidates}) == 12
    # Duplicates and invalid proposals do not consume the budget.
    assert out.counters.proposed >= out.counters.evaluated


def test_best_candidate_is_feasible_and_maximal() -> None:
    env = build_env(seed=9)
    out = run_random_search(env.evaluator, env.space, budget=15, seed=1)
    assert out.best is not None
    assert out.best.status == CandidateStatus.EVALUATED
    feasible = [c.fitness for c in out.feasible_candidates() if c.fitness is not None]
    assert out.best.fitness == max(feasible)


def test_convergence_is_monotonic_non_decreasing() -> None:
    env = build_env(seed=4)
    out = run_random_search(env.evaluator, env.space, budget=12, seed=2)
    for a, b in zip(out.convergence, out.convergence[1:], strict=False):
        assert b >= a
