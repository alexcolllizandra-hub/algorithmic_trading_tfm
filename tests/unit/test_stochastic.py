"""Statistical properties and reproducibility of the stochastic benchmarks."""

from __future__ import annotations

import numpy as np
import pytest

from perp_lab.stochastic import (
    GbmParameters,
    OuParameters,
    bootstrap_return_paths,
    calibrate_gbm,
    calibrate_ou,
    compare_risk_estimates,
    drawdown_distribution,
    first_passage_summary,
    max_drawdowns,
    reversion_detection_power,
    ruin_probability,
    search_false_positive_rate,
    simulate_gbm,
    simulate_ou,
)

# --------------------------------------------------------------------------- #
# GBM: calibration and simulation round-trip
# --------------------------------------------------------------------------- #


def test_gbm_calibration_recovers_the_parameters_it_simulated_with() -> None:
    truth = GbmParameters(drift=0.0002, volatility=0.01, n_observations=100_000)
    path = simulate_gbm(truth, n_paths=1, n_steps=100_000, seed=1)[0]
    fitted = calibrate_gbm(np.diff(np.log(path)))
    assert fitted.volatility == pytest.approx(truth.volatility, rel=0.02)
    assert fitted.drift == pytest.approx(truth.drift, abs=3 * fitted.drift_standard_error)


def test_gbm_log_returns_are_serially_independent_by_construction() -> None:
    params = GbmParameters(drift=0.0, volatility=0.01, n_observations=50_000)
    path = simulate_gbm(params, n_paths=1, n_steps=50_000, seed=2)[0]
    r = np.diff(np.log(path))
    autocorrelation = float(np.corrcoef(r[:-1], r[1:])[0, 1])
    assert abs(autocorrelation) < 0.02


def test_the_drift_standard_error_shows_the_drift_is_not_knowable() -> None:
    # The documented limitation, made quantitative: over a year of hourly bars a
    # realistic drift is swamped by its own estimation error.
    n = 365 * 24
    params = GbmParameters(drift=0.00002, volatility=0.01, n_observations=n)
    assert params.drift_standard_error > params.drift
    assert abs(params.drift_t_statistic) < 1.0


def test_gbm_simulation_is_reproducible_and_seed_sensitive() -> None:
    params = GbmParameters(drift=0.0, volatility=0.01, n_observations=1000)
    first = simulate_gbm(params, n_paths=5, n_steps=200, seed=3)
    assert np.array_equal(first, simulate_gbm(params, n_paths=5, n_steps=200, seed=3))
    assert not np.allclose(first, simulate_gbm(params, n_paths=5, n_steps=200, seed=4))


def test_gbm_paths_start_at_the_initial_price_and_stay_positive() -> None:
    params = GbmParameters(drift=-0.01, volatility=0.05, n_observations=1000)
    paths = simulate_gbm(params, n_paths=20, n_steps=500, seed=5, initial_price=250.0)
    assert paths.shape == (20, 501)
    assert np.all(paths[:, 0] == 250.0)
    assert np.all(paths > 0.0)


def test_gbm_calibration_refuses_a_sample_it_cannot_fit() -> None:
    with pytest.raises(ValueError, match="at least two finite"):
        calibrate_gbm(np.array([0.01]))


# --------------------------------------------------------------------------- #
# Ornstein-Uhlenbeck
# --------------------------------------------------------------------------- #


def test_ou_calibration_recovers_the_half_life_it_simulated_with() -> None:
    truth = OuParameters(kappa=0.05, theta=2.0, sigma=0.3)
    path = simulate_ou(truth, n_paths=1, n_steps=200_000, seed=6)[0]
    fitted = calibrate_ou(path)
    assert fitted.half_life == pytest.approx(truth.half_life, rel=0.1)
    assert fitted.theta == pytest.approx(truth.theta, abs=0.1)


def test_an_ou_path_reverts_and_a_gbm_path_does_not() -> None:
    # The defining difference: an OU level is negatively autocorrelated in its
    # increments, a random walk's increments are not autocorrelated at all.
    ou = simulate_ou(
        OuParameters(kappa=0.1, theta=0.0, sigma=1.0), n_paths=1, n_steps=20_000, seed=7
    )[0]
    walk = np.cumsum(np.random.default_rng(7).normal(0.0, 1.0, size=20_000))
    ou_increment_autocorrelation = float(np.corrcoef(np.diff(ou)[:-1], np.diff(ou)[1:])[0, 1])
    walk_increment_autocorrelation = float(np.corrcoef(np.diff(walk)[:-1], np.diff(walk)[1:])[0, 1])
    assert ou_increment_autocorrelation < -0.02
    assert abs(walk_increment_autocorrelation) < 0.02


def test_ou_paths_start_stationary_so_there_is_no_burn_in_trend() -> None:
    params = OuParameters(kappa=0.1, theta=5.0, sigma=1.0)
    paths = simulate_ou(params, n_paths=4000, n_steps=10, seed=8)
    assert float(paths[:, 0].mean()) == pytest.approx(params.theta, abs=0.1)
    assert float(paths[:, 0].std()) == pytest.approx(params.stationary_sd, rel=0.1)
    assert float(paths[:, -1].std()) == pytest.approx(params.stationary_sd, rel=0.1)


