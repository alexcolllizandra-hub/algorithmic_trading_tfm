"""The nine families, the interface they must satisfy, and their registration.

Two claims are load-bearing here and are tested rather than asserted in prose:
that long and short are one implementation invoked with a different side, and
that a position produced by these families is filled by the existing engine on
the bar after the close that produced it. The families themselves are untested
hypotheses; nothing below says anything about whether they make money.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from perp_lab.backtesting.engine import run_backtest
from perp_lab.config.settings import load_experiment_config
from perp_lab.crt.risk import RiskConfig
from perp_lab.crt.states import Side
from perp_lab.crt.strategies import (
    CRT_BUILDERS,
    CRT_FAMILIES,
    CRT_ROUND_TAG,
    CrtStrategy,
    CrtStrategyError,
    FamilyMechanics,
    ReferenceSpec,
    crt_htf_range_reversal,
    crt_three_candle_model,
    double_sweep_reversal,
    failed_breakout_reversal,
    opening_range_breakout_retest,
    pdh_reclaim_short,
    pdl_reclaim_long,
    resolve_targets,
    session_liquidity_sweep,
    session_range_rotation,
)
from perp_lab.search.registry import (
    CRT_INTRADAY_V1_FAMILIES,
    R3_CLOSED_FAMILIES,
    ROUND_TAGS,
    S1_FAMILIES,
    build_search_space,
)
from perp_lab.strategies.base import SIDE_COL, Strategy

START = datetime(2024, 1, 1, tzinfo=UTC)

Row = tuple[float, float, float, float]


def _frame(rows: list[Row]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "open_time": [START + timedelta(hours=i) for i in range(len(rows))],
            "open": [r[0] for r in rows],
            "high": [r[1] for r in rows],
            "low": [r[2] for r in rows],
            "close": [r[3] for r in rows],
            "volume": [10.0] * len(rows),
        }
    ).with_columns(pl.col("open_time").dt.cast_time_unit("ms").dt.replace_time_zone("UTC"))


def _sweep_and_reclaim() -> pl.DataFrame:
    """Day one is a box between 99 and 110; day two sweeps 99, reclaims, and rallies.

    The reclaim closes at 100.5 on bar 29, so the signal belongs to bar 29 and
    the fill to bar 30. The rally then walks up 0.8 an hour, reaching the range
    mid of 104.5 on bar 34.
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


def _mirrored(bars: pl.DataFrame, level: float = 100.0) -> pl.DataFrame:
    """The same series reflected through ``level``: every long becomes a short."""
    return bars.with_columns(
        (2 * level - pl.col("open")).alias("open"),
        (2 * level - pl.col("low")).alias("high"),
        (2 * level - pl.col("high")).alias("low"),
        (2 * level - pl.col("close")).alias("close"),
    )


def _five_days() -> pl.DataFrame:
    """A longer series with sessions, swings and both extremes taken.

    Used only to check that every family runs end to end on data it recognises;
    the shape is deliberately varied rather than tuned to make anything fire.
    """
    rows: list[Row] = []
    for i in range(24 * 5):
        hour = i % 24
        drift = 100.0 + 3.0 * ((i % 17) - 8) / 8.0
        spread = 1.0 + (hour % 5) * 0.3
        rows.append((drift, drift + spread, drift - spread, drift + (0.4 if i % 3 else -0.5)))
    return _frame(rows)


def _cheap() -> FamilyMechanics:
    """Mechanics with a nominal cost, so refusals are about geometry, not fees."""
    return FamilyMechanics(cost_bps_per_side=1.0)


def _long_strategy(**overrides: object) -> CrtStrategy:
    kwargs: dict[str, object] = {
        "target_plan": "mid",
        "min_net_reward_risk": 1.0,
        "min_sweep_bps": 5.0,
        "mechanics": _cheap(),
    }
    kwargs.update(overrides)
    return pdl_reclaim_long(**kwargs)


