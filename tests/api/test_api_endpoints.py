"""Integration tests for the read-only quantitative API v1."""

from __future__ import annotations

from fastapi.testclient import TestClient

BASE = "/api/v1"


def test_health(client: TestClient) -> None:
    r = client.get(f"{BASE}/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["api_version"] == "v1"
    assert body["runs_available"] >= 1
    assert r.headers.get("X-Request-ID")


def test_openapi_available(client: TestClient) -> None:
    r = client.get(f"{BASE}/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    assert f"{BASE}/runs" in spec["paths"]
    assert f"{BASE}/market/coverage" in spec["paths"]


def test_list_runs_and_filter(client: TestClient, run_id: str) -> None:
    r = client.get(f"{BASE}/runs?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["total"] >= 1
    assert any(item["run_id"] == run_id for item in body["items"])
    # kind of the fixture run is synthetic-smoke (synthetic config flag).
    kinds = {item["kind"] for item in body["items"]}
    assert "synthetic-smoke" in kinds
    filtered = client.get(f"{BASE}/runs?family=momentum").json()
    assert all(i["family"] == "momentum" for i in filtered["items"])


def test_list_runs_pagination(client: TestClient) -> None:
    r = client.get(f"{BASE}/runs?limit=1&offset=0")
    body = r.json()
    assert body["meta"]["limit"] == 1
    assert body["meta"]["returned"] <= 1


def test_run_detail(client: TestClient, run_id: str) -> None:
    r = client.get(f"{BASE}/runs/{run_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == run_id
    assert set(body["available_methods"]) == {"random_search", "genetic_algorithm"}
    assert any("EXPLORATORY" in w for w in body["warnings"])


def test_comparison(client: TestClient, run_id: str) -> None:
    r = client.get(f"{BASE}/runs/{run_id}/comparison")
    assert r.status_code == 200
    body = r.json()
    assert body["best_out_of_sample_method"] == "genetic_algorithm"
    assert body["fair_budget"]["ok"] is True
    methods = {mth["method"] for mth in body["methods"]}
    assert methods == {"random_search", "genetic_algorithm"}


def test_candidates_pagination(client: TestClient, run_id: str) -> None:
    r = client.get(f"{BASE}/runs/{run_id}/candidates?method=random_search&limit=1")
    assert r.status_code == 200
    body = r.json()
    assert body["method"] == "random_search"
    assert body["meta"]["returned"] <= 1
    if body["items"]:
        assert "params" in body["items"][0]


def test_folds_and_winners(client: TestClient, run_id: str) -> None:
    r = client.get(f"{BASE}/runs/{run_id}/folds")
    assert r.status_code == 200
    body = r.json()
    assert len(body["folds"]) == 1
    assert body["folds"][0]["purge_bars"] == 24
    assert "genetic_algorithm" in body["winners"]


def test_analytics(client: TestClient, run_id: str) -> None:
    r = client.get(f"{BASE}/runs/{run_id}/analytics")
    assert r.status_code == 200
    body = r.json()
    assert "genetic_algorithm" in body["convergence"]
    assert body["ga_diversity"]
    assert body["ga_lineage"]


def test_performance_and_equity_and_trades(client: TestClient, run_id: str) -> None:
    perf = client.get(f"{BASE}/runs/{run_id}/performance").json()
    assert perf["kind"] == "synthetic-smoke"
    assert perf["folds"], "at least one fold has test equity"
    eq = client.get(f"{BASE}/runs/{run_id}/equity?method=genetic_algorithm&fold=0").json()
    assert eq["points"] and "equity" in eq["points"][0]
    assert eq["summary"]["n_points_total"] >= len(eq["points"])
    assert eq["summary"]["final_equity"] == eq["points"][-1]["equity"]
    tr = client.get(f"{BASE}/runs/{run_id}/trades?method=genetic_algorithm&fold=0").json()
    assert tr["items"] and tr["items"][0]["trade_id"] == 1


def test_artifacts(client: TestClient, run_id: str) -> None:
    r = client.get(f"{BASE}/runs/{run_id}/artifacts")
    assert r.status_code == 200
    body = r.json()
    assert body["feature_manifest"]["n_features"] == 5
    assert "random_search" in body["failed_candidates"]
    assert "comparison_summary.json" in body["files"]


def test_market_coverage(client: TestClient) -> None:
    r = client.get(f"{BASE}/market/coverage")
    assert r.status_code == 200
    body = r.json()
    assert body["holdout_start"].startswith("2026-01-01")
    assert isinstance(body["datasets"], list)
