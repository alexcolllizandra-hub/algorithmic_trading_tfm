"""Selection-bias corrections required by the Gate S1 contract."""

from __future__ import annotations

import numpy as np
import pytest

from perp_lab.evaluation.multiple_testing import (
    benjamini_hochberg,
    benjamini_hochberg_correction,
    deflated_sharpe_ratio,
    expected_maximum_sharpe,
    holm_bonferroni,
    probability_of_backtest_overfitting,
    reality_check,
    stationary_bootstrap_indices,
    superior_predictive_ability,
)


def test_a_single_trial_carries_no_selection_bias() -> None:
    assert expected_maximum_sharpe(1, sharpe_std=0.5) == 0.0


def test_expected_maximum_grows_with_the_number_of_trials() -> None:
    few = expected_maximum_sharpe(10, sharpe_std=0.3)
    many = expected_maximum_sharpe(1000, sharpe_std=0.3)
    assert 0.0 < few < many


def test_expected_maximum_scales_with_dispersion() -> None:
    narrow = expected_maximum_sharpe(100, sharpe_std=0.1)
    wide = expected_maximum_sharpe(100, sharpe_std=0.4)
    assert wide > narrow
    assert wide == pytest.approx(4.0 * narrow, rel=1e-9)


def test_deflated_sharpe_falls_as_more_configurations_are_tried() -> None:
    kwargs = {"n_observations": 2000, "sharpe_std": 0.05, "skewness": -0.2, "kurtosis": 6.0}
    honest = deflated_sharpe_ratio(0.06, n_trials=1, **kwargs)
    mined = deflated_sharpe_ratio(0.06, n_trials=5000, **kwargs)
    assert honest.deflated_sharpe > mined.deflated_sharpe
    assert mined.benchmark_sharpe > honest.benchmark_sharpe


def test_deflated_sharpe_records_every_input() -> None:
    result = deflated_sharpe_ratio(
        0.05, n_trials=200, n_observations=1000, sharpe_std=0.02, skewness=0.1, kurtosis=4.0
    )
    payload = result.to_dict()
    assert payload["n_trials"] == 200
    assert payload["n_observations"] == 1000
    assert 0.0 <= float(payload["deflated_sharpe"]) <= 1.0
    assert result.significant_at == pytest.approx(1.0 - result.deflated_sharpe)


def test_deflated_sharpe_rejects_excess_kurtosis_passed_as_raw() -> None:
    with pytest.raises(ValueError, match="raw fourth standardised moment"):
        deflated_sharpe_ratio(0.05, n_trials=10, n_observations=500, sharpe_std=0.01, kurtosis=0.0)


def test_pbo_reports_one_split_per_half_sized_block_combination() -> None:
    rng = np.random.default_rng(3)
    result = probability_of_backtest_overfitting(rng.normal(size=(240, 40)), n_partitions=8)
    assert result.n_splits == 70  # C(8, 4)
    assert len(result.logits) == 70


def test_pbo_approaches_one_half_when_every_configuration_is_noise() -> None:
    # The 70 CSCV splits share blocks, so a single draw is noisy; the estimator's
    # unbiasedness is a property of its expectation, not of one matrix.
    values = [
        probability_of_backtest_overfitting(
            np.random.default_rng(seed).normal(size=(240, 40)), n_partitions=8
        ).pbo
        for seed in range(20)
    ]
    assert float(np.mean(values)) == pytest.approx(0.5, abs=0.1)


def test_pbo_is_zero_when_one_configuration_is_genuinely_better() -> None:
    for seed in range(5):
        rng = np.random.default_rng(100 + seed)
        matrix = rng.normal(scale=0.2, size=(240, 20))
        matrix[:, 7] += 3.0  # better in every subsample, not only in-sample
        assert probability_of_backtest_overfitting(matrix, n_partitions=8).pbo == 0.0


def test_pbo_rejects_an_odd_partition_count() -> None:
    with pytest.raises(ValueError, match="even number"):
        probability_of_backtest_overfitting(np.zeros((100, 5)) + 1.0, n_partitions=7)


def test_pbo_rejects_non_finite_performance() -> None:
    matrix = np.ones((100, 5))
    matrix[3, 2] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        probability_of_backtest_overfitting(matrix)


def test_benjamini_hochberg_controls_the_discovery_set() -> None:
    p_values = [0.001, 0.008, 0.02, 0.2, 0.9]
    rejected = benjamini_hochberg(p_values, alpha=0.05)
    assert rejected == (True, True, True, False, False)


