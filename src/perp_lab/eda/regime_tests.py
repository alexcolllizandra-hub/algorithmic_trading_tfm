"""Non-parametric comparison of a variable across market-regime groups.

Volatility regimes partition the development sample into ``low`` / ``medium`` /
``high`` states (see :mod:`perp_lab.eda.regimes`). To ask whether a quantity
(absolute return, high-low range, volume, funding, drawdown, ...) *differs*
across those states we use rank-based tests, which are robust to the heavy tails
documented in the EDA:

* **Kruskal-Wallis** tests the global null that the distribution is identical
  across all regimes;
* **Dunn's test** provides the pairwise post-hoc comparisons, tie-corrected and
  adjusted for multiple testing (Benjamini-Hochberg by default);
* the **effect size** is reported as epsilon-squared, ``H / (n - 1)`` in
  ``[0, 1]``;
* per-regime **medians** carry moving-block bootstrap confidence intervals.

These are descriptive, in-sample diagnostics on the development set. A small
p-value indicates a distributional difference between regimes, not causality and
not an exploitable trading edge.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
from scipy import stats
from statsmodels.stats.multitest import multipletests

from perp_lab.eda.bootstrap import bootstrap_ci, median_stat

DEFAULT_REGIMES: tuple[str, ...] = ("low", "medium", "high")


def _regime_groups(
    df: pl.DataFrame,
    value_col: str,
    group_col: str,
    groups: tuple[str, ...],
) -> list[tuple[str, np.ndarray]]:
    """Ordered ``(label, values)`` pairs for the requested, non-empty regimes."""
    out: list[tuple[str, np.ndarray]] = []
    for label in groups:
        sub = (
            df.filter(pl.col(group_col) == label)
            .select(pl.col(value_col))
            .drop_nulls()
            .to_series()
            .to_numpy()
        )
        sub = sub[np.isfinite(sub)]
        if sub.size > 0:
            out.append((label, sub))
    return out


def kruskal_regime(
    df: pl.DataFrame,
    value_col: str,
    *,
    group_col: str = "vol_regime",
    groups: tuple[str, ...] = DEFAULT_REGIMES,
) -> dict[str, float]:
    """Kruskal-Wallis test of ``value_col`` across regime groups.

    Returns the H statistic, p-value, group and sample counts, and the
    epsilon-squared effect size. Empty when fewer than two non-empty groups.
    """
    grouped = _regime_groups(df, value_col, group_col, groups)
    if len(grouped) < 2:
        return {}
    arrays = [g for _, g in grouped]
    res: Any = stats.kruskal(*arrays)
    n = int(sum(g.size for g in arrays))
    h = float(res.statistic)
    epsilon_sq = h / (n - 1) if n > 1 else float("nan")
    return {
        "H": h,
        "pvalue": float(res.pvalue),
        "n_groups": float(len(arrays)),
        "n": float(n),
        "epsilon_squared": float(epsilon_sq),
    }


def dunn_posthoc(
    df: pl.DataFrame,
    value_col: str,
    *,
    group_col: str = "vol_regime",
    groups: tuple[str, ...] = DEFAULT_REGIMES,
    adjust: str = "fdr_bh",
    alpha: float = 0.05,
) -> pl.DataFrame:
    """Tie-corrected Dunn post-hoc pairwise comparisons with p-value adjustment.

    For each regime pair the z-statistic compares mean ranks in the pooled
    ranking; two-sided p-values are corrected across all pairs with ``adjust``
    (any ``statsmodels.stats.multitest.multipletests`` method). Columns:
    ``group_a``, ``group_b``, ``n_a``, ``n_b``, ``z``, ``p_raw``, ``p_adj`` and
    ``reject`` (at ``alpha``).
    """
    schema = {
        "group_a": pl.Utf8,
        "group_b": pl.Utf8,
        "n_a": pl.Int64,
        "n_b": pl.Int64,
        "z": pl.Float64,
        "p_raw": pl.Float64,
        "p_adj": pl.Float64,
        "reject": pl.Boolean,
    }
    grouped = _regime_groups(df, value_col, group_col, groups)
    if len(grouped) < 2:
        return pl.DataFrame(schema=schema)

    labels = [lab for lab, _ in grouped]
    sizes = {lab: g.size for lab, g in grouped}
    pooled = np.concatenate([g for _, g in grouped])
    n = pooled.size
    ranks = stats.rankdata(pooled)

    mean_rank: dict[str, float] = {}
    offset = 0
    for lab, g in grouped:
        mean_rank[lab] = float(np.mean(ranks[offset : offset + g.size]))
        offset += g.size

    # Tie correction for the rank-sum variance.
    _, counts = np.unique(pooled, return_counts=True)
    ties = float(np.sum(counts**3 - counts))
    var_base = (n * (n + 1)) / 12.0 - ties / (12.0 * (n - 1)) if n > 1 else float("nan")

    rows: list[dict[str, object]] = []
    raw_p: list[float] = []
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            a, b = labels[i], labels[j]
            se = float(np.sqrt(var_base * (1.0 / sizes[a] + 1.0 / sizes[b])))
            z = (mean_rank[a] - mean_rank[b]) / se if se > 0 else float("nan")
            p = float(2.0 * stats.norm.sf(abs(z))) if np.isfinite(z) else float("nan")
            raw_p.append(p)
            rows.append(
                {
                    "group_a": a,
                    "group_b": b,
                    "n_a": int(sizes[a]),
                    "n_b": int(sizes[b]),
                    "z": float(z),
                    "p_raw": p,
                }
            )

    finite_mask = np.isfinite(np.asarray(raw_p, dtype=float))
    p_adj = np.full(len(raw_p), float("nan"))
    reject = np.zeros(len(raw_p), dtype=bool)
    if finite_mask.any():
        rej, adj, _, _ = multipletests(
            [raw_p[k] for k in range(len(raw_p)) if finite_mask[k]],
            alpha=alpha,
            method=adjust,
        )
        it = iter(zip(rej, adj, strict=True))
        for k in range(len(raw_p)):
            if finite_mask[k]:
                r, pa = next(it)
                p_adj[k] = float(pa)
                reject[k] = bool(r)

    for k, row in enumerate(rows):
        row["p_adj"] = float(p_adj[k])
        row["reject"] = bool(reject[k])
    return pl.DataFrame(rows, schema=schema)


def regime_medians_ci(
    df: pl.DataFrame,
    value_col: str,
    *,
    group_col: str = "vol_regime",
    groups: tuple[str, ...] = DEFAULT_REGIMES,
    block: int = 24,
    n_boot: int = 500,
    alpha: float = 0.05,
    seed: int = 42,
) -> pl.DataFrame:
    """Per-regime median with a moving-block bootstrap confidence interval."""
    grouped = _regime_groups(df, value_col, group_col, groups)
    rows: list[dict[str, object]] = []
    for k, (label, values) in enumerate(grouped):
        ci = bootstrap_ci(
            values, median_stat, block=block, n_boot=n_boot, alpha=alpha, seed=seed + k
        )
        rows.append(
            {
                "regime": label,
                "n": int(values.size),
                "median": float(np.median(values)),
                "ci_low": ci.get("ci_low", float("nan")),
                "ci_high": ci.get("ci_high", float("nan")),
            }
        )
    schema = {
        "regime": pl.Utf8,
        "n": pl.Int64,
        "median": pl.Float64,
        "ci_low": pl.Float64,
        "ci_high": pl.Float64,
    }
    return pl.DataFrame(rows, schema=schema)


def regime_comparison(
    df: pl.DataFrame,
    value_cols: list[str],
    *,
    group_col: str = "vol_regime",
    groups: tuple[str, ...] = DEFAULT_REGIMES,
) -> pl.DataFrame:
    """One Kruskal-Wallis row per variable (H, p-value, effect size, counts)."""
    rows: list[dict[str, object]] = []
    for col in value_cols:
        res = kruskal_regime(df, col, group_col=group_col, groups=groups)
        if not res:
            continue
        rows.append(
            {
                "variable": col,
                "n": int(res["n"]),
                "n_groups": int(res["n_groups"]),
                "H": round(res["H"], 4),
                "pvalue": res["pvalue"],
                "epsilon_squared": round(res["epsilon_squared"], 4),
            }
        )
    schema = {
        "variable": pl.Utf8,
        "n": pl.Int64,
        "n_groups": pl.Int64,
        "H": pl.Float64,
        "pvalue": pl.Float64,
        "epsilon_squared": pl.Float64,
    }
    return pl.DataFrame(rows, schema=schema)
