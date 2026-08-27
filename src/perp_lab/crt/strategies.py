"""Nine CRT hypotheses, assembled from the same four parts.

Every family below is a configuration of one engine: a reference range, a state
machine per side of it, an entry rule, an exit plan and a risk policy. None of
them is a separate algorithm, and that is the design rather than an economy —
nine hand-written strategies would drift apart in exactly the places that matter
(what counts as a sweep, when a level expires, which bar fills), and the
comparison between them would stop meaning anything.

**Long and short are the same code.** :class:`~perp_lab.crt.states.Side` carries
the sign, :class:`~perp_lab.crt.signals.SetupKind` says whether the trade goes
back into the range or away from it, and the traded direction falls out of the
two. ``direction`` selects which sides are watched; it never selects a code path.
``pdl_reclaim_long`` and ``pdh_reclaim_short`` are the clearest case: they are
one family, invoked with a different side.

**Nothing here is a claim.** These are untested hypotheses registered under the
round tag :data:`CRT_ROUND_TAG`. They inherit the study's protocol — walk-forward,
purge and embargo, seeds, cost stress, multiple-testing correction — and the
prior is that they fail, like the families the study has already rejected.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Any

import polars as pl

from perp_lab.crt.entries import (
    EntryConfig,
    EntryRule,
    Pivot,
    confirmed_pivots,
    latest_confirmed_pivot,
)
from perp_lab.crt.exits import (
    AmbiguityReport,
    ExitConfig,
    StopKind,
    TargetKind,
    TargetSpec,
    TradeOutcome,
    TradePlan,
    TradeReferences,
    ambiguity_metrics,
    plan_trade,
    simulate_trade,
)
from perp_lab.crt.ranges import (
    RANGE_SCHEMA,
    RangeError,
    active_ranges_at,
    candle_ranges,
    daily_ranges,
    opening_ranges,
    session_ranges,
)
from perp_lab.crt.risk import RiskConfig, RiskDecision, RiskLedger, TradeRequest
from perp_lab.crt.sessions import SessionSpec, resolve_session, session_windows
from perp_lab.crt.signals import (
    CrtPipelineResult,
    SetupKind,
    SignalSpec,
    bars_from_frame,
    run_crt_pipeline,
)
from perp_lab.crt.states import Bar, InteractionConfig, LevelState, Side
from perp_lab.strategies.base import SIDE_COL, validate_direction

CRT_ROUND_TAG = "CRT_INTRADAY_V1"
"""The experimental round these families belong to. Not R2, not R3."""

CRT_FAMILIES: tuple[str, ...] = (
    "crt_htf_range_reversal",
    "pdl_reclaim_long",
    "pdh_reclaim_short",
    "session_liquidity_sweep",
    "session_range_rotation",
    "opening_range_breakout_retest",
    "failed_breakout_reversal",
    "double_sweep_reversal",
    "crt_three_candle_model",
)


class CrtStrategyError(ValueError):
    """Raised when a family is asked for something it cannot represent."""


# -- target catalogues ------------------------------------------------------- #

TARGET_PLANS: dict[str, tuple[TargetSpec, ...]] = {
    "mid": (TargetSpec(TargetKind.RANGE_MID),),
    "mid_then_opposite": (
        TargetSpec(TargetKind.RANGE_MID, fraction=0.5),
        TargetSpec(TargetKind.OPPOSITE_EXTREME, fraction=0.5),
    ),
    "q_then_mid": (
        TargetSpec(TargetKind.RANGE_Q25, fraction=0.5),
        TargetSpec(TargetKind.RANGE_MID, fraction=0.5),
    ),
    "r_multiple_2": (TargetSpec(TargetKind.R_MULTIPLE, r_multiple=2.0),),
    "atr_multiple_2": (TargetSpec(TargetKind.ATR_MULTIPLE, atr_multiple=2.0),),
    "r1_then_r3": (
        TargetSpec(TargetKind.R_MULTIPLE, fraction=0.5, r_multiple=1.0),
        TargetSpec(TargetKind.R_MULTIPLE, fraction=0.5, r_multiple=3.0),
    ),
    "thirds_r": (
        TargetSpec(TargetKind.R_MULTIPLE, fraction=1 / 3, r_multiple=1.0),
        TargetSpec(TargetKind.R_MULTIPLE, fraction=1 / 3, r_multiple=1.5),
        TargetSpec(TargetKind.R_MULTIPLE, fraction=1 / 3, r_multiple=3.0),
    ),
    "next_liquidity": (TargetSpec(TargetKind.NEXT_LIQUIDITY),),
    "daily_open": (TargetSpec(TargetKind.DAILY_OPEN),),
    "session_open": (TargetSpec(TargetKind.SESSION_OPEN),),
}
"""Named objective sets. A few well-separated plans, not a continuum of prices."""


def resolve_targets(plan: str) -> tuple[TargetSpec, ...]:
    if plan not in TARGET_PLANS:
        raise CrtStrategyError(f"Unknown target plan {plan!r}; known: {sorted(TARGET_PLANS)}.")
    return TARGET_PLANS[plan]


# -- reference ranges -------------------------------------------------------- #


@dataclass(frozen=True)
class ReferenceSpec:
    """Which reference range a family reads, and how to build it from bars."""

    kind: str
    timeframe: str = "1d"
    session: str = "asia"
    minutes: int = 60
    timezone: str = "UTC"

    _KINDS = ("previous_day", "previous_candle", "previous_session", "opening_range")

    def __post_init__(self) -> None:
        if self.kind not in self._KINDS:
            raise CrtStrategyError(f"Unknown reference kind {self.kind!r}; known: {self._KINDS}.")
        if self.kind in {"previous_session", "opening_range"}:
            resolve_session(self.session)

    @property
    def label(self) -> str:
        if self.kind == "previous_day":
            return "previous_day"
        if self.kind == "previous_candle":
            return f"previous_candle_{self.timeframe}"
        if self.kind == "previous_session":
            return f"previous_session_{self.session}"
        return f"opening_range_{self.minutes}m_{self.session}"

    @property
    def session_spec(self) -> SessionSpec | None:
        if self.kind in {"previous_session", "opening_range"}:
            return resolve_session(self.session)
        return None

    def build(self, bars: pl.DataFrame) -> pl.DataFrame:
        """The reference ranges for this family, and nothing else.

        Only what the family reads is built. Building the whole catalogue would
        cost time on every candidate the search evaluates and would tempt a
        family into quoting a level it never declared.
        """
        if self.kind == "previous_day":
            return daily_ranges(bars, timezone=self.timezone)
        if self.kind == "previous_candle":
            return candle_ranges(bars, self.timeframe)
        spec = resolve_session(self.session)
        if self.kind == "previous_session":
            return session_ranges(bars, spec)
        try:
            return opening_ranges(bars, spec, self.minutes)
        except RangeError as exc:
            raise CrtStrategyError(
                f"A {self.minutes}-minute opening range cannot be built from these bars: {exc} "
                "Choose a length of at least one bar, or run the family on a finer timeframe."
            ) from exc


class _AuxiliaryLevels:
    """Prices a target may quote that are not part of the family's own range.

    All causal: the day's open is the open of a bar that has already started,
    previous-day extremes come from :func:`~perp_lab.crt.ranges.daily_ranges`
    (which shifts them), and "next liquidity" is chosen only from ranges that
    :func:`~perp_lab.crt.ranges.active_ranges_at` would return at that instant.
    """

    def __init__(
        self,
        bars: pl.DataFrame,
        reference_ranges: pl.DataFrame,
        *,
        session: SessionSpec | None,
        time_column: str = "open_time",
    ) -> None:
        self.daily = daily_ranges(bars) if bars.height > 1 else pl.DataFrame(schema=RANGE_SCHEMA)
        frames = [f for f in (reference_ranges, self.daily) if f.height]
        self.usable = (
            pl.concat(frames, how="diagonal").sort("available_from")
            if frames
            else pl.DataFrame(schema=RANGE_SCHEMA)
        )
        self._day_open: dict[date, float] = {}
        if bars.height:
            per_day = (
                bars.sort(time_column)
                .group_by(pl.col(time_column).dt.date().alias("_day"))
                .agg(pl.col("open").first().alias("_open"))
            )
            self._day_open = {r["_day"]: float(r["_open"]) for r in per_day.to_dicts()}

        self._session_open: list[tuple[datetime, datetime, float]] = []
        if session is not None and bars.height:
            times = bars[time_column]
            start, end = times.min(), times.max()
            if isinstance(start, datetime) and isinstance(end, datetime):
                for _day, opened, closed in session_windows(session, start, end):
                    inside = bars.filter(
                        (pl.col(time_column) >= opened) & (pl.col(time_column) < closed)
                    )
                    if inside.height:
                        self._session_open.append(
                            (opened, closed, float(inside["open"].first()))  # type: ignore[arg-type]
                        )

    def daily_open(self, moment: datetime) -> float | None:
        return self._day_open.get(moment.date())

    def session_open(self, moment: datetime) -> float | None:
        for opened, closed, price in self._session_open:
            if opened <= moment < closed:
                return price
        return None

    def previous_day(self, moment: datetime) -> tuple[float | None, float | None]:
        if self.daily.height == 0:
            return None, None
        rows = active_ranges_at(self.daily, moment)
        if rows.height == 0:
            return None, None
        last = rows.sort("available_from").tail(1).to_dicts()[0]
        return float(last["high"]), float(last["low"])

    def next_liquidity(self, moment: datetime, price: float) -> tuple[float | None, float | None]:
        """The nearest usable level above and below ``price``."""
        if self.usable.height == 0:
            return None, None
        rows = active_ranges_at(self.usable, moment)
        if rows.height == 0:
            return None, None
        levels = [
            float(v)
            for v in (*rows["high"].to_list(), *rows["low"].to_list())
            if v is not None and float(v) != price
        ]
        above = [level for level in levels if level > price]
        below = [level for level in levels if level < price]
        return (min(above) if above else None, max(below) if below else None)


# -- the engine -------------------------------------------------------------- #


@dataclass(frozen=True)
class CrtTrade:
    """One signal, all the way through the pipeline, kept for auditing."""

    signal: dict[str, Any]
    plan: TradePlan
    decision: RiskDecision | None
    outcome: TradeOutcome | None
    taken: bool
    reason: str


@dataclass(frozen=True)
class CrtRunResult:
    """Everything one pass produced, so a position can be traced to its cause."""

    positions: pl.DataFrame
    crt_signals: pl.DataFrame
    events: pl.DataFrame
    trades: tuple[CrtTrade, ...]
    ambiguity: AmbiguityReport
    fingerprint: str

    @property
    def taken(self) -> tuple[CrtTrade, ...]:
        return tuple(t for t in self.trades if t.taken)

    def refusals(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for trade in self.trades:
            if not trade.taken:
                counts[trade.reason] = counts.get(trade.reason, 0) + 1
        return counts


@dataclass(frozen=True)
class CrtStrategy:
    """One CRT family, ready for the existing backtester.

    Implements the repository's :class:`~perp_lab.strategies.base.Strategy`
    protocol: ``signals`` returns a target position per bar, decided at that
    bar's close, and the engine fills it at the next bar's open. Partial exits
    appear as fractional positions, which the engine already prices correctly.
    """

    family: str
    reference: ReferenceSpec
    interaction: InteractionConfig
    entry: EntryConfig
    exits: ExitConfig
    setup: SetupKind = SetupKind.REVERSAL
    trigger_states: tuple[LevelState, ...] = (LevelState.RECLAIMED,)
    require_sweep: bool = True
    min_sweep_bps: float = 0.0
    min_closes_outside: int = 0
    require_opposite_side_swept: bool = False
    session: str | None = None
    direction: str = "both"
    risk: RiskConfig | None = None
    atr_window: int = 14
    round_tag: str = CRT_ROUND_TAG
    symbol: str = ""
    timeframe: str = ""

    def __post_init__(self) -> None:
        validate_direction(self.direction)
        if self.family not in CRT_FAMILIES:
            raise CrtStrategyError(f"Unknown CRT family {self.family!r}; known: {CRT_FAMILIES}.")
        if not self.sides:
            raise CrtStrategyError(
                f"{self.family}: direction {self.direction!r} leaves no side to watch."
            )

    # -- identity ------------------------------------------------------------ #

    @property
    def name(self) -> str:
        return f"{self.family}_{self.reference.label}_{self.entry.rule}_{self.direction}"

    @property
    def sides(self) -> tuple[Side, ...]:
        """The sides whose setups trade in the allowed direction.

        This single expression is the whole of the long/short sharing: a side is
        watched when the direction it would trade is permitted. There is no
        mirrored branch to keep in step.
        """
        allowed = {"long": (1,), "short": (-1,), "both": (-1, 1)}[self.direction]
        return tuple(s for s in (Side.LOW, Side.HIGH) if self.setup.sign_for(s) in allowed)

    def signal_spec(self) -> SignalSpec:
        return SignalSpec(
            labels=(self.reference.label,),
            setup=self.setup,
            sides=self.sides,
            trigger_states=self.trigger_states,
            require_sweep=self.require_sweep,
            min_sweep_bps=self.min_sweep_bps,
            min_closes_outside=self.min_closes_outside,
            require_opposite_side_swept=self.require_opposite_side_swept,
            session=self.session,
        )

    def params(self) -> dict[str, object]:
        return {
            "family": self.family,
            "round_tag": self.round_tag,
            "reference": self.reference.label,
            "setup": str(self.setup),
            "direction": self.direction,
            "session": self.session,
            "entry_rule": str(self.entry.rule),
            "entry_max_wait_bars": self.entry.max_wait_bars,
            "sweep_bps": self.interaction.sweep_bps,
            "min_sweep_bps": self.min_sweep_bps,
            "reclaim_within_bars": self.interaction.reclaim_within_bars,
            "reclaim_confirmation_closes": self.interaction.reclaim_confirmation_closes,
            "require_sweep": self.require_sweep,
            "min_closes_outside": self.min_closes_outside,
            "require_opposite_side_swept": self.require_opposite_side_swept,
            "trigger_states": [str(s) for s in self.trigger_states],
            "stop_kind": str(self.exits.stop),
            "targets": [str(t.kind) for t in self.exits.targets],
            "target_fractions": [t.fraction for t in self.exits.targets],
            "move_to_breakeven_after_first_target": (
                self.exits.move_to_breakeven_after_first_target
            ),
            "trailing": None if self.exits.trailing is None else str(self.exits.trailing.kind),
            "time_stop_bars": self.exits.time_stop_bars,
            "close_at_window_end": self.exits.close_at_window_end,
            "min_net_reward_risk": self.exits.min_net_reward_risk,
            "cost_bps_per_side": self.exits.cost_bps_per_side,
        }

    def required_features(self) -> tuple[str, ...]:
        # Raw OHLC only: every level this family reads is built from the bars.
        return ()

    # -- execution ----------------------------------------------------------- #

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        """Target position per bar, decided at that bar's close."""
        return self.run(features).positions

    def run(self, features: pl.DataFrame, *, time_column: str = "open_time") -> CrtRunResult:
        """The full pass, with every intermediate kept for inspection."""
        needed = (time_column, "open", "high", "low", "close")
        missing = [c for c in needed if c not in features.columns]
        if missing:
            raise CrtStrategyError(f"{self.family} requires columns {missing}.")
        frame = features.sort(time_column)

        ranges = (
            self.reference.build(frame) if frame.height > 1 else pl.DataFrame(schema=RANGE_SCHEMA)
        )
        pipeline = run_crt_pipeline(
            frame,
            ranges,
            spec=self.signal_spec(),
            interaction=self.interaction,
            entry=self.entry,
            symbol=self.symbol,
            timeframe=self.timeframe,
            atr_window=self.atr_window,
            time_column=time_column,
        )
        bars, _ = bars_from_frame(frame, atr_window=self.atr_window, time_column=time_column)
        trades = self._trade(bars, pipeline, frame, ranges, time_column=time_column)
        side = self._positions(bars, trades)
        return CrtRunResult(
            positions=frame.select(time_column).with_columns(
                pl.Series(SIDE_COL, side, dtype=pl.Float64)
            ),
            crt_signals=pipeline.signals,
            events=pipeline.events,
            trades=trades,
            ambiguity=ambiguity_metrics([t.outcome for t in trades if t.outcome is not None]),
            fingerprint=pipeline.fingerprint,
        )

    def _trade(
        self,
        bars: Sequence[Bar],
        pipeline: CrtPipelineResult,
        frame: pl.DataFrame,
        ranges: pl.DataFrame,
        *,
        time_column: str,
    ) -> tuple[CrtTrade, ...]:
        """Turn signals into planned, permitted, simulated trades — in that order."""
        if pipeline.signals.height == 0:
            return ()
        auxiliary = _AuxiliaryLevels(
            frame, ranges, session=self.reference.session_spec, time_column=time_column
        )
        pivots: tuple[Pivot, ...] = ()
        if self.exits.stop is StopKind.STRUCTURAL:
            pivots = confirmed_pivots(bars, self.entry.pivot_span)
        ledger = RiskLedger(self.risk) if self.risk is not None else None

        trades: list[CrtTrade] = []
        busy_until = -1
        for row in pipeline.signals.sort("bar_index").to_dicts():
            index = int(row["bar_index"])
            sign = int(row["direction"])
            # One position at a time: overlapping the same hypothesis with itself
            # would size the bet by how often the trigger repeats.
            if index <= busy_until:
                trades.append(_untaken(row, "a position was already open"))
                continue
            if index + 1 >= len(bars):
                trades.append(_untaken(row, "no execution bar after the confirming close"))
                continue

            refs = self._references(row, sign, auxiliary, pivots, index)
            plan = plan_trade(
                sign=sign, entry_price=float(row["reference_price"]), refs=refs, config=self.exits
            )
            if not plan.accepted:
                trades.append(
                    CrtTrade(
                        signal=row,
                        plan=plan,
                        decision=None,
                        outcome=None,
                        taken=False,
                        reason=plan.refusal or "refused",
                    )
                )
                continue

            decision: RiskDecision | None = None
            if ledger is not None:
                decision = ledger.evaluate(_request(row, plan, index))
                if not decision.accepted:
                    trades.append(
                        CrtTrade(
                            signal=row,
                            plan=plan,
                            decision=decision,
                            outcome=None,
                            taken=False,
                            reason=decision.reason,
                        )
                    )
                    continue

            outcome = simulate_trade(
                plan,
                bars,
                config=self.exits,
                entry_bar_index=index + 1,
                window_end=row.get("session_end"),
            )
            busy_until = outcome.exit_bar if outcome.exit_bar is not None else index
            if ledger is not None:
                ledger.register_outcome(
                    resolved_at_bar=max(busy_until, index + 1),
                    won=outcome.modelled_r > 0,
                    day=row.get("session_day"),
                )
            trades.append(
                CrtTrade(
                    signal=row,
                    plan=plan,
                    decision=decision,
                    outcome=outcome,
                    taken=True,
                    reason="taken",
                )
            )
        return tuple(trades)

    def _references(
        self,
        row: dict[str, Any],
        sign: int,
        auxiliary: _AuxiliaryLevels,
        pivots: Sequence[Pivot],
        index: int,
    ) -> TradeReferences:
        moment = row["open_time"]
        entry = float(row["reference_price"])
        pdh, pdl = auxiliary.previous_day(moment)
        above, below = auxiliary.next_liquidity(moment, entry)
        structural: float | None = None
        if pivots:
            # The stop sits behind the structure the trade is leaning on, so it
            # is the pivot on the *opposite* side to the direction traded.
            pivot = latest_confirmed_pivot(pivots, Side.LOW if sign > 0 else Side.HIGH, index)
            structural = pivot.price if pivot is not None else None
        is_session_range = self.reference.kind in {"previous_session", "opening_range"}
        return TradeReferences(
            level=float(row["level"]),
            range_high=float(row["range_high"]),
            range_low=float(row["range_low"]),
            range_mid=_maybe(row.get("range_mid")),
            range_q25=_maybe(row.get("range_q25")),
            range_q75=_maybe(row.get("range_q75")),
            range_open=_maybe(row.get("range_open")),
            opposite_level=_maybe(row.get("opposite_level")),
            sweep_extreme=_maybe(row.get("sweep_extreme")),
            structural_level=structural,
            atr=_maybe(row.get("atr")),
            daily_open=auxiliary.daily_open(moment),
            session_open=auxiliary.session_open(moment),
            previous_day_high=pdh,
            previous_day_low=pdl,
            session_high=float(row["range_high"]) if is_session_range else None,
            session_low=float(row["range_low"]) if is_session_range else None,
            next_liquidity_above=above,
            next_liquidity_below=below,
        )

    def _positions(self, bars: Sequence[Bar], trades: Sequence[CrtTrade]) -> list[float]:
        """The side path: full size from the confirming close, then the exposure path."""
        side = [0.0] * len(bars)
        for trade in trades:
            if not trade.taken or trade.outcome is None:
                continue
            size = trade.decision.size_fraction if trade.decision is not None else 1.0
            signed = float(trade.signal["direction"]) * size
            side[int(trade.signal["bar_index"])] = signed
            for bar_index, remaining in trade.outcome.exposure:
                side[bar_index] = signed * remaining
        return side


