"""How much to bet, and when not to bet at all — kept away from the signal.

This module is deliberately unable to generate a signal, and
:mod:`perp_lab.crt.signals` is deliberately unable to size one. The separation is
a research requirement rather than a matter of taste, for two reasons.

A risk limit that lives inside the signal changes *which setups exist*, so the
hit rate measured for a pattern silently becomes the hit rate of the pattern
plus a position-management rule, and the two can never be told apart afterwards.
And a sizing rule that reads the same state as the entry rule can, without
anyone intending it, let the size depend on how the last trade went — which is a
different strategy from the one being tested.

So the flow is one-directional: signals propose, exits price, risk disposes.
Everything here consumes an already-priced :class:`~perp_lab.crt.exits.TradePlan`
and answers two questions — *may this trade happen* and *how large* — using only
trades that had already resolved when the question was asked.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime


class RiskError(ValueError):
    """Raised when a risk policy is incoherent or applied out of order."""


@dataclass(frozen=True)
class RiskConfig:
    """A complete risk policy. Every limit is off by default except sizing."""

    initial_capital: float = 10_000.0
    risk_per_trade_pct: float = 0.5
    """Share of capital risked between entry and stop, in percent."""

    fixed_risk_cash: float | None = None
    """A cash amount per trade; overrides the percentage when set."""

    max_exposure: float = 1.0
    """Cap on notional as a multiple of capital, applied after sizing."""

    max_trades_per_session: int | None = None
    max_trades_per_level: int = 1
    max_daily_losses: int | None = None
    lockout_after_losses: int | None = None
    """Consecutive losses that stop trading for a while."""

    lockout_bars: int = 24
    block_after_entry_cutoff: bool = True
    """Refuse new entries once the session's cutoff has passed."""

    min_net_reward_risk: float = 0.0
    """A portfolio-level floor, on top of the per-setup feasibility gate."""

    def __post_init__(self) -> None:
        if self.initial_capital <= 0:
            raise RiskError("initial_capital must be positive.")
        if self.fixed_risk_cash is None and self.risk_per_trade_pct <= 0:
            raise RiskError("Either a positive risk_per_trade_pct or a fixed_risk_cash is needed.")
        if self.fixed_risk_cash is not None and self.fixed_risk_cash <= 0:
            raise RiskError("fixed_risk_cash must be positive when set.")
        if self.max_exposure <= 0:
            raise RiskError("max_exposure must be positive.")
        if self.max_trades_per_level < 1:
            raise RiskError("max_trades_per_level must allow at least one trade.")
        if self.lockout_after_losses is not None and self.lockout_after_losses < 1:
            raise RiskError("lockout_after_losses must be at least one loss.")
        if self.lockout_bars < 0:
            raise RiskError("lockout_bars cannot be negative.")

    @property
    def risk_cash(self) -> float:
        if self.fixed_risk_cash is not None:
            return self.fixed_risk_cash
        return self.initial_capital * self.risk_per_trade_pct / 100.0


@dataclass(frozen=True)
class TradeRequest:
    """A priced setup asking for permission and a size."""

    bar_index: int
    at: datetime
    sign: int
    entry_price: float
    stop_price: float
    net_reward_risk: float
    level_key: str
    session_key: str = ""
    day: date | None = None
    after_entry_cutoff: bool = False

    def __post_init__(self) -> None:
        if self.sign not in (-1, 1):
            raise RiskError("sign must be -1 (short) or +1 (long).")


@dataclass(frozen=True)
class RiskDecision:
    accepted: bool
    size_fraction: float
    risk_cash: float
    reason: str

    @property
    def signed_size(self) -> float:
        return self.size_fraction


def size_from_stop_distance(
    *,
    capital: float,
    risk_cash: float,
    entry_price: float,
    stop_price: float,
    max_exposure: float,
) -> float:
    """Notional as a fraction of capital, from the distance to the stop.

    Sizing from the stop rather than from a fixed notional is what makes "1% per
    trade" mean the same thing in a quiet session and a violent one: a wider stop
    buys fewer units. The exposure cap then binds when the stop is so tight that
    honouring the risk budget would demand more leverage than the policy allows —
    and when it binds, the trade risks *less* than the budget, never more.
    """
    distance = abs(entry_price - stop_price)
    if distance <= 0 or entry_price <= 0 or capital <= 0:
        return 0.0
    units = risk_cash / distance
    notional = units * entry_price
    return min(notional / capital, max_exposure)


@dataclass
class _PendingResult:
    resolved_at_bar: int
    day: date | None
    won: bool


