"""From bars and levels to a tidy record of what happened and what was traded.

This module is the seam between the mechanical vocabulary in
:mod:`perp_lab.crt.states` and anything that wants to reason about it. It drives
one :class:`~perp_lab.crt.states.LevelTracker` per side of every reference range,
bar by bar, and writes down two things:

* an **event** for every state transition, with the measurement that caused it;
* a **signal** for every setup that survived its entry rule, with the whole
  story attached — which level, how deep the sweep was, what confirmed it, which
  session it happened in, and, deliberately, **which optional conditions this
  configuration did not require**.

That last column is the difference between a reproducible signal and an
explainable one. "Long PDL reclaim" is ambiguous; "long, previous-day low swept
by 18 bps, reclaimed on the next close, entered on that close, retest and
displacement *not* required" is a claim someone else can check.

Causality holds by construction rather than by convention. Bars are consumed in
order, once each; a level enters the loop only when
:func:`~perp_lab.crt.ranges.active_ranges_at` would return it, and leaves when it
expires; a signal is timestamped at the bar whose **close** confirmed it, which
under the repository's execution contract fills at the next bar's open.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any

import polars as pl

from perp_lab.crt.entries import (
    EntryConfig,
    EntryContext,
    EntryEvaluator,
    EntryRule,
    Pivot,
    bps_between,
    confirmed_pivots,
    resolve_entry,
)
from perp_lab.crt.ranges import active_ranges_at, average_true_range
from perp_lab.crt.sessions import (
    SESSION_REGISTRY,
    SessionSpec,
    resolve_session,
    session_windows,
)
from perp_lab.crt.states import (
    TERMINAL_STATES,
    Bar,
    InteractionConfig,
    LevelState,
    LevelTracker,
    Side,
)

UTC_MS = pl.Datetime("ms", "UTC")


class SignalError(ValueError):
    """Raised when the pipeline is asked for something it cannot compute causally."""


class SetupKind(StrEnum):
    """Which way the setup trades once it completes.

    Both values read the same :class:`~perp_lab.crt.states.Side`; only the sign
    differs, which is what lets one implementation serve long and short.
    """

    REVERSAL = "reversal"
    """Price left the range and came back: trade back into the range."""

    CONTINUATION = "continuation"
    """Price left the range and stayed out: trade away from the range."""

    def sign_for(self, side: Side) -> int:
        outward = int(side.sign)
        return -outward if self is SetupKind.REVERSAL else outward


EVENT_SCHEMA: dict[str, pl.DataType] = {
    "symbol": pl.String(),
    "timeframe": pl.String(),
    "open_time": UTC_MS,
    "bar_index": pl.Int64(),
    "session": pl.String(),
    "timezone": pl.String(),
    "label": pl.String(),
    "level_kind": pl.String(),
    "level_side": pl.String(),
    "level": pl.Float64(),
    "range_id": pl.String(),
    "previous_state": pl.String(),
    "state": pl.String(),
    "sweep_depth_bps": pl.Float64(),
    "wick": pl.Float64(),
    "body": pl.Float64(),
    "wick_body_ratio": pl.Float64(),
    "atr": pl.Float64(),
    "volume": pl.Float64(),
    "config_fingerprint": pl.String(),
}

SIGNAL_SCHEMA: dict[str, pl.DataType] = {
    "symbol": pl.String(),
    "timeframe": pl.String(),
    "open_time": UTC_MS,
    "bar_index": pl.Int64(),
    "session": pl.String(),
    "session_day": pl.Date(),
    "session_end": UTC_MS,
    "entry_cutoff": UTC_MS,
    "timezone": pl.String(),
    "range_id": pl.String(),
    "label": pl.String(),
    "level_kind": pl.String(),
    "level_side": pl.String(),
    "level": pl.Float64(),
    "direction": pl.Int8(),
    "setup": pl.String(),
    "trigger_state": pl.String(),
    "trigger_bar": pl.Int64(),
    "trigger_time": UTC_MS,
    "sweep_depth_bps": pl.Float64(),
    "sweep_extreme": pl.Float64(),
    "closes_outside_before": pl.Int64(),
    "first_swept_side": pl.String(),
    "confirmation": pl.String(),
    "bars_waited": pl.Int64(),
    "reference_price": pl.Float64(),
    "atr": pl.Float64(),
    "volume": pl.Float64(),
    "range_high": pl.Float64(),
    "range_low": pl.Float64(),
    "range_mid": pl.Float64(),
    "range_q25": pl.Float64(),
    "range_q75": pl.Float64(),
    "range_open": pl.Float64(),
    "opposite_level": pl.Float64(),
    "conditions_required": pl.String(),
    "conditions_waived": pl.String(),
    "config_fingerprint": pl.String(),
}


@dataclass(frozen=True)
class SignalSpec:
    """Which levels are watched, what completes a setup, and where it may trade.

    Everything a family varies about *pattern recognition* lives here; how the
    resulting trade is managed lives in :mod:`perp_lab.crt.exits`, and how big it
    is lives in :mod:`perp_lab.crt.risk`. Keeping the three apart is what stops a
    risk limit from quietly becoming an entry filter.
    """

    labels: tuple[str, ...]
    """Range labels to track, as produced by :mod:`perp_lab.crt.ranges`."""

    setup: SetupKind = SetupKind.REVERSAL
    sides: tuple[Side, ...] = (Side.LOW, Side.HIGH)
    trigger_states: tuple[LevelState, ...] = (LevelState.RECLAIMED,)
    """The states that complete the setup and hand over to the entry rule."""

    require_sweep: bool = True
    """Whether the level must have been swept, not merely touched."""

    min_sweep_bps: float = 0.0
    """An extra depth floor on top of ``InteractionConfig.sweep_bps``."""

    min_closes_outside: int = 0
    """Closes beyond the level required before the trigger: a real break, not a wick."""

    require_opposite_side_swept: bool = False
    """Both extremes of the same range must have been swept, the opposite one first."""

    session: str | None = None
    """Restrict signals to bars inside this session; tracking is unaffected."""

    respect_entry_cutoff: bool = True
    """Refuse signals after the session's entry cutoff."""

    def __post_init__(self) -> None:
        if not self.labels:
            raise SignalError("A signal spec must name at least one range label.")
        if not self.sides:
            raise SignalError("A signal spec must watch at least one side of the range.")
        if not self.trigger_states:
            raise SignalError("A signal spec must name at least one trigger state.")
        if self.session is not None and self.session not in SESSION_REGISTRY:
            raise SignalError(f"Unknown session {self.session!r}.")

    def sign_for(self, side: Side) -> int:
        return self.setup.sign_for(side)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, StrEnum):
        return str(value)
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, tuple | list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, bool | int | float | str) or value is None:
        return value
    return str(value)