def test_benjamini_hochberg_rejects_nothing_when_no_signal_exists() -> None:
    assert benjamini_hochberg([0.4, 0.6, 0.99], alpha=0.05) == (False, False, False)


def test_benjamini_hochberg_preserves_input_order() -> None:
    rejected = benjamini_hochberg([0.9, 0.001, 0.5], alpha=0.05)
    assert rejected == (False, True, False)


def test_benjamini_hochberg_validates_its_inputs() -> None:
    assert benjamini_hochberg([]) == ()
    with pytest.raises(ValueError, match="p_values"):
        benjamini_hochberg([0.1, 1.5])


# --------------------------------------------------------------------------- #
# Stationary bootstrap
# --------------------------------------------------------------------------- #


def test_stationary_bootstrap_returns_indices_inside_the_series() -> None:
    rng = np.random.default_rng(0)
    idx = stationary_bootstrap_indices(50, 100, block_probability=0.2, rng=rng)
    assert idx.shape == (100, 50)
    assert idx.min() >= 0
    assert idx.max() <= 49


def test_a_restart_probability_of_one_resamples_independently() -> None:
    rng = np.random.default_rng(1)
    idx = stationary_bootstrap_indices(200, 200, block_probability=1.0, rng=rng)
    # Every step restarts, so consecutive positions are almost never adjacent.
    contiguous = (idx[:, 1:] == (idx[:, :-1] + 1) % 200).mean()
    assert contiguous < 0.02


def test_a_low_restart_probability_preserves_contiguous_blocks() -> None:
    rng = np.random.default_rng(1)
    idx = stationary_bootstrap_indices(200, 200, block_probability=0.05, rng=rng)
    contiguous = (idx[:, 1:] == (idx[:, :-1] + 1) % 200).mean()
    assert contiguous > 0.9, "block resampling must keep the time ordering inside blocks"


def test_stationary_bootstrap_validates_its_inputs() -> None:
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="block_probability"):
        stationary_bootstrap_indices(10, 5, block_probability=0.0, rng=rng)
    with pytest.raises(ValueError, match="n_observations"):
        stationary_bootstrap_indices(1, 5, block_probability=0.5, rng=rng)


# --------------------------------------------------------------------------- #
# Hansen SPA and White's Reality Check
# --------------------------------------------------------------------------- #


def _null_differentials(seed: int, n_obs: int = 300, n_candidates: int = 15) -> np.ndarray:
    return np.random.default_rng(seed).normal(0.0, 1.0, size=(n_obs, n_candidates))


def test_spa_does_not_find_significance_when_no_candidate_beats_the_benchmark() -> None:
    p_values = [
        superior_predictive_ability(_null_differentials(seed), n_bootstrap=400, seed=seed).p_value
        for seed in range(12)
    ]
    assert float(np.mean(p_values)) > 0.25, "p-values must not collapse under the null"
    assert float(np.mean(np.asarray(p_values) < 0.05)) <= 0.25


def test_spa_detects_a_planted_signal() -> None:
    for seed in range(5):
        rng = np.random.default_rng(200 + seed)
        differentials = rng.normal(0.0, 1.0, size=(400, 15))
        differentials[:, 4] += 0.3
        result = superior_predictive_ability(differentials, n_bootstrap=400, seed=seed)
        assert result.p_value < 0.05
        assert result.best_candidate == 4
        assert result.significant_at_5pct


def test_spa_reports_no_evidence_when_every_candidate_is_worse() -> None:
    differentials = np.random.default_rng(3).normal(-1.0, 1.0, size=(300, 15))
    result = superior_predictive_ability(differentials, n_bootstrap=400, seed=3)
    assert result.statistic == 0.0
    assert result.p_value == 1.0


def test_spa_is_more_powerful_than_the_reality_check_when_bad_candidates_abound() -> None:
    # One genuinely good candidate buried among many hopeless ones. The Reality
    # Check lets the hopeless candidates inflate its null distribution; Hansen's
    # consistent recentring removes them.
    rng = np.random.default_rng(7)
    differentials = rng.normal(-1.0, 1.0, size=(400, 40))
    differentials[:, 0] = rng.normal(0.18, 1.0, size=400)
    spa = superior_predictive_ability(differentials, n_bootstrap=600, seed=7)
    rc = reality_check(differentials, n_bootstrap=600, seed=7)
    assert spa.p_value < rc.p_value


def test_reality_check_behaves_sensibly_under_the_null_and_with_a_signal() -> None:
    null_p = [
        reality_check(_null_differentials(seed), n_bootstrap=400, seed=seed).p_value
        for seed in range(8)
    ]
    assert float(np.mean(null_p)) > 0.25

    rng = np.random.default_rng(11)
    planted = rng.normal(0.0, 1.0, size=(400, 15))
    planted[:, 2] += 0.4
    assert reality_check(planted, n_bootstrap=400, seed=11).p_value < 0.05


