"""The study-closure endpoints: the whole study rather than one run.

These endpoints are the only place the API reports a holdout number, so the
tests below pin the distinction the project depends on: the *published result*
of the single sanctioned reading may be served, while the holdout observations
themselves must remain unreachable.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

BASE = "/api/v1"


def _family(
    family: str,
    symbol: str,
    *,
    gate: str = "R3",
    total_return: float = -0.2,
    with_criteria: bool = True,
) -> dict[str, Any]:
    equity = [{"t": f"2024-01-0{i + 1}T00:00:00+00:00", "equity": 1.0 + i / 100} for i in range(4)]
    return {
        "key": f"{family}|{symbol}",
        "family": family,
        "gate": gate,
        "symbol": symbol,
        "thesis": "FIXTURE hypothesis, not a research claim.",
        "n_seeds": 2,
        "n_bars": 4.0,
        "total_return": total_return,
        "sharpe": -0.3,
        "max_drawdown": -0.25,
        "p_value": 0.42,
        "holm_adjusted_p": 1.0,
        "bh_adjusted_p": 0.99,
        "survives_correction": False,
        "verdict": "REJECTED",
        "gate_note": None,
        "criteria": (
            [
                {
                    "key": "positive_total_return",
                    "label": "C1 positive return",
                    "passed": 1,
                    "of": 2,
                    "required": 2,
                    "met": False,
                }
            ]
            if with_criteria
            else None
        ),
        "min_trades_veto": {"passed": 2, "of": 2, "triggered": False},
        "buy_and_hold_return": 0.5,
        "equity": equity,
        "seeds": [
            {
                "seed": 1,
                "total_return": 0.4,
                "sharpe": 0.9,
                "max_drawdown": -0.1,
                "n_bars": 4.0,
                "equity": equity,
            },
            {
                "seed": 2,
                "total_return": -0.6,
                "sharpe": -1.2,
                "max_drawdown": -0.7,
                "n_bars": 4.0,
                "equity": equity,
            },
        ],
        "monte_carlo": {
            "method": "stationary_bootstrap",
            "n_paths": 10,
            "expected_block_bars": 24.0,
            "seed": 1,
            "measures": "path_risk_not_significance",
            "checkpoint_index": [0, 3],
            "bands": {
                "p05": [0.9, 0.6],
                "p25": [0.95, 0.8],
                "p50": [1.0, 1.0],
                "p75": [1.05, 1.2],
                "p95": [1.1, 1.5],
            },
            "observed": [1.0, 1.03],
            "terminal": {
                "observed_total_return": total_return,
                "p05": -0.4,
                "p25": -0.2,
                "p50": 0.0,
                "p75": 0.2,
                "p95": 0.5,
                "probability_positive": 0.5,
            },
        },
    }


def _payload() -> dict[str, Any]:
    return {
        "report": "study_dashboard",
        "schema_version": 1,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "primary_symbol": "BTCUSDT",
        "secondary_symbol": "ETHUSDT",
        "primary_engine": "random_search",
        "timeframe": "1h",
        "study": {
            "n_families": 2,
            "n_units": 4,
            "n_configurations_evaluated": 1000,
            "alpha": 0.05,
            "best_family": "fixture_breakout",
            "holm": {"n_rejected": 0, "adjusted_p_values": {"fixture_breakout": 1.0}},
            "benjamini_hochberg": {
                "n_rejected": 0,
                "adjusted_p_values": {"fixture_breakout": 0.99},
            },
            "pbo": {"available": True, "pbo": 0.49, "n_splits": 70},
            "deflated_sharpe": {"family_selection": {"deflated_sharpe": 0.1}},
            "sensitivity": {"families": {"n_tests": 2, "any_survive": False}},
            "criteria_by_gate": {"R3": "FIXTURE criterion"},
            "conclusion": "FIXTURE conclusion: nothing survives.",
            "source_commit": "abc123",
        },
        "families": [
            _family("fixture_breakout", "BTCUSDT", total_return=0.05),
            _family("fixture_breakout", "ETHUSDT", total_return=-0.55),
            _family("fixture_flow", "BTCUSDT", gate="S2", total_return=-0.3, with_criteria=False),
        ],
        "regimes": {
            "cells": [{"family": "fixture_breakout", "dimension": "volatility", "regime": "high"}],
            "correction": {"holm_bonferroni": {"n_rejected": 0}},
            "candidate": None,
            "conclusion": "FIXTURE: no cell survives.",
        },
        "holdout": {
            "provenance": {
                "opened_at": "2026-01-01T00:00:00+00:00",
                "partition_evaluated": "holdout",
            },
            "result": {"combined": {"total_return": -0.12}},
            "buy_and_hold": {"total_return": -0.33},
        },
    }


@pytest.fixture
def study_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    from perp_lab.api.settings import get_settings

    runs_dir = tmp_path / "artifacts" / "runs"
    runs_dir.mkdir(parents=True)
    payload_path = tmp_path / "study_dashboard.json"
    payload_path.write_text(json.dumps(_payload()), encoding="utf-8")

    monkeypatch.setenv("PERP_LAB_RUNS_DIR", str(runs_dir))
    monkeypatch.setenv("PERP_LAB_STUDY_DASHBOARD", str(payload_path))
    get_settings.cache_clear()

    from perp_lab.api.main import create_app

    with TestClient(create_app()) as c:
        yield c
    get_settings.cache_clear()


@pytest.fixture
def studyless_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    from perp_lab.api.settings import get_settings

    runs_dir = tmp_path / "artifacts" / "runs"
    runs_dir.mkdir(parents=True)
    monkeypatch.setenv("PERP_LAB_RUNS_DIR", str(runs_dir))
    monkeypatch.setenv("PERP_LAB_STUDY_DASHBOARD", str(tmp_path / "absent.json"))
    get_settings.cache_clear()

    from perp_lab.api.main import create_app

    with TestClient(create_app()) as c:
        yield c
    get_settings.cache_clear()


def test_the_summary_lists_every_family_without_shipping_its_curves(
    study_client: TestClient,
) -> None:
    body = study_client.get(f"{BASE}/study/summary").json()

    assert len(body["families"]) == 3
    assert body["study"]["conclusion"] == "FIXTURE conclusion: nothing survives."
    # The summary is fetched on every page load; the curves are the bulk of the
    # payload and belong to the detail endpoint.
    for row in body["families"]:
        assert "equity" not in row
        assert "seeds" not in row
        assert "monte_carlo" not in row


def test_families_arrive_ordered_by_return_so_the_table_reads_top_down(
    study_client: TestClient,
) -> None:
    body = study_client.get(f"{BASE}/study/summary").json()
    returns = [row["total_return"] for row in body["families"]]
    assert returns == sorted(returns, reverse=True)


def test_no_family_is_reported_as_surviving_correction(study_client: TestClient) -> None:
    body = study_client.get(f"{BASE}/study/summary").json()
    assert all(row["survives_correction"] is False for row in body["families"])
    assert body["study"]["holm"]["n_rejected"] == 0


def test_the_detail_carries_the_seeds_and_the_resampling_fan(study_client: TestClient) -> None:
    r = study_client.get(f"{BASE}/study/families/fixture_breakout%7CBTCUSDT")
    assert r.status_code == 200
    body = r.json()

    assert len(body["seeds"]) == 2
    assert body["equity"][-1]["equity"] == pytest.approx(1.03)
    # The fan must announce what it measures, so the UI cannot present path
    # dispersion as evidence about significance.
    assert body["monte_carlo"]["measures"] == "path_risk_not_significance"


def test_a_family_without_a_gate_grid_reports_no_criteria_rather_than_empty_ones(
    study_client: TestClient,
) -> None:
    body = study_client.get(f"{BASE}/study/families/fixture_flow%7CBTCUSDT").json()
    # S1 and S2 families were never scored on the six R3 criteria. Null says
    # "not applicable"; an empty list would read as "scored, passed none".
    assert body["criteria"] is None


def test_an_unknown_family_is_a_404(study_client: TestClient) -> None:
    assert study_client.get(f"{BASE}/study/families/nope%7CBTCUSDT").status_code == 404


def test_the_regime_block_is_flagged_exploratory_in_the_payload(study_client: TestClient) -> None:
    body = study_client.get(f"{BASE}/study/regimes").json()
    # The warning travels with the data, not only with the page that renders it.
    assert body["exploratory"] is True
    assert body["candidate"] is None


def test_the_holdout_endpoint_serves_the_published_result(study_client: TestClient) -> None:
    body = study_client.get(f"{BASE}/study/holdout").json()
    assert body["opened"] is True
    assert body["result"]["combined"]["total_return"] == pytest.approx(-0.12)
    assert body["buy_and_hold"]["total_return"] == pytest.approx(-0.33)


def test_the_holdout_endpoint_serves_no_holdout_observations(study_client: TestClient) -> None:
    """Metrics about the partition are publishable; the bars are not."""
    body = study_client.get(f"{BASE}/study/holdout").json()
    assert set(body) == {"opened", "provenance", "result", "buy_and_hold"}
    assert "ledger" not in json.dumps(body)
    assert "open_time" not in json.dumps(body)


def test_a_study_that_was_never_built_says_so_instead_of_inventing_one(
    studyless_client: TestClient,
) -> None:
    r = studyless_client.get(f"{BASE}/study/summary")
    assert r.status_code == 503
    assert "build_study_dashboard" in r.json()["detail"]


def test_the_study_routes_are_published_in_the_schema(study_client: TestClient) -> None:
    spec = study_client.get(f"{BASE}/openapi.json").json()
    assert f"{BASE}/study/summary" in spec["paths"]
    assert f"{BASE}/study/holdout" in spec["paths"]
