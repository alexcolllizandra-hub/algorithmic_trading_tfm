"""Stops, targets, refusals and the intrabar assumption.

The arithmetic in these tests is deliberately done by hand in the docstrings: a
reward:risk ratio that is only checked against the code that produced it is not
checked at all. The intrabar cases have their own class because the conservative
policy is an assumption, and an assumption that is not tested is a claim.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from perp_lab.crt.exits import (
    ExitConfig,
    ExitError,
    ExitReason,
    IntrabarPolicy,
    StopKind,
    TargetKind,
    TargetSpec,
    TradeOutcome,
    TradePlan,
    TradeReferences,
    TrailingKind,
    TrailingSpec,
    ambiguity_metrics,
    plan_trade,
    simulate_trade,
    stop_price,
    target_price,
)
from perp_lab.crt.states import Bar

START = datetime(2024, 1, 1, tzinfo=UTC)
LEVEL = 100.0
ENTRY = 100.5


def _bar(index: int, o: float, h: float, low: float, c: float, atr: float | None = 1.0) -> Bar:
    return Bar(
        index=index,
        open_time=START + timedelta(hours=index),
        open=o,
        high=h,
        low=low,
        close=c,
        atr=atr,
    )


def _mirror(bar: Bar) -> Bar:
    return Bar(
        index=bar.index,
        open_time=bar.open_time,
        open=2 * LEVEL - bar.open,
        high=2 * LEVEL - bar.low,
        low=2 * LEVEL - bar.high,
        close=2 * LEVEL - bar.close,
        atr=bar.atr,
    )


def _refs(**overrides: float | None) -> TradeReferences:
    base: dict[str, float | None] = {
        "level": LEVEL,
        "range_high": 105.0,
        "range_low": 99.0,
        "range_mid": 102.0,
        "range_q25": 100.5,
        "range_q75": 103.5,
        "opposite_level": 105.0,
        "sweep_extreme": 99.0,
        "atr": 1.0,
    }
    base.update(overrides)
    return TradeReferences(**base)  # type: ignore[arg-type]


def _mirrored_refs() -> TradeReferences:
    """The same references reflected through the level, for the short twin."""
    return TradeReferences(
        level=LEVEL,
        range_high=2 * LEVEL - 99.0,
        range_low=2 * LEVEL - 105.0,
        range_mid=2 * LEVEL - 102.0,
        opposite_level=2 * LEVEL - 105.0,
        sweep_extreme=2 * LEVEL - 99.0,
        atr=1.0,
    )


def _config(**overrides: object) -> ExitConfig:
    base: dict[str, object] = {
        "stop": StopKind.WICK_EXTREME,
        "stop_buffer_bps": 0.0,
        "targets": (TargetSpec(TargetKind.R_MULTIPLE, r_multiple=2.0),),
        "cost_bps_per_side": 0.0,
        "min_net_reward_risk": 1.0,
    }
    base.update(overrides)
    return ExitConfig(**base)  # type: ignore[arg-type]


class TestStopPlacement:
    def test_a_wick_stop_sits_beyond_the_sweep_plus_a_buffer(self) -> None:
        """5 bps of an entry at 100.5 is 0.050250, below a sweep low of 99."""
        config = _config(stop_buffer_bps=5.0)
        assert stop_price(1, ENTRY, _refs(), config) == pytest.approx(99.0 - 0.050250)

    def test_a_range_stop_sits_beyond_the_level_itself(self) -> None:
        config = _config(stop=StopKind.RANGE_EXTREME)
        assert stop_price(1, ENTRY, _refs(), config) == pytest.approx(LEVEL)

    def test_an_atr_stop_scales_with_volatility(self) -> None:
        config = _config(stop=StopKind.ATR_DISTANCE, stop_atr_multiple=1.5)
        assert stop_price(1, ENTRY, _refs(atr=2.0), config) == pytest.approx(ENTRY - 3.0)

    def test_a_percentage_stop_is_a_share_of_the_entry(self) -> None:
        config = _config(stop=StopKind.FIXED_PCT, stop_pct=1.0)
        assert stop_price(1, ENTRY, _refs(), config) == pytest.approx(ENTRY * 0.99)

    def test_a_structural_stop_uses_the_swing_the_trade_leans_on(self) -> None:
        config = _config(stop=StopKind.STRUCTURAL)
        assert stop_price(1, ENTRY, _refs(structural_level=98.5), config) == pytest.approx(98.5)

    def test_a_missing_anchor_produces_nan_rather_than_a_guess(self) -> None:
        config = _config(stop=StopKind.STRUCTURAL)
        assert stop_price(1, ENTRY, _refs(structural_level=None), config) != stop_price(
            1, ENTRY, _refs(structural_level=None), config
        )

    def test_short_stops_are_the_mirror_of_long_ones(self) -> None:
        config = _config()
        long_stop = stop_price(1, ENTRY, _refs(), config)
        short_stop = stop_price(-1, 2 * LEVEL - ENTRY, _mirrored_refs(), config)
        assert short_stop == pytest.approx(2 * LEVEL - long_stop)


class TestTargetResolution:
    def test_an_r_multiple_is_measured_from_the_risk(self) -> None:
        spec = TargetSpec(TargetKind.R_MULTIPLE, r_multiple=2.0)
        price = target_price(spec, sign=1, entry_price=ENTRY, risk_per_unit=1.5, refs=_refs())
        assert price == pytest.approx(ENTRY + 3.0)

    def test_a_missing_reference_resolves_to_nothing(self) -> None:
        spec = TargetSpec(TargetKind.DAILY_OPEN)
        assert (
            target_price(spec, sign=1, entry_price=ENTRY, risk_per_unit=1.5, refs=_refs()) is None
        )

    def test_next_liquidity_picks_the_side_the_trade_is_going(self) -> None:
        refs = _refs(next_liquidity_above=104.0, next_liquidity_below=97.0)
        spec = TargetSpec(TargetKind.NEXT_LIQUIDITY)
        assert target_price(spec, sign=1, entry_price=ENTRY, risk_per_unit=1.5, refs=refs) == 104.0
        assert target_price(spec, sign=-1, entry_price=ENTRY, risk_per_unit=1.5, refs=refs) == 97.0

    def test_a_target_must_close_a_positive_share_of_the_position(self) -> None:
        with pytest.raises(ExitError, match="positive share"):
            TargetSpec(TargetKind.RANGE_MID, fraction=0.0)


class TestConfigurationIsCoherent:
    def test_target_fractions_must_close_the_whole_position(self) -> None:
        with pytest.raises(ExitError, match="sum to"):
            _config(
                targets=(
                    TargetSpec(TargetKind.RANGE_MID, fraction=0.5),
                    TargetSpec(TargetKind.OPPOSITE_EXTREME, fraction=0.2),
                )
            )

    def test_more_than_three_targets_is_not_managed(self) -> None:
        with pytest.raises(ExitError, match="one, two or three"):
            _config(
                targets=tuple(TargetSpec(TargetKind.R_MULTIPLE, fraction=0.25) for _ in range(4))
            )

    def test_break_even_needs_something_left_to_protect(self) -> None:
        with pytest.raises(ExitError, match="single"):
            _config(move_to_breakeven_after_first_target=True)


class TestPlanningRefusals:
    def test_a_stop_on_the_winning_side_of_the_entry_is_refused(self) -> None:
        plan = plan_trade(
            sign=1, entry_price=ENTRY, refs=_refs(sweep_extreme=101.0), config=_config()
        )
        assert not plan.accepted
        assert plan.refusal is not None and "losing side" in plan.refusal

    def test_an_unresolvable_stop_is_refused_with_its_reason(self) -> None:
        config = _config(stop=StopKind.ATR_DISTANCE)
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(atr=None), config=config)
        assert not plan.accepted
        assert plan.refusal is not None and "atr_distance" in plan.refusal

    def test_a_target_behind_the_entry_is_refused(self) -> None:
        config = _config(targets=(TargetSpec(TargetKind.RANGE_MID),))
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(range_mid=99.5), config=config)
        assert not plan.accepted
        assert plan.refusal is not None and "behind the entry" in plan.refusal

    def test_targets_must_be_ordered_away_from_the_entry(self) -> None:
        config = _config(
            targets=(
                TargetSpec(TargetKind.OPPOSITE_EXTREME, fraction=0.5),
                TargetSpec(TargetKind.RANGE_MID, fraction=0.5),
            )
        )
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        assert not plan.accepted
        assert plan.refusal is not None and "ordered" in plan.refusal

    def test_a_target_that_cannot_pay_the_round_trip_is_refused(self) -> None:
        """Entry 100.5, target 100.51: one cent of reward against 10 bps of cost."""
        config = _config(
            targets=(TargetSpec(TargetKind.RANGE_MID),),
            cost_bps_per_side=5.0,
            min_net_reward_risk=0.0,
        )
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(range_mid=100.51), config=config)
        assert not plan.accepted
        assert plan.refusal is not None and "round-trip cost" in plan.refusal

    def test_a_refusal_keeps_the_arithmetic_that_produced_it(self) -> None:
        config = _config(min_net_reward_risk=3.0)
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        assert not plan.accepted
        assert plan.net_reward_risk == pytest.approx(2.0)
        assert plan.targets  # the numbers survive the verdict, so it can be audited

    def test_a_refused_plan_must_not_be_simulated(self) -> None:
        config = _config(min_net_reward_risk=3.0)
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        with pytest.raises(ExitError, match="refused plan"):
            simulate_trade(
                plan, [_bar(1, 100.5, 101.0, 100.0, 100.8)], config=config, entry_bar_index=1
            )


class TestCostsBiteBeforeTheTrade:
    def test_without_costs_the_ratio_is_the_geometric_one(self) -> None:
        """Risk 1.5 to a 2R target: exactly 2.0 when nothing is charged."""
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=_config())
        assert plan.accepted
        assert plan.risk_per_unit == pytest.approx(1.5)
        assert plan.gross_reward_risk == pytest.approx(2.0)
        assert plan.net_reward_risk == pytest.approx(2.0)

    def test_costs_are_charged_to_the_reward_and_to_the_risk(self) -> None:
        """A round trip of 10 bps on 100.5 is 0.1005: (3.0-0.1005)/(1.5+0.1005)."""
        config = _config(cost_bps_per_side=5.0)
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        assert plan.net_reward_risk == pytest.approx(2.8995 / 1.6005)
        assert plan.net_reward_risk < plan.gross_reward_risk

    def test_a_trade_below_the_minimum_net_ratio_is_refused(self) -> None:
        config = _config(cost_bps_per_side=5.0, min_net_reward_risk=2.0)
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        assert not plan.accepted
        assert plan.refusal is not None and "reward:risk" in plan.refusal

    def test_the_same_trade_is_accepted_when_the_bar_is_lower(self) -> None:
        config = _config(cost_bps_per_side=5.0, min_net_reward_risk=1.5)
        assert plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config).accepted

    def test_a_minimum_profit_floor_can_refuse_a_thin_trade(self) -> None:
        config = _config(cost_bps_per_side=5.0, min_net_reward_risk=0.0, min_net_profit_bps=1_000.0)
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        assert not plan.accepted
        assert plan.refusal is not None and "net profit" in plan.refusal


class TestIntrabarAmbiguity:
    """Both levels inside one bar, and no data that can order them."""

    def _plan_and_config(self) -> tuple[TradePlan, ExitConfig]:
        config = _config()
        return plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config), config

    def test_a_bar_containing_both_resolves_as_the_stop(self) -> None:
        """Stop 99.0 and target 103.5 are both inside a bar spanning 98.5 to 104."""
        plan, config = self._plan_and_config()
        bars = [_bar(1, 100.5, 104.0, 98.5, 101.0)]
        outcome = simulate_trade(plan, bars, config=config, entry_bar_index=1)
        assert outcome.exit_reason is ExitReason.STOP
        assert outcome.modelled_r == pytest.approx(-1.0)

    def test_the_assumption_is_recorded_on_the_trade(self) -> None:
        plan, config = self._plan_and_config()
        bars = [_bar(1, 100.5, 104.0, 98.5, 101.0)]
        outcome = simulate_trade(plan, bars, config=config, entry_bar_index=1)
        assert outcome.ambiguous
        assert outcome.ambiguous_bars == (1,)
        assert outcome.fills[-1].ambiguous

    def test_an_unambiguous_winner_is_not_flagged(self) -> None:
        plan, config = self._plan_and_config()
        bars = [_bar(1, 100.5, 104.0, 100.2, 103.9)]
        outcome = simulate_trade(plan, bars, config=config, entry_bar_index=1)
        assert outcome.exit_reason is ExitReason.TARGET
        assert not outcome.ambiguous

    def test_the_policy_is_the_only_one_offered(self) -> None:
        """A single member is the honest surface: there is no optimistic reading."""
        assert tuple(IntrabarPolicy) == (IntrabarPolicy.STOP_FIRST,)
        assert _config().intrabar_policy is IntrabarPolicy.STOP_FIRST

    def test_the_metric_counts_affected_trades_and_bars(self) -> None:
        plan, config = self._plan_and_config()
        ambiguous = simulate_trade(
            plan, [_bar(1, 100.5, 104.0, 98.5, 101.0)], config=config, entry_bar_index=1
        )
        clean = simulate_trade(
            plan, [_bar(1, 100.5, 104.0, 100.2, 103.9)], config=config, entry_bar_index=1
        )
        report = ambiguity_metrics([ambiguous, clean])
        assert report.n_trades == 2
        assert report.n_ambiguous_trades == 1
        assert report.n_ambiguous_bars == 1
        assert report.ambiguous_trade_rate == pytest.approx(0.5)
        assert report.policy is IntrabarPolicy.STOP_FIRST

    def test_an_empty_book_reports_no_rate_rather_than_dividing_by_zero(self) -> None:
        assert ambiguity_metrics([]).ambiguous_trade_rate == 0.0


class TestManagement:
    def _partial_config(self) -> ExitConfig:
        """Two halves at 1R (102.0) and 3R (105.0), with break-even after the first."""
        return _config(
            targets=(
                TargetSpec(TargetKind.R_MULTIPLE, fraction=0.5, r_multiple=1.0),
                TargetSpec(TargetKind.R_MULTIPLE, fraction=0.5, r_multiple=3.0),
            ),
            move_to_breakeven_after_first_target=True,
        )

    def test_the_first_target_closes_only_its_share(self) -> None:
        config = self._partial_config()
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        bars = [
            _bar(1, 100.6, 102.2, 100.5, 102.0),
            _bar(2, 102.0, 102.5, 101.8, 102.2),
        ]
        outcome = simulate_trade(plan, bars, config=config, entry_bar_index=1)
        assert outcome.fills[0].reason is ExitReason.TARGET
        assert outcome.fills[0].fraction == pytest.approx(0.5)
        assert dict(outcome.exposure)[1] == pytest.approx(0.5)

    def test_the_stop_moves_to_the_entry_after_the_first_target(self) -> None:
        config = self._partial_config()
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        bars = [
            _bar(1, 100.6, 102.2, 100.5, 102.0),
            _bar(2, 102.0, 102.1, 100.4, 100.6),  # comes back to the entry
        ]
        outcome = simulate_trade(plan, bars, config=config, entry_bar_index=1)
        assert outcome.moved_to_breakeven
        assert outcome.fills[-1].reason is ExitReason.BREAK_EVEN
        assert outcome.fills[-1].level == pytest.approx(ENTRY)
        assert outcome.modelled_r == pytest.approx(0.5)  # half at 1R, half at nothing

    def test_both_targets_can_fill_inside_one_bar(self) -> None:
        config = self._partial_config()
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        outcome = simulate_trade(
            plan, [_bar(1, 100.6, 105.5, 100.5, 105.2)], config=config, entry_bar_index=1
        )
        assert [f.reason for f in outcome.fills] == [ExitReason.TARGET, ExitReason.TARGET]
        assert outcome.modelled_r == pytest.approx(2.0)  # half at 1R plus half at 3R

    def test_three_partials_are_supported(self) -> None:
        config = _config(
            targets=(
                TargetSpec(TargetKind.R_MULTIPLE, fraction=1 / 3, r_multiple=1.0),
                TargetSpec(TargetKind.R_MULTIPLE, fraction=1 / 3, r_multiple=1.5),
                TargetSpec(TargetKind.R_MULTIPLE, fraction=1 / 3, r_multiple=3.0),
            )
        )
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        outcome = simulate_trade(
            plan, [_bar(1, 100.6, 105.5, 100.5, 105.2)], config=config, entry_bar_index=1
        )
        # Three thirds leave a floating-point residue; the trade must still be
        # closed by the third target rather than by a phantom dust fill.
        assert len(outcome.fills) == 3
        assert outcome.closed
        assert outcome.modelled_r == pytest.approx((1.0 + 1.5 + 3.0) / 3.0)

    def test_a_time_exit_closes_what_is_left(self) -> None:
        config = _config(time_stop_bars=2)
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        bars = [_bar(i, 100.6, 101.0, 100.2, 100.8) for i in range(1, 6)]
        outcome = simulate_trade(plan, bars, config=config, entry_bar_index=1)
        assert outcome.exit_reason is ExitReason.TIME_EXIT
        assert outcome.bars_held == 2

    def test_a_session_trade_is_closed_at_the_end_of_its_window(self) -> None:
        config = _config(close_at_window_end=True)
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        bars = [_bar(i, 100.6, 101.0, 100.2, 100.8) for i in range(1, 5)]
        outcome = simulate_trade(
            plan, bars, config=config, entry_bar_index=1, window_end=START + timedelta(hours=3)
        )
        assert outcome.exit_reason is ExitReason.SESSION_END
        assert outcome.exit_bar == 3

    def test_a_trade_still_open_when_the_sample_ends_says_so(self) -> None:
        config = _config()
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        bars = [_bar(i, 100.6, 101.0, 100.2, 100.8) for i in range(1, 4)]
        outcome = simulate_trade(plan, bars, config=config, entry_bar_index=1)
        assert not outcome.closed
        assert outcome.exit_reason is ExitReason.END_OF_DATA

    def test_a_trailing_stop_only_ratchets_towards_the_trade(self) -> None:
        config = _config(trailing=TrailingSpec(kind=TrailingKind.PRIOR_EXTREME, lookback_bars=1))
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        bars = [
            _bar(1, 100.6, 101.5, 100.4, 101.4),  # trail rises to 100.4
            _bar(2, 101.4, 102.0, 101.0, 101.9),  # trail rises to 101.0
            _bar(3, 101.9, 102.0, 100.9, 101.0),  # takes out 101.0
        ]
        outcome = simulate_trade(plan, bars, config=config, entry_bar_index=1)
        assert outcome.exit_reason is ExitReason.TRAILING_STOP
        assert outcome.fills[-1].level == pytest.approx(101.0)

    def test_a_signal_on_the_last_bar_has_no_trade_to_simulate(self) -> None:
        config = _config()
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        with pytest.raises(ExitError, match="No bar at or after"):
            simulate_trade(
                plan, [_bar(0, 100.0, 100.6, 99.0, 100.5)], config=config, entry_bar_index=1
            )

    def test_the_stop_is_live_on_the_very_first_bar_of_exposure(self) -> None:
        config = _config()
        plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        outcome = simulate_trade(
            plan, [_bar(1, 100.4, 100.5, 98.0, 98.5)], config=config, entry_bar_index=1
        )
        assert outcome.exit_bar == 1
        assert outcome.exit_reason is ExitReason.STOP


class TestLongShortSymmetry:
    """A short is the long reflected through the level, to the last decimal."""

    def _pair(self, bars: list[Bar]) -> tuple[TradeOutcome, TradeOutcome]:
        config = _config()
        long_plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        short_plan = plan_trade(
            sign=-1, entry_price=2 * LEVEL - ENTRY, refs=_mirrored_refs(), config=config
        )
        long_out = simulate_trade(long_plan, bars, config=config, entry_bar_index=1)
        short_out = simulate_trade(
            short_plan, [_mirror(b) for b in bars], config=config, entry_bar_index=1
        )
        return long_out, short_out

    def test_the_planned_prices_mirror_exactly(self) -> None:
        config = _config()
        long_plan = plan_trade(sign=1, entry_price=ENTRY, refs=_refs(), config=config)
        short_plan = plan_trade(
            sign=-1, entry_price=2 * LEVEL - ENTRY, refs=_mirrored_refs(), config=config
        )
        assert short_plan.stop_price == pytest.approx(2 * LEVEL - long_plan.stop_price)
        assert short_plan.targets[0].price == pytest.approx(2 * LEVEL - long_plan.targets[0].price)
        assert short_plan.risk_per_unit == pytest.approx(long_plan.risk_per_unit)

    def test_a_mirrored_winner_wins_by_the_same_amount(self) -> None:
        long_out, short_out = self._pair([_bar(1, 100.6, 104.0, 100.4, 103.8)])
        assert long_out.exit_reason is short_out.exit_reason
        assert long_out.modelled_r == pytest.approx(short_out.modelled_r)

    def test_a_mirrored_loser_loses_by_the_same_amount(self) -> None:
        long_out, short_out = self._pair([_bar(1, 100.4, 100.6, 98.5, 98.8)])
        assert long_out.exit_reason is short_out.exit_reason
        assert long_out.modelled_r == pytest.approx(short_out.modelled_r)

    def test_a_mirrored_ambiguity_is_flagged_on_both_sides(self) -> None:
        long_out, short_out = self._pair([_bar(1, 100.5, 104.0, 98.5, 101.0)])
        assert long_out.ambiguous_bars == short_out.ambiguous_bars
