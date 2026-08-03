"""Tests for the momentum moving-average crossover baseline."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from perp_lab.strategies.momentum import MomentumCrossover


def _feats(fast: list[float | None], slow: list[float | None]) -> pl.DataFrame:
    n = len(fast)
    t0 = datetime(2021, 1, 1, tzinfo=UTC)
    return pl.DataFrame(
        {
            "open_time": [t0 + timedelta(hours=i) for i in range(n)],
            "sma_2": fast,
            "sma_3": slow,
        }
    )


def test_crossover_sides_follow_ma_relationship() -> None:
    feats = _feats([None, 10.0, 12.0, 8.0], [None, 11.0, 11.0, 9.0])
    sides = MomentumCrossover(2, 3).signals(feats)["side"].to_list()
    assert sides == [0, -1, 1, -1]  # null->0, below->-1, above->1, below->-1


def test_long_only_clamps_shorts_to_flat() -> None:
    feats = _feats([12.0, 8.0], [11.0, 9.0])
    sides = MomentumCrossover(2, 3, direction="long").signals(feats)["side"].to_list()
    assert sides == [1, 0]


def test_short_only_clamps_longs_to_flat() -> None:
    feats = _feats([12.0, 8.0], [11.0, 9.0])
    sides = MomentumCrossover(2, 3, direction="short").signals(feats)["side"].to_list()
    assert sides == [0, -1]


def test_fast_must_be_less_than_slow() -> None:
    with pytest.raises(ValueError, match="fast"):
        MomentumCrossover(96, 24)


def test_missing_feature_columns_raise() -> None:
    feats = pl.DataFrame({"open_time": [datetime(2021, 1, 1, tzinfo=UTC)], "sma_2": [1.0]})
    with pytest.raises(ValueError, match="Missing feature columns"):
        MomentumCrossover(2, 3).signals(feats)
