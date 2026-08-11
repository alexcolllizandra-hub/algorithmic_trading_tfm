"""Selection-bias corrections required by the Gate S1 contract."""

from __future__ import annotations

import numpy as np
import pytest

from perp_lab.evaluation.multiple_testing import (
    benjamini_hochberg,
    deflated_sharpe_ratio,
    expected_maximum_sharpe,
    probability_of_backtest_overfitting,
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
