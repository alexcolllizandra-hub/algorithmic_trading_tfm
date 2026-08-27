"""Where the trade is wrong, where it is finished, and what to do in between.

An entry rule without an exit rule is not a strategy, and "I'd manage it" is not
an exit rule. Everything a discretionary trader decides while a position is open
is enumerated here as configuration: which price proves the idea wrong, which
prices pay, whether to scale out, whether to move the stop, and when to give up
on the clock.

Three things in this module deserve to be read before it is trusted.

**Refusal is part of the plan.** A setup whose first target does not clear the
round-trip cost by a configured margin is refused *before* entry, by
:func:`plan_trade`. A strategy that takes every signal and loses to fees is not
evidence about the signal.

**Intrabar order is unknowable.** With one timeframe and no tick data, a bar
whose range contains both the stop and the target cannot say which came first.
The policy is therefore fixed at the pessimistic reading — the stop fills —
*and the trade is flagged*, because the number to report is not the
result but how much of the result rests on an assumption. See
:func:`ambiguity_metrics`.

**Prices here are modelled trigger levels, not fills.** The authoritative profit
and loss comes from :mod:`perp_lab.backtesting.engine`, which fills the position
change at the next bar's open. This module decides *when* the position changes;
it never claims the change happened at the stop price. The two "targets" from
the catalogue that carry no price — the time-based exit and the session-end
exit — live in the management section for the same reason.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from itertools import pairwise

from perp_lab.crt.entries import bps_between, bps_to_price
from perp_lab.crt.states import Bar


class ExitError(ValueError):
    """Raised when an exit configuration cannot describe a coherent trade."""


class StopKind(StrEnum):
    """Which price proves the idea wrong."""

    WICK_EXTREME = "wick_extreme"
    """Beyond the extreme of the sweep that created the setup."""

    RANGE_EXTREME = "range_extreme"
    """Beyond the level itself."""

    ATR_DISTANCE = "atr_distance"
    """A volatility-scaled distance from the entry reference."""

    FIXED_PCT = "fixed_pct"
    """A fixed percentage of the entry reference."""

    STRUCTURAL = "structural"
    """Beyond the confirmed swing point the setup depends on."""


class TargetKind(StrEnum):
    """Which prices pay. Every one of these is a level someone else is watching."""

    RANGE_MID = "range_mid"
    RANGE_Q25 = "range_q25"
    RANGE_Q75 = "range_q75"
    OPPOSITE_EXTREME = "opposite_extreme"
    DAILY_OPEN = "daily_open"
    SESSION_OPEN = "session_open"
    PREVIOUS_DAY_HIGH = "previous_day_high"
    PREVIOUS_DAY_LOW = "previous_day_low"
    SESSION_HIGH = "session_high"
    SESSION_LOW = "session_low"
    NEXT_LIQUIDITY = "next_liquidity"
    R_MULTIPLE = "r_multiple"
    ATR_MULTIPLE = "atr_multiple"


class TrailingKind(StrEnum):
    ATR = "atr"
    PRIOR_EXTREME = "prior_extreme"


class ExitReason(StrEnum):
    """Why the position changed size."""

    TARGET = "target"
    STOP = "stop"
    BREAK_EVEN = "break_even"
    TRAILING_STOP = "trailing_stop"
    TIME_EXIT = "time_exit"
    SESSION_END = "session_end"
    END_OF_DATA = "end_of_data"


class IntrabarPolicy(StrEnum):
    """How a bar containing both the stop and a target is resolved.

    Single member by design: with one timeframe there is no
    defensible optimistic option, so the choice is recorded rather than offered.
    A finer timeframe would justify adding one, and the enum is where it would go.
    """

    STOP_FIRST = "stop_first"


@dataclass(frozen=True)
class TargetSpec:
    """One objective and the share of the position it closes."""

    kind: TargetKind
    fraction: float = 1.0
    r_multiple: float = 2.0
    atr_multiple: float = 2.0

    def __post_init__(self) -> None:
        if not 0.0 < self.fraction <= 1.0:
            raise ExitError("A target must close a positive share of the position, at most all.")
        if self.kind is TargetKind.R_MULTIPLE and self.r_multiple <= 0:
            raise ExitError("An R-multiple target needs a positive multiple.")
        if self.kind is TargetKind.ATR_MULTIPLE and self.atr_multiple <= 0:
            raise ExitError("An ATR target needs a positive multiple.")


@dataclass(frozen=True)
class TrailingSpec:
    kind: TrailingKind = TrailingKind.ATR
    atr_multiple: float = 1.5
    lookback_bars: int = 3

    def __post_init__(self) -> None:
        if self.atr_multiple <= 0:
            raise ExitError("A trailing ATR distance must be positive.")
        if self.lookback_bars < 1:
            raise ExitError("A trailing extreme needs at least one bar to look back at.")


@dataclass(frozen=True)
class ExitConfig:
    """The full management plan, fixed before the trade is taken."""

    stop: StopKind = StopKind.WICK_EXTREME
    stop_buffer_bps: float = 5.0
    stop_atr_multiple: float = 1.0
    stop_pct: float = 0.5
    targets: tuple[TargetSpec, ...] = (TargetSpec(TargetKind.RANGE_MID),)
    move_to_breakeven_after_first_target: bool = False
    trailing: TrailingSpec | None = None
    time_stop_bars: int | None = None
    """The time-based exit: give up after this many bars of exposure."""

    close_at_window_end: bool = True
    """The session-end exit: never carry a session trade past its window."""

    min_net_reward_risk: float = 1.0
    min_net_profit_bps: float = 0.0
    cost_bps_per_side: float = 5.0
    intrabar_policy: IntrabarPolicy = IntrabarPolicy.STOP_FIRST

    def __post_init__(self) -> None:
        if not 1 <= len(self.targets) <= 3:
            raise ExitError("A trade takes one, two or three targets; nothing else is managed.")
        total = sum(t.fraction for t in self.targets)
        if abs(total - 1.0) > 1e-9:
            raise ExitError(f"Target fractions must close the whole position; they sum to {total}.")
        if self.time_stop_bars is not None and self.time_stop_bars < 1:
            raise ExitError("A time exit must allow at least one bar of exposure.")
        if self.cost_bps_per_side < 0:
            raise ExitError("Costs cannot be negative.")
        if self.move_to_breakeven_after_first_target and len(self.targets) < 2:
            raise ExitError(
                "Moving to break-even after the first target is meaningless with a single "
                "target: the position is already closed."
            )

    @property
    def round_trip_bps(self) -> float:
        return 2.0 * self.cost_bps_per_side


@dataclass(frozen=True)
class TradeReferences:
    """Every price the plan may quote, resolved by the caller from usable levels.

    Passed as one object so that a family adding a new objective cannot silently
    receive ``None`` from a positional argument it forgot to fill in: an
    unresolvable target refuses the trade instead.
    """

    level: float
    range_high: float
    range_low: float
    range_mid: float | None = None
    range_q25: float | None = None
    range_q75: float | None = None
    range_open: float | None = None
    opposite_level: float | None = None
    sweep_extreme: float | None = None
    structural_level: float | None = None
    atr: float | None = None
    daily_open: float | None = None
    session_open: float | None = None
    previous_day_high: float | None = None
    previous_day_low: float | None = None
    session_high: float | None = None
    session_low: float | None = None
    next_liquidity_above: float | None = None
    next_liquidity_below: float | None = None


@dataclass(frozen=True)
class PlannedTarget:
    kind: TargetKind
    price: float
    fraction: float


@dataclass(frozen=True)
class TradePlan:
    """A complete, pre-trade description of the bet, including whether to take it."""

    sign: int
    entry_price: float
    stop_price: float
    targets: tuple[PlannedTarget, ...]
    risk_per_unit: float
    gross_reward_risk: float
    net_reward_risk: float
    net_profit_bps: float
    cost_per_unit: float
    accepted: bool
    refusal: str | None = None
    config: ExitConfig | None = None

    @property
    def stop_distance_bps(self) -> float:
        return bps_between(self.risk_per_unit, self.entry_price)

    def describe(self) -> str:
        verdict = "accepted" if self.accepted else f"refused ({self.refusal})"
        first = self.targets[0].price if self.targets else float("nan")
        return (
            f"{'long' if self.sign > 0 else 'short'} from {self.entry_price:.2f}, "
            f"stop {self.stop_price:.2f} ({self.stop_distance_bps:.1f} bps), "
            f"first target {first:.2f}, net R:R {self.net_reward_risk:.2f} — {verdict}"
        )


def _beyond(sign: int, price: float, reference: float) -> bool:
    """``price`` lies in the trade's favour relative to ``reference``."""
    return sign * (price - reference) > 0


