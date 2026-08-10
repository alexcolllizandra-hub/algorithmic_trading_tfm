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
from perp_lab.evaluation.robustness import (
    block_bootstrap_ci,
    drop_best_trades,
    regime_conditional_metrics,
    stress_costs,
    trade_return_bootstrap,
)

ENGINES = ("random_search", "genetic_algorithm")

# The always-long baseline IS buy-and-hold, paying the run's realised costs.
BUY_AND_HOLD = "always_long"

# One day, one week and one month of hourly bars. Reporting several block sizes
# shows whether the interval depends on the assumed dependence horizon.
BLOCK_SIZES = (24, 168, 720)

# Gate R3 promotion contract (phase_gates.md). Random Search is the primary
# engine because it is the declared search baseline; GA is reported in parallel.
R3_PRIMARY_ENGINE = "random_search"
R3_DROP_TOP_K = 5
R3_MIN_OOS_TRADES = 5

PROMOTION_TESTS = (
    "positive_total_return",
    "bootstrap_sharpe_ci_excludes_zero",
    "survives_double_costs",
    "beats_buy_and_hold",
    "survives_drop_top_trades",
    "not_confined_to_one_fold",
)

REJECTION_TESTS = (
    "zero_seeds_positive",
    "no_bootstrap_ci_excludes_zero",
    "zero_seeds_survive_double_costs",
    "depends_on_few_trades",
    "confined_to_one_fold",
)


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


def load_oos_trades(run_dir: str | Path, method: str) -> pl.DataFrame:
    """Concatenate one run's per-fold out-of-sample trade tables in fold order."""
    run_dir = Path(run_dir)
    paths = sorted(run_dir.glob(f"{method}_fold*_test_trades.parquet"), key=_fold_index)
    if not paths:
        return pl.DataFrame()
    return pl.concat([pl.read_parquet(p) for p in paths], how="vertical_relaxed")


def per_fold_total_returns(run_dir: str | Path, method: str) -> list[tuple[int, float]]:
    """Compound total return inside each outer fold's test window."""
    run_dir = Path(run_dir)
    paths = sorted(run_dir.glob(f"{method}_fold*_test_equity.parquet"), key=_fold_index)
    out: list[tuple[int, float]] = []
    for path in paths:
        net = pl.read_parquet(path)["net_return"].cast(pl.Float64).to_numpy().astype(float)
        total = float(np.prod(1.0 + net) - 1.0) if net.size else 0.0
        out.append((_fold_index(path), total))
    return out


def analyse_trade_concentration(
    trades: pl.DataFrame,
    *,
    drop_top_k: int = R3_DROP_TOP_K,
    min_trades: int = R3_MIN_OOS_TRADES,
) -> dict[str, Any]:
    """Trade-count and drop-top-k checks for Gate R3."""
    if trades.height == 0 or "net_return" not in trades.columns:
        return {
            "n_trades": 0,
            "min_trades_required": min_trades,
            "depends_on_few_trades": True,
            "drop_top_k": drop_top_k,
            "total_return_without_best": None,
            "survives_drop_top_trades": False,
        }

    trade_returns = trades["net_return"].cast(pl.Float64).to_numpy().astype(float)
    trade_returns = trade_returns[np.isfinite(trade_returns)]
    n_trades = int(trade_returns.size)
    dropped = drop_best_trades(trade_returns, k=drop_top_k)
    without_best = dropped.get("total_return_without_best")
    survives = bool(without_best is not None and without_best > 0.0)
    return {
        "n_trades": n_trades,
        "min_trades_required": min_trades,
        "depends_on_few_trades": n_trades < min_trades,
        "drop_top_k": drop_top_k,
        "total_return_all": dropped.get("total_return_all"),
        "total_return_without_best": without_best,
        "survives_drop_top_trades": survives if n_trades >= min_trades else False,
    }


def analyse_fold_locality(per_fold: list[tuple[int, float]]) -> dict[str, Any]:
    """Whether the aggregate OOS result rests on a single outer fold."""
    if not per_fold:
        return {
            "n_folds": 0,
            "n_folds_positive": 0,
            "aggregate_return": 0.0,
            "total_return_without_best_fold": None,
            "confined_to_one_fold": False,
        }

    returns = np.asarray([value for _, value in per_fold], dtype=float)
    aggregate = float(np.prod(1.0 + returns) - 1.0)
    n_positive = int(np.sum(returns > 0.0))

    without_best: float | None = None
    if returns.size > 1:
        best = int(np.argmax(returns))
        mask = np.ones(returns.size, dtype=bool)
        mask[best] = False
        without_best = float(np.prod(1.0 + returns[mask]) - 1.0)

    confined = bool(
        aggregate > 0.0 and (n_positive <= 1 or (without_best is not None and without_best <= 0.0))
    )
    return {
        "n_folds": int(returns.size),
        "n_folds_positive": n_positive,
        "aggregate_return": aggregate,
        "total_return_without_best_fold": without_best,
        "confined_to_one_fold": confined,
    }