def _maybe(value: object) -> float | None:
    return None if value is None else float(value)  # type: ignore[arg-type]


def _untaken(row: dict[str, Any], reason: str) -> CrtTrade:
    empty = TradePlan(
        sign=int(row["direction"]),
        entry_price=float(row["reference_price"]),
        stop_price=float("nan"),
        targets=(),
        risk_per_unit=0.0,
        gross_reward_risk=0.0,
        net_reward_risk=0.0,
        net_profit_bps=0.0,
        cost_per_unit=0.0,
        accepted=False,
        refusal=reason,
    )
    return CrtTrade(signal=row, plan=empty, decision=None, outcome=None, taken=False, reason=reason)


def _request(row: dict[str, Any], plan: TradePlan, index: int) -> TradeRequest:
    day = row.get("session_day")
    cutoff = row.get("entry_cutoff")
    return TradeRequest(
        bar_index=index,
        at=row["open_time"],
        sign=plan.sign,
        entry_price=plan.entry_price,
        stop_price=plan.stop_price,
        net_reward_risk=plan.net_reward_risk,
        level_key=f"{row['range_id']}:{row['level_side']}",
        session_key=f"{row['session']}:{day}" if row.get("session") else "",
        day=day if isinstance(day, date) else None,
        after_entry_cutoff=cutoff is not None and row["open_time"] >= cutoff,
    )


