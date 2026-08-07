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

import hashlib
from typing import Any

import numpy as np
import polars as pl

from perp_lab.backtesting.metrics import performance_metrics
from perp_lab.evaluation.robustness import reconstruct_bar_returns

# Per-bar funding rate persisted by the engine, independent of any position.
FUNDING_RATE_COL = "funding_rate_in_bar"


def realised_cost_rate(ledger: pl.DataFrame) -> float:
    """Cost per unit of turnover actually charged in the run (fees + slippage).

    Reported for auditing only. It must NOT be used to price a baseline: it is a
    property of the searched strategy's own turnover, so two engines produce
    slightly different rates and the "baseline" would drift with whatever it is
    being compared against. Baselines use the contract rate instead.
    """
    turnover = float(np.abs(np.diff(ledger["position"].to_numpy(), prepend=0.0)).sum())
    if turnover <= 0:
        return 0.0
    cost = float(ledger["fee"].cast(pl.Float64).sum()) + float(
        ledger["slippage"].cast(pl.Float64).sum()
    )
    return cost / turnover


def contract_cost_rate(fee_bps_per_side: float, slippage_bps_per_side: float) -> float:
    """Cost per unit of turnover implied by the experiment contract.

    Both engines run under the same contract, so this rate is identical for every
    strategy compared on a given study -- which is what makes a baseline a fixed
    reference rather than a moving target.
    """
    return (fee_bps_per_side + slippage_bps_per_side) / 1e4


def funding_rate_per_bar(ledger: pl.DataFrame) -> np.ndarray:
    """The funding rate settling in each bar, independent of any position.

    Read from the ledger column the engine persists. Deriving it as
    ``funding / position`` is wrong: it is undefined wherever the strategy was
    flat, and defaulting those bars to zero hands a baseline free funding on
    exactly the bars the strategy chose to sit out.
    """
    if FUNDING_RATE_COL not in ledger.columns:
        raise ValueError(
            f"Ledger has no {FUNDING_RATE_COL!r} column. It was written by an older "
            "engine version that back-derived funding from the strategy's own "
            "position; re-run the experiment so baselines can be charged correctly."
        )
    return ledger[FUNDING_RATE_COL].cast(pl.Float64).to_numpy().astype(float)


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
    fee_bps_per_side: float,
    slippage_bps_per_side: float,
    seed: int = 42,
    days_per_year: int = 365,
) -> dict[str, dict[str, float]]:
    """Evaluate the fixed baseline suite over the ledger's own bars.

    Costs come from the experiment contract and funding from the ledger's own
    per-bar rate, so a baseline depends only on (asset, bars, contract) and is
    therefore identical for every engine compared on the same coverage. Parameters
    are fixed in :mod:`perp_lab.strategies.baselines` and are never tuned here.
    """
    market = reconstruct_bar_returns(ledger)
    n = market.size
    funding_per_unit = funding_rate_per_bar(ledger)
    cost_rate = contract_cost_rate(fee_bps_per_side, slippage_bps_per_side)
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


def coverage_id(ledger: pl.DataFrame) -> str:
    """Stable hash of the exact out-of-sample bars a result was scored on.

    Two results may only be compared when this matches. It is cheap to record and
    it turns "were these scored on the same bars?" from an assumption into an
    assertion.
    """
    times = ledger["open_time"].cast(pl.Int64).to_numpy()
    digest = hashlib.sha256()
    digest.update(str(times.size).encode("utf-8"))
    digest.update(times.tobytes())
    return digest.hexdigest()[:16]


def strategy_versus_baselines(
    ledger: pl.DataFrame,
    *,
    timeframe: str,
    fee_bps_per_side: float,
    slippage_bps_per_side: float,
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
        ledger,
        timeframe=timeframe,
        fee_bps_per_side=fee_bps_per_side,
        slippage_bps_per_side=slippage_bps_per_side,
        seed=seed,
        days_per_year=days_per_year,
    )
    return {
        "strategy": strategy,
        "baselines": baselines,
        "coverage_id": coverage_id(ledger),
        "contract_cost_rate_per_unit_turnover": contract_cost_rate(
            fee_bps_per_side, slippage_bps_per_side
        ),
        "strategy_realised_cost_rate": realised_cost_rate(ledger),
        "n_bars": int(ledger.height),
        "note": (
            "Baselines are evaluated on the same bars and next-bar execution "
            "convention as the searched strategy, priced at the contract cost rate "
            "and the ledger's own per-bar funding rate. They therefore depend only "
            "on (asset, coverage, contract) and are identical across engines. Their "
            "parameters are fixed in advance and never tuned on validation or test."
        ),
    }