def _majority_required(n_seeds: int) -> int:
    return n_seeds // 2 + 1


def _assert_engines_share_coverage(per_run: dict[str, dict[str, Any]]) -> None:
    """Both engines of a unit must have been scored on exactly the same bars.

    If they were not, every paired difference mixes an algorithmic effect with a
    different market window, and the baselines are not the same baselines. This
    has to abort rather than warn: an unnoticed mismatch invalidates the whole
    comparison.
    """
    by_unit: dict[str, dict[str, str]] = {}
    for full_key, entry in per_run.items():
        unit, _, method = full_key.rpartition("|")
        by_unit.setdefault(unit, {})[method] = entry["coverage_id"]

    mismatched = {
        unit: methods for unit, methods in by_unit.items() if len(set(methods.values())) > 1
    }
    if mismatched:
        detail = "; ".join(f"{unit}: {methods}" for unit, methods in sorted(mismatched.items())[:5])
        raise ValueError(
            "Engines were scored on different out-of-sample bars, so their results "
            f"are not comparable ({len(mismatched)} unit(s)). First few: {detail}"
        )


def _sharpe(x: np.ndarray) -> float:
    sd = float(x.std(ddof=1)) if x.size > 1 else 0.0
    return float(x.mean() / sd) if sd > 0 else 0.0


def analyse_run(
    run_dir: str | Path,
    method: str,
    *,
    timeframe: str = "1h",
    fee_bps_per_side: float,
    slippage_bps_per_side: float,
    seed: int = 42,
    resamples: int = 500,
    days_per_year: int = 365,
) -> dict[str, Any]:
    """Baselines, cost stress and a temporal bootstrap for ONE run and engine."""
    ledger = load_oos_ledger(run_dir, method)
    net = ledger["net_return"].cast(pl.Float64).to_numpy().astype(float)

    comparison = strategy_versus_baselines(
        ledger,
        timeframe=timeframe,
        fee_bps_per_side=fee_bps_per_side,
        slippage_bps_per_side=slippage_bps_per_side,
        seed=seed,
        days_per_year=days_per_year,
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

    trades = load_oos_trades(run_dir, method)
    trade_checks = analyse_trade_concentration(trades)
    fold_checks = analyse_fold_locality(per_fold_total_returns(run_dir, method))

    trade_returns = (
        trades["net_return"].cast(pl.Float64).to_numpy().astype(float)
        if trades.height and "net_return" in trades.columns
        else np.array([], dtype=float)
    )
    trade_returns = trade_returns[np.isfinite(trade_returns)]
    extended = {
        "regime_conditional": regime_conditional_metrics(
            ledger, timeframe=timeframe, days_per_year=days_per_year
        ),
        "trade_path_bootstrap": trade_return_bootstrap(
            trade_returns, n_resamples=resamples, seed=seed
        )
        if trade_returns.size
        else {},
    }

    return {
        "run_dir": str(run_dir),
        "method": method,
        "coverage_id": comparison["coverage_id"],
        "n_bars": int(ledger.height),
        "oos_start": str(ledger["open_time"].min()),
        "oos_end": str(ledger["open_time"].max()),
        "strategy": strategy,
        "buy_and_hold": buy_hold,
        "cost_stress_2x": doubled.to_dict(),
        "bootstrap_sharpe": bootstrap,
        "trade_concentration": trade_checks,
        "fold_locality": fold_checks,
        "extended_robustness": extended,
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
            "survives_drop_top_trades": bool(trade_checks["survives_drop_top_trades"]),
            "not_confined_to_one_fold": not bool(fold_checks["confined_to_one_fold"]),
            "min_oos_trades_met": not bool(trade_checks["depends_on_few_trades"]),
        },
    }


