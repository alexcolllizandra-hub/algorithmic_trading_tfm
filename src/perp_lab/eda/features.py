"""EDA-side characterisation of the engineered feature set and the labels.

Answers three descriptive questions for Chapter 5.7 without training anything:
how redundant the feature set is (correlation structure, PCA scree), how much
dependence it carries about forward returns at each horizon (mutual
information against a permutation-based noise floor), and what the
triple-barrier labels look like at the protocol's parameters.

The feature *construction* lives in :mod:`perp_lab.features`; this module only
consumes the finished matrix.
"""

from __future__ import annotations

from typing import cast

import numpy as np
import polars as pl
from sklearn.feature_selection import mutual_info_regression


def feature_correlation_matrix(frame: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """Spearman correlation matrix of the feature columns, tidy long format."""
    data = frame.select(cols).drop_nulls()
    ranked = np.column_stack([data[c].rank().to_numpy().astype(float) for c in cols])
    corr = np.corrcoef(ranked, rowvar=False)
    rows = []
    for i, a in enumerate(cols):
        for j, b in enumerate(cols):
            rows.append({"feature_a": a, "feature_b": b, "spearman": float(corr[i, j])})
    return pl.DataFrame(rows)


def high_correlation_pairs(corr_long: pl.DataFrame, *, threshold: float = 0.9) -> pl.DataFrame:
    """Distinct feature pairs with |Spearman| at or above ``threshold``."""
    return corr_long.filter(
        (pl.col("feature_a") < pl.col("feature_b")) & (pl.col("spearman").abs() >= threshold)
    ).sort(pl.col("spearman").abs(), descending=True)


def pca_scree(frame: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """Explained-variance share per principal component of the standardised set."""
    data = frame.select(cols).drop_nulls()
    x = np.column_stack([data[c].to_numpy().astype(float) for c in cols])
    x = (x - x.mean(axis=0)) / x.std(axis=0, ddof=1)
    eigvals = np.linalg.eigvalsh(np.cov(x, rowvar=False))[::-1]
    share = eigvals / eigvals.sum()
    return pl.DataFrame(
        {
            "component": list(range(1, len(cols) + 1)),
            "explained_share": share.tolist(),
            "cumulative_share": np.cumsum(share).tolist(),
        }
    )


def mutual_information_by_horizon(
    frame: pl.DataFrame,
    feature_cols: list[str],
    *,
    ret_col: str = "log_return",
    horizons: list[int] | None = None,
    n_permutations: int = 5,
    seed: int = 42,
    n_neighbors: int = 3,
) -> pl.DataFrame:
    """Mutual information of each feature with forward returns per horizon.

    The forward target at horizon h is the sum of the next h log-returns
    (excluding the current bar). For every (feature, horizon) pair the frame
    also carries a permutation-based noise floor: the mean and max MI obtained
    after shuffling the target with a fixed seed, which is what "no dependence"
    looks like for this estimator at this sample size.
    """
    horizons = horizons or [1, 2, 4, 8, 12, 24, 48]
    rng = np.random.default_rng(seed)
    ret = frame[ret_col].to_numpy().astype(float)
    csum = np.concatenate([[0.0], np.cumsum(np.nan_to_num(ret))])
    rows = []
    for h in horizons:
        fwd = csum[1 + h :] - csum[1:-h] if h < ret.size else np.array([])
        usable = frame.head(fwd.size)
        target = fwd
        for col in feature_cols:
            x = usable[col].to_numpy().astype(float)
            valid = np.isfinite(x) & np.isfinite(target)
            xv = x[valid].reshape(-1, 1)
            yv = target[valid]
            mi = float(
                mutual_info_regression(xv, yv, n_neighbors=n_neighbors, random_state=seed)[0]
            )
            perms = []
            for _ in range(n_permutations):
                perms.append(
                    float(
                        mutual_info_regression(
                            xv,
                            rng.permutation(yv),
                            n_neighbors=n_neighbors,
                            random_state=seed,
                        )[0]
                    )
                )
            rows.append(
                {
                    "feature": col,
                    "horizon_bars": h,
                    "n": int(valid.sum()),
                    "mi_nats": mi,
                    "noise_floor_mean": float(np.mean(perms)),
                    "noise_floor_max": float(np.max(perms)),
                }
            )
    return pl.DataFrame(rows)


def label_summary(labels: pl.DataFrame) -> dict[str, float]:
    """Class balance and resolution profile of a triple-barrier label frame."""
    n = labels.height
    counts = dict(labels.group_by("label").agg(pl.len().alias("n")).iter_rows())
    barrier = dict(labels.group_by("barrier_touched").agg(pl.len().alias("n")).iter_rows())
    return {
        "n_events": float(n),
        "share_positive": counts.get(1, 0) / n,
        "share_negative": counts.get(-1, 0) / n,
        "share_zero": counts.get(0, 0) / n,
        "share_meta_positive": float(cast("float", labels["meta_label"].mean() or 0.0)),
        "share_upper": barrier.get("upper", 0) / n,
        "share_lower": barrier.get("lower", 0) / n,
        "share_vertical": barrier.get("vertical", 0) / n,
        "median_holding_bars": float(cast("float", labels["holding_bars"].median() or 0.0)),
        "mean_holding_bars": float(cast("float", labels["holding_bars"].mean() or 0.0)),
    }