def test_snooping_tests_are_deterministic_for_a_given_seed() -> None:
    differentials = _null_differentials(5)
    first = superior_predictive_ability(differentials, n_bootstrap=200, seed=99)
    second = superior_predictive_ability(differentials, n_bootstrap=200, seed=99)
    assert first.p_value == second.p_value
    assert first.to_dict() == second.to_dict()


def test_spa_records_its_own_configuration() -> None:
    result = superior_predictive_ability(_null_differentials(0), n_bootstrap=200, seed=0)
    payload = result.to_dict()
    assert payload["test"] == "hansen_spa_consistent"
    assert payload["n_candidates"] == 15
    assert payload["n_observations"] == 300
    assert payload["n_bootstrap"] == 200


def test_snooping_tests_reject_malformed_input() -> None:
    with pytest.raises(ValueError, match="2-D"):
        superior_predictive_ability(np.zeros(10), n_bootstrap=10)
    with pytest.raises(ValueError, match="non-finite"):
        superior_predictive_ability(np.full((10, 2), np.nan), n_bootstrap=10)
    with pytest.raises(ValueError, match="at least 4 observations"):
        superior_predictive_ability(np.zeros((3, 2)) + 1.0, n_bootstrap=10)


# --------------------------------------------------------------------------- #
# Holm (FWER) and the BH variant that also reports adjusted values
# --------------------------------------------------------------------------- #


def test_holm_scales_the_smallest_p_value_by_the_full_family_size() -> None:
    # The most significant of five tests is multiplied by 5, the next by 4, and
    # so on; that step-down is the whole difference from plain Bonferroni.
    result = holm_bonferroni([0.001, 0.008, 0.02, 0.2, 0.9], alpha=0.05)
    assert result.adjusted_p_values[0] == pytest.approx(0.005)
    assert result.adjusted_p_values[1] == pytest.approx(0.032)
    assert result.rejected == (True, True, False, False, False)
    assert result.n_rejected == 2


def test_holm_is_more_conservative_than_benjamini_hochberg() -> None:
    p_values = [0.001, 0.008, 0.02, 0.2, 0.9]
    fwer = holm_bonferroni(p_values, alpha=0.05)
    fdr = benjamini_hochberg_correction(p_values, alpha=0.05)
    assert fwer.n_rejected <= fdr.n_rejected
    assert all(a >= b for a, b in zip(fwer.adjusted_p_values, fdr.adjusted_p_values, strict=True))


def test_holm_stops_at_the_first_failure_even_if_a_later_test_would_pass() -> None:
    # 0.04 alone would clear alpha, but Holm cannot reject it while the more
    # significant 0.03 has already failed its own, stricter threshold.
    result = holm_bonferroni([0.03, 0.04], alpha=0.05)
    assert result.rejected == (False, False)


def test_adjusted_values_are_returned_in_the_input_order() -> None:
    shuffled = [0.9, 0.001, 0.2, 0.008]
    result = holm_bonferroni(shuffled, alpha=0.05)
    assert result.adjusted_p_values[1] == pytest.approx(0.004)
    assert result.rejected == (False, True, False, True)


def test_bh_correction_agrees_with_the_flag_only_implementation() -> None:
    p_values = [0.001, 0.008, 0.02, 0.2, 0.9, 0.03, 0.5]
    assert benjamini_hochberg_correction(p_values, alpha=0.05).rejected == benjamini_hochberg(
        p_values, alpha=0.05
    )


def test_adjusted_values_never_exceed_one_and_stay_monotone() -> None:
    p_values = [0.4, 0.5, 0.6, 0.9, 0.95]
    for result in (
        holm_bonferroni(p_values, alpha=0.05),
        benjamini_hochberg_correction(p_values, alpha=0.05),
    ):
        adjusted = np.asarray(result.adjusted_p_values)
        assert adjusted.max() <= 1.0
        ordered = adjusted[np.argsort(p_values)]
        assert np.all(np.diff(ordered) >= -1e-12), result.method
        assert result.n_rejected == 0


def test_corrections_handle_an_empty_family_and_reject_bad_input() -> None:
    for correct in (holm_bonferroni, benjamini_hochberg_correction):
        empty = correct([])
        assert empty.n_tests == 0
        assert empty.rejected == ()
        with pytest.raises(ValueError, match="alpha"):
            correct([0.1], alpha=0.0)
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            correct([1.5])
