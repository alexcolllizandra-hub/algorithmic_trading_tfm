"""Selection-bias corrections for a search that tried many strategies.

A backtest reports the performance of the *winner* of a search, not of a
strategy chosen in advance. The more configurations are tried, the higher the
best in-sample Sharpe ratio will be even when every configuration is worthless,
so an uncorrected Sharpe ratio is not evidence. This module implements the three
corrections the Gate S1 contract requires:

* :func:`expected_maximum_sharpe` -- the Sharpe ratio a *null* search of this
  size would be expected to produce by luck alone;
* :func:`deflated_sharpe_ratio` -- the probability that the observed Sharpe
  ratio exceeds that benchmark, adjusting for the non-normality of the return
  distribution (Bailey and Lopez de Prado, 2014);
* :func:`probability_of_backtest_overfitting` -- the combinatorially symmetric
  cross-validation (CSCV) estimate of how often the in-sample winner
  underperforms the median out of sample (Bailey, Borwein, Lopez de Prado and
  Zhu, 2017);
* :func:`benjamini_hochberg` -- false-discovery-rate control when several
  families are tested at once.

References
----------
Bailey, D. H. and Lopez de Prado, M. (2014). "The Deflated Sharpe Ratio:
Correcting for Selection Bias, Backtest Overfitting and Non-Normality."
*Journal of Portfolio Management* 40(5), 94-107.

Bailey, D. H., Borwein, J., Lopez de Prado, M. and Zhu, Q. J. (2017). "The
Probability of Backtest Overfitting." *Journal of Computational Finance* 20(4),
39-69.

Benjamini, Y. and Hochberg, Y. (1995). "Controlling the False Discovery Rate."
*Journal of the Royal Statistical Society B* 57(1), 289-300.

Consulted 2026-08-11. These are corrections applied to results the pipeline has
already produced; nothing here reads market data.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations

import numpy as np

# Euler-Mascheroni constant, used by the expected-maximum-of-N-Gaussians bound.
_EULER_MASCHERONI = 0.5772156649015329


def _standard_normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _standard_normal_ppf(p: float) -> float:
    """Inverse standard normal CDF via bisection on ``erf``.

    Bisection is slower than a rational approximation and exact enough for the
    two evaluations this module needs, which keeps SciPy out of a numerical path
    that has to stay reproducible across environments.
    """
    if not 0.0 < p < 1.0:
        raise ValueError(f"p ({p}) must lie strictly inside (0, 1).")
    lo, hi = -40.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if _standard_normal_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def expected_maximum_sharpe(n_trials: int, sharpe_std: float) -> float:
    """Expected maximum Sharpe ratio of ``n_trials`` independent null strategies.

    ``sharpe_std`` is the cross-sectional standard deviation of the Sharpe
    ratios actually produced by the search. With one trial the expectation is
    zero: there is nothing to select from, so there is no selection bias.
    """
    if n_trials < 1:
        raise ValueError("n_trials must be at least 1.")
    if sharpe_std < 0:
        raise ValueError("sharpe_std must be non-negative.")
    if n_trials == 1 or sharpe_std == 0.0:
        return 0.0
    n = float(n_trials)
    gamma = _EULER_MASCHERONI
    term = (1.0 - gamma) * _standard_normal_ppf(1.0 - 1.0 / n) + gamma * _standard_normal_ppf(
        1.0 - 1.0 / (n * math.e)
    )
    return sharpe_std * term


@dataclass(frozen=True)
class DeflatedSharpe:
    """Result of a deflated-Sharpe test, with every input kept for the record."""

    observed_sharpe: float
    benchmark_sharpe: float
    deflated_sharpe: float
    n_trials: int
    n_observations: int
    skewness: float
    kurtosis: float

    @property
    def significant_at(self) -> float:
        """Smallest significance level at which the observed Sharpe survives."""
        return 1.0 - self.deflated_sharpe

    def to_dict(self) -> dict[str, float | int]:
        return {
            "observed_sharpe": self.observed_sharpe,
            "benchmark_sharpe": self.benchmark_sharpe,
            "deflated_sharpe": self.deflated_sharpe,
            "n_trials": self.n_trials,
            "n_observations": self.n_observations,
            "skewness": self.skewness,
            "kurtosis": self.kurtosis,
        }


def deflated_sharpe_ratio(
    observed_sharpe: float,
    *,
    n_trials: int,
    n_observations: int,
    sharpe_std: float,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
) -> DeflatedSharpe:
    """Probability that ``observed_sharpe`` beats a null search of ``n_trials``.

    All Sharpe ratios must be expressed **per observation** (not annualised), on
    the same sampling frequency as ``n_observations``, because the estimator's
    standard error depends on the number of returns behind it.

    ``kurtosis`` is the raw fourth standardised moment (3.0 for a Gaussian), not
    the excess. A value below 1.0 is impossible for any real distribution and is
    rejected rather than silently producing a negative variance.
    """
    if n_observations < 2:
        raise ValueError("n_observations must be at least 2 for a Sharpe standard error.")
    if kurtosis < 1.0:
        raise ValueError(
            f"kurtosis ({kurtosis}) is the raw fourth standardised moment and cannot be "
            "below 1.0; pass 3.0 for a Gaussian, not 0.0."
        )
    benchmark = expected_maximum_sharpe(n_trials, sharpe_std)
    n = float(n_observations)
    variance = (1.0 - skewness * observed_sharpe + 0.25 * (kurtosis - 1.0) * observed_sharpe**2) / (
        n - 1.0
    )
    if variance <= 0.0:
        raise ValueError(
            "Non-positive Sharpe variance: the supplied moments are mutually inconsistent "
            f"(skewness={skewness}, kurtosis={kurtosis}, sharpe={observed_sharpe})."
        )
    statistic = (observed_sharpe - benchmark) / math.sqrt(variance)
    return DeflatedSharpe(
        observed_sharpe=observed_sharpe,
        benchmark_sharpe=benchmark,
        deflated_sharpe=_standard_normal_cdf(statistic),
        n_trials=n_trials,
        n_observations=n_observations,
        skewness=skewness,
        kurtosis=kurtosis,
    )


@dataclass(frozen=True)
class PBOResult:
    """Combinatorially symmetric cross-validation overfitting estimate."""

    pbo: float
    n_splits: int
    logits: tuple[float, ...]

    def to_dict(self) -> dict[str, object]:
        return {"pbo": self.pbo, "n_splits": self.n_splits, "logits": list(self.logits)}


def probability_of_backtest_overfitting(
    performance: np.ndarray,
    *,
    n_partitions: int = 8,
) -> PBOResult:
    """CSCV estimate of the probability the in-sample winner is out-of-sample median-or-worse.

    ``performance`` is a ``(n_observations, n_configurations)`` matrix of
    per-period performance (for example per-fold returns) for **every**
    configuration the search evaluated -- not only the winner. The rows are split
    into ``n_partitions`` contiguous chronological blocks; every half-sized
    combination of blocks forms an in-sample set and its complement the
    out-of-sample set.

    Blocks are contiguous and never reordered, so the procedure respects the time
    ordering that the rest of the pipeline enforces.
    """
    matrix = np.asarray(performance, dtype=float)
    if matrix.ndim != 2:
        raise ValueError(
            f"performance must be 2-D (observations x configurations), got {matrix.ndim}-D."
        )
    n_obs, n_config = matrix.shape
    if n_config < 2:
        raise ValueError("PBO needs at least two configurations to rank.")
    if n_partitions < 2 or n_partitions % 2 != 0:
        raise ValueError(f"n_partitions ({n_partitions}) must be an even number of at least 2.")
    if n_obs < n_partitions:
        raise ValueError(
            f"performance has {n_obs} observations, fewer than the {n_partitions} partitions "
            "requested; use fewer partitions or a longer evaluation."
        )
    if not np.isfinite(matrix).all():
        raise ValueError("performance contains non-finite entries; clean or mask them first.")

    blocks = np.array_split(np.arange(n_obs), n_partitions)
    half = n_partitions // 2
    logits: list[float] = []
    for chosen in combinations(range(n_partitions), half):
        in_idx = np.concatenate([blocks[b] for b in chosen])
        out_idx = np.concatenate([blocks[b] for b in range(n_partitions) if b not in chosen])
        in_perf = matrix[in_idx].mean(axis=0)
        out_perf = matrix[out_idx].mean(axis=0)
        best = int(np.argmax(in_perf))
        # Relative rank of the in-sample winner within the out-of-sample results.
        rank = float((out_perf <= out_perf[best]).sum()) / float(n_config + 1)
        rank = min(max(rank, 1.0 / (n_config + 1)), 1.0 - 1.0 / (n_config + 1))
        logits.append(math.log(rank / (1.0 - rank)))

    pbo = float(np.mean([1.0 if logit <= 0.0 else 0.0 for logit in logits]))
    return PBOResult(pbo=pbo, n_splits=len(logits), logits=tuple(logits))


def benjamini_hochberg(p_values: Sequence[float], *, alpha: float = 0.05) -> tuple[bool, ...]:
    """Benjamini-Hochberg false-discovery-rate control at level ``alpha``.

    Returns one rejection flag per input p-value, in the input order.
    """
    if not p_values:
        return ()
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha ({alpha}) must lie strictly inside (0, 1).")
    values = np.asarray(p_values, dtype=float)
    if np.any((values < 0.0) | (values > 1.0)) or not np.isfinite(values).all():
        raise ValueError("p_values must be finite and lie in [0, 1].")
    m = values.size
    order = np.argsort(values)
    thresholds = alpha * (np.arange(1, m + 1) / m)
    passed = values[order] <= thresholds
    rejected = np.zeros(m, dtype=bool)
    if passed.any():
        cutoff = int(np.max(np.flatnonzero(passed)))
        rejected[order[: cutoff + 1]] = True
    return tuple(bool(x) for x in rejected)
