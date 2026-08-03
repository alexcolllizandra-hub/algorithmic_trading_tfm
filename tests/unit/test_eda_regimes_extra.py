"""Full transition matrix (with self-transitions) and duration table."""

from __future__ import annotations

from datetime import datetime, timedelta

import polars as pl
import pytest

from perp_lab.eda.regimes import regime_duration_table, regime_transition_matrix_full


def _regimes(labels: list[str]) -> pl.DataFrame:
    base = datetime(2021, 1, 1)
    times = pl.Series(
        [base + timedelta(hours=i) for i in range(len(labels))], dtype=pl.Datetime("ms", "UTC")
    )
    return pl.DataFrame({"open_time": times, "regime": labels})


def test_full_transition_matrix_includes_self_transitions():
    # low,low,high,high,high,low -> transitions: low->low, low->high, high->high(2), high->low.
    tm = regime_transition_matrix_full(_regimes(["low", "low", "high", "high", "high", "low"]))
    self_low = tm.filter((pl.col("from") == "low") & (pl.col("to") == "low"))
    assert self_low.height == 1
    # Row probabilities sum to 1 per 'from'.
    sums = tm.group_by("from").agg(pl.col("probability").sum().alias("s"))
    for r in sums.iter_rows(named=True):
        assert r["s"] == pytest.approx(1.0)


def test_duration_table_occupancy_sums_to_one():
    dt = regime_duration_table(_regimes(["low", "low", "high", "high", "high", "low"]))
    assert dt.select(pl.col("occupancy").sum()).item() == pytest.approx(1.0)
    high = dt.filter(pl.col("regime") == "high").row(0, named=True)
    assert high["n_episodes"] == 1
    assert high["max_bars"] == 3
