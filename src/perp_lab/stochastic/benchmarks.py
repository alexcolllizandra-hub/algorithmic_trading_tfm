"""What a search finds when there is nothing to find, and what risk looks like.

Four questions, each with its own tool:

1. **How impressive is my winner, really?** :func:`search_false_positive_rate`
   runs the caller's whole selection procedure on markets that are unpredictable
   by construction and reports the distribution of the statistic it selects. A
   Sharpe of 1.2 means nothing until you know that searching 100 candidates on
   pure noise produces 1.1 half the time.
2. **Does the pipeline work at all?** A detector that never fires is not
   conservative, it is broken. :func:`reversion_detection_power` checks that the
   same procedure *does* fire on an Ornstein-Uhlenbeck path, where reversion
   genuinely exists.
3. **Is the triple-barrier implementation right?** :func:`first_passage_summary`
   simulates a driftless diffusion, where the probability of touching a
   symmetric upper barrier first is exactly one half, giving the labeler a
   ground truth to be checked against.
4. **How bad can the equity curve get?** :func:`drawdown_distribution` and
   :func:`ruin_probability` estimate drawdown and ruin. The **primary** input is
   the stationary block bootstrap of realised returns
   (:func:`bootstrap_return_paths`), because it keeps fat tails and serial
   dependence; GBM is the sensitivity analysis, and
   :func:`compare_risk_estimates` puts the two side by side so the gap is
   visible rather than assumed away.

Nothing here is a strategy or a source of alpha.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from perp_lab.evaluation.multiple_testing import stationary_bootstrap_indices
from perp_lab.stochastic.processes import (
    GbmParameters,
    OuParameters,
    simulate_gbm,
    simulate_ou,
)

# A selection procedure: given one synthetic price path and a seeded generator,
# run the whole search and return the statistic of the candidate it selected.
SelectionProcedure = Callable[[np.ndarray, np.random.Generator], float]


@dataclass(frozen=True)
class NullSelectionReport:
    """The null distribution of whatever statistic a search procedure selects."""

    statistics: np.ndarray = field(repr=False)
    threshold: float
    false_positive_rate: float
    median: float
    quantile_95: float
    quantile_99: float
    maximum: float
    n_trials: int

    def to_dict(self) -> dict[str, float | int]:
        return {
            "threshold": self.threshold,
            "false_positive_rate": self.false_positive_rate,
            "median": self.median,
            "quantile_95": self.quantile_95,
            "quantile_99": self.quantile_99,
            "maximum": self.maximum,
            "n_trials": self.n_trials,
        }


def _summarise(statistics: np.ndarray, threshold: float, n_trials: int) -> NullSelectionReport:
    return NullSelectionReport(
        statistics=statistics,
        threshold=threshold,
        false_positive_rate=float(np.mean(statistics > threshold)),
        median=float(np.median(statistics)),
        quantile_95=float(np.quantile(statistics, 0.95)),
        quantile_99=float(np.quantile(statistics, 0.99)),
        maximum=float(statistics.max()),
        n_trials=n_trials,
    )


def search_false_positive_rate(
    select: SelectionProcedure,
    params: GbmParameters,
    *,
    n_trials: int,
    n_steps: int,
    seed: int,
    threshold: float,
    initial_price: float = 100.0,
) -> NullSelectionReport:
    """Rate at which ``select`` exceeds ``threshold`` on unpredictable markets.

    Each trial gets its own GBM path and its own child generator, so the trials
    are independent and the whole report is reproducible from ``seed`` alone.

    The returned ``false_positive_rate`` is the probability that this selection
    procedure, applied to data containing no signal, produces a statistic the
    caller would have accepted. It is a property of the *procedure* — its budget,
    its search space, its selection rule — not of any strategy.
    """
    if n_trials < 1:
        raise ValueError("n_trials must be positive.")
    child_seeds = np.random.SeedSequence(seed).spawn(n_trials)
    statistics = np.empty(n_trials, dtype=float)
    for trial, child in enumerate(child_seeds):
        rng = np.random.default_rng(child)
        path = simulate_gbm(
            params,
            n_paths=1,
            n_steps=n_steps,
            seed=int(rng.integers(0, 2**31 - 1)),
            initial_price=initial_price,
        )[0]
        statistics[trial] = float(select(path, rng))
    return _summarise(statistics, threshold, n_trials)


def reversion_detection_power(
    select: SelectionProcedure,
    params: OuParameters,
    *,
    n_trials: int,
    n_steps: int,
    seed: int,
    threshold: float,
) -> NullSelectionReport:
    """The same procedure, run where mean reversion genuinely exists.

    Read together with :func:`search_false_positive_rate`: a procedure whose
    rate here is no higher than on GBM has no power, and its silence on real
    data carries no information.

    ``false_positive_rate`` on the returned report is really a *detection* rate
    here; the field keeps its name so the two reports stay comparable.
    """
    if n_trials < 1:
        raise ValueError("n_trials must be positive.")
    child_seeds = np.random.SeedSequence(seed).spawn(n_trials)
    statistics = np.empty(n_trials, dtype=float)
    for trial, child in enumerate(child_seeds):
        rng = np.random.default_rng(child)
        path = simulate_ou(
            params,
            n_paths=1,
            n_steps=n_steps,
            seed=int(rng.integers(0, 2**31 - 1)),
        )[0]
        statistics[trial] = float(select(path, rng))
    return _summarise(statistics, threshold, n_trials)


@dataclass(frozen=True)
class FirstPassageSummary:
    """Where a simulated path went first, relative to two barriers."""

    upper_first: float
    lower_first: float
    no_touch: float
    mean_bars_to_touch: float
    n_paths: int

    def to_dict(self) -> dict[str, float | int]:
        return {
            "upper_first": self.upper_first,
            "lower_first": self.lower_first,
            "no_touch": self.no_touch,
            "mean_bars_to_touch": self.mean_bars_to_touch,
            "n_paths": self.n_paths,
        }


def first_passage_summary(
    params: GbmParameters,
    *,
    upper: float,
    lower: float,
    horizon: int,
    n_paths: int,
    seed: int,
) -> FirstPassageSummary:
    """Which of two return barriers a GBM path touches first, within ``horizon``.

    ``upper`` and ``lower`` are returns relative to the entry price: ``0.01`` and
    ``-0.01`` are symmetric one-percent barriers. With zero drift and symmetric
    barriers the two touch probabilities are equal, which is the identity a
    triple-barrier labeler must reproduce.

    Touches are evaluated on closing values only, so a barrier crossed and
    reversed inside one bar is not counted — the same convention the labeler
    uses on real bars, which keeps the two comparable.
    """
    if upper <= 0.0 or lower >= 0.0:
        raise ValueError("upper must be positive and lower negative, as returns from entry.")
    if horizon < 1:
        raise ValueError("horizon must be at least one bar.")

    paths = simulate_gbm(params, n_paths=n_paths, n_steps=horizon, seed=seed)
    returns = paths[:, 1:] / paths[:, :1] - 1.0

    hit_upper = returns >= upper
    hit_lower = returns <= lower
    first_upper = np.where(hit_upper.any(axis=1), hit_upper.argmax(axis=1), horizon + 1)
    first_lower = np.where(hit_lower.any(axis=1), hit_lower.argmax(axis=1), horizon + 1)

    upper_wins = first_upper < first_lower
    lower_wins = first_lower < first_upper
    neither = (first_upper > horizon) & (first_lower > horizon)
    touched = np.minimum(first_upper, first_lower)
    touched_bars = touched[~neither]

    return FirstPassageSummary(
        upper_first=float(upper_wins.mean()),
        lower_first=float(lower_wins.mean()),
        no_touch=float(neither.mean()),
        mean_bars_to_touch=float(touched_bars.mean() + 1) if touched_bars.size else float("nan"),
        n_paths=int(n_paths),
    )


def bootstrap_return_paths(
    returns: np.ndarray,
    *,
    n_paths: int,
    n_steps: int,
    block_probability: float,
    seed: int,
) -> np.ndarray:
    """Resample realised returns with the stationary block bootstrap.

    This is the **primary** risk generator. Blocks of consecutive observations
    are kept intact, so volatility clustering and fat tails survive resampling —
    exactly the features that make real drawdowns deeper than a Gaussian model
    predicts.
    """
    r = np.asarray(returns, dtype=float).ravel()
    if r.size < 2:
        raise ValueError("bootstrap_return_paths needs at least two observations.")
    if n_paths < 1 or n_steps < 1:
        raise ValueError("n_paths and n_steps must both be positive.")
    rng = np.random.default_rng(seed)
    # The resampler emits blocks of the same length as the source series, so a
    # longer horizon is built from consecutive draws. The seam between draws is
    # a forced block restart, which the stationary bootstrap already allows.
    n_draws = int(np.ceil(n_steps / r.size))
    index = np.concatenate(
        [
            stationary_bootstrap_indices(
                r.size, n_paths, block_probability=block_probability, rng=rng
            )
            for _ in range(n_draws)
        ],
        axis=1,
    )
    return r[index[:, :n_steps]]


@dataclass(frozen=True)
class DrawdownReport:
    """Distribution of the worst peak-to-trough loss across simulated paths."""

    median_max_drawdown: float
    quantile_95_max_drawdown: float
    worst_max_drawdown: float
    ruin_probability: float
    ruin_threshold: float
    n_paths: int

    def to_dict(self) -> dict[str, float | int]:
        return {
            "median_max_drawdown": self.median_max_drawdown,
            "quantile_95_max_drawdown": self.quantile_95_max_drawdown,
            "worst_max_drawdown": self.worst_max_drawdown,
            "ruin_probability": self.ruin_probability,
            "ruin_threshold": self.ruin_threshold,
            "n_paths": self.n_paths,
        }


def max_drawdowns(return_paths: np.ndarray) -> np.ndarray:
    """Maximum peak-to-trough drawdown of each path, as a positive fraction."""
    paths = np.atleast_2d(np.asarray(return_paths, dtype=float))
    equity = np.cumprod(1.0 + paths, axis=1)
    running_peak = np.maximum.accumulate(equity, axis=1)
    return np.max(1.0 - equity / running_peak, axis=1)


def drawdown_distribution(
    return_paths: np.ndarray, *, ruin_threshold: float = 0.5
) -> DrawdownReport:
    """Summarise drawdown risk, including the probability of ruin.

    ``ruin_threshold`` is the drawdown a funded account cannot survive; the
    default of 0.5 is a placeholder, not a rule. Ruin is a *path* property: an
    account breaching it is closed, so a path that recovers afterwards still
    counts as ruined. That is why ruin is estimated from simulated paths rather
    than from the final return.
    """
    if not 0.0 < ruin_threshold < 1.0:
        raise ValueError("ruin_threshold must lie strictly inside (0, 1).")
    drawdowns = max_drawdowns(return_paths)
    return DrawdownReport(
        median_max_drawdown=float(np.median(drawdowns)),
        quantile_95_max_drawdown=float(np.quantile(drawdowns, 0.95)),
        worst_max_drawdown=float(drawdowns.max()),
        ruin_probability=float(np.mean(drawdowns >= ruin_threshold)),
        ruin_threshold=float(ruin_threshold),
        n_paths=int(drawdowns.size),
    )


def ruin_probability(return_paths: np.ndarray, *, ruin_threshold: float = 0.5) -> float:
    """Fraction of paths whose drawdown ever reaches ``ruin_threshold``."""
    return drawdown_distribution(return_paths, ruin_threshold=ruin_threshold).ruin_probability


def compare_risk_estimates(
    returns: np.ndarray,
    *,
    n_paths: int,
    n_steps: int,
    block_probability: float,
    seed: int,
    ruin_threshold: float = 0.5,
) -> dict[str, DrawdownReport]:
    """Drawdown risk under the block bootstrap and under a GBM fitted to it.

    Returns both reports under the keys ``"block_bootstrap"`` and ``"gbm"``. The
    bootstrap figure is the one to quote; the GBM figure is a sensitivity check.
    The two are expected to differ, and the direction of the difference is the
    point: a Gaussian, serially independent model generally understates the
    drawdown of a fat-tailed, clustered series, so a GBM estimate that looks
    reassuring is evidence about the model, not about the account.
    """
    from perp_lab.stochastic.processes import calibrate_gbm

    r = np.asarray(returns, dtype=float).ravel()
    bootstrap_paths = bootstrap_return_paths(
        r,
        n_paths=n_paths,
        n_steps=n_steps,
        block_probability=block_probability,
        seed=seed,
    )
    params = calibrate_gbm(np.log1p(np.clip(r, -0.999999, None)))
    gbm_prices = simulate_gbm(params, n_paths=n_paths, n_steps=n_steps, seed=seed + 1)
    gbm_returns = gbm_prices[:, 1:] / gbm_prices[:, :-1] - 1.0
    return {
        "block_bootstrap": drawdown_distribution(bootstrap_paths, ruin_threshold=ruin_threshold),
        "gbm": drawdown_distribution(gbm_returns, ruin_threshold=ruin_threshold),
    }
