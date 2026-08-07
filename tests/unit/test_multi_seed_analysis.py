"""Tests for the multi-seed statistical analysis.

The critical property is that seeds are NOT counted as independent out-of-sample
evidence. A test that only checked the arithmetic would miss the one mistake that
actually matters, so several tests here are about the size of the interval.
"""

from __future__ import annotations

import numpy as np
import pytest

from perp_lab.evaluation.multi_seed import (
    analyse_study,
    long_table,
    paired_rs_ga,
    per_seed_aggregate,
    seed_stability_report,
    variance_decomposition,
)


def _units(
    *,
    symbols: tuple[str, ...] = ("BTCUSDT",),
    n_seeds: int = 5,
    n_folds: int = 10,
    ga_shift: float = 0.0,
    fold_ga_spread: float = 0.0,
    seed_noise: float = 0.0,
    rng_seed: int = 0,
) -> dict[str, dict]:
    """Synthetic study payload with controllable fold and seed structure.

    ``fold_ga_spread`` gives the genetic algorithm an advantage that differs by
    fold but is identical across seeds -- the realistic case, and the one where
    counting seeds as independent observations does real damage.
    """
    rng = np.random.default_rng(rng_seed)
    fold_effect = {f: float(rng.normal(0.0, 0.5)) for f in range(n_folds)}
    fold_advantage = {f: float(rng.normal(0.0, fold_ga_spread)) for f in range(n_folds)}
    units: dict[str, dict] = {}
    for symbol in symbols:
        for s in range(n_seeds):
            winners = {}
            for engine in ("random_search", "genetic_algorithm"):
                is_ga = engine == "genetic_algorithm"
                shift = ga_shift if is_ga else 0.0
                rows = []
                for f in range(n_folds):
                    value = fold_effect[f] + shift + rng.normal(0.0, seed_noise)
                    if is_ga:
                        value += fold_advantage[f]
                    rows.append(
                        {
                            "fold": f,
                            "winner": f"cand-{engine}-{f}",
                            "val_sharpe": value + 0.1,
                            "test_metrics": {"sharpe": value, "total_return": value / 10},
                        }
                    )
                winners[engine] = rows
            units[f"{symbol}|seed={s}"] = {
                "symbol": symbol,
                "seed": s,
                "run_id": f"run-{symbol}-{s}",
                "fold_winners": winners,
                "engines": {},
            }
    return units


def test_long_table_flattens_every_symbol_seed_engine_fold() -> None:
    table = long_table(_units(symbols=("BTCUSDT", "ETHUSDT"), n_seeds=3, n_folds=4))
    assert table.height == 2 * 3 * 2 * 4
    assert set(table["engine"].unique().to_list()) == {"random_search", "genetic_algorithm"}


def test_long_table_handles_an_empty_study() -> None:
    table = long_table({})
    assert table.height == 0
    assert "test_sharpe" in table.columns


def test_paired_comparison_uses_folds_not_seed_cells_as_units() -> None:
    """The whole point: 10 seeds must not multiply the sample size by 10."""
    result = paired_rs_ga(long_table(_units(n_seeds=10, n_folds=15)))
    assert result["n_cells_symbol_seed_fold"] == 10 * 15
    assert result["n_independent_units_used"] == 15


def test_adding_seeds_never_grows_the_sample_size() -> None:
    """Seeds are repeated measurements; only the number of folds may count."""
    for n_seeds in (1, 2, 10, 20):
        result = paired_rs_ga(long_table(_units(n_seeds=n_seeds, n_folds=12, seed_noise=0.3)))
        assert result["n_independent_units_used"] == 12
        assert result["n_cells_symbol_seed_fold"] == 12 * n_seeds


def test_interval_is_far_wider_than_treating_every_cell_as_independent() -> None:
    """The naive analysis would divide the standard error by sqrt(n_seeds)."""
    units = _units(n_seeds=10, n_folds=12, fold_ga_spread=0.6, seed_noise=0.3)
    table = long_table(units)
    result = paired_rs_ga(table)

    wide = table.pivot(values="test_sharpe", index=["symbol", "seed", "fold"], on="engine")
    cell_diff = (wide["genetic_algorithm"] - wide["random_search"]).to_numpy()
    naive_se = float(np.std(cell_diff, ddof=1)) / np.sqrt(cell_diff.size)
    naive_width = 2 * 1.96 * naive_se

    actual_width = result["ci_high"] - result["ci_low"]
    assert actual_width > 2 * naive_width, (
        "the interval is close to the naive one, so seeds are leaking into the sample size"
    )


def test_no_difference_yields_a_no_evidence_verdict() -> None:
    result = paired_rs_ga(long_table(_units(n_seeds=6, n_folds=15, ga_shift=0.0, seed_noise=0.2)))
    assert not result["ci_excludes_zero"]
    assert "no evidence" in result["verdict"]


def test_a_large_consistent_advantage_is_detected() -> None:
    result = paired_rs_ga(long_table(_units(n_seeds=6, n_folds=15, ga_shift=1.0, seed_noise=0.05)))
    assert result["mean_difference_ga_minus_rs"] == pytest.approx(1.0, abs=0.1)
    assert result["ci_excludes_zero"]
    assert "genetic_algorithm" in result["verdict"]
    assert result["effect_size_cohens_dz"] > 0


def test_paired_comparison_requires_both_engines() -> None:
    units = _units(n_seeds=2, n_folds=3)
    for payload in units.values():
        payload["fold_winners"].pop("genetic_algorithm")
    assert "error" in paired_rs_ga(long_table(units))


def test_variance_decomposition_separates_seed_noise_from_fold_spread() -> None:
    quiet = variance_decomposition(long_table(_units(n_seeds=8, n_folds=12, seed_noise=0.01)))
    noisy = variance_decomposition(long_table(_units(n_seeds=8, n_folds=12, seed_noise=1.0)))
    quiet_sd = quiet["random_search"]["seed_variability"]["mean_sd_within_symbol_fold"]
    noisy_sd = noisy["random_search"]["seed_variability"]["mean_sd_within_symbol_fold"]
    assert noisy_sd > quiet_sd * 10
    # Fold-level spread comes from the market structure and is present in both.
    assert quiet["random_search"]["fold_level_mean"]["n_folds"] == 12


def test_seed_to_fold_ratio_flags_an_unstable_search() -> None:
    noisy = variance_decomposition(long_table(_units(n_seeds=8, n_folds=12, seed_noise=2.0)))
    assert noisy["seed_to_fold_sd_ratio"]["values"]["random_search"] > 1.0


def test_per_seed_aggregate_gives_one_row_per_run() -> None:
    agg = per_seed_aggregate(
        long_table(_units(symbols=("BTCUSDT", "ETHUSDT"), n_seeds=4, n_folds=6))
    )
    assert agg.height == 2 * 4 * 2
    assert set(agg["n_folds"].unique().to_list()) == {6}


def test_seed_stability_counts_positive_seeds() -> None:
    report = seed_stability_report(long_table(_units(n_seeds=10, n_folds=8, ga_shift=5.0)))
    ga = report["BTCUSDT|genetic_algorithm"]
    assert ga["n_seeds"] == 10
    assert ga["n_seeds_positive"] == 10
    assert ga["share_seeds_positive"] == 1.0


def test_full_analysis_always_carries_the_seed_caveat() -> None:
    analysis = analyse_study(_units(n_seeds=3, n_folds=5))
    assert "repeated measurements" in analysis["caveat"]
    assert "never be pooled across seeds" in analysis["caveat"]
    assert analysis["seeds"] == [0, 1, 2]