# -- the families ------------------------------------------------------------ #


def _interaction(
    *,
    sweep_bps: float,
    reclaim_within_bars: int = 3,
    reclaim_confirmation_closes: int = 1,
    acceptance_closes: int = 3,
    acceptance_bps: float = 10.0,
    retest_tolerance_bps: float = 10.0,
    max_bars_active: int = 96,
    min_wick_body_ratio: float | None = None,
) -> InteractionConfig:
    return InteractionConfig(
        sweep_bps=sweep_bps,
        reclaim_within_bars=reclaim_within_bars,
        reclaim_confirmation_closes=reclaim_confirmation_closes,
        acceptance_closes=acceptance_closes,
        acceptance_bps=acceptance_bps,
        retest_tolerance_bps=retest_tolerance_bps,
        max_bars_active=max_bars_active,
        min_wick_body_ratio=min_wick_body_ratio,
    )


def _exit_config(
    *,
    stop_kind: str,
    target_plan: str,
    time_stop_bars: int | None,
    min_net_reward_risk: float,
    cost_bps_per_side: float,
    stop_buffer_bps: float = 5.0,
    stop_atr_multiple: float = 1.0,
    breakeven: bool = False,
    close_at_window_end: bool = True,
) -> ExitConfig:
    targets = resolve_targets(target_plan)
    return ExitConfig(
        stop=StopKind(stop_kind),
        stop_buffer_bps=stop_buffer_bps,
        stop_atr_multiple=stop_atr_multiple,
        targets=targets,
        move_to_breakeven_after_first_target=breakeven and len(targets) > 1,
        time_stop_bars=time_stop_bars,
        close_at_window_end=close_at_window_end,
        min_net_reward_risk=min_net_reward_risk,
        cost_bps_per_side=cost_bps_per_side,
    )