def config_fingerprint(*parts: object) -> str:
    """A short, stable digest of the configuration that produced a row.

    Every event and signal carries it, so two frames can be compared without
    trusting a filename or a memory of which settings were in force.
    """
    payload = json.dumps([_jsonable(p) for p in parts], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class _SessionWindow:
    day: date
    opened: datetime
    closed: datetime
    cutoff: datetime | None


class _SessionIndex:
    """Which occurrence of a session a bar belongs to, resolved once per run."""

    def __init__(self, spec: SessionSpec | None, start: datetime, end: datetime) -> None:
        self.spec = spec
        self.windows: tuple[_SessionWindow, ...] = ()
        if spec is None:
            return
        self.windows = tuple(
            _SessionWindow(
                day=day,
                opened=opened,
                closed=closed,
                cutoff=spec.cutoff_on(day),
            )
            for day, opened, closed in session_windows(spec, start, end)
        )

    def at(self, moment: datetime) -> _SessionWindow | None:
        for window in self.windows:
            if window.opened <= moment < window.closed:
                return window
        return None


@dataclass
class _Watch:
    """One side of one range, plus everything the pattern rules need to remember."""

    row: dict[str, Any]
    side: Side
    tracker: LevelTracker
    sign: int
    closes_outside: int = 0
    swept_at: int | None = None
    evaluator: EntryEvaluator | None = None
    consumed: bool = False

    @property
    def key(self) -> tuple[str, Side]:
        return str(self.row["range_id"]), self.side

    @property
    def level(self) -> float:
        return float(self.tracker.level)

    @property
    def done(self) -> bool:
        pending = self.evaluator is not None and not self.evaluator.settled
        return (self.tracker.finished or self.consumed) and not pending


@dataclass(frozen=True)
class CrtPipelineResult:
    """Everything one pass over the bars produced."""

    events: pl.DataFrame
    signals: pl.DataFrame
    fingerprint: str
    n_levels_tracked: int = 0

    def signal_count(self) -> int:
        return self.signals.height


def bars_from_frame(
    frame: pl.DataFrame, *, atr_window: int = 14, time_column: str = "open_time"
) -> tuple[list[Bar], list[float | None]]:
    """Closed bars in the form the state machine needs, plus their volumes.

    The ATR attached to each bar is the shifted, causal one from
    :func:`~perp_lab.crt.ranges.average_true_range`: it summarises the bars
    strictly before, so a threshold expressed in ATR cannot be met using the very
    bar it is judging.
    """
    required = (time_column, "open", "high", "low", "close")
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise SignalError(f"Bars are missing required columns: {missing}")
    ordered = frame.sort(time_column)
    atr: list[float | None] = (
        [None if v is None else float(v) for v in average_true_range(ordered, atr_window).to_list()]
        if ordered.height > atr_window
        else [None] * ordered.height
    )
    volumes: list[float | None] = (
        [None if v is None else float(v) for v in ordered["volume"].to_list()]
        if "volume" in ordered.columns
        else [None] * ordered.height
    )
    times = ordered[time_column].to_list()
    opens = ordered["open"].to_list()
    highs = ordered["high"].to_list()
    lows = ordered["low"].to_list()
    closes = ordered["close"].to_list()
    bars = [
        Bar(
            index=i,
            open_time=times[i],
            open=float(opens[i]),
            high=float(highs[i]),
            low=float(lows[i]),
            close=float(closes[i]),
            atr=atr[i],
        )
        for i in range(ordered.height)
    ]
    return bars, volumes


def _wick_and_body(bar: Bar, side: Side) -> tuple[float, float, float]:
    """Wick on the level's side, body, and their ratio."""
    body = abs(bar.close - bar.open)
    wick = (
        bar.high - max(bar.open, bar.close)
        if side is Side.HIGH
        else min(bar.open, bar.close) - bar.low
    )
    ratio = (float("inf") if wick > 0 else 0.0) if body <= 0 else wick / body
    return wick, body, ratio


def _finite(value: float) -> float | None:
    """Polars has no infinity in a Float64 column we want to reason about."""
    return None if value == float("inf") else value


def run_crt_pipeline(
    bars: pl.DataFrame,
    ranges: pl.DataFrame,
    *,
    spec: SignalSpec,
    interaction: InteractionConfig,
    entry: EntryConfig,
    symbol: str = "",
    timeframe: str = "",
    atr_window: int = 14,
    time_column: str = "open_time",
) -> CrtPipelineResult:
    """Drive every level through the data and record events and signals.

    The loop is deliberately explicit. A vectorised version would have to encode
    "a reclaim only counts if a sweep preceded it within a bar budget, unless the
    opposite extreme was swept first" as window functions, and nobody could
    check the result. The cost is one Python pass over the bars per run; the
    benefit is that the ordering rules are readable.
    """
    fingerprint = config_fingerprint(spec, interaction, entry)
    empty = CrtPipelineResult(
        events=pl.DataFrame(schema=EVENT_SCHEMA),
        signals=pl.DataFrame(schema=SIGNAL_SCHEMA),
        fingerprint=fingerprint,
    )
    if bars.height == 0:
        return empty

    bar_list, volumes = bars_from_frame(bars, atr_window=atr_window, time_column=time_column)
    if not bar_list:
        return empty

    session_spec = resolve_session(spec.session) if spec.session else None
    sessions = _SessionIndex(session_spec, bar_list[0].open_time, bar_list[-1].open_time)

    pivots: tuple[Pivot, ...] = ()
    if entry.rule is EntryRule.STRUCTURE_BREAK:
        pivots = confirmed_pivots(bar_list, entry.pivot_span)

    usable = (
        ranges.filter(pl.col("label").is_in(list(spec.labels))).sort("available_from", "range_id")
        if ranges.height
        else ranges
    )
    range_rows: list[dict[str, Any]] = usable.to_dicts() if usable.height else []

    events: list[dict[str, Any]] = []
    signals: list[dict[str, Any]] = []
    active: dict[tuple[str, Side], _Watch] = {}
    seen: set[tuple[str, Side]] = set()
    swept_first: dict[str, Side] = {}
    cursor = 0
    n_levels = 0

    for bar in bar_list:
        moment = bar.open_time

        # A level joins the loop exactly when active_ranges_at would return it.
        # The cursor is an incremental restatement of that predicate, not a
        # second one: ranges are ordered by availability, so everything at or
        # before ``moment`` has become usable, and expiry is checked below.
        while cursor < len(range_rows) and range_rows[cursor]["available_from"] <= moment:
            row = range_rows[cursor]
            cursor += 1
            for side in spec.sides:
                key = (str(row["range_id"]), side)
                if key in seen:
                    continue
                seen.add(key)
                level = float(row["high"] if side is Side.HIGH else row["low"])
                expires = row.get("expires_at")
                if expires is not None and expires <= moment:
                    continue
                active[key] = _Watch(
                    row=row,
                    side=side,
                    sign=spec.sign_for(side),
                    tracker=LevelTracker(
                        range_id=str(row["range_id"]),
                        label=str(row["label"]),
                        side=side,
                        level=level,
                        available_from=row["available_from"],
                        config=interaction,
                        expires_at=expires,
                    ),
                )
                n_levels += 1

        for key, watch in list(active.items()):
            _advance(
                watch,
                bar,
                volume=volumes[bar.index],
                spec=spec,
                entry=entry,
                pivots=pivots,
                sessions=sessions,
                swept_first=swept_first,
                symbol=symbol,
                timeframe=timeframe,
                fingerprint=fingerprint,
                events=events,
                signals=signals,
            )
            if watch.done:
                del active[key]

    return CrtPipelineResult(
        events=pl.DataFrame(events, schema=EVENT_SCHEMA)
        if events
        else pl.DataFrame(schema=EVENT_SCHEMA),
        signals=pl.DataFrame(signals, schema=SIGNAL_SCHEMA)
        if signals
        else pl.DataFrame(schema=SIGNAL_SCHEMA),
        fingerprint=fingerprint,
        n_levels_tracked=n_levels,
    )


def _advance(
    watch: _Watch,
    bar: Bar,
    *,
    volume: float | None,
    spec: SignalSpec,
    entry: EntryConfig,
    pivots: Sequence[Pivot],
    sessions: _SessionIndex,
    swept_first: dict[str, Side],
    symbol: str,
    timeframe: str,
    fingerprint: str,
    events: list[dict[str, Any]],
    signals: list[dict[str, Any]],
) -> None:
    """One level, one bar: transitions first, then the entry rule."""
    before = len(watch.tracker.transitions)
    if not watch.tracker.finished:
        watch.tracker.update(bar)
    new_transitions = watch.tracker.transitions[before:]

    row = watch.row
    wick, body, ratio = _wick_and_body(bar, watch.side)
    for transition in new_transitions:
        events.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "open_time": bar.open_time,
                "bar_index": bar.index,
                "session": spec.session or str(row.get("session") or ""),
                "timezone": str(row.get("timezone") or ""),
                "label": str(row["label"]),
                "level_kind": str(row["kind"]),
                "level_side": str(watch.side),
                "level": watch.level,
                "range_id": str(row["range_id"]),
                "previous_state": str(transition.previous),
                "state": str(transition.state),
                "sweep_depth_bps": float(transition.depth_bps),
                "wick": wick,
                "body": body,
                "wick_body_ratio": _finite(ratio),
                "atr": bar.atr,
                "volume": volume,
                "config_fingerprint": fingerprint,
            }
        )
        if transition.state is LevelState.SWEPT:
            watch.swept_at = bar.index
            swept_first.setdefault(str(row["range_id"]), watch.side)

    # Closes beyond the level, counted here rather than read out of the tracker:
    # the tracker resets its own counter whenever price steps back inside, which
    # is right for acceptance and wrong for "was this ever a real break?".
    if watch.side.sign * (bar.close - watch.level) > 0:
        watch.closes_outside += 1

    # Structure-break entries need confirmed swing points. Early in a series
    # there are none, so no setup can be entered yet; that is a warm-up, not a
    # misconfiguration, and it must not raise.
    enterable = entry.rule is not EntryRule.STRUCTURE_BREAK or bool(pivots)
    if watch.evaluator is None and enterable:
        for transition in new_transitions:
            if transition.state in spec.trigger_states and _preconditions_met(
                watch, spec, swept_first
            ):
                watch.evaluator = resolve_entry(
                    entry,
                    EntryContext(
                        range_id=str(row["range_id"]),
                        label=str(row["label"]),
                        side=watch.side,
                        sign=watch.sign,
                        level=watch.level,
                        trigger_bar=bar.index,
                        trigger_at=bar.open_time,
                        trigger_state=str(transition.state),
                    ),
                    pivots=pivots,
                )
                break

    evaluator = watch.evaluator
    if evaluator is None or evaluator.settled:
        return

    # A hypothesis that has already failed must not still be entered on a late
    # retest, so terminal states other than the trigger cancel the pending entry.
    if watch.tracker.state in TERMINAL_STATES and watch.tracker.state not in spec.trigger_states:
        evaluator.cancel()
        return

    confirmation = evaluator.observe(bar)
    if confirmation is None:
        return

    window = sessions.at(bar.open_time)
    if spec.session is not None:
        if window is None:
            watch.consumed = True
            return
        if (
            spec.respect_entry_cutoff
            and window.cutoff is not None
            and bar.open_time >= window.cutoff
        ):
            watch.consumed = True
            return

    context = evaluator.context
    high = float(row["high"])
    low = float(row["low"])
    opposite = low if watch.side is Side.HIGH else high
    signals.append(
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "open_time": bar.open_time,
            "bar_index": bar.index,
            "session": spec.session or str(row.get("session") or ""),
            "session_day": window.day if window else None,
            "session_end": window.closed if window else None,
            "entry_cutoff": window.cutoff if window else None,
            "timezone": str(row.get("timezone") or ""),
            "range_id": str(row["range_id"]),
            "label": str(row["label"]),
            "level_kind": str(row["kind"]),
            "level_side": str(watch.side),
            "level": watch.level,
            "direction": watch.sign,
            "setup": str(spec.setup),
            "trigger_state": context.trigger_state,
            "trigger_bar": context.trigger_bar,
            "trigger_time": context.trigger_at,
            "sweep_depth_bps": float(watch.tracker.max_depth_bps),
            "sweep_extreme": watch.tracker.sweep_extreme,
            "closes_outside_before": watch.closes_outside,
            "first_swept_side": str(swept_first.get(str(row["range_id"]), "")),
            "confirmation": str(confirmation.rule),
            "bars_waited": confirmation.bars_waited,
            "reference_price": confirmation.reference_price,
            "atr": bar.atr,
            "volume": volume,
            "range_high": high,
            "range_low": low,
            "range_mid": row.get("mid"),
            "range_q25": row.get("q25"),
            "range_q75": row.get("q75"),
            "range_open": row.get("open"),
            "opposite_level": opposite,
            "conditions_required": ",".join(confirmation.conditions_required),
            "conditions_waived": ",".join(confirmation.conditions_waived),
            "config_fingerprint": fingerprint,
        }
    )
    # One level, one signal. Consuming it here is the no-duplicate guarantee:
    # the watch is retired and never rebuilt, because its key stays in ``seen``.
    watch.consumed = True


