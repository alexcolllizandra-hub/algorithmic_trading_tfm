"""Ranked extreme-event detection with leak-free context."""

from __future__ import annotations

from datetime import datetime, timedelta

import polars as pl

from perp_lab.eda.extremes import coexceedance_rate, rank_extreme_events


def _returns(vals: list[float]) -> pl.DataFrame:
    n = len(vals)
    times = [datetime(2021, 1, 1) + timedelta(hours=h) for h in range(n)]
    close = [100.0]
    for r in vals[1:]:
        close.append(close[-1] * (1 + r))
    return pl.DataFrame(
        {
            "open_time": pl.Series(times, dtype=pl.Datetime("ms", "UTC")),
            "close": close,
            "volume": [10.0] * n,
            "log_return": vals,
        }
    )


def test_ranks_by_absolute_return_and_is_leak_free():
    vals = [0.0] + [0.001] * 28 + [-0.20]  # last bar is the extreme
    left = _returns(vals)
    right = _returns([0.0] + [0.001] * 28 + [-0.15])  # other asset also extreme at end
    events = rank_extreme_events(
        left, symbol="BTC", other=right, other_symbol="ETH", k=3, vol_window=5
    )
    top = events.row(0, named=True)
    assert top["symbol"] == "BTC"
    assert abs(top["log_return"]) >= abs(events["log_return"].to_list()[1])
    # Pre-event volatility uses only past bars -> defined for the last bar.
    assert top["pre_vol"] is not None
    assert top["other_simultaneous_extreme"] is True


def test_coexceedance_rate():
    events = pl.DataFrame({"other_simultaneous_extreme": [True, False, True, True]})
    assert coexceedance_rate(events) == 0.75
