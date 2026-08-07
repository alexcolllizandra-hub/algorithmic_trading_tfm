"""Tests for the strict ExperimentConfig models and cross-field validation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from perp_lab.config import load_experiment_config
from perp_lab.config.experiment import ExperimentConfig

_PERIODS = {
    "development_start": "2020-01-01T00:00:00Z",
    "development_end_exclusive": "2026-01-01T00:00:00Z",
    "holdout_start": "2026-01-01T00:00:00Z",
    "cutoff_exclusive": "2026-07-01T00:00:00Z",
}


def _config(**overrides: object) -> ExperimentConfig:
    payload: dict[str, object] = {"periods": dict(_PERIODS)}
    payload.update(overrides)
    return ExperimentConfig.model_validate(payload)


def test_repo_experiment_yaml_loads() -> None:
    cfg = load_experiment_config("configs/experiment.yaml")
    assert cfg.timeframes.primary == "1h"
    assert cfg.periods.holdout_start == datetime(2026, 1, 1, tzinfo=UTC)


def test_periods_must_be_contiguous_and_ordered() -> None:
    bad = dict(_PERIODS, development_end_exclusive="2025-12-01T00:00:00Z")
    with pytest.raises(ValidationError, match=r"contiguous|holdout_start"):
        ExperimentConfig.model_validate({"periods": bad})


def test_holdout_before_cutoff_enforced() -> None:
    bad = dict(
        _PERIODS,
        development_end_exclusive="2026-08-01T00:00:00Z",
        holdout_start="2026-08-01T00:00:00Z",
    )
    with pytest.raises(ValidationError):
        ExperimentConfig.model_validate({"periods": bad})


def test_search_budget_parity_enforced() -> None:
    with pytest.raises(ValidationError, match="budget parity"):
        _config(search={"evaluation_budget": 999})


def test_search_budget_parity_ok_when_matched() -> None:
    # Elitism (default 5) means only generation 0 evaluates a full population:
    # 20 + 12 * (20 - 5) = 200 unique evaluations.
    cfg = _config(
        search={
            "evaluation_budget": 200,
            "genetic_algorithm": {"population_size": 20, "generations": 13},
        }
    )
    assert cfg.search.evaluation_budget == 200


def test_search_budget_parity_rejects_naive_population_times_generations() -> None:
    """population * generations overstates the GA's evaluations when elitism > 0."""
    with pytest.raises(ValidationError, match="budget parity"):
        _config(
            search={
                "evaluation_budget": 200,
                "genetic_algorithm": {"population_size": 20, "generations": 10},
            }
        )


def test_feature_windows_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        _config(features={"return_windows": [0, 1, 2]})


def test_unknown_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _config(unexpected_key=123)


def test_execution_must_be_next_bar_open() -> None:
    with pytest.raises(ValidationError):
        _config(strategies={"execution": "same_bar_close"})


def test_purge_and_embargo_are_derived() -> None:
    cfg = _config()
    # max(label horizon 24, max holding 96) = 96 bars.
    assert cfg.purge_bars == 96
    # embargo = purge + ceil(0.01 * test_days(90) * 24 bars/day) = 96 + 22.
    assert cfg.embargo_bars == 118
    assert cfg.embargo_bars >= cfg.purge_bars


def test_check_against_contract_detects_holdout_mismatch() -> None:
    cfg = _config()
    with pytest.raises(ValueError, match="holdout"):
        cfg.check_against_contract(
            holdout_start=datetime(2025, 1, 1, tzinfo=UTC),
            cutoff=datetime(2026, 7, 1, tzinfo=UTC),
        )


def test_check_against_contract_passes_when_aligned() -> None:
    cfg = _config()
    cfg.check_against_contract(
        holdout_start=datetime(2026, 1, 1, tzinfo=UTC),
        cutoff=datetime(2026, 7, 1, tzinfo=UTC),
    )


def test_atr_multiples_must_be_positive() -> None:
    with pytest.raises(ValidationError, match="ATR"):
        _config(strategies={"stop_loss_atr": [0.0, 1.0]})


def test_mean_reversion_entry_must_exceed_exit() -> None:
    with pytest.raises(ValidationError, match="entry_z"):
        _config(strategies={"families": {"mean_reversion": {"entry_z": [0.5], "exit_z": [1.0]}}})


def test_momentum_fast_must_offer_values_below_slow() -> None:
    with pytest.raises(ValidationError, match="fast_ma"):
        _config(strategies={"families": {"momentum": {"fast_ma": [400], "slow_ma": [96]}}})


def test_unknown_allowed_direction_rejected() -> None:
    with pytest.raises(ValidationError, match="allowed_directions"):
        _config(strategies={"allowed_directions": ["sideways"]})
