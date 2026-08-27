"""When a completed setup is allowed to become a position.

A sweep-and-reclaim tells you *that* something happened; it does not tell you
where to get in. Discretionary traders resolve that with taste — "I'd wait for
the retest here, but this one I'd take immediately" — and taste cannot be
backtested, because the choice is made after the outcome is visible.

So the choice is made a parameter. Each rule below is a complete, mechanical
answer to "which closed bar turns this setup into a position", they are mutually
exclusive, and a run records which one was used. Comparing them is then a
legitimate experiment rather than a story told afterwards.

Two constraints shape every rule.

**Execution.** The repository fills a decision taken at the close of bar *t* at
the open of bar *t+1* (see :mod:`perp_lab.backtesting.engine`). No rule here can
therefore fill at a closing price, and none pretends to. What a rule chooses is
the *confirming bar*; the fill follows from the engine's contract.

**Pivots do not repaint.** :data:`EntryRule.STRUCTURE_BREAK` needs swing points,
and a swing point needs bars on both sides of it. A pivot with ``span`` bars
either side is therefore unknown until ``span`` bars later, and
:func:`confirmed_pivots` timestamps it accordingly. Reading a pivot at the bar
that forms it is the single most common way this family of models leaks.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from perp_lab.crt.states import Bar, Side


class EntryError(ValueError):
    """Raised when an entry rule is configured in a way that cannot fire."""


# -- shared geometry --------------------------------------------------------- #
# These live in the lowest-level of the new CRT modules so that entries, exits
# and the signal pipeline all measure distances the same way; a second, subtly
# different basis-point helper is exactly how two modules start disagreeing
# about whether a level was reached.


def bps_between(distance: float, reference: float) -> float:
    """``distance`` as basis points of ``reference``. Sign-free."""
    if reference == 0:
        return 0.0
    return abs(distance) / abs(reference) * 10_000.0


def bps_to_price(reference: float, bps: float) -> float:
    """The price distance that ``bps`` represents at ``reference``."""
    return abs(reference) * bps / 10_000.0


class EntryRule(StrEnum):
    """Which closed bar converts a completed setup into a position."""

    RECLAIM_CLOSE = "reclaim_close"
    """The bar that completed the setup. The earliest admissible entry."""

    NEXT_BAR_OPEN = "next_bar_open"
    """One bar later, and only if the level still held on that bar's close."""

    FIRST_RETEST = "first_retest"
    """The first return to the level after the setup completed."""

    RETEST_WITH_REJECTION = "retest_with_rejection"
    """A retest that is also shaped like a rejection."""

    DISPLACEMENT_CONFIRMATION = "displacement_confirmation"
    """A subsequent bar whose body travels a configured distance in the trade's favour."""

    STRUCTURE_BREAK = "structure_break"
    """A close beyond the most recent *confirmed* swing point in the trade's direction."""


WAIVABLE_CONDITIONS: tuple[str, ...] = (
    "level_held_after_trigger",
    "retest",
    "rejection_shape",
    "displacement",
    "structure_break",
)
"""Every optional condition any rule can impose.

Recorded in full on each signal, split into required and waived, so a signal can
be read as "this fired *without* demanding a retest" rather than leaving the
reader to reconstruct the configuration.
"""

_REQUIRED_BY_RULE: dict[EntryRule, tuple[str, ...]] = {
    EntryRule.RECLAIM_CLOSE: (),
    EntryRule.NEXT_BAR_OPEN: ("level_held_after_trigger",),
    EntryRule.FIRST_RETEST: ("retest",),
    EntryRule.RETEST_WITH_REJECTION: ("retest", "rejection_shape"),
    EntryRule.DISPLACEMENT_CONFIRMATION: ("displacement",),
    EntryRule.STRUCTURE_BREAK: ("structure_break",),
}


def required_conditions(rule: EntryRule) -> tuple[str, ...]:
    return _REQUIRED_BY_RULE[rule]


