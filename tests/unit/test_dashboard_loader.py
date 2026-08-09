"""Unit tests for the read-only Research Dashboard loader and transforms.

These tests build a minimal on-disk artifact directory mirroring the schema
produced by ``perp_lab.search.runner.run_search`` and verify that the
Streamlit-free loader parses it, classifies the run kind, and produces the
principal dashboard tables. They also verify graceful handling of missing or
incomplete artifacts.
"""

from __future__ import annotations

import json
from itertools import pairwise
from pathlib import Path

import polars as pl
import pytest

from perp_lab.dashboard import loader


def _write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj), encoding="utf-8")


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    """A complete synthetic comparison run directory."""
    d = tmp_path / "runs" / "search_momentum_20260101T000000Z_abc123"
    d.mkdir(parents=True)

    summary = {
        "run_kind": "search_comparison",
        "label": "development_pilot_EXPLORATORY_not_holdout",
        "family": "momentum",
        "algorithm": "comparison",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "seed": 42,
        "budget": 12,
        "space_version": "1.0.0",
        "n_folds": 3,
        "fair_budget": "budget caps UNIQUE objective evaluations",
        "comparison_metric": "aggregate OOS test sharpe",
        "best_out_of_sample_method": "genetic_algorithm",
        "warning": "EXPLORATORY RESULT: development folds only.",
        "methods": {
            "random_search": {
                "counters": {
                    "proposed": 12,
                    "invalid": 0,
                    "duplicate": 0,
                    "cached": 0,
                    "evaluated": 12,
                },
                "n_unique_candidates": 12,
                "n_feasible": 11,
                "best_fitness": -0.24,
                "best_candidate_id": "momentum-aaa",
                "aggregate_test": {
                    "n_fold_winners": 3,
                    "mean_test_sharpe": -1.59,
                    "mean_test_total_return": -0.13,
                    "mean_test_max_drawdown": -0.27,
                    "mean_test_n_trades": 31.6,
                    "mean_test_ann_return": -0.38,
                },
                "diversity": None,
            },
            "genetic_algorithm": {
                "counters": {
                    "proposed": 10,
                    "invalid": 0,
                    "duplicate": 0,
                    "cached": 0,
                    "evaluated": 10,
                },
                "n_unique_candidates": 10,
                "n_feasible": 8,
                "best_fitness": 0.41,
                "best_candidate_id": "momentum-bbb",
                "aggregate_test": {
                    "n_fold_winners": 3,
                    "mean_test_sharpe": -0.55,
                    "mean_test_total_return": -0.04,
                    "mean_test_max_drawdown": -0.20,
                    "mean_test_n_trades": 26.0,
                    "mean_test_ann_return": -0.10,
                },
                "diversity": [
                    {"generation": 0, "param_diversity": 0.64, "unique_ratio": 1.0},
                    {"generation": 1, "param_diversity": 0.42, "unique_ratio": 1.0},
                ],
            },
        },
    }
    _write_json(d / "comparison_summary.json", summary)
    _write_json(d / "search_config.json", {"family": "momentum", "synthetic": False, "seed": 42})
    _write_json(d / "objective.json", {"weights": {"sharpe": 1.0}, "constraints": {}})
    _write_json(d / "environment.json", {"python_version": "3.12.3"})
    _write_json(
        d / "dataset_manifests.json",
        {"btc_klines_1h": {"sha256": "deadbeef", "row_count": 52608}},
    )
    _write_json(
        d / "feature_manifest.json", {"symbol": "BTCUSDT", "timeframe": "1h", "n_features": 9}
    )
    _write_json(
        d / "folds.json",
        {
            "regime_inputs": ["rvol_96"],
            "folds": [
                {
                    "index": 0,
                    "train_start": "2020-01-01T00:00:00+00:00",
                    "train_end": "2021-12-26T02:00:00+00:00",
                    "val_start": "2021-12-31T00:00:00+00:00",
                    "val_end": "2022-03-27T00:00:00+00:00",
                    "test_start": "2022-03-31T00:00:00+00:00",
                    "test_end": "2022-06-29T00:00:00+00:00",
                    "purge_bars": 96,
                    "embargo_bars": 118,
                }
            ],
        },
    )
    _write_json(d / "warnings.json", {"exploratory": "development folds only"})
    _write_json(
        d / "ga_diversity.json",
        {
            "generation_best": [
                {"generation": 0, "best_candidate_id": "momentum-bbb", "best_fitness": 0.1},
            ],
            "diversity": [
                {"generation": 0, "param_diversity": 0.64, "unique_ratio": 1.0},
                {"generation": 1, "param_diversity": 0.42, "unique_ratio": 1.0},
            ],
        },
    )
    _write_json(
        d / "ga_lineage.json",
        [{"generation": 1, "child": "momentum-ccc", "parents": ["momentum-bbb"]}],
    )
    _write_json(
        d / "random_search_convergence.json",
        {"best_fitness_after_each_eval": [-0.4, -0.4, -0.24, -0.24]},
    )
    _write_json(
        d / "random_search_fold_winners.json",
        [
            {
                "fold": 0,
                "winner": "momentum-aaa",
                "val_sharpe": 0.65,
                "test_metrics": {
                    "sharpe": -1.59,
                    "total_return": -0.30,
                    "max_drawdown": -0.53,
                    "n_trades": 44.0,
                    "ann_return": -0.77,
                },
                "params": {"fast": 6, "slow": 168},
            }
        ],
    )
    _write_json(d / "random_search_failed_candidates.json", [])
    _write_json(d / "genetic_algorithm_failed_candidates.json", [])

    pl.DataFrame(
        {
            "candidate_id": ["momentum-aaa", "momentum-ddd"],
            "family": ["momentum", "momentum"],
            "status": ["evaluated", "evaluated"],
            "fitness": [-0.24, -1.13],
            "params_json": ['{"fast":6}', '{"fast":48}'],
        }
    ).write_parquet(d / "random_search_candidates.parquet")
    pl.DataFrame(
        {
            "candidate_id": ["momentum-bbb"],
            "family": ["momentum"],
            "status": ["evaluated"],
            "fitness": [0.41],
            "params_json": ['{"fast":12}'],
        }
    ).write_parquet(d / "genetic_algorithm_candidates.parquet")
    pl.DataFrame(
        {
            "open_time": ["2022-03-31T00:00:00", "2022-03-31T01:00:00"],
            "equity": [1.0, 1.01],
            "drawdown": [0.0, -0.01],
        }
    ).write_parquet(d / "random_search_fold0_test_equity.parquet")
    pl.DataFrame(
        {"trade_id": [1], "net_return": [0.01], "funding": [-0.001], "cost": [0.0002]}
    ).write_parquet(d / "random_search_fold0_test_trades.parquet")
    (d / "comparison_report.md").write_text("# report", encoding="utf-8")
    return d


