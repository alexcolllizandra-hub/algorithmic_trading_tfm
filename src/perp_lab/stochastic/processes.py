"""Synthetic price processes: geometric Brownian motion and Ornstein-Uhlenbeck.

These are **benchmarks and test instruments, never strategies.** Nothing in this
module produces a trading signal, and no result computed here may be reported as
evidence that a strategy predicts anything.

What each process is for
------------------------
**GBM** generates markets in which, by construction, *nothing is predictable*:
increments are independent. Its purpose is to answer "how good would my search
look if there were nothing to find?" — see
:mod:`perp_lab.stochastic.benchmarks`.

**Ornstein-Uhlenbeck** generates a market in which mean reversion *genuinely
exists*, with a known speed. Its purpose is the opposite check: a pipeline that
cannot find reversion in an OU path is broken, and any failure to find it in real
data would then be uninformative. It is a test of the instrument, not a claim
about markets.

What GBM is not
---------------
GBM is a poor description of crypto returns and must never be used to argue that
a strategy is safe. It assumes:

* **constant volatility** — real volatility clusters and moves by an order of
  magnitude between regimes;
* **Gaussian returns** — real returns are fat tailed, so GBM understates the
  frequency of large moves and therefore understates drawdown and ruin;
* **no jumps** — liquidations, exchange outages and macro releases produce gaps
  that a diffusion cannot generate;
* **no volatility clustering** — losing days are independent under GBM, whereas
  real drawdowns are made of consecutive bad days, which is exactly what makes
  them deep;
* **a drift that cannot be estimated** — the standard error of the mean scales
  as ``sigma / sqrt(n)``, so over any realistic sample the estimated drift is
  dominated by noise. :attr:`GbmParameters.drift_standard_error` reports it so
  the point stays quantitative rather than rhetorical.

Consequently, for drawdown and ruin questions the **stationary block bootstrap
of realised returns is the primary method** because it preserves fat tails and
serial dependence; GBM is a sensitivity analysis around it.

Causality
---------
:func:`calibrate_gbm` and :func:`calibrate_ou` fit to whatever sample they are
given and take no view on where it came from. Callers must pass **training data
only**; :func:`calibrate_gbm` records the window it saw so a run's artifacts can
be audited against the fold geometry.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# 24/7 markets: 365 days, not 252 trading days.
BARS_PER_YEAR_1H = 365 * 24
BARS_PER_YEAR_15M = 365 * 24 * 4
BARS_PER_YEAR_5M = 365 * 24 * 12


@dataclass(frozen=True)
class GbmParameters:
    """Per-bar log-return drift and volatility of a geometric Brownian motion.

    The parameterisation is deliberately in *log-return* space rather than in
    the ``mu``/``sigma`` of the stochastic differential equation, because the
    exact discretisation of GBM is simply "log returns are i.i.d. normal". That
    removes the Euler discretisation error and the recurring sign confusion over
    the ``- sigma^2 / 2`` Ito correction.
    """

    drift: float
    volatility: float
    n_observations: int

    def __post_init__(self) -> None:
        if self.volatility < 0.0:
            raise ValueError("volatility must be non-negative.")
        if self.n_observations < 2:
            raise ValueError("GBM calibration needs at least two observations.")

    @property
    def drift_standard_error(self) -> float:
        """Standard error of the estimated drift, ``sigma / sqrt(n)``.

        Compare it with :attr:`drift`. On any sample this project can obtain the
        ratio is small, which is the precise sense in which the drift of a GBM
        fitted to market data is not knowable.
        """
        return float(self.volatility / np.sqrt(self.n_observations))

    @property
    def drift_t_statistic(self) -> float:
        """``drift / drift_standard_error``; near zero means the drift is noise."""
        se = self.drift_standard_error
        return float(self.drift / se) if se > 0 else 0.0

    def annualised_volatility(self, bars_per_year: int) -> float:
        if bars_per_year < 1:
            raise ValueError("bars_per_year must be positive.")
        return float(self.volatility * np.sqrt(bars_per_year))

    def to_dict(self) -> dict[str, float | int]:
        return {
            "drift": self.drift,
            "volatility": self.volatility,
            "n_observations": self.n_observations,
            "drift_standard_error": self.drift_standard_error,
            "drift_t_statistic": self.drift_t_statistic,
        }


def calibrate_gbm(log_returns: np.ndarray) -> GbmParameters:
    """Fit GBM to a sample of per-bar log returns.

    **Pass training data only.** This function cannot tell a train slice from a
    test slice, so the causality guarantee lives with the caller.
    """
    r = np.asarray(log_returns, dtype=float).ravel()
    r = r[np.isfinite(r)]
    if r.size < 2:
        raise ValueError("GBM calibration needs at least two finite log returns.")
    return GbmParameters(
        drift=float(r.mean()),
        volatility=float(r.std(ddof=1)),
        n_observations=int(r.size),
    )


def simulate_gbm(
    params: GbmParameters,
    *,
    n_paths: int,
    n_steps: int,
    seed: int,
    initial_price: float = 100.0,
) -> np.ndarray:
    """Simulate ``n_paths`` price paths of ``n_steps`` bars each.

    Returns an array of shape ``(n_paths, n_steps + 1)`` whose first column is
    ``initial_price``. Uses the exact discretisation, so the result is a GBM at
    every step size rather than an Euler approximation of one.
    """
    if n_paths < 1 or n_steps < 1:
        raise ValueError("n_paths and n_steps must both be positive.")
    if initial_price <= 0.0:
        raise ValueError("initial_price must be positive.")
    rng = np.random.default_rng(seed)
    increments = rng.normal(params.drift, params.volatility, size=(n_paths, n_steps))
    log_path = np.concatenate(
        [np.zeros((n_paths, 1)), np.cumsum(increments, axis=1)],
        axis=1,
    )
    return initial_price * np.exp(log_path)


@dataclass(frozen=True)
class OuParameters:
    """Ornstein-Uhlenbeck parameters in discrete time.

    ``kappa`` is the per-bar reversion speed, ``theta`` the long-run level and
    ``sigma`` the per-bar shock size. ``half_life`` is the more interpretable
    quantity and is what a strategy's lookback should be compared against.
    """

    kappa: float
    theta: float
    sigma: float

    def __post_init__(self) -> None:
        if self.kappa <= 0.0:
            raise ValueError("kappa must be positive; a non-reverting series is not OU.")
        if self.sigma < 0.0:
            raise ValueError("sigma must be non-negative.")

    @property
    def half_life(self) -> float:
        """Bars for a deviation to decay by half."""
        return float(np.log(2.0) / self.kappa)

    @property
    def stationary_sd(self) -> float:
        """Standard deviation of the stationary distribution."""
        return float(self.sigma / np.sqrt(2.0 * self.kappa))

    def to_dict(self) -> dict[str, float]:
        return {
            "kappa": self.kappa,
            "theta": self.theta,
            "sigma": self.sigma,
            "half_life": self.half_life,
            "stationary_sd": self.stationary_sd,
        }


def simulate_ou(
    params: OuParameters,
    *,
    n_paths: int,
    n_steps: int,
    seed: int,
    initial_value: float | None = None,
) -> np.ndarray:
    """Simulate an OU process exactly, shape ``(n_paths, n_steps + 1)``.

    The transition is sampled from its exact Gaussian law rather than stepped
    with Euler, so the simulated half-life matches ``params.half_life`` at any
    step size. Paths start from the stationary distribution unless
    ``initial_value`` is given, which avoids a burn-in transient that would
    otherwise look like a trend.
    """
    if n_paths < 1 or n_steps < 1:
        raise ValueError("n_paths and n_steps must both be positive.")
    rng = np.random.default_rng(seed)
    decay = float(np.exp(-params.kappa))
    shock_sd = float(params.sigma * np.sqrt((1.0 - decay**2) / (2.0 * params.kappa)))

    out = np.empty((n_paths, n_steps + 1), dtype=float)
    if initial_value is None:
        out[:, 0] = rng.normal(params.theta, params.stationary_sd, size=n_paths)
    else:
        out[:, 0] = float(initial_value)
    shocks = rng.normal(0.0, shock_sd, size=(n_paths, n_steps))
    for t in range(n_steps):
        out[:, t + 1] = params.theta + (out[:, t] - params.theta) * decay + shocks[:, t]
    return out


def calibrate_ou(series: np.ndarray, *, max_half_life_fraction: float = 0.1) -> OuParameters:
    """Fit an OU process by ordinary least squares on the AR(1) representation.

    ``x[t+1] = a + b x[t] + e`` with ``b = exp(-kappa)``, so ``kappa = -log(b)``
    and ``theta = a / (1 - b)``.

    Two refusals, both deliberate. ``b`` outside ``(0, 1)`` is not a
    mean-reverting process at all. And a fitted half-life longer than
    ``max_half_life_fraction`` of the sample is **not identifiable**: a random
    walk regressed on its own lag yields ``b`` slightly below one — the
    well-known downward bias of the least-squares autoregressive estimator — so
    without this guard a pure random walk calibrates happily as an OU process
    with an enormous half-life. The default of 0.1 demands roughly ten reversion
    cycles inside the sample.

    **This guard is necessary, not sufficient.** It is not a unit-root test. On
    5 000-step random walks it refuses about three quarters of realisations;
    the rest happen to produce a short enough fitted half-life to pass. A caller
    who needs to establish that a real series is stationary must run a proper
    test and must not treat a successful calibration as evidence of reversion.

    **Pass training data only.**
    """
    x = np.asarray(series, dtype=float).ravel()
    x = x[np.isfinite(x)]
    if x.size < 3:
        raise ValueError("OU calibration needs at least three finite observations.")

    current, following = x[:-1], x[1:]
    design = np.column_stack([np.ones_like(current), current])
    coefficients, *_ = np.linalg.lstsq(design, following, rcond=None)
    intercept, slope = float(coefficients[0]), float(coefficients[1])
    if not 0.0 < slope < 1.0:
        raise ValueError(
            f"The AR(1) slope is {slope:.4f}, outside (0, 1): this series is not a "
            "mean-reverting OU process."
        )

    kappa = -float(np.log(slope))
    half_life = float(np.log(2.0) / kappa)
    if half_life > max_half_life_fraction * x.size:
        raise ValueError(
            f"The fitted half-life is {half_life:.1f} bars on a sample of {x.size}: "
            "reversion this slow is not identifiable from this much data and is "
            "indistinguishable from a random walk."
        )

    residuals = following - design @ coefficients
    residual_sd = float(np.sqrt(np.sum(residuals**2) / max(residuals.size - 2, 1)))
    sigma = residual_sd * np.sqrt(2.0 * kappa / (1.0 - slope**2))
    return OuParameters(kappa=kappa, theta=intercept / (1.0 - slope), sigma=float(sigma))