def test_ou_calibration_refuses_a_random_walk() -> None:
    # Least squares on a random walk returns an AR(1) slope just below one, so
    # the (0, 1) check alone would accept it and report a vast half-life. The
    # identifiability guard is what stops estimator bias becoming a mechanism.
    walk = np.cumsum(np.random.default_rng(0).normal(0.0, 1.0, size=5000))
    with pytest.raises(ValueError, match="not identifiable"):
        calibrate_ou(walk)


def test_the_identifiability_guard_is_not_a_unit_root_test() -> None:
    # Documented limitation, pinned so it cannot be quietly forgotten: some
    # random-walk realisations produce a fitted half-life short enough to pass.
    # A successful calibration is therefore not evidence of mean reversion.
    walk = np.cumsum(np.random.default_rng(3).normal(0.0, 1.0, size=5000))
    fitted = calibrate_ou(walk)
    assert fitted.half_life > 100  # implausibly slow, but under the 500-bar bar
    rejected = 0
    for seed in range(20):
        sample = np.cumsum(np.random.default_rng(seed).normal(0.0, 1.0, size=5000))
        try:
            calibrate_ou(sample)
        except ValueError:
            rejected += 1
    assert 12 <= rejected <= 19, f"expected most but not all random walks refused, got {rejected}"


def test_ou_calibration_refuses_reversion_slower_than_the_sample() -> None:
    # An almost noiseless decay at b = 0.999: the half-life is 693 bars, which a
    # 400-bar sample cannot resolve even though the reversion is real here.
    rng = np.random.default_rng(23)
    series = np.empty(400)
    series[0] = 1.0
    for t in range(399):
        series[t + 1] = 0.999 * series[t] + rng.normal(0.0, 1e-6)
    with pytest.raises(ValueError, match="not identifiable"):
        calibrate_ou(series)


def test_ou_rejects_a_non_positive_reversion_speed() -> None:
    with pytest.raises(ValueError, match="kappa must be positive"):
        OuParameters(kappa=0.0, theta=0.0, sigma=1.0)


# --------------------------------------------------------------------------- #
# What a search finds when there is nothing to find
# --------------------------------------------------------------------------- #


def _best_of_k(k: int):
    """A selection procedure that reports the best of ``k`` random rules.

    Each 'rule' is a random long/short mask on the path's returns; the statistic
    is the annualisation-free Sharpe of the selected one. It is a caricature of a
    search, which is the point: even a caricature manufactures a good-looking
    winner out of noise.
    """

    def select(prices: np.ndarray, rng: np.random.Generator) -> float:
        returns = np.diff(prices) / prices[:-1]
        best = -np.inf
        for _ in range(k):
            position = rng.choice(np.array([-1.0, 1.0]), size=returns.size)
            pnl = position * returns
            sd = pnl.std(ddof=1)
            best = max(best, float(pnl.mean() / sd) if sd > 0 else 0.0)
        return best

    return select


def test_searching_harder_on_noise_manufactures_a_better_winner() -> None:
    params = GbmParameters(drift=0.0, volatility=0.01, n_observations=500)
    common = {"params": params, "n_trials": 40, "n_steps": 500, "seed": 10, "threshold": 0.05}
    narrow = search_false_positive_rate(_best_of_k(1), **common)
    wide = search_false_positive_rate(_best_of_k(50), **common)

    # Nothing is predictable in either case; only the budget differs.
    assert wide.median > narrow.median
    assert wide.false_positive_rate > narrow.false_positive_rate


def test_the_null_report_is_reproducible_from_its_seed() -> None:
    params = GbmParameters(drift=0.0, volatility=0.01, n_observations=300)
    common = {"params": params, "n_trials": 15, "n_steps": 300, "seed": 11, "threshold": 0.05}
    first = search_false_positive_rate(_best_of_k(5), **common)
    second = search_false_positive_rate(_best_of_k(5), **common)
    assert first.to_dict() == second.to_dict()
    assert np.array_equal(first.statistics, second.statistics)


def test_a_procedure_with_no_power_is_distinguishable_from_one_with_power() -> None:
    # A detector that fires no more often on a genuinely reverting market than on
    # noise tells us nothing when it stays silent on real data.
    def reversion_score(prices: np.ndarray, _rng: np.random.Generator) -> float:
        r = np.diff(prices)
        return -float(np.corrcoef(r[:-1], r[1:])[0, 1])

    gbm = GbmParameters(drift=0.0, volatility=0.01, n_observations=2000)
    # kappa = 0.5 gives increments an autocorrelation near -0.2, comfortably
    # above the 0.05 detection threshold; a slower process would sit on it.
    ou = OuParameters(kappa=0.5, theta=0.0, sigma=1.0)
    null = search_false_positive_rate(
        reversion_score, gbm, n_trials=25, n_steps=2000, seed=12, threshold=0.05
    )
    powered = reversion_detection_power(
        reversion_score, ou, n_trials=25, n_steps=2000, seed=12, threshold=0.05
    )
    assert null.false_positive_rate < 0.2
    assert powered.false_positive_rate > 0.9


