"""Stationarity / dependence test wrappers on synthetic series."""

from __future__ import annotations

import numpy as np
import polars as pl

from perp_lab.eda.stationarity import (
    adf_test,
    arch_lm_test,
    kpss_test,
    ljung_box,
    stationarity_report,
)


def test_adf_rejects_unit_root_for_white_noise():
    rng = np.random.default_rng(0)
    x = rng.standard_normal(2000)
    out = adf_test(x)
    assert out["pvalue"] < 0.05  # stationary noise -> reject unit-root null


def test_adf_does_not_reject_for_random_walk():
    rng = np.random.default_rng(1)
    rw = np.cumsum(rng.standard_normal(2000))
    out = adf_test(rw)
    assert out["pvalue"] > 0.05  # random walk -> fail to reject unit root


def test_kpss_and_arch_and_ljung_return_expected_keys():
    rng = np.random.default_rng(2)
    x = rng.standard_normal(1000)
    assert set(kpss_test(x)) >= {"stat", "pvalue"}
    assert set(arch_lm_test(x)) >= {"lm_stat", "lm_pvalue"}
    assert set(ljung_box(x, lags=10)) == {"lb_stat", "lb_pvalue"}


def test_arch_lm_flags_volatility_clustering():
    rng = np.random.default_rng(3)
    # GARCH-like: variance depends on previous squared shock.
    n = 3000
    e = rng.standard_normal(n)
    x = np.zeros(n)
    sig2 = np.ones(n)
    for t in range(1, n):
        sig2[t] = 0.1 + 0.85 * x[t - 1] ** 2 + 0.1
        x[t] = np.sqrt(sig2[t]) * e[t]
    assert arch_lm_test(x)["lm_pvalue"] < 0.05


def test_stationarity_report_shape():
    rng = np.random.default_rng(4)
    price = 100 * np.exp(np.cumsum(rng.standard_normal(1000) * 0.01))
    df = pl.DataFrame({"close": price}).with_columns(
        (pl.col("close").log() - pl.col("close").log().shift(1)).alias("log_return")
    )
    rep = stationarity_report(df, symbol="BTCUSDT")
    assert rep.height == 7
    assert set(rep.columns) == {"symbol", "test", "series", "statistic", "pvalue", "null"}
