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
  families are tested at once;
* :func:`superior_predictive_ability` -- Hansen's SPA test, and
  :func:`reality_check` -- White's Reality Check, which ask whether *any* of the
  candidates beats a benchmark once the whole set of candidates is accounted
  for. Both share a stationary bootstrap, so the time dependence of the
  performance series is preserved rather than destroyed by an i.i.d. shuffle.

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

White, H. (2000). "A Reality Check for Data Snooping." *Econometrica* 68(5),
1097-1126.

Hansen, P. R. (2005). "A Test for Superior Predictive Ability." *Journal of
Business and Economic Statistics* 23(4), 365-380.

Politis, D. N. and Romano, J. P. (1994). "The Stationary Bootstrap." *Journal of
the American Statistical Association* 89(428), 1303-1313.

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


@dataclass(frozen=True)
class MultipleTestCorrection:
    """Outcome of correcting a family of p-values, with the adjusted values kept.

    ``adjusted_p_values`` are reported in the input order and are directly
    comparable against ``alpha``: a test is rejected exactly when its adjusted
    value is at or below it. Reporting them rather than only the flags lets a
    reader see how far a result was from surviving.
    """

    method: str
    alpha: float
    n_tests: int
    rejected: tuple[bool, ...]
    adjusted_p_values: tuple[float, ...]

    @property
    def n_rejected(self) -> int:
        return sum(self.rejected)


def _checked_p_values(p_values: Sequence[float], alpha: float) -> np.ndarray:
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha ({alpha}) must lie strictly inside (0, 1).")
    values = np.asarray(p_values, dtype=float)
    if np.any((values < 0.0) | (values > 1.0)) or not np.isfinite(values).all():
        raise ValueError("p_values must be finite and lie in [0, 1].")
    return values


def holm_bonferroni(p_values: Sequence[float], *, alpha: float = 0.05) -> MultipleTestCorrection:
    """Holm step-down control of the family-wise error rate at level ``alpha``.

    Holm controls the probability of **even one** false rejection across the
    whole family, which is the guarantee wanted when the question is "did any of
    the strategies we tried actually work". It is uniformly more powerful than
    plain Bonferroni and needs no independence assumption.

    The adjusted value for the *i*-th smallest p-value is
    ``max_{j <= i} (m - j + 1) * p_(j)``, capped at one; the running maximum is
    what keeps the sequence monotone, so a test is never rejected while a
    stronger one is not.
    """
    if not p_values:
        return MultipleTestCorrection("holm_bonferroni", alpha, 0, (), ())
    values = _checked_p_values(p_values, alpha)
    m = values.size
    order = np.argsort(values)
    scaled = (m - np.arange(m)) * values[order]
    adjusted_sorted = np.maximum.accumulate(scaled).clip(max=1.0)
    adjusted = np.empty(m, dtype=float)
    adjusted[order] = adjusted_sorted
    return MultipleTestCorrection(
        method="holm_bonferroni",
        alpha=alpha,
        n_tests=int(m),
        rejected=tuple(bool(x) for x in adjusted <= alpha),
        adjusted_p_values=tuple(float(x) for x in adjusted),
    )


def benjamini_hochberg_correction(
    p_values: Sequence[float], *, alpha: float = 0.05
) -> MultipleTestCorrection:
    """Benjamini-Hochberg FDR control, returning adjusted p-values as well.

    Same rejection set as :func:`benjamini_hochberg`; this variant additionally
    reports the adjusted values (q-values), which is what a results table needs.
    The adjusted value for the *i*-th smallest p-value is
    ``min_{j >= i} (m / j) * p_(j)``, capped at one.
    """
    if not p_values:
        return MultipleTestCorrection("benjamini_hochberg", alpha, 0, (), ())
    values = _checked_p_values(p_values, alpha)
    m = values.size
    order = np.argsort(values)
    ranks = np.arange(1, m + 1)
    scaled = (m / ranks) * values[order]
    # Running minimum from the largest p-value downwards keeps q-values monotone.
    adjusted_sorted = np.minimum.accumulate(scaled[::-1])[::-1].clip(max=1.0)
    adjusted = np.empty(m, dtype=float)
    adjusted[order] = adjusted_sorted
    return MultipleTestCorrection(
        method="benjamini_hochberg",
        alpha=alpha,
        n_tests=int(m),
        rejected=tuple(bool(x) for x in adjusted <= alpha),
        adjusted_p_values=tuple(float(x) for x in adjusted),
    )


