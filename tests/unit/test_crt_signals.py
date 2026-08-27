"""The event and signal pipeline, on a series whose story is known bar by bar.

The scenario is one clean box followed by a sweep of its low and an immediate
close back inside, because every assertion here should be checkable by reading
the fixture rather than by running the code.

:class:`TestTruncationInvariance` is the important one. Everything else in the
CRT layer can be wrong in a way that shows up as a poor result; a signal that
changes when later bars arrive is a leak, and a leak shows up as a *good* one.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from perp_lab.crt.entries import EntryConfig, EntryRule
from perp_lab.crt.ranges import RANGE_SCHEMA, daily_ranges
from perp_lab.crt.signals import (
    EVENT_SCHEMA,
    SIGNAL_SCHEMA,
    SetupKind,
    SignalError,
    SignalSpec,
    bars_from_frame,
    config_fingerprint,
    explain_signal,
    levels_readable_at,
    run_crt_pipeline,
    summarise,
)
from perp_lab.crt.states import InteractionConfig, LevelState, Side

START = datetime(2024, 1, 1, tzinfo=UTC)

Row = tuple[float, float, float, float]


_BAR_SCHEMA: dict[str, pl.DataType] = {
    "open_time": pl.Datetime("ms", "UTC"),
    "open": pl.Float64(),
    "high": pl.Float64(),
    "low": pl.Float64(),
    "close": pl.Float64(),
    "volume": pl.Float64(),
}


def _frame(rows: list[Row]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame(schema=_BAR_SCHEMA)
    return pl.DataFrame(
        {
            "open_time": [START + timedelta(hours=i) for i in range(len(rows))],
            "open": [r[0] for r in rows],
            "high": [r[1] for r in rows],
            "low": [r[2] for r in rows],
            "close": [r[3] for r in rows],
            "volume": [10.0 + i for i in range(len(rows))],
        }
    ).with_columns(pl.col("open_time").dt.cast_time_unit("ms").dt.replace_time_zone("UTC"))


def _sweep_and_reclaim() -> pl.DataFrame:
    """Day one is a box between 99 and 110; day two sweeps 99 and closes back in.

    The sweep is on bar 29 (hour five of day two): a low of 97 is 202 bps below
    the previous-day low of 99, and the close of 100.5 is back inside, so the
    whole sequence completes on that one bar.
    """
    rows: list[Row] = [(105.0, 110.0, 99.0, 105.0) for _ in range(24)]
    for i in range(24):
        if i == 5:
            rows.append((101.0, 101.5, 97.0, 100.5))
        elif i > 5:
            base = 100.5 + (i - 5) * 0.8
            rows.append((base, base + 0.6, base - 0.4, base + 0.5))
        else:
            rows.append((104.0, 105.0, 103.0, 104.0))
    return _frame(rows)


def _run(
    bars: pl.DataFrame,
    *,
    spec: SignalSpec | None = None,
    interaction: InteractionConfig | None = None,
    entry: EntryConfig | None = None,
):
    ranges = daily_ranges(bars) if bars.height > 1 else pl.DataFrame(schema=RANGE_SCHEMA)
    return run_crt_pipeline(
        bars,
        ranges,
        spec=spec or SignalSpec(labels=("previous_day",), sides=(Side.LOW,)),
        interaction=interaction or InteractionConfig(sweep_bps=5.0),
        entry=entry or EntryConfig(rule=EntryRule.RECLAIM_CLOSE),
        symbol="BTCUSDT",
        timeframe="1h",
    )


class TestBarConversion:
    def test_missing_columns_are_named_rather_than_crashing_later(self) -> None:
        with pytest.raises(SignalError, match="missing required columns"):
            bars_from_frame(pl.DataFrame({"open_time": [START], "open": [1.0]}))

    def test_the_attached_atr_is_the_shifted_causal_one(self) -> None:
        """A window of 14 leaves the first fourteen bars without an ATR."""
        bars, _ = bars_from_frame(_sweep_and_reclaim(), atr_window=14)
        assert all(bar.atr is None for bar in bars[:14])
        assert bars[20].atr is not None

    def test_a_series_shorter_than_the_window_has_no_atr_at_all(self) -> None:
        bars, _ = bars_from_frame(_sweep_and_reclaim().head(10), atr_window=14)
        assert all(bar.atr is None for bar in bars)


class TestEvents:
    def test_every_transition_becomes_a_row(self) -> None:
        result = _run(_sweep_and_reclaim())
        states = result.events["state"].to_list()
        assert str(LevelState.SWEPT) in states
        assert str(LevelState.RECLAIMED) in states

    def test_the_frame_has_the_declared_schema(self) -> None:
        result = _run(_sweep_and_reclaim())
        assert dict(result.events.schema) == EVENT_SCHEMA
        assert dict(result.signals.schema) == SIGNAL_SCHEMA

    def test_the_measurement_that_caused_the_transition_travels_with_it(self) -> None:
        """The sweep is 2.0 below a level of 99, i.e. 202.02 bps."""
        result = _run(_sweep_and_reclaim())
        swept = result.events.filter(pl.col("state") == str(LevelState.SWEPT)).to_dicts()[0]
        assert swept["bar_index"] == 29
        assert swept["level"] == pytest.approx(99.0)
        assert swept["sweep_depth_bps"] == pytest.approx(2.0 / 99.0 * 10_000.0)
        # The wick below the body: the lower of open and close, less the low.
        assert swept["wick"] == pytest.approx(100.5 - 97.0)
        assert swept["volume"] == pytest.approx(39.0)
        assert swept["symbol"] == "BTCUSDT"

    def test_no_level_is_read_before_it_exists(self) -> None:
        """The previous-day low is not a level during the day that forms it."""
        result = _run(_sweep_and_reclaim())
        assert result.events["bar_index"].min() >= 24  # type: ignore[operator]

    def test_an_empty_sample_produces_empty_frames_not_an_error(self) -> None:
        result = _run(_frame([]))
        assert result.events.height == 0
        assert result.signals.height == 0

    def test_the_summary_counts_what_the_frames_contain(self) -> None:
        result = _run(_sweep_and_reclaim())
        summary = summarise(result)
        assert summary.n_events == result.events.height
        assert summary.n_signals == result.signals.height
        assert summary.n_levels_tracked == 1  # one side of one previous-day range
        assert sum(summary.by_state.values()) == summary.n_events


class TestSignals:
    def test_a_completed_setup_emits_one_signal_at_its_confirming_close(self) -> None:
        result = _run(_sweep_and_reclaim())
        assert result.signals.height == 1
        signal = result.signals.to_dicts()[0]
        assert signal["bar_index"] == 29
        assert signal["open_time"] == START + timedelta(hours=29)
        assert signal["reference_price"] == pytest.approx(100.5)
        assert signal["direction"] == 1

    def test_the_signal_carries_the_whole_explanation(self) -> None:
        signal = _run(_sweep_and_reclaim()).signals.to_dicts()[0]
        assert signal["label"] == "previous_day"
        assert signal["level_side"] == str(Side.LOW)
        assert signal["trigger_state"] == str(LevelState.RECLAIMED)
        assert signal["sweep_depth_bps"] == pytest.approx(2.0 / 99.0 * 10_000.0)
        assert signal["sweep_extreme"] == pytest.approx(97.0)
        assert signal["confirmation"] == str(EntryRule.RECLAIM_CLOSE)
        assert signal["range_mid"] == pytest.approx((110.0 + 99.0) / 2)

    def test_the_conditions_the_configuration_waived_are_recorded(self) -> None:
        """A reader must be able to see what the rule did *not* ask for."""
        signal = _run(_sweep_and_reclaim()).signals.to_dicts()[0]
        assert signal["conditions_required"] == ""
        waived = signal["conditions_waived"].split(",")
        assert "retest" in waived
        assert "displacement" in waived

    def test_the_explanation_reads_as_a_sentence(self) -> None:
        signal = _run(_sweep_and_reclaim()).signals.to_dicts()[0]
        sentence = explain_signal(signal)
        assert "long" in sentence
        assert "previous_day" in sentence
        assert "not required by this configuration" in sentence

    def test_a_later_entry_rule_moves_the_signal_to_a_later_bar(self) -> None:
        result = _run(
            _sweep_and_reclaim(), entry=EntryConfig(rule=EntryRule.NEXT_BAR_OPEN, max_wait_bars=3)
        )
        assert result.signals["bar_index"].to_list() == [30]

    def test_a_rule_that_never_completes_emits_nothing(self) -> None:
        """Price walks away and never retests, so the retest rule finds no bar."""
        result = _run(
            _sweep_and_reclaim(),
            entry=EntryConfig(
                rule=EntryRule.FIRST_RETEST, retest_tolerance_bps=1.0, max_wait_bars=4
            ),
        )
        assert result.signals.height == 0

    def test_a_depth_floor_can_veto_a_shallow_sweep(self) -> None:
        spec = SignalSpec(labels=("previous_day",), sides=(Side.LOW,), min_sweep_bps=500.0)
        assert _run(_sweep_and_reclaim(), spec=spec).signals.height == 0

    def test_requiring_a_real_break_vetoes_a_pure_wick(self) -> None:
        """No bar closed below 99, so "at least one close outside" is never met."""
        spec = SignalSpec(labels=("previous_day",), sides=(Side.LOW,), min_closes_outside=1)
        assert _run(_sweep_and_reclaim(), spec=spec).signals.height == 0

    def test_requiring_the_other_extreme_first_vetoes_a_single_sweep(self) -> None:
        spec = SignalSpec(
            labels=("previous_day",),
            sides=(Side.LOW, Side.HIGH),
            require_opposite_side_swept=True,
        )
        assert _run(_sweep_and_reclaim(), spec=spec).signals.height == 0

    def test_a_continuation_setup_trades_the_other_way(self) -> None:
        spec = SignalSpec(labels=("previous_day",), sides=(Side.LOW,), setup=SetupKind.CONTINUATION)
        assert spec.sign_for(Side.LOW) == -1

    def test_an_unknown_session_is_refused_at_construction(self) -> None:
        with pytest.raises(SignalError, match="Unknown session"):
            SignalSpec(labels=("previous_day",), session="mars")

    def test_a_spec_must_name_a_label_a_side_and_a_trigger(self) -> None:
        with pytest.raises(SignalError, match="at least one range label"):
            SignalSpec(labels=())
        with pytest.raises(SignalError, match="at least one side"):
            SignalSpec(labels=("previous_day",), sides=())
        with pytest.raises(SignalError, match="at least one trigger state"):
            SignalSpec(labels=("previous_day",), trigger_states=())


class TestNoDuplicateSignals:
    def _two_sweeps(self) -> pl.DataFrame:
        """The same previous-day low is swept and reclaimed twice on day two."""
        rows: list[Row] = [(105.0, 110.0, 99.0, 105.0) for _ in range(24)]
        for i in range(24):
            if i in (5, 15):
                rows.append((101.0, 101.5, 97.0, 100.5))
            else:
                rows.append((104.0, 105.0, 103.0, 104.0))
        return _frame(rows)

    def test_one_level_emits_at_most_one_signal(self) -> None:
        result = _run(self._two_sweeps())
        assert result.signals.height == 1
        assert result.signals["bar_index"].to_list() == [29]

    def test_the_consumed_level_is_never_rebuilt(self) -> None:
        result = _run(self._two_sweeps())
        keys = result.signals.select("range_id", "level_side").unique()
        assert keys.height == result.signals.height


class TestLevelExpiry:
    def test_a_level_expires_when_its_budget_of_bars_runs_out(self) -> None:
        result = _run(
            _sweep_and_reclaim(),
            interaction=InteractionConfig(sweep_bps=5.0, max_bars_active=3),
        )
        states = result.events["state"].to_list()
        assert str(LevelState.EXPIRED) in states
        assert result.signals.height == 0

    def test_nothing_is_recorded_after_the_level_expires(self) -> None:
        result = _run(
            _sweep_and_reclaim(),
            interaction=InteractionConfig(sweep_bps=5.0, max_bars_active=3),
        )
        expired_at = result.events.filter(pl.col("state") == str(LevelState.EXPIRED))[
            "bar_index"
        ].to_list()[0]
        assert result.events["bar_index"].max() == expired_at

    def test_a_level_is_only_readable_between_availability_and_expiry(self) -> None:
        bars = _sweep_and_reclaim()
        ranges = daily_ranges(bars)
        assert levels_readable_at(ranges, START + timedelta(hours=5)) == set()
        assert levels_readable_at(ranges, START + timedelta(hours=29))


class TestTruncationInvariance:
    """Signals computed on a prefix must equal the prefix of the signals.

    This is the operational definition of "no look-ahead" for this pipeline: if
    a signal at bar 29 can be changed, added or removed by bars that arrive
    after bar 29, then the backtest is reading the future. The check is run
    across prefixes that end before, on, and after the confirming bar, and on
    the events as well as the signals, because an event is what a later study of
    these levels would be built from.
    """

    CUTS = (10, 24, 25, 29, 30, 31, 40, 48)

    @pytest.mark.parametrize("k", CUTS)
    def test_signals_from_a_prefix_match_the_prefix_of_the_signals(self, k: int) -> None:
        bars = _sweep_and_reclaim()
        full = _run(bars).signals
        prefix = _run(bars.head(k)).signals
        assert_frame_equal(prefix, full.filter(pl.col("bar_index") < k))

    @pytest.mark.parametrize("k", CUTS)
    def test_events_from_a_prefix_match_the_prefix_of_the_events(self, k: int) -> None:
        bars = _sweep_and_reclaim()
        full = _run(bars).events
        prefix = _run(bars.head(k)).events
        assert_frame_equal(prefix, full.filter(pl.col("bar_index") < k))

    def test_the_fixture_would_have_caught_a_leak(self) -> None:
        """A guard against the invariance test passing on an empty frame."""
        bars = _sweep_and_reclaim()
        assert _run(bars).signals.height == 1
        assert _run(bars.head(29)).signals.height == 0
        assert _run(bars.head(30)).signals.height == 1

    @pytest.mark.parametrize("rule", list(EntryRule))
    def test_every_entry_rule_is_truncation_invariant(self, rule: EntryRule) -> None:
        bars = _sweep_and_reclaim()
        entry = EntryConfig(rule=rule, retest_tolerance_bps=100.0, max_wait_bars=6, pivot_span=2)
        full = _run(bars, entry=entry).signals
        for k in (28, 30, 33, 40):
            prefix = _run(bars.head(k), entry=entry).signals
            assert_frame_equal(prefix, full.filter(pl.col("bar_index") < k))


class TestConfigFingerprint:
    def test_the_same_configuration_hashes_the_same_way(self) -> None:
        spec = SignalSpec(labels=("previous_day",))
        assert config_fingerprint(spec, InteractionConfig()) == config_fingerprint(
            SignalSpec(labels=("previous_day",)), InteractionConfig()
        )

    def test_a_changed_threshold_changes_the_fingerprint(self) -> None:
        spec = SignalSpec(labels=("previous_day",))
        assert config_fingerprint(spec, InteractionConfig(sweep_bps=5.0)) != config_fingerprint(
            spec, InteractionConfig(sweep_bps=6.0)
        )

    def test_every_row_carries_the_fingerprint_of_the_run(self) -> None:
        result = _run(_sweep_and_reclaim())
        assert result.events["config_fingerprint"].unique().to_list() == [result.fingerprint]
        assert result.signals["config_fingerprint"].unique().to_list() == [result.fingerprint]
