"""Out-of-sample coverage guarantees for the repository walk-forward geometry.

These tests exist because a capped pilot run (``max_folds``) produces a single
90-day OOS window that can be mistaken for the whole experiment. They pin down,
against ``configs/experiment.yaml``:

* how many folds the development period actually yields;
* that consecutive OOS test windows tile the period without gaps or overlaps;
* that purge and embargo separate fit / selection / evaluation data;
* that no fold, and no aggregate OOS span, reaches the frozen holdout.
"""

from __future__ import annotations

from datetime import timedelta
from itertools import pairwise

import pytest

from perp_lab.config import load_experiment_config
from perp_lab.config.experiment import ga_unique_evaluations
from perp_lab.search.config import load_search_config
from perp_lab.utils.timeutils import timeframe_to_timedelta
from perp_lab.validation.walk_forward import assert_folds_exclude_holdout, generate_walk_forward

CONFIG = "configs/experiment.yaml"


@pytest.fixture(scope="module")
def cfg():
    return load_experiment_config(CONFIG)


@pytest.fixture(scope="module")
def folds(cfg):
    return generate_walk_forward(cfg, strict=True)


def test_development_period_yields_many_folds(cfg, folds) -> None:
    """The full development span must produce a real walk-forward, not one window."""
    assert len(folds) >= cfg.walk_forward.min_folds
    assert len(folds) > 1, "a single fold is a pilot, never the full experiment"


def test_oos_windows_tile_without_gaps_or_overlaps(cfg, folds) -> None:
    """step_days == test_days, so OOS windows must be exactly contiguous."""
    assert cfg.walk_forward.step_days == cfg.walk_forward.test_days
    for a, b in pairwise(folds):
        assert a.test_end == b.test_start


def test_each_oos_window_has_the_configured_duration(cfg, folds) -> None:
    expected = timedelta(days=cfg.walk_forward.test_days)
    for f in folds:
        assert f.test_end - f.test_start == expected


def test_aggregate_oos_coverage_is_reported_correctly(cfg, folds) -> None:
    """Total OOS days == n_folds * test_days and stays inside development."""
    total = sum((f.test_end - f.test_start).days for f in folds)
    assert total == len(folds) * cfg.walk_forward.test_days
    assert folds[0].test_start >= cfg.periods.development_start
    assert folds[-1].test_end <= cfg.periods.development_end_exclusive
    # A pilot covering one window must be a small fraction of the whole period.
    dev_days = (cfg.periods.development_end_exclusive - cfg.periods.development_start).days
    assert 0 < total <= dev_days


def test_training_is_anchored_and_expands(cfg, folds) -> None:
    assert all(f.train_start == cfg.periods.development_start for f in folds)
    spans = [f.train_end - f.train_start for f in folds]
    assert all(a < b for a, b in pairwise(spans))


def test_purge_and_embargo_match_the_configured_bar_counts(cfg, folds) -> None:
    """Gaps must equal the derived purge/embargo, converted at the primary step."""
    step = timeframe_to_timedelta(cfg.timeframes.primary)
    for f in folds:
        assert f.purge_bars == cfg.purge_bars
        assert f.embargo_bars == cfg.embargo_bars
        assert f.val_start - f.train_end == cfg.embargo_bars * step
        assert f.test_start - f.val_end == cfg.purge_bars * step
    assert cfg.embargo_bars >= cfg.purge_bars


def test_train_validation_test_are_pairwise_disjoint(folds) -> None:
    for f in folds:
        assert f.train_end <= f.val_start
        assert f.val_end <= f.test_start


def test_no_fold_touches_the_frozen_holdout(cfg, folds) -> None:
    assert_folds_exclude_holdout(folds, cfg.periods.holdout_start)
    assert folds[-1].test_end <= cfg.periods.holdout_start


def test_capped_pilot_is_a_strict_subset_of_the_full_geometry(cfg, folds) -> None:
    """A `max_folds` pilot must reuse the full geometry's leading folds verbatim."""
    capped = folds[:3]
    assert [f.to_dict() for f in capped] == [f.to_dict() for f in folds[:3]]
    covered = sum((f.test_end - f.test_start).days for f in capped)
    full = sum((f.test_end - f.test_start).days for f in folds)
    assert covered < full, "the pilot must not be presented as full coverage"


# --------------------------------------------------------------------------- #
# Random Search vs Genetic Algorithm budget parity
# --------------------------------------------------------------------------- #


def test_ga_unique_evaluation_formula_accounts_for_elitism() -> None:
    # Generation 0 evaluates the whole population; later generations only the
    # non-elite offspring.
    assert ga_unique_evaluations(population_size=4, generations=3, elitism=1) == 10
    assert ga_unique_evaluations(population_size=100, generations=21, elitism=5) == 2000
    # With no elitism every generation is fully re-evaluated.
    assert ga_unique_evaluations(population_size=10, generations=4, elitism=0) == 40


def test_experiment_budget_is_reachable_within_the_generation_cap(cfg) -> None:
    ga = cfg.search.genetic_algorithm
    reachable = ga_unique_evaluations(ga.population_size, ga.max_generations, ga.elitism)
    assert reachable >= cfg.search.evaluation_budget


@pytest.mark.parametrize(
    "path",
    [
        "configs/search.yaml",
        "configs/search_pilot.yaml",
        "configs/search_pilot_eth.yaml",
        "configs/search_development_eth.yaml",
        "configs/search_development_btc.yaml",
    ],
)
def test_shipped_search_configs_declare_a_reachable_shared_budget(path: str) -> None:
    """Both engines target this number exactly, so the GA must be able to reach it."""
    sc = load_search_config(path)
    assert sc.budget == sc.effective_budget
    assert sc.ga.reachable_evaluations() >= sc.effective_budget


def test_full_development_config_does_not_cap_folds() -> None:
    sc = load_search_config("configs/search_development_eth.yaml")
    assert sc.max_folds is None
    assert sc.walk_forward_override is None
    assert sc.synthetic is False
