"""Tests for the upgraded backtester: funding, trades, reversals, rich ledger."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from perp_lab.backtesting.engine import run_backtest


def _frames(
    opens: list[float], sides: list[int]
) -> tuple[pl.DataFrame, pl.DataFrame, list[datetime]]:
    n = len(opens)
    t0 = datetime(2021, 1, 1, tzinfo=UTC)
    times = [t0 + timedelta(hours=i) for i in range(n)]
    prices = pl.DataFrame({"open_time": times, "open": opens})
    signals = pl.DataFrame({"open_time": times, "side": sides})
    return signals, prices, times


def test_ledger_has_full_column_contract() -> None:
    signals, prices, _ = _frames([100.0] * 6, [1, 1, -1, -1, 0, 0])
    res = run_backtest(
        signals,
        prices,
        timeframe="1h",
        fee_bps_per_side=1.0,
        slippage_bps_per_side=1.0,
        asset="BTCUSDT",
    )
    for col in (
        "asset",
        "timeframe",
        "raw_signal",
        "target_position",
        "position",
        "execution_price",
        "gross_return",
        "fee",
        "slippage",
        "funding",
        "net_return",
        "turnover",
        "equity",
        "drawdown",
        "trade_id",
        "exit_reason",
    ):
        assert col in res.ledger.columns
    assert res.ledger["asset"][0] == "BTCUSDT"


def test_direct_reversal_is_two_units_of_turnover() -> None:
    # side: long then short -> executed position flips +1 -> -1 (two units).
    signals, prices, _ = _frames([100.0] * 6, [1, 1, -1, -1, -1, -1])
    res = run_backtest(
        signals, prices, timeframe="1h", fee_bps_per_side=0.0, slippage_bps_per_side=0.0
    )
    turn = res.ledger["turnover"].to_list()
    # find the reversal bar (position goes +1 -> -1)
    pos = res.ledger["position"].to_list()
    rev_idx = next(i for i in range(1, len(pos)) if pos[i] == -1.0 and pos[i - 1] == 1.0)
    assert turn[rev_idx] == pytest.approx(2.0)


def test_funding_sign_and_timestamp_alignment() -> None:
    # Hold long the whole time; a single positive funding at hour 3 costs the long.
    signals, prices, times = _frames([100.0] * 6, [1, 1, 1, 1, 1, 1])
    funding = pl.DataFrame({"funding_time": [times[3]], "funding_rate": [0.01]})
    res = run_backtest(
        signals,
        prices,
        timeframe="1h",
        fee_bps_per_side=0.0,
        slippage_bps_per_side=0.0,
        funding=funding,
    )
    assert res.funding_applied is True
    funding_col = res.ledger["funding"].to_list()
    # Exactly one bar (the one holding a long over hour 3) pays +0.01 funding.
    assert res.ledger["funding"].sum() == pytest.approx(0.01)
    assert max(funding_col) == pytest.approx(0.01)
    # A long paying positive funding reduces its net return on that bar.
    idx = funding_col.index(pytest.approx(0.01))
    assert res.ledger["net_return"].to_list()[idx] == pytest.approx(-0.01)


def test_funding_short_receives_positive_funding() -> None:
    signals, prices, times = _frames([100.0] * 6, [-1, -1, -1, -1, -1, -1])
    funding = pl.DataFrame({"funding_time": [times[3]], "funding_rate": [0.01]})
    res = run_backtest(
        signals,
        prices,
        timeframe="1h",
        fee_bps_per_side=0.0,
        slippage_bps_per_side=0.0,
        funding=funding,
    )
    # Short position * positive rate => negative funding "cost" => a credit.
    assert res.ledger["funding"].sum() == pytest.approx(-0.01)


def test_require_funding_raises_without_frame() -> None:
    signals, prices, _ = _frames([100.0] * 6, [1] * 6)
    with pytest.raises(ValueError, match="Funding data is required"):
        run_backtest(
            signals,
            prices,
            timeframe="1h",
            fee_bps_per_side=0.0,
            slippage_bps_per_side=0.0,
            require_funding=True,
        )


def test_trade_records_and_exit_reasons() -> None:
    # long (entry) held then flat (close), then short (entry) held then flat.
    signals, prices, _ = _frames([100.0] * 8, [1, 1, 0, 0, -1, -1, 0, 0])
    res = run_backtest(
        signals, prices, timeframe="1h", fee_bps_per_side=0.0, slippage_bps_per_side=0.0
    )
    trades = res.trades()
    assert trades.height == 2  # one long trade, one short trade
    reasons = [r for r in res.ledger["exit_reason"].to_list() if r is not None]
    assert "signal_close" in reasons


def test_no_funding_frame_flag_false() -> None:
    signals, prices, _ = _frames([100.0] * 6, [1] * 6)
    res = run_backtest(
        signals, prices, timeframe="1h", fee_bps_per_side=0.0, slippage_bps_per_side=0.0
    )
    assert res.funding_applied is False
    assert res.ledger["funding"].sum() == pytest.approx(0.0)
