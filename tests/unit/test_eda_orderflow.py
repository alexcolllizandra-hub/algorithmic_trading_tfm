from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl

from perp_lab.eda.orderflow import add_order_flow_imbalance, order_flow_summary


def _frame(quote: list[float], taker: list[float]) -> pl.DataFrame:
    n = len(quote)
    t0 = datetime(2021, 1, 1, tzinfo=UTC)
    return pl.DataFrame(
        {
            "open_time": [t0 + timedelta(hours=i) for i in range(n)],
            "quote_volume": quote,
            "taker_buy_quote": taker,
            "log_return": [0.001 * (i - n / 2) for i in range(n)],
        }
    )


def test_imbalance_maps_ratio_to_symmetric_range() -> None:
    df = _frame([100.0, 100.0, 100.0], [100.0, 50.0, 0.0])
    out = add_order_flow_imbalance(df)
    ratios = out["taker_buy_ratio"].to_list()
    imb = out["taker_buy_imbalance"].to_list()
    assert ratios == [1.0, 0.5, 0.0]
    assert imb == [1.0, 0.0, -1.0]


def test_zero_denominator_is_null_not_infinite() -> None:
    df = _frame([0.0, 200.0], [0.0, 100.0])
    out = add_order_flow_imbalance(df)
    assert out["taker_buy_ratio"].to_list()[0] is None
    assert out["taker_buy_imbalance"].to_list()[0] is None
    # A well-defined bar still computes.
    assert out["taker_buy_imbalance"].to_list()[1] == 0.0


def test_order_flow_summary_keys_and_share() -> None:
    df = _frame([100.0] * 6, [80.0, 70.0, 60.0, 40.0, 30.0, 20.0])
    summ = order_flow_summary(df, symbol="BTCUSDT", timeframe="1h")
    assert summ["symbol"] == "BTCUSDT"
    assert summ["n"] == 6
    # Three bars net-buy (>0.5 ratio), three net-sell.
    assert summ["share_net_buy"] == 0.5
    for key in ("median_imbalance", "iqr_imbalance", "acf_lag1", "spearman_with_return"):
        assert key in summ