def stop_price(sign: int, entry_price: float, refs: TradeReferences, config: ExitConfig) -> float:
    """The price that proves the idea wrong, or ``nan`` when it cannot be placed.

    ``nan`` rather than an exception: a structural stop with no confirmed pivot
    yet is a normal early-sample condition, and the caller turns it into a
    refusal with a reason attached.
    """
    buffer = bps_to_price(entry_price, config.stop_buffer_bps)
    if config.stop is StopKind.WICK_EXTREME:
        anchor = refs.sweep_extreme
    elif config.stop is StopKind.RANGE_EXTREME:
        anchor = refs.level
    elif config.stop is StopKind.STRUCTURAL:
        anchor = refs.structural_level
    elif config.stop is StopKind.ATR_DISTANCE:
        if not refs.atr:
            return float("nan")
        return entry_price - sign * config.stop_atr_multiple * refs.atr
    else:
        return entry_price * (1.0 - sign * config.stop_pct / 100.0)

    if anchor is None:
        return float("nan")
    return anchor - sign * buffer


def target_price(
    spec: TargetSpec,
    *,
    sign: int,
    entry_price: float,
    risk_per_unit: float,
    refs: TradeReferences,
) -> float | None:
    """Resolve one objective to a price, or ``None`` if the reference is absent."""
    kind = spec.kind
    if kind is TargetKind.R_MULTIPLE:
        return entry_price + sign * spec.r_multiple * risk_per_unit
    if kind is TargetKind.ATR_MULTIPLE:
        return None if not refs.atr else entry_price + sign * spec.atr_multiple * refs.atr
    if kind is TargetKind.NEXT_LIQUIDITY:
        return refs.next_liquidity_above if sign > 0 else refs.next_liquidity_below
    lookup: dict[TargetKind, float | None] = {
        TargetKind.RANGE_MID: refs.range_mid,
        TargetKind.RANGE_Q25: refs.range_q25,
        TargetKind.RANGE_Q75: refs.range_q75,
        TargetKind.OPPOSITE_EXTREME: refs.opposite_level,
        TargetKind.DAILY_OPEN: refs.daily_open,
        TargetKind.SESSION_OPEN: refs.session_open,
        TargetKind.PREVIOUS_DAY_HIGH: refs.previous_day_high,
        TargetKind.PREVIOUS_DAY_LOW: refs.previous_day_low,
        TargetKind.SESSION_HIGH: refs.session_high,
        TargetKind.SESSION_LOW: refs.session_low,
    }
    return lookup[kind]


