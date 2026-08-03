"""Historical (non-parametric) tail-risk measures: VaR and Expected Shortfall.

These are *descriptive, in-sample historical* risk estimates on the development
data, not forward-looking guarantees. We use the order-statistic definition so
results are exactly reproducible and manually verifiable:

- ``k = floor(level * n)`` (at least 1) worst observations define the tail.
- ``VaR`` is the ``k``-th smallest return (the tail threshold).
- ``ES`` is the mean of the ``k`` worst returns.

Returns are expressed as signed returns, so losses are negative; a VaR of
``-0.03`` means "the loss threshold at this level is -3%".
"""

from __future__ import annotations

import numpy as np
import polars as pl


def historical_var_es(values: np.ndarray, level: float = 0.05) -> dict[str, float]:
    """Return historical VaR and ES for a 1-D return array at ``level``."""
    clean = np.asarray(values, dtype=float)
    clean = clean[~np.isnan(clean)]
    n = clean.size
    if n == 0 or not (0.0 < level < 1.0):
        return {}
    k = max(1, int(np.floor(level * n)))
    ordered = np.sort(clean)
    tail = ordered[:k]
    return {
        "level": level,
        "n": float(n),
        "k": float(k),
        "var": float(ordered[k - 1]),
        "es": float(np.mean(tail)),
    }


def tail_risk_table(
    df: pl.DataFrame,
    col: str = "log_return",
    levels: tuple[float, ...] = (0.01, 0.05),
) -> pl.DataFrame:
    """Historical VaR/ES at several levels for a return column (nulls dropped)."""
    values = df.select(pl.col(col)).drop_nulls().to_series().to_numpy()
    rows = [historical_var_es(values, level) for level in levels]
    rows = [r for r in rows if r]
    schema = {
        "level": pl.Float64,
        "n": pl.Float64,
        "k": pl.Float64,
        "var": pl.Float64,
        "es": pl.Float64,
    }
    if not rows:
        return pl.DataFrame(schema=schema)
    return pl.DataFrame(rows, schema=schema)


def tail_asymmetry(
    df: pl.DataFrame, col: str = "log_return", level: float = 0.05
) -> dict[str, float]:
    """Compare the magnitude of the lower and upper ``level`` tails.

    Returns the lower-tail ES (losses), the symmetric upper-tail mean (gains)
    and their absolute ratio; a ratio > 1 means the loss tail is heavier.
    """
    values = df.select(pl.col(col)).drop_nulls().to_series().to_numpy()
    n = values.size
    if n == 0 or not (0.0 < level < 1.0):
        return {}
    k = max(1, int(np.floor(level * n)))
    ordered = np.sort(values)
    lower = float(np.mean(ordered[:k]))
    upper = float(np.mean(ordered[-k:]))
    ratio = abs(lower) / abs(upper) if upper != 0 else float("nan")
    return {"level": level, "lower_es": lower, "upper_mean": upper, "abs_ratio": ratio}