def test_discover_runs_finds_and_classifies(run_dir: Path) -> None:
    runs = loader.discover_runs(run_dir.parent)
    assert len(runs) == 1
    r = runs[0]
    assert r.family == "momentum"
    assert r.budget == 12
    assert r.n_folds == 3
    assert r.best_method == "genetic_algorithm"
    assert r.kind == loader.KIND_DEVELOPMENT


def test_discover_runs_missing_dir_returns_empty(tmp_path: Path) -> None:
    assert loader.discover_runs(tmp_path / "does_not_exist") == []


def test_classify_run_kind_variants() -> None:
    assert (
        loader.classify_run_kind({"label": "smoke"}, {"synthetic": True}) == loader.KIND_SYNTHETIC
    )
    assert loader.classify_run_kind({"label": "dev pilot"}, {"synthetic": False}) == (
        loader.KIND_DEVELOPMENT
    )
    assert loader.classify_run_kind({"label": "final holdout run"}, None) == loader.KIND_HOLDOUT
    assert loader.classify_run_kind(None, None) == loader.KIND_UNKNOWN


def test_comparison_table(run_dir: Path) -> None:
    art = loader.load_run(run_dir)
    df = loader.comparison_table(art.summary)
    assert set(df["method"]) == {"random_search", "genetic_algorithm"}
    ga = df.filter(pl.col("method") == "genetic_algorithm")
    assert ga["mean_test_sharpe"][0] == pytest.approx(-0.55)
    assert ga["feasible"][0] == 8


def test_fair_budget_report_ok(run_dir: Path) -> None:
    art = loader.load_run(run_dir)
    fb = loader.fair_budget_report(art.summary)
    assert fb["ok"] is True
    assert fb["budget"] == 12
    rows = fb["rows"]
    assert bool(rows["within_budget"].all())