def _refused(sign: int, entry_price: float, stop: float, reason: str) -> TradePlan:
    risk = 0.0 if math.isnan(stop) else abs(entry_price - stop)
    return TradePlan(
        sign=sign,
        entry_price=entry_price,
        stop_price=stop,
        targets=(),
        risk_per_unit=risk,
        gross_reward_risk=0.0,
        net_reward_risk=0.0,
        net_profit_bps=0.0,
        cost_per_unit=0.0,
        accepted=False,
        refusal=reason,
    )


def plan_trade(
    *,
    sign: int,
    entry_price: float,
    refs: TradeReferences,
    config: ExitConfig,
) -> TradePlan:
    """Price the whole trade before taking it, and refuse it if it does not pay.

    The reward:risk test is applied **net of a round trip of costs** on both
    sides of the ratio: the reward loses a round trip, and the risk gains one.
    Testing gross reward:risk and subtracting costs afterwards is the standard
    way an unprofitable rule looks acceptable at the planning stage.
    """
    if sign not in (-1, 1):
        raise ExitError("sign must be -1 (short) or +1 (long).")
    if entry_price <= 0:
        raise ExitError("entry_price must be positive.")

    stop = stop_price(sign, entry_price, refs, config)
    if math.isnan(stop):  # The anchor this stop kind needs does not exist yet.
        return _refused(sign, entry_price, stop, f"no reference for a {config.stop} stop")
    if _beyond(sign, stop, entry_price) or stop == entry_price:
        return _refused(sign, entry_price, stop, "stop is not on the losing side of the entry")

    risk = abs(entry_price - stop)
    cost = bps_to_price(entry_price, config.round_trip_bps)

    planned: list[PlannedTarget] = []
    for spec in config.targets:
        price = target_price(
            spec, sign=sign, entry_price=entry_price, risk_per_unit=risk, refs=refs
        )
        if price is None:
            return _refused(sign, entry_price, stop, f"no reference for the {spec.kind} target")
        if not _beyond(sign, price, entry_price):
            return _refused(sign, entry_price, stop, f"{spec.kind} target is behind the entry")
        planned.append(PlannedTarget(kind=spec.kind, price=price, fraction=spec.fraction))

    # Targets must be ordered outward, or "the first target" is not the first
    # price reached and every partial-exit calculation below is wrong.
    for earlier, later in pairwise(planned):
        if not _beyond(sign, later.price, earlier.price):
            return _refused(sign, entry_price, stop, "targets are not ordered away from the entry")

    first = planned[0]
    gross_reward = abs(first.price - entry_price)
    net_reward = gross_reward - cost
    net_risk = risk + cost
    net_rr = net_reward / net_risk if net_risk > 0 else 0.0
    net_profit_bps = bps_between(net_reward, entry_price) * (1.0 if net_reward >= 0 else -1.0)

    plan = TradePlan(
        sign=sign,
        entry_price=entry_price,
        stop_price=stop,
        targets=tuple(planned),
        risk_per_unit=risk,
        gross_reward_risk=gross_reward / risk if risk > 0 else 0.0,
        net_reward_risk=net_rr,
        net_profit_bps=net_profit_bps,
        cost_per_unit=cost,
        accepted=True,
        config=config,
    )
    if net_reward <= 0:
        return _reject(plan, "the first target does not cover the round-trip cost")
    if net_profit_bps < config.min_net_profit_bps:
        return _reject(plan, "net profit to the first target is below the minimum")
    if net_rr < config.min_net_reward_risk:
        return _reject(plan, "net reward:risk is below the minimum")
    return plan