def waived_conditions(rule: EntryRule) -> tuple[str, ...]:
    """The optional conditions this rule deliberately does **not** demand."""
    required = set(_REQUIRED_BY_RULE[rule])
    return tuple(c for c in WAIVABLE_CONDITIONS if c not in required)


@dataclass(frozen=True)
class EntryConfig:
    """Thresholds for the rule in force. Only the active rule reads its own fields."""

    rule: EntryRule = EntryRule.RECLAIM_CLOSE

    max_wait_bars: int = 6
    """Closed bars after the trigger before the setup is abandoned unentered."""

    retest_tolerance_bps: float = 10.0
    """How close price must come back to the level to count as a retest."""

    rejection_wick_body_ratio: float = 1.0
    """Minimum wick-to-body ratio, measured on the level's side of the bar."""

    displacement_atr: float = 0.5
    """Displacement floor as a fraction of ATR; combined with the bps floor by max."""

    displacement_bps: float = 0.0
    """Displacement floor in basis points of the level."""

    pivot_span: int = 2
    """Bars required either side of a swing point before it is confirmed."""

    def __post_init__(self) -> None:
        if self.max_wait_bars < 1:
            raise EntryError("max_wait_bars must leave at least one bar to enter on.")
        if self.pivot_span < 1:
            raise EntryError("pivot_span must be at least one bar on each side.")
        if self.rule is EntryRule.DISPLACEMENT_CONFIRMATION and (
            self.displacement_atr <= 0 and self.displacement_bps <= 0
        ):
            raise EntryError(
                "displacement_confirmation needs a positive displacement floor; with both "
                "floors at zero every bar displaces and the rule is inert."
            )

    @property
    def required(self) -> tuple[str, ...]:
        return required_conditions(self.rule)

    @property
    def waived(self) -> tuple[str, ...]:
        return waived_conditions(self.rule)


# -- swing structure --------------------------------------------------------- #


@dataclass(frozen=True)
class Pivot:
    """A swing point, together with the bar at which it became knowable."""

    index: int
    at: datetime
    price: float
    kind: Side
    confirmed_index: int
    confirmed_at: datetime

    @property
    def confirmation_lag(self) -> int:
        return self.confirmed_index - self.index


def confirmed_pivots(bars: Sequence[Bar], span: int) -> tuple[Pivot, ...]:
    """Swing highs and lows with ``span`` bars either side, dated when confirmed.

    A pivot is strict — the centre bar must exceed *every* neighbour in the
    window — so a flat top produces no pivot rather than an arbitrary one.

    ``confirmed_index`` is ``span`` bars after the pivot itself, and consumers
    must filter on it. The pivot price is perfectly well defined at the centre
    bar, where it was not yet knowable.
    """
    if span < 1:
        raise EntryError("A swing point needs at least one bar on each side.")
    pivots: list[Pivot] = []
    for position in range(span, len(bars) - span):
        centre = bars[position]
        window = bars[position - span : position + span + 1]
        confirm = bars[position + span]
        neighbours = [b for offset, b in enumerate(window) if offset != span]
        if all(b.high < centre.high for b in neighbours):
            pivots.append(
                Pivot(
                    index=centre.index,
                    at=centre.open_time,
                    price=centre.high,
                    kind=Side.HIGH,
                    confirmed_index=confirm.index,
                    confirmed_at=confirm.open_time,
                )
            )
        if all(b.low > centre.low for b in neighbours):
            pivots.append(
                Pivot(
                    index=centre.index,
                    at=centre.open_time,
                    price=centre.low,
                    kind=Side.LOW,
                    confirmed_index=confirm.index,
                    confirmed_at=confirm.open_time,
                )
            )
    return tuple(pivots)


