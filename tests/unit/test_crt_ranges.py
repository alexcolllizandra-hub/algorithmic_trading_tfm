"""Reference levels must not be readable before the period that produced them ends.

This is the single most dangerous file in the CRT module. "Yesterday's high" is
one number for a whole day, so broadcasting it across the day's bars is the
natural implementation and it is also look-ahead: bars before the high was set
would know it. The tests below are built on data where the answer is known by
construction, so a leak shows up as a wrong number rather than as suspiciously
good performance later.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from perp_lab.crt.ranges import (
    RangeConfig,
    RangeError,
    active_ranges_at,
    average_true_range,
    build_ranges,
    candle_ranges,
    daily_ranges,
    latest_range,
    n_day_ranges,
    opening_ranges,
    rolling_ranges,
    session_ranges,
)
from perp_lab.crt.sessions import LONDON


def _bars(
    n: int,
    *,
    start: datetime | None = None,
    step: timedelta = timedelta(hours=1),
    highs: list[float] | None = None,
    lows: list[float] | None = None,
) -> pl.DataFrame:
    origin = start or datetime(2024, 1, 1, tzinfo=UTC)
    times = [origin + step * i for i in range(n)]
    base = [100.0 + i for i in range(n)]
    return pl.DataFrame(
        {
            "open_time": times,
            "open": base,
            "high": highs if highs is not None else [b + 1.0 for b in base],
            "low": lows if lows is not None else [b - 1.0 for b in base],
            "close": base,
        }
    ).with_columns(pl.col("open_time").dt.cast_time_unit("ms").dt.replace_time_zone("UTC"))


class TestPreviousDayLevels:
    def test_the_previous_day_high_is_the_previous_day_high(self) -> None:
        """Two days with known extremes; day two must see day one's numbers."""
        highs = [110.0] * 24 + [220.0] * 24
        lows = [90.0] * 24 + [180.0] * 24
        bars = _bars(48, highs=highs, lows=lows)

        ranges = daily_ranges(bars)

        assert ranges.height == 1
        row = ranges.to_dicts()[0]
        assert row["high"] == 110.0
        assert row["low"] == 90.0
        assert row["mid"] == 100.0

    def test_the_level_becomes_available_only_after_the_day_it_describes_closes(self) -> None:
        bars = _bars(48)
        row = daily_ranges(bars).to_dicts()[0]

        # Day one runs [00:00, 24:00) on 1 January; its levels may first be read
        # at midnight on the 2nd, which is the first bar of day two.
        assert row["available_from"] == datetime(2024, 1, 2, tzinfo=UTC)
        assert row["period_end"] == datetime(2024, 1, 2, tzinfo=UTC)

    def test_no_bar_of_a_day_can_see_that_days_own_extremes(self) -> None:
        """The leak this module exists to prevent, stated as an assertion."""
        highs = [110.0] * 24 + [999.0] * 24
        bars = _bars(48, highs=highs)
        ranges = daily_ranges(bars)

        for hour in range(24, 48):
            moment = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=hour)
            visible = active_ranges_at(ranges, moment)
            assert 999.0 not in visible["high"].to_list()

    def test_a_single_day_of_data_yields_no_previous_day(self) -> None:
        assert daily_ranges(_bars(24)).height == 0

    def test_the_local_day_boundary_follows_the_configured_zone(self) -> None:
        bars = _bars(72)
        utc_days = daily_ranges(bars, timezone="UTC")
        tokyo_days = daily_ranges(bars, timezone="Asia/Tokyo")
        assert utc_days["available_from"].to_list() != tokyo_days["available_from"].to_list()


class TestHigherTimeframeCandles:
    def test_only_closed_candles_produce_a_range(self) -> None:
        """A 4h candle that is still forming has no final high, so it has no range."""
        bars = _bars(10)  # two complete 4h candles plus a partial third
        ranges = candle_ranges(bars, "4h")

        last_period_end = ranges["period_end"].max()
        assert isinstance(last_period_end, datetime)
        assert last_period_end <= datetime(2024, 1, 1, 8, tzinfo=UTC)

    def test_the_range_of_a_candle_is_available_when_that_candle_closes(self) -> None:
        bars = _bars(12)
        row = candle_ranges(bars, "4h").to_dicts()[0]
        assert row["period_start"] == datetime(2024, 1, 1, 0, tzinfo=UTC)
        assert row["available_from"] == datetime(2024, 1, 1, 4, tzinfo=UTC)


