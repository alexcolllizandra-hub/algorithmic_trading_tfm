"""Tests for cross-asset and derivatives (context) feature builders."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from perp_lab.features import (
    FeatureContext,
    add_basis,
    add_open_interest_change,
    add_relative_momentum,
    add_relative_return,
    add_rolling_xcorr,
    attach_funding_rate,
    resolve_feature_set,
)
from perp_lab.features.registry import build_feature_frame


def _bars(n: int, base: float, step: float = 1.0) -> pl.DataFrame:
    start = datetime(2021, 1, 1, tzinfo=UTC)
    times = [start + timedelta(hours=i) for i in range(n)]
    close = [base + step * i for i in range(n)]
    return pl.DataFrame({"open_time": times, "close": close})


def test_relative_return_exact_alignment_and_warmup() -> None:
    a = _bars(10, 100.0, 1.0)
    b = _bars(10, 50.0, 0.5)
    out = add_relative_return(a, b)
    assert out["xasset_rel_return"].null_count() == 1  # first bar warm-up
    # Both rise; self grows faster in log terms early on -> difference finite.
    assert out["xasset_rel_return"].drop_nulls().is_finite().all()


def test_rolling_xcorr_perfectly_correlated_is_one() -> None:
    a = _bars(30, 100.0, 1.0)
    b = a.rename({"close": "close"})  # identical -> corr 1
    out = add_rolling_xcorr(a, b, window=5)
    vals = out["xasset_corr_5"].drop_nulls().to_list()
    assert all(abs(v - 1.0) < 1e-6 for v in vals)


def test_rolling_xcorr_is_bounded() -> None:
    import numpy as np

    rng = np.random.default_rng(0)
    a = _bars(60, 100.0)
    b = _bars(60, 100.0).with_columns(pl.Series("close", 100.0 + np.cumsum(rng.normal(0, 1, 60))))
    out = add_rolling_xcorr(a, b, window=10)
    vals = out["xasset_corr_10"].drop_nulls().to_list()
    assert all(-1.0 <= v <= 1.0 for v in vals)


def test_relative_momentum_difference() -> None:
    a = _bars(20, 100.0, 2.0)
    b = _bars(20, 100.0, 1.0)
    out = add_relative_momentum(a, b, window=3)
    # self appreciates faster => relative momentum positive after warm-up.
    assert out["xasset_rel_momentum_3"].drop_nulls().min() > 0.0  # type: ignore[operator]


def test_attach_funding_is_backward_asof() -> None:
    bars = _bars(6, 100.0)
    # Funding settles at hour 2 and hour 5 only.
    funding = pl.DataFrame(
        {
            "funding_time": [
                datetime(2021, 1, 1, 2, tzinfo=UTC),
                datetime(2021, 1, 1, 5, tzinfo=UTC),
            ],
            "funding_rate": [0.001, -0.002],
        }
    )
    out = attach_funding_rate(bars, funding)
    rates = out["funding_rate"].to_list()
    # Bars 0,1 before first funding -> null; bars 2,3,4 carry 0.001; bar 5 -> -0.002.
    assert rates[0] is None and rates[1] is None
    assert rates[2] == pytest.approx(0.001)
    assert rates[4] == pytest.approx(0.001)
    assert rates[5] == pytest.approx(-0.002)


def test_basis_is_scale_free() -> None:
    bars = _bars(5, 100.0)
    mark = _bars(5, 100.0).with_columns((pl.col("close") * 1.001).alias("close"))
    index = _bars(5, 100.0)
    out = add_basis(bars, mark, index)
    assert out["basis"].drop_nulls().to_list()[0] == pytest.approx(0.001)


def test_oi_change_is_log_difference() -> None:
    bars = _bars(8, 100.0)
    oi = pl.DataFrame(
        {"open_time": bars["open_time"], "open_interest": [100.0 * (1.1**i) for i in range(8)]}
    )
    out = add_open_interest_change(bars, oi, window=1)
    import math

    assert out["oi_change_1"].drop_nulls().to_list()[0] == pytest.approx(math.log(1.1))


# --------------------------------------------------------------------------- #
# Registry integration: context features require the auxiliary input
# --------------------------------------------------------------------------- #
def _primary(n: int) -> pl.DataFrame:
    bars = _bars(n, 100.0)
    return bars.with_columns(
        pl.col("close").alias("open"),
        (pl.col("close") + 1).alias("high"),
        (pl.col("close") - 1).alias("low"),
        pl.lit(1000.0).alias("volume"),
        (pl.col("close") * 1000.0).alias("quote_volume"),
        (pl.col("close") * 600.0).alias("taker_buy_quote"),
    )


def test_context_feature_without_context_raises() -> None:
    from perp_lab.config.experiment import FeatureItem

    specs = resolve_feature_set([FeatureItem(kind="xasset_rel_return")])
    with pytest.raises(ValueError, match="requires the 'peer' context"):
        build_feature_frame(_primary(10), specs, context=None)


def test_context_feature_builds_with_peer() -> None:
    from perp_lab.config.experiment import FeatureItem

    specs = resolve_feature_set(
        [FeatureItem(kind="xasset_rel_return"), FeatureItem(kind="xasset_corr", window=5)]
    )
    ctx = FeatureContext(peer=_bars(20, 50.0, 0.5), peer_symbol="ETHUSDT")
    feats, _ = build_feature_frame(_primary(20), specs, context=ctx)
    assert "xasset_rel_return" in feats.columns
    assert "xasset_corr_5" in feats.columns
