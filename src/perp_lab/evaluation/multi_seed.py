"""Statistical analysis of a multi-seed, multi-asset walk-forward study.

The central methodological point of this module is what counts as an independent
observation. A study of 2 assets x 10 seeds x 15 folds produces 300 numbers per
engine, but it does **not** contain 300 independent pieces of evidence:

* the ten seeds all run over the *same* price history, so they are repeated
  measurements of one experiment, not ten new out-of-sample periods;
* folds within an asset share overlapping training data and adjacent market
  regimes, so they are correlated too, though far less than seeds are.

Treating seeds as independent replicates would shrink every confidence interval
by roughly the square root of the number of seeds and manufacture significance
out of nothing. So the analysis collapses seeds first (their spread is reported
separately, as *search instability*) and uses the fold as the replication unit
for market variation.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import polars as pl

ENGINES = ("random_search", "genetic_algorithm")

_TEST_METRICS = ("sharpe", "total_return", "max_drawdown", "n_trades", "ann_return")


def long_table(units: dict[str, dict[str, Any]]) -> pl.DataFrame:
    """Flatten a study's per-unit summaries into one tidy per-fold table."""
    rows: list[dict[str, Any]] = []
    for payload in units.values():
        symbol = payload["symbol"]
        seed = payload["seed"]
        for engine, winners in payload.get("fold_winners", {}).items():
            for w in winners:
                metrics = w.get("test_metrics") or {}
                rows.append(
                    {
                        "symbol": symbol,
                        "seed": seed,
                        "engine": engine,
                        "fold": int(w["fold"]),
                        "winner": w.get("winner"),
                        "val_sharpe": w.get("val_sharpe"),
                        **{f"test_{k}": metrics.get(k) for k in _TEST_METRICS},
                    }
                )
    if not rows:
        return pl.DataFrame(
            schema={
                "symbol": pl.String,
                "seed": pl.Int64,
                "engine": pl.String,
                "fold": pl.Int64,
                "winner": pl.String,
                "val_sharpe": pl.Float64,
                **{f"test_{k}": pl.Float64 for k in _TEST_METRICS},
            }
        )
    return pl.DataFrame(rows).sort("symbol", "seed", "engine", "fold")


def _finite(values: Any) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    return arr[np.isfinite(arr)]


def _t_critical(df: int, alpha: float = 0.05) -> float:
    """Two-sided t critical value, falling back to the normal quantile."""
    try:
        from scipy import stats

        return float(stats.t.ppf(1 - alpha / 2, df))
    except ImportError:  # pragma: no cover - scipy is a hard dependency
        return 1.96


def per_seed_aggregate(table: pl.DataFrame, metric: str = "test_sharpe") -> pl.DataFrame:
    """One row per (symbol, seed, engine): the mean across that run's folds."""
    if table.height == 0:
        return table
    return (
        table.group_by("symbol", "seed", "engine")
        .agg(
            pl.col(metric).mean().alias("mean"),
            pl.col(metric).std().alias("std_across_folds"),
            pl.col(metric).count().alias("n_folds"),
            (pl.col(metric) > 0).sum().alias("n_folds_positive"),
        )
        .sort("symbol", "engine", "seed")
    )


