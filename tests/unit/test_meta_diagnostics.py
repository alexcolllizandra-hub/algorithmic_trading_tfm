"""Explanation, drift and economic diagnostics for the meta-label layer."""

from __future__ import annotations

import numpy as np
import pytest

from perp_lab.meta_labeling import (
    build_classifier,
    compare_primary_and_meta,
    feature_drift,
    meta_position_scale,
    permutation_importance_scores,
    population_stability_index,
)

FEATURES = ("signal", "noise_a", "noise_b")


def _fitted_model(n: int = 400, seed: int = 0):
    """A model whose label depends on the first feature and nothing else."""
    rng = np.random.default_rng(seed)
    x = rng.normal(0.0, 1.0, size=(n, 3))
    y = (1.8 * x[:, 0] + rng.normal(0.0, 1.0, size=n) > 0).astype(int)
    model = build_classifier("logistic_regression", seed=seed)
    model.fit(x, y)
    return model, x, y


# --------------------------------------------------------------------------- #
# Permutation importance
# --------------------------------------------------------------------------- #


def test_permutation_importance_finds_the_only_informative_feature() -> None:
    model, x, y = _fitted_model()
    scores = permutation_importance_scores(model, x, y, FEATURES, seed=3, n_repeats=10)
    assert scores["feature"][0] == "signal"
    informative = scores.filter(scores["feature"] == "signal")["importance_mean"][0]
    for name in ("noise_a", "noise_b"):
        assert informative > scores.filter(scores["feature"] == name)["importance_mean"][0]


def test_permutation_importance_is_deterministic_under_a_fixed_seed() -> None:
    model, x, y = _fitted_model()
    first = permutation_importance_scores(model, x, y, FEATURES, seed=11, n_repeats=5)
    second = permutation_importance_scores(model, x, y, FEATURES, seed=11, n_repeats=5)
    assert first.equals(second)


def test_permutation_importance_rejects_a_name_count_mismatch() -> None:
    model, x, y = _fitted_model()
    with pytest.raises(ValueError, match="names were supplied"):
        permutation_importance_scores(model, x, y, ("only_one",), seed=1, n_repeats=2)


# --------------------------------------------------------------------------- #
# Drift
# --------------------------------------------------------------------------- #


def test_psi_is_near_zero_for_two_draws_from_the_same_distribution() -> None:
    rng = np.random.default_rng(5)
    reference = rng.normal(0.0, 1.0, size=4000)
    current = rng.normal(0.0, 1.0, size=4000)
    assert population_stability_index(reference, current) < 0.1


def test_psi_grows_with_the_size_of_the_shift() -> None:
    rng = np.random.default_rng(6)
    reference = rng.normal(0.0, 1.0, size=4000)
    small = population_stability_index(reference, rng.normal(0.3, 1.0, size=4000))
    large = population_stability_index(reference, rng.normal(2.0, 1.0, size=4000))
    assert small < large
    assert large > 0.25


def test_psi_is_non_negative_because_it_is_a_symmetrised_divergence() -> None:
    rng = np.random.default_rng(7)
    reference = rng.normal(0.0, 1.0, size=1000)
    for shift in (-1.5, 0.0, 1.5):
        assert population_stability_index(reference, reference + shift) >= 0.0


def test_feature_drift_flags_only_the_feature_that_moved() -> None:
    rng = np.random.default_rng(8)
    reference = rng.normal(0.0, 1.0, size=(3000, 3))
    current = rng.normal(0.0, 1.0, size=(3000, 3))
    current[:, 1] += 3.0
    report = feature_drift(reference, current, FEATURES)
    assert report["feature"][0] == "noise_a"
    assert bool(report["severe_drift"][0])
    assert not any(report.filter(report["feature"] != "noise_a")["severe_drift"].to_list())
    shift = report.filter(report["feature"] == "noise_a")["mean_shift_in_reference_sd"][0]
    assert shift == pytest.approx(3.0, abs=0.2)


def test_feature_drift_rejects_mismatched_column_counts() -> None:
    rng = np.random.default_rng(9)
    with pytest.raises(ValueError, match="same feature columns"):
        feature_drift(rng.normal(size=(50, 3)), rng.normal(size=(50, 2)), FEATURES)


# --------------------------------------------------------------------------- #
# Position scaling: the meta-label may veto or resize, never reverse
# --------------------------------------------------------------------------- #


