"""Run the frozen volatility-forecasting annex (HAR vs LSTM).

Run with: ``uv run python scripts/run_volforecast_experiment.py``
(needs the optional ``dl`` extra: ``uv sync --extra dl``)

Spec: docs/methodology/volforecast_spec.md — frozen before any fit. Uses the
study's own expanding walk-forward folds, the gated development DataLake and
seeds {42, 43, 44} for the LSTM. Writes per-fold and concatenated-OOS results
to ``artifacts/volforecast/results.json`` plus the aligned OOS prediction
arrays to parquet for the figure builder.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl

from perp_lab.config import load_data_contract, load_experiment_config
from perp_lab.eda import DataLake
from perp_lab.eda.returns import add_log_returns
from perp_lab.validation.walk_forward import generate_walk_forward
from perp_lab.volforecast.data import build_vol_dataset, slice_by_time
from perp_lab.volforecast.metrics import diebold_mariano, oos_metrics
from perp_lab.volforecast.models import fit_har, fit_predict_lstm, predict_har, predict_naive

SEEDS = (42, 43, 44)
SYMBOLS = ("BTCUSDT", "ETHUSDT")
OUT = Path("artifacts/volforecast")


def run_symbol(symbol: str, lake: DataLake, folds) -> dict:
    bars = add_log_returns(lake.load_klines(symbol, "1h", partition="development").frame)
    dataset = build_vol_dataset(bars)

    oos: dict[str, list[np.ndarray]] = {"true": [], "naive": [], "har": []}
    oos_lstm: dict[int, list[np.ndarray]] = {seed: [] for seed in SEEDS}
    oos_times: list[np.ndarray] = []
    fold_rows = []

    for fold in folds:
        train = slice_by_time(
            dataset, np.datetime64(fold.train_start), np.datetime64(fold.train_end)
        )
        val = slice_by_time(dataset, np.datetime64(fold.val_start), np.datetime64(fold.val_end))
        test = slice_by_time(dataset, np.datetime64(fold.test_start), np.datetime64(fold.test_end))
        if test.sum() == 0 or train.sum() == 0 or val.sum() == 0:
            continue

        true = dataset.target_log_rv[test]
        naive = predict_naive(dataset, test)
        har_model = fit_har(dataset, train | val)
        har = predict_har(har_model, dataset, test)
        lstm_preds = {
            seed: fit_predict_lstm(dataset, train, val, test, seed=seed) for seed in SEEDS
        }

        oos["true"].append(true)
        oos["naive"].append(naive)
        oos["har"].append(har)
        for seed, pred in lstm_preds.items():
            oos_lstm[seed].append(pred)
        oos_times.append(dataset.times[test])

        row = {"fold": fold.index, "n_test": int(test.sum())}
        row["har"] = oos_metrics(har, true, naive)
        for seed, pred in lstm_preds.items():
            row[f"lstm_seed{seed}"] = oos_metrics(pred, true, naive)
        fold_rows.append(row)
        print(
            f"{symbol} fold {fold.index:2d}: n={int(test.sum()):4d} "
            f"HAR qlike={row['har']['qlike']:.4f} "
            f"LSTM42 qlike={row['lstm_seed42']['qlike']:.4f}",
            flush=True,
        )

    true = np.concatenate(oos["true"])
    naive = np.concatenate(oos["naive"])
    har = np.concatenate(oos["har"])
    lstm_by_seed = {seed: np.concatenate(chunks) for seed, chunks in oos_lstm.items()}
    lstm_mean = np.mean(np.stack(list(lstm_by_seed.values())), axis=0)

    summary = {
        "n_oos": int(true.size),
        "n_folds": len(fold_rows),
        "naive": oos_metrics(naive, true, naive),
        "har": oos_metrics(har, true, naive),
        "lstm_mean_of_seeds": oos_metrics(lstm_mean, true, naive),
        "lstm_per_seed": {
            str(seed): oos_metrics(pred, true, naive) for seed, pred in lstm_by_seed.items()
        },
        "dm_har_vs_lstm_mean": diebold_mariano(har, lstm_mean, true),
        "dm_har_vs_lstm_per_seed": {
            str(seed): diebold_mariano(har, pred, true) for seed, pred in lstm_by_seed.items()
        },
        "folds": fold_rows,
    }

    frame = pl.DataFrame(
        {
            "open_time": np.concatenate(oos_times),
            "true_log_rv": true,
            "naive": naive,
            "har": har,
            **{f"lstm_seed{seed}": pred for seed, pred in lstm_by_seed.items()},
        }
    )
    OUT.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(OUT / f"oos_predictions_{symbol}.parquet")
    return summary


def main() -> int:
    contract = load_data_contract()
    exp = load_experiment_config()
    lake = DataLake(contract)
    folds = generate_walk_forward(exp)
    print(f"{len(folds)} walk-forward folds")

    results = {"spec": "docs/methodology/volforecast_spec.md", "seeds": list(SEEDS)}
    for symbol in SYMBOLS:
        results[symbol] = run_symbol(symbol, lake, folds)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(OUT / "results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
