"""Drawdown curve and episode tests with manually verifiable values."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from perp_lab.eda.drawdown import (
    add_drawdown,
    drawdown_episodes,
    max_drawdown,
    underwater_fraction,
)


def _prices(closes: list[float]) -> pl.DataFrame:
    start = datetime(2021, 1, 1, tzinfo=UTC)
    times = [start + timedelta(hours=i) for i in range(len(closes))]
    return pl.DataFrame({"open_time": times, "close": closes}).with_columns(
        pl.col("open_time").cast(pl.Datetime("ms", "UTC"))
    )


def test_add_drawdown_matches_manual_values():
    df = add_drawdown(_prices([100.0, 110.0, 90.0, 120.0]))
    assert df["running_peak"].to_list() == [100.0, 110.0, 110.0, 120.0]
    dd = df["drawdown"].to_list()
    assert dd[0] == pytest.approx(0.0)
    assert dd[1] == pytest.approx(0.0)
    assert dd[2] == pytest.approx(90.0 / 110.0 - 1.0)
    assert dd[3] == pytest.approx(0.0)


def test_max_drawdown_and_underwater_fraction():
    df = _prices([100.0, 110.0, 90.0, 120.0])
    assert max_drawdown(df) == pytest.approx(90.0 / 110.0 - 1.0)
    # Only the third bar is below its running peak => 1 of 4 bars underwater.
    assert underwater_fraction(df) == pytest.approx(0.25)


def test_drawdown_episode_recovered():
    episodes = drawdown_episodes(_prices([100.0, 110.0, 90.0, 120.0]))
    assert episodes.height == 1
    row = episodes.row(0, named=True)
    assert row["recovered"] is True
    assert row["depth"] == pytest.approx(90.0 / 110.0 - 1.0)
    assert row["drawdown_bars"] == 1
    assert row["recovery_bars"] == 1


def test_drawdown_episode_unrecovered_at_end():
    episodes = drawdown_episodes(_prices([100.0, 120.0, 80.0]))
    assert episodes.height == 1
    row = episodes.row(0, named=True)
    assert row["recovered"] is False
    assert row["recovery_time"] is None
    assert row["depth"] == pytest.approx(80.0 / 120.0 - 1.0)


def test_drawdown_empty_frame_returns_typed_empty():
    empty = pl.DataFrame(schema={"open_time": pl.Datetime("ms", "UTC"), "close": pl.Float64})
    assert drawdown_episodes(empty).height == 0
    assert max_drawdown(empty) == 0.0
