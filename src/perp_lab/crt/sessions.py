"""Trading sessions on a 24/7 market, with real time zones.

Crypto perpetuals never close, so a "session" here is not an exchange calendar —
it is a window of the day during which a particular pool of participants is
active. That makes the definition a modelling choice rather than a fact, and the
choice has to be explicit and reproducible.

Two things make this harder than adding an offset to UTC.

**Daylight saving.** London and New York change clocks on different dates, so
for a few weeks each spring and autumn the gap between them is not what it is
the rest of the year. A session pinned to 08:00 Europe/London is at 08:00 UTC in
winter and 07:00 UTC in summer. Hard-coding an offset silently shifts every
level by an hour twice a year, and the resulting artefacts look like seasonality.
Everything below therefore resolves through IANA zones, per calendar day.

**Midnight.** The Asian session starts in the evening in its own zone and ends
the following morning. A window is stored as a start time and a duration rather
than a start and an end, so a window that wraps is the ordinary case rather than
a special one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import polars as pl

UTC = ZoneInfo("UTC")


class SessionError(ValueError):
    """Raised when a session definition or a session query is not coherent."""


@dataclass(frozen=True)
class SessionSpec:
    """One named intraday window, anchored in a real time zone.

    ``duration`` rather than an end time is deliberate: it makes a window that
    crosses midnight indistinguishable in code from one that does not, so the
    wrap case cannot be forgotten.

    ``entry_cutoff`` and ``force_close`` express the practical asymmetry of
    intraday trading — you stop taking new risk before you stop managing it.
    Both are offsets from the session open, so they follow the zone along with
    everything else.
    """

    name: str
    timezone: str
    start: time
    duration: timedelta
    opening_window: timedelta = timedelta(minutes=30)
    entry_cutoff: timedelta | None = None
    force_close: bool = False
    max_trades: int | None = None
    references: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        if self.duration <= timedelta(0):
            raise SessionError(f"{self.name}: duration must be positive.")
        if self.duration > timedelta(days=1):
            raise SessionError(f"{self.name}: a session cannot be longer than a day.")
        if self.opening_window > self.duration:
            raise SessionError(f"{self.name}: the opening window outlasts the session.")
        if self.entry_cutoff is not None and self.entry_cutoff > self.duration:
            raise SessionError(f"{self.name}: the entry cutoff falls after the session ends.")
        try:
            ZoneInfo(self.timezone)
        except Exception as exc:
            raise SessionError(f"{self.name}: unknown IANA time zone {self.timezone!r}.") from exc

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def open_on(self, local_day: date) -> datetime:
        """The UTC instant this session opens on a given local calendar day.

        The local day is the anchor, not the UTC day: a session that opens at
        23:00 Asia/Tokyo belongs to the Tokyo day it opens on, whichever UTC day
        that lands in.

        On the spring-forward transition the nominal start time may not exist
        locally. ``fold``/normalisation in ``zoneinfo`` resolves it forward
        rather than raising, which is the behaviour we want: the session still
        happens, it merely starts at the first instant that exists.
        """
        naive = datetime.combine(local_day, self.start)
        return naive.replace(tzinfo=self.zone).astimezone(UTC)

    def close_on(self, local_day: date) -> datetime:
        return self.open_on(local_day) + self.duration

    def window_on(self, local_day: date) -> tuple[datetime, datetime]:
        """``[open, close)`` in UTC. Left-closed, matching the bar convention."""
        opened = self.open_on(local_day)
        return opened, opened + self.duration

    def cutoff_on(self, local_day: date) -> datetime | None:
        if self.entry_cutoff is None:
            return None
        return self.open_on(local_day) + self.entry_cutoff


ASIA = SessionSpec(
    name="asia",
    timezone="Asia/Tokyo",
    start=time(9, 0),
    duration=timedelta(hours=9),
    entry_cutoff=timedelta(hours=8),
)
LONDON = SessionSpec(
    name="london",
    timezone="Europe/London",
    start=time(8, 0),
    duration=timedelta(hours=8, minutes=30),
    entry_cutoff=timedelta(hours=7),
    references=("asia",),
)
NEW_YORK = SessionSpec(
    name="new_york",
    timezone="America/New_York",
    start=time(9, 30),
    duration=timedelta(hours=6, minutes=30),
    entry_cutoff=timedelta(hours=5),
    references=("asia", "london"),
)
LONDON_NEW_YORK_OVERLAP = SessionSpec(
    name="london_new_york_overlap",
    timezone="America/New_York",
    start=time(9, 30),
    duration=timedelta(hours=3),
    opening_window=timedelta(minutes=15),
    references=("asia", "london"),
)
CRYPTO_DAY = SessionSpec(
    name="crypto_day",
    timezone="UTC",
    start=time(0, 0),
    duration=timedelta(hours=24),
    opening_window=timedelta(hours=1),
)

DEFAULT_SESSIONS: tuple[SessionSpec, ...] = (
    ASIA,
    LONDON,
    NEW_YORK,
    LONDON_NEW_YORK_OVERLAP,
    CRYPTO_DAY,
)

SESSION_REGISTRY: dict[str, SessionSpec] = {s.name: s for s in DEFAULT_SESSIONS}


def resolve_session(name: str, *, registry: dict[str, SessionSpec] | None = None) -> SessionSpec:
    table = SESSION_REGISTRY if registry is None else registry
    if name not in table:
        raise SessionError(f"Unknown session {name!r}. Known: {sorted(table)}")
    return table[name]


def _local_days(start: datetime, end: datetime, zone: ZoneInfo) -> list[date]:
    """Local calendar days that could host a session overlapping ``[start, end]``.

    Padded by a day at each end because a local day's session can begin before
    the requested window opens and finish after it closes.
    """
    first = (start.astimezone(zone) - timedelta(days=1)).date()
    last = (end.astimezone(zone) + timedelta(days=1)).date()
    out: list[date] = []
    cursor = first
    while cursor <= last:
        out.append(cursor)
        cursor += timedelta(days=1)
    return out


def session_windows(
    spec: SessionSpec, start: datetime, end: datetime
) -> list[tuple[date, datetime, datetime]]:
    """Every occurrence of ``spec`` overlapping ``[start, end)``, in UTC.

    Returned as ``(local_day, open, close)`` so that downstream code can group by
    the session's own day rather than by the UTC day, which is what makes an
    Asian session that straddles midnight a single object instead of two halves.
    """
    if end < start:
        raise SessionError("The window ends before it starts.")
    zone = spec.zone
    windows: list[tuple[date, datetime, datetime]] = []
    for day in _local_days(start, end, zone):
        opened, closed = spec.window_on(day)
        if closed > start and opened < end:
            windows.append((day, opened, closed))
    return windows


def tag_sessions(
    frame: pl.DataFrame,
    specs: tuple[SessionSpec, ...] = DEFAULT_SESSIONS,
    *,
    time_column: str = "open_time",
) -> pl.DataFrame:
    """Attach, per bar, which sessions contain it and which local day they belong to.

    One boolean column and one day column per session rather than a single
    categorical, because sessions genuinely overlap — the London/New York
    overlap is inside both of its parents by construction, and forcing a bar to
    pick one would destroy the thing being measured.

    Membership is decided on the bar's **open** time. Bars are left-closed and
    labelled by open, so a bar belongs to the session that was running when it
    started, and no bar is ever assigned to a session that had not begun.
    """
    if time_column not in frame.columns:
        raise SessionError(f"Frame has no {time_column!r} column.")
    if frame.height == 0:
        return frame

    times = frame[time_column]
    start = times.min()
    end = times.max()
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        raise SessionError(f"{time_column!r} must be a tz-aware datetime column.")

    out = frame
    for spec in specs:
        in_session = pl.Series([False] * frame.height, dtype=pl.Boolean)
        day_of = pl.Series([None] * frame.height, dtype=pl.Date)
        for local_day, opened, closed in session_windows(spec, start, end):
            mask = (times >= opened) & (times < closed)
            in_session = in_session | mask
            day_of = day_of.zip_with(~mask, pl.Series([local_day] * frame.height, dtype=pl.Date))
        out = out.with_columns(
            in_session.alias(f"in_{spec.name}"),
            day_of.alias(f"{spec.name}_day"),
        )
    return out


__all__ = [
    "ASIA",
    "CRYPTO_DAY",
    "DEFAULT_SESSIONS",
    "LONDON",
    "LONDON_NEW_YORK_OVERLAP",
    "NEW_YORK",
    "SESSION_REGISTRY",
    "SessionError",
    "SessionSpec",
    "resolve_session",
    "session_windows",
    "tag_sessions",
]
