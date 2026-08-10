"""Unit tests for the typed parameter-space system."""

from __future__ import annotations

from typing import cast

import numpy as np
import pytest

from perp_lab.config import load_experiment_config
from perp_lab.search.config import GASettings, SearchRunConfig
from perp_lab.search.registry import build_search_space
from perp_lab.search.runner import SearchSpaceBudgetError, run_search
from perp_lab.search.space import (
    BoolParam,
    CategoricalParam,
    FloatParam,
    IntParam,
    SearchSpace,
    param_distance,
    population_diversity,
)
from perp_lab.strategies.base import Strategy


def _rng(seed: int = 0) -> np.random.Generator:
    return np.random.default_rng(seed)


def test_int_param_boundaries_and_grid() -> None:
    p = IntParam("w", 2, 10, step=2)
    for _ in range(50):
        v = p.sample(_rng(_))
        assert p.is_valid(v)
        assert v in (2, 4, 6, 8, 10)
    assert p.repair(11) == 10
    assert p.repair(1) == 2
    assert p.repair(5) in (4, 6)  # snapped to the step grid
    assert not p.is_valid(3)


def test_float_param_log_scale_within_bounds() -> None:
    p = FloatParam("z", 0.1, 10.0, log=True)
    vals = [float(p.sample(_rng(s))) for s in range(200)]  # type: ignore[arg-type]
    assert all(0.1 <= v <= 10.0 for v in vals)
    assert p.repair(100.0) == 10.0
    assert p.repair(float("nan")) == 0.1


def test_categorical_and_bool_sampling() -> None:
    c = CategoricalParam("d", ("long", "short", "both"))
    seen = {c.sample(_rng(s)) for s in range(50)}
    assert seen <= {"long", "short", "both"}
    assert c.repair("bogus") == "long"
    b = BoolParam("flag")
    assert isinstance(b.sample(_rng(1)), bool)
    assert b.mutate(True, _rng(1)) is False


def test_deterministic_sampling_same_seed() -> None:
    exp = load_experiment_config("configs/experiment.yaml")
    space = build_search_space(exp, "momentum")
    a = space.sample(_rng(123))
    b = space.sample(_rng(123))
    assert a == b
    assert space.candidate_hash(a) == space.candidate_hash(b)


def test_conditional_params_excluded_from_hash_when_inactive() -> None:
    exp = load_experiment_config("configs/experiment.yaml")
    space = build_search_space(exp, "momentum")
    base = {
        "fast": 6,
        "slow": 96,
        "direction": "both",
        "use_trend_filter": False,
        "trend_filter_ma": 168,
        "use_regime_gate": False,
        "regime_gate": ("low", "medium"),
    }
    other = dict(base)
    other["trend_filter_ma"] = 336  # inactive -> must not change identity
    other["regime_gate"] = ("medium", "high")
    assert space.candidate_hash(base) == space.candidate_hash(other)
    # Active parameters exclude the inactive conditionals.
    active = space.active_params(base)
    assert "trend_filter_ma" not in active
    assert "regime_gate" not in active


def test_momentum_repair_enforces_fast_below_slow() -> None:
    exp = load_experiment_config("configs/experiment.yaml")
    space = build_search_space(exp, "momentum")
    bad = {
        "fast": 48,
        "slow": 48,
        "direction": "both",
        "use_trend_filter": False,
        "trend_filter_ma": 168,
        "use_regime_gate": False,
        "regime_gate": ("low", "medium"),
    }
    repaired = space.repair(bad)
    ok, reason = space.is_valid(repaired)
    assert ok, reason
    assert cast(int, repaired["fast"]) < cast(int, repaired["slow"])


def test_mean_reversion_repair_enforces_exit_below_entry() -> None:
    exp = load_experiment_config("configs/experiment.yaml")
    space = build_search_space(exp, "mean_reversion")
    bad = {
        "zscore_window": 48,
        "entry_z": 1.5,
        "exit_z": 1.0,
        "direction": "both",
        "use_regime_gate": False,
        "regime_gate": ("low", "medium"),
    }
    # exit 1.0 < entry 1.5 already valid; force a violation:
    bad["exit_z"] = 1.0
    bad["entry_z"] = 1.5
    assert space.is_valid(bad)[0]
    violate = dict(bad)
    violate["exit_z"] = 1.0
    violate["entry_z"] = 1.0  # invalid: exit == entry
    ok, _ = space.is_valid(violate)
    assert not ok
    repaired = space.repair(violate)
    assert space.is_valid(repaired)[0]


def test_candidate_hash_stable_and_duplicate_detection() -> None:
    exp = load_experiment_config("configs/experiment.yaml")
    space = build_search_space(exp, "breakout")
    seen: set[str] = set()
    dupes = 0
    for s in range(300):
        v = space.sample(_rng(s))
        h = space.candidate_hash(v)
        if h in seen:
            dupes += 1
        seen.add(h)
    assert dupes > 0  # a finite space must repeat within 300 draws
    # Re-hashing the same values is stable.
    v = space.sample(_rng(5))
    assert space.candidate_hash(v) == space.candidate_hash(dict(v))


def test_finite_cardinality_collapses_inactive_and_repaired_duplicates() -> None:
    exp = load_experiment_config("configs/experiment.yaml")
    # The raw breakout product has 162 tuples, but inactive regime choices
    # collapse to 108 distinct candidate identities.
    assert build_search_space(exp, "breakout").finite_cardinality() == 108
    assert build_search_space(exp, "momentum").finite_cardinality() == 540


def test_continuous_space_has_no_finite_cardinality() -> None:
    space = SearchSpace(
        "continuous",
        "1",
        (FloatParam("x", 0.0, 1.0),),
        lambda values: values,
        lambda values: values,
        lambda values: (True, None),
    )
    assert space.finite_cardinality() is None


def test_impossible_budget_fails_before_loading_market_data() -> None:
    cfg = SearchRunConfig(
        family="breakout",
        effective_budget=109,
        ga=GASettings(population_size=30, max_generations=200, elitism=3),
    )
    with pytest.raises(SearchSpaceBudgetError, match="finite cardinality 108"):
        run_search(cfg, write_artifacts=False)


def test_build_constructs_working_strategy() -> None:
    exp = load_experiment_config("configs/experiment.yaml")
    space = build_search_space(exp, "mean_reversion")
    v = space.sample(_rng(3))
    strat = cast(Strategy, space.build(v))
    assert strat.params()["family"] == "mean_reversion"
    assert strat.required_features()  # zscore column


def test_diversity_metrics() -> None:
    exp = load_experiment_config("configs/experiment.yaml")
    space = build_search_space(exp, "mean_reversion")
    a = space.active_params(space.sample(_rng(1)))
    assert param_distance(space, a, a) == 0.0
    pops = [space.active_params(space.sample(_rng(s))) for s in range(6)]
    div = population_diversity(space, pops)
    assert 0.0 <= div <= 1.0


def test_invalid_space_construction_rejected() -> None:
    with pytest.raises(ValueError):
        IntParam("x", 10, 1)
    with pytest.raises(ValueError):
        CategoricalParam("x", ())
    with pytest.raises(ValueError):
        FloatParam("x", 0.0, 1.0, log=True)


def test_search_space_describe_roundtrip() -> None:
    exp = load_experiment_config("configs/experiment.yaml")
    space: SearchSpace = build_search_space(exp, "momentum")
    desc = space.describe()
    assert desc["family"] == "momentum"
    assert {p["name"] for p in desc["params"]} >= {"fast", "slow", "direction"}
