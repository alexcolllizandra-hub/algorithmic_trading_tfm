"""How price interacts with a level, as a state machine rather than a checklist.

Price-action vocabulary — "swept", "reclaimed", "accepted outside" — describes a
*sequence*, not a condition. A close back inside a range means nothing on its own;
it means something only if price had first left the range by enough to count.
Writing these as independent boolean columns loses the ordering, and a model
built on unordered booleans will fire on bars where the story never happened.

So each level gets an explicit machine. Every transition is recorded with the
bar that caused it and the measured quantity that triggered it, which is what
makes a signal explainable after the fact instead of merely reproducible.

Causality: transitions are evaluated on **closed** bars only. Intrabar highs and
lows are used, because they are part of the closed bar's record, but a bar is
never consulted before it has closed, and the machine never looks forward.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class LevelState(StrEnum):
    """The interaction between price and one side of one range."""

    AVAILABLE = "AVAILABLE"
    """The level exists and its defining period has closed."""

    APPROACHING = "APPROACHING"
    """Price came within tolerance without touching."""

    TOUCHED = "TOUCHED"
    """Price reached the level."""

    PIERCED = "PIERCED"
    """Price traded through the level, by less than the sweep threshold."""

    SWEPT = "SWEPT"
    """The penetration reached the configured minimum depth."""

    REJECTED = "REJECTED"
    """After piercing, the bar closed back on the original side."""

    RECLAIMED = "RECLAIMED"
    """A confirmed close recovered the level after a sweep."""

    RETESTED = "RETESTED"
    """Price returned to the reclaimed level from the inside."""

    ACCEPTED_OUTSIDE = "ACCEPTED_OUTSIDE"
    """The market stayed beyond the level on the acceptance criterion."""

    FAILED_RECLAIM = "FAILED_RECLAIM"
    """Reclaimed, then lost the level again."""

    TARGET_REACHED = "TARGET_REACHED"
    """Price reached the objective associated with the setup."""

    INVALIDATED = "INVALIDATED"
    """The hypothesis stopped holding."""

    EXPIRED = "EXPIRED"
    """The tradeable window closed with the sequence unresolved."""


TERMINAL_STATES: frozenset[LevelState] = frozenset(
    {
        LevelState.ACCEPTED_OUTSIDE,
        LevelState.FAILED_RECLAIM,
        LevelState.TARGET_REACHED,
        LevelState.INVALIDATED,
        LevelState.EXPIRED,
    }
)
"""States after which the machine stops; the sequence has resolved one way or another."""


class Side(StrEnum):
    """Which edge of a range is being watched.

    ``LOW`` means the low is the level and a sweep goes downward; the setup that
    follows a reclaim is long. ``HIGH`` is the mirror image. Encoding it once
    here is what lets the long and short variants share a single implementation
    instead of being written twice and drifting apart.
    """

    LOW = "low"
    HIGH = "high"

    @property
    def sign(self) -> float:
        """+1 when beyond means above, -1 when beyond means below."""
        return 1.0 if self is Side.HIGH else -1.0

    @property
    def opposite(self) -> Side:
        return Side.LOW if self is Side.HIGH else Side.HIGH


@dataclass(frozen=True)
class InteractionConfig:
    """Mechanical definitions for words that are usually left to judgement.

    Every threshold has an explicit unit. Depths are expressed in basis points
    of the level and, optionally, as a fraction of ATR; a sweep must clear
    whichever of the two is configured, which keeps the definition meaningful
    across volatility regimes without hard-coding a price scale.
    """

    approach_bps: float = 15.0
    """How close price must come for the level to count as approached."""

    pierce_bps: float = 0.0
    """Penetration beyond the level that counts as a pierce at all."""

    sweep_bps: float = 5.0
    """Minimum penetration for a pierce to be promoted to a sweep."""

    sweep_atr_fraction: float | None = None
    """Optional alternative depth floor, as a fraction of ATR."""

    reclaim_within_bars: int = 3
    """How many closed bars after the sweep a reclaim may still occur."""

    reclaim_confirmation_closes: int = 1
    """Closes back inside required before the level counts as reclaimed."""

    reclaim_buffer_bps: float = 0.0
    """How far back inside the close must be, so a close exactly on the level does not count."""

    min_wick_body_ratio: float | None = None
    """Optional shape filter on the rejecting bar."""

    min_wick_recovery: float | None = None
    """Optional floor on the fraction of the penetration retraced within the bar."""

    acceptance_closes: int = 3
    """Consecutive closes beyond the level that constitute acceptance."""

    acceptance_bps: float = 10.0
    """How far beyond the level those closes must be."""

    retest_tolerance_bps: float = 10.0
    """How close price must return for a retest to be recorded."""

    max_bars_active: int = 96
    """Bars after availability before an unresolved sequence expires."""

    def __post_init__(self) -> None:
        if self.sweep_bps < self.pierce_bps:
            raise ValueError("A sweep cannot be shallower than a pierce.")
        if self.reclaim_confirmation_closes < 1:
            raise ValueError("A reclaim needs at least one confirming close.")
        if self.reclaim_within_bars < 1:
            raise ValueError("A reclaim needs at least one bar to happen in.")


@dataclass(frozen=True)
class Transition:
    """One state change, with the evidence that caused it."""

    bar_index: int
    at: datetime
    previous: LevelState
    state: LevelState
    price: float
    level: float
    depth_bps: float = 0.0
    detail: dict[str, float] = field(default_factory=dict)

    def describe(self) -> str:
        return (
            f"{self.previous} -> {self.state} at {self.at.isoformat()} "
            f"(price {self.price:.2f}, level {self.level:.2f}, depth {self.depth_bps:.1f} bps)"
        )


@dataclass
class Bar:
    """A closed bar, in the only form the machine needs."""

    index: int
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    atr: float | None = None


def _bps(distance: float, level: float) -> float:
    """Distance in basis points of the level. Sign-free; direction is handled by the caller."""
    if level == 0:
        return 0.0
    return abs(distance) / abs(level) * 10_000.0


class LevelTracker:
    """Follows one side of one range through its whole interaction with price.

    Deliberately a small stateful object rather than a vectorised pass. The
    sequence is order-dependent and history-dependent — a reclaim is only a
    reclaim if a sweep preceded it within a bar budget — and expressing that as
    window functions produces code nobody can check. The cost is a Python loop
    over bars, which is paid once per level and stays well inside budget because
    a level is only tracked while it is active.
    """

    def __init__(
        self,
        *,
        range_id: str,
        label: str,
        side: Side,
        level: float,
        available_from: datetime,
        config: InteractionConfig,
        expires_at: datetime | None = None,
    ) -> None:
        self.range_id = range_id
        self.label = label
        self.side = side
        self.level = float(level)
        self.available_from = available_from
        self.expires_at = expires_at
        self.config = config

        self.state = LevelState.AVAILABLE
        self.transitions: list[Transition] = []
        self.bars_seen = 0
        self.max_depth_bps = 0.0
        self.sweep_extreme: float | None = None
        self.sweep_bar: int | None = None
        self._closes_inside = 0
        self._closes_outside = 0
        self._reclaim_bar: int | None = None

    # -- geometry ---------------------------------------------------------- #

    def _beyond(self, price: float) -> float:
        """How far ``price`` sits beyond the level, positive when it is outside."""
        return (price - self.level) * self.side.sign

    def _extreme(self, bar: Bar) -> float:
        """The bar's furthest excursion beyond the level."""
        return bar.high if self.side is Side.HIGH else bar.low

    def _sweep_threshold_bps(self, bar: Bar) -> float:
        """The depth a penetration must reach, taking the stricter of the two rules."""
        threshold = self.config.sweep_bps
        if self.config.sweep_atr_fraction is not None and bar.atr:
            atr_bps = _bps(bar.atr * self.config.sweep_atr_fraction, self.level)
            threshold = max(threshold, atr_bps)
        return threshold

    # -- transitions ------------------------------------------------------- #

    def _move(
        self,
        bar: Bar,
        state: LevelState,
        *,
        price: float,
        depth_bps: float = 0.0,
        **detail: float,
    ) -> None:
        if state is self.state:
            return
        self.transitions.append(
            Transition(
                bar_index=bar.index,
                at=bar.open_time,
                previous=self.state,
                state=state,
                price=price,
                level=self.level,
                depth_bps=depth_bps,
                detail=dict(detail),
            )
        )
        self.state = state

    @property
    def finished(self) -> bool:
        return self.state in TERMINAL_STATES

    def update(self, bar: Bar) -> LevelState:
        """Advance the machine by one closed bar and return the resulting state."""
        if self.finished:
            return self.state
        if bar.open_time < self.available_from:
            # The level is not usable yet. Consuming the bar anyway would be the
            # look-ahead this module exists to prevent.
            return self.state

        self.bars_seen += 1
        if self._expired(bar):
            return self.state

        excursion = self._beyond(self._extreme(bar))
        depth_bps = _bps(excursion, self.level) if excursion > 0 else 0.0
        self.max_depth_bps = max(self.max_depth_bps, depth_bps)

        if self.state in {LevelState.RECLAIMED, LevelState.RETESTED}:
            self._after_reclaim(bar, depth_bps)
            return self.state

        # Reaching the level exactly counts as touching it. Using a strict
        # inequality here would classify a bar whose low equals the level as
        # merely "approaching", which is wrong in the one case traders care
        # about most: the clean test that holds to the tick.
        if excursion < 0:
            self._short_of_the_level(bar)
            return self.state

        self._beyond_the_level(bar, depth_bps)
        return self.state

    # -- branches ---------------------------------------------------------- #

    def _expired(self, bar: Bar) -> bool:
        past_window = self.expires_at is not None and bar.open_time >= self.expires_at
        past_budget = self.bars_seen > self.config.max_bars_active
        if past_window or past_budget:
            self._move(bar, LevelState.EXPIRED, price=bar.close)
            return True
        return False

    def _short_of_the_level(self, bar: Bar) -> None:
        """Price stayed on its original side of the level for this whole bar."""
        gap_bps = _bps(self._beyond(self._extreme(bar)), self.level)
        if self.state is LevelState.AVAILABLE and gap_bps <= self.config.approach_bps:
            self._move(bar, LevelState.APPROACHING, price=self._extreme(bar), depth_bps=gap_bps)
            return
        # A sequence awaiting confirmation keeps advancing on bars that never
        # revisit the level. Requiring the confirming bar to touch it again
        # would make multi-close confirmation impossible to satisfy, since the
        # whole point of a reclaim is that price leaves the level behind.
        if self.state in {LevelState.PIERCED, LevelState.SWEPT, LevelState.REJECTED}:
            self._maybe_reclaim(bar)

    def _beyond_the_level(self, bar: Bar, depth_bps: float) -> None:
        """Price traded through the level on this bar."""
        if self.state in {LevelState.AVAILABLE, LevelState.APPROACHING}:
            self._move(bar, LevelState.TOUCHED, price=self._extreme(bar), depth_bps=depth_bps)

        if depth_bps <= self.config.pierce_bps:
            return

        if self.state is LevelState.TOUCHED:
            self._move(bar, LevelState.PIERCED, price=self._extreme(bar), depth_bps=depth_bps)

        if depth_bps >= self._sweep_threshold_bps(bar) and self.state is LevelState.PIERCED:
            self.sweep_extreme = self._extreme(bar)
            self.sweep_bar = bar.index
            self._move(bar, LevelState.SWEPT, price=self._extreme(bar), depth_bps=depth_bps)

        # A bar that pierces and closes back inside is a rejection; a bar that
        # closes beyond counts towards acceptance. Both are decided on the close,
        # never on the excursion alone.
        if self._beyond(bar.close) <= 0:
            self._maybe_reclaim(bar)
        else:
            self._maybe_accept(bar, depth_bps)

    def _maybe_reclaim(self, bar: Bar) -> None:
        """A close back inside: rejection, and possibly a confirmed reclaim."""
        buffer = self.level * self.config.reclaim_buffer_bps / 10_000.0
        inside_enough = self._beyond(bar.close) <= -abs(buffer)
        if not inside_enough:
            self._closes_inside = 0
            return

        self._closes_outside = 0
        if self.state in {LevelState.PIERCED, LevelState.SWEPT}:
            self._move(
                bar,
                LevelState.REJECTED,
                price=bar.close,
                depth_bps=self.max_depth_bps,
                wick_body_ratio=self._wick_body_ratio(bar),
                wick_recovery=self._wick_recovery(bar),
            )

        if self.state is not LevelState.REJECTED:
            return
        if self.sweep_bar is None:
            # Never deep enough to be a sweep, so there is nothing to reclaim.
            return
        if bar.index - self.sweep_bar > self.config.reclaim_within_bars:
            self._move(bar, LevelState.INVALIDATED, price=bar.close)
            return
        if not self._shape_ok(bar):
            return

        self._closes_inside += 1
        if self._closes_inside >= self.config.reclaim_confirmation_closes:
            self._reclaim_bar = bar.index
            self._move(
                bar,
                LevelState.RECLAIMED,
                price=bar.close,
                depth_bps=self.max_depth_bps,
                confirming_closes=float(self._closes_inside),
            )

    def _maybe_accept(self, bar: Bar, depth_bps: float) -> None:
        """Consecutive closes far enough beyond the level mean the market accepted it."""
        if depth_bps < self.config.acceptance_bps:
            self._closes_outside = 0
            return
        self._closes_outside += 1
        if self._closes_outside >= self.config.acceptance_closes:
            self._move(
                bar,
                LevelState.ACCEPTED_OUTSIDE,
                price=bar.close,
                depth_bps=depth_bps,
                closes_outside=float(self._closes_outside),
            )

    def _after_reclaim(self, bar: Bar, depth_bps: float) -> None:
        """Once reclaimed, the level is either held, retested, or lost again."""
        if self._beyond(bar.close) > 0:
            self._move(bar, LevelState.FAILED_RECLAIM, price=bar.close, depth_bps=depth_bps)
            return
        if self.state is LevelState.RECLAIMED:
            distance_bps = _bps(self._beyond(self._extreme(bar)), self.level)
            reached_back = self._beyond(self._extreme(bar)) > 0 or (
                distance_bps <= self.config.retest_tolerance_bps
            )
            if reached_back and bar.index > (self._reclaim_bar or -1):
                self._move(
                    bar, LevelState.RETESTED, price=self._extreme(bar), depth_bps=distance_bps
                )

    # -- bar shape --------------------------------------------------------- #

    def _wick_body_ratio(self, bar: Bar) -> float:
        """Length of the wick on the level's side, relative to the body."""
        body = abs(bar.close - bar.open)
        wick = (
            bar.high - max(bar.open, bar.close)
            if self.side is Side.HIGH
            else min(bar.open, bar.close) - bar.low
        )
        if body <= 0:
            return float("inf") if wick > 0 else 0.0
        return wick / body

    def _wick_recovery(self, bar: Bar) -> float:
        """Fraction of the excursion beyond the level that the close took back."""
        excursion = self._beyond(self._extreme(bar))
        if excursion <= 0:
            return 1.0
        recovered = excursion - max(self._beyond(bar.close), 0.0)
        return recovered / excursion

    def _shape_ok(self, bar: Bar) -> bool:
        if (
            self.config.min_wick_body_ratio is not None
            and self._wick_body_ratio(bar) < self.config.min_wick_body_ratio
        ):
            return False
        return not (
            self.config.min_wick_recovery is not None
            and self._wick_recovery(bar) < self.config.min_wick_recovery
        )


def run_tracker(tracker: LevelTracker, bars: list[Bar]) -> LevelTracker:
    """Feed a tracker its bars in order, stopping once the sequence resolves."""
    for bar in bars:
        tracker.update(bar)
        if tracker.finished:
            break
    return tracker


__all__ = [
    "TERMINAL_STATES",
    "Bar",
    "InteractionConfig",
    "LevelState",
    "LevelTracker",
    "Side",
    "Transition",
    "run_tracker",
]
