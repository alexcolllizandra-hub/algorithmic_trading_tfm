"""Time helpers.

All timestamps in the project are timezone-aware UTC. Binance bulk data ships
millisecond epoch integers; candles are labeled by their **open time** and are
left-closed / right-open (a 5m bar labeled 10:00 covers [10:00, 10:05)).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

# Supported timeframes and their duration in milliseconds.
TIMEFRAME_TO_MS: dict[str, int] = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}


def timeframe_to_timedelta(timeframe: str) -> timedelta:
    """Return the :class:`datetime.timedelta` for a supported timeframe."""
    try:
        return timedelta(milliseconds=TIMEFRAME_TO_MS[timeframe])
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(
            f"Unsupported timeframe {timeframe!r}. Supported: {sorted(TIMEFRAME_TO_MS)}"
        ) from exc


def ms_to_utc(epoch_ms: int) -> datetime:
    """Convert a millisecond epoch integer to a tz-aware UTC datetime."""
    return datetime.fromtimestamp(epoch_ms / 1000, tz=UTC)


def utc_to_ms(dt: datetime) -> int:
    """Convert a datetime to a millisecond epoch integer.

    Naive datetimes are assumed to already be in UTC.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def floor_to_timeframe(dt: datetime, timeframe: str) -> datetime:
    """Floor a UTC datetime to the start of its enclosing bar.

    The epoch (1970-01-01T00:00:00Z) is the alignment anchor, which matches how
    Binance labels klines.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    step = TIMEFRAME_TO_MS[timeframe]
    ms = utc_to_ms(dt)
    return ms_to_utc(ms - (ms % step))


def expected_bar_count(start: datetime, end: datetime, timeframe: str) -> int:
    """Number of bars expected in ``[start, end)`` for a 24/7 market.

    Both bounds are treated as bar-open timestamps; ``start`` is inclusive and
    ``end`` is exclusive. Used to detect missing candles.
    """
    if end <= start:
        return 0
    step = TIMEFRAME_TO_MS[timeframe]
    span_ms = utc_to_ms(end) - utc_to_ms(start)
    return span_ms // step
