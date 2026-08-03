"""Seasonality grouping tests (counts, means, standard errors)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from perp_lab.eda.seasonality import seasonality_kruskal, seasonality_stats


def test_seasonality_by_hour_counts_and_mean():
    # Two full days of hourly bars: each UTC hour appears exactly twice.
    start = datetime(2021, 1, 1, tzinfo=UTC)
    times = [start + timedelta(hours=i) for i in range(48)]
    values = [float(t.hour) for t in times]  # value equals the hour
    df = pl.DataFrame({"open_time": times, "v": values}).with_columns(
        pl.col("open_time").cast(pl.Datetime("ms", "UTC"))
    )
    out = seasonality_stats(df, "v", by="hour").sort("hour")
    assert out.height == 24
    assert out["count"].to_list() == [2] * 24
    # Mean value for hour h is h (both days identical).
    assert out.filter(pl.col("hour") == 5)["mean"].item() == pytest.approx(5.0)
    # Zero within-group variance => zero standard error.
    assert out["stderr"].max() == pytest.approx(0.0)


def test_seasonality_weekday_partitions():
    start = datetime(2021, 1, 4, tzinfo=UTC)  # a Monday
    times = [start + timedelta(days=i) for i in range(7)]
    df = pl.DataFrame({"open_time": times, "v": list(range(7))}).with_columns(
        pl.col("open_time").cast(pl.Datetime("ms", "UTC"))
    )
    out = seasonality_stats(df, "v", by="weekday")
    assert set(out["weekday"].to_list()) == set(range(1, 8))


def test_seasonality_rejects_unknown_dimension():
    df = pl.DataFrame({"open_time": [datetime(2021, 1, 1, tzinfo=UTC)], "v": [1.0]}).with_columns(
        pl.col("open_time").cast(pl.Datetime("ms", "UTC"))
    )
    with pytest.raises(ValueError, match="seasonality dimension"):
        seasonality_stats(df, "v", by="month")


def test_kruskal_detects_hour_effect():
    # Hour 0 has large values, all other hours small -> distributions differ.
    start = datetime(2021, 1, 1, tzinfo=UTC)
    times = [start + timedelta(hours=i) for i in range(240)]
    values = [10.0 if t.hour == 0 else 0.1 for t in times]
    df = pl.DataFrame({"open_time": times, "v": values}).with_columns(
        pl.col("open_time").cast(pl.Datetime("ms", "UTC"))
    )
    out = seasonality_kruskal(df, "v", by="hour")
    assert out["n_groups"] == 24.0
    assert out["pvalue"] < 0.01


def test_kruskal_rejects_unknown_dimension():
    df = pl.DataFrame({"open_time": [datetime(2021, 1, 1, tzinfo=UTC)], "v": [1.0]}).with_columns(
        pl.col("open_time").cast(pl.Datetime("ms", "UTC"))
    )
    with pytest.raises(ValueError, match="seasonality dimension"):
        seasonality_kruskal(df, "v", by="month")
