"""Every registered family must be reachable, samplable and correctly constrained.

A family can be implemented perfectly and still be dead: if its builder is not in
the registry, or its parameters cannot be sampled, or its constraints reject every
draw, the search will simply never produce one. These tests check that the wiring
holds for all six families rather than only the three that existed first.
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pytest

from perp_lab.config import load_experiment_config
from perp_lab.search.registry import FAMILIES, available_families, build_search_space
from perp_lab.search.space import ParamValue
from perp_lab.strategies.base import Strategy
from perp_lab.strategies.cross_asset import CrossAssetConfirmation

NEW_FAMILIES = ("volatility_breakout", "funding", "BTC_ETH_confirmation")


def _f(value: ParamValue) -> float:
    return float(cast(float, value))


def _i(value: ParamValue) -> int:
    return int(cast(int, value))


@pytest.fixture(scope="module")
def exp():
    return load_experiment_config("configs/experiment.yaml")


def test_every_declared_family_has_a_builder() -> None:
    assert set(FAMILIES) == set(available_families())


@pytest.mark.parametrize("family", NEW_FAMILIES)
def test_the_new_families_are_registered(family: str) -> None:
    assert family in available_families()


@pytest.mark.parametrize("family", FAMILIES)
def test_every_family_samples_valid_strategies(exp, family: str) -> None:
    """Constraints must leave a usable region, not reject everything."""
    space = build_search_space(exp, family, "ETHUSDT")
    rng = np.random.default_rng(7)
    built = 0
    for _ in range(60):
        values = space.sample(rng)
        ok, _ = space.is_valid(values)
        if ok:
            strategy = cast(Strategy, space.build(values))
            assert strategy.params()["family"]
            built += 1
    assert built > 0, f"{family}: no sampled candidate survived its own constraints"


@pytest.mark.parametrize("family", FAMILIES)
def test_repair_makes_most_draws_admissible(exp, family: str) -> None:
    """Repair exists so the budget is not burned on candidates that cannot exist."""
    space = build_search_space(exp, family, "BTCUSDT")
    rng = np.random.default_rng(11)
    draws = [space.sample(rng) for _ in range(200)]
    valid = sum(1 for v in draws if space.is_valid(v)[0])
    assert valid / len(draws) > 0.5, f"{family}: repair leaves most draws invalid"


@pytest.mark.parametrize("family", FAMILIES)
def test_sampling_is_reproducible_from_the_seed(exp, family: str) -> None:
    space = build_search_space(exp, family, "BTCUSDT")
    a = [space.sample(np.random.default_rng(3)) for _ in range(3)]
    b = [space.sample(np.random.default_rng(3)) for _ in range(3)]
    assert a == b


# --------------------------------------------------------------------------- #
# Family-specific constraints reach the search space, not only the dataclass
# --------------------------------------------------------------------------- #


def test_volatility_stop_never_receives_an_exit_beyond_its_entry(exp) -> None:
    space = build_search_space(exp, "volatility_breakout", "BTCUSDT")
    rng = np.random.default_rng(5)
    checked = 0
    for _ in range(300):
        values = space.sample(rng)
        if not space.is_valid(values)[0] or values["exit_mode"] != "volatility_stop":
            continue
        assert _f(values["exit_atr"]) < _f(values["entry_atr"])
        checked += 1
    assert checked > 0, "no volatility_stop candidate was sampled"


def test_funding_exit_band_is_always_inside_the_entry_band(exp) -> None:
    space = build_search_space(exp, "funding", "BTCUSDT")
    rng = np.random.default_rng(5)
    for _ in range(200):
        values = space.sample(rng)
        if space.is_valid(values)[0]:
            assert _f(values["exit_z"]) < _f(values["entry_z"])


def test_cross_asset_resolves_the_reference_from_the_traded_symbol(exp) -> None:
    rng = np.random.default_rng(5)
    for target, expected in (("BTCUSDT", "ETHUSDT"), ("ETHUSDT", "BTCUSDT")):
        space = build_search_space(exp, "BTC_ETH_confirmation", target)
        values = space.sample(rng)
        strategy = space.build(values)
        assert isinstance(strategy, CrossAssetConfirmation)
        assert strategy.target_symbol == target
        assert strategy.reference_symbol == expected


def test_cross_asset_refuses_a_symbol_with_no_configured_reference(exp) -> None:
    """Silently degrading to a single-asset strategy would mislabel the family."""
    with pytest.raises(ValueError, match="No reference symbol configured"):
        build_search_space(exp, "BTC_ETH_confirmation", "SOLUSDT")


def test_cross_asset_lag_is_never_below_one_bar(exp) -> None:
    space = build_search_space(exp, "BTC_ETH_confirmation", "ETHUSDT")
    rng = np.random.default_rng(9)
    for _ in range(150):
        values = space.sample(rng)
        if space.is_valid(values)[0]:
            assert _i(values["reference_lag"]) >= 1


def test_funding_family_requests_the_feature_it_reads(exp) -> None:
    """A family that names a feature it never receives would trade on nulls."""
    space = build_search_space(exp, "funding", "BTCUSDT")
    kinds = {getattr(item, "kind", None) for item in space.feature_items}
    assert "funding_rate" in kinds
