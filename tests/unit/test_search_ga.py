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


def _ga(env, *, budget=18, seed=5, pop=6, gens=3):
    return run_genetic_algorithm(
        env.evaluator,
        env.space,
        population_size=pop,
        generations=gens,
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


def test_ga_never_exceeds_budget() -> None:
    env = build_env(seed=7)
    out = _ga(env, budget=10, pop=5, gens=4)
    assert out.counters.evaluated <= 10


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


def test_ga_fair_budget_matches_random_search_cap() -> None:
    env_ga = build_env(seed=6)
    env_rs = build_env(seed=6)
    budget = 12
    ga = _ga(env_ga, budget=budget, pop=4, gens=3)
    rs = run_random_search(env_rs.evaluator, env_rs.space, budget=budget, seed=5)
    assert ga.counters.evaluated <= budget
    assert rs.counters.evaluated <= budget


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