def _preconditions_met(watch: _Watch, spec: SignalSpec, swept_first: Mapping[str, Side]) -> bool:
    """The pattern requirements a trigger state alone does not express."""
    if spec.require_sweep and watch.tracker.sweep_bar is None:
        return False
    if watch.tracker.max_depth_bps < spec.min_sweep_bps:
        return False
    if watch.closes_outside < spec.min_closes_outside:
        return False
    if spec.require_opposite_side_swept:
        first = swept_first.get(watch.tracker.range_id)
        if first is None or first is watch.side:
            return False
    return True


def explain_signal(row: Mapping[str, Any]) -> str:
    """One sentence stating exactly what fired and what was not required.

    Written for a reader auditing a trade list months later, who needs to know
    both what the rule demanded and what it let pass.
    """
    direction = "long" if int(row["direction"]) > 0 else "short"
    depth = float(row["sweep_depth_bps"])
    waived = str(row["conditions_waived"]) or "nothing"
    session = str(row["session"]) or "no session filter"
    return (
        f"{direction} {row['setup']} on {row['label']} "
        f"({row['level_side']} at {float(row['level']):.2f}), swept {depth:.1f} bps, "
        f"{row['trigger_state']} then confirmed by {row['confirmation']} "
        f"{int(row['bars_waited'])} bar(s) later at {float(row['reference_price']):.2f}; "
        f"session: {session}; not required by this configuration: {waived}"
    )


