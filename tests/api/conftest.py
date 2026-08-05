"""Fixtures for API tests: a clearly-labelled SYNTHETIC fixture run + client.

The fixture run is explicitly labelled ``fixture_synthetic_...`` so it can never
be confused with a real development or holdout result. Tests use it to exercise
the read-only API without depending on real artifacts.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient


def _write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj), encoding="utf-8")


def _build_fixture_run(runs_dir: Path) -> str:
    run_id = "fixture_synthetic_momentum_20200101T000000Z_test01"
    d = runs_dir / run_id
    d.mkdir(parents=True)
    summary = {
        "run_kind": "search_comparison",
        "label": "fixture_synthetic_NOT_a_research_result",
        "family": "momentum",
        "algorithm": "comparison",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "seed": 7,
        "budget": 8,
        "space_version": "1.0.0",
        "n_folds": 2,
        "fair_budget": "budget caps UNIQUE objective evaluations",
        "comparison_metric": "aggregate OOS test sharpe",
        "best_out_of_sample_method": "genetic_algorithm",
        "warning": "EXPLORATORY fixture result.",
        "methods": {
            "random_search": {
                "counters": {
                    "proposed": 8,
                    "invalid": 0,
                    "duplicate": 0,
                    "cached": 0,
                    "evaluated": 8,
                },
                "n_unique_candidates": 8,
                "n_feasible": 6,
                "best_fitness": -0.1,
                "aggregate_test": {
                    "n_fold_winners": 2,
                    "mean_test_sharpe": -0.5,
                    "mean_test_total_return": -0.02,
                    "mean_test_max_drawdown": -0.2,
                    "mean_test_n_trades": 20.0,
                    "mean_test_ann_return": -0.05,
                },
                "diversity": None,
            },
            "genetic_algorithm": {
                "counters": {
                    "proposed": 7,
                    "invalid": 0,
                    "duplicate": 0,
                    "cached": 0,
                    "evaluated": 7,
                },
                "n_unique_candidates": 7,
                "n_feasible": 5,
                "best_fitness": 0.3,
                "aggregate_test": {
                    "n_fold_winners": 2,
                    "mean_test_sharpe": 0.2,
                    "mean_test_total_return": 0.03,
                    "mean_test_max_drawdown": -0.15,
                    "mean_test_n_trades": 18.0,
                    "mean_test_ann_return": 0.06,
                },
                "diversity": [{"generation": 0, "param_diversity": 0.5, "unique_ratio": 1.0}],
            },
        },
    }
    _write_json(d / "comparison_summary.json", summary)
    _write_json(
        d / "search_config.json",
        {"family": "momentum", "synthetic": True, "label": "fixture_synthetic"},
    )
    _write_json(d / "objective.json", {"weights": {"sharpe": 1.0}, "constraints": {}})
    _write_json(d / "environment.json", {"python_version": "3.12.3"})
    _write_json(d / "git_state.json", {"commit": "abc123", "dirty": True})
    _write_json(d / "dataset_manifests.json", {"synthetic": {"row_count": 1000, "sha256": None}})
    _write_json(
        d / "feature_manifest.json", {"symbol": "BTCUSDT", "timeframe": "1h", "n_features": 5}
    )
    _write_json(d / "search_space.json", {"family": "momentum", "params": []})
    _write_json(d / "warnings.json", {"exploratory": "EXPLORATORY fixture result."})
    _write_json(
        d / "folds.json",
        {
            "regime_inputs": ["rvol_96"],
            "folds": [
                {
                    "index": 0,
                    "train_start": "2020-01-01T00:00:00+00:00",
                    "train_end": "2020-02-01T00:00:00+00:00",
                    "val_start": "2020-02-02T00:00:00+00:00",
                    "val_end": "2020-02-10T00:00:00+00:00",
                    "test_start": "2020-02-11T00:00:00+00:00",
                    "test_end": "2020-02-20T00:00:00+00:00",
                    "purge_bars": 24,
                    "embargo_bars": 12,
                }
            ],
        },
    )
    _write_json(
        d / "ga_diversity.json",
        {
            "generation_best": [
                {"generation": 0, "best_candidate_id": "momentum-bbb", "best_fitness": 0.3}
            ],
            "diversity": [{"generation": 0, "param_diversity": 0.5, "unique_ratio": 1.0}],
        },
    )
    _write_json(
        d / "ga_lineage.json",
        [{"generation": 1, "child": "momentum-ccc", "parents": ["momentum-bbb"]}],
    )
    _write_json(
        d / "random_search_convergence.json", {"best_fitness_after_each_eval": [-0.2, -0.1, -0.1]}
    )
    _write_json(
        d / "genetic_algorithm_convergence.json", {"best_fitness_after_each_eval": [-0.1, 0.1, 0.3]}
    )
    for method, wid in (("random_search", "momentum-aaa"), ("genetic_algorithm", "momentum-bbb")):
        _write_json(
            d / f"{method}_fold_winners.json",
            [
                {
                    "fold": 0,
                    "winner": wid,
                    "val_sharpe": 0.5,
                    "test_metrics": {
                        "sharpe": 0.2,
                        "total_return": 0.03,
                        "max_drawdown": -0.15,
                        "n_trades": 18.0,
                        "ann_return": 0.06,
                    },
                    "params": {"fast": 6, "slow": 96},
                }
            ],
        )
        _write_json(d / f"{method}_failed_candidates.json", {"count": 0, "candidates": []})
        pl.DataFrame(
            {
                "candidate_id": [f"{method}-a", f"{method}-b"],
                "family": ["momentum", "momentum"],
                "status": ["evaluated", "evaluated"],
                "fitness": [0.3, -0.1],
                "params_json": ['{"fast":6,"slow":96}', '{"fast":12,"slow":48}'],
                "obj_mean_val_sharpe": [0.3, -0.1],
            }
        ).write_parquet(d / f"{method}_candidates.parquet")
    pl.DataFrame(
        {
            "open_time": ["2020-02-11T00:00:00", "2020-02-11T01:00:00"],
            "equity": [1.0, 1.02],
            "drawdown": [0.0, -0.01],
        }
    ).write_parquet(d / "genetic_algorithm_fold0_test_equity.parquet")
    pl.DataFrame(
        {
            "trade_id": [1],
            "entry_time": ["2020-02-11T00:00:00"],
            "exit_time": ["2020-02-11T05:00:00"],
            "n_bars": [5],
            "position": [1.0],
            "net_return": [0.02],
            "funding": [-0.001],
            "cost": [0.0002],
            "exit_reason": ["signal"],
        }
    ).write_parquet(d / "genetic_algorithm_fold0_test_trades.parquet")
    (d / "comparison_report.md").write_text("# fixture report", encoding="utf-8")
    return run_id


@pytest.fixture
def api_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[str, Path]]:
    from perp_lab.api.settings import get_settings

    artifact_root = tmp_path / "artifacts"
    runs_dir = artifact_root / "runs"
    runs_dir.mkdir(parents=True)
    run_id = _build_fixture_run(runs_dir)
    monkeypatch.setenv("PERP_LAB_ARTIFACT_ROOT", str(artifact_root))
    monkeypatch.setenv("PERP_LAB_RUNS_DIR", str(runs_dir))
    get_settings.cache_clear()
    yield run_id, runs_dir
    get_settings.cache_clear()


@pytest.fixture
def client(api_env: tuple[str, Path]) -> Iterator[TestClient]:
    from perp_lab.api.main import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def run_id(api_env: tuple[str, Path]) -> str:
    return api_env[0]
