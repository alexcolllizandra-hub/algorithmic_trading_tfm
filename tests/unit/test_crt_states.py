"""The liquidity state machine, on bars built so the right answer is known.

Every scenario below is a handful of bars where the intended reading is obvious
to a human, so a disagreement is a bug in the machine rather than an argument
about interpretation. The cases that matter most are the ones that must *not*
fire: a shallow poke is not a sweep, a close back inside without a preceding
sweep is not a reclaim, and a reclaim that arrives too late is not a reclaim at
all.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from perp_lab.crt.states import (
    Bar,
    InteractionConfig,
    LevelState,
    LevelTracker,
    Side,
    run_tracker,
)

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


def _tracker(side: Side = Side.LOW, **overrides: object) -> LevelTracker:
    config = InteractionConfig(**overrides)  # type: ignore[arg-type]
    return LevelTracker(
        range_id="test",
        label="previous_day",
        side=side,
        level=LEVEL,
        available_from=START,
        config=config,
    )


class TestSweepBelow:
    def test_a_deep_penetration_is_a_sweep(self) -> None:
        """5 bps of 100 is 0.05, so a low of 99.9 is 10 bps deep.

        With one confirming close required, a bar that sweeps and closes back
        inside completes the whole sequence on its own — the classic single-candle
        sweep and reclaim.
        """
        tracker = _tracker(sweep_bps=5.0)
        tracker.update(_bar(0, 101.0, 101.5, 99.9, 100.5))
        assert tracker.max_depth_bps == pytest.approx(10.0)
        assert tracker.sweep_bar == 0
        assert tracker.state is LevelState.RECLAIMED

    def test_a_shallow_poke_is_rejected_but_never_swept(self) -> None:
        """Rejection without a sweep is not a setup.

        Price dipped through and closed back inside, which looks like the
        pattern, but it never went deep enough for there to be anything to
        reclaim, so no sweep is recorded and nothing downstream may fire.
        """
        tracker = _tracker(sweep_bps=50.0, pierce_bps=1.0)
        tracker.update(_bar(0, 101.0, 101.5, 99.9, 101.0))
        assert tracker.sweep_bar is None
        assert tracker.state is LevelState.REJECTED

    def test_reaching_the_level_exactly_counts_as_a_touch(self) -> None:
        """A low equal to the level is a touch, not an approach.

        The clean test that holds to the tick is the case traders care about
        most, and a strict inequality would file it under "never got there".
        """
        tracker = _tracker()
        tracker.update(_bar(0, 101.0, 101.5, 100.0, 101.0))
        assert tracker.state is LevelState.TOUCHED

    def test_coming_close_without_touching_is_only_an_approach(self) -> None:
        tracker = _tracker(approach_bps=20.0)
        tracker.update(_bar(0, 101.0, 101.5, 100.15, 101.0))
        assert tracker.state is LevelState.APPROACHING

    def test_staying_far_away_leaves_the_level_untouched(self) -> None:
        tracker = _tracker(approach_bps=5.0)
        tracker.update(_bar(0, 110.0, 111.0, 109.0, 110.0))
        assert tracker.state is LevelState.AVAILABLE

    def test_an_atr_floor_can_make_a_sweep_harder_than_the_bps_rule(self) -> None:
        """With ATR at 1.0, half an ATR is 0.5, i.e. 50 bps of a level of 100."""
        tracker = _tracker(sweep_bps=5.0, sweep_atr_fraction=0.5)
        tracker.update(_bar(0, 101.0, 101.5, 99.9, 100.5, atr=1.0))
        assert tracker.sweep_bar is None


class TestReclaim:
    def test_a_sweep_then_a_confirmed_close_inside_is_a_reclaim(self) -> None:
        tracker = _tracker(sweep_bps=5.0, reclaim_confirmation_closes=1)
        run_tracker(tracker, [_bar(0, 101.0, 101.5, 99.5, 100.4)])
        assert tracker.state is LevelState.RECLAIMED

    def test_a_close_inside_without_a_prior_sweep_is_not_a_reclaim(self) -> None:
        """The ordering requirement, stated as a test.

        Unordered booleans would fire here: price closed inside the range, but
        it never left it far enough for there to be anything to reclaim.
        """
        tracker = _tracker(sweep_bps=100.0)
        run_tracker(tracker, [_bar(0, 101.0, 101.5, 99.95, 100.5)])
        assert tracker.state is not LevelState.RECLAIMED

    def test_two_confirming_closes_can_be_demanded(self) -> None:
        tracker = _tracker(sweep_bps=5.0, reclaim_confirmation_closes=2)
        run_tracker(
            tracker,
            [
                _bar(0, 101.0, 101.5, 99.5, 100.4),
                _bar(1, 100.4, 101.0, 100.2, 100.8),
            ],
        )
        assert tracker.state is LevelState.RECLAIMED

    def test_one_close_is_not_enough_when_two_are_demanded(self) -> None:
        tracker = _tracker(sweep_bps=5.0, reclaim_confirmation_closes=2)
        run_tracker(tracker, [_bar(0, 101.0, 101.5, 99.5, 100.4)])
        assert tracker.state is LevelState.REJECTED

    def test_a_reclaim_that_arrives_too_late_invalidates_instead(self) -> None:
        # Acceptance is held off deliberately so the late reclaim is what
        # resolves the sequence; otherwise three closes outside would settle it
        # first, which is correct behaviour but a different test.
        tracker = _tracker(sweep_bps=5.0, reclaim_within_bars=1, acceptance_closes=10)
        run_tracker(
            tracker,
            [
                _bar(0, 101.0, 101.5, 99.5, 99.6),
                _bar(1, 99.6, 99.8, 99.4, 99.5),
                _bar(2, 99.5, 99.7, 99.3, 99.4),
                _bar(3, 99.4, 100.6, 99.3, 100.5),
            ],
        )
        assert tracker.state is LevelState.INVALIDATED

    def test_a_reclaim_buffer_rejects_a_close_sitting_on_the_level(self) -> None:
        tracker = _tracker(sweep_bps=5.0, reclaim_buffer_bps=20.0)
        run_tracker(tracker, [_bar(0, 101.0, 101.5, 99.5, 100.01)])
        assert tracker.state is not LevelState.RECLAIMED

    def test_a_wick_shape_filter_can_veto_an_otherwise_valid_reclaim(self) -> None:
        # Body 100.4 -> 100.5 is 0.1; lower wick is 100.4 - 99.5 = 0.9, ratio 9.
        tracker = _tracker(sweep_bps=5.0, min_wick_body_ratio=20.0)
        run_tracker(tracker, [_bar(0, 100.4, 101.5, 99.5, 100.5)])
        assert tracker.state is LevelState.REJECTED


class TestAfterReclaim:
    def test_losing_the_level_again_is_a_failed_reclaim(self) -> None:
        tracker = _tracker(sweep_bps=5.0)
        run_tracker(
            tracker,
            [
                _bar(0, 101.0, 101.5, 99.5, 100.4),
                _bar(1, 100.4, 100.6, 99.0, 99.2),
            ],
        )
        assert tracker.state is LevelState.FAILED_RECLAIM

    def test_returning_to_the_reclaimed_level_is_a_retest(self) -> None:
        tracker = _tracker(sweep_bps=5.0, retest_tolerance_bps=30.0)
        run_tracker(
            tracker,
            [
                _bar(0, 101.0, 101.5, 99.5, 100.9),
                _bar(1, 100.9, 101.2, 100.1, 100.8),
            ],
        )
        assert tracker.state is LevelState.RETESTED

    def test_running_away_from_the_level_leaves_it_merely_reclaimed(self) -> None:
        tracker = _tracker(sweep_bps=5.0, retest_tolerance_bps=5.0)
        run_tracker(
            tracker,
            [
                _bar(0, 101.0, 101.5, 99.5, 100.9),
                _bar(1, 100.9, 103.0, 100.8, 102.5),
            ],
        )
        assert tracker.state is LevelState.RECLAIMED


class TestAcceptanceOutside:
    def test_consecutive_closes_far_beyond_the_level_are_acceptance(self) -> None:
        tracker = _tracker(sweep_bps=5.0, acceptance_closes=2, acceptance_bps=10.0)
        run_tracker(
            tracker,
            [
                _bar(0, 101.0, 101.2, 99.5, 99.6),
                _bar(1, 99.6, 99.8, 99.2, 99.3),
            ],
        )
        assert tracker.state is LevelState.ACCEPTED_OUTSIDE

    def test_closes_that_hug_the_level_do_not_count_as_acceptance(self) -> None:
        tracker = _tracker(sweep_bps=5.0, acceptance_closes=2, acceptance_bps=100.0)
        run_tracker(
            tracker,
            [
                _bar(0, 101.0, 101.2, 99.5, 99.95),
                _bar(1, 99.95, 100.0, 99.9, 99.96),
            ],
        )
        assert tracker.state is not LevelState.ACCEPTED_OUTSIDE


class TestSymmetry:
    def test_the_short_side_mirrors_the_long_side_exactly(self) -> None:
        """The same story reflected through the level must reach the same state.

        Long and short share one implementation precisely so they cannot drift
        apart; this asserts the sharing actually works.
        """
        low_side = _tracker(Side.LOW, sweep_bps=5.0)
        run_tracker(low_side, [_bar(0, 101.0, 101.5, 99.5, 100.4)])

        high_side = _tracker(Side.HIGH, sweep_bps=5.0)
        # Reflect every price through the level: p -> 2*LEVEL - p.
        run_tracker(high_side, [_bar(0, 99.0, 100.5, 98.5, 99.6)])

        assert low_side.state is high_side.state is LevelState.RECLAIMED
        assert low_side.max_depth_bps == pytest.approx(high_side.max_depth_bps)

    def test_the_short_side_treats_an_upward_sweep_as_the_deep_one(self) -> None:
        tracker = _tracker(Side.HIGH, sweep_bps=5.0)
        tracker.update(_bar(0, 99.0, 100.5, 98.5, 99.6))
        assert tracker.max_depth_bps == pytest.approx(50.0)


class TestCausalityAndLifetime:
    def test_bars_before_availability_are_ignored_entirely(self) -> None:
        """Feeding history to a level that did not exist yet must change nothing."""
        tracker = LevelTracker(
            range_id="test",
            label="previous_day",
            side=Side.LOW,
            level=LEVEL,
            available_from=START + timedelta(hours=5),
            config=InteractionConfig(),
        )
        for index in range(5):
            tracker.update(_bar(index, 101.0, 101.5, 90.0, 91.0))

        assert tracker.state is LevelState.AVAILABLE
        assert tracker.bars_seen == 0
        assert tracker.transitions == []

    def test_an_unresolved_sequence_expires_on_its_bar_budget(self) -> None:
        tracker = _tracker(max_bars_active=3, approach_bps=0.0)
        run_tracker(tracker, [_bar(i, 110.0, 111.0, 109.0, 110.0) for i in range(6)])
        assert tracker.state is LevelState.EXPIRED

    def test_a_resolved_sequence_stops_consuming_bars(self) -> None:
        tracker = _tracker(sweep_bps=5.0, acceptance_closes=1, acceptance_bps=10.0)
        run_tracker(tracker, [_bar(i, 99.0, 99.5, 98.0, 98.5) for i in range(10)])
        assert tracker.finished
        assert tracker.bars_seen < 10


class TestAuditTrail:
    def test_every_transition_records_the_bar_and_the_measurement(self) -> None:
        tracker = _tracker(sweep_bps=5.0)
        run_tracker(tracker, [_bar(0, 101.0, 101.5, 99.5, 100.4)])

        assert tracker.transitions
        for transition in tracker.transitions:
            assert transition.previous is not transition.state
            assert transition.level == LEVEL
            assert transition.at.tzinfo is not None
            assert transition.describe()

    def test_the_reclaim_transition_carries_the_shape_that_justified_it(self) -> None:
        tracker = _tracker(sweep_bps=5.0)
        run_tracker(tracker, [_bar(0, 101.0, 101.5, 99.5, 100.4)])

        rejections = [t for t in tracker.transitions if t.state is LevelState.REJECTED]
        assert rejections
        assert "wick_body_ratio" in rejections[0].detail
        assert "wick_recovery" in rejections[0].detail


class TestConfigurationIsChecked:
    def test_a_sweep_shallower_than_a_pierce_is_incoherent(self) -> None:
        with pytest.raises(ValueError, match="shallower"):
            InteractionConfig(pierce_bps=10.0, sweep_bps=5.0)

    def test_a_reclaim_needs_at_least_one_confirming_close(self) -> None:
        with pytest.raises(ValueError, match="confirming close"):
            InteractionConfig(reclaim_confirmation_closes=0)

    def test_a_reclaim_needs_a_window_to_happen_in(self) -> None:
        with pytest.raises(ValueError, match="at least one bar"):
            InteractionConfig(reclaim_within_bars=0)