def _entry(rule: str, *, max_wait_bars: int = 6, displacement_atr: float = 0.5) -> EntryConfig:
    return EntryConfig(
        rule=EntryRule(rule),
        max_wait_bars=max_wait_bars,
        displacement_atr=displacement_atr,
    )


@dataclass(frozen=True)
class FamilyMechanics:
    """The mechanics every family shares, fixed rather than searched.

    Held apart from the searched grid on purpose: the study counts every
    distinct configuration towards its multiple-testing correction, so widening
    the grid has a statistical price. These values are documented defaults, not
    tuned ones.
    """

    stop_buffer_bps: float = 5.0
    stop_atr_multiple: float = 1.0
    max_wait_bars: int = 6
    reclaim_within_bars: int = 3
    reclaim_confirmation_closes: int = 1
    acceptance_closes: int = 3
    acceptance_bps: float = 10.0
    retest_tolerance_bps: float = 10.0
    max_bars_active: int = 96
    displacement_atr: float = 0.5
    cost_bps_per_side: float = 5.0
    breakeven_after_first_target: bool = True
    atr_window: int = 14
    risk: RiskConfig | None = None


DEFAULT_MECHANICS = FamilyMechanics()


def _assemble(
    family: str,
    *,
    reference: ReferenceSpec,
    setup: SetupKind,
    trigger_states: tuple[LevelState, ...],
    entry_rule: str,
    sweep_bps: float,
    stop_kind: str,
    target_plan: str,
    time_stop_bars: int | None,
    min_net_reward_risk: float,
    direction: str,
    session: str | None = None,
    require_sweep: bool = True,
    min_sweep_bps: float = 0.0,
    min_closes_outside: int = 0,
    require_opposite_side_swept: bool = False,
    min_wick_body_ratio: float | None = None,
    mechanics: FamilyMechanics = DEFAULT_MECHANICS,
) -> CrtStrategy:
    """One constructor for all nine families; only the arguments differ."""
    return CrtStrategy(
        family=family,
        reference=reference,
        interaction=_interaction(
            sweep_bps=sweep_bps,
            reclaim_within_bars=mechanics.reclaim_within_bars,
            reclaim_confirmation_closes=mechanics.reclaim_confirmation_closes,
            acceptance_closes=mechanics.acceptance_closes,
            acceptance_bps=mechanics.acceptance_bps,
            retest_tolerance_bps=mechanics.retest_tolerance_bps,
            max_bars_active=mechanics.max_bars_active,
            min_wick_body_ratio=min_wick_body_ratio,
        ),
        entry=_entry(
            entry_rule,
            max_wait_bars=mechanics.max_wait_bars,
            displacement_atr=mechanics.displacement_atr,
        ),
        exits=_exit_config(
            stop_kind=stop_kind,
            target_plan=target_plan,
            time_stop_bars=time_stop_bars,
            min_net_reward_risk=min_net_reward_risk,
            cost_bps_per_side=mechanics.cost_bps_per_side,
            stop_buffer_bps=mechanics.stop_buffer_bps,
            stop_atr_multiple=mechanics.stop_atr_multiple,
            breakeven=mechanics.breakeven_after_first_target,
            close_at_window_end=session is not None,
        ),
        setup=setup,
        trigger_states=trigger_states,
        require_sweep=require_sweep,
        min_sweep_bps=min_sweep_bps,
        min_closes_outside=min_closes_outside,
        require_opposite_side_swept=require_opposite_side_swept,
        session=session,
        direction=direction,
        risk=mechanics.risk,
        atr_window=mechanics.atr_window,
    )