class TestSessionRanges:
    def test_a_session_range_is_not_readable_while_the_session_is_running(self) -> None:
        bars = _bars(96, start=datetime(2024, 6, 3, tzinfo=UTC))
        ranges = session_ranges(bars, LONDON)
        assert ranges.height > 0

        for row in ranges.to_dicts():
            # Availability is the session's close, never any instant inside it.
            assert row["available_from"] >= row["period_end"]
            assert row["available_from"] > row["period_start"]

    def test_each_session_occurrence_produces_at_most_one_range(self) -> None:
        bars = _bars(96, start=datetime(2024, 6, 3, tzinfo=UTC))
        ranges = session_ranges(bars, LONDON)
        assert ranges["range_id"].n_unique() == ranges.height


class TestOpeningRange:
    def test_the_opening_range_is_available_when_its_window_elapses(self) -> None:
        bars = _bars(96, start=datetime(2024, 6, 3, tzinfo=UTC))
        ranges = opening_ranges(bars, LONDON, 60)
        assert ranges.height > 0

        for row in ranges.to_dicts():
            assert row["available_from"] == row["period_start"] + timedelta(minutes=60)
            # It is the one reference that becomes usable inside its own session,
            # and it must die with that session rather than persist.
            assert row["expires_at"] > row["available_from"]

    def test_an_opening_range_shorter_than_a_bar_is_refused(self) -> None:
        bars = _bars(96, start=datetime(2024, 6, 3, tzinfo=UTC))
        with pytest.raises(RangeError, match="cannot be built"):
            opening_ranges(bars, LONDON, 15)


class TestRollingAndMultiDay:
    def test_a_rolling_range_excludes_the_bar_it_is_attached_to(self) -> None:
        highs = [100.0] * 10 + [500.0]
        bars = _bars(11, highs=highs)
        ranges = rolling_ranges(bars, 5)

        last = ranges.sort("available_from").tail(1).to_dicts()[0]
        assert last["available_from"] == bars["open_time"].to_list()[-1]
        assert last["high"] == 100.0  # the 500 belongs to the current bar

    def test_the_n_day_range_spans_exactly_n_completed_days(self) -> None:
        highs = [110.0] * 24 + [130.0] * 24 + [120.0] * 24 + [999.0] * 24
        bars = _bars(96, highs=highs)
        ranges = n_day_ranges(bars, 3)

        assert ranges.height >= 1
        first = ranges.sort("available_from").head(1).to_dicts()[0]
        assert first["high"] == 130.0
        assert first["available_from"] == datetime(2024, 1, 4, tzinfo=UTC)


class TestDerivedGeometry:
    def test_quartiles_and_mid_sit_where_arithmetic_puts_them(self) -> None:
        highs = [200.0] * 24 + [1.0] * 24
        lows = [100.0] * 24 + [0.5] * 24
        row = daily_ranges(_bars(48, highs=highs, lows=lows)).to_dicts()[0]

        assert row["mid"] == 150.0
        assert row["q25"] == 125.0
        assert row["q75"] == 175.0
        assert row["width"] == 100.0

    def test_atr_warms_up_as_null_rather_than_as_zero(self) -> None:
        bars = _bars(40)
        atr = average_true_range(bars, 14)
        # Fourteen observations plus the one-bar shift. Before that there is no
        # answer, and the absence is a null, never a zero that would read as
        # "no volatility".
        assert atr[:14].null_count() == 14
        assert atr[14] is not None

    def test_atr_at_a_bar_does_not_change_when_later_bars_change(self) -> None:
        """Truncation invariance: the direct test for look-ahead.

        If the value at bar *i* were contaminated by anything after *i*, editing
        a later bar would move it. Nothing later may matter.
        """
        bars = _bars(40)
        truncated = average_true_range(bars.head(30), 14)

        tampered = bars.with_columns(
            pl.when(pl.int_range(pl.len()) >= 30)
            .then(pl.col("high") * 10.0)
            .otherwise(pl.col("high"))
            .alias("high")
        )
        full = average_true_range(tampered, 14)

        assert truncated.to_list() == full.head(30).to_list()


