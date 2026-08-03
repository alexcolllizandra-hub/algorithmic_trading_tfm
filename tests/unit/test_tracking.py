"""Tests for the reproducible run/artifact tracking contract."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from perp_lab.tracking.run import (
    RunTracker,
    environment_info,
    generate_run_id,
    git_state,
)


def test_run_id_is_unique_and_sortable() -> None:
    now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    a = generate_run_id("dev", now=now)
    b = generate_run_id("dev", now=now)
    assert a.startswith("dev_20260102T030405Z_")
    assert a != b  # random suffix differs


def test_environment_info_has_core_keys() -> None:
    info = environment_info()
    assert "python_version" in info
    assert "packages" in info
    assert "polars" in info["packages"]


def test_git_state_returns_expected_shape() -> None:
    state = git_state(".")
    assert set(state) == {"commit", "branch", "dirty"}


def test_run_tracker_creates_dirs_and_writes(tmp_path: Path) -> None:
    tracker = RunTracker.create(tmp_path / "runs", run_id="r1")
    assert tracker.logs_dir.is_dir()
    assert tracker.figures_dir.is_dir()

    tracker.write_yaml("resolved_config.yaml", {"a": 1, "b": [1, 2]})
    tracker.write_json("metrics.json", {"run_id": "r1", "sharpe": 0.5})
    tracker.write_parquet("equity.parquet", pl.DataFrame({"equity": [1.0, 1.1]}))

    assert (tracker.run_dir / "resolved_config.yaml").exists()
    assert (tracker.run_dir / "metrics.json").exists()
    reloaded = pl.read_parquet(tracker.run_dir / "equity.parquet")
    assert reloaded.height == 2
