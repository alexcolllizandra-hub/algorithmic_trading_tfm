"""Sizing and limits, checked for the two things that make them trustworthy.

A limit is only worth configuring if it actually refuses something, so every
policy below is tested against a stream it must block. And a loss limit that
reacts to a trade before that trade has resolved is a look-ahead leak wearing a
risk badge, so the ledger's ordering discipline is tested as carefully as the
arithmetic.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from perp_lab.crt.risk import (
    RiskConfig,
    RiskError,
    RiskLedger,
    TradeRequest,
    evaluate_requests,
    exposure_cap,
    size_from_stop_distance,
)

START = datetime(2024, 1, 1, tzinfo=UTC)
DAY = date(2024, 1, 1)


def _request(
    bar_index: int,
    *,
    level: str = "r0:low",
    session: str = "london:2024-01-01",
    day: date | None = DAY,
    entry: float = 100.0,
    stop: float = 99.0,
    net_rr: float = 2.0,
    after_cutoff: bool = False,
) -> TradeRequest:
    return TradeRequest(
        bar_index=bar_index,
        at=START + timedelta(hours=bar_index),
        sign=1,
        entry_price=entry,
        stop_price=stop,
        net_reward_risk=net_rr,
        level_key=level,
        session_key=session,
        day=day,
        after_entry_cutoff=after_cutoff,
    )


class TestSizing:
    def test_a_wider_stop_buys_fewer_units(self) -> None:
        """1% of 10,000 is 100 of risk; a stop 1.0 wide buys 100 units of a 100 asset."""
        tight = size_from_stop_distance(
            capital=10_000.0, risk_cash=100.0, entry_price=100.0, stop_price=99.0, max_exposure=10.0
        )
        wide = size_from_stop_distance(
            capital=10_000.0, risk_cash=100.0, entry_price=100.0, stop_price=98.0, max_exposure=10.0
        )
        assert tight == pytest.approx(1.0)
        assert wide == pytest.approx(0.5)

    def test_the_exposure_cap_binds_before_leverage_does(self) -> None:
        """A stop 0.1 wide would demand ten times capital; the cap allows one."""
        size = size_from_stop_distance(
            capital=10_000.0,
            risk_cash=100.0,
            entry_price=100.0,
            stop_price=99.9,
            max_exposure=1.0,
        )
        assert size == pytest.approx(1.0)

    def test_a_capped_trade_risks_less_than_the_budget_never_more(self) -> None:
        capped = size_from_stop_distance(
            capital=10_000.0, risk_cash=100.0, entry_price=100.0, stop_price=99.9, max_exposure=1.0
        )
        risked = capped * 10_000.0 * (0.1 / 100.0)
        assert risked < 100.0

    def test_a_zero_stop_distance_gives_no_size(self) -> None:
        assert (
            size_from_stop_distance(
                capital=10_000.0,
                risk_cash=100.0,
                entry_price=100.0,
                stop_price=100.0,
                max_exposure=1.0,
            )
            == 0.0
        )

    def test_a_cash_budget_overrides_the_percentage(self) -> None:
        config = RiskConfig(initial_capital=10_000.0, risk_per_trade_pct=1.0, fixed_risk_cash=50.0)
        assert config.risk_cash == pytest.approx(50.0)

    def test_a_percentage_budget_is_a_share_of_capital(self) -> None:
        assert RiskConfig(initial_capital=10_000.0, risk_per_trade_pct=0.5).risk_cash == 50.0


class TestPolicyValidation:
    def test_capital_must_be_positive(self) -> None:
        with pytest.raises(RiskError, match="initial_capital"):
            RiskConfig(initial_capital=0.0)

    def test_some_risk_budget_must_exist(self) -> None:
        with pytest.raises(RiskError, match="risk_per_trade_pct"):
            RiskConfig(risk_per_trade_pct=0.0)

    def test_a_level_must_be_tradeable_at_least_once(self) -> None:
        with pytest.raises(RiskError, match="max_trades_per_level"):
            RiskConfig(max_trades_per_level=0)

    def test_a_request_needs_a_direction(self) -> None:
        with pytest.raises(RiskError, match="sign"):
            TradeRequest(
                bar_index=0,
                at=START,
                sign=0,
                entry_price=100.0,
                stop_price=99.0,
                net_reward_risk=2.0,
                level_key="r0:low",
            )


class TestLimitsBind:
    def test_a_level_is_traded_once_by_default(self) -> None:
        ledger = RiskLedger(RiskConfig())
        assert ledger.evaluate(_request(0)).accepted
        second = ledger.evaluate(_request(5))
        assert not second.accepted
        assert "already been traded" in second.reason

    def test_a_different_level_is_unaffected(self) -> None:
        ledger = RiskLedger(RiskConfig())
        assert ledger.evaluate(_request(0, level="r0:low")).accepted
        assert ledger.evaluate(_request(5, level="r1:high")).accepted

    def test_the_session_limit_binds_across_levels(self) -> None:
        ledger = RiskLedger(RiskConfig(max_trades_per_session=2))
        assert ledger.evaluate(_request(0, level="a")).accepted
        assert ledger.evaluate(_request(1, level="b")).accepted
        third = ledger.evaluate(_request(2, level="c"))
        assert not third.accepted
        assert "session trade limit" in third.reason

    def test_the_next_session_starts_with_a_clean_count(self) -> None:
        ledger = RiskLedger(RiskConfig(max_trades_per_session=1))
        assert ledger.evaluate(_request(0, level="a", session="london:2024-01-01")).accepted
        assert ledger.evaluate(_request(9, level="b", session="london:2024-01-02")).accepted

    def test_no_new_entries_past_the_entry_cutoff(self) -> None:
        ledger = RiskLedger(RiskConfig())
        decision = ledger.evaluate(_request(0, after_cutoff=True))
        assert not decision.accepted
        assert "entry cutoff" in decision.reason

    def test_the_cutoff_rule_can_be_switched_off(self) -> None:
        ledger = RiskLedger(RiskConfig(block_after_entry_cutoff=False))
        assert ledger.evaluate(_request(0, after_cutoff=True)).accepted

    def test_a_thin_trade_is_refused_by_the_portfolio_floor(self) -> None:
        ledger = RiskLedger(RiskConfig(min_net_reward_risk=1.5))
        decision = ledger.evaluate(_request(0, net_rr=1.2))
        assert not decision.accepted
        assert "reward:risk" in decision.reason

    def test_a_refused_trade_does_not_consume_the_level_budget(self) -> None:
        """Otherwise a policy would silently ration setups it never took."""
        ledger = RiskLedger(RiskConfig(min_net_reward_risk=1.5))
        assert not ledger.evaluate(_request(0, net_rr=1.2)).accepted
        assert ledger.evaluate(_request(1, net_rr=2.0)).accepted

    def test_the_daily_loss_limit_binds_once_losses_have_resolved(self) -> None:
        ledger = RiskLedger(RiskConfig(max_daily_losses=2, max_trades_per_level=10))
        ledger.evaluate(_request(0))
        ledger.register_outcome(resolved_at_bar=1, won=False, day=DAY)
        ledger.evaluate(_request(2))
        ledger.register_outcome(resolved_at_bar=3, won=False, day=DAY)
        blocked = ledger.evaluate(_request(4))
        assert not blocked.accepted
        assert "daily loss limit" in blocked.reason

    def test_the_daily_loss_limit_resets_on_the_next_day(self) -> None:
        ledger = RiskLedger(RiskConfig(max_daily_losses=1, max_trades_per_level=10))
        ledger.evaluate(_request(0))
        ledger.register_outcome(resolved_at_bar=1, won=False, day=DAY)
        assert not ledger.evaluate(_request(2)).accepted
        assert ledger.evaluate(_request(3, day=date(2024, 1, 2))).accepted


class TestLockout:
    def test_consecutive_losses_stop_trading(self) -> None:
        config = RiskConfig(lockout_after_losses=2, lockout_bars=10, max_trades_per_level=10)
        ledger = RiskLedger(config)
        ledger.evaluate(_request(0))
        ledger.register_outcome(resolved_at_bar=1, won=False)
        ledger.evaluate(_request(2))
        ledger.register_outcome(resolved_at_bar=3, won=False)
        blocked = ledger.evaluate(_request(4))
        assert not blocked.accepted
        assert "locked out" in blocked.reason

    def test_the_lockout_expires_after_the_configured_bars(self) -> None:
        """The second loss resolves on bar 3, so trading resumes at bar 13."""
        config = RiskConfig(lockout_after_losses=2, lockout_bars=10, max_trades_per_level=10)
        ledger = RiskLedger(config)
        ledger.evaluate(_request(0))
        ledger.register_outcome(resolved_at_bar=1, won=False)
        ledger.evaluate(_request(2))
        ledger.register_outcome(resolved_at_bar=3, won=False)
        assert not ledger.evaluate(_request(12)).accepted
        assert ledger.evaluate(_request(13)).accepted

    def test_a_win_resets_the_streak(self) -> None:
        config = RiskConfig(lockout_after_losses=2, max_trades_per_level=10)
        ledger = RiskLedger(config)
        ledger.evaluate(_request(0))
        ledger.register_outcome(resolved_at_bar=1, won=False)
        ledger.evaluate(_request(2))
        ledger.register_outcome(resolved_at_bar=3, won=True)
        ledger.evaluate(_request(4))
        ledger.register_outcome(resolved_at_bar=5, won=False)
        assert ledger.evaluate(_request(6)).accepted


class TestOutcomesCannotBeSeenEarly:
    def test_a_loss_is_invisible_until_the_bar_it_resolves_on(self) -> None:
        """The trade is open at bar 2; its result cannot yet lock anything out."""
        config = RiskConfig(lockout_after_losses=1, lockout_bars=5, max_trades_per_level=10)
        ledger = RiskLedger(config)
        ledger.evaluate(_request(0))
        ledger.register_outcome(resolved_at_bar=9, won=False)
        assert ledger.evaluate(_request(2)).accepted
        assert not ledger.evaluate(_request(9)).accepted

    def test_backdating_an_outcome_is_an_error_rather_than_a_quiet_leak(self) -> None:
        ledger = RiskLedger(RiskConfig())
        ledger.evaluate(_request(5))
        with pytest.raises(RiskError, match="using the future"):
            ledger.register_outcome(resolved_at_bar=3, won=False)


class TestStreamEvaluation:
    def test_a_whole_stream_runs_through_one_policy(self) -> None:
        config = RiskConfig(lockout_after_losses=2, lockout_bars=4, max_trades_per_level=10)
        items = [
            (_request(0), 1, False),
            (_request(2), 3, False),
            (_request(4), 5, True),  # inside the lockout window that starts at bar 3
            (_request(8), 9, True),
        ]
        decisions = evaluate_requests(config, items)
        assert [d.accepted for d in decisions] == [True, True, False, True]

    def test_the_stream_is_evaluated_in_bar_order_whatever_order_it_arrives_in(self) -> None:
        config = RiskConfig(max_trades_per_level=1)
        items = [(_request(5, level="a"), 6, True), (_request(0, level="a"), 1, True)]
        decisions = evaluate_requests(config, items)
        assert decisions[0].accepted and not decisions[1].accepted

    def test_the_largest_accepted_size_never_exceeds_the_cap(self) -> None:
        config = RiskConfig(max_exposure=0.75, max_trades_per_level=10)
        decisions = evaluate_requests(
            config, [(_request(i, stop=99.99), i + 1, True) for i in range(3)]
        )
        assert exposure_cap(decisions) == pytest.approx(0.75)

    def test_an_empty_stream_reports_no_exposure(self) -> None:
        assert exposure_cap([]) == 0.0


class TestSeparationFromSignals:
    def test_the_module_never_sees_a_bar(self) -> None:
        """Sizing consumes a priced plan, not price action.

        If this ever fails, risk has grown the ability to change *which* setups
        exist, and the hit rate of a pattern stops being measurable.
        """
        import inspect

        import perp_lab.crt.risk as risk_module

        source = inspect.getsource(risk_module)
        assert "import" in source
        assert "from perp_lab.crt.signals" not in source
        assert "from perp_lab.crt.states" not in source