class TestActiveWindow:
    def test_a_range_is_invisible_before_it_is_available(self) -> None:
        ranges = daily_ranges(_bars(48))
        just_before = datetime(2024, 1, 1, 23, tzinfo=UTC)
        assert active_ranges_at(ranges, just_before).height == 0

    def test_a_range_is_invisible_after_it_expires(self) -> None:
        ranges = daily_ranges(_bars(96))
        long_after = datetime(2024, 1, 5, tzinfo=UTC)
        assert active_ranges_at(ranges, long_after).height == 0

    def test_asking_for_a_label_that_is_not_active_returns_nothing(self) -> None:
        ranges = daily_ranges(_bars(48))
        assert latest_range(ranges, "previous_day", datetime(2024, 1, 1, tzinfo=UTC)) is None

    def test_the_most_recent_usable_range_is_the_one_returned(self) -> None:
        ranges = daily_ranges(_bars(96))
        moment = datetime(2024, 1, 3, 12, tzinfo=UTC)
        row = latest_range(ranges, "previous_day", moment)
        assert row is not None
        available_from = row["available_from"]
        assert isinstance(available_from, datetime)
        assert available_from <= moment


class TestBuildRanges:
    def test_a_configured_build_produces_every_requested_family_of_level(self) -> None:
        bars = _bars(240, start=datetime(2024, 6, 3, tzinfo=UTC))
        config = RangeConfig(
            daily=True,
            weekly=False,
            monthly=False,
            n_day_windows=(3,),
            sessions=("london",),
            candle_timeframes=("4h",),
            opening_range_minutes=(60,),
            rolling_windows=(12,),
        )
        ranges = build_ranges(bars, config)
        labels = set(ranges["label"].to_list())

        assert "previous_day" in labels
        assert "last_3_days" in labels
        assert "previous_candle_4h" in labels
        assert "previous_session_london" in labels
        assert "opening_range_60m_london" in labels
        assert "rolling_12" in labels

    def test_every_built_range_is_available_no_earlier_than_its_period_ends(self) -> None:
        """The invariant that makes the whole module safe, checked across all kinds."""
        bars = _bars(240, start=datetime(2024, 6, 3, tzinfo=UTC))
        ranges = build_ranges(
            bars,
            RangeConfig(n_day_windows=(3,), rolling_windows=(12,), opening_range_minutes=(60,)),
        )

        breaches = ranges.filter(pl.col("available_from") < pl.col("period_end"))
        assert breaches.height == 0, breaches.to_dicts()

    def test_asking_for_an_opening_range_finer_than_the_bars_says_what_to_do(self) -> None:
        """A 15-minute opening range on hourly bars is a specification error.

        It must fail loudly rather than be skipped, because silently dropping a
        requested reference changes which levels a strategy trades against
        without anybody noticing.
        """
        bars = _bars(240, start=datetime(2024, 6, 3, tzinfo=UTC))
        with pytest.raises(RangeError, match="opening_range_minutes"):
            build_ranges(bars, RangeConfig(opening_range_minutes=(15,)))

    def test_width_in_atr_units_is_attached_where_atr_exists(self) -> None:
        bars = _bars(240, start=datetime(2024, 6, 3, tzinfo=UTC))
        ranges = build_ranges(bars, RangeConfig(sessions=(), candle_timeframes=()))
        assert ranges.filter(pl.col("width_atr").is_not_null()).height > 0

    def test_bars_without_the_required_columns_are_refused(self) -> None:
        with pytest.raises(RangeError, match="missing required columns"):
            daily_ranges(pl.DataFrame({"open_time": [datetime(2024, 1, 1, tzinfo=UTC)]}))
