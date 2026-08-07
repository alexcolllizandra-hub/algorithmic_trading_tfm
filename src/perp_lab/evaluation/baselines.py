"""Evaluate the reference baselines on exactly the bars a strategy was tested on.

The concatenated out-of-sample ledger already carries everything needed: the
market return of each holding interval (``oo_return``), the execution price
(``open``) and the run's realised cost rate. Re-evaluating baselines from that
ledger guarantees they see the *same* bars, the *same* costs and the *same*
execution convention as the searched strategy, which is what makes the comparison
fair. It also avoids re-loading market data, so no path exists by which this
analysis could reach the frozen holdout.

Walk-forward test windows tile the development period without gaps or overlaps,
so the concatenated execution-price series is a genuine contiguous series and
trailing indicators computed on it are well defined (apart from a documented
warm-up at the very start).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from perp_lab.backtesting.metrics import performance_metrics
from perp_lab.evaluation.robustness import reconstruct_bar_returns


def realised_cost_rate(ledger: pl.DataFrame) -> float:
    """Cost per unit of turnover actually charged in the run (fees + slippage)."""
    turnover = float(np.abs(np.diff(ledger["position"].to_numpy(), prepend=0.0)).sum())
    if turnover <= 0:
        return 0.0
    cost = float(ledger["fee"].cast(pl.Float64).sum()) + float(
        ledger["slippage"].cast(pl.Float64).sum()
    )
    return cost / turnover


def _evaluate(
    positions: np.ndarray,
    market: np.ndarray,
    *,
    timeframe: str,
    cost_rate: float,
    funding_per_unit: np.ndarray,
    days_per_year: int,
) -> dict[str, float]:
    turnover = np.abs(np.diff(positions, prepend=0.0))
    net = positions * market - turnover * cost_rate - positions * funding_per_unit
    metrics = performance_metrics(
        net,
        timeframe=timeframe,
        positions=positions,
        turnover=turnover,
        days_per_year=days_per_year,
    )
    metrics["total_cost"] = float((turnover * cost_rate).sum())
    metrics["total_funding"] = float((positions * funding_per_unit).sum())
    return metrics


def baselines_on_ledger(
    ledger: pl.DataFrame,
    *,
    timeframe: str,
    seed: int = 42,
    days_per_year: int = 365,
) -> dict[str, dict[str, float]]:
    """Evaluate the fixed baseline suite over the ledger's own bars.

    Every baseline pays the run's realised cost rate and the same per-unit funding,
    so none of them is advantaged by a cheaper execution assumption. Parameters are
    fixed in :mod:`perp_lab.strategies.baselines` and are never tuned here.
    """
    market = reconstruct_bar_returns(ledger)
    n = market.size
    position = ledger["position"].cast(pl.Float64).to_numpy().astype(float)
    funding_per_unit = np.divide(
        ledger["funding"].cast(pl.Float64).to_numpy(),
        position,
        out=np.zeros_like(position),
        where=position != 0,
    )
    cost_rate = realised_cost_rate(ledger)
    price = ledger["execution_price"].cast(pl.Float64).to_numpy().astype(float)

    def run(positions: np.ndarray) -> dict[str, float]:
        return _evaluate(
            positions.astype(float),
            market,
            timeframe=timeframe,
            cost_rate=cost_rate,
            funding_per_unit=funding_per_unit,
            days_per_year=days_per_year,
        )

    def sma(window: int) -> np.ndarray:
        series = pl.Series(price).rolling_mean(window)
        return series.to_numpy().astype(float)

    out: dict[str, dict[str, float]] = {}
    out["flat"] = run(np.zeros(n))
    out["always_long"] = run(np.ones(n))

    fast, slow = sma(24), sma(96)
    cross = np.where(fast > slow, 1.0, np.where(fast < slow, -1.0, 0.0))
    out["ma_crossover_24_96"] = run(np.nan_to_num(cross, nan=0.0))

    # Trailing 24-bar momentum on the same price series.
    mom = np.full(n, np.nan)
    if n > 24:
        mom[24:] = price[24:] / price[:-24] - 1.0
    out["momentum_24"] = run(np.nan_to_num(np.sign(mom), nan=0.0))

    roll = pl.Series(price)
    z = ((roll - roll.rolling_mean(48)) / roll.rolling_std(48)).to_numpy().astype(float)
    fade = np.where(z >= 2.0, -1.0, np.where(z <= -2.0, 1.0, 0.0))
    out["mean_reversion_z48"] = run(np.nan_to_num(fade, nan=0.0))

    rng = np.random.default_rng(seed)
    active = rng.random(n) < 0.5
    sign = np.where(rng.random(n) < 0.5, -1.0, 1.0)
    out["random_entry"] = run(np.where(active, sign, 0.0))

    return out


def strategy_versus_baselines(
    ledger: pl.DataFrame,
    *,
    timeframe: str,
    seed: int = 42,
    days_per_year: int = 365,
) -> dict[str, Any]:
    """The searched strategy's own OOS metrics alongside every baseline."""
    strategy = performance_metrics(
        ledger["net_return"].cast(pl.Float64).to_numpy(),
        timeframe=timeframe,
        positions=ledger["position"].cast(pl.Float64).to_numpy(),
        turnover=(
            ledger["turnover"].cast(pl.Float64).to_numpy() if "turnover" in ledger.columns else None
        ),
        days_per_year=days_per_year,
    )
    baselines = baselines_on_ledger(
        ledger, timeframe=timeframe, seed=seed, days_per_year=days_per_year
    )
    return {
        "strategy": strategy,
        "baselines": baselines,
        "cost_rate_per_unit_turnover": realised_cost_rate(ledger),
        "n_bars": int(ledger.height),
        "note": (
            "Baselines are evaluated on the same bars, costs, funding and next-bar "
            "execution convention as the searched strategy. Their parameters are "
            "fixed in advance and never tuned on validation or test."
        ),
    }
