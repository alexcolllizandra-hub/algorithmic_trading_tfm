"""Mixed-type Genetic Algorithm over a shared :class:`SearchSpace`.

Operators handle integers, floats, categoricals, booleans and conditional
parameters through the typed parameter objects, so the GA never hard-codes
family knowledge. It uses the **same** evaluator, folds, objective and
fair-budget definition as Random Search: the budget caps the number of unique
objective evaluations. Elites and duplicate offspring reuse cached fitness and
never consume additional evaluations, guaranteeing the GA cannot obtain more
objective evaluations than Random Search.
"""

from __future__ import annotations

import numpy as np

from perp_lab.search.candidate import Candidate, CandidateStatus
from perp_lab.search.evaluator import CandidateEvaluator
from perp_lab.search.outcome import Counters, SearchOutcome
from perp_lab.search.space import ParamValue, SearchSpace, population_diversity

ALGORITHM = "genetic_algorithm"
VERSION = "1.0.0"


def _fitness(candidate: Candidate) -> float:
    if candidate.status != CandidateStatus.EVALUATED or candidate.fitness is None:
        return float("-inf")
    return candidate.fitness


def _tournament(rng: np.random.Generator, population: list[Candidate], size: int) -> Candidate:
    idx = rng.integers(0, len(population), size=min(size, len(population)))
    contenders = [population[int(i)] for i in idx]
    return max(contenders, key=_fitness)


def _crossover(
    space: SearchSpace,
    a: dict[str, ParamValue],
    b: dict[str, ParamValue],
    rng: np.random.Generator,
    rate: float,
) -> dict[str, ParamValue]:
    child = dict(a)
    if rng.random() < rate:
        for name in space.param_names():
            if rng.random() < 0.5:
                child[name] = b[name]
    return child


def _mutate(
    space: SearchSpace,
    values: dict[str, ParamValue],
    rng: np.random.Generator,
    rate: float,
) -> dict[str, ParamValue]:
    out = dict(values)
    for p in space.params:
        if rng.random() < rate:
            out[p.name] = p.mutate(out[p.name], rng)
    return out


def run_genetic_algorithm(
    evaluator: CandidateEvaluator,
    space: SearchSpace,
    *,
    population_size: int,
    generations: int,
    crossover_rate: float,
    mutation_rate: float,
    elitism: int,
    tournament_size: int,
    seed: int,
    budget: int,
    max_attempts_factor: int = 200,
) -> SearchOutcome:
    rng = np.random.default_rng(seed)
    counters = Counters()
    convergence: list[float] = []
    best_so_far = float("-inf")
    unique: dict[str, Candidate] = {}

    def evaluate(candidate: Candidate) -> None:
        nonlocal best_so_far
        was_cached = evaluator.evaluate(candidate)
        if was_cached:
            counters.cached += 1
        else:
            counters.evaluated += 1
        unique.setdefault(candidate.candidate_id, candidate)
        if candidate.status == CandidateStatus.EVALUATED and candidate.fitness is not None:
            best_so_far = max(best_so_far, candidate.fitness)
        convergence.append(best_so_far)

    def propose(
        values: dict[str, ParamValue], step: int, parents: tuple[str, ...]
    ) -> Candidate | None:
        counters.proposed += 1
        ok, _reason = space.is_valid(values)
        if not ok:
            counters.invalid += 1
            return None
        return Candidate.create(space, values, seed=seed, step=step, parent_ids=parents)

    # -- Generation 0: deterministic unique initial population -------------- #
    population: list[Candidate] = []
    pop_hashes: set[str] = set()
    attempts = 0
    max_attempts = max(population_size * max_attempts_factor, population_size + 1)
    while len(population) < population_size and attempts < max_attempts:
        attempts += 1
        if counters.evaluated >= budget:
            break
        cand = propose(space.sample(rng), step=0, parents=())
        if cand is None or cand.candidate_id in pop_hashes:
            if cand is not None:
                counters.duplicate += 1
            continue
        evaluate(cand)
        population.append(cand)
        pop_hashes.add(cand.candidate_id)

    gen_best: list[dict[str, object]] = []
    diversity: list[dict[str, object]] = []
    lineage: list[dict[str, object]] = []

    def record_generation(gen: int, pop: list[Candidate]) -> None:
        best = max(pop, key=_fitness) if pop else None
        gen_best.append(
            {
                "generation": gen,
                "best_candidate_id": best.candidate_id if best else None,
                "best_fitness": _fitness(best) if best else None,
                "n_evaluated": counters.evaluated,
            }
        )
        div = population_diversity(space, [c.active_params for c in pop]) if pop else 0.0
        unique_ratio = len({c.candidate_id for c in pop}) / len(pop) if pop else 0.0
        diversity.append({"generation": gen, "param_diversity": div, "unique_ratio": unique_ratio})

    record_generation(0, population)

    # -- Evolution loop ----------------------------------------------------- #
    for gen in range(1, generations):
        if counters.evaluated >= budget:
            break
        ranked = sorted(population, key=_fitness, reverse=True)
        next_pop: list[Candidate] = list(ranked[: min(elitism, len(ranked))])
        next_hashes: set[str] = {c.candidate_id for c in next_pop}

        child_attempts = 0
        max_child_attempts = max(population_size * max_attempts_factor, population_size + 1)
        while len(next_pop) < population_size and child_attempts < max_child_attempts:
            child_attempts += 1
            if counters.evaluated >= budget:
                break
            p1 = _tournament(rng, population, tournament_size)
            p2 = _tournament(rng, population, tournament_size)
            child_values = _crossover(space, p1.params, p2.params, rng, crossover_rate)
            child_values = _mutate(space, child_values, rng, mutation_rate)
            child_values = space.repair(child_values)
            child = propose(child_values, step=gen, parents=(p1.candidate_id, p2.candidate_id))
            if child is None:
                continue
            if child.candidate_id in next_hashes:
                counters.duplicate += 1
                continue
            evaluate(child)
            next_pop.append(child)
            next_hashes.add(child.candidate_id)
            lineage.append(
                {
                    "generation": gen,
                    "child": child.candidate_id,
                    "parents": [p1.candidate_id, p2.candidate_id],
                }
            )

        # If the budget ran out mid-fill, keep the population size stable with elites.
        while len(next_pop) < population_size and ranked:
            next_pop.append(ranked[len(next_pop) % len(ranked)])
        population = next_pop
        record_generation(gen, population)

    candidates = list(unique.values())
    best = max(
        (c for c in candidates if c.status == CandidateStatus.EVALUATED),
        key=_fitness,
        default=None,
    )
    return SearchOutcome(
        algorithm=ALGORITHM,
        version=VERSION,
        seed=seed,
        budget=budget,
        candidates=candidates,
        counters=counters,
        convergence=convergence,
        best=best,
        extra={
            "population_size": population_size,
            "generations": generations,
            "crossover_rate": crossover_rate,
            "mutation_rate": mutation_rate,
            "elitism": elitism,
            "tournament_size": tournament_size,
            "generation_best": gen_best,
            "diversity": diversity,
            "lineage": lineage,
        },
    )