class TestFamilyConstruction:
    def test_nine_families_are_declared(self) -> None:
        assert len(CRT_FAMILIES) == 9
        assert set(CRT_BUILDERS) == set(CRT_FAMILIES)

    @pytest.mark.parametrize("family", CRT_FAMILIES)
    def test_every_family_builds_with_its_defaults(self, family: str) -> None:
        strategy = CRT_BUILDERS[family]()
        assert strategy.family == family
        assert strategy.round_tag == CRT_ROUND_TAG

    @pytest.mark.parametrize("family", CRT_FAMILIES)
    def test_every_family_satisfies_the_repository_strategy_protocol(self, family: str) -> None:
        strategy = CRT_BUILDERS[family]()
        assert isinstance(strategy, Strategy)
        assert isinstance(strategy.name, str)
        assert strategy.required_features() == ()
        assert strategy.params()["round_tag"] == CRT_ROUND_TAG

    def test_family_names_are_distinct(self) -> None:
        names = {CRT_BUILDERS[family]().name for family in CRT_FAMILIES}
        assert len(names) == len(CRT_FAMILIES)

    @pytest.mark.parametrize("family", CRT_FAMILIES)
    def test_every_family_runs_over_a_realistic_series(self, family: str) -> None:
        bars = _five_days()
        positions = CRT_BUILDERS[family](mechanics=_cheap()).signals(bars)
        assert positions.height == bars.height
        assert positions.columns == ["open_time", SIDE_COL]

    def test_an_unknown_target_plan_is_refused(self) -> None:
        with pytest.raises(CrtStrategyError, match="Unknown target plan"):
            resolve_targets("moon")

    def test_an_unknown_reference_kind_is_refused(self) -> None:
        with pytest.raises(CrtStrategyError, match="Unknown reference kind"):
            ReferenceSpec(kind="vibes")

    def test_an_opening_range_shorter_than_a_bar_says_what_to_do(self) -> None:
        strategy = opening_range_breakout_retest(minutes=5, mechanics=_cheap())
        with pytest.raises(CrtStrategyError, match="finer timeframe"):
            strategy.run(_five_days())

    def test_a_family_needs_the_raw_bar_columns(self) -> None:
        strategy = _long_strategy()
        with pytest.raises(CrtStrategyError, match="requires columns"):
            strategy.run(_sweep_and_reclaim().drop("high"))


class TestLongAndShortAreOneImplementation:
    def test_the_two_previous_day_families_differ_only_in_their_side(self) -> None:
        long_params = pdl_reclaim_long().params()
        short_params = pdh_reclaim_short().params()
        differing = {k for k in long_params if long_params[k] != short_params[k]}
        assert differing == {"family", "direction"}

    def test_the_direction_selects_sides_rather_than_a_code_path(self) -> None:
        assert pdl_reclaim_long().sides == (Side.LOW,)
        assert pdh_reclaim_short().sides == (Side.HIGH,)
        assert set(crt_htf_range_reversal(direction="both").sides) == {Side.LOW, Side.HIGH}

    def test_a_continuation_family_maps_the_sides_the_other_way(self) -> None:
        """Breaking the high of the opening range is the long, not the short."""
        assert opening_range_breakout_retest(direction="long").sides == (Side.HIGH,)
        assert opening_range_breakout_retest(direction="short").sides == (Side.LOW,)

    def test_an_unknown_direction_is_refused(self) -> None:
        with pytest.raises(ValueError, match="direction must be one of"):
            crt_htf_range_reversal(direction="sideways")

    def test_a_fixed_side_family_will_not_be_talked_out_of_its_side(self) -> None:
        with pytest.raises(CrtStrategyError, match="by definition"):
            pdl_reclaim_long(direction="short")

    def test_a_mirrored_series_produces_the_mirrored_signal(self) -> None:
        """The short twin of the long fixture, to the bar and to the price."""
        long_signal = _long_strategy().run(_sweep_and_reclaim()).crt_signals.to_dicts()
        short_signal = (
            pdh_reclaim_short(
                target_plan="mid", min_net_reward_risk=1.0, min_sweep_bps=5.0, mechanics=_cheap()
            )
            .run(_mirrored(_sweep_and_reclaim()))
            .crt_signals.to_dicts()
        )
        assert len(long_signal) == len(short_signal) == 1
        long_row, short_row = long_signal[0], short_signal[0]
        assert short_row["bar_index"] == long_row["bar_index"]
        assert short_row["trigger_bar"] == long_row["trigger_bar"]
        assert short_row["confirmation"] == long_row["confirmation"]
        assert short_row["direction"] == -long_row["direction"]
        assert short_row["level"] == pytest.approx(200.0 - long_row["level"])
        assert short_row["reference_price"] == pytest.approx(200.0 - long_row["reference_price"])

    def test_the_mirrored_trade_is_managed_the_same_way(self) -> None:
        long_run = _long_strategy().run(_sweep_and_reclaim())
        short_run = pdh_reclaim_short(
            target_plan="mid", min_net_reward_risk=1.0, min_sweep_bps=5.0, mechanics=_cheap()
        ).run(_mirrored(_sweep_and_reclaim()))
        long_trade, short_trade = long_run.taken[0], short_run.taken[0]
        assert long_trade.outcome is not None and short_trade.outcome is not None
        assert long_trade.outcome.exit_reason is short_trade.outcome.exit_reason
        assert long_trade.outcome.exit_bar == short_trade.outcome.exit_bar
        assert long_trade.plan.net_reward_risk == pytest.approx(
            short_trade.plan.net_reward_risk, rel=1e-2
        )