# --------------------------------------------------------------------------- #
# Data-snooping tests over a whole set of candidates (White RC / Hansen SPA)
# --------------------------------------------------------------------------- #


def stationary_bootstrap_indices(
    n_observations: int,
    n_bootstrap: int,
    *,
    block_probability: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Politis-Romano stationary-bootstrap resampling indices.

    Each resample walks forward through the series, restarting at a uniformly
    random position with probability ``block_probability`` at every step, which
    produces geometrically distributed blocks with mean length
    ``1 / block_probability``. Resampling *blocks* rather than individual
    observations is what preserves the autocorrelation and volatility clustering
    of a performance series; an i.i.d. shuffle would destroy both and understate
    the sampling variability of the mean.

    Returns an integer array of shape ``(n_bootstrap, n_observations)``.
    """
    if n_observations < 2:
        raise ValueError("n_observations must be at least 2.")
    if n_bootstrap < 1:
        raise ValueError("n_bootstrap must be at least 1.")
    if not 0.0 < block_probability <= 1.0:
        raise ValueError(
            f"block_probability ({block_probability}) must lie in (0, 1]; it is the "
            "per-step restart probability, so its reciprocal is the mean block length."
        )
    restarts = rng.random((n_bootstrap, n_observations)) < block_probability
    fresh = rng.integers(0, n_observations, size=(n_bootstrap, n_observations))
    indices = np.empty((n_bootstrap, n_observations), dtype=np.int64)
    indices[:, 0] = fresh[:, 0]
    for t in range(1, n_observations):
        advanced = (indices[:, t - 1] + 1) % n_observations
        indices[:, t] = np.where(restarts[:, t], fresh[:, t], advanced)
    return indices


@dataclass(frozen=True)
class SnoopingTestResult:
    """Outcome of a data-snooping test over a set of candidates."""

    test: str
    statistic: float
    p_value: float
    n_candidates: int
    n_observations: int
    n_bootstrap: int
    block_probability: float
    best_candidate: int

    @property
    def significant_at_5pct(self) -> bool:
        return self.p_value < 0.05

    def to_dict(self) -> dict[str, object]:
        return {
            "test": self.test,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "n_candidates": self.n_candidates,
            "n_observations": self.n_observations,
            "n_bootstrap": self.n_bootstrap,
            "block_probability": self.block_probability,
            "best_candidate": self.best_candidate,
        }


def _validate_differentials(loss_differentials: np.ndarray) -> np.ndarray:
    matrix = np.asarray(loss_differentials, dtype=float)
    if matrix.ndim != 2:
        raise ValueError(
            f"loss_differentials must be 2-D (observations x candidates), got {matrix.ndim}-D."
        )
    if matrix.shape[0] < 2:
        raise ValueError("loss_differentials needs at least 2 observations.")
    if matrix.shape[1] < 1:
        raise ValueError("loss_differentials needs at least one candidate.")
    if not np.isfinite(matrix).all():
        raise ValueError("loss_differentials contains non-finite entries.")
    return matrix


def _bootstrap_means(
    matrix: np.ndarray,
    *,
    n_bootstrap: int,
    block_probability: float,
    rng: np.random.Generator,
) -> np.ndarray:
    indices = stationary_bootstrap_indices(
        matrix.shape[0], n_bootstrap, block_probability=block_probability, rng=rng
    )
    return matrix[indices].mean(axis=1)


def reality_check(
    loss_differentials: np.ndarray,
    *,
    n_bootstrap: int = 1000,
    block_probability: float = 0.1,
    seed: int = 42,
) -> SnoopingTestResult:
    """White's Reality Check: does the best candidate beat the benchmark?

    ``loss_differentials[t, k]`` is candidate *k*'s performance advantage over the
    benchmark at observation *t* (positive means the candidate did better). The
    null hypothesis is that **no** candidate is better than the benchmark.

    The test recentres every candidate at its own sample mean, including
    candidates that are clearly hopeless. Those poor candidates still enlarge the
    bootstrap maximum, which is why the Reality Check is conservative and why
    :func:`superior_predictive_ability` is normally preferred.
    """
    matrix = _validate_differentials(loss_differentials)
    n_obs, n_candidates = matrix.shape
    rng = np.random.default_rng(seed)

    means = matrix.mean(axis=0)
    root_t = math.sqrt(n_obs)
    statistic = float(np.max(root_t * means))

    boot_means = _bootstrap_means(
        matrix, n_bootstrap=n_bootstrap, block_probability=block_probability, rng=rng
    )
    boot_statistics = np.max(root_t * (boot_means - means[None, :]), axis=1)
    p_value = float(np.mean(boot_statistics >= statistic))

    return SnoopingTestResult(
        test="white_reality_check",
        statistic=statistic,
        p_value=p_value,
        n_candidates=n_candidates,
        n_observations=n_obs,
        n_bootstrap=n_bootstrap,
        block_probability=block_probability,
        best_candidate=int(np.argmax(means)),
    )


def superior_predictive_ability(
    loss_differentials: np.ndarray,
    *,
    n_bootstrap: int = 1000,
    block_probability: float = 0.1,
    seed: int = 42,
) -> SnoopingTestResult:
    """Hansen's SPA test: does any candidate beat the benchmark, studentised?

    ``loss_differentials[t, k]`` is candidate *k*'s performance advantage over the
    benchmark at observation *t*. The null hypothesis is that no candidate is
    better than the benchmark once the size of the candidate set is accounted
    for. A small p-value is evidence that at least one candidate genuinely
    outperforms.

    Two things distinguish this from :func:`reality_check`:

    * the statistic is **studentised** by each candidate's own bootstrap standard
      error, so a candidate is not favoured merely for being volatile;
    * candidates whose sample mean is far enough below zero are recentred at
      zero rather than at their own mean (Hansen's *consistent* estimator), which
      removes them from the null distribution instead of letting them inflate its
      maximum. This is what makes the test more powerful than the Reality Check.

    The threshold for that recentring is Hansen's
    ``-sqrt(omega_k^2 / T * 2 * log(log(T)))``.
    """
    matrix = _validate_differentials(loss_differentials)
    n_obs, n_candidates = matrix.shape
    if n_obs < 4:
        raise ValueError(
            "Hansen's SPA needs at least 4 observations: its recentring threshold "
            "uses log(log(T)), which is undefined below T = 3."
        )
    rng = np.random.default_rng(seed)

    means = matrix.mean(axis=0)
    root_t = math.sqrt(n_obs)

    boot_means = _bootstrap_means(
        matrix, n_bootstrap=n_bootstrap, block_probability=block_probability, rng=rng
    )
    # Bootstrap variance of sqrt(T) * mean, taken around the sample mean.
    omega_squared = float(n_obs) * np.mean((boot_means - means[None, :]) ** 2, axis=0)
    # A candidate with no variation at all cannot be studentised; it is also
    # uninformative, so it is given an infinite scale and drops out of the max.
    degenerate = omega_squared <= 0.0
    omega = np.sqrt(np.where(degenerate, 1.0, omega_squared))

    studentised = np.where(degenerate, -np.inf, root_t * means / omega)
    statistic = float(max(np.max(studentised), 0.0))

    threshold = -np.sqrt(omega_squared / n_obs * 2.0 * math.log(math.log(n_obs)))
    recentred = np.where(means >= threshold, means, 0.0)

    boot_studentised = np.where(
        degenerate[None, :],
        -np.inf,
        root_t * (boot_means - recentred[None, :]) / omega[None, :],
    )
    boot_statistics = np.maximum(np.max(boot_studentised, axis=1), 0.0)
    p_value = float(np.mean(boot_statistics >= statistic))

    return SnoopingTestResult(
        test="hansen_spa_consistent",
        statistic=statistic,
        p_value=p_value,
        n_candidates=n_candidates,
        n_observations=n_obs,
        n_bootstrap=n_bootstrap,
        block_probability=block_probability,
        best_candidate=int(np.argmax(studentised)),
    )
