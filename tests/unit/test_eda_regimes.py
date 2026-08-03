"""Regime frequency, duration and transition tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from perp_lab.eda.regimes import (
    regime_duration_summary,
    regime_frequencies,
    regime_runs,
    regime_transition_matrix,
    tag_activity_regime,
)


def _regime_frame(labels: list[str]) -> pl.DataFrame:
    start = datetime(2021, 1, 1, tzinfo=UTC)
    times = [start + timedelta(hours=i) for i in range(len(labels))]
    return pl.DataFrame({"open_time": times, "regime": labels}).with_columns(
        pl.col("open_time").cast(pl.Datetime("ms", "UTC"))
    )


def test_regime_runs_and_durations():
    df = _regime_frame(["a", "a", "b", "b", "b", "a"])
    runs = regime_runs(df)
    assert runs["run_length"].to_list() == [2, 3, 1]
    dur = regime_duration_summary(df).sort("regime")
    a_row = dur.filter(pl.col("regime") == "a").row(0, named=True)
    assert a_row["n_runs"] == 2
    assert a_row["mean_bars"] == pytest.approx(1.5)


def test_regime_frequencies_sum_to_one():
    df = _regime_frame(["a", "a", "b", "b", "b", "a"])
    freq = regime_frequencies(df)
    assert freq["share"].sum() == pytest.approx(1.0)
    assert freq.filter(pl.col("regime") == "a")["count"].item() == 3


def test_transition_matrix_excludes_self_transitions():
    df = _regime_frame(["a", "a", "b", "b", "b", "a"])
    trans = regime_transition_matrix(df, normalize=True)
    # Only genuine changes: a->b once and b->a once.
    ab = trans.filter((pl.col("from") == "a") & (pl.col("to") == "b"))
    ba = trans.filter((pl.col("from") == "b") & (pl.col("to") == "a"))
    assert ab["count"].item() == 1
    assert ba["count"].item() == 1
    assert ab["probability"].item() == pytest.approx(1.0)


def test_tag_activity_regime_labels_are_valid():
    start = datetime(2021, 1, 1, tzinfo=UTC)
    n = 300
    times = [start + timedelta(minutes=5 * i) for i in range(n)]
    volume = [float(i % 50) for i in range(n)]
    df = pl.DataFrame({"open_time": times, "volume": volume}).with_columns(
        pl.col("open_time").cast(pl.Datetime("ms", "UTC"))
    )
    out = tag_activity_regime(df, window=10)
    assert set(out["activity_regime"].unique().to_list()) <= {"low", "normal", "high", "unknown"}