class TestTheBacktesterContract:
    def test_signals_returns_one_target_position_per_bar(self) -> None:
        bars = _sweep_and_reclaim()
        positions = _long_strategy().signals(bars)
        assert positions.height == bars.height
        assert positions["open_time"].to_list() == bars["open_time"].to_list()

    def test_the_position_is_taken_on_the_confirming_close(self) -> None:
        positions = _long_strategy().signals(_sweep_and_reclaim())
        side = positions[SIDE_COL].to_list()
        assert side[28] == 0.0
        assert side[29] == pytest.approx(1.0)

    def test_the_engine_fills_it_on_the_following_bar(self) -> None:
        """The contract the whole module is written against, checked end to end."""
        bars = _sweep_and_reclaim()
        positions = _long_strategy().signals(bars)
        result = run_backtest(
            positions,
            bars,
            timeframe="1h",
            fee_bps_per_side=1.0,
            slippage_bps_per_side=0.0,
        )
        held = result.ledger["position"].to_list()
        assert held[29] == 0.0  # the confirming bar itself is still flat
        assert held[30] == pytest.approx(1.0)

    def test_the_trade_closes_at_the_target_and_the_position_goes_flat(self) -> None:
        run = _long_strategy().run(_sweep_and_reclaim())
        trade = run.taken[0]
        assert trade.outcome is not None
        assert trade.outcome.exit_bar == 34
        side = run.positions[SIDE_COL].to_list()
        assert side[33] == pytest.approx(1.0)
        assert side[34] == 0.0

    def test_partial_exits_appear_as_fractional_positions(self) -> None:
        """Two halves at the mid and the opposite extreme: half the size survives TP1."""
        strategy = _long_strategy(target_plan="mid_then_opposite")
        run = strategy.run(_sweep_and_reclaim())
        side = run.positions[SIDE_COL].to_list()
        assert pytest.approx(0.5) == side[34]

    def test_a_signal_on_the_last_bar_is_dropped_rather_than_filled(self) -> None:
        bars = _sweep_and_reclaim().head(30)
        run = _long_strategy().run(bars)
        assert run.crt_signals.height == 1
        assert not run.taken
        assert "no execution bar" in "".join(run.refusals())


class TestTruncationInvariance:
    """The strategy layer must not reintroduce the leak the pipeline avoids."""

    @pytest.mark.parametrize("k", (25, 29, 30, 34, 40, 48))
    def test_signals_from_a_prefix_match_the_prefix_of_the_signals(self, k: int) -> None:
        bars = _sweep_and_reclaim()
        full = _long_strategy().run(bars).crt_signals
        prefix = _long_strategy().run(bars.head(k)).crt_signals
        assert_frame_equal(prefix, full.filter(pl.col("bar_index") < k))

    def test_positions_before_the_signal_never_change(self) -> None:
        """A later bar cannot alter a position that was already decided."""
        bars = _sweep_and_reclaim()
        full = _long_strategy().signals(bars)[SIDE_COL].to_list()
        prefix = _long_strategy().signals(bars.head(31))[SIDE_COL].to_list()
        assert prefix[:30] == full[:30]

    def test_the_fixture_would_have_caught_a_leak(self) -> None:
        bars = _sweep_and_reclaim()
        assert _long_strategy().run(bars).crt_signals.height == 1
        assert _long_strategy().run(bars.head(29)).crt_signals.height == 0