def _reject(plan: TradePlan, reason: str) -> TradePlan:
    """Keep every number that was computed; only the verdict changes.

    A refusal with the arithmetic attached can be audited; a bare ``None``
    cannot, and refusals are as much a result as fills.
    """
    return TradePlan(
        sign=plan.sign,
        entry_price=plan.entry_price,
        stop_price=plan.stop_price,
        targets=plan.targets,
        risk_per_unit=plan.risk_per_unit,
        gross_reward_risk=plan.gross_reward_risk,
        net_reward_risk=plan.net_reward_risk,
        net_profit_bps=plan.net_profit_bps,
        cost_per_unit=plan.cost_per_unit,
        accepted=False,
        refusal=reason,
        config=plan.config,
    )


@dataclass(frozen=True)
class Fill:
    """One change in position size, at the level that triggered it."""

    bar_index: int
    at: datetime
    fraction: float
    level: float
    reason: ExitReason
    ambiguous: bool = False


@dataclass(frozen=True)
class TradeOutcome:
    """What the plan did, bar by bar, on closed-bar information only."""

    plan: TradePlan
    entry_bar: int
    entry_time: datetime
    fills: tuple[Fill, ...] = ()
    exposure: tuple[tuple[int, float], ...] = ()
    """``(bar_index, share still open after that bar)`` — the strategy's side path."""

    ambiguous_bars: tuple[int, ...] = ()
    bars_held: int = 0
    closed: bool = True
    """True when a rule closed the trade; False when the sample simply ran out."""

    moved_to_breakeven: bool = False
    modelled_r: float = 0.0
    """Result in R at the *trigger levels*, for auditing the plan — not a fill price."""

    @property
    def ambiguous(self) -> bool:
        return bool(self.ambiguous_bars)

    @property
    def exit_reason(self) -> ExitReason | None:
        return self.fills[-1].reason if self.fills else None

    @property
    def exit_bar(self) -> int | None:
        return self.fills[-1].bar_index if self.fills else None


