"""Gate S1-A: the S1 families are reachable through the shared search registry.

Both engines build candidates only through ``build_search_space``, so a family
that is not registered here cannot be searched at all, and a space that samples
invalid candidates burns budget on proposals the evaluator will reject.
"""

from __future__ import annotations

import numpy as np
import pytest

from perp_lab.config.settings import load_experiment_config
from perp_lab.search.registry import (
    R3_CLOSED_FAMILIES,
    S1_FAMILIES,
    available_families,
    build_search_space,
)
from perp_lab.strategies.base import Strategy

SYMBOL = "BTCUSDT"


@pytest.fixture(scope="module")
def experiment():
    return load_experiment_config()


def test_s1_families_are_registered_and_disjoint_from_the_closed_ones() -> None:
    assert set(S1_FAMILIES).isdisjoint(R3_CLOSED_FAMILIES)
    assert set(S1_FAMILIES) <= set(available_families())


@pytest.mark.parametrize("family", S1_FAMILIES)
def test_sampled_candidates_are_valid_and_buildable(family: str, experiment) -> None:
    space = build_search_space(experiment, family, SYMBOL)
    rng = np.random.default_rng(0)
    built = 0
    for _ in range(200):
        values = space.sample(rng)
        ok, reason = space.is_valid(values)
        if not ok:
            # An invalid proposal is allowed, but it must be rejected with a
            # reason rather than silently building a broken strategy.
            assert reason
            continue
        strategy = space.build_fn(values)
        assert isinstance(strategy, Strategy)
        assert strategy.params()["family"] == family
        built += 1
    assert built > 0, f"{family} never produced a valid candidate in 200 draws"


@pytest.mark.parametrize("family", S1_FAMILIES)
def test_sampling_is_deterministic_for_a_given_seed(family: str, experiment) -> None:
    space = build_search_space(experiment, family, SYMBOL)
    first = [space.sample(np.random.default_rng(11)) for _ in range(3)]
    second = [space.sample(np.random.default_rng(11)) for _ in range(3)]
    assert first == second


@pytest.mark.parametrize("family", S1_FAMILIES)
def test_required_features_are_declared_by_every_built_strategy(family: str, experiment) -> None:
    space = build_search_space(experiment, family, SYMBOL)
    declared = {col for item in space.feature_items for col in _columns(item)}
    rng = np.random.default_rng(3)
    for _ in range(50):
        values = space.sample(rng)
        if not space.is_valid(values)[0]:
            continue
        strategy = space.build_fn(values)
        assert isinstance(strategy, Strategy)
        needed = set(strategy.required_features())
        missing = needed - declared
        assert not missing, (
            f"{family} builds strategies needing {sorted(missing)}, which the space never "
            "requests from the feature engine; they would be null at signal time."
        )


def _columns(item) -> tuple[str, ...]:
    from perp_lab.features.spec import resolve_spec

    spec = resolve_spec(
        item.kind,
        window=item.window,
        window_slow=getattr(item, "window_slow", None),
        lag=item.lag,
    )
    return spec.columns


def test_cross_asset_spread_refuses_an_unknown_target(experiment) -> None:
    with pytest.raises(ValueError, match="A spread needs two legs"):
        build_search_space(experiment, "xasset_spread_reversion", "SOLUSDT")