def crt_htf_range_reversal(
    *,
    candle_timeframe: str = "4h",
    entry_rule: str = "reclaim_close",
    sweep_bps: float = 5.0,
    stop_kind: str = "wick_extreme",
    target_plan: str = "mid_then_opposite",
    time_stop_bars: int | None = 24,
    min_net_reward_risk: float = 1.0,
    direction: str = "both",
    mechanics: FamilyMechanics = DEFAULT_MECHANICS,
) -> CrtStrategy:
    """Freeze a closed HTF candle, wait for one extreme to be swept and reclaimed.

    The reference is the last *completed* 1h/4h/daily candle. A candle still
    forming has no final high, and using one is the classic way this idea leaks.
    """
    return _assemble(
        "crt_htf_range_reversal",
        reference=ReferenceSpec(kind="previous_candle", timeframe=candle_timeframe),
        setup=SetupKind.REVERSAL,
        trigger_states=(LevelState.RECLAIMED,),
        entry_rule=entry_rule,
        sweep_bps=sweep_bps,
        stop_kind=stop_kind,
        target_plan=target_plan,
        time_stop_bars=time_stop_bars,
        min_net_reward_risk=min_net_reward_risk,
        direction=direction,
        mechanics=mechanics,
    )


def previous_day_reclaim(
    *,
    direction: str,
    entry_rule: str = "reclaim_close",
    sweep_bps: float = 5.0,
    min_sweep_bps: float = 5.0,
    stop_kind: str = "wick_extreme",
    target_plan: str = "mid_then_opposite",
    time_stop_bars: int | None = 24,
    min_net_reward_risk: float = 1.0,
    mechanics: FamilyMechanics = DEFAULT_MECHANICS,
) -> CrtStrategy:
    """The shared body of ``pdl_reclaim_long`` and ``pdh_reclaim_short``.

    The two named families differ by one argument. Writing the short side out
    again would double the surface on which they could disagree about what a
    sweep is, and the point of the exercise is that they cannot.
    """
    family = "pdl_reclaim_long" if direction == "long" else "pdh_reclaim_short"
    return _assemble(
        family,
        reference=ReferenceSpec(kind="previous_day"),
        setup=SetupKind.REVERSAL,
        trigger_states=(LevelState.RECLAIMED,),
        entry_rule=entry_rule,
        sweep_bps=sweep_bps,
        stop_kind=stop_kind,
        target_plan=target_plan,
        time_stop_bars=time_stop_bars,
        min_net_reward_risk=min_net_reward_risk,
        direction=direction,
        min_sweep_bps=min_sweep_bps,
        mechanics=mechanics,
    )