_DUST = 1e-9
"""Below this share the position is closed.

Three partials of a third each leave a residue of about 1e-16, and treating that
residue as an open position produces a phantom fill and reports the trade as
never closed. The tolerance is far below any size the sizing rules can produce.
"""


def _touches(sign: int, bar: Bar, price: float, *, favourable: bool) -> bool:
    """Whether the bar's range reached ``price``.

    ``favourable`` selects the extreme that matters: a long's target is reached
    by the high, its stop by the low.
    """
    if (sign > 0) == favourable:
        return bar.high >= price
    return bar.low <= price


def simulate_trade(
    plan: TradePlan,
    bars: Sequence[Bar],
    *,
    config: ExitConfig,
    entry_bar_index: int,
    window_end: datetime | None = None,
) -> TradeOutcome:
    """Walk the trade forward through closed bars and record every size change.

    ``entry_bar_index`` is the first bar of *exposure* — under next-bar
    execution, the bar after the one whose close confirmed the signal. The stop
    is live from that bar: a position can be stopped out on the bar it was
    opened on, and pretending otherwise flatters every fast loser.
    """
    if not plan.accepted:
        raise ExitError("A refused plan must not be simulated; that is what refusing means.")
    if plan.config is not None and plan.config is not config:
        raise ExitError("simulate_trade received a different ExitConfig from the one planned.")
    exposed = [bar for bar in bars if bar.index >= entry_bar_index]
    if not exposed:
        raise ExitError(
            f"No bar at or after index {entry_bar_index}: a signal on the last bar of the "
            "sample has no execution bar and must be dropped, not simulated."
        )

    sign = plan.sign
    stop = plan.stop_price
    remaining = 1.0
    target_index = 0
    fills: list[Fill] = []
    exposure: list[tuple[int, float]] = []
    ambiguous: list[int] = []
    history: list[Bar] = []
    moved_to_breakeven = False
    entry_time = exposed[0].open_time
    stop_reason = ExitReason.STOP
    bars_held = 0
    closed = False

    for bar in exposed:
        bars_held += 1
        history.append(bar)

        hit_stop = _touches(sign, bar, stop, favourable=False)
        next_target = plan.targets[target_index] if target_index < len(plan.targets) else None
        hit_target = next_target is not None and _touches(
            sign, bar, next_target.price, favourable=True
        )

        if hit_stop and hit_target:
            # Both inside one bar and no finer data to order them: the stop wins
            # and the trade is marked, so the reader can size the assumption.
            ambiguous.append(bar.index)

        if hit_stop:
            fills.append(
                Fill(
                    bar_index=bar.index,
                    at=bar.open_time,
                    fraction=remaining,
                    level=stop,
                    reason=stop_reason,
                    ambiguous=hit_target,
                )
            )
            remaining = 0.0
            exposure.append((bar.index, 0.0))
            closed = True
            break

        while (
            target_index < len(plan.targets)
            and _touches(sign, bar, plan.targets[target_index].price, favourable=True)
            and remaining > 0
        ):
            hit = plan.targets[target_index]
            taken = min(hit.fraction, remaining)
            fills.append(
                Fill(
                    bar_index=bar.index,
                    at=bar.open_time,
                    fraction=taken,
                    level=hit.price,
                    reason=ExitReason.TARGET,
                )
            )
            remaining = max(remaining - taken, 0.0)
            if remaining <= _DUST:
                remaining = 0.0
            target_index += 1
            if target_index == 1 and config.move_to_breakeven_after_first_target and remaining > 0:
                stop = plan.entry_price
                stop_reason = ExitReason.BREAK_EVEN
                moved_to_breakeven = True

        if remaining <= 0:
            exposure.append((bar.index, 0.0))
            closed = True
            break

        if config.trailing is not None:
            trailed = _trailing_stop(sign, history, config.trailing)
            if trailed is not None and sign * (trailed - stop) > 0:
                stop = trailed
                if not moved_to_breakeven:
                    stop_reason = ExitReason.TRAILING_STOP

        if config.time_stop_bars is not None and bars_held >= config.time_stop_bars:
            fills.append(
                Fill(
                    bar_index=bar.index,
                    at=bar.open_time,
                    fraction=remaining,
                    level=bar.close,
                    reason=ExitReason.TIME_EXIT,
                )
            )
            remaining = 0.0
            exposure.append((bar.index, 0.0))
            closed = True
            break

        if config.close_at_window_end and window_end is not None and bar.open_time >= window_end:
            fills.append(
                Fill(
                    bar_index=bar.index,
                    at=bar.open_time,
                    fraction=remaining,
                    level=bar.close,
                    reason=ExitReason.SESSION_END,
                )
            )
            remaining = 0.0
            exposure.append((bar.index, 0.0))
            closed = True
            break

        exposure.append((bar.index, remaining))

    if not closed and exposure:
        last = history[-1]
        fills.append(
            Fill(
                bar_index=last.index,
                at=last.open_time,
                fraction=remaining,
                level=last.close,
                reason=ExitReason.END_OF_DATA,
            )
        )
        exposure[-1] = (last.index, 0.0)

    modelled = 0.0
    if plan.risk_per_unit > 0:
        modelled = sum(
            f.fraction * sign * (f.level - plan.entry_price) / plan.risk_per_unit for f in fills
        )

    return TradeOutcome(
        plan=plan,
        entry_bar=entry_bar_index,
        entry_time=entry_time,
        fills=tuple(fills),
        exposure=tuple(exposure),
        ambiguous_bars=tuple(ambiguous),
        bars_held=bars_held,
        closed=closed,
        moved_to_breakeven=moved_to_breakeven,
        modelled_r=modelled,
    )