def test_position_scale_is_zero_below_the_threshold_and_positive_above() -> None:
    probability = np.array([0.0, 0.3, 0.59, 0.6, 0.8, 1.0])
    scale = meta_position_scale(probability, threshold=0.6, min_scale=0.5, max_scale=1.0)
    assert np.all(scale[:3] == 0.0)
    assert np.all(scale[3:] > 0.0)


def test_position_scale_is_never_negative_for_any_probability() -> None:
    # This is the contract that stops a meta-label inverting the primary rule.
    probability = np.linspace(0.0, 1.0, 501)
    for threshold in (0.05, 0.5, 0.95):
        scale = meta_position_scale(probability, threshold=threshold)
        assert np.all(scale >= 0.0)


def test_position_scale_is_monotone_in_confidence() -> None:
    probability = np.linspace(0.6, 1.0, 50)
    scale = meta_position_scale(probability, threshold=0.6, min_scale=0.5, max_scale=1.2)
    assert np.all(np.diff(scale) >= -1e-12)
    assert scale[-1] == pytest.approx(1.2)
    assert scale[0] == pytest.approx(0.5)


def test_position_scale_refuses_bounds_outside_the_frozen_limits() -> None:
    probability = np.array([0.7])
    with pytest.raises(ValueError, match="scales must satisfy"):
        meta_position_scale(probability, threshold=0.5, min_scale=0.5, max_scale=2.0)
    with pytest.raises(ValueError, match="scales must satisfy"):
        meta_position_scale(probability, threshold=0.5, min_scale=-0.1, max_scale=1.0)


# --------------------------------------------------------------------------- #
# Economic comparison: net return decides, not AUC
# --------------------------------------------------------------------------- #


def test_a_filter_that_removes_the_losers_adds_value() -> None:
    returns = np.array([-0.02, -0.01, 0.01, 0.02])
    probability = np.array([0.1, 0.2, 0.9, 0.95])
    result = compare_primary_and_meta(returns, probability, threshold=0.5)
    assert result.filtered_trades == 2
    assert result.trades_removed == 2
    assert result.filtered_net_return > result.primary_net_return
    assert result.meta_adds_value


def test_a_filter_that_removes_the_winners_does_not_add_value() -> None:
    returns = np.array([-0.02, -0.01, 0.01, 0.05])
    probability = np.array([0.9, 0.95, 0.1, 0.2])
    result = compare_primary_and_meta(returns, probability, threshold=0.5)
    assert result.filtered_net_return < result.primary_net_return
    assert not result.meta_adds_value


def test_a_sharper_classifier_that_loses_money_is_still_rejected() -> None:
    # The filter keeps a majority of small winners and drops one large one, so
    # hit rate rises while net return falls. Only net return may open the gate.
    returns = np.array([0.001, 0.001, 0.001, -0.05, 0.20])
    probability = np.array([0.9, 0.9, 0.9, 0.1, 0.1])
    result = compare_primary_and_meta(returns, probability, threshold=0.5)
    assert result.filtered_hit_rate > result.primary_hit_rate
    assert not result.meta_adds_value


def test_declining_a_trade_saves_its_cost() -> None:
    returns = np.array([0.0, 0.0])
    probability = np.array([0.1, 0.9])
    free = compare_primary_and_meta(returns, probability, threshold=0.5, cost_per_trade=0.0)
    costly = compare_primary_and_meta(returns, probability, threshold=0.5, cost_per_trade=0.001)
    assert free.cost_saved == 0.0
    assert costly.cost_saved == pytest.approx(0.001)
    assert costly.filtered_net_return > free.filtered_net_return


def test_taking_every_trade_at_full_size_reproduces_the_primary_arm() -> None:
    rng = np.random.default_rng(12)
    returns = rng.normal(0.0, 0.01, size=200)
    probability = np.full(200, 0.99)
    result = compare_primary_and_meta(returns, probability, threshold=0.5)
    assert result.filtered_net_return == pytest.approx(result.primary_net_return)
    assert result.return_delta == pytest.approx(0.0)
    assert result.filtered_trades == result.primary_trades


def test_the_comparison_rejects_mismatched_inputs() -> None:
    with pytest.raises(ValueError, match="disagree on the number of trades"):
        compare_primary_and_meta(np.zeros(3), np.zeros(4), threshold=0.5)
    with pytest.raises(ValueError, match="at least one trade"):
        compare_primary_and_meta(np.zeros(0), np.zeros(0), threshold=0.5)
