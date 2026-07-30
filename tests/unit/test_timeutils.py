from datetime import UTC, datetime

from perp_lab.utils.timeutils import (
    expected_bar_count,
    floor_to_timeframe,
    ms_to_utc,
    timeframe_to_timedelta,
    utc_to_ms,
)


def test_ms_roundtrip():
    dt = datetime(2021, 1, 1, 10, 5, tzinfo=UTC)
    assert ms_to_utc(utc_to_ms(dt)) == dt


def test_ms_to_utc_is_tz_aware():
    assert ms_to_utc(0).tzinfo is UTC


def test_floor_to_timeframe_15m():
    dt = datetime(2021, 1, 1, 10, 7, 30, tzinfo=UTC)
    assert floor_to_timeframe(dt, "15m") == datetime(2021, 1, 1, 10, 0, tzinfo=UTC)


def test_floor_to_timeframe_1h():
    dt = datetime(2021, 1, 1, 10, 59, tzinfo=UTC)
    assert floor_to_timeframe(dt, "1h") == datetime(2021, 1, 1, 10, 0, tzinfo=UTC)


def test_expected_bar_count():
    start = datetime(2021, 1, 1, tzinfo=UTC)
    end = datetime(2021, 1, 2, tzinfo=UTC)  # 24h
    assert expected_bar_count(start, end, "5m") == 288
    assert expected_bar_count(start, end, "1h") == 24


def test_expected_bar_count_empty_when_reversed():
    start = datetime(2021, 1, 2, tzinfo=UTC)
    end = datetime(2021, 1, 1, tzinfo=UTC)
    assert expected_bar_count(start, end, "5m") == 0


def test_timeframe_to_timedelta():
    assert timeframe_to_timedelta("1h").total_seconds() == 3600
