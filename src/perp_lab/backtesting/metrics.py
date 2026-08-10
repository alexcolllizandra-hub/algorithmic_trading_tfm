"""Net-of-cost performance metrics for a per-bar strategy return series."""

from __future__ import annotations

import numpy as np

from perp_lab.utils.timeutils import TIMEFRAME_TO_MS

_MS_PER_YEAR_365 = 365 * 24 * 60 * 60 * 1000


def bars_per_year(timeframe: str, days_per_year: int = 365) -> float:
    """Number of bars in a 24/7 year for the given timeframe."""
    step_ms = TIMEFRAME_TO_MS[timeframe]
    return (days_per_year / 365) * _MS_PER_YEAR_365 / step_ms


def _tail_risk(r: np.ndarray, levels: tuple[float, ...] = (0.95, 0.99)) -> dict[str, float]:
    """Empirical VaR / Expected Shortfall on the per-bar net return distribution.

    Both are reported as signed returns (negative = loss), estimated from the
    realised sample without assuming a distributional form. Expected Shortfall is
    the mean of the returns at or below the VaR quantile.
    """
    out: dict[str, float] = {}
    if r.size < 2:
        return out
    for level in levels:
        tag = round(level * 100)
        var = float(np.quantile(r, 1.0 - level))
        tail = r[r <= var]
        out[f"var_{tag}"] = var
        out[f"expected_shortfall_{tag}"] = float(np.mean(tail)) if tail.size else var
    mean = float(np.mean(r))
    sd = float(np.std(r, ddof=1))
    if sd > 0:
        z = (r - mean) / sd
        out["skewness"] = float(np.mean(z**3))
        out["excess_kurtosis"] = float(np.mean(z**4) - 3.0)
    return out


def _drawdown_shape(drawdown: np.ndarray) -> dict[str, float]:
    """How long the strategy spends under water, not just how deep it goes."""
    if drawdown.size == 0:
        return {}
    under = drawdown < 0
    longest = current = 0
    for flag in under:
        current = current + 1 if flag else 0
        longest = max(longest, current)
    return {
        "time_in_drawdown": float(np.mean(under)),
        "max_drawdown_duration_bars": float(longest),
        # Ulcer index: RMS drawdown, penalising long shallow pain as well as depth.
        "ulcer_index": float(np.sqrt(np.mean(drawdown**2))),
    }


def _streaks(r: np.ndarray) -> dict[str, float]:
    """Longest consecutive runs of positive / negative bar returns."""
    if r.size == 0:
        return {}
    best_win = best_loss = cur_win = cur_loss = 0
    for value in r:
        if value > 0:
            cur_win, cur_loss = cur_win + 1, 0
        elif value < 0:
            cur_win, cur_loss = 0, cur_loss + 1
        else:
            cur_win = cur_loss = 0
        best_win, best_loss = max(best_win, cur_win), max(best_loss, cur_loss)
    return {"longest_win_streak": float(best_win), "longest_loss_streak": float(best_loss)}


def trade_metrics(net_returns: np.ndarray, durations: np.ndarray | None = None) -> dict[str, float]:
    """Trade-level statistics from per-trade net returns.

    Separate from :func:`performance_metrics` because these are defined on closed
    round-trip trades, not on per-bar returns. ``profit_factor`` is gross profit
    over gross loss; ``expectancy`` is the mean net return per trade; ``payoff``
    is the average win divided by the average loss.
    """
    t = np.asarray(net_returns, dtype=float)
    t = t[np.isfinite(t)]
    if t.size == 0:
        return {"n_trades_closed": 0.0}

    wins, losses = t[t > 0], t[t < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(-losses.sum())
    avg_win = float(wins.mean()) if wins.size else 0.0
    avg_loss = float(-losses.mean()) if losses.size else 0.0

    out = {
        "n_trades_closed": float(t.size),
        "trade_hit_rate": float(wins.size / t.size),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        # Undefined with no losing trades: report inf rather than a silent zero.
        "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else float("inf"),
        "expectancy": float(t.mean()),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "payoff_ratio": (avg_win / avg_loss) if avg_loss > 0 else float("inf"),
        "best_trade": float(t.max()),
        "worst_trade": float(t.min()),
    }
    # Concentration: how much of the gross profit sits in the five best trades.
    if wins.size:
        top = np.sort(wins)[::-1][:5]
        out["top5_profit_share"] = float(top.sum() / gross_profit) if gross_profit > 0 else 0.0
    if durations is not None:
        d = np.asarray(durations, dtype=float)
        d = d[np.isfinite(d)]
        if d.size:
            out["mean_duration_bars"] = float(d.mean())
            out["median_duration_bars"] = float(np.median(d))
    return out


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
        "downside_volatility": dstd * float(np.sqrt(bpy)),
        **_tail_risk(r),
        **_drawdown_shape(drawdown),
        **_streaks(r),
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