def evaluate_r3_promotion(
    payload: dict[str, Any],
    *,
    engine: str = R3_PRIMARY_ENGINE,
) -> dict[str, Any]:
    """Apply Gate R3 promotion/rejection criteria to a study robustness payload."""
    per_run = payload.get("per_run", {})
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for entry in per_run.values():
        if entry.get("method") != engine:
            continue
        by_symbol.setdefault(str(entry["symbol"]), []).append(entry)

    if not by_symbol:
        return {
            "engine": engine,
            "verdict": "INSUFFICIENT_DATA",
            "reason": f"no completed runs for engine {engine!r}",
        }

    symbol_reports: dict[str, Any] = {}
    failed_promotion: list[str] = []
    triggered_rejections: list[str] = []
    majority_required_by_symbol: dict[str, int] = {}

    for symbol in sorted(by_symbol):
        runs = by_symbol[symbol]
        n_seeds = len(runs)
        majority = _majority_required(n_seeds)
        majority_required_by_symbol[symbol] = majority

        counts = dict.fromkeys(PROMOTION_TESTS, 0)
        n_depends_on_few = 0
        n_confined = 0
        for entry in runs:
            tests = entry["tests"]
            for name in PROMOTION_TESTS:
                counts[name] += int(tests[name])
            n_depends_on_few += int(not tests["min_oos_trades_met"])
            n_confined += int(not tests["not_confined_to_one_fold"])

        promotion = {
            name: {
                "n_pass": counts[name],
                "required": majority,
                "pass": counts[name] >= majority,
            }
            for name in PROMOTION_TESTS
        }
        rejections = {
            "zero_seeds_positive": {
                "triggered": counts["positive_total_return"] == 0,
                "n_pass": counts["positive_total_return"],
            },
            "no_bootstrap_ci_excludes_zero": {
                "triggered": counts["bootstrap_sharpe_ci_excludes_zero"] == 0,
                "n_pass": counts["bootstrap_sharpe_ci_excludes_zero"],
            },
            "zero_seeds_survive_double_costs": {
                "triggered": counts["survives_double_costs"] == 0,
                "n_pass": counts["survives_double_costs"],
            },
            "depends_on_few_trades": {
                "triggered": n_depends_on_few > 0,
                "n_seeds_below_min_trades": n_depends_on_few,
                "min_trades_required": R3_MIN_OOS_TRADES,
            },
            "confined_to_one_fold": {
                "triggered": n_confined >= majority,
                "n_confined": n_confined,
                "required_not_confined": majority,
            },
        }

        symbol_reports[symbol] = {
            "n_seeds": n_seeds,
            "majority_required": majority,
            "promotion": promotion,
            "rejections": rejections,
        }

        for name, row in promotion.items():
            if not row["pass"]:
                failed_promotion.append(f"{symbol}: {name} ({row['n_pass']}/{row['required']})")
        for name, row in rejections.items():
            if row["triggered"]:
                triggered_rejections.append(f"{symbol}: {name}")

    all_symbols_pass = all(
        all(row["pass"] for row in symbol_reports[sym]["promotion"].values())
        for sym in symbol_reports
    )
    any_rejection = bool(triggered_rejections)

    if any_rejection:
        verdict = "REJECTED"
    elif all_symbols_pass:
        verdict = "PROMOTED"
    else:
        verdict = "REJECTED"

    return {
        "engine": engine,
        "primary_engine_note": (
            "Gate R3 uses random_search as the primary engine; genetic_algorithm "
            "is reported in parallel but does not decide family promotion."
        ),
        "majority_required_by_symbol": majority_required_by_symbol,
        "drop_top_k": R3_DROP_TOP_K,
        "min_oos_trades": R3_MIN_OOS_TRADES,
        "by_symbol": symbol_reports,
        "failed_promotion_criteria": failed_promotion,
        "triggered_rejections": triggered_rejections,
        "verdict": verdict,
    }


def analyse_study_robustness(
    units: dict[str, dict[str, Any]],
    *,
    timeframe: str = "1h",
    fee_bps_per_side: float,
    slippage_bps_per_side: float,
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
                    fee_bps_per_side=fee_bps_per_side,
                    slippage_bps_per_side=slippage_bps_per_side,
                    seed=int(unit["seed"]),
                    resamples=resamples,
                    days_per_year=days_per_year,
                )
                per_run[f"{key}|{method}"].update({"symbol": unit["symbol"], "seed": unit["seed"]})
            except (FileNotFoundError, ValueError):
                continue

    _assert_engines_share_coverage(per_run)

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
                "n_survives_drop_top_trades": 0,
                "n_not_confined_to_one_fold": 0,
                "n_min_oos_trades_met": 0,
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
        bucket["n_survives_drop_top_trades"] += int(tests["survives_drop_top_trades"])
        bucket["n_not_confined_to_one_fold"] += int(tests["not_confined_to_one_fold"])
        bucket["n_min_oos_trades_met"] += int(tests["min_oos_trades_met"])
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

    payload = {
        "per_run": per_run,
        "by_symbol_and_engine": tally,
        "method_note": (
            "Every bootstrap interval is computed on a single run's own concatenated "
            "out-of-sample series. Seeds are never concatenated: that would replay one "
            "price history ten times and shrink the interval without adding evidence."
        ),
    }
    payload["r3_promotion"] = evaluate_r3_promotion(payload)
    payload["r3_promotion_ga"] = evaluate_r3_promotion(payload, engine="genetic_algorithm")
    return payload
