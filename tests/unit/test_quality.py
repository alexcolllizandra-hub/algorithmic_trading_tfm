from datetime import UTC, datetime

import polars as pl

from perp_lab.validation.quality import (
    check_ohlc_consistency,
    coverage_summary,
    find_duplicates,
    find_gaps,
    flag_extreme_returns,
    is_monotonic_increasing,
    quality_report,
)


def test_find_gaps_detects_missing_bars(klines_5m):
    # Drop three consecutive bars to create a gap of 3 missing candles.
    trimmed = pl.concat([klines_5m.head(10), klines_5m.slice(13, None)])
    gaps = find_gaps(trimmed, "5m")
    assert gaps.height == 1
    assert gaps["missing"].item() == 3


def test_no_gaps_on_contiguous(klines_5m):
    assert find_gaps(klines_5m, "5m").height == 0


def test_find_duplicates(klines_5m):
    dup = pl.concat([klines_5m, klines_5m.head(2)])
    assert find_duplicates(dup).height == 2


def test_monotonic(klines_5m):
    assert is_monotonic_increasing(klines_5m)
    shuffled = klines_5m.reverse()
    assert not is_monotonic_increasing(shuffled)


def test_ohlc_consistency_flags_bad_row(klines_5m):
    bad = klines_5m.with_columns(
        pl.when(pl.int_range(pl.len()) == 5)
        .then(pl.col("low") - 1.0)  # high now below low
        .otherwise(pl.col("high"))
        .alias("high")
    )
    assert check_ohlc_consistency(bad).height >= 1


def test_flag_extreme_returns_never_drops(klines_5m):
    flagged = flag_extreme_returns(klines_5m, sigma=10.0, window=20)
    assert flagged.height == klines_5m.height
    assert "extreme" in flagged.columns


def test_coverage_summary(klines_5m):
    start = datetime(2021, 1, 1, tzinfo=UTC)
    end = datetime(2021, 1, 2, tzinfo=UTC)
    cov = coverage_summary(klines_5m, "5m", start, end)
    assert cov["expected_bars"] == 288
    assert cov["present_bars"] == 288
    assert cov["coverage_ratio"] == 1.0


def test_quality_report_smoke(klines_5m):
    start = datetime(2021, 1, 1, tzinfo=UTC)
    end = datetime(2021, 1, 2, tzinfo=UTC)
    report = quality_report(klines_5m, symbol="BTCUSDT", timeframe="5m", start=start, end=end)
    assert report.row_count == 288
    assert report.duplicate_timestamps == 0
    assert report.ohlc_violations == 0
    assert report.is_monotonic