@dataclass
class RiskLedger:
    """Applies a policy to a chronological stream of requests.

    Results of earlier trades feed the loss limits, but only once they have
    actually resolved: :meth:`register_outcome` queues an outcome against the bar
    that closed it, and it is not visible to any decision taken before that bar.
    Applying a result at the moment the trade *opened* would let a limit use the
    future, which is the same leak as a look-ahead feature wearing a risk badge.
    """

    config: RiskConfig
    trades_per_session: dict[str, int] = field(default_factory=dict)
    trades_per_level: dict[str, int] = field(default_factory=dict)
    losses_per_day: dict[date, int] = field(default_factory=dict)
    consecutive_losses: int = 0
    locked_out_until_bar: int | None = None
    _pending: list[_PendingResult] = field(default_factory=list)
    _settled_to: int = -1

    def register_outcome(self, *, resolved_at_bar: int, won: bool, day: date | None = None) -> None:
        if resolved_at_bar <= self._settled_to:
            raise RiskError(
                f"Outcome resolving at bar {resolved_at_bar} arrived after decisions were "
                f"already taken at bar {self._settled_to}; the ledger would be using the future."
            )
        self._pending.append(_PendingResult(resolved_at_bar, day, won))

    def settle_up_to(self, bar_index: int) -> None:
        """Absorb every outcome that had resolved by ``bar_index``."""
        due = [p for p in self._pending if p.resolved_at_bar <= bar_index]
        self._pending = [p for p in self._pending if p.resolved_at_bar > bar_index]
        for result in sorted(due, key=lambda p: p.resolved_at_bar):
            if result.won:
                self.consecutive_losses = 0
                continue
            self.consecutive_losses += 1
            if result.day is not None:
                self.losses_per_day[result.day] = self.losses_per_day.get(result.day, 0) + 1
            if (
                self.config.lockout_after_losses is not None
                and self.consecutive_losses >= self.config.lockout_after_losses
            ):
                self.locked_out_until_bar = result.resolved_at_bar + self.config.lockout_bars
        self._settled_to = max(self._settled_to, bar_index)

    def evaluate(self, request: TradeRequest) -> RiskDecision:
        """May this trade happen, and how large?"""
        self.settle_up_to(request.bar_index)
        config = self.config

        if self.locked_out_until_bar is not None:
            if request.bar_index < self.locked_out_until_bar:
                return self._no(f"locked out after {self.consecutive_losses} consecutive losses")
            self.locked_out_until_bar = None
            self.consecutive_losses = 0

        if config.block_after_entry_cutoff and request.after_entry_cutoff:
            return self._no("past the session's entry cutoff")
        if request.net_reward_risk < config.min_net_reward_risk:
            return self._no("net reward:risk below the policy floor")
        if self.trades_per_level.get(request.level_key, 0) >= config.max_trades_per_level:
            return self._no("this level has already been traded")
        if (
            config.max_trades_per_session is not None
            and request.session_key
            and self.trades_per_session.get(request.session_key, 0) >= config.max_trades_per_session
        ):
            return self._no("session trade limit reached")
        if (
            config.max_daily_losses is not None
            and request.day is not None
            and self.losses_per_day.get(request.day, 0) >= config.max_daily_losses
        ):
            return self._no("daily loss limit reached")

        size = size_from_stop_distance(
            capital=config.initial_capital,
            risk_cash=config.risk_cash,
            entry_price=request.entry_price,
            stop_price=request.stop_price,
            max_exposure=config.max_exposure,
        )
        if size <= 0:
            return self._no("stop distance gives no size")

        self.trades_per_level[request.level_key] = (
            self.trades_per_level.get(request.level_key, 0) + 1
        )
        if request.session_key:
            self.trades_per_session[request.session_key] = (
                self.trades_per_session.get(request.session_key, 0) + 1
            )
        return RiskDecision(
            accepted=True,
            size_fraction=size,
            risk_cash=config.risk_cash,
            reason="accepted",
        )

    def _no(self, reason: str) -> RiskDecision:
        return RiskDecision(accepted=False, size_fraction=0.0, risk_cash=0.0, reason=reason)


def evaluate_requests(
    config: RiskConfig,
    items: Iterable[tuple[TradeRequest, int, bool]],
) -> list[RiskDecision]:
    """Run a whole chronological stream through one ledger.

    ``items`` are ``(request, bar the trade resolves on, whether it won)``.
    Outcomes are registered when the request is accepted and only become visible
    from the bar they resolve on, so the loss limits cannot see their own future.
    """
    ledger = RiskLedger(config)
    decisions: list[RiskDecision] = []
    ordered = sorted(items, key=lambda item: item[0].bar_index)
    for request, resolved_at, won in ordered:
        decision = ledger.evaluate(request)
        decisions.append(decision)
        if decision.accepted:
            ledger.register_outcome(
                resolved_at_bar=max(resolved_at, request.bar_index + 1),
                won=won,
                day=request.day,
            )
    return decisions


def exposure_cap(decisions: Sequence[RiskDecision]) -> float:
    """The largest size any accepted decision produced; a policy sanity check."""
    accepted = [d.size_fraction for d in decisions if d.accepted]
    return max(accepted) if accepted else 0.0


__all__ = [
    "RiskConfig",
    "RiskDecision",
    "RiskError",
    "RiskLedger",
    "TradeRequest",
    "evaluate_requests",
    "exposure_cap",
    "size_from_stop_distance",
]
