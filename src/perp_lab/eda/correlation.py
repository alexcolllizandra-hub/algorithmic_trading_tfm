"""Cross-asset correlation (static, rolling and conditional)."""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
from scipy import stats


def _aligned(
    left: pl.DataFrame,
    right: pl.DataFrame,
    col: str,
    time_col: str,
    suffixes: tuple[str, str],
) -> pl.DataFrame:
    a, b = suffixes
    return (
        left.select(time_col, pl.col(col).alias(f"{col}{a}"))
        .join(right.select(time_col, pl.col(col).alias(f"{col}{b}")), on=time_col, how="inner")
        .sort(time_col)
    )


def static_correlation(
    left: pl.DataFrame,
    right: pl.DataFrame,
    col: str = "log_return",
    time_col: str = "open_time",
) -> float:
    """Pearson correlation of ``col`` between two assets on their shared index."""
    joined = _aligned(left, right, col, time_col, ("_a", "_b"))
    if joined.height < 2:
        return float("nan")
    return float(joined.select(pl.corr(f"{col}_a", f"{col}_b")).item())


def spearman_correlation(
    left: pl.DataFrame,
    right: pl.DataFrame,
    col: str = "log_return",
    time_col: str = "open_time",
) -> float:
    """Spearman rank correlation of ``col`` between two assets on their shared index."""
    joined = _aligned(left, right, col, time_col, ("_a", "_b")).drop_nulls()
    if joined.height < 2:
        return float("nan")
    res: Any = stats.spearmanr(joined[f"{col}_a"].to_numpy(), joined[f"{col}_b"].to_numpy())
    return float(res.correlation)


def rolling_correlation(
    left: pl.DataFrame,
    right: pl.DataFrame,
    window: int,
    col: str = "log_return",
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Rolling Pearson correlation of ``col`` over ``window`` bars."""
    joined = _aligned(left, right, col, time_col, ("_a", "_b"))
    return joined.with_columns(
        pl.rolling_corr(
            pl.col(f"{col}_a"), pl.col(f"{col}_b"), window_size=window, min_samples=window
        ).alias(f"rolling_corr_{window}")
    ).select(time_col, f"rolling_corr_{window}")


def correlation_by_sign(
    left: pl.DataFrame,
    right: pl.DataFrame,
    col: str = "log_return",
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Correlation conditional on the sign of the ``left`` asset's return."""
    joined = _aligned(left, right, col, time_col, ("_a", "_b")).drop_nulls()
    rows: list[dict[str, object]] = []
    for label, mask in (
        ("left_positive", joined[f"{col}_a"] > 0),
        ("left_negative", joined[f"{col}_a"] < 0),
    ):
        sub = joined.filter(mask)
        rows.append(
            {
                "condition": label,
                "n": sub.height,
                "pearson": round(float(sub.select(pl.corr(f"{col}_a", f"{col}_b")).item()), 4)
                if sub.height > 2
                else float("nan"),
            }
        )
    return pl.DataFrame(rows)


def correlation_by_vol_regime(
    left: pl.DataFrame,
    right: pl.DataFrame,
    *,
    col: str = "log_return",
    time_col: str = "open_time",
    vol_window: int = 24,
) -> pl.DataFrame:
    """Correlation conditional on low/medium/high volatility of the ``left`` asset.

    Volatility terciles are computed on the shared-index sample (descriptive
    only); this characterises how co-movement changes with market stress.
    """
    left_vol = left.sort(time_col).with_columns(
        pl.col(col).rolling_std(vol_window, min_samples=vol_window).alias("_vol")
    )
    joined = (
        left_vol.select(time_col, pl.col(col).alias(f"{col}_a"), "_vol")
        .join(right.select(time_col, pl.col(col).alias(f"{col}_b")), on=time_col, how="inner")
        .drop_nulls()
    )
    if joined.height < 30:
        return pl.DataFrame(schema={"vol_regime": pl.Utf8, "n": pl.Int64, "pearson": pl.Float64})
    q33, q66 = joined.select(
        pl.col("_vol").quantile(0.33).alias("q33"), pl.col("_vol").quantile(0.66).alias("q66")
    ).row(0)
    labelled = joined.with_columns(
        pl.when(pl.col("_vol") <= q33)
        .then(pl.lit("low"))
        .when(pl.col("_vol") <= q66)
        .then(pl.lit("medium"))
        .otherwise(pl.lit("high"))
        .alias("vol_regime")
    )
    rows: list[dict[str, object]] = []
    for label in ("low", "medium", "high"):
        sub = labelled.filter(pl.col("vol_regime") == label)
        rows.append(
            {
                "vol_regime": label,
                "n": sub.height,
                "pearson": round(float(sub.select(pl.corr(f"{col}_a", f"{col}_b")).item()), 4)
                if sub.height > 2
                else float("nan"),
            }
        )
    return pl.DataFrame(rows)


def block_bootstrap_corr_ci(
    left: pl.DataFrame,
    right: pl.DataFrame,
    *,
    col: str = "log_return",
    time_col: str = "open_time",
    block: int = 24,
    n_boot: int = 500,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict[str, float]:
    """Block-bootstrap confidence interval for the Pearson return correlation.

    Overlapping blocks of length ``block`` preserve short-range dependence. The
    interval is the empirical ``[alpha/2, 1-alpha/2]`` quantile of the bootstrap
    correlations.
    """
    joined = _aligned(left, right, col, time_col, ("_a", "_b")).drop_nulls()
    n = joined.height
    if n < block * 3:
        return {}
    a = joined[f"{col}_a"].to_numpy()
    b = joined[f"{col}_b"].to_numpy()
    point = float(np.corrcoef(a, b)[0, 1])
    rng = np.random.default_rng(seed)
    n_blocks = n // block
    starts_max = n - block
    boot = np.empty(n_boot)
    for i in range(n_boot):
        starts = rng.integers(0, starts_max + 1, size=n_blocks)
        idx = (starts[:, None] + np.arange(block)[None, :]).ravel()
        boot[i] = np.corrcoef(a[idx], b[idx])[0, 1]
    lo, hi = np.quantile(boot, [alpha / 2, 1 - alpha / 2])
    return {
        "corr": round(point, 4),
        "ci_low": round(float(lo), 4),
        "ci_high": round(float(hi), 4),
        "n": float(n),
    }