def _fixed_side(direction: str, family: str, kwargs: dict[str, Any]) -> CrtStrategy:
    if "direction" in kwargs:
        raise CrtStrategyError(
            f"{family} is the {direction} side of previous_day_reclaim by definition; "
            "call previous_day_reclaim directly to choose a side."
        )
    return previous_day_reclaim(direction=direction, **kwargs)


def pdl_reclaim_long(**kwargs: Any) -> CrtStrategy:
    """Previous-day low swept, reclaimed, traded long."""
    return _fixed_side("long", "pdl_reclaim_long", kwargs)


def pdh_reclaim_short(**kwargs: Any) -> CrtStrategy:
    """Previous-day high swept, reclaimed, traded short. Same code, other side."""
    return _fixed_side("short", "pdh_reclaim_short", kwargs)


def session_liquidity_sweep(
    *,
    swept_session: str = "asia",
    trading_session: str = "london",
    entry_rule: str = "reclaim_close",
    sweep_bps: float = 5.0,
    stop_kind: str = "wick_extreme",
    target_plan: str = "mid_then_opposite",
    time_stop_bars: int | None = 12,
    min_net_reward_risk: float = 1.0,
    direction: str = "both",
    mechanics: FamilyMechanics = DEFAULT_MECHANICS,
) -> CrtStrategy:
    """One session takes the liquidity resting at another session's extreme.

    The swept range must have *closed* — an Asian high is only a level once Asia
    is over — and the trade may only be entered inside the trading session, up to
    its entry cutoff.
    """
    return _assemble(
        "session_liquidity_sweep",
        reference=ReferenceSpec(kind="previous_session", session=swept_session),
        setup=SetupKind.REVERSAL,
        trigger_states=(LevelState.RECLAIMED,),
        entry_rule=entry_rule,
        sweep_bps=sweep_bps,
        stop_kind=stop_kind,
        target_plan=target_plan,
        time_stop_bars=time_stop_bars,
        min_net_reward_risk=min_net_reward_risk,
        direction=direction,
        session=trading_session,
        mechanics=mechanics,
    )


