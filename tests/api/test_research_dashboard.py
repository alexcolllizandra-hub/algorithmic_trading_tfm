"""Tests for performance metric consistency across API endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ETH_PILOT = Path("artifacts/runs/search_momentum_20260804T190438Z_1a68e0")


@pytest.fixture
def real_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Client wired to the repository's real artifact tree (development only)."""
    from perp_lab.api.main import create_app
    from perp_lab.api.settings import get_settings

    monkeypatch.setenv("PERP_LAB_ARTIFACT_ROOT", "artifacts")
    monkeypatch.setenv("PERP_LAB_RUNS_DIR", "artifacts/runs")
    monkeypatch.setenv("PERP_LAB_MANIFESTS_DIR", "data/manifests")
    monkeypatch.setenv("PERP_LAB_DATA_CONTRACT", "configs/data_contract.yaml")
    monkeypatch.setenv("PERP_LAB_EDA_FIGURES_DIR", "reports/figures/eda")
    monkeypatch.setenv("PERP_LAB_EDA_METADATA_DIR", "reports/metadata/eda")
    get_settings.cache_clear()
    with TestClient(create_app()) as c:
        yield c
    get_settings.cache_clear()


@pytest.mark.skipif(not ETH_PILOT.is_dir(), reason="ETH pilot artifacts not present locally")
def test_performance_fold_matches_equity_summary(real_client: TestClient) -> None:
    """Fold table metrics must match equity.summary from the same method/fold."""
    run_id = ETH_PILOT.name
    perf = real_client.get(f"/api/v1/runs/{run_id}/performance").json()
    assert perf["folds"], "expected fold performance rows"
    for fold_row in perf["folds"]:
        method = fold_row["method"]
        fold = fold_row["fold"]
        eq = real_client.get(
            f"/api/v1/runs/{run_id}/equity",
            params={"method": method, "fold": fold, "limit": 500, "offset": 0},
        ).json()
        summary = eq["summary"]
        assert summary["n_points_total"] == fold_row["n_points"]
        assert summary["final_equity"] == pytest.approx(fold_row["final_equity"], rel=1e-9)
        assert summary["max_drawdown"] == pytest.approx(fold_row["max_drawdown"], rel=1e-9)
        if eq["meta"]["returned"] < summary["n_points_total"] and eq["points"]:
            last_window = eq["points"][-1]["equity"]
            assert (
                last_window != summary["final_equity"]
                or summary["n_points_total"] <= eq["meta"]["returned"]
            )


@pytest.mark.skipif(not ETH_PILOT.is_dir(), reason="ETH pilot artifacts not present locally")
def test_rs_fold_zero_winner_matches_full_unpaginated_equity(real_client: TestClient) -> None:
    """Pin the fold → selected candidate → full equity artifact chain.

    The point window is deliberately shorter than the series. Dashboard cards
    must use ``summary``, never the last point displayed after pagination.
    """
    run_id = ETH_PILOT.name
    performance = real_client.get(f"/api/v1/runs/{run_id}/performance").json()
    fold = next(
        row for row in performance["folds"] if row["method"] == "random_search" and row["fold"] == 0
    )
    equity = real_client.get(
        f"/api/v1/runs/{run_id}/equity",
        params={"method": "random_search", "fold": 0, "limit": 500, "offset": 0},
    ).json()
    summary = equity["summary"]

    assert fold["candidate_id"] == "momentum-f1fa297f04234be9"
    assert summary["candidate_id"] == fold["candidate_id"]
    assert summary["final_equity"] == pytest.approx(0.9040595814842268, rel=1e-12)
    assert fold["final_equity"] == pytest.approx(summary["final_equity"], rel=1e-12)
    assert summary["n_points_total"] == fold["n_points"] == 2159
    assert summary["period_start"].startswith("2022-03-31")
    assert summary["period_end"].startswith("2022-06-28")
    assert equity["meta"]["returned"] == 500
    assert equity["meta"]["total"] == summary["n_points_total"]
    assert equity["points"][-1]["equity"] != summary["final_equity"]


def test_eda_figure_path_traversal_rejected(client: TestClient) -> None:
    r = client.get("/api/v1/eda/figures/../secrets")
    assert r.status_code in (400, 404, 422)


@pytest.mark.parametrize(
    "path",
    (
        "/api/v1/research/summary?run_id=..",
        "/api/v1/research/timeline?run_id=..",
        "/api/v1/methodology/features?run_id=..",
        "/api/v1/methodology/strategies?run_id=..",
    ),
)
def test_research_query_run_id_path_traversal_rejected(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 400


def test_research_summary_schema(client: TestClient) -> None:
    r = client.get("/api/v1/research/summary")
    assert r.status_code == 200
    body = r.json()
    assert "holdout_start" in body
    assert "runs_total" in body


@pytest.mark.skipif(not ETH_PILOT.is_dir(), reason="ETH pilot artifacts not present locally")
def test_timeline_excludes_holdout_observations(real_client: TestClient) -> None:
    run_id = ETH_PILOT.name
    r = real_client.get("/api/v1/research/timeline", params={"run_id": run_id})
    assert r.status_code == 200
    body = r.json()
    holdout = body["holdout_start"]
    if body["development_end"]:
        assert body["development_end"] < holdout
    for fold in body["folds"]:
        if fold["test_end"]:
            assert fold["test_end"] < holdout


@pytest.mark.skipif(not ETH_PILOT.is_dir(), reason="ETH pilot artifacts not present locally")
def test_run_validity_flags_unequal_evaluations(real_client: TestClient) -> None:
    run_id = ETH_PILOT.name
    r = real_client.get(f"/api/v1/runs/{run_id}/validity")
    assert r.status_code == 200
    body = r.json()
    assert body["random_search_evaluated"] == 12
    assert body["genetic_algorithm_evaluated"] == 10
    assert body["equal_effective_evaluations"] is False
