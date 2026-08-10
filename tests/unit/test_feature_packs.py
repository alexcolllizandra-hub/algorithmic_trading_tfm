"""Tests for feature packs, catalogue introspection and proxy labelling.

Packs bound the search space; proxy labelling stops an approximation from being
reported as an observed quantity. Both are overfitting / integrity controls, so
they are tested rather than documented.
"""

from __future__ import annotations

import pytest

from perp_lab.features.spec import (
    KIND_REGISTRY,
    PACKS,
    catalogue,
    catalogue_counts,
    kinds_in_packs,
    known_kinds,
    proxy_kinds,
    resolve_spec,
    validate_packs,
)


def test_every_registered_kind_declares_a_known_pack() -> None:
    for kind, kd in KIND_REGISTRY.items():
        assert kd.pack in PACKS, f"{kind} declares unknown pack {kd.pack!r}"


def test_packs_are_cumulative() -> None:
    core = set(kinds_in_packs(["core"]))
    extended = set(kinds_in_packs(["extended"]))
    experimental = set(kinds_in_packs(["experimental"]))
    assert core < extended < experimental
    assert experimental == set(known_kinds())


def test_core_pack_excludes_speculative_kinds() -> None:
    core = set(kinds_in_packs(["core"]))
    assert "taker_buy_imbalance" not in core
    assert "funding_rate" not in core
    assert {"sma", "ema", "rvol", "atr", "momentum", "zscore"} <= core


def test_unknown_pack_is_rejected_not_silently_ignored() -> None:
    with pytest.raises(ValueError, match="Unknown feature pack"):
        kinds_in_packs(["core", "kitchen_sink"])
    with pytest.raises(ValueError, match="Unknown feature pack"):
        validate_packs(["nope"])


def test_catalogue_counts_report_kinds_not_columns() -> None:
    counts = catalogue_counts()
    assert counts["total_kinds"]["kinds"] == len(KIND_REGISTRY)
    assert sum(counts["by_pack"].values()) == len(KIND_REGISTRY)
    assert sum(counts["by_family"].values()) == len(KIND_REGISTRY)


def test_catalogue_rows_cover_every_kind_and_are_serialisable() -> None:
    rows = catalogue()
    assert len(rows) == len(KIND_REGISTRY)
    assert {r["kind"] for r in rows} == set(known_kinds())
    for row in rows:
        assert isinstance(row["family"], str) and row["family"]
        assert isinstance(row["leakage_risk"], str) and row["leakage_risk"]


def test_every_proxy_explains_what_it_actually_measures() -> None:
    """A proxy without a note could be mistaken for an observed quantity."""
    for kind in proxy_kinds():
        assert KIND_REGISTRY[kind].proxy_note, f"{kind} is a proxy but carries no note"


def test_basis_is_labelled_as_a_proxy_not_a_spot_basis() -> None:
    kd = KIND_REGISTRY["basis"]
    assert kd.is_proxy
    assert "spot" in kd.proxy_note.lower()


def test_order_flow_features_are_experimental_proxies() -> None:
    for kind in ("taker_buy_ratio", "taker_buy_imbalance"):
        kd = KIND_REGISTRY[kind]
        assert kd.pack == "experimental"
        assert kd.is_proxy


def test_resolved_specs_carry_the_pack_and_proxy_flags_into_artifacts() -> None:
    spec = resolve_spec("sma", window=20)
    assert spec.pack == "core" and spec.is_proxy is False
    payload = spec.to_dict()
    assert payload["pack"] == "core"

    proxy = resolve_spec("taker_buy_imbalance", lag=1)
    assert proxy.pack == "experimental" and proxy.is_proxy is True
    assert proxy.to_dict()["proxy_note"]


def test_funding_is_never_defaulted_to_zero() -> None:
    """Missing funding must stay null; a silent zero would understate holding cost."""
    kd = KIND_REGISTRY["funding_rate"]
    assert "null" in kd.null_policy.lower()
    assert "0" in kd.null_policy or "zero" in kd.null_policy.lower()
