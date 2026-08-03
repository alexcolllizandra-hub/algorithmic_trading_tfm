"""Net-of-cost performance metrics for a per-bar strategy return series."""

from __future__ import annotations

import numpy as np

from perp_lab.utils.timeutils import TIMEFRAME_TO_MS

_MS_PER_YEAR_365 = 365 * 24 * 60 * 60 * 1000


def bars_per_year(timeframe: str, days_per_year: int = 365) -> float:
    """Number of bars in a 24/7 year for the given timeframe."""
    step_ms = TIMEFRAME_TO_MS[timeframe]
    return (days_per_year / 365) * _MS_PER_YEAR_365 / step_ms


def performance_metrics(
    net_returns: np.ndarray,
    *,
    timeframe: str,
    positions: np.ndarray | None = None,
    turnover: np.ndarray | None = None,
    days_per_year: int = 365,
) -> dict[str, float]:
    """Compute net-of-cost performance metrics from per-bar simple returns.

    ``net_returns`` are simple (arithmetic) per-bar returns already net of
    costs. ``positions`` and ``turnover`` (both per-bar, aligned) enable
    exposure, hit-rate and trade-count metrics. All annualisation uses the 24/7
    365-day convention.
    """
    r = np.asarray(net_returns, dtype=float)
    r = r[np.isfinite(r)]
    n = int(r.size)
    if n == 0:
        return {"n_bars": 0.0}

    bpy = bars_per_year(timeframe, days_per_year)
    total_return = float(np.prod(1.0 + r) - 1.0)
    mean = float(np.mean(r))
    std = float(np.std(r, ddof=1)) if n > 1 else 0.0

    equity = np.cumprod(1.0 + r)
    running_peak = np.maximum.accumulate(equity)
    drawdown = equity / running_peak - 1.0
    max_dd = float(drawdown.min()) if n else 0.0

    ann_vol = std * float(np.sqrt(bpy))
    ann_return = (1.0 + total_return) ** (bpy / n) - 1.0 if total_return > -1.0 else -1.0
    sharpe = (mean / std) * float(np.sqrt(bpy)) if std > 0 else 0.0

    downside = r[r < 0]
    dstd = float(np.std(downside, ddof=1)) if downside.size > 1 else 0.0
    sortino = (mean / dstd) * float(np.sqrt(bpy)) if dstd > 0 else 0.0

    calmar = ann_return / abs(max_dd) if max_dd < 0 else 0.0

    metrics = {
        "n_bars": float(n),
        "total_return": total_return,
        "ann_return": float(ann_return),
        "ann_volatility": ann_vol,
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "max_drawdown": max_dd,
        "calmar": float(calmar),
    }

    if positions is not None:
        pos = np.asarray(positions, dtype=float)
        active = pos != 0.0
        metrics["exposure"] = float(np.mean(active)) if pos.size else 0.0
        active_returns = r[active[: r.size]] if pos.size >= r.size else r
        metrics["hit_rate"] = float(np.mean(active_returns > 0)) if active_returns.size else 0.0
    if turnover is not None:
        tvr = np.asarray(turnover, dtype=float)
        metrics["turnover"] = float(np.nansum(tvr))
        metrics["n_trades"] = float(int(np.count_nonzero(tvr > 0)))
    return metrics