def session_range_rotation(
    *,
    session: str = "london",
    entry_rule: str = "reclaim_close",
    sweep_bps: float = 5.0,
    stop_kind: str = "range_extreme",
    target_plan: str = "mid",
    time_stop_bars: int | None = 12,
    min_net_reward_risk: float = 1.0,
    direction: str = "both",
    mechanics: FamilyMechanics = DEFAULT_MECHANICS,
) -> CrtStrategy:
    """Rejection at one edge of a closed session range, rotating towards the other.

    Unlike the sweep families this one triggers on ``REJECTED``, so it does not
    require the level to have been taken out by a configured depth first — a
    rotation is the case where the edge simply holds.
    """
    return _assemble(
        "session_range_rotation",
        reference=ReferenceSpec(kind="previous_session", session=session),
        setup=SetupKind.REVERSAL,
        trigger_states=(LevelState.REJECTED,),
        entry_rule=entry_rule,
        sweep_bps=sweep_bps,
        stop_kind=stop_kind,
        target_plan=target_plan,
        time_stop_bars=time_stop_bars,
        min_net_reward_risk=min_net_reward_risk,
        direction=direction,
        session=session,
        require_sweep=False,
        mechanics=mechanics,
    )


def opening_range_breakout_retest(
    *,
    minutes: int = 60,
    session: str = "new_york",
    entry_rule: str = "first_retest",
    stop_kind: str = "range_extreme",
    target_plan: str = "r_multiple_2",
    time_stop_bars: int | None = 12,
    min_net_reward_risk: float = 1.0,
    direction: str = "both",
    mechanics: FamilyMechanics = DEFAULT_MECHANICS,
) -> CrtStrategy:
    """A *closing* break of the opening range, then acceptance or a retest.

    The trigger is ``ACCEPTED_OUTSIDE``, which is reached only by closes beyond
    the level. A bar that wicks through and closes back inside never reaches it,
    which is the distinction the whole family rests on.
    """
    return _assemble(
        "opening_range_breakout_retest",
        reference=ReferenceSpec(kind="opening_range", session=session, minutes=minutes),
        setup=SetupKind.CONTINUATION,
        trigger_states=(LevelState.ACCEPTED_OUTSIDE,),
        entry_rule=entry_rule,
        sweep_bps=5.0,
        stop_kind=stop_kind,
        target_plan=target_plan,
        time_stop_bars=time_stop_bars,
        min_net_reward_risk=min_net_reward_risk,
        direction=direction,
        session=session,
        require_sweep=False,
        mechanics=mechanics,
    )


