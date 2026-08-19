"""The search config's family vocabulary must be the registry's, not a copy of it.

`SearchRunConfig.family` once carried a hand-written literal listing the families
it would accept. That list drifted from `search/registry.py`: the CRT round was
registered and reachable by both engines, but every CRT config was rejected at
validation time because the copy had never been updated.

The defect was the duplication, not the missing names — a second list will always
drift eventually. These tests fail if the two vocabularies ever diverge again, in
either direction: a registered family that the config refuses, or a family the
config accepts that the registry cannot build.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from perp_lab.search.config import SearchRunConfig
from perp_lab.search.registry import (
    CRT_INTRADAY_V1_FAMILIES,
    FAMILIES,
    R3_CLOSED_FAMILIES,
    S1_FAMILIES,
    S2_FAMILIES,
    available_families,
)


def _config(family: str) -> SearchRunConfig:
    return SearchRunConfig.model_validate({"family": family})


@pytest.mark.parametrize("family", FAMILIES)
def test_every_registered_family_is_accepted_by_the_config(family: str) -> None:
    """No family may be searchable by the registry and rejected by the config."""
    assert _config(family).family == family


def test_an_unregistered_family_is_refused() -> None:
    """Validation stays strict: unknown names fail before any data is loaded."""
    with pytest.raises(ValidationError) as excinfo:
        _config("not_a_real_family")
    # The message names the offending value and lists the real vocabulary, so the
    # failure is actionable without opening the source.
    rendered = str(excinfo.value)
    assert "not_a_real_family" in rendered
    assert "momentum" in rendered


def test_the_config_accepts_nothing_the_registry_cannot_build() -> None:
    """The same set, checked in the other direction.

    There is a third vocabulary besides `FAMILIES` and the config: the keys of
    the registry's builder table, exposed as `available_families()`. If the
    config accepted a name that table could not build, the run would fail after
    loading data instead of at validation. All three are pinned together here.
    """
    assert sorted(available_families()) == sorted(FAMILIES)


def test_the_round_groups_partition_the_registry() -> None:
    """Every registered family belongs to exactly one declared round.

    This is what keeps the multiple-testing denominator honest: a family that
    belongs to no round would be searchable but uncounted.
    """
    grouped = (*R3_CLOSED_FAMILIES, *S1_FAMILIES, *S2_FAMILIES, *CRT_INTRADAY_V1_FAMILIES)
    assert sorted(grouped) == sorted(FAMILIES)
    assert len(set(grouped)) == len(grouped), "a family appears in two rounds"


def test_the_crt_round_is_reachable_from_a_config() -> None:
    """The regression this file exists for: CRT configs must validate.

    Kept as its own test so a failure names the round that was unreachable
    rather than only the parametrised family that happened to fail first.
    """
    for family in CRT_INTRADAY_V1_FAMILIES:
        assert _config(family).family == family
