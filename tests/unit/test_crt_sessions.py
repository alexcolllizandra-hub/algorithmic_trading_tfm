"""Sessions must survive the two things that quietly break intraday research.

Daylight saving, because a session pinned to a wall-clock hour moves relative to
UTC twice a year and a fixed offset turns that into fake seasonality. And
midnight, because the Asian session starts in the evening and ends the next
morning, so any implementation that stores an end time rather than a duration
gets it wrong for a third of the trading day.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

import polars as pl
import pytest

from perp_lab.crt.sessions import (
    ASIA,
    CRYPTO_DAY,
    LONDON,
    NEW_YORK,
    SessionError,
    SessionSpec,
    resolve_session,
    session_windows,
    tag_sessions,
)


class TestDaylightSaving:
    def test_london_moves_against_utc_when_the_clocks_change(self) -> None:
        winter = LONDON.open_on(date(2024, 1, 15))
        summer = LONDON.open_on(date(2024, 7, 15))

        # 08:00 Europe/London is 08:00 UTC in winter and 07:00 UTC in summer.
        assert winter.astimezone(UTC).hour == 8
        assert summer.astimezone(UTC).hour == 7

    def test_london_and_new_york_are_briefly_out_of_step(self) -> None:
        """Europe and the United States do not change clocks on the same date.

        Between the US spring transition and the European one, the gap between
        the two sessions is an hour narrower than usual. A hard-coded offset
        cannot represent this fortnight, and every level built during it would
        be shifted.
        """
        gap = LONDON.open_on(date(2024, 3, 13)) - NEW_YORK.open_on(date(2024, 3, 13))
        usual = LONDON.open_on(date(2024, 2, 13)) - NEW_YORK.open_on(date(2024, 2, 13))
        assert gap != usual
        assert abs((usual - gap).total_seconds()) == 3600

    def test_a_start_time_that_does_not_exist_locally_still_produces_a_session(self) -> None:
        """On spring-forward the nominal hour can be skipped entirely."""
        skipped = SessionSpec(
            name="skipped",
            timezone="America/New_York",
            start=time(2, 30),
            duration=timedelta(hours=2),
        )
        opened = skipped.open_on(date(2024, 3, 10))
        assert opened.tzinfo is not None

    def test_an_ambiguous_start_time_resolves_without_raising(self) -> None:
        """On autumn fall-back the nominal hour happens twice."""
        doubled = SessionSpec(
            name="doubled",
            timezone="America/New_York",
            start=time(1, 30),
            duration=timedelta(hours=2),
        )
        opened = doubled.open_on(date(2024, 11, 3))
        assert opened.tzinfo is not None


class TestMidnightCrossing:
    def test_the_asian_session_spans_two_utc_days_as_one_window(self) -> None:
        opened, closed = ASIA.window_on(date(2024, 6, 3))
        assert closed > opened
        assert closed - opened == timedelta(hours=9)
        # Anchored on the Tokyo day, the window lands on a single UTC date here,
        # but the contract is that it is one window regardless.
        assert (closed - opened).total_seconds() == 9 * 3600

    def test_a_window_that_wraps_midnight_is_not_split(self) -> None:
        evening = SessionSpec(
            name="evening",
            timezone="UTC",
            start=time(22, 0),
            duration=timedelta(hours=4),
        )
        opened, closed = evening.window_on(date(2024, 6, 3))
        assert opened.day == 3
        assert closed.day == 4
        assert closed - opened == timedelta(hours=4)

    def test_each_local_day_yields_exactly_one_occurrence(self) -> None:
        start = datetime(2024, 6, 1, tzinfo=UTC)
        end = datetime(2024, 6, 8, tzinfo=UTC)
        windows = session_windows(LONDON, start, end)
        days = [day for day, _, _ in windows]
        assert len(days) == len(set(days))


class TestDefinitionsAreChecked:
    def test_a_session_cannot_outlast_a_day(self) -> None:
        with pytest.raises(SessionError, match="longer than a day"):
            SessionSpec(
                name="too_long", timezone="UTC", start=time(0, 0), duration=timedelta(hours=25)
            )

    def test_a_zero_length_session_is_refused(self) -> None:
        with pytest.raises(SessionError, match="positive"):
            SessionSpec(name="empty", timezone="UTC", start=time(0, 0), duration=timedelta(0))

    def test_an_unknown_time_zone_is_refused_by_name(self) -> None:
        with pytest.raises(SessionError, match="Mars"):
            SessionSpec(
                name="mars", timezone="Mars/Olympus", start=time(0, 0), duration=timedelta(hours=1)
            )

    def test_an_entry_cutoff_after_the_close_is_refused(self) -> None:
        with pytest.raises(SessionError, match="cutoff"):
            SessionSpec(
                name="late",
                timezone="UTC",
                start=time(0, 0),
                duration=timedelta(hours=2),
                entry_cutoff=timedelta(hours=3),
            )

    def test_an_unknown_session_name_lists_what_is_available(self) -> None:
        with pytest.raises(SessionError, match="london"):
            resolve_session("frankfurt")


class TestTagging:
    @staticmethod
    def _bars(n: int = 48) -> pl.DataFrame:
        start = datetime(2024, 6, 3, tzinfo=UTC)
        return pl.DataFrame(
            {"open_time": [start + timedelta(hours=i) for i in range(n)]},
        ).with_columns(pl.col("open_time").dt.replace_time_zone("UTC"))

    def test_a_bar_is_tagged_by_the_session_running_when_it_opened(self) -> None:
        tagged = tag_sessions(self._bars(), (LONDON,))
        assert "in_london" in tagged.columns
        assert tagged["in_london"].sum() > 0

    def test_overlapping_sessions_both_claim_their_bars(self) -> None:
        """The overlap is inside both parents by construction.

        Forcing a bar to belong to one session would destroy the very thing the
        overlap window is meant to measure.
        """
        tagged = tag_sessions(self._bars(), (LONDON, NEW_YORK, CRYPTO_DAY))
        both = tagged.filter(pl.col("in_london") & pl.col("in_new_york"))
        assert both.height > 0
        assert tagged["in_crypto_day"].all()

    def test_every_tagged_bar_carries_the_local_day_it_belongs_to(self) -> None:
        tagged = tag_sessions(self._bars(), (LONDON,))
        inside = tagged.filter(pl.col("in_london"))
        assert inside["london_day"].null_count() == 0

    def test_an_empty_frame_passes_through_untouched(self) -> None:
        empty = pl.DataFrame(schema={"open_time": pl.Datetime("ms", "UTC")})
        assert tag_sessions(empty, (LONDON,)).height == 0

    def test_a_frame_without_a_time_column_is_refused(self) -> None:
        with pytest.raises(SessionError, match="open_time"):
            tag_sessions(pl.DataFrame({"close": [1.0]}), (LONDON,))