def test_fair_budget_report_detects_violation() -> None:
    summary = {
        "budget": 5,
        "fair_budget": "x",
        "methods": {
            "random_search": {"counters": {"evaluated": 8}, "n_unique_candidates": 8},
        },
    }
    fb = loader.fair_budget_report(summary)
    assert fb["ok"] is False


def test_convergence_frame_reads_a_legacy_single_trace(run_dir: Path) -> None:
    """Pre-ADR-0012 runs stored one trace; they must still render, tagged as fold 0."""
    cf = loader.convergence_frame(run_dir, "random_search")
    assert cf.shape == (4, 3)
    assert cf["fold"].to_list() == [0, 0, 0, 0]
    assert cf["evaluation"].to_list() == [1, 2, 3, 4]
    # Best fitness must be monotonically non-decreasing.
    vals = cf["best_fitness"].to_list()
    assert all(b >= a for a, b in pairwise(vals))


def test_convergence_frame_keeps_folds_separate(tmp_path: Path) -> None:
    """Each outer fold is its own search, so its trace is its own series.

    Concatenating them would splice fitness values measured on different
    validation windows into a curve that describes no single search.
    """
    d = tmp_path / "run_per_fold"
    d.mkdir()
    _write_json(
        d / "random_search_convergence.json",
        {
            "protocol": loader.CURRENT_SEARCH_PROTOCOL,
            "per_fold": {"0": [-0.5, -0.2], "1": [-0.9, -0.9, -0.1]},
        },
    )
    cf = loader.convergence_frame(d, "random_search")
    assert cf["fold"].to_list() == [0, 0, 1, 1, 1]
    assert cf["evaluation"].to_list() == [1, 2, 1, 2, 3]
    assert loader.convergence_folds(d, "random_search") == [0, 1]

    only_one = loader.convergence_frame(d, "random_search", fold=1)
    assert only_one["fold"].to_list() == [1, 1, 1]


def test_convergence_frame_missing_returns_empty(run_dir: Path) -> None:
    assert loader.convergence_frame(run_dir, "genetic_algorithm").is_empty()


def test_diversity_and_generation_best(run_dir: Path) -> None:
    art = loader.load_run(run_dir)
    div = loader.diversity_frame(art)
    assert div.shape == (2, 3)
    gb = loader.generation_best_frame(art)
    assert gb.height == 1


def test_fold_winners_frame(run_dir: Path) -> None:
    df = loader.fold_winners_frame(run_dir, "random_search")
    assert df.height == 1
    assert df["test_sharpe"][0] == pytest.approx(-1.59)
    assert df["winner"][0] == "momentum-aaa"


def test_folds_frame(run_dir: Path) -> None:
    art = loader.load_run(run_dir)
    df = loader.folds_frame(art)
    assert df.height == 1
    assert df["purge_bars"][0] == 96
    assert df["embargo_bars"][0] == 118


def test_candidate_ranking_sorted(run_dir: Path) -> None:
    ranked = loader.candidate_ranking(run_dir, "random_search")
    assert ranked["fitness"].to_list() == sorted(ranked["fitness"].to_list(), reverse=True)


def test_equity_and_trades_frames(run_dir: Path) -> None:
    eq = loader.equity_frame(run_dir, "random_search", 0)
    assert "equity" in eq.columns and eq.height == 2
    tr = loader.trades_frame(run_dir, "random_search", 0)
    assert tr.height == 1


def test_dataset_manifest_frame(run_dir: Path) -> None:
    art = loader.load_run(run_dir)
    df = loader.dataset_manifest_frame(art)
    assert df["row_count"][0] == 52608


def test_available_methods(run_dir: Path) -> None:
    art = loader.load_run(run_dir)
    assert set(art.available_methods) == {"random_search", "genetic_algorithm"}


def test_load_run_tolerates_missing_artifacts(tmp_path: Path) -> None:
    empty = tmp_path / "empty_run"
    empty.mkdir()
    art = loader.load_run(empty)
    assert art.summary is None
    assert loader.comparison_table(art.summary).is_empty()
    assert loader.folds_frame(art).is_empty()
    assert loader.convergence_frame(empty, "random_search").is_empty()
    assert art.available_methods == []
    assert loader.warning_messages(art) == []


def test_warning_messages(run_dir: Path) -> None:
    art = loader.load_run(run_dir)
    msgs = loader.warning_messages(art)
    assert any("development" in m for m in msgs)
