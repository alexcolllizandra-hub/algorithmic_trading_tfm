"""Baselines, temporal bootstrap and cost stress across a whole multi-seed study.

Each (symbol, seed, engine) run is analysed on **its own** concatenated
out-of-sample series. The ten seeds are never pooled into one long series: doing
so would replay the same eighteen months of price history ten times and shrink
every bootstrap interval by roughly sqrt(10) while adding no market information.

What the study level *does* aggregate is counts -- how many seeds ended positive,
how many beat buy-and-hold, how many still beat zero once costs are doubled. A
strategy that only works for three seeds out of ten is not a strategy.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from perp_lab.evaluation.baselines import strategy_versus_baselines
from perp_lab.evaluation.robustness import block_bootstrap_ci, stress_costs

ENGINES = ("random_search", "genetic_algorithm")

# The always-long baseline IS buy-and-hold, paying the run's realised costs.
BUY_AND_HOLD = "always_long"

# One day, one week and one month of hourly bars. Reporting several block sizes
# shows whether the interval depends on the assumed dependence horizon.
BLOCK_SIZES = (24, 168, 720)


def _fold_index(path: Path) -> int:
    match = re.search(r"fold(\d+)", path.name)
    return int(match.group(1)) if match else -1


def load_oos_ledger(run_dir: str | Path, method: str) -> pl.DataFrame:
    """Concatenate one run's per-fold out-of-sample ledgers in fold order.

    Sorting is numeric, not lexicographic: ``fold10`` must not land between
    ``fold1`` and ``fold2``, which would silently scramble the chronology of the
    concatenated out-of-sample evidence.
    """
    run_dir = Path(run_dir)
    paths = sorted(run_dir.glob(f"{method}_fold*_test_equity.parquet"), key=_fold_index)
    if not paths:
        raise FileNotFoundError(f"No {method} OOS fold ledgers under {run_dir}")
    ledger = pl.concat([pl.read_parquet(p) for p in paths], how="vertical_relaxed")
    times = ledger["open_time"].to_list()
    if times != sorted(times):
        raise ValueError(
            f"Concatenated OOS ledger for {method} in {run_dir} is not chronological; "
            "refusing to analyse out-of-order out-of-sample evidence."
        )
    return ledger


def _sharpe(x: np.ndarray) -> float:
    sd = float(x.std(ddof=1)) if x.size > 1 else 0.0
    return float(x.mean() / sd) if sd > 0 else 0.0


def analyse_run(
    run_dir: str | Path,
    method: str,
    *,
    timeframe: str = "1h",
    seed: int = 42,
    resamples: int = 500,
    days_per_year: int = 365,
) -> dict[str, Any]:
    """Baselines, cost stress and a temporal bootstrap for ONE run and engine."""
    ledger = load_oos_ledger(run_dir, method)
    net = ledger["net_return"].cast(pl.Float64).to_numpy().astype(float)

    comparison = strategy_versus_baselines(
        ledger, timeframe=timeframe, seed=seed, days_per_year=days_per_year
    )
    strategy = comparison["strategy"]
    # Buy-and-hold is the always-long baseline, charged the run's own cost rate
    # and funding so it is not given an artificially cheap execution.
    buy_hold = comparison["baselines"].get(BUY_AND_HOLD)
    if buy_hold is None:
        raise KeyError(
            f"Baseline {BUY_AND_HOLD!r} missing from the comparison; available: "
            f"{sorted(comparison['baselines'])}"
        )

    doubled = stress_costs(
        ledger,
        timeframe=timeframe,
        fee_multiplier=2.0,
        slippage_multiplier=2.0,
        days_per_year=days_per_year,
    )

    bootstrap = {
        f"block_{b}": block_bootstrap_ci(
            net, _sharpe, block_size=b, n_resamples=resamples, seed=seed
        )
        for b in BLOCK_SIZES
    }

    return {
        "run_dir": str(run_dir),
        "method": method,
        "n_bars": int(ledger.height),
        "oos_start": str(ledger["open_time"].min()),
        "oos_end": str(ledger["open_time"].max()),
        "strategy": strategy,
        "buy_and_hold": buy_hold,
        "cost_stress_2x": doubled.to_dict(),
        "bootstrap_sharpe": bootstrap,
        "tests": {
            "positive_total_return": bool(strategy.get("total_return", 0.0) > 0),
            "beats_buy_and_hold": bool(
                strategy.get("total_return", float("-inf"))
                > buy_hold.get("total_return", float("inf"))
            ),
            "survives_double_costs": bool(doubled.metrics.get("total_return", 0.0) > 0),
            "bootstrap_sharpe_ci_excludes_zero": bool(
                bootstrap["block_168"].get("ci_low", -1.0) > 0
            ),
        },
    }


def analyse_study_robustness(
    units: dict[str, dict[str, Any]],
    *,
    timeframe: str = "1h",
    resamples: int = 500,
    days_per_year: int = 365,
) -> dict[str, Any]:
    """Per-run robustness for every unit, plus counts across seeds.

    Each unit's bootstrap uses its own out-of-sample series only. The aggregate is
    a tally of how many seeds pass each test, which is the honest way to summarise
    repeated runs on one price history.
    """
    per_run: dict[str, dict[str, Any]] = {}
    for key, unit in units.items():
        run_dir = unit.get("run_dir")
        if not run_dir or not Path(run_dir).exists():
            continue
        for method in ENGINES:
            try:
                per_run[f"{key}|{method}"] = analyse_run(
                    run_dir,
                    method,
                    timeframe=timeframe,
                    seed=int(unit["seed"]),
                    resamples=resamples,
                    days_per_year=days_per_year,
                )
                per_run[f"{key}|{method}"].update({"symbol": unit["symbol"], "seed": unit["seed"]})
            except (FileNotFoundError, ValueError):
                continue

    tally: dict[str, dict[str, Any]] = {}
    for entry in per_run.values():
        group = f"{entry['symbol']}|{entry['method']}"
        bucket = tally.setdefault(
            group,
            {
                "n_seeds": 0,
                "n_positive": 0,
                "n_beat_buy_and_hold": 0,
                "n_survive_double_costs": 0,
                "n_bootstrap_ci_excludes_zero": 0,
                "total_returns": [],
                "buy_and_hold_returns": [],
            },
        )
        tests = entry["tests"]
        bucket["n_seeds"] += 1
        bucket["n_positive"] += int(tests["positive_total_return"])
        bucket["n_beat_buy_and_hold"] += int(tests["beats_buy_and_hold"])
        bucket["n_survive_double_costs"] += int(tests["survives_double_costs"])
        bucket["n_bootstrap_ci_excludes_zero"] += int(tests["bootstrap_sharpe_ci_excludes_zero"])
        bucket["total_returns"].append(float(entry["strategy"].get("total_return", float("nan"))))
        bucket["buy_and_hold_returns"].append(
            float(entry["buy_and_hold"].get("total_return", float("nan")))
        )

    for bucket in tally.values():
        returns = np.asarray(bucket.pop("total_returns"), dtype=float)
        bh = np.asarray(bucket.pop("buy_and_hold_returns"), dtype=float)
        returns = returns[np.isfinite(returns)]
        bh = bh[np.isfinite(bh)]
        bucket["median_total_return"] = float(np.median(returns)) if returns.size else None
        bucket["min_total_return"] = float(returns.min()) if returns.size else None
        bucket["max_total_return"] = float(returns.max()) if returns.size else None
        bucket["median_buy_and_hold_return"] = float(np.median(bh)) if bh.size else None

    return {
        "per_run": per_run,
        "by_symbol_and_engine": tally,
        "method_note": (
            "Every bootstrap interval is computed on a single run's own concatenated "
            "out-of-sample series. Seeds are never concatenated: that would replay one "
            "price history ten times and shrink the interval without adding evidence."
        ),
    }
