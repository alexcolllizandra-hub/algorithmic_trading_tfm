"""Gate S2-A: the S2 families are reachable and correctly budgeted in the registry.

Both engines build candidates only through ``build_search_space``, so a family
that is not registered cannot be searched. Beyond the S1-A checks, this batch
also has to prove that the *causality* constraint survives the search: no
sampled candidate may carry a zero flow lag, because the search space -- not the
strategy constructor -- is where a leaky configuration would enter the study.
"""

from __future__ import annotations

import numpy as np
import pytest

from perp_lab.config.settings import load_experiment_config
from perp_lab.search.registry import (
    R3_CLOSED_FAMILIES,
    S1_FAMILIES,
    S2_FAMILIES,
    available_families,
    build_search_space,
)
from perp_lab.strategies.base import Strategy

SYMBOL = "BTCUSDT"


@pytest.fixture(scope="module")
def experiment():
    return load_experiment_config()


def test_s2_families_are_registered_and_disjoint_from_every_closed_batch() -> None:
    assert set(S2_FAMILIES).isdisjoint(R3_CLOSED_FAMILIES)
    assert set(S2_FAMILIES).isdisjoint(S1_FAMILIES)
    assert set(S2_FAMILIES) <= set(available_families())


@pytest.mark.parametrize("family", S2_FAMILIES)
def test_sampled_candidates_are_valid_and_buildable(family: str, experiment) -> None:
    space = build_search_space(experiment, family, SYMBOL)
    rng = np.random.default_rng(0)
    built = 0
    for _ in range(200):
        values = space.sample(rng)
        ok, reason = space.is_valid(values)
        if not ok:
            assert reason
            continue
        strategy = space.build_fn(values)
        assert isinstance(strategy, Strategy)
        assert strategy.params()["family"] == family
        built += 1
    assert built > 0, f"{family} never produced a valid candidate in 200 draws"


@pytest.mark.parametrize("family", S2_FAMILIES)
def test_no_sampled_candidate_can_read_flow_contemporaneously(family: str, experiment) -> None:
    """The frozen lag rule must be unreachable-to-violate from inside the search."""
    space = build_search_space(experiment, family, SYMBOL)
    rng = np.random.default_rng(17)
    checked = 0
    for _ in range(300):
        values = space.sample(rng)
        if not space.is_valid(values)[0]:
            continue
        strategy = space.build_fn(values)
        assert isinstance(strategy, Strategy)
        lag = strategy.params()["flow_lag"]
        assert isinstance(lag, int) and lag >= 1, (
            f"{family} sampled flow_lag={lag!r}; contemporaneous flow is forbidden by "
            "docs/methodology/experimental_design.md"
        )
        checked += 1
    assert checked > 0


@pytest.mark.parametrize("family", S2_FAMILIES)
def test_sampling_is_deterministic_for_a_given_seed(family: str, experiment) -> None:
    space = build_search_space(experiment, family, SYMBOL)
    first = [space.sample(np.random.default_rng(11)) for _ in range(3)]
    second = [space.sample(np.random.default_rng(11)) for _ in range(3)]
    assert first == second


@pytest.mark.parametrize("family", S2_FAMILIES)
def test_s2_families_need_no_feature_engine_columns(family: str, experiment) -> None:
    """S2 reads raw klines, so it must not silently depend on a built feature.

    The flow windows are search parameters; materialising one feature column per
    candidate window would couple the feature frame to the search space. Any
    strategy that nonetheless declared a requirement would be reading a column
    the space never asked to be built, i.e. nulls at signal time.
    """
    space = build_search_space(experiment, family, SYMBOL)
    assert space.feature_items == ()
    rng = np.random.default_rng(3)
    for _ in range(50):
        values = space.sample(rng)
        if not space.is_valid(values)[0]:
            continue
        strategy = space.build_fn(values)
        assert isinstance(strategy, Strategy)
        assert strategy.required_features() == ()


@pytest.mark.parametrize("family", S2_FAMILIES)
def test_the_declared_hypothesis_count_is_reproducible(family: str, experiment) -> None:
    """The pre-specification records a space cardinality; it must be computable."""
    space = build_search_space(experiment, family, SYMBOL)
    cardinality = space.finite_cardinality()
    assert cardinality is not None and cardinality > 0


def test_recorded_cardinalities_match_the_frozen_prespecification(experiment) -> None:
    """Guard the numbers written into docs/roadmap/gate_s2_batch_01.md.

    If a grid changes, this test fails and forces the pre-specification (and the
    data-snooping ledger that depends on it) to be updated deliberately rather
    than drifting out of sync with the code.
    """
    expected = {
        "taker_flow_extreme": 6_912,
        "illiquidity_reversion": 5_184,
        "flow_price_divergence": 10_368,
    }
    actual = {
        family: build_search_space(experiment, family, SYMBOL).finite_cardinality()
        for family in S2_FAMILIES
    }
    assert actual == expected
