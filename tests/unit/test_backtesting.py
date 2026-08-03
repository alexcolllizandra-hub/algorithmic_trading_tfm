"""Tests for the minimal next-bar, cost-aware backtester."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.backtesting.engine import run_backtest
from perp_lab.backtesting.metrics import bars_per_year, performance_metrics


def _frame(opens: list[float], sides: list[int]) -> tuple[pl.DataFrame, pl.DataFrame]:
    n = len(opens)
    t0 = datetime(2021, 1, 1, tzinfo=UTC)
    times = [t0 + timedelta(hours=i) for i in range(n)]
    prices = pl.DataFrame({"open_time": times, "open": opens})
    signals = pl.DataFrame({"open_time": times, "side": sides})
    return signals, prices


def test_signal_is_executed_next_bar_not_same_bar() -> None:
    # +10% open-to-open each bar; go long on bar 0. Because entry is delayed to
    # the next bar's open, the position during bar 0 is flat (gross_return 0).
    opens = [100.0, 110.0, 121.0, 133.1, 146.41]
    signals, prices = _frame(opens, [1, 1, 1, 1, 1])
    res = run_backtest(
        signals, prices, timeframe="1h", fee_bps_per_side=0.0, slippage_bps_per_side=0.0
    )
    ledger = res.ledger
    assert ledger["position"].to_list()[0] == 0.0  # delayed entry
    assert ledger["gross_return"].to_list()[0] == pytest.approx(0.0)
    # From bar 1 onward the position is long and earns the +10% open-to-open move.
    assert ledger["gross_return"].to_list()[1] == pytest.approx(0.10)


def test_costs_reduce_returns_on_position_changes() -> None:
    opens = [100.0, 100.0, 100.0, 100.0]
    signals, prices = _frame(opens, [1, 1, 1, 1])
    free = run_backtest(
        signals, prices, timeframe="1h", fee_bps_per_side=0.0, slippage_bps_per_side=0.0
    )
    costed = run_backtest(
        signals, prices, timeframe="1h", fee_bps_per_side=4.0, slippage_bps_per_side=1.0
    )
    # A position change from 0->1 happens once; that bar must carry a cost.
    assert float(costed.ledger["cost"].sum()) > 0.0
    assert float(costed.ledger["net_return"].sum()) < float(free.ledger["net_return"].sum()) + 1e-12


def test_fees_reduce_equity_by_deterministic_amount() -> None:
    # Flat prices => zero gross return; a single 0->1 entry costs exactly the fee.
    opens = [100.0, 100.0, 100.0, 100.0]
    signals, prices = _frame(opens, [1, 1, 1, 1])
    res = run_backtest(
        signals, prices, timeframe="1h", fee_bps_per_side=4.0, slippage_bps_per_side=0.0
    )
    costs = res.ledger["cost"].to_list()
    # Position changes 0 -> 1 on the second ledger bar (entry executed next bar);
    # that bar carries exactly the 4 bps fee and no other bar does.
    assert costs[1] == pytest.approx(4.0 / 1e4)
    assert res.ledger["net_return"].to_list()[1] == pytest.approx(-4.0 / 1e4)
    assert sum(costs) == pytest.approx(4.0 / 1e4)


def test_slippage_is_adverse_for_both_long_and_short_entries() -> None:
    opens = [100.0, 100.0, 100.0]
    # Long entry.
    long_sig, prices = _frame(opens, [1, 1, 1])
    long_res = run_backtest(
        long_sig, prices, timeframe="1h", fee_bps_per_side=0.0, slippage_bps_per_side=2.0
    )
    # Short entry.
    short_sig, _ = _frame(opens, [-1, -1, -1])
    short_res = run_backtest(
        short_sig, prices, timeframe="1h", fee_bps_per_side=0.0, slippage_bps_per_side=2.0
    )
    # On flat prices any position change only loses money (adverse) regardless of side.
    assert long_res.ledger["cost"].sum() > 0.0
    assert short_res.ledger["cost"].sum() > 0.0
    assert float(long_res.ledger["net_return"].sum()) < 0.0
    assert float(short_res.ledger["net_return"].sum()) < 0.0


def test_long_short_flat_transitions_accounted() -> None:
    opens = [100.0, 100.0, 100.0, 100.0, 100.0]
    signals, prices = _frame(opens, [1, 0, -1, -1, -1])
    res = run_backtest(
        signals, prices, timeframe="1h", fee_bps_per_side=1.0, slippage_bps_per_side=0.0
    )
    # position = side.shift(1); turnover = |Δposition|.
    positions = res.ledger["position"].to_list()
    assert positions[0] == 0.0  # first bar: no prior side
    assert positions[1] == 1.0  # long entered
    assert positions[2] == 0.0  # flat
    assert positions[3] == -1.0  # short


def test_backtest_is_deterministic() -> None:
    opens = [100.0 * (1.01**i) for i in range(30)]
    sides = [1 if i % 2 == 0 else -1 for i in range(30)]
    signals, prices = _frame(opens, sides)
    a = run_backtest(
        signals, prices, timeframe="1h", fee_bps_per_side=2.0, slippage_bps_per_side=1.0
    )
    b = run_backtest(
        signals, prices, timeframe="1h", fee_bps_per_side=2.0, slippage_bps_per_side=1.0
    )
    assert a.ledger.equals(b.ledger)
    assert a.metrics == b.metrics


def test_metrics_basic_properties() -> None:
    r = np.full(100, 0.001)
    m = performance_metrics(r, timeframe="1h")
    assert m["total_return"] == pytest.approx((1.001**100) - 1.0)
    # A monotonically rising equity curve has no drawdown.
    assert m["max_drawdown"] == pytest.approx(0.0)
    assert np.isfinite(m["sharpe"])


def test_metrics_empty_series() -> None:
    m = performance_metrics(np.array([]), timeframe="1h")
    assert m == {"n_bars": 0.0}


def test_metrics_drawdown_is_negative_on_loss() -> None:
    r = np.array([0.1, -0.5, 0.1])
    m = performance_metrics(r, timeframe="1h")
    assert m["max_drawdown"] < 0.0


def test_bars_per_year_1h() -> None:
    assert bars_per_year("1h") == pytest.approx(24 * 365)
