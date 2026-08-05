"""Path-traversal and error-handling tests for the API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from perp_lab.api.security import (
    InvalidRunId,
    RunNotFound,
    resolve_run_dir,
    validate_run_id,
)

BASE = "/api/v1"


@pytest.mark.parametrize(
    "bad",
    ["..", "%2e%2e", "....", ".hidden", "foo bar", "a/b", "a\\b", "", "-x", "." * 3],
)
def test_validate_run_id_rejects_bad(bad: str) -> None:
    with pytest.raises(InvalidRunId):
        validate_run_id(bad)


def test_validate_run_id_accepts_good() -> None:
    ok = "search_momentum_20260101T000000Z_abc123"
    assert validate_run_id(ok) == ok


def test_resolve_run_dir_blocks_escape(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    runs.mkdir()
    (tmp_path / "secret").mkdir()
    with pytest.raises(InvalidRunId):
        resolve_run_dir("..", runs)
    with pytest.raises(RunNotFound):
        resolve_run_dir("missing", runs)


def test_resolve_run_dir_ok(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    (runs / "run1").mkdir(parents=True)
    resolved = resolve_run_dir("run1", runs)
    assert resolved.name == "run1"
    assert resolved.is_relative_to(runs.resolve())


@pytest.mark.parametrize("bad", ["%2e%2e", "....", ".hidden", "-x"])
def test_api_rejects_traversal(client: TestClient, bad: str) -> None:
    r = client.get(f"{BASE}/runs/{bad}")
    assert r.status_code == 400


def test_api_missing_run_404(client: TestClient) -> None:
    r = client.get(f"{BASE}/runs/definitely_missing_run_xyz")
    assert r.status_code == 404


def test_api_missing_run_subresource_404(client: TestClient) -> None:
    for sub in ("comparison", "candidates", "folds", "performance", "artifacts"):
        r = client.get(f"{BASE}/runs/definitely_missing_run_xyz/{sub}")
        assert r.status_code == 404