def _trailing_stop(sign: int, history: Sequence[Bar], spec: TrailingSpec) -> float | None:
    """A stop derived from bars that have already closed, never from this one's future."""
    last = history[-1]
    if spec.kind is TrailingKind.ATR:
        if not last.atr:
            return None
        return last.close - sign * spec.atr_multiple * last.atr
    window = history[-spec.lookback_bars :]
    return min(b.low for b in window) if sign > 0 else max(b.high for b in window)


@dataclass(frozen=True)
class AmbiguityReport:
    n_trades: int
    n_ambiguous_trades: int
    n_ambiguous_bars: int
    ambiguous_trade_rate: float
    policy: IntrabarPolicy = IntrabarPolicy.STOP_FIRST
    detail: dict[str, float] = field(default_factory=dict)


def ambiguity_metrics(outcomes: Sequence[TradeOutcome]) -> AmbiguityReport:
    """How much of the result rests on the intrabar assumption.

    Reported alongside performance, not instead of it: a strategy whose trades
    are mostly ambiguous has not been measured, it has been assumed.
    """
    n = len(outcomes)
    affected = [o for o in outcomes if o.ambiguous]
    bars = sum(len(o.ambiguous_bars) for o in outcomes)
    return AmbiguityReport(
        n_trades=n,
        n_ambiguous_trades=len(affected),
        n_ambiguous_bars=bars,
        ambiguous_trade_rate=(len(affected) / n) if n else 0.0,
    )


__all__ = [
    "AmbiguityReport",
    "ExitConfig",
    "ExitError",
    "ExitReason",
    "Fill",
    "IntrabarPolicy",
    "PlannedTarget",
    "StopKind",
    "TargetKind",
    "TargetSpec",
    "TradeOutcome",
    "TradePlan",
    "TradeReferences",
    "TrailingKind",
    "TrailingSpec",
    "ambiguity_metrics",
    "plan_trade",
    "simulate_trade",
    "stop_price",
    "target_price",
]