def variance_decomposition(table: pl.DataFrame, metric: str = "test_sharpe") -> dict[str, Any]:
    """Separate seed-driven variation from fold-driven variation.

    Seed spread is computed *within* a (symbol, fold) cell, so it isolates the
    search algorithm's own instability on fixed data. Fold spread is computed
    within a (symbol, seed) run, so it isolates variation across market periods.
    They answer different questions and must not be pooled into a single "error
    bar".
    """
    out: dict[str, Any] = {}
    if table.height == 0:
        return out

    for engine in ENGINES:
        sub = table.filter(pl.col("engine") == engine)
        if sub.height == 0:
            continue

        # Spread across seeds, holding the market period fixed.
        by_cell = sub.group_by("symbol", "fold").agg(
            pl.col(metric).std().alias("sd"),
            pl.col(metric).mean().alias("mean"),
            pl.col(metric).count().alias("n"),
        )
        seed_sd = _finite(by_cell.filter(pl.col("n") > 1)["sd"].to_list())

        # Spread across folds, holding the seed fixed.
        by_run = sub.group_by("symbol", "seed").agg(
            pl.col(metric).std().alias("sd"), pl.col(metric).count().alias("n")
        )
        fold_sd = _finite(by_run.filter(pl.col("n") > 1)["sd"].to_list())

        # Fold-level means (seeds collapsed): the quantity market inference uses.
        fold_means = _finite(by_cell["mean"].to_list())

        out[engine] = {
            "metric": metric,
            "seed_variability": {
                "mean_sd_within_symbol_fold": float(seed_sd.mean()) if seed_sd.size else None,
                "max_sd_within_symbol_fold": float(seed_sd.max()) if seed_sd.size else None,
                "n_cells": int(seed_sd.size),
                "interpretation": (
                    "spread caused by the search's randomness on identical data; "
                    "it is instability of the method, not extra out-of-sample evidence"
                ),
            },
            "fold_variability": {
                "mean_sd_within_run": float(fold_sd.mean()) if fold_sd.size else None,
                "sd_of_fold_means": float(fold_sd.std(ddof=1)) if fold_sd.size > 1 else None,
                "n_runs": int(fold_sd.size),
                "interpretation": "spread across market periods within one run",
            },
            "fold_level_mean": {
                "mean": float(fold_means.mean()) if fold_means.size else None,
                "sd": float(fold_means.std(ddof=1)) if fold_means.size > 1 else None,
                "n_folds": int(fold_means.size),
            },
        }

    ratios = {}
    for engine, payload in out.items():
        seed_sd = payload["seed_variability"]["mean_sd_within_symbol_fold"]
        fold_sd = payload["fold_level_mean"]["sd"]
        if seed_sd and fold_sd:
            ratios[engine] = round(seed_sd / fold_sd, 4)
    if ratios:
        out["seed_to_fold_sd_ratio"] = {
            "values": ratios,
            "interpretation": (
                "a ratio near or above 1 means re-running the search with a different "
                "seed moves the result about as much as changing the market period, "
                "which makes any single-seed conclusion unreliable"
            ),
        }
    return out


def paired_rs_ga(table: pl.DataFrame, metric: str = "test_sharpe") -> dict[str, Any]:
    """Paired Random Search vs Genetic Algorithm comparison, correctly nested.

    Pairing is exact: both engines are compared on the same (symbol, seed, fold)
    cell, so market conditions and the fold's difficulty cancel out. Seeds are then
    averaged within each (symbol, fold), and inference is done across folds, whose
    count is the honest sample size.
    """
    if table.height == 0:
        return {}

    wide = table.pivot(values=metric, index=["symbol", "seed", "fold"], on="engine")
    if not all(engine in wide.columns for engine in ENGINES):
        return {"error": "both engines are required for a paired comparison"}
    wide = wide.drop_nulls(subset=list(ENGINES)).sort("symbol", "seed", "fold")
    if wide.height == 0:
        return {"error": "no (symbol, seed, fold) cell has a result from both engines"}

    wide = wide.with_columns(
        (pl.col("genetic_algorithm") - pl.col("random_search")).alias("difference")
    )

    cell_diffs = _finite(wide["difference"].to_list())

    # Collapse seeds inside each (symbol, fold), then treat folds as the units.
    by_fold = wide.group_by("symbol", "fold").agg(
        pl.col("difference").mean().alias("mean_difference"),
        pl.col("difference").std().alias("sd_across_seeds"),
        pl.col("difference").count().alias("n_seeds"),
    )
    fold_diffs = _finite(by_fold["mean_difference"].to_list())
    n_folds = int(fold_diffs.size)

    result: dict[str, Any] = {
        "metric": metric,
        "n_cells_symbol_seed_fold": int(cell_diffs.size),
        "n_independent_units_used": n_folds,
        "unit_of_inference": "symbol x fold (seeds averaged within each cell)",
        "why": (
            "the seeds share one price history, so counting them as independent "
            "observations would shrink the interval by ~sqrt(n_seeds) and invent "
            "significance that the data do not contain"
        ),
        "mean_difference_ga_minus_rs": float(fold_diffs.mean()) if n_folds else None,
        "median_difference_ga_minus_rs": float(np.median(fold_diffs)) if n_folds else None,
        "n_folds_favouring_ga": int((fold_diffs > 0).sum()),
        "n_folds_favouring_rs": int((fold_diffs < 0).sum()),
    }

    if n_folds > 1:
        sd = float(fold_diffs.std(ddof=1))
        mean = float(fold_diffs.mean())
        se = sd / math.sqrt(n_folds)
        crit = _t_critical(n_folds - 1)
        result.update(
            {
                "sd_of_fold_differences": sd,
                "standard_error": se,
                "ci_low": mean - crit * se,
                "ci_high": mean + crit * se,
                "ci_level": 0.95,
                # Cohen's dz for a paired design: mean difference in units of its
                # own standard deviation.
                "effect_size_cohens_dz": (mean / sd) if sd > 0 else None,
                "ci_excludes_zero": bool((mean - crit * se) * (mean + crit * se) > 0),
            }
        )
        result["verdict"] = _verdict(result)
    else:
        result["verdict"] = "insufficient folds for inference"

    result["per_symbol"] = {}
    for symbol in sorted(set(by_fold["symbol"].to_list())):
        vals = _finite(by_fold.filter(pl.col("symbol") == symbol)["mean_difference"].to_list())
        if vals.size == 0:
            continue
        entry: dict[str, Any] = {
            "n_folds": int(vals.size),
            "mean_difference": float(vals.mean()),
            "n_folds_favouring_ga": int((vals > 0).sum()),
        }
        if vals.size > 1:
            sd = float(vals.std(ddof=1))
            se = sd / math.sqrt(vals.size)
            crit = _t_critical(vals.size - 1)
            entry["ci_low"] = float(vals.mean()) - crit * se
            entry["ci_high"] = float(vals.mean()) + crit * se
        result["per_symbol"][symbol] = entry

    seed_sd = _finite(by_fold["sd_across_seeds"].to_list())
    result["seed_dispersion_of_the_difference"] = {
        "mean_sd_across_seeds_within_fold": float(seed_sd.mean()) if seed_sd.size else None,
        "interpretation": (
            "how much the RS-GA gap itself moves when only the seed changes; if this "
            "is comparable to the mean difference, the gap is noise"
        ),
    }
    return result


