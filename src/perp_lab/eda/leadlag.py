"""Cross-asset lead-lag cross-correlation and tail co-exceedance.

These are strictly *descriptive* diagnostics. A non-zero cross-correlation at a
positive lag is NOT evidence of a causal or tradable lead-lag relationship; it
can arise from asynchronous trading, common factors or microstructure noise.
The notebooks must interpret these results with that caution.
"""

from __future__ import annotations

import numpy as np
import polars as pl


def _aligned_pair(
    left: pl.DataFrame,
    right: pl.DataFrame,
    col: str,
    time_col: str,
) -> tuple[np.ndarray, np.ndarray]:
    joined = (
        left.select(time_col, pl.col(col).alias("a"))
        .join(right.select(time_col, pl.col(col).alias("b")), on=time_col, how="inner")
        .drop_nulls()
        .sort(time_col)
    )
    return joined["a"].to_numpy(), joined["b"].to_numpy()


def cross_correlation(
    left: pl.DataFrame,
    right: pl.DataFrame,
    col: str = "log_return",
    time_col: str = "open_time",
    max_lag: int = 12,
) -> pl.DataFrame:
    """Cross-correlation of ``left`` vs ``right`` for lags in ``[-max_lag, max_lag]``.

    Convention: at lag ``k > 0`` we correlate ``left[t]`` with ``right[t - k]``,
    i.e. a positive-lag peak means ``right``'s past co-moves with ``left``'s
    present (``right`` "leads"). Returns columns ``lag`` and ``cross_corr``.
    """
    a, b = _aligned_pair(left, right, col, time_col)
    n = a.size
    schema = {"lag": pl.Int64, "cross_corr": pl.Float64}
    if n < 3:
        return pl.DataFrame(schema=schema)

    a = (a - a.mean()) / (a.std(ddof=0) or 1.0)
    b = (b - b.mean()) / (b.std(ddof=0) or 1.0)

    lags = list(range(-max_lag, max_lag + 1))
    corrs: list[float] = []
    for k in lags:
        if k >= 0:
            x, y = a[k:], b[: n - k] if k > 0 else b
        else:
            x, y = a[: n + k], b[-k:]
        m = min(x.size, y.size)
        corrs.append(float(np.mean(x[:m] * y[:m])) if m > 1 else float("nan"))
    return pl.DataFrame({"lag": lags, "cross_corr": corrs})


def peak_lag(cc: pl.DataFrame) -> dict[str, float]:
    """Return the lag and value of the maximum absolute cross-correlation."""
    if cc.height == 0:
        return {}
    idx = int(cc.select(pl.col("cross_corr").abs().arg_max()).item())
    row = cc.row(idx, named=True)
    return {"lag": float(row["lag"]), "cross_corr": float(row["cross_corr"])}


def tail_coexceedance(
    left: pl.DataFrame,
    right: pl.DataFrame,
    col: str = "log_return",
    time_col: str = "open_time",
    quantile: float = 0.05,
) -> dict[str, float]:
    """Joint tail behaviour of two return series on their shared index.

    Reports, for the lower and upper ``quantile`` tails, the empirical
    probability that both assets are jointly in the tail and the corresponding
    exceedance ratio versus independence (``joint / quantile**2``). Under
    independence the joint probability is ``quantile**2`` so the ratio is 1; a
    ratio well above 1 indicates tail co-movement stronger than independence.
    """
    a, b = _aligned_pair(left, right, col, time_col)
    n = a.size
    if n < 20:
        return {}

    lo_a, lo_b = np.quantile(a, quantile), np.quantile(b, quantile)
    hi_a, hi_b = np.quantile(a, 1 - quantile), np.quantile(b, 1 - quantile)

    joint_lower = float(np.mean((a <= lo_a) & (b <= lo_b)))
    joint_upper = float(np.mean((a >= hi_a) & (b >= hi_b)))
    independence = quantile * quantile
    return {
        "n": float(n),
        "quantile": quantile,
        "joint_lower": joint_lower,
        "joint_upper": joint_upper,
        "lower_exceedance_ratio": joint_lower / independence if independence else float("nan"),
        "upper_exceedance_ratio": joint_upper / independence if independence else float("nan"),
    }
