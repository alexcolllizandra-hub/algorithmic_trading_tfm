"""Reference ranges and liquidity levels, available only after they are finished.

Every level carries an ``available_from`` timestamp; consumers must join on
it rather than on the calendar day.

The failure this prevents is easy to write by accident. "Yesterday's high" is a single number for the whole of today, so it is
tempting to compute a daily high and broadcast it across the day's bars. Do that
without shifting and every bar in a day knows the high of the day it is in,
including bars that occur before the high was set. A strategy built on that
looks superb and is worthless. The same trap applies to session highs while the
session is still running, and to the extremes of an HTF candle that has not
closed.

So: a range is created by a period, and it becomes usable at the instant that
period ends — never before. Consumers must filter on ``available_from``, and
``active_ranges_at`` does it for them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from itertools import pairwise
from zoneinfo import ZoneInfo

import polars as pl

from perp_lab.crt.sessions import (
    DEFAULT_SESSIONS,
    SessionError,
    SessionSpec,
    session_windows,
)

UTC = ZoneInfo("UTC")

RANGE_SCHEMA: dict[str, pl.DataType] = {
    "range_id": pl.String(),
    "kind": pl.String(),
    "label": pl.String(),
    "session": pl.String(),
    "timezone": pl.String(),
    "period_start": pl.Datetime("ms", "UTC"),
    "period_end": pl.Datetime("ms", "UTC"),
    "available_from": pl.Datetime("ms", "UTC"),
    "expires_at": pl.Datetime("ms", "UTC"),
    "high": pl.Float64(),
    "low": pl.Float64(),
    "open": pl.Float64(),
    "close": pl.Float64(),
    "mid": pl.Float64(),
    "q25": pl.Float64(),
    "q75": pl.Float64(),
    "width": pl.Float64(),
    "width_pct": pl.Float64(),
    "width_atr": pl.Float64(),
}


class RangeError(ValueError):
    """Raised when a range cannot be built causally from the bars supplied."""


class RangeKind(StrEnum):
    """What produced a range, which determines how it should be read."""

    PREVIOUS_DAY = "previous_day"
    PREVIOUS_WEEK = "previous_week"
    PREVIOUS_MONTH = "previous_month"
    PREVIOUS_SESSION = "previous_session"
    PREVIOUS_CANDLE = "previous_candle"
    OPENING_RANGE = "opening_range"
    ROLLING = "rolling"
    N_DAY = "n_day"


@dataclass(frozen=True)
class RangeConfig:
    """Which reference ranges to build, and how wide the derived levels are.

    ``atr_window`` normalises range width so a 400-point range means something
    comparable in a calm week and a violent one. It is measured on the execution
    timeframe and, like everything else here, uses only closed bars.
    """

    daily: bool = True
    weekly: bool = True
    monthly: bool = False
    n_day_windows: tuple[int, ...] = (5, 20)
    sessions: tuple[str, ...] = ("asia", "london", "new_york")
    candle_timeframes: tuple[str, ...] = ("1h", "4h", "1d")
    opening_range_minutes: tuple[int, ...] = (15, 60)
    rolling_windows: tuple[int, ...] = ()
    atr_window: int = 14
    timezone: str = "UTC"


def _require_columns(frame: pl.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise RangeError(f"Bars are missing required columns: {missing}")


def _bar_span(frame: pl.DataFrame) -> timedelta:
    """The bar interval, inferred from the data rather than trusted from a label."""
    if frame.height < 2:
        raise RangeError("At least two bars are needed to infer the bar interval.")
    times = frame["open_time"].to_list()
    deltas = {times[i + 1] - times[i] for i in range(min(64, len(times) - 1))}
    return min(deltas)


def average_true_range(frame: pl.DataFrame, window: int) -> pl.Series:
    """Wilder-style true range, smoothed causally and shifted by one bar.

    The shift matters: the ATR attached to a bar must be computable before that
    bar opens, so it summarises the bars strictly before it.
    """
    _require_columns(frame, ("high", "low", "close"))
    prev_close = frame["close"].shift(1)
    high = frame["high"]
    low = frame["low"]
    true_range = (
        pl.DataFrame(
            {
                "hl": high - low,
                "hc": (high - prev_close).abs(),
                "lc": (low - prev_close).abs(),
            }
        )
        .max_horizontal()
        .alias("tr")
    )
    return true_range.rolling_mean(window_size=window, min_samples=window).shift(1)


def _empty_ranges() -> pl.DataFrame:
    return pl.DataFrame(schema=RANGE_SCHEMA)


def _derive(rows: list[dict[str, object]]) -> pl.DataFrame:
    if not rows:
        return _empty_ranges()
    frame = pl.DataFrame(rows, schema_overrides=RANGE_SCHEMA)
    return frame.with_columns(
        ((pl.col("high") + pl.col("low")) / 2.0).alias("mid"),
        (pl.col("low") + 0.25 * (pl.col("high") - pl.col("low"))).alias("q25"),
        (pl.col("low") + 0.75 * (pl.col("high") - pl.col("low"))).alias("q75"),
        (pl.col("high") - pl.col("low")).alias("width"),
    ).with_columns(
        pl.when(pl.col("low") > 0)
        .then(pl.col("width") / pl.col("low") * 100.0)
        .otherwise(None)
        .alias("width_pct"),
    )


def _aggregate(frame: pl.DataFrame, key: pl.Expr, label: str) -> pl.DataFrame:
    """Collapse bars into one row per period, keeping first open and last close."""
    return (
        frame.with_columns(key.alias("_period"))
        .group_by("_period")
        .agg(
            pl.col("open_time").min().alias("period_start"),
            pl.col("open_time").max().alias("last_open"),
            pl.col("high").max().alias("high"),
            pl.col("low").min().alias("low"),
            pl.col("open").first().alias("open"),
            pl.col("close").last().alias("close"),
        )
        .sort("period_start")
        .with_columns(pl.lit(label).alias("label"))
    )


def previous_period_ranges(
    bars: pl.DataFrame,
    *,
    key: pl.Expr,
    kind: RangeKind,
    label: str,
    timezone: str = "UTC",
    lifetime: timedelta | None = None,
) -> pl.DataFrame:
    """Levels of each completed period, usable from the moment it completes.

    The shift is what enforces causality: period *N*'s extremes are attached to
    the row describing period *N+1*, so they can only ever be read after period
    *N* has closed. There is no configuration that turns this off.
    """
    _require_columns(bars, ("open_time", "open", "high", "low", "close"))
    if bars.height == 0:
        return _empty_ranges()

    span = _bar_span(bars)
    periods = _aggregate(bars, key, label)
    if periods.height < 2:
        return _empty_ranges()

    rows: list[dict[str, object]] = []
    records = periods.to_dicts()
    for previous, current in pairwise(records):
        # The previous period is complete once its last bar has closed, which is
        # one bar span after that bar opened.
        available = previous["last_open"] + span
        start_of_current = current["period_start"]
        # A level cannot become available before the period that follows it has
        # begun, and it cannot become available after that period's first bar.
        available = max(available, start_of_current)
        expires = (available + lifetime) if lifetime is not None else current["last_open"] + span
        rows.append(
            {
                "range_id": f"{label}:{previous['period_start'].isoformat()}",
                "kind": str(kind),
                "label": label,
                "session": "",
                "timezone": timezone,
                "period_start": previous["period_start"],
                "period_end": previous["last_open"] + span,
                "available_from": available,
                "expires_at": expires,
                "high": previous["high"],
                "low": previous["low"],
                "open": previous["open"],
                "close": previous["close"],
                "mid": None,
                "q25": None,
                "q75": None,
                "width": None,
                "width_pct": None,
                "width_atr": None,
            }
        )
    return _derive(rows)


def _local_day_key(timezone: str) -> pl.Expr:
    return pl.col("open_time").dt.convert_time_zone(timezone).dt.date()


def daily_ranges(bars: pl.DataFrame, *, timezone: str = "UTC") -> pl.DataFrame:
    """Previous-day high, low, mid and open — PDH, PDL, PDM."""
    return previous_period_ranges(
        bars,
        key=_local_day_key(timezone),
        kind=RangeKind.PREVIOUS_DAY,
        label="previous_day",
        timezone=timezone,
    )


def weekly_ranges(bars: pl.DataFrame, *, timezone: str = "UTC") -> pl.DataFrame:
    key = pl.col("open_time").dt.convert_time_zone(timezone).dt.truncate("1w")
    return previous_period_ranges(
        bars, key=key, kind=RangeKind.PREVIOUS_WEEK, label="previous_week", timezone=timezone
    )


def monthly_ranges(bars: pl.DataFrame, *, timezone: str = "UTC") -> pl.DataFrame:
    key = pl.col("open_time").dt.convert_time_zone(timezone).dt.truncate("1mo")
    return previous_period_ranges(
        bars, key=key, kind=RangeKind.PREVIOUS_MONTH, label="previous_month", timezone=timezone
    )


def candle_ranges(bars: pl.DataFrame, timeframe: str) -> pl.DataFrame:
    """The previous closed HTF candle, e.g. the last completed 4h or daily bar.

    Only closed candles: an HTF candle that is still forming has no final high
    or low, and using one is the most common way this kind of model leaks.
    """
    key = pl.col("open_time").dt.truncate(timeframe)
    return previous_period_ranges(
        bars,
        key=key,
        kind=RangeKind.PREVIOUS_CANDLE,
        label=f"previous_candle_{timeframe}",
    )


def n_day_ranges(bars: pl.DataFrame, window: int, *, timezone: str = "UTC") -> pl.DataFrame:
    """Highest high and lowest low of the last ``window`` completed days."""
    daily = _aggregate(bars, _local_day_key(timezone), f"last_{window}_days").sort("period_start")
    if daily.height <= window:
        return _empty_ranges()
    span = _bar_span(bars)

    rolled = daily.with_columns(
        pl.col("high").rolling_max(window_size=window, min_samples=window).alias("win_high"),
        pl.col("low").rolling_min(window_size=window, min_samples=window).alias("win_low"),
        pl.col("open").shift(window - 1).alias("win_open"),
    )
    records = rolled.to_dicts()
    rows: list[dict[str, object]] = []
    for previous, current in pairwise(records):
        if previous["win_high"] is None:
            continue
        available = max(previous["last_open"] + span, current["period_start"])
        rows.append(
            {
                "range_id": f"last_{window}_days:{previous['period_start'].isoformat()}",
                "kind": str(RangeKind.N_DAY),
                "label": f"last_{window}_days",
                "session": "",
                "timezone": timezone,
                "period_start": previous["period_start"],
                "period_end": previous["last_open"] + span,
                "available_from": available,
                "expires_at": current["last_open"] + span,
                "high": previous["win_high"],
                "low": previous["win_low"],
                "open": previous["win_open"],
                "close": previous["close"],
                "mid": None,
                "q25": None,
                "q75": None,
                "width": None,
                "width_pct": None,
                "width_atr": None,
            }
        )
    return _derive(rows)


def session_ranges(bars: pl.DataFrame, spec: SessionSpec) -> pl.DataFrame:
    """The completed range of each occurrence of a session.

    Available from the session's close, not from any instant inside it. Expires
    when the next occurrence of the same session closes, which is the window
    during which "yesterday's London range" is the relevant reference.
    """
    _require_columns(bars, ("open_time", "open", "high", "low", "close"))
    if bars.height == 0:
        return _empty_ranges()

    span = _bar_span(bars)
    times = bars["open_time"]
    start, end = times.min(), times.max()
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        raise RangeError("open_time must be a tz-aware datetime column.")

    built: list[dict[str, object]] = []
    for local_day, opened, closed in session_windows(spec, start, end):
        window = bars.filter((pl.col("open_time") >= opened) & (pl.col("open_time") < closed))
        if window.height == 0:
            continue
        last_open = window["open_time"].max()
        assert isinstance(last_open, datetime)
        built.append(
            {
                "local_day": local_day,
                "period_start": opened,
                "period_end": min(closed, last_open + span),
                "high": float(window["high"].max()),  # type: ignore[arg-type]
                "low": float(window["low"].min()),  # type: ignore[arg-type]
                "open": float(window["open"].first()),  # type: ignore[arg-type]
                "close": float(window["close"].last()),  # type: ignore[arg-type]
            }
        )

    rows: list[dict[str, object]] = []
    for index, record in enumerate(built):
        expires = built[index + 1]["period_end"] if index + 1 < len(built) else None
        rows.append(
            {
                "range_id": f"{spec.name}:{record['local_day']}",
                "kind": str(RangeKind.PREVIOUS_SESSION),
                "label": f"previous_session_{spec.name}",
                "session": spec.name,
                "timezone": spec.timezone,
                "period_start": record["period_start"],
                "period_end": record["period_end"],
                "available_from": record["period_end"],
                "expires_at": expires,
                "high": record["high"],
                "low": record["low"],
                "open": record["open"],
                "close": record["close"],
                "mid": None,
                "q25": None,
                "q75": None,
                "width": None,
                "width_pct": None,
                "width_atr": None,
            }
        )
    return _derive(rows)


def opening_ranges(bars: pl.DataFrame, spec: SessionSpec, minutes: int) -> pl.DataFrame:
    """The first ``minutes`` of a session, usable once that window has elapsed.

    The opening range is the one reference that becomes available *during* its
    own session, which is exactly why it needs care: it is available from the
    end of the opening window, and it stays valid only until the session closes.
    """
    _require_columns(bars, ("open_time", "open", "high", "low", "close"))
    if bars.height == 0:
        return _empty_ranges()

    span = _bar_span(bars)
    length = timedelta(minutes=minutes)
    if length < span:
        raise RangeError(
            f"A {minutes}-minute opening range cannot be built from {span} bars: the window "
            "would close before the first bar does. Either supply finer bars or drop this "
            "length from RangeConfig.opening_range_minutes."
        )

    times = bars["open_time"]
    start, end = times.min(), times.max()
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        raise RangeError("open_time must be a tz-aware datetime column.")

    rows: list[dict[str, object]] = []
    for local_day, opened, closed in session_windows(spec, start, end):
        stop = opened + length
        window = bars.filter((pl.col("open_time") >= opened) & (pl.col("open_time") < stop))
        if window.height == 0:
            continue
        rows.append(
            {
                "range_id": f"or{minutes}_{spec.name}:{local_day}",
                "kind": str(RangeKind.OPENING_RANGE),
                "label": f"opening_range_{minutes}m_{spec.name}",
                "session": spec.name,
                "timezone": spec.timezone,
                "period_start": opened,
                "period_end": stop,
                "available_from": stop,
                "expires_at": closed,
                "high": float(window["high"].max()),  # type: ignore[arg-type]
                "low": float(window["low"].min()),  # type: ignore[arg-type]
                "open": float(window["open"].first()),  # type: ignore[arg-type]
                "close": float(window["close"].last()),  # type: ignore[arg-type]
                "mid": None,
                "q25": None,
                "q75": None,
                "width": None,
                "width_pct": None,
                "width_atr": None,
            }
        )
    return _derive(rows)


def rolling_ranges(bars: pl.DataFrame, window: int) -> pl.DataFrame:
    """Highest high and lowest low of the last ``window`` closed bars."""
    _require_columns(bars, ("open_time", "open", "high", "low", "close"))
    if bars.height <= window:
        return _empty_ranges()
    span = _bar_span(bars)
    rolled = bars.select(
        pl.col("open_time"),
        pl.col("high").rolling_max(window_size=window, min_samples=window).shift(1).alias("rh"),
        pl.col("low").rolling_min(window_size=window, min_samples=window).shift(1).alias("rl"),
        pl.col("open").shift(window).alias("ro"),
        pl.col("close").shift(1).alias("rc"),
    ).drop_nulls()

    rows = [
        {
            "range_id": f"rolling{window}:{record['open_time'].isoformat()}",
            "kind": str(RangeKind.ROLLING),
            "label": f"rolling_{window}",
            "session": "",
            "timezone": "UTC",
            "period_start": record["open_time"] - span * window,
            "period_end": record["open_time"],
            "available_from": record["open_time"],
            "expires_at": record["open_time"] + span,
            "high": record["rh"],
            "low": record["rl"],
            "open": record["ro"],
            "close": record["rc"],
            "mid": None,
            "q25": None,
            "q75": None,
            "width": None,
            "width_pct": None,
            "width_atr": None,
        }
        for record in rolled.to_dicts()
    ]
    return _derive(rows)


def build_ranges(
    bars: pl.DataFrame,
    config: RangeConfig,
    *,
    sessions: tuple[SessionSpec, ...] = DEFAULT_SESSIONS,
) -> pl.DataFrame:
    """Every configured reference range for one instrument, in one frame."""
    by_name = {s.name: s for s in sessions}
    parts: list[pl.DataFrame] = []

    if config.daily:
        parts.append(daily_ranges(bars, timezone=config.timezone))
    if config.weekly:
        parts.append(weekly_ranges(bars, timezone=config.timezone))
    if config.monthly:
        parts.append(monthly_ranges(bars, timezone=config.timezone))
    for window in config.n_day_windows:
        parts.append(n_day_ranges(bars, window, timezone=config.timezone))
    for timeframe in config.candle_timeframes:
        parts.append(candle_ranges(bars, timeframe))
    for name in config.sessions:
        if name not in by_name:
            raise SessionError(f"Unknown session {name!r} in RangeConfig.")
        parts.append(session_ranges(bars, by_name[name]))
        for minutes in config.opening_range_minutes:
            parts.append(opening_ranges(bars, by_name[name], minutes))
    for window in config.rolling_windows:
        parts.append(rolling_ranges(bars, window))

    parts = [p for p in parts if p.height > 0]
    if not parts:
        return _empty_ranges()
    combined = pl.concat(parts, how="vertical").sort("available_from", "range_id")
    return _attach_atr_width(combined, bars, config.atr_window)


def _attach_atr_width(ranges: pl.DataFrame, bars: pl.DataFrame, window: int) -> pl.DataFrame:
    """Normalise each range's width by the ATR prevailing when it became usable."""
    atr = bars.select(
        pl.col("open_time"),
        average_true_range(bars, window).alias("_atr"),
    ).drop_nulls()
    if atr.height == 0:
        return ranges
    joined = ranges.sort("available_from").join_asof(
        atr.sort("open_time"),
        left_on="available_from",
        right_on="open_time",
        strategy="backward",
    )
    return joined.with_columns(
        pl.when(pl.col("_atr") > 0)
        .then(pl.col("width") / pl.col("_atr"))
        .otherwise(None)
        .alias("width_atr")
    ).drop("_atr", "open_time")


