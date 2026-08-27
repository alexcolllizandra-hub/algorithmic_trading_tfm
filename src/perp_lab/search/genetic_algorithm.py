"""Mixed-type Genetic Algorithm over a shared :class:`SearchSpace`.

Operators handle integers, floats, categoricals, booleans and conditional
parameters through the typed parameter objects, so the GA never hard-codes
family knowledge. It uses the **same** evaluator, folds, objective and
fair-budget definition as Random Search: the budget caps the number of unique
objective evaluations. Elites and duplicate offspring reuse cached fitness and
never consume additional evaluations, guaranteeing the GA cannot obtain more
objective evaluations than Random Search.

The engine comparison this serves is specified in ADR 0009; ADR 0014 records why
a budget can exceed what a finite space can supply, which is the case the
termination reasons below distinguish.
"""

from __future__ import annotations

import numpy as np

from perp_lab.search.candidate import Candidate, CandidateStatus
from perp_lab.search.evaluator import CandidateEvaluator
from perp_lab.search.outcome import Counters, SearchOutcome
from perp_lab.search.space import ParamValue, SearchSpace, population_diversity

ALGORITHM = "genetic_algorithm"
VERSION = "2.1.0"

# Generations in a row that buy no new unique evaluation before the search is
# declared converged. One barren generation is normal drift; several in a row mean
# crossover and mutation are only regenerating genotypes already scored.
_MAX_STALLED_GENERATIONS = 5


def _fitness(candidate: Candidate) -> float:
    # -inf, so failed and unevaluated candidates lose every tournament without
    # needing a special case in selection.
    if candidate.status != CandidateStatus.EVALUATED or candidate.fitness is None:
        return float("-inf")
    return candidate.fitness


def _tournament(rng: np.random.Generator, population: list[Candidate], size: int) -> Candidate:
    # Sampling with replacement: a contender may appear twice in one tournament.
    # That keeps selection pressure independent of population size.
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
    # Uniform crossover: each gene is drawn independently from either parent with
    # equal probability. Chosen over single-point because the parameter vector has
    # no meaningful ordering, so no locus is more natural to cut at than another.
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
    max_generations: int,
    crossover_rate: float,
    mutation_rate: float,
    elitism: int,
    tournament_size: int,
    seed: int,
    budget: int,
    max_attempts_factor: int = 200,
) -> SearchOutcome:
    """Evolve until exactly ``budget`` unique objective evaluations are spent.

    The loop is driven by the budget, not by a generation count. A generational
    GA carries elites forward with cached fitness and re-proposes genotypes it has
    already scored, so a fixed number of generations consumes an amount of budget
    that varies with the seed and the search space -- which would give each unit of
    a multi-seed study a slightly different budget and make the units incomparable.

    ``max_generations`` is a safety cap, not the target. If the budget is not met
    within it, the outcome records why and the caller decides whether that is
    acceptable; it is never silently reported as a completed run.
    """
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

    # Generation 0 is sampled to be unique by construction, so the GA and Random
    # Search start from populations of the same effective size.
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

    gen = 0
    stalled_generations = 0
    random_immigrants = 0
    space_exhausted = False
    while counters.evaluated < budget and gen + 1 < max_generations:
        gen += 1
        spent_before = counters.evaluated
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

        # If the budget ran out mid-fill, pad with elites so population_size stays
        # constant across generations. The repeats are deliberate and cost nothing:
        # cached fitness means they never consume an objective evaluation.
        while len(next_pop) < population_size and ranked:
            next_pop.append(ranked[len(next_pop) % len(ranked)])
        population = next_pop
        record_generation(gen, population)

        # A generation that buys no new evaluation means the population has
        # collapsed onto genotypes already scored. Continuing forever would spin;
        # stopping immediately would abandon a budget a mutation might still reach.
        stalled_generations = 0 if counters.evaluated > spent_before else stalled_generations + 1
        if stalled_generations >= _MAX_STALLED_GENERATIONS:
            # Selection can collapse a finite population before the declared
            # fair budget is spent, especially when the target covers most of a
            # small space. Stopping here gives the GA less effort than RS. Inject
            # globally unseen random immigrants, then resume evolution. This is
            # a diversity mechanism, not extra budget: only the same unique
            # objective evaluations count, and the run still fails if no unseen
            # identity can be found.
            immigrant_target = min(
                max(population_size - elitism, 1),
                budget - counters.evaluated,
            )
            immigrants: list[Candidate] = []
            immigrant_attempts = 0
            max_immigrant_attempts = max(
                immigrant_target * max_attempts_factor,
                population_size * max_attempts_factor,
            )
            while (
                len(immigrants) < immigrant_target
                and counters.evaluated < budget
                and immigrant_attempts < max_immigrant_attempts
            ):
                immigrant_attempts += 1
                immigrant = propose(space.sample(rng), step=gen, parents=())
                if immigrant is None:
                    continue
                if immigrant.candidate_id in unique:
                    counters.duplicate += 1
                    continue
                evaluate(immigrant)
                immigrants.append(immigrant)
                random_immigrants += 1

            if not immigrants:
                space_exhausted = True
                break

            ranked = sorted(population, key=_fitness, reverse=True)
            population = list(ranked[: min(elitism, len(ranked))]) + immigrants
            while len(population) < population_size and ranked:
                population.append(ranked[len(population) % len(ranked)])
            record_generation(gen, population)
            stalled_generations = 0

    if counters.evaluated >= budget:
        termination = "budget_reached"
    elif space_exhausted:
        termination = "finite_space_exhausted"
    elif stalled_generations >= _MAX_STALLED_GENERATIONS:
        termination = "population_converged"
    else:
        termination = "max_generations"

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
            "max_generations": max_generations,
            "generations_run": gen + 1,
            "termination_reason": termination,
            "budget_reached": counters.evaluated == budget,
            "crossover_rate": crossover_rate,
            "mutation_rate": mutation_rate,
            "elitism": elitism,
            "tournament_size": tournament_size,
            "generation_best": gen_best,
            "diversity": diversity,
            "lineage": lineage,
            "random_immigrants": random_immigrants,
        },
    )