# --------------------------------------------------------------------------- #
# First passage: ground truth for the triple-barrier labeler
# --------------------------------------------------------------------------- #


def test_symmetric_barriers_on_a_driftless_path_are_equally_likely() -> None:
    params = GbmParameters(drift=0.0, volatility=0.01, n_observations=1000)
    summary = first_passage_summary(
        params, upper=0.02, lower=-0.02, horizon=200, n_paths=4000, seed=13
    )
    assert summary.upper_first == pytest.approx(summary.lower_first, abs=0.03)
    assert summary.upper_first + summary.lower_first + summary.no_touch == pytest.approx(1.0)


def test_a_positive_drift_tilts_the_first_touch_upwards() -> None:
    drifted = GbmParameters(drift=0.002, volatility=0.01, n_observations=1000)
    summary = first_passage_summary(
        drifted, upper=0.02, lower=-0.02, horizon=200, n_paths=3000, seed=14
    )
    assert summary.upper_first > summary.lower_first


def test_a_wider_barrier_is_touched_less_often_and_later() -> None:
    params = GbmParameters(drift=0.0, volatility=0.01, n_observations=1000)
    tight = first_passage_summary(
        params, upper=0.01, lower=-0.01, horizon=100, n_paths=2000, seed=15
    )
    wide = first_passage_summary(
        params, upper=0.05, lower=-0.05, horizon=100, n_paths=2000, seed=15
    )
    assert wide.no_touch > tight.no_touch
    assert wide.mean_bars_to_touch > tight.mean_bars_to_touch


def test_first_passage_rejects_barriers_on_the_wrong_side_of_entry() -> None:
    params = GbmParameters(drift=0.0, volatility=0.01, n_observations=100)
    with pytest.raises(ValueError, match="upper must be positive"):
        first_passage_summary(params, upper=-0.01, lower=-0.02, horizon=10, n_paths=10, seed=16)


# --------------------------------------------------------------------------- #
# Drawdown, ruin, and bootstrap vs GBM
# --------------------------------------------------------------------------- #


def test_max_drawdown_of_a_monotonically_rising_path_is_zero() -> None:
    rising = np.full((1, 100), 0.01)
    assert max_drawdowns(rising)[0] == pytest.approx(0.0, abs=1e-12)


def test_max_drawdown_matches_a_hand_computed_path() -> None:
    # +100%, then -50%, then +10%: peak 2.0, trough 1.0, so the drawdown is 50%.
    path = np.array([[1.0, -0.5, 0.1]])
    assert max_drawdowns(path)[0] == pytest.approx(0.5)


def test_ruin_probability_rises_with_a_lower_survival_threshold() -> None:
    rng = np.random.default_rng(17)
    paths = rng.normal(-0.001, 0.03, size=(500, 400))
    assert ruin_probability(paths, ruin_threshold=0.2) >= ruin_probability(
        paths, ruin_threshold=0.6
    )


def test_the_block_bootstrap_preserves_clustering_that_gbm_destroys() -> None:
    # A series of alternating calm and violent regimes: the bootstrap should keep
    # the violent runs intact and therefore report deeper drawdowns than a
    # Gaussian model fitted to the same unconditional moments.
    rng = np.random.default_rng(18)
    calm = rng.normal(0.0, 0.002, size=200)
    violent = rng.normal(-0.004, 0.03, size=200)
    returns = np.concatenate([np.tile(np.concatenate([calm, violent]), 5)])
    comparison = compare_risk_estimates(
        returns,
        n_paths=300,
        n_steps=400,
        block_probability=0.02,
        seed=19,
        ruin_threshold=0.3,
    )
    assert set(comparison) == {"block_bootstrap", "gbm"}
    assert (
        comparison["block_bootstrap"].quantile_95_max_drawdown
        > comparison["gbm"].quantile_95_max_drawdown
    )


def test_bootstrap_paths_only_ever_reuse_observed_returns() -> None:
    returns = np.array([-0.03, -0.01, 0.0, 0.01, 0.04])
    paths = bootstrap_return_paths(returns, n_paths=20, n_steps=50, block_probability=0.1, seed=20)
    assert paths.shape == (20, 50)
    assert np.all(np.isin(paths, returns))


def test_bootstrap_paths_are_reproducible_from_their_seed() -> None:
    returns = np.random.default_rng(21).normal(0.0, 0.01, size=300)
    kwargs = {"n_paths": 10, "n_steps": 100, "block_probability": 0.1, "seed": 22}
    assert np.array_equal(
        bootstrap_return_paths(returns, **kwargs),
        bootstrap_return_paths(returns, **kwargs),
    )


def test_drawdown_report_rejects_an_impossible_ruin_threshold() -> None:
    paths = np.zeros((5, 10))
    with pytest.raises(ValueError, match="ruin_threshold must lie strictly inside"):
        drawdown_distribution(paths, ruin_threshold=1.0)