def failed_breakout_reversal(
    *,
    reference_kind: str = "previous_day",
    candle_timeframe: str = "4h",
    entry_rule: str = "reclaim_close",
    sweep_bps: float = 5.0,
    stop_kind: str = "wick_extreme",
    target_plan: str = "mid_then_opposite",
    time_stop_bars: int | None = 24,
    min_net_reward_risk: float = 1.0,
    direction: str = "both",
    mechanics: FamilyMechanics = DEFAULT_MECHANICS,
) -> CrtStrategy:
    """A real break that never earned acceptance, then recovered against it.

    ``min_closes_outside`` is what separates this from an ordinary sweep: at
    least one bar must have *closed* beyond the level, so the market genuinely
    left the range before failing to hold it.
    """
    reference = (
        ReferenceSpec(kind="previous_day")
        if reference_kind == "previous_day"
        else ReferenceSpec(kind="previous_candle", timeframe=candle_timeframe)
    )
    return _assemble(
        "failed_breakout_reversal",
        reference=reference,
        setup=SetupKind.REVERSAL,
        trigger_states=(LevelState.RECLAIMED,),
        entry_rule=entry_rule,
        sweep_bps=sweep_bps,
        stop_kind=stop_kind,
        target_plan=target_plan,
        time_stop_bars=time_stop_bars,
        min_net_reward_risk=min_net_reward_risk,
        direction=direction,
        min_closes_outside=1,
        mechanics=mechanics,
    )


def double_sweep_reversal(
    *,
    reference_kind: str = "previous_day",
    candle_timeframe: str = "4h",
    entry_rule: str = "reclaim_close",
    sweep_bps: float = 5.0,
    stop_kind: str = "wick_extreme",
    target_plan: str = "mid",
    time_stop_bars: int | None = 24,
    min_net_reward_risk: float = 1.0,
    direction: str = "both",
    mechanics: FamilyMechanics = DEFAULT_MECHANICS,
) -> CrtStrategy:
    """Both extremes taken, traded only from the second one.

    Which extreme went first is recorded on the signal
    (``first_swept_side``), because "both sides were swept" without an order is
    two different setups wearing one name.
    """
    reference = (
        ReferenceSpec(kind="previous_day")
        if reference_kind == "previous_day"
        else ReferenceSpec(kind="previous_candle", timeframe=candle_timeframe)
    )
    return _assemble(
        "double_sweep_reversal",
        reference=reference,
        setup=SetupKind.REVERSAL,
        trigger_states=(LevelState.RECLAIMED,),
        entry_rule=entry_rule,
        sweep_bps=sweep_bps,
        stop_kind=stop_kind,
        target_plan=target_plan,
        time_stop_bars=time_stop_bars,
        min_net_reward_risk=min_net_reward_risk,
        direction=direction,
        require_opposite_side_swept=True,
        mechanics=mechanics,
    )


def crt_three_candle_model(
    *,
    candle_timeframe: str = "4h",
    displacement_atr: float = 0.5,
    sweep_bps: float = 5.0,
    stop_kind: str = "wick_extreme",
    target_plan: str = "mid_then_opposite",
    time_stop_bars: int | None = 24,
    min_net_reward_risk: float = 1.0,
    direction: str = "both",
    mechanics: FamilyMechanics = DEFAULT_MECHANICS,
) -> CrtStrategy:
    """Candle one is the range, candle two takes an extreme, candle three displaces.

    The third leg is not "price went the other way" but a bar whose *body*
    travels a configured multiple of ATR in the trade's direction, which is what
    :data:`~perp_lab.crt.entries.EntryRule.DISPLACEMENT_CONFIRMATION` measures.
    """
    return _assemble(
        "crt_three_candle_model",
        reference=ReferenceSpec(kind="previous_candle", timeframe=candle_timeframe),
        setup=SetupKind.REVERSAL,
        trigger_states=(LevelState.RECLAIMED, LevelState.REJECTED),
        entry_rule="displacement_confirmation",
        sweep_bps=sweep_bps,
        stop_kind=stop_kind,
        target_plan=target_plan,
        time_stop_bars=time_stop_bars,
        min_net_reward_risk=min_net_reward_risk,
        direction=direction,
        mechanics=replace(mechanics, displacement_atr=displacement_atr),
    )


CRT_BUILDERS = {
    "crt_htf_range_reversal": crt_htf_range_reversal,
    "pdl_reclaim_long": pdl_reclaim_long,
    "pdh_reclaim_short": pdh_reclaim_short,
    "session_liquidity_sweep": session_liquidity_sweep,
    "session_range_rotation": session_range_rotation,
    "opening_range_breakout_retest": opening_range_breakout_retest,
    "failed_breakout_reversal": failed_breakout_reversal,
    "double_sweep_reversal": double_sweep_reversal,
    "crt_three_candle_model": crt_three_candle_model,
}


__all__ = [
    "CRT_BUILDERS",
    "CRT_FAMILIES",
    "CRT_ROUND_TAG",
    "TARGET_PLANS",
    "CrtRunResult",
    "CrtStrategy",
    "CrtStrategyError",
    "CrtTrade",
    "FamilyMechanics",
    "ReferenceSpec",
    "crt_htf_range_reversal",
    "crt_three_candle_model",
    "double_sweep_reversal",
    "failed_breakout_reversal",
    "opening_range_breakout_retest",
    "pdh_reclaim_short",
    "pdl_reclaim_long",
    "previous_day_reclaim",
    "resolve_targets",
    "session_liquidity_sweep",
    "session_range_rotation",
]