def latest_confirmed_pivot(
    pivots: Sequence[Pivot], kind: Side, bar_index: int, *, not_after: int | None = None
) -> Pivot | None:
    """The most recent pivot of ``kind`` already confirmed at ``bar_index``.

    ``not_after`` optionally caps the pivot's own index, which is how a rule asks
    for "the structure that existed before the setup" rather than a swing formed
    by the setup itself.
    """
    best: Pivot | None = None
    for pivot in pivots:
        if pivot.kind is not kind or pivot.confirmed_index > bar_index:
            continue
        if not_after is not None and pivot.index > not_after:
            continue
        if best is None or pivot.index > best.index:
            best = pivot
    return best


# -- evaluation -------------------------------------------------------------- #


@dataclass(frozen=True)
class EntryContext:
    """What the completed setup was, expressed so long and short share one path."""

    range_id: str
    label: str
    side: Side
    """The side of the range price interacted with."""

    sign: int
    """The direction the resulting trade would take: +1 long, -1 short."""

    level: float
    trigger_bar: int
    trigger_at: datetime
    trigger_state: str

    def __post_init__(self) -> None:
        if self.sign not in (-1, 1):
            raise EntryError("sign must be -1 (short) or +1 (long).")


@dataclass(frozen=True)
class EntryConfirmation:
    """The bar that turned a setup into a position, and why it qualified."""

    bar_index: int
    at: datetime
    reference_price: float
    """The close of the confirming bar: the last price known when the plan is made."""

    rule: EntryRule
    bars_waited: int
    detail: dict[str, float] = field(default_factory=dict)
    conditions_required: tuple[str, ...] = ()
    conditions_waived: tuple[str, ...] = ()