def active_ranges_at(ranges: pl.DataFrame, moment: datetime) -> pl.DataFrame:
    """The ranges a decision taken at ``moment`` is allowed to see.

    Available and not yet expired. This is the only supported way to read the
    range table from strategy code; filtering by hand is how the shift gets
    forgotten.
    """
    return ranges.filter(
        (pl.col("available_from") <= moment)
        & (pl.col("expires_at").is_null() | (pl.col("expires_at") > moment))
    )


def latest_range(ranges: pl.DataFrame, label: str, moment: datetime) -> dict[str, object] | None:
    """The most recent usable range with a given label, or ``None`` if there is none."""
    candidates = active_ranges_at(ranges, moment).filter(pl.col("label") == label)
    if candidates.height == 0:
        return None
    return candidates.sort("available_from").tail(1).to_dicts()[0]


__all__ = [
    "RANGE_SCHEMA",
    "RangeConfig",
    "RangeError",
    "RangeKind",
    "active_ranges_at",
    "average_true_range",
    "build_ranges",
    "candle_ranges",
    "daily_ranges",
    "latest_range",
    "monthly_ranges",
    "n_day_ranges",
    "opening_ranges",
    "previous_period_ranges",
    "rolling_ranges",
    "session_ranges",
    "weekly_ranges",
]
