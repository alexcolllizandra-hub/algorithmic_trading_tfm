"""End-to-end (offline, synthetic) test of the development pipeline slice."""

from __future__ import annotations

import json
from pathlib import Path

from perp_lab.config import Paths, load_data_contract, load_experiment_config
from perp_lab.experiments.pipeline import run_dev_pipeline, synthetic_klines


def test_synthetic_klines_deterministic_and_schema() -> None:
    a = synthetic_klines(50, seed=42)
    b = synthetic_klines(50, seed=42)
    assert a.equals(b)
    assert a.height == 50
    assert {"open", "high", "low", "close", "taker_buy_quote"}.issubset(a.columns)
    # OHLC consistency: high >= max(open, close), low <= min(open, close).
    assert (a["high"] >= a[["open", "close"]].max_horizontal()).all()
    assert (a["low"] <= a[["open", "close"]].min_horizontal()).all()


def test_dev_pipeline_runs_end_to_end_on_synthetic_data() -> None:
    contract = load_data_contract("configs/data_contract.yaml")
    experiment = load_experiment_config("configs/experiment.yaml")
    res = run_dev_pipeline(
        contract=contract,
        experiment=experiment,
        symbol="BTCUSDT",
        timeframe="1h",
        fast=24,
        slow=96,
        synthetic=True,
        synthetic_bars=500,
        write_artifacts=False,
    )
    assert res.synthetic is True
    assert res.n_rows == 500
    assert res.metrics["n_bars"] > 0
    assert "sharpe" in res.metrics


def test_dev_pipeline_deterministic_metrics() -> None:
    contract = load_data_contract("configs/data_contract.yaml")
    experiment = load_experiment_config("configs/experiment.yaml")
    kwargs = {
        "contract": contract,
        "experiment": experiment,
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "synthetic": True,
        "synthetic_bars": 400,
        "write_artifacts": False,
    }
    m1 = run_dev_pipeline(**kwargs).metrics  # type: ignore[arg-type]
    m2 = run_dev_pipeline(**kwargs).metrics  # type: ignore[arg-type]
    assert m1 == m2


def test_dev_pipeline_writes_run_contract(tmp_path: Path) -> None:
    contract = load_data_contract("configs/data_contract.yaml")
    experiment = load_experiment_config("configs/experiment.yaml")
    paths = Paths(artifacts_root=tmp_path)
    res = run_dev_pipeline(
        contract=contract,
        experiment=experiment,
        paths=paths,
        synthetic=True,
        synthetic_bars=300,
        write_artifacts=True,
        run_id="test_run_0001",
    )
    run_dir = tmp_path / "runs" / "test_run_0001"
    assert res.run_dir == run_dir
    for name in (
        "resolved_config.yaml",
        "dataset_manifests.json",
        "environment.json",
        "git_state.json",
        "metrics.json",
        "feature_metadata.json",
        "trades.parquet",
        "equity.parquet",
    ):
        assert (run_dir / name).exists(), f"missing artifact {name}"
    assert (run_dir / "figures").is_dir()
    assert (run_dir / "logs").is_dir()

    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["run_id"] == "test_run_0001"
    assert metrics["seed"] == experiment.random_seed
    assert "git_commit" in metrics
    assert metrics["execution"] == "next_bar_open"