class EntryEvaluator:
    """Watches bars after a setup completes and decides whether to enter.

    One evaluator per setup. It is fed closed bars in order, starting with the
    trigger bar itself, and settles exactly once — confirmed, expired or
    cancelled — which is what gives the pipeline its no-duplicate guarantee.
    """

    def __init__(
        self,
        config: EntryConfig,
        context: EntryContext,
        *,
        pivots: Sequence[Pivot] = (),
    ) -> None:
        self.config = config
        self.context = context
        self.pivots = tuple(pivots)
        self._confirmed = False
        self._expired = False
        self._cancelled = False

    @property
    def settled(self) -> bool:
        return self._confirmed or self._expired or self._cancelled

    @property
    def expired(self) -> bool:
        return self._expired

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        """Abandon the setup: the hypothesis stopped holding before entry."""
        if not self._confirmed:
            self._cancelled = True

    def observe(self, bar: Bar) -> EntryConfirmation | None:
        if self.settled:
            return None
        waited = bar.index - self.context.trigger_bar
        if waited < 0:
            return None
        if waited > self.config.max_wait_bars:
            self._expired = True
            return None

        ok, detail = self._qualifies(bar, waited)
        if not ok:
            return None
        self._confirmed = True
        return EntryConfirmation(
            bar_index=bar.index,
            at=bar.open_time,
            reference_price=bar.close,
            rule=self.config.rule,
            bars_waited=waited,
            detail=detail,
            conditions_required=self.config.required,
            conditions_waived=self.config.waived,
        )

    # -- geometry, written once for both directions -------------------------- #

    def _holds(self, bar: Bar) -> bool:
        """The bar closed on the side of the level the trade needs."""
        return self.context.sign * (bar.close - self.context.level) >= 0

    def _towards_level(self, bar: Bar) -> float:
        """The bar's extreme nearest the level, seen from the trade's side."""
        return bar.low if self.context.sign > 0 else bar.high

    def _distance_to_level_bps(self, bar: Bar) -> float:
        gap = self.context.sign * (self._towards_level(bar) - self.context.level)
        # A negative gap means price traded back through the level, which is a
        # retest by any reading, so it is clamped rather than treated as far away.
        return bps_between(max(gap, 0.0), self.context.level)

    def _wick_body_ratio(self, bar: Bar) -> float:
        body = abs(bar.close - bar.open)
        wick = (
            min(bar.open, bar.close) - bar.low
            if self.context.sign > 0
            else bar.high - max(bar.open, bar.close)
        )
        if body <= 0:
            return float("inf") if wick > 0 else 0.0
        return wick / body

    def _displacement_floor(self, bar: Bar) -> float:
        by_atr = (bar.atr or 0.0) * self.config.displacement_atr
        by_bps = bps_to_price(self.context.level, self.config.displacement_bps)
        return max(by_atr, by_bps)

    # -- the rules ----------------------------------------------------------- #

    def _qualifies(self, bar: Bar, waited: int) -> tuple[bool, dict[str, float]]:
        rule = self.config.rule
        if rule is EntryRule.RECLAIM_CLOSE:
            return waited == 0, {"bars_waited": float(waited)}
        if rule is EntryRule.NEXT_BAR_OPEN:
            return (waited == 1 and self._holds(bar)), {"bars_waited": float(waited)}
        if rule is EntryRule.FIRST_RETEST:
            return self._retest(bar, waited)
        if rule is EntryRule.RETEST_WITH_REJECTION:
            ok, detail = self._retest(bar, waited)
            ratio = self._wick_body_ratio(bar)
            detail["wick_body_ratio"] = ratio
            shaped = ratio >= self.config.rejection_wick_body_ratio and (
                self.context.sign * (bar.close - bar.open) >= 0
            )
            return (ok and shaped), detail
        if rule is EntryRule.DISPLACEMENT_CONFIRMATION:
            return self._displacement(bar, waited)
        return self._structure_break(bar, waited)

    def _retest(self, bar: Bar, waited: int) -> tuple[bool, dict[str, float]]:
        gap = self._distance_to_level_bps(bar)
        detail = {"bars_waited": float(waited), "retest_gap_bps": gap}
        if waited < 1:
            return False, detail
        return (gap <= self.config.retest_tolerance_bps and self._holds(bar)), detail

    def _displacement(self, bar: Bar, waited: int) -> tuple[bool, dict[str, float]]:
        travelled = self.context.sign * (bar.close - bar.open)
        floor = self._displacement_floor(bar)
        detail = {
            "bars_waited": float(waited),
            "displacement": travelled,
            "displacement_floor": floor,
        }
        if waited < 1:
            return False, detail
        return (travelled >= floor > 0 and self._holds(bar)), detail

    def _structure_break(self, bar: Bar, waited: int) -> tuple[bool, dict[str, float]]:
        detail = {"bars_waited": float(waited)}
        if waited < 1:
            return False, detail
        kind = Side.HIGH if self.context.sign > 0 else Side.LOW
        pivot = latest_confirmed_pivot(self.pivots, kind, bar.index)
        if pivot is None:
            return False, detail
        detail["pivot_price"] = pivot.price
        detail["pivot_index"] = float(pivot.index)
        detail["pivot_confirmation_lag"] = float(pivot.confirmation_lag)
        broken = self.context.sign * (bar.close - pivot.price) > 0
        return (broken and self._holds(bar)), detail


def resolve_entry(
    config: EntryConfig, context: EntryContext, *, pivots: Sequence[Pivot] = ()
) -> EntryEvaluator:
    """Build the evaluator for the configured rule.

    A resolver rather than a constructor call so that callers select a rule by
    value — the point of the enum is that the choice is data, recorded with the
    run, not a branch chosen in code.
    """
    if config.rule is EntryRule.STRUCTURE_BREAK and not pivots:
        raise EntryError(
            "structure_break needs a confirmed pivot series; passing none would make the "
            "rule silently unenterable rather than obviously misconfigured."
        )
    return EntryEvaluator(config, context, pivots=pivots)


__all__ = [
    "WAIVABLE_CONDITIONS",
    "EntryConfig",
    "EntryConfirmation",
    "EntryContext",
    "EntryError",
    "EntryEvaluator",
    "EntryRule",
    "Pivot",
    "bps_between",
    "bps_to_price",
    "confirmed_pivots",
    "latest_confirmed_pivot",
    "required_conditions",
    "resolve_entry",
    "waived_conditions",
]
