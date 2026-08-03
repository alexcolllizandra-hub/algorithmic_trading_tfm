from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl

from perp_lab.eda.events import market_events_frame, market_stress_index
from perp_lab.eda.funding import basis_summary, mark_price_basis
from perp_lab.eda.regimes import regime_intervals


def _klines(closes: list[float]) -> pl.DataFrame:
    n = len(closes)
    t0 = datetime(2022, 1, 1, tzinfo=UTC)
    return pl.DataFrame(
        {
            "open_time": [t0 + timedelta(minutes=5 * i) for i in range(n)],
            "close": closes,
        }
    )


def test_mark_price_basis_matched_only_and_bps() -> None:
    trade = _klines([100.0, 101.0, 102.0])
    # Mark misses the middle timestamp -> must not be imputed.
    mark = _klines([100.0, 101.0, 102.0]).with_columns(pl.col("close") * 1.0)
    mark = mark.filter(pl.col("open_time") != mark["open_time"][1])
    mark = mark.with_columns((pl.col("close") - 1.0).alias("close"))  # mark below trade
    basis = mark_price_basis(trade, mark)
    assert basis.height == 2  # only matched timestamps
    # basis_bps = 1e4 * (100 - 99)/99 for the first matched bar
    assert abs(basis["basis_bps"][0] - 1e4 * (100.0 - 99.0) / 99.0) < 1e-6


def test_basis_summary_reports_coverage() -> None:
    trade = _klines([100.0, 200.0, 300.0, 400.0])
    mark = _klines([100.0, 200.0, 300.0, 400.0])
    summ = basis_summary(trade, mark, n_expected=trade.height)
    assert summ["n_matched"] == 4.0
    assert summ["coverage_pct"] == 100.0
    assert abs(summ["mean_bps"]) < 1e-6  # identical -> zero basis


def test_market_events_frame_clips_to_window() -> None:
    start = datetime(2022, 1, 1, tzinfo=UTC)
    end = datetime(2023, 1, 1, tzinfo=UTC)
    ev = market_events_frame(start, end)
    assert ev.height >= 1
    # No event may fall outside the requested window.
    assert ev.filter((pl.col("date") < start) | (pl.col("date") >= end)).height == 0
    assert set(ev.columns) == {"date", "label", "category"}


def test_market_stress_index_bounded_and_high_in_drawdown() -> None:
    # Rally then a deep crash: stress must be higher in the crash tail.
    closes = [100.0 + i for i in range(50)] + [149.0 - 2 * i for i in range(50)]
    df = _klines(closes).with_columns(pl.col("close").log().diff().alias("log_return"))
    stress = market_stress_index(df, vol_window=5)
    vals = stress["stress_index"].to_numpy()
    finite = vals[np.isfinite(vals)]
    assert finite.min() >= 0.0 and finite.max() <= 1.0
    assert np.nanmean(vals[-10:]) > np.nanmean(vals[10:20])


def test_regime_intervals_consolidates_runs() -> None:
    labels = ["low", "low", "high", "high", "high", "low"]
    df = _klines([1.0] * len(labels)).with_columns(pl.Series("vol_regime", labels))
    intervals = regime_intervals(df, "vol_regime")
    assert intervals.height == 3
    assert intervals["run_length"].to_list() == [2, 3, 1]
    assert intervals["vol_regime"].to_list() == ["low", "high", "low"]