def _verdict(result: dict[str, Any]) -> str:
    """State only what the paired comparison actually supports."""
    if not result.get("ci_excludes_zero"):
        return (
            "no evidence of a difference between Random Search and the Genetic "
            "Algorithm: the 95% confidence interval for the paired difference "
            "includes zero"
        )
    direction = (
        "genetic_algorithm" if result["mean_difference_ga_minus_rs"] > 0 else "random_search"
    )
    return (
        f"{direction} is ahead on the paired fold-level comparison (interval excludes "
        "zero); this is development out-of-sample evidence only and does not "
        "establish holdout performance"
    )


def seed_stability_report(
    table: pl.DataFrame, metric: str = "test_sharpe"
) -> dict[str, dict[str, Any]]:
    """How many seeds produced a positive result, per symbol and engine."""
    out: dict[str, dict[str, Any]] = {}
    if table.height == 0:
        return out
    agg = per_seed_aggregate(table, metric)
    for symbol in sorted(set(agg["symbol"].to_list())):
        for engine in ENGINES:
            sub = agg.filter((pl.col("symbol") == symbol) & (pl.col("engine") == engine))
            values = _finite(sub["mean"].to_list())
            if values.size == 0:
                continue
            out[f"{symbol}|{engine}"] = {
                "n_seeds": int(values.size),
                "n_seeds_positive": int((values > 0).sum()),
                "share_seeds_positive": float((values > 0).mean()),
                "mean_across_seeds": float(values.mean()),
                "sd_across_seeds": float(values.std(ddof=1)) if values.size > 1 else None,
                "min": float(values.min()),
                "max": float(values.max()),
            }
    return out


def analyse_study(units: dict[str, dict[str, Any]], metric: str = "test_sharpe") -> dict[str, Any]:
    """Full analysis payload for one multi-seed study."""
    table = long_table(units)
    return {
        "metric": metric,
        "n_rows": table.height,
        "symbols": sorted(set(table["symbol"].to_list())) if table.height else [],
        "seeds": sorted(set(table["seed"].to_list())) if table.height else [],
        "seed_stability": seed_stability_report(table, metric),
        "variance_decomposition": variance_decomposition(table, metric),
        "paired_rs_vs_ga": paired_rs_ga(table, metric),
        "caveat": (
            "Seeds are repeated measurements on ONE price history. They quantify the "
            "search's instability, not additional out-of-sample evidence, and the "
            "concatenated out-of-sample series must never be pooled across seeds."
        ),
    }