def sweep_depth_bps(level: float, extreme: float) -> float:
    """Convenience wrapper so callers do not re-derive the basis-point basis."""
    return bps_between(extreme - level, level)


@dataclass(frozen=True)
class SignalSummary:
    """Counts a reader needs before trusting anything downstream."""

    n_events: int
    n_signals: int
    n_levels_tracked: int
    by_state: dict[str, int] = field(default_factory=dict)


def summarise(result: CrtPipelineResult) -> SignalSummary:
    by_state: dict[str, int] = {}
    if result.events.height:
        counts = result.events.group_by("state").len().sort("state")
        by_state = {str(r["state"]): int(r["len"]) for r in counts.to_dicts()}
    return SignalSummary(
        n_events=result.events.height,
        n_signals=result.signals.height,
        n_levels_tracked=result.n_levels_tracked,
        by_state=by_state,
    )


def levels_readable_at(ranges: pl.DataFrame, moment: datetime) -> set[str]:
    """The range ids a decision at ``moment`` may read, via the sanctioned filter."""
    return set(active_ranges_at(ranges, moment)["range_id"].to_list())


__all__ = [
    "EVENT_SCHEMA",
    "SIGNAL_SCHEMA",
    "CrtPipelineResult",
    "SetupKind",
    "SignalError",
    "SignalSpec",
    "SignalSummary",
    "bars_from_frame",
    "config_fingerprint",
    "explain_signal",
    "levels_readable_at",
    "run_crt_pipeline",
    "summarise",
    "sweep_depth_bps",
]
