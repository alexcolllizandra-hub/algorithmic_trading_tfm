"""Distribution-shape diagnostics beyond moments: t fits, tails, aggregation.

Everything here is descriptive machinery for Chapter 5: how far returns are
from Gaussian (Student-t fit, Jarque-Bera lives in ``returns.return_stats``),
how heavy the tails are (empirical survival function, Hill estimator) and how
the shape changes under temporal aggregation (kurtosis by horizon). All
functions are pure ``(arrays/frames, params) -> tidy frame`` transforms.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from scipy import stats


def _clean(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    return arr[np.isfinite(arr)]


def fit_student_t(values: np.ndarray) -> dict[str, float]:
    """Maximum-likelihood Student-t fit; ``df`` is the tail-heaviness headline.

    Location and scale are free so the fit answers "which t shape tracks the
    empirical quantiles", not "is the mean zero".
    """
    arr = _clean(values)
    df, loc, scale = stats.t.fit(arr)
    return {"df": float(df), "loc": float(loc), "scale": float(scale), "n": float(arr.size)}


def kurtosis_by_aggregation(
    base_returns: np.ndarray, factors: list[int], base_minutes: int = 5
) -> pl.DataFrame:
    """Excess kurtosis of k-bar aggregated returns for each factor.

    Log-returns aggregate by summation, so the k-bar series is the sum of k
    consecutive base returns over non-overlapping blocks. Under i.i.d.
    normality excess kurtosis would be zero at every horizon; slow decay with
    k is the classical aggregational-Gaussianity stylized fact.
    """
    arr = _clean(base_returns)
    rows = []
    for k in factors:
        n_blocks = arr.size // k
        blocks = arr[: n_blocks * k].reshape(n_blocks, k).sum(axis=1)
        rows.append(
            {
                "factor": k,
                "horizon_minutes": k * base_minutes,
                "n": n_blocks,
                "excess_kurtosis": float(stats.kurtosis(blocks, fisher=True, bias=False)),
                "skewness": float(stats.skew(blocks, bias=False)),
            }
        )
    return pl.DataFrame(rows)


def survival_function(values: np.ndarray, *, n_points: int = 400) -> pl.DataFrame:
    """Empirical survival P(|X| > x) of absolute values on a log-spaced grid.

    Downsampled to ``n_points`` log-spaced thresholds so a 600k-observation
    series still plots as a light frame; the exact empirical tail is preserved
    because thresholds are taken from the observed order statistics.
    """
    arr = np.sort(np.abs(_clean(values)))
    arr = arr[arr > 0]
    n = arr.size
    # Log-spaced ranks: dense in the tail where the plot matters.
    idx = np.unique((n - np.logspace(0, np.log10(n), n_points)).clip(0, n - 1).astype(int))
    return pl.DataFrame(
        {
            "abs_return": arr[idx].tolist(),
            "survival": ((n - idx) / n).tolist(),
        }
    ).sort("abs_return")


def hill_tail_index(values: np.ndarray, *, tail_fraction: float = 0.02) -> dict[str, float]:
    """Hill estimator of the tail index alpha over the top ``tail_fraction``.

    alpha_hat = k / sum(log(x_(i) / x_threshold)) over the k largest absolute
    observations. The asymptotic standard error is alpha / sqrt(k). alpha in
    (2, 4) means variance exists but the fourth moment is fragile — the reading
    the chapter leans on.
    """
    if not 0 < tail_fraction < 0.5:
        raise ValueError("tail_fraction must be in (0, 0.5).")
    arr = np.sort(np.abs(_clean(values)))[::-1]
    arr = arr[arr > 0]
    k = max(10, int(arr.size * tail_fraction))
    if arr.size <= k:
        raise ValueError("Not enough observations for the requested tail fraction.")
    tail = arr[:k]
    threshold = arr[k]
    alpha = k / float(np.sum(np.log(tail / threshold)))
    return {
        "alpha": float(alpha),
        "se": float(alpha / np.sqrt(k)),
        "k": float(k),
        "threshold": float(threshold),
        "tail_fraction": float(tail_fraction),
    }


def hill_by_k(values: np.ndarray, *, fractions: list[float] | None = None) -> pl.DataFrame:
    """Hill estimates over a range of tail fractions (stability check)."""
    fractions = fractions or [0.005, 0.01, 0.02, 0.05]
    rows = [hill_tail_index(values, tail_fraction=f) for f in fractions]
    return pl.DataFrame(rows)
