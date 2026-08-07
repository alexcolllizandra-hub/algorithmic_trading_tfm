"""Unit tests for the Genetic Algorithm and its operators."""

from __future__ import annotations

from itertools import pairwise

import numpy as np
from search_helpers import build_env

from perp_lab.search.candidate import Candidate, CandidateStatus
from perp_lab.search.genetic_algorithm import (
    _crossover,
    _mutate,
    _tournament,
    run_genetic_algorithm,
)
from perp_lab.search.random_search import run_random_search


def _ga(env, *, budget=18, seed=5, pop=6, max_gens=30):
    return run_genetic_algorithm(
        env.evaluator,
        env.space,
        population_size=pop,
        max_generations=max_gens,
        crossover_rate=0.7,
        mutation_rate=0.3,
        elitism=1,
        tournament_size=3,
        seed=seed,
        budget=budget,
    )


def test_ga_deterministic() -> None:
    e1 = build_env(seed=11)
    e2 = build_env(seed=11)
    out1 = _ga(e1)
    out2 = _ga(e2)
    assert {c.candidate_id for c in out1.candidates} == {c.candidate_id for c in out2.candidates}
    assert out1.convergence == out2.convergence
    assert out1.extra["generation_best"] == out2.extra["generation_best"]


def test_ga_spends_exactly_the_budget_and_never_more() -> None:
    env = build_env(seed=7)
    out = _ga(env, budget=10, pop=5)
    assert out.counters.evaluated == 10
    assert out.extra["termination_reason"] == "budget_reached"
    assert out.extra["budget_reached"] is True


def test_ga_keeps_evolving_past_a_generation_count_to_reach_its_budget() -> None:
    """The loop is driven by the budget; a fixed generation count would fall short.

    With population 5 and elitism 1, four generations can add at most 5 + 3*4 = 17
    new genotypes, and cross-generation duplicates usually make it fewer. Asking
    for 30 must simply run more generations.
    """
    out = _ga(build_env(seed=7), budget=30, pop=5)
    assert out.counters.evaluated == 30
    assert out.extra["generations_run"] > 4


def test_ga_reports_when_it_cannot_reach_the_budget() -> None:
    """Stopping short must be visible, never reported as a completed run."""
    out = _ga(build_env(seed=7), budget=10_000, pop=4, max_gens=3)
    assert out.counters.evaluated < 10_000
    assert out.extra["budget_reached"] is False
    assert out.extra["termination_reason"] in {"max_generations", "population_converged"}


def test_ga_records_lineage_and_diversity() -> None:
    env = build_env(seed=3)
    out = _ga(env)
    assert out.extra["lineage"]  # at least one offspring with parents
    for entry in out.extra["lineage"]:
        assert len(entry["parents"]) == 2
    div = out.extra["diversity"]
    assert div and all(0.0 <= d["param_diversity"] <= 1.0 for d in div)


def test_ga_elitism_preserves_best_across_generations() -> None:
    env = build_env(seed=8)
    out = _ga(env)
    gen_best = [
        g["best_fitness"] for g in out.extra["generation_best"] if g["best_fitness"] is not None
    ]
    # With elitism the best-so-far never decreases generation to generation.
    for a, b in pairwise(gen_best):
        assert b >= a - 1e-9


def test_both_engines_land_on_the_identical_budget() -> None:
    """Neither engine is capped at the other's spend; both hit the declared target."""
    budget = 12
    ga = _ga(build_env(seed=6), budget=budget, pop=4)
    env_rs = build_env(seed=6)
    rs = run_random_search(env_rs.evaluator, env_rs.space, budget=budget, seed=5)
    assert ga.counters.evaluated == rs.counters.evaluated == budget


def test_cached_duplicate_and_invalid_proposals_never_consume_budget() -> None:
    env = build_env(seed=4)
    out = _ga(env, budget=15, pop=5)
    counters = out.counters
    assert counters.evaluated == 15
    # Everything the GA proposed beyond its 15 paid evaluations was free.
    assert counters.proposed >= counters.evaluated
    assert counters.duplicate + counters.invalid + counters.cached == (
        counters.proposed - counters.evaluated
    )


def _mk_candidate(env, values, fitness) -> Candidate:
    c = Candidate.create(env.space, values, seed=0, step=0)
    c.status = CandidateStatus.EVALUATED
    c.fitness = fitness
    return c


def test_crossover_mixes_parent_genes() -> None:
    env = build_env(seed=2)
    rng = np.random.default_rng(0)
    a = env.space.sample(np.random.default_rng(1))
    b = env.space.sample(np.random.default_rng(2))
    child = _crossover(env.space, a, b, rng, rate=1.0)
    for name in env.space.param_names():
        assert child[name] in (a[name], b[name])


def test_mutation_changes_all_genes_at_rate_one() -> None:
    env = build_env(seed=2)
    rng = np.random.default_rng(0)
    values = env.space.sample(np.random.default_rng(3))
    mutated = _mutate(env.space, values, rng, rate=1.0)
    changed = [n for n in env.space.param_names() if mutated[n] != values[n]]
    # Every single-choice-free parameter should change under full mutation.
    assert changed


def test_tournament_selects_highest_fitness() -> None:
    env = build_env(seed=2)
    rng = np.random.default_rng(0)
    pop = [
        _mk_candidate(env, env.space.sample(np.random.default_rng(s)), fitness=float(s))
        for s in range(5)
    ]
    winner = _tournament(rng, pop, size=5)
    assert winner.fitness == max(c.fitness for c in pop if c.fitness is not None)