class TestRiskStaysSeparate:
    def test_without_a_risk_policy_the_family_emits_unit_size(self) -> None:
        """The signal is the hypothesis; sizing is somebody else's decision."""
        side = _long_strategy().signals(_sweep_and_reclaim())[SIDE_COL].to_list()
        assert max(side) == pytest.approx(1.0)

    def test_a_risk_policy_sizes_the_position_from_the_stop_distance(self) -> None:
        mechanics = FamilyMechanics(
            cost_bps_per_side=1.0,
            risk=RiskConfig(initial_capital=10_000.0, risk_per_trade_pct=1.0, max_exposure=10.0),
        )
        run = _long_strategy(mechanics=mechanics).run(_sweep_and_reclaim())
        trade = run.taken[0]
        assert trade.decision is not None
        expected = (100.0 / trade.plan.risk_per_unit) * trade.plan.entry_price / 10_000.0
        assert trade.decision.size_fraction == pytest.approx(expected)
        assert max(run.positions[SIDE_COL].to_list()) == pytest.approx(expected)

    def test_a_risk_limit_blocks_the_trade_without_deleting_the_signal(self) -> None:
        """The setup still happened; the policy simply declined to fund it."""
        mechanics = FamilyMechanics(
            cost_bps_per_side=1.0, risk=RiskConfig(min_net_reward_risk=10.0)
        )
        run = _long_strategy(mechanics=mechanics).run(_sweep_and_reclaim())
        assert run.crt_signals.height == 1
        assert not run.taken
        assert "net reward:risk below the policy floor" in run.refusals()
        assert set(run.positions[SIDE_COL].to_list()) == {0.0}

    def test_a_trade_that_cannot_pay_its_costs_is_refused_before_entry(self) -> None:
        run = _long_strategy(min_net_reward_risk=5.0).run(_sweep_and_reclaim())
        assert run.crt_signals.height == 1
        assert not run.taken
        assert any("reward:risk" in reason for reason in run.refusals())

    def test_the_run_reports_how_much_rests_on_the_intrabar_assumption(self) -> None:
        run = _long_strategy().run(_sweep_and_reclaim())
        assert run.ambiguity.n_trades == 1
        assert run.ambiguity.n_ambiguous_trades == 0


class TestRegistration:
    def test_the_round_tag_is_the_declared_one(self) -> None:
        assert CRT_ROUND_TAG == "CRT_INTRADAY_V1"
        assert set(CRT_INTRADAY_V1_FAMILIES) == set(CRT_FAMILIES)

    def test_the_families_are_tagged_to_their_own_round(self) -> None:
        for family in CRT_INTRADAY_V1_FAMILIES:
            assert ROUND_TAGS[family] == CRT_ROUND_TAG

    def test_the_closed_rounds_are_left_alone(self) -> None:
        """R2 and R3 were pre-specified; adding to them afterwards would be cheating."""
        assert not set(CRT_INTRADAY_V1_FAMILIES) & set(R3_CLOSED_FAMILIES)
        assert not set(CRT_INTRADAY_V1_FAMILIES) & set(S1_FAMILIES)

    @pytest.mark.parametrize("family", CRT_INTRADAY_V1_FAMILIES)
    def test_every_family_has_a_search_space_built_from_validated_config(self, family: str) -> None:
        space = build_search_space(load_experiment_config(), family, "BTCUSDT")
        assert space.family == family
        assert space.params

    @pytest.mark.parametrize("family", CRT_INTRADAY_V1_FAMILIES)
    def test_a_sampled_candidate_builds_a_usable_strategy(self, family: str) -> None:
        import numpy as np

        space = build_search_space(load_experiment_config(), family, "BTCUSDT")
        values = space.repair(space.sample(np.random.default_rng(11)))
        valid, why = space.is_valid(values)
        assert valid, why
        strategy = space.build(values)
        assert isinstance(strategy, Strategy)
        assert isinstance(strategy, CrtStrategy)
        assert strategy.family == family

    @pytest.mark.parametrize("family", CRT_INTRADAY_V1_FAMILIES)
    def test_the_grids_stay_within_the_multiple_testing_budget(self, family: str) -> None:
        """A few well-separated values, not a continuum: every candidate is paid for."""
        space = build_search_space(load_experiment_config(), family, "BTCUSDT")
        cardinality = space.finite_cardinality()
        assert cardinality is not None
        assert cardinality <= 1_000

    def test_the_families_reachable_from_the_registry_are_the_declared_ones(self) -> None:
        builders = {
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
        assert set(builders) == set(CRT_INTRADAY_V1_FAMILIES)
