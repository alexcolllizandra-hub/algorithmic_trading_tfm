"""Strategy-search framework: shared spaces, evaluator, Random Search and GA.

Both search algorithms share one typed parameter-space system, one candidate
representation, one leakage-safe walk-forward evaluator and one objective, so a
Random-Search vs Genetic-Algorithm comparison is fair by construction.
"""

from perp_lab.search.candidate import Candidate, CandidateStatus
from perp_lab.search.config import SearchRunConfig, load_search_config
from perp_lab.search.evaluator import (
    CandidateEvaluator,
    FoldData,
    FoldsBundle,
    build_folds_data,
)
from perp_lab.search.genetic_algorithm import run_genetic_algorithm
from perp_lab.search.objective import (
    FAILURE_PENALTY,
    ObjectiveConfig,
    ObjectiveResult,
    aggregate_objective,
)
from perp_lab.search.outcome import Counters, SearchOutcome
from perp_lab.search.random_search import run_random_search
from perp_lab.search.registry import (
    SPACE_VERSION,
    available_families,
    build_search_space,
)
from perp_lab.search.runner import SearchRunResult, run_search
from perp_lab.search.space import (
    BoolParam,
    CategoricalParam,
    FloatParam,
    IntParam,
    Param,
    SearchSpace,
    population_diversity,
)

__all__ = [
    "FAILURE_PENALTY",
    "SPACE_VERSION",
    "BoolParam",
    "Candidate",
    "CandidateEvaluator",
    "CandidateStatus",
    "CategoricalParam",
    "Counters",
    "FloatParam",
    "FoldData",
    "FoldsBundle",
    "IntParam",
    "ObjectiveConfig",
    "ObjectiveResult",
    "Param",
    "SearchOutcome",
    "SearchRunConfig",
    "SearchRunResult",
    "SearchSpace",
    "aggregate_objective",
    "available_families",
    "build_folds_data",
    "build_search_space",
    "load_search_config",
    "population_diversity",
    "run_genetic_algorithm",
    "run_random_search",
    "run_search",
]
