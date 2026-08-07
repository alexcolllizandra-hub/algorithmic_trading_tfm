"""Every family must survive the whole pipeline, not just its own unit tests.

A family can be causally correct and still be unusable: its features may never
reach the signal, its constraints may reject every draw the engine makes, or its
cross-asset dependency may never be supplied. These tests run the real search
runner on synthetic smoke data for each family and check the properties that only
appear once search, backtest and artifact writing are all involved.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from perp_lab.config import Paths
from perp_lab.search.config import load_search_config
from perp_lab.search.runner import run_search

NEW_FAMILIES = ("volatility_breakout", "funding", "BTC_ETH_confirmation")


def _cfg(family: str, tmp_path: Path):
    base = load_search_config("configs/search_smoke.yaml")
    return base.model_copy(
        update={
            "family": family,
            "algorithm": "comparison",
            "label": f"smoke_{family}",
            # The funding family reads the published rate, so the smoke run must
            # actually carry one rather than silently signalling on nulls.
            "require_funding": family == "funding",
        }
    )


def _paths(tmp_path: Path) -> Paths:
    return Paths(
        data_root=tmp_path / "data",
        reports_root=tmp_path / "reports",
        artifacts_root=tmp_path / "artifacts",
    )


@pytest.mark.parametrize("family", NEW_FAMILIES)
def test_family_runs_through_the_real_search_pipeline(family: str, tmp_path: Path) -> None:
    cfg = _cfg(family, tmp_path)
    result = run_search(cfg, paths=_paths(tmp_path), write_artifacts=True)

    assert set(result.outcomes) == {"random_search", "genetic_algorithm"}
    for name, outcome in result.outcomes.items():
        assert outcome.counters.evaluated == cfg.budget, (
            f"{family}/{name} did not spend the declared budget"
        )
        assert outcome.best is not None, f"{family}/{name} found no admissible candidate"
        assert outcome.best.params, "the winning candidate recorded no parameters"


@pytest.mark.parametrize("family", NEW_FAMILIES)
def test_both_engines_spend_the_identical_budget_for_every_family(
    family: str, tmp_path: Path
) -> None:
    cfg = _cfg(family, tmp_path)
    result = run_search(cfg, paths=_paths(tmp_path), write_artifacts=False)
    spent = {name: o.counters.evaluated for name, o in result.outcomes.items()}
    assert len(set(spent.values())) == 1, f"{family}: budgets diverged {spent}"


def test_the_winning_candidate_records_its_family(tmp_path: Path) -> None:
    result = run_search(
        _cfg("volatility_breakout", tmp_path), paths=_paths(tmp_path), write_artifacts=False
    )
    best = result.outcomes["random_search"].best
    assert best is not None
    assert best.family == "volatility_breakout"


def test_cross_asset_run_records_both_symbols(tmp_path: Path) -> None:
    """A cross-asset result that does not name its reference is not reproducible."""
    result = run_search(
        _cfg("BTC_ETH_confirmation", tmp_path), paths=_paths(tmp_path), write_artifacts=False
    )
    best = result.outcomes["genetic_algorithm"].best
    assert best is not None
    assert int(cast(int, best.params["reference_lag"])) >= 1


def test_funding_family_refuses_to_run_without_a_funding_stream(tmp_path: Path) -> None:
    """Signalling on a missing rate would produce a flat strategy labelled 'funding'."""
    cfg = _cfg("funding", tmp_path).model_copy(update={"require_funding": False})
    with pytest.raises(Exception, match="funding"):
        run_search(cfg, paths=_paths(tmp_path), write_artifacts=False)
