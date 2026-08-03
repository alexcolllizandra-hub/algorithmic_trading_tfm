"""Coverage and per-dataset quality helpers."""

from __future__ import annotations

from datetime import datetime

import polars as pl

from perp_lab.eda.coverage import dataset_quality_row, longest_gap, monthly_coverage


def _klines(open_times: list[datetime], close: float = 100.0) -> pl.DataFrame:
    n = len(open_times)
    return pl.DataFrame(
        {
            "open_time": pl.Series(open_times, dtype=pl.Datetime("ms", "UTC")),
            "open": [close] * n,
            "high": [close + 1] * n,
            "low": [close - 1] * n,
            "close": [close] * n,
            "volume": [10.0] * n,
        }
    )


def test_full_day_has_complete_coverage():
    times = list(
        pl.datetime_range(
            datetime(2021, 3, 1),
            datetime(2021, 3, 2),
            interval="5m",
            closed="left",
            time_zone="UTC",
            eager=True,
        )
    )
    df = _klines(times)
    row = dataset_quality_row(df, symbol="BTCUSDT", timeframe="5m")
    assert row["observed"] == 288
    assert row["expected"] == 288
    assert row["coverage_pct"] == 100.0
    assert row["missing"] == 0
    assert row["duplicates"] == 0


def test_gap_is_detected_and_measured():
    times = list(
        pl.datetime_range(
            datetime(2021, 3, 1),
            datetime(2021, 3, 1, 2),
            interval="5m",
            closed="left",
            time_zone="UTC",
            eager=True,
        )
    )
    # Drop 3 consecutive bars (indices 5,6,7) to create a gap of 3 missing bars.
    kept = times[:5] + times[8:]
    df = _klines(kept)
    gap = longest_gap(df, "5m")
    assert gap["n_gaps"] == 1.0
    assert gap["max_gap_bars"] == 3.0
    assert gap["max_gap_hours"] == 0.25  # 3 * 5min
    row = dataset_quality_row(df, symbol="BTCUSDT", timeframe="5m")
    assert row["missing"] == 3
    assert row["longest_gap_bars"] == 3


def test_monthly_coverage_ratio():
    times = list(
        pl.datetime_range(
            datetime(2021, 3, 1),
            datetime(2021, 3, 2),
            interval="5m",
            closed="left",
            time_zone="UTC",
            eager=True,
        )
    )
    kept = times[:100] + times[110:]  # drop 10 -> 278 observed of 288 expected
    cov = monthly_coverage(_klines(kept), "5m")
    assert cov.height == 1
    r = cov.row(0, named=True)
    assert r["observed"] == 278
    assert r["expected"] == 288
