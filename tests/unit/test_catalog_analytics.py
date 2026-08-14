"""Tests for the DuckDB layer over registered Parquet.

The fixtures are deliberately tiny and the expected numbers are written out by
hand, so a failure points at the SQL rather than at a reimplementation of the
same aggregation in the test.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from perp_lab.catalog.analytics import (
    AnalyticsError,
    aggregate_metrics_across_runs,
    materialise,
    parquet_columns,
    per_fold_rollup,
    resample_equity,
    status_breakdown,
)
from perp_lab.catalog.storage import LocalObjectStore


def _measurements(path: Path) -> Path:
    """Two families on BTCUSDT: momentum measured, breakout partly never run."""
    frame = pl.DataFrame(
        {
            "family": ["momentum"] * 4 + ["breakout"] * 2,
            "symbol": ["BTCUSDT"] * 6,
            "engine": ["random_search"] * 6,
            "seed": [1, 1, 2, 2, 1, 2],
            "fold_index": [0, 1, 0, 1, 0, 0],
            "status": [
                "EXECUTED",
                "EXECUTED",
                "EXECUTED",
                "EXECUTED",
                "EXECUTED",
                "NOT_EXECUTED",
            ],
            "total_return": [0.10, 0.20, 0.30, 0.40, -0.10, None],
            "sharpe": [0.5, 1.5, 1.0, 2.0, -0.5, None],
            "max_drawdown": [-0.05, -0.10, -0.20, -0.15, -0.30, None],
            "n_trades": [10, 20, 30, 40, 50, None],
        }
    )
    frame.write_parquet(path)
    return path


def _equity(path: Path) -> Path:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    hours = 72
    pl.DataFrame(
        {
            "ts": [start + timedelta(hours=i) for i in range(hours)],
            "equity": [1.0 + 0.001 * i for i in range(hours)],
        }
    ).write_parquet(path)
    return path


def test_aggregating_across_runs_averages_only_measured_rows(tmp_path: Path) -> None:
    source = _measurements(tmp_path / "measurements.parquet")

    result = aggregate_metrics_across_runs(source).sort("family")
    momentum = result.filter(pl.col("family") == "momentum").to_dicts()[0]
    breakout = result.filter(pl.col("family") == "breakout").to_dicts()[0]

    assert momentum["n_results"] == 4
    assert momentum["n_seeds"] == 2
    assert momentum["mean_total_return"] == pytest.approx(0.25)
    assert momentum["median_sharpe"] == pytest.approx(1.25)
    assert momentum["worst_max_drawdown"] == pytest.approx(-0.20)
    assert momentum["total_trades"] == 100
    # The unmeasured breakout seed is excluded, not counted as a zero return.
    assert breakout["n_results"] == 1
    assert breakout["mean_total_return"] == pytest.approx(-0.10)


def test_the_status_breakdown_counts_every_row_including_unmeasured_ones(
    tmp_path: Path,
) -> None:
    source = _measurements(tmp_path / "measurements.parquet")

    counts = {row["status"]: row["n_rows"] for row in status_breakdown(source).to_dicts()}

    assert counts == {"EXECUTED": 5, "NOT_EXECUTED": 1}


def test_the_per_fold_rollup_separates_folds_and_counts_seeds(tmp_path: Path) -> None:
    source = _measurements(tmp_path / "measurements.parquet")

    rollup = per_fold_rollup(source).filter(pl.col("family") == "momentum").sort("fold_index")

    assert rollup["fold_index"].to_list() == [0, 1]
    assert rollup["mean_total_return"].to_list() == pytest.approx([0.20, 0.30])
    assert rollup["n_seeds"].to_list() == [2, 2]


def test_aggregating_over_several_files_pools_them(tmp_path: Path) -> None:
    first = _measurements(tmp_path / "one.parquet")
    second = _measurements(tmp_path / "two.parquet")

    pooled = aggregate_metrics_across_runs([first, second])
    momentum = pooled.filter(pl.col("family") == "momentum").to_dicts()[0]

    assert momentum["n_results"] == 8
    assert momentum["mean_total_return"] == pytest.approx(0.25)


def test_resampling_an_equity_curve_keeps_the_closing_value_of_each_day(
    tmp_path: Path,
) -> None:
    source = _equity(tmp_path / "equity.parquet")

    daily = resample_equity(source, unit="day")

    assert daily.height == 3
    assert daily["n_bars"].to_list() == [24, 24, 24]
    assert daily["value_close"].to_list() == pytest.approx([1.023, 1.047, 1.071])
    assert daily["value_min"][0] == pytest.approx(1.0)


def test_resampling_rejects_a_column_that_is_not_in_the_file(tmp_path: Path) -> None:
    source = _equity(tmp_path / "equity.parquet")

    with pytest.raises(AnalyticsError):
        resample_equity(source, value_column="drawdown")


def test_resampling_rejects_an_unsupported_truncation_unit(tmp_path: Path) -> None:
    source = _equity(tmp_path / "equity.parquet")

    with pytest.raises(AnalyticsError):
        resample_equity(source, unit="fortnight")


def test_querying_a_missing_file_says_so(tmp_path: Path) -> None:
    with pytest.raises(AnalyticsError):
        aggregate_metrics_across_runs(tmp_path / "absent.parquet")


def test_parquet_columns_reads_the_schema_without_loading_rows(tmp_path: Path) -> None:
    source = _equity(tmp_path / "equity.parquet")

    assert parquet_columns(source) == ["ts", "equity"]


def test_materialising_a_local_object_returns_its_path_without_copying(
    tmp_path: Path,
) -> None:
    store = LocalObjectStore(tmp_path / "objects")
    store.put_file("runs/r1/equity.parquet", _equity(tmp_path / "equity.parquet"))

    resolved = materialise(store, "runs/r1/equity.parquet", tmp_path / "cache")

    assert resolved == store.local_path("runs/r1/equity.parquet")
    assert not (tmp_path / "cache").exists()
    assert resample_equity(resolved, unit="day").height == 3


def test_materialising_a_key_the_store_does_not_hold_raises(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path / "objects")

    with pytest.raises(AnalyticsError):
        materialise(store, "runs/r1/absent.parquet", tmp_path / "cache")
