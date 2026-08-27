"""Chapter-5 EDA additions: estimators validated against synthetic series.

Every estimator added for the thesis's EDA chapter is checked on a synthetic
process with known properties, so a wrong implementation fails loudly rather
than producing plausible-looking numbers:

* white noise      -> flat ACF, VR(q) ~ 1, Hurst ~ 0.5
* persistent AR(1) -> VR(q) > 1, Hurst > 0.5
* GARCH-like       -> ARCH-LM rejects
* random walk      -> ADF keeps the unit root on levels, rejects on differences
* Pareto tail      -> Hill recovers the true alpha
* Student-t        -> the ML fit recovers the true degrees of freedom
* cointegrated pair-> Engle-Granger rejects; independent walks do not
* independent MI   -> stays at the permutation noise floor; dependent exceeds it
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

import numpy as np
import polars as pl
import pytest

from perp_lab.eda.cointegration import engle_granger
from perp_lab.eda.dependence import (
    autocorrelation,
    hurst_rs,
    leverage_effect,
    variance_ratio,
    variance_ratio_profile,
)
from perp_lab.eda.distributions import (
    fit_student_t,
    hill_tail_index,
    kurtosis_by_aggregation,
    survival_function,
)
from perp_lab.eda.features import (
    feature_correlation_matrix,
    high_correlation_pairs,
    label_summary,
    mutual_information_by_horizon,
    pca_scree,
)
from perp_lab.eda.regimes import MARKET_REGIMES, market_regime_stats
from perp_lab.eda.stationarity import adf_test, arch_lm_test

RNG = np.random.default_rng(42)
WHITE = RNG.standard_normal(20_000)


def _frame(values: np.ndarray) -> pl.DataFrame:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    return pl.DataFrame(
        {
            "open_time": [start + timedelta(hours=i) for i in range(values.size)],
            "log_return": values,
        }
    )


# --------------------------------------------------------------------------- #
# Random-walk diagnostics on synthetics
# --------------------------------------------------------------------------- #
def test_white_noise_acf_flat() -> None:
    acf = autocorrelation(_frame(WHITE), max_lag=20)
    beyond = acf.filter(pl.col("lag") > 0)["acf"].abs().max()
    assert beyond < 3.5 / np.sqrt(WHITE.size)


def test_white_noise_variance_ratio_near_one() -> None:
    for q in (2, 4, 8, 16):
        result = variance_ratio(WHITE, q)
        assert abs(result["vr"] - 1.0) < 0.05
        assert abs(result["z_robust"]) < 3.0


def test_persistent_ar1_variance_ratio_above_one() -> None:
    phi = 0.3
    noise = RNG.standard_normal(20_000)
    ar = np.empty_like(noise)
    ar[0] = noise[0]
    for i in range(1, noise.size):
        ar[i] = phi * ar[i - 1] + noise[i]
    result = variance_ratio(ar, 4)
    assert result["vr"] > 1.2
    assert result["z_robust"] > 3.0


def test_variance_ratio_profile_shape() -> None:
    profile = variance_ratio_profile(WHITE, [2, 4, 8])
    assert profile.columns == ["q", "vr", "z_robust", "n"]
    assert profile.height == 3


def test_hurst_white_noise_near_half() -> None:
    assert abs(hurst_rs(WHITE) - 0.5) < 0.08


def test_hurst_persistent_series_above_half() -> None:
    phi = 0.6
    noise = RNG.standard_normal(20_000)
    ar = np.empty_like(noise)
    ar[0] = noise[0]
    for i in range(1, noise.size):
        ar[i] = phi * ar[i - 1] + noise[i]
    assert hurst_rs(ar) > 0.6


def test_adf_random_walk_levels_vs_differences() -> None:
    walk = np.cumsum(RNG.standard_normal(5_000))
    assert adf_test(walk)["pvalue"] > 0.05
    assert adf_test(np.diff(walk))["pvalue"] < 0.01


def test_arch_lm_rejects_on_garch_like_series() -> None:
    # GARCH(1,1)-style variance recursion produces volatility clustering.
    n = 10_000
    omega, alpha, beta = 0.05, 0.15, 0.8
    z = RNG.standard_normal(n)
    sigma2 = np.empty(n)
    r = np.empty(n)
    sigma2[0] = omega / (1 - alpha - beta)
    r[0] = np.sqrt(sigma2[0]) * z[0]
    for i in range(1, n):
        sigma2[i] = omega + alpha * r[i - 1] ** 2 + beta * sigma2[i - 1]
        r[i] = np.sqrt(sigma2[i]) * z[i]
    assert arch_lm_test(r)["lm_pvalue"] < 0.01
    assert arch_lm_test(WHITE)["lm_pvalue"] > 0.01


# --------------------------------------------------------------------------- #
# Tail machinery
# --------------------------------------------------------------------------- #
def test_hill_recovers_pareto_alpha() -> None:
    alpha_true = 3.0
    sample = RNG.pareto(alpha_true, 200_000) + 1.0
    est = hill_tail_index(sample, tail_fraction=0.02)
    assert abs(est["alpha"] - alpha_true) < 0.3


def test_student_t_fit_recovers_df() -> None:
    sample = RNG.standard_t(4.0, 100_000)
    fit = fit_student_t(sample)
    assert 3.0 < fit["df"] < 5.5


def test_survival_function_monotone() -> None:
    surv = survival_function(WHITE)
    max_step = float(cast("float", surv["survival"].diff().drop_nulls().max() or 0.0))
    assert max_step <= 0
    s_min = float(cast("float", surv["survival"].min() or -1.0))
    s_max = float(cast("float", surv["survival"].max() or -1.0))
    assert 0 < s_min <= s_max <= 1


def test_kurtosis_by_aggregation_declines_for_t() -> None:
    heavy = RNG.standard_t(4.0, 400_000)
    table = kurtosis_by_aggregation(heavy, [1, 12])
    k1 = table.filter(pl.col("factor") == 1)["excess_kurtosis"].item()
    k12 = table.filter(pl.col("factor") == 12)["excess_kurtosis"].item()
    assert k1 > k12 > 0


# --------------------------------------------------------------------------- #
# Cross-asset
# --------------------------------------------------------------------------- #
def test_engle_granger_detects_cointegration() -> None:
    n = 4_000
    common = np.cumsum(RNG.standard_normal(n))
    p1 = common + RNG.standard_normal(n) * 0.5
    p2 = 0.8 * common + RNG.standard_normal(n) * 0.5
    assert engle_granger(p1, p2)["pvalue"] < 0.05

    rng = np.random.default_rng(0)
    ind1 = np.cumsum(rng.standard_normal(n))
    ind2 = np.cumsum(rng.standard_normal(n))
    assert engle_granger(ind1, ind2)["pvalue"] > 0.05


# --------------------------------------------------------------------------- #
# Regime windows
# --------------------------------------------------------------------------- #
def test_market_regimes_partition_development_window() -> None:
    # Contiguous, ordered, spanning 2020-01-01 .. 2026-01-01 with no overlap.
    assert MARKET_REGIMES[0][1] == "2020-01-01"
    assert MARKET_REGIMES[-1][2] == "2026-01-01"
    import itertools

    for (_, _, end), (_, start, _) in itertools.pairwise(MARKET_REGIMES):
        assert end == start


def test_market_regime_stats_computes_corr() -> None:
    n = 60_000
    r_btc = RNG.standard_normal(n) * 0.01
    r_eth = 0.8 * r_btc + 0.6 * RNG.standard_normal(n) * 0.01
    btc, eth = _frame(r_btc), _frame(r_eth)
    stats = market_regime_stats(btc, eth)
    assert stats.height >= 4
    assert float(cast("float", stats["btc_eth_corr"].min() or -1.0)) > 0.5


# --------------------------------------------------------------------------- #
# Feature/label characterisation
# --------------------------------------------------------------------------- #
def test_mutual_information_floor_separates_dependence() -> None:
    n = 6_000
    ret = RNG.standard_normal(n) * 0.01
    frame = _frame(ret).with_columns(
        pl.Series("informative", np.concatenate([ret[1:], [0.0]])),
        pl.Series("noise", RNG.standard_normal(n)),
    )
    mi = mutual_information_by_horizon(
        frame, ["informative", "noise"], horizons=[1], n_permutations=3
    )
    informative = mi.filter(pl.col("feature") == "informative")
    noise = mi.filter(pl.col("feature") == "noise")
    assert informative["mi_nats"].item() > 3 * informative["noise_floor_max"].item()
    assert noise["mi_nats"].item() < noise["noise_floor_max"].item() + 0.01


def test_pca_and_correlation_tools() -> None:
    n = 5_000
    a = RNG.standard_normal(n)
    frame = pl.DataFrame(
        {"a": a, "b": a + RNG.standard_normal(n) * 0.01, "c": RNG.standard_normal(n)}
    )
    corr = feature_correlation_matrix(frame, ["a", "b", "c"])
    pairs = high_correlation_pairs(corr)
    assert pairs.height == 1 and pairs["feature_a"].item() == "a"
    scree = pca_scree(frame, ["a", "b", "c"])
    assert scree["explained_share"].sum() == pytest.approx(1.0)
    assert scree["explained_share"][0] > 0.6  # a and b share one component


def test_leverage_effect_bounds() -> None:
    result = leverage_effect(_frame(WHITE), forward_bars=24)
    assert -1.0 <= result["corr"] <= 1.0
    assert abs(result["corr"]) < 0.05  # white noise: no leverage relation


def test_label_summary_shares_sum_to_one() -> None:
    labels = pl.DataFrame(
        {
            "label": [1, -1, 0, 1],
            "meta_label": [1, 0, 0, 1],
            "barrier_touched": ["upper", "lower", "vertical", "upper"],
            "holding_bars": [3, 5, 24, 2],
        }
    )
    summary = label_summary(labels)
    assert summary["share_positive"] + summary["share_negative"] + summary[
        "share_zero"
    ] == pytest.approx(1.0)
    assert summary["share_upper"] + summary["share_lower"] + summary[
        "share_vertical"
    ] == pytest.approx(1.0)
    assert summary["median_holding_bars"] == 4.0
