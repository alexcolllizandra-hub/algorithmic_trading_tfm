"""Entry rules, on bars where the admissible bar is obvious by construction.

Each rule is checked twice: once on the bar it must fire, and once on a bar that
looks similar but must not. The two properties that would invalidate everything
downstream get their own classes — a pivot is unknown until the bars on its right
have closed, and the long and short readings of the same geometry must agree
exactly rather than approximately.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from perp_lab.crt.entries import (
    EntryConfig,
    EntryContext,
    EntryError,
    EntryRule,
    bps_between,
    bps_to_price,
    confirmed_pivots,
    latest_confirmed_pivot,
    required_conditions,
    resolve_entry,
    waived_conditions,
)
from perp_lab.crt.states import Bar, Side

START = datetime(2024, 1, 1, tzinfo=UTC)
LEVEL = 100.0


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


def _context(sign: int = 1, *, trigger_bar: int = 0, level: float = LEVEL) -> EntryContext:
    return EntryContext(
        range_id="r0",
        label="previous_day",
        side=Side.LOW if sign > 0 else Side.HIGH,
        sign=sign,
        level=level,
        trigger_bar=trigger_bar,
        trigger_at=START + timedelta(hours=trigger_bar),
        trigger_state="reclaimed",
    )


def _mirror(bar: Bar, level: float = LEVEL) -> Bar:
    """The same bar reflected through the level: a long becomes its short twin."""
    return Bar(
        index=bar.index,
        open_time=bar.open_time,
        open=2 * level - bar.open,
        high=2 * level - bar.low,
        low=2 * level - bar.high,
        close=2 * level - bar.close,
        atr=bar.atr,
    )


class TestBasisPointHelpers:
    def test_a_distance_is_expressed_against_its_reference(self) -> None:
        assert bps_between(0.5, 100.0) == pytest.approx(50.0)

    def test_direction_is_dropped_because_depth_has_no_sign(self) -> None:
        assert bps_between(-0.5, 100.0) == bps_between(0.5, 100.0)

    def test_the_two_helpers_are_inverses(self) -> None:
        assert bps_to_price(100.0, bps_between(0.5, 100.0)) == pytest.approx(0.5)

    def test_a_zero_reference_gives_zero_rather_than_an_error(self) -> None:
        assert bps_between(1.0, 0.0) == 0.0


class TestConditionBookkeeping:
    def test_the_earliest_rule_requires_nothing_optional(self) -> None:
        assert required_conditions(EntryRule.RECLAIM_CLOSE) == ()

    def test_every_optional_condition_is_either_required_or_waived(self) -> None:
        for rule in EntryRule:
            overlap = set(required_conditions(rule)) & set(waived_conditions(rule))
            assert not overlap
            assert len(required_conditions(rule)) + len(waived_conditions(rule)) == 5

    def test_a_retest_rule_waives_displacement_explicitly(self) -> None:
        """The point of the record: what the rule let pass, not only what it demanded."""
        assert "displacement" in waived_conditions(EntryRule.FIRST_RETEST)
        assert "retest" in required_conditions(EntryRule.FIRST_RETEST)


class TestConfigurationRefusesToBeInert:
    def test_a_zero_displacement_floor_is_rejected(self) -> None:
        with pytest.raises(EntryError, match="positive displacement floor"):
            EntryConfig(
                rule=EntryRule.DISPLACEMENT_CONFIRMATION,
                displacement_atr=0.0,
                displacement_bps=0.0,
            )

    def test_a_setup_must_have_at_least_one_bar_to_enter_on(self) -> None:
        with pytest.raises(EntryError, match="max_wait_bars"):
            EntryConfig(max_wait_bars=0)

    def test_a_pivot_needs_a_bar_on_each_side(self) -> None:
        with pytest.raises(EntryError, match="pivot_span"):
            EntryConfig(pivot_span=0)

    def test_structure_break_without_pivots_is_a_misconfiguration_not_silence(self) -> None:
        config = EntryConfig(rule=EntryRule.STRUCTURE_BREAK)
        with pytest.raises(EntryError, match="confirmed pivot series"):
            resolve_entry(config, _context())


class TestReclaimClose:
    def test_it_fires_on_the_bar_that_completed_the_setup(self) -> None:
        evaluator = resolve_entry(EntryConfig(rule=EntryRule.RECLAIM_CLOSE), _context())
        confirmation = evaluator.observe(_bar(0, 99.5, 100.6, 99.0, 100.5))
        assert confirmation is not None
        assert confirmation.bars_waited == 0
        assert confirmation.reference_price == pytest.approx(100.5)

    def test_the_confirming_close_is_the_last_price_the_plan_may_use(self) -> None:
        """Not the next open: that price is unknown when the decision is made."""
        evaluator = resolve_entry(EntryConfig(rule=EntryRule.RECLAIM_CLOSE), _context())
        confirmation = evaluator.observe(_bar(0, 99.5, 100.6, 99.0, 100.5))
        assert confirmation is not None
        assert confirmation.reference_price == 100.5

    def test_a_settled_evaluator_never_fires_again(self) -> None:
        evaluator = resolve_entry(EntryConfig(rule=EntryRule.RECLAIM_CLOSE), _context())
        assert evaluator.observe(_bar(0, 99.5, 100.6, 99.0, 100.5)) is not None
        assert evaluator.observe(_bar(1, 100.5, 101.0, 100.2, 100.9)) is None
        assert evaluator.settled


class TestNextBarOpen:
    def test_it_waits_one_bar_and_requires_the_level_to_still_hold(self) -> None:
        evaluator = resolve_entry(EntryConfig(rule=EntryRule.NEXT_BAR_OPEN), _context())
        assert evaluator.observe(_bar(0, 99.5, 100.6, 99.0, 100.5)) is None
        confirmation = evaluator.observe(_bar(1, 100.5, 101.0, 100.2, 100.9))
        assert confirmation is not None
        assert confirmation.bars_waited == 1

    def test_a_close_back_through_the_level_cancels_the_idea(self) -> None:
        evaluator = resolve_entry(EntryConfig(rule=EntryRule.NEXT_BAR_OPEN), _context())
        evaluator.observe(_bar(0, 99.5, 100.6, 99.0, 100.5))
        assert evaluator.observe(_bar(1, 100.4, 100.5, 99.0, 99.2)) is None
        assert evaluator.observe(_bar(2, 99.2, 101.0, 99.1, 100.9)) is None


class TestFirstRetest:
    def test_a_return_to_the_level_within_tolerance_confirms(self) -> None:
        config = EntryConfig(rule=EntryRule.FIRST_RETEST, retest_tolerance_bps=10.0)
        evaluator = resolve_entry(config, _context())
        evaluator.observe(_bar(0, 99.5, 100.6, 99.0, 100.5))
        confirmation = evaluator.observe(_bar(1, 100.4, 100.7, 100.05, 100.6))
        assert confirmation is not None
        assert confirmation.detail["retest_gap_bps"] == pytest.approx(5.0)

    def test_price_that_never_comes_back_does_not_confirm(self) -> None:
        """10 bps of 100 is one cent; a low of 101 is a hundred times too far."""
        config = EntryConfig(rule=EntryRule.FIRST_RETEST, retest_tolerance_bps=10.0)
        evaluator = resolve_entry(config, _context())
        evaluator.observe(_bar(0, 99.5, 100.6, 99.0, 100.5))
        assert evaluator.observe(_bar(1, 101.2, 101.5, 101.0, 101.4)) is None

    def test_the_trigger_bar_is_not_its_own_retest(self) -> None:
        config = EntryConfig(rule=EntryRule.FIRST_RETEST, retest_tolerance_bps=100.0)
        evaluator = resolve_entry(config, _context())
        assert evaluator.observe(_bar(0, 99.5, 100.6, 99.9, 100.5)) is None


class TestRetestWithRejection:
    def test_a_retest_shaped_like_a_rejection_confirms(self) -> None:
        """Body 0.1, wick towards the level 0.35: a ratio of 3.5."""
        config = EntryConfig(
            rule=EntryRule.RETEST_WITH_REJECTION,
            retest_tolerance_bps=10.0,
            rejection_wick_body_ratio=1.0,
        )
        evaluator = resolve_entry(config, _context())
        evaluator.observe(_bar(0, 99.5, 100.6, 99.0, 100.5))
        confirmation = evaluator.observe(_bar(1, 100.4, 100.55, 100.05, 100.5))
        assert confirmation is not None
        assert confirmation.detail["wick_body_ratio"] == pytest.approx(3.5)

    def test_a_retest_without_the_shape_is_refused(self) -> None:
        config = EntryConfig(
            rule=EntryRule.RETEST_WITH_REJECTION,
            retest_tolerance_bps=10.0,
            rejection_wick_body_ratio=2.0,
        )
        evaluator = resolve_entry(config, _context())
        evaluator.observe(_bar(0, 99.5, 100.6, 99.0, 100.5))
        assert evaluator.observe(_bar(1, 100.05, 100.9, 100.03, 100.85)) is None


class TestDisplacementConfirmation:
    def test_a_body_beyond_the_atr_floor_confirms(self) -> None:
        """ATR 1.0 and a floor of half an ATR: the body must travel 0.5."""
        config = EntryConfig(rule=EntryRule.DISPLACEMENT_CONFIRMATION, displacement_atr=0.5)
        evaluator = resolve_entry(config, _context())
        evaluator.observe(_bar(0, 99.5, 100.6, 99.0, 100.5))
        confirmation = evaluator.observe(_bar(1, 100.2, 101.0, 100.1, 100.9))
        assert confirmation is not None
        assert confirmation.detail["displacement"] == pytest.approx(0.7)
        assert confirmation.detail["displacement_floor"] == pytest.approx(0.5)

    def test_a_small_body_is_not_displacement(self) -> None:
        config = EntryConfig(rule=EntryRule.DISPLACEMENT_CONFIRMATION, displacement_atr=0.5)
        evaluator = resolve_entry(config, _context())
        evaluator.observe(_bar(0, 99.5, 100.6, 99.0, 100.5))
        assert evaluator.observe(_bar(1, 100.2, 100.6, 100.1, 100.5)) is None

    def test_a_basis_point_floor_can_stand_in_for_a_missing_atr(self) -> None:
        config = EntryConfig(
            rule=EntryRule.DISPLACEMENT_CONFIRMATION,
            displacement_atr=0.5,
            displacement_bps=30.0,
        )
        evaluator = resolve_entry(config, _context())
        evaluator.observe(_bar(0, 99.5, 100.6, 99.0, 100.5, atr=None))
        confirmation = evaluator.observe(_bar(1, 100.2, 101.0, 100.1, 100.6, atr=None))
        assert confirmation is not None
        assert confirmation.detail["displacement_floor"] == pytest.approx(0.3)


class TestPivotsDoNotRepaint:
    """The property that makes STRUCTURE_BREAK admissible at all."""

    def _swing(self) -> list[Bar]:
        # A single clean swing high at index 2 and a swing low at index 4.
        return [
            _bar(0, 99.0, 99.5, 98.5, 99.2),
            _bar(1, 99.2, 100.2, 99.1, 100.0),
            _bar(2, 100.0, 101.0, 99.8, 100.8),
            _bar(3, 100.8, 100.9, 99.9, 100.1),
            _bar(4, 100.1, 100.2, 99.0, 99.4),
            _bar(5, 99.4, 100.4, 99.3, 100.3),
            _bar(6, 100.3, 101.6, 100.2, 101.5),
        ]

    def test_a_swing_high_is_dated_at_the_bar_that_confirmed_it(self) -> None:
        pivots = confirmed_pivots(self._swing(), span=1)
        high = next(p for p in pivots if p.kind is Side.HIGH and p.index == 2)
        assert high.price == pytest.approx(101.0)
        assert high.confirmed_index == 3
        assert high.confirmation_lag == 1

    def test_a_wider_span_pushes_confirmation_further_into_the_future(self) -> None:
        pivots = confirmed_pivots(self._swing(), span=2)
        high = next(p for p in pivots if p.kind is Side.HIGH and p.index == 2)
        assert high.confirmed_index == 4
        assert high.confirmation_lag == 2

    def test_the_pivot_is_invisible_on_the_bar_that_formed_it(self) -> None:
        pivots = confirmed_pivots(self._swing(), span=1)
        assert latest_confirmed_pivot(pivots, Side.HIGH, bar_index=2) is None
        seen = latest_confirmed_pivot(pivots, Side.HIGH, bar_index=3)
        assert seen is not None and seen.index == 2

    def test_a_flat_top_produces_no_pivot_rather_than_an_arbitrary_one(self) -> None:
        bars = [
            _bar(0, 99.0, 100.0, 98.5, 99.5),
            _bar(1, 99.5, 101.0, 99.0, 100.5),
            _bar(2, 100.5, 101.0, 100.0, 100.8),
            _bar(3, 100.8, 101.0, 100.1, 100.9),
            _bar(4, 100.9, 100.5, 99.5, 100.0),
        ]
        assert not [p for p in confirmed_pivots(bars, span=1) if p.kind is Side.HIGH]

    def test_a_series_shorter_than_the_window_has_no_pivots(self) -> None:
        assert confirmed_pivots(self._swing()[:2], span=2) == ()

    def test_truncating_the_series_cannot_change_a_confirmed_pivot(self) -> None:
        """The invariance the entry rule relies on, checked directly."""
        full = confirmed_pivots(self._swing(), span=1)
        for k in range(1, 8):
            prefix = confirmed_pivots(self._swing()[:k], span=1)
            assert prefix == tuple(p for p in full if p.confirmed_index < k)

    def test_a_close_beyond_a_confirmed_swing_high_confirms_the_entry(self) -> None:
        bars = self._swing()
        pivots = confirmed_pivots(bars, span=1)
        config = EntryConfig(rule=EntryRule.STRUCTURE_BREAK, pivot_span=1)
        evaluator = resolve_entry(config, _context(trigger_bar=4), pivots=pivots)
        assert evaluator.observe(bars[4]) is None
        assert evaluator.observe(bars[5]) is None  # 100.3 is still below the 101.0 swing
        confirmation = evaluator.observe(bars[6])
        assert confirmation is not None
        assert confirmation.detail["pivot_index"] == 2.0
        assert confirmation.detail["pivot_confirmation_lag"] == 1.0


class TestLifecycle:
    def test_a_setup_that_is_never_confirmed_expires(self) -> None:
        config = EntryConfig(rule=EntryRule.FIRST_RETEST, max_wait_bars=2)
        evaluator = resolve_entry(config, _context())
        for index in range(5):
            evaluator.observe(_bar(index, 105.0, 106.0, 104.0, 105.5))
        assert evaluator.expired
        assert evaluator.settled

    def test_an_expired_setup_cannot_be_revived_by_a_late_retest(self) -> None:
        config = EntryConfig(
            rule=EntryRule.FIRST_RETEST, max_wait_bars=1, retest_tolerance_bps=10.0
        )
        evaluator = resolve_entry(config, _context())
        evaluator.observe(_bar(0, 99.5, 100.6, 99.0, 100.5))
        evaluator.observe(_bar(1, 105.0, 106.0, 104.0, 105.5))
        evaluator.observe(_bar(2, 105.0, 106.0, 104.0, 105.5))
        assert evaluator.observe(_bar(3, 100.4, 100.7, 100.02, 100.6)) is None

    def test_cancelling_a_pending_setup_settles_it(self) -> None:
        evaluator = resolve_entry(EntryConfig(rule=EntryRule.FIRST_RETEST), _context())
        evaluator.observe(_bar(0, 99.5, 100.6, 99.0, 100.5))
        evaluator.cancel()
        assert evaluator.cancelled
        assert evaluator.observe(_bar(1, 100.4, 100.7, 100.02, 100.6)) is None

    def test_bars_before_the_trigger_are_ignored(self) -> None:
        evaluator = resolve_entry(
            EntryConfig(rule=EntryRule.RECLAIM_CLOSE), _context(trigger_bar=3)
        )
        assert evaluator.observe(_bar(0, 99.5, 100.6, 99.0, 100.5)) is None
        assert not evaluator.settled


class TestLongShortSymmetry:
    """The same geometry, reflected through the level, must read identically."""

    CASES = (
        (EntryRule.RECLAIM_CLOSE, {}),
        (EntryRule.NEXT_BAR_OPEN, {}),
        (EntryRule.FIRST_RETEST, {"retest_tolerance_bps": 100.0}),
        (EntryRule.RETEST_WITH_REJECTION, {"retest_tolerance_bps": 100.0}),
        (EntryRule.DISPLACEMENT_CONFIRMATION, {"displacement_atr": 0.5}),
    )

    @pytest.mark.parametrize(("rule", "overrides"), CASES)
    def test_a_mirrored_setup_confirms_on_the_same_bar(
        self, rule: EntryRule, overrides: dict[str, float]
    ) -> None:
        long_bars = [
            _bar(0, 99.5, 100.6, 99.0, 100.5),
            _bar(1, 100.4, 100.55, 100.05, 100.5),
            _bar(2, 100.5, 101.4, 100.4, 101.3),
        ]
        config = EntryConfig(rule=rule, **overrides)  # type: ignore[arg-type]
        long_eval = resolve_entry(config, _context(sign=1))
        short_eval = resolve_entry(config, _context(sign=-1))

        long_hits = [long_eval.observe(bar) for bar in long_bars]
        short_hits = [short_eval.observe(_mirror(bar)) for bar in long_bars]

        assert [c is None for c in long_hits] == [c is None for c in short_hits]
        for long_hit, short_hit in zip(long_hits, short_hits, strict=True):
            if long_hit is None or short_hit is None:
                continue
            assert long_hit.bar_index == short_hit.bar_index
            assert long_hit.bars_waited == short_hit.bars_waited
            assert short_hit.reference_price == pytest.approx(2 * LEVEL - long_hit.reference_price)

    def test_at_least_one_rule_actually_fired_in_the_symmetry_fixture(self) -> None:
        """Guards the parametrised test above from passing on universal silence."""
        config = EntryConfig(rule=EntryRule.RECLAIM_CLOSE)
        evaluator = resolve_entry(config, _context(sign=-1))
        assert evaluator.observe(_mirror(_bar(0, 99.5, 100.6, 99.0, 100.5))) is not None
