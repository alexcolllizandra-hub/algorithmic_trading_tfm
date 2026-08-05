"""Moving-block bootstrap confidence intervals for dependent series.

Financial return series are serially dependent (volatility clustering, slow
funding dynamics), so an i.i.d. bootstrap that resamples individual observations
destroys the temporal dependence and understates the sampling variability of
statistics such as the mean, realised volatility and Sharpe ratio. The
*moving-block* bootstrap resamples overlapping blocks of ``block`` consecutive
observations, preserving short-range dependence within each block.

All intervals here are **percentile** intervals of the bootstrap distribution
and are strictly descriptive: they quantify the in-sample sampling uncertainty
of a statistic on the development set. They are not out-of-sample performance
guarantees and say nothing about profitability, which requires a cost-aware
backtest and the frozen holdout.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.intp]
Statistic = Callable[[FloatArray], float]


def _clean(x: npt.ArrayLike) -> FloatArray:
    """Return a 1-D float array with non-finite values removed."""
    a = np.asarray(x, dtype=float).ravel()
    return a[np.isfinite(a)]


def _block_indices(n: int, block: int, rng: np.random.Generator) -> IntArray:
    """Indices of ``ceil(n / block)`` overlapping blocks, truncated to length ``n``."""
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=n_blocks)
    idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n]
    return idx.astype(np.intp)


def mean_stat(x: FloatArray) -> float:
    """Sample mean."""
    return float(np.mean(x))


def vol_stat(x: FloatArray) -> float:
    """Sample standard deviation (ddof=1); the per-bar realised volatility."""
    return float(np.std(x, ddof=1)) if x.size > 1 else float("nan")


def median_stat(x: FloatArray) -> float:
    """Sample median."""
    return float(np.median(x))


def sharpe_stat(periods_per_year: float) -> Statistic:
    """Return a Sharpe-ratio statistic annualised by ``sqrt(periods_per_year)``.

    Computed on per-bar returns with a zero risk-free rate (a descriptive,
    in-sample Sharpe): ``mean / std * sqrt(periods_per_year)``.
    """
    scale = float(np.sqrt(periods_per_year))

    def _sharpe(x: FloatArray) -> float:
        sd = float(np.std(x, ddof=1)) if x.size > 1 else 0.0
        if sd <= 0.0:
            return float("nan")
        return float(np.mean(x) / sd * scale)

    return _sharpe


def moving_block_bootstrap(
    x: npt.ArrayLike,
    statistic: Statistic,
    *,
    block: int = 24,
    n_boot: int = 1000,
    seed: int = 42,
) -> FloatArray:
    """Bootstrap distribution of ``statistic`` under a moving-block resample."""
    a = _clean(x)
    n = a.size
    if block < 1 or n < block * 2:
        return np.empty(0, dtype=float)
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        out[i] = statistic(a[_block_indices(n, block, rng)])
    return out


def bootstrap_ci(
    x: npt.ArrayLike,
    statistic: Statistic,
    *,
    block: int = 24,
    n_boot: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict[str, float]:
    """Point estimate and percentile confidence interval for ``statistic``.

    Returns an empty dict when the series is too short for the chosen block
    length (``n < 2 * block``).
    """
    a = _clean(x)
    boot = moving_block_bootstrap(a, statistic, block=block, n_boot=n_boot, seed=seed)
    if boot.size == 0:
        return {}
    finite = boot[np.isfinite(boot)]
    if finite.size == 0:
        return {}
    lo, hi = np.quantile(finite, [alpha / 2, 1 - alpha / 2])
    return {
        "estimate": float(statistic(a)),
        "ci_low": float(lo),
        "ci_high": float(hi),
        "n": float(a.size),
        "block": float(block),
        "n_boot": float(boot.size),
    }


def bootstrap_diff_ci(
    x_a: npt.ArrayLike,
    x_b: npt.ArrayLike,
    statistic: Statistic,
    *,
    block: int = 24,
    n_boot: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict[str, float]:
    """Confidence interval for the difference ``statistic(a) - statistic(b)``.

    Each sample is resampled independently with its own moving-block bootstrap
    (they may have different lengths, e.g. two timeframes or two regimes), and
    the paired bootstrap differences form the interval. ``prob_positive`` is the
    share of resamples with a positive difference, supporting statements such as
    "the difference remained positive in most resamples".
    """
    a = _clean(x_a)
    b = _clean(x_b)
    if block < 1 or a.size < block * 2 or b.size < block * 2:
        return {}
    rng = np.random.default_rng(seed)
    boot = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        sa = statistic(a[_block_indices(a.size, block, rng)])
        sb = statistic(b[_block_indices(b.size, block, rng)])
        boot[i] = sa - sb
    finite = boot[np.isfinite(boot)]
    if finite.size == 0:
        return {}
    lo, hi = np.quantile(finite, [alpha / 2, 1 - alpha / 2])
    return {
        "estimate": float(statistic(a) - statistic(b)),
        "ci_low": float(lo),
        "ci_high": float(hi),
        "n_a": float(a.size),
        "n_b": float(b.size),
        "block": float(block),
        "prob_positive": float(np.mean(finite > 0.0)),
    }
