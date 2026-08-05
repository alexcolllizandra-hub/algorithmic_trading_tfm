"""Extreme-tail dependence between two assets (BTC-ETH stress co-movement).

Ordinary Pearson correlation summarises the *average* co-movement and can hide
the fact that two assets become far more dependent during sharp sell-offs -
precisely when diversification is most needed. These descriptive diagnostics
characterise dependence *in the tails* on the development set:

* :func:`conditional_exceedance` - probability that one asset is in its extreme
  tail given the other is, and the lift versus independence;
* :func:`coexceedance_summary` - joint tail probabilities and conditional
  crash probabilities at several quantiles (e.g. 5% and 1%);
* :func:`normal_vs_stress_correlation` - correlation in calm bars versus in
  market-stress bars;
* :func:`rolling_tail_dependence` - how the lower-tail co-exceedance evolves
  through time.

All quantities are contemporaneous and descriptive; they are not predictive
signals and imply nothing about tradable edges.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import polars as pl

FloatArray = npt.NDArray[np.float64]


def _aligned(
    left: pl.DataFrame,
    right: pl.DataFrame,
    col: str,
    time_col: str,
) -> tuple[pl.Series, FloatArray, FloatArray]:
    """Inner-join two series on ``time_col`` and return times and aligned arrays."""
    joined = (
        left.select(time_col, pl.col(col).alias("a"))
        .join(right.select(time_col, pl.col(col).alias("b")), on=time_col, how="inner")
        .drop_nulls()
        .sort(time_col)
    )
    return joined[time_col], joined["a"].to_numpy(), joined["b"].to_numpy()


def conditional_exceedance(
    left: pl.DataFrame,
    right: pl.DataFrame,
    *,
    col: str = "log_return",
    time_col: str = "open_time",
    quantile: float = 0.05,
    tail: str = "lower",
) -> dict[str, float]:
    """Conditional tail-exceedance probabilities between ``left`` and ``right``.

    For the ``lower`` (crash) or ``upper`` tail at ``quantile`` this returns the
    marginal exceedance rates, the joint probability, both conditional
    probabilities ``P(right extreme | left extreme)`` and vice versa, and the
    lift of the conditional probability versus independence (``= quantile``).
    ``left`` is treated as the conditioning asset for ``p_right_given_left``.
    """
    if tail not in {"lower", "upper"}:
        raise ValueError(f"tail must be 'lower' or 'upper', got {tail!r}.")
    _, a, b = _aligned(left, right, col, time_col)
    n = a.size
    if n < 20:
        return {}
    if tail == "lower":
        thr_a, thr_b = np.quantile(a, quantile), np.quantile(b, quantile)
        ex_a, ex_b = a <= thr_a, b <= thr_b
    else:
        thr_a, thr_b = np.quantile(a, 1 - quantile), np.quantile(b, 1 - quantile)
        ex_a, ex_b = a >= thr_a, b >= thr_b
    p_a = float(np.mean(ex_a))
    p_b = float(np.mean(ex_b))
    joint = float(np.mean(ex_a & ex_b))
    p_b_given_a = joint / p_a if p_a > 0 else float("nan")
    p_a_given_b = joint / p_b if p_b > 0 else float("nan")
    return {
        "n": float(n),
        "quantile": float(quantile),
        "p_left": p_a,
        "p_right": p_b,
        "joint": joint,
        "p_right_given_left": p_b_given_a,
        "p_left_given_right": p_a_given_b,
        "independence": float(quantile),
        "lift": p_b_given_a / quantile if quantile > 0 else float("nan"),
    }


def coexceedance_summary(
    left: pl.DataFrame,
    right: pl.DataFrame,
    *,
    col: str = "log_return",
    time_col: str = "open_time",
    quantiles: tuple[float, ...] = (0.05, 0.01),
) -> pl.DataFrame:
    """Joint and conditional tail dependence at several quantiles.

    One row per quantile with the lower/upper joint probabilities, their
    exceedance ratios versus independence (``joint / quantile**2``) and the
    lower-tail conditional crash probabilities in both directions.
    """
    schema = {
        "quantile": pl.Float64,
        "n": pl.Int64,
        "joint_lower": pl.Float64,
        "joint_upper": pl.Float64,
        "lower_ratio": pl.Float64,
        "upper_ratio": pl.Float64,
        "p_right_given_left_lower": pl.Float64,
        "p_left_given_right_lower": pl.Float64,
    }
    _, a, b = _aligned(left, right, col, time_col)
    n = a.size
    if n < 20:
        return pl.DataFrame(schema=schema)
    rows: list[dict[str, object]] = []
    for q in quantiles:
        lo_a, lo_b = np.quantile(a, q), np.quantile(b, q)
        hi_a, hi_b = np.quantile(a, 1 - q), np.quantile(b, 1 - q)
        low_a, low_b = a <= lo_a, b <= lo_b
        joint_lower = float(np.mean(low_a & low_b))
        joint_upper = float(np.mean((a >= hi_a) & (b >= hi_b)))
        indep = q * q
        p_left = float(np.mean(low_a))
        p_right = float(np.mean(low_b))
        rows.append(
            {
                "quantile": float(q),
                "n": int(n),
                "joint_lower": joint_lower,
                "joint_upper": joint_upper,
                "lower_ratio": joint_lower / indep if indep > 0 else float("nan"),
                "upper_ratio": joint_upper / indep if indep > 0 else float("nan"),
                "p_right_given_left_lower": joint_lower / p_left if p_left > 0 else float("nan"),
                "p_left_given_right_lower": joint_lower / p_right if p_right > 0 else float("nan"),
            }
        )
    return pl.DataFrame(rows, schema=schema)


def normal_vs_stress_correlation(
    left: pl.DataFrame,
    right: pl.DataFrame,
    *,
    col: str = "log_return",
    time_col: str = "open_time",
    stress_quantile: float = 0.10,
) -> dict[str, float]:
    """Pearson correlation in calm bars versus market-stress bars.

    A bar is flagged as *stress* when either asset's return is at or below its
    ``stress_quantile`` lower quantile; the remaining bars are *calm*.
    ``corr_stress_left`` conditions on the ``left`` (conditioning) asset only.
    """
    _, a, b = _aligned(left, right, col, time_col)
    n = a.size
    if n < 30:
        return {}
    thr_a = np.quantile(a, stress_quantile)
    thr_b = np.quantile(b, stress_quantile)
    stress = (a <= thr_a) | (b <= thr_b)
    calm = ~stress
    left_stress = a <= thr_a

    def _corr(mask: npt.NDArray[np.bool_]) -> float:
        if int(mask.sum()) < 3:
            return float("nan")
        return float(np.corrcoef(a[mask], b[mask])[0, 1])

    return {
        "n_all": float(n),
        "stress_quantile": float(stress_quantile),
        "corr_all": float(np.corrcoef(a, b)[0, 1]),
        "corr_calm": _corr(calm),
        "corr_stress": _corr(stress),
        "corr_stress_left": _corr(left_stress),
        "n_stress": float(int(stress.sum())),
        "n_calm": float(int(calm.sum())),
    }


def rolling_tail_dependence(
    left: pl.DataFrame,
    right: pl.DataFrame,
    *,
    col: str = "log_return",
    time_col: str = "open_time",
    window: int = 2160,
    step: int = 720,
    quantile: float = 0.05,
) -> pl.DataFrame:
    """Evolution of lower-tail co-exceedance over stepped rolling windows.

    Within each window of ``window`` bars (advanced by ``step``) the lower
    ``quantile`` thresholds are recomputed *inside the window*, so the ratio
    tracks the dependence structure rather than the changing volatility level.
    Returns ``window_end``, ``n``, ``joint_lower`` and ``lower_ratio`` (joint
    versus the ``quantile**2`` independence baseline) at each window end.
    """
    times, a, b = _aligned(left, right, col, time_col)
    n = a.size
    schema = {
        "window_end": times.dtype,
        "n": pl.Int64,
        "joint_lower": pl.Float64,
        "lower_ratio": pl.Float64,
    }
    if window < 20 or n < window:
        return pl.DataFrame(schema=schema)
    indep = quantile * quantile
    rows: list[dict[str, object]] = []
    end_times = times.to_list()
    for start in range(0, n - window + 1, step):
        stop = start + window
        wa, wb = a[start:stop], b[start:stop]
        lo_a, lo_b = np.quantile(wa, quantile), np.quantile(wb, quantile)
        joint_lower = float(np.mean((wa <= lo_a) & (wb <= lo_b)))
        rows.append(
            {
                "window_end": end_times[stop - 1],
                "n": int(window),
                "joint_lower": joint_lower,
                "lower_ratio": joint_lower / indep if indep > 0 else float("nan"),
            }
        )
    return pl.DataFrame(rows, schema=schema)
