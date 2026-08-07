"""Robustness battery for concatenated development out-of-sample evidence.

A single point estimate of Sharpe or total return from one walk-forward pass is
not evidence. This module quantifies how fragile that estimate is, using only the
per-bar ledger and trade table a run already persisted:

* **Block bootstrap** confidence intervals that respect serial dependence, so the
  interval is not artificially narrow the way an i.i.d. bootstrap would be.
* **Cost and slippage stress**: fees and slippage are provisional assumptions
  (ADR-0005), so results must be re-priced at multiples of them.
* **Execution delay**: filling one or two bars later than the contract assumes.
* **Trade concentration**: how much of the result rests on a handful of trades.

None of these functions re-run a search or re-select a candidate, and none of
them read the frozen holdout.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import polars as pl

from perp_lab.backtesting.metrics import performance_metrics

# Columns a persisted OOS ledger must carry for the battery to run.
REQUIRED_COLUMNS = ("position", "oo_return", "gross_return", "fee", "slippage", "funding")


@dataclass(frozen=True)
class RobustnessReport:
    """Serialisable outcome of one robustness scenario."""

    scenario: str
    params: dict[str, Any]
    metrics: dict[str, float]
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "params": self.params,
            "metrics": self.metrics,
            "note": self.note,
        }


def _require(ledger: pl.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in ledger.columns]
    if missing:
        raise ValueError(
            f"Ledger is missing columns required for robustness analysis: {missing}. "
            "Re-run the experiment with the current runner so the full ledger is persisted."
        )


def reconstruct_bar_returns(ledger: pl.DataFrame) -> np.ndarray:
    """Per-bar market return of each holding interval.

    The backtester holds a position over ``[open_b, open_{b+1})`` and persists
    that interval's return as ``oo_return``. It is read directly rather than
    re-derived from consecutive execution prices, because the ledger drops each
    fold's final bar and concatenating folds makes cross-boundary price ratios
    meaningless.
    """
    if "oo_return" not in ledger.columns:
        raise ValueError(
            "Ledger has no 'oo_return' column. It was written by an older engine "
            "version; re-run the experiment to enable exact re-pricing."
        )
    values = ledger["oo_return"].cast(pl.Float64).to_numpy().astype(float)
    return np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)


def stress_costs(
    ledger: pl.DataFrame,
    *,
    timeframe: str,
    fee_multiplier: float = 1.0,
    slippage_multiplier: float = 1.0,
    days_per_year: int = 365,
) -> RobustnessReport:
    """Re-price the same positions under scaled fees and slippage.

    Fees and slippage are both proportional to turnover and to their bps rate, so
    scaling the persisted per-bar amounts is exactly equivalent to re-running the
    backtest with scaled bps. Positions, funding and market returns are untouched.
    """
    _require(ledger)
    net = (
        ledger["gross_return"].cast(pl.Float64).to_numpy()
        - fee_multiplier * ledger["fee"].cast(pl.Float64).to_numpy()
        - slippage_multiplier * ledger["slippage"].cast(pl.Float64).to_numpy()
        - ledger["funding"].cast(pl.Float64).to_numpy()
    )
    metrics = performance_metrics(
        net,
        timeframe=timeframe,
        positions=ledger["position"].cast(pl.Float64).to_numpy(),
        turnover=(
            ledger["turnover"].cast(pl.Float64).to_numpy() if "turnover" in ledger.columns else None
        ),
        days_per_year=days_per_year,
    )
    return RobustnessReport(
        scenario="cost_stress",
        params={"fee_multiplier": fee_multiplier, "slippage_multiplier": slippage_multiplier},
        metrics=metrics,
        note="positions unchanged; only the provisional cost assumptions are re-priced",
    )


def stress_execution_delay(
    ledger: pl.DataFrame,
    *,
    timeframe: str,
    delay_bars: int = 1,
    days_per_year: int = 365,
) -> RobustnessReport:
    """Fill ``delay_bars`` bars later than the next-bar contract assumes.

    The position series is shifted forward and re-priced against the market
    returns implied by the ledger's execution prices. Costs are recomputed from
    the shifted turnover at the ledger's own realised cost rate, so a slower fill
    is not silently made cheaper.
    """
    _require(ledger)
    if delay_bars < 0:
        raise ValueError("delay_bars must be >= 0.")

    market = reconstruct_bar_returns(ledger)
    position = ledger["position"].cast(pl.Float64).to_numpy().astype(float)
    delayed = np.concatenate([np.zeros(delay_bars), position])[: position.shape[0]]

    turnover = np.abs(np.diff(delayed, prepend=0.0))
    # Realised cost per unit of turnover in the original run (fees + slippage).
    original_turnover = float(np.abs(np.diff(position, prepend=0.0)).sum())
    original_cost = float(ledger["fee"].cast(pl.Float64).sum()) + float(
        ledger["slippage"].cast(pl.Float64).sum()
    )
    rate = (original_cost / original_turnover) if original_turnover > 0 else 0.0

    funding_rate_per_unit = np.divide(
        ledger["funding"].cast(pl.Float64).to_numpy(),
        position,
        out=np.zeros_like(position),
        where=position != 0,
    )
    net = delayed * market - turnover * rate - delayed * funding_rate_per_unit

    metrics = performance_metrics(
        net,
        timeframe=timeframe,
        positions=delayed,
        turnover=turnover,
        days_per_year=days_per_year,
    )
    return RobustnessReport(
        scenario="execution_delay",
        params={"delay_bars": delay_bars},
        metrics=metrics,
        note="positions shifted later and re-priced at the run's realised cost rate",
    )


def block_bootstrap_ci(
    returns: np.ndarray,
    statistic: Callable[[np.ndarray], float],
    *,
    block_size: int,
    n_resamples: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
) -> dict[str, float]:
    """Circular block-bootstrap confidence interval for a time-series statistic.

    Resampling whole contiguous blocks preserves short-range serial dependence
    (volatility clustering, autocorrelated positions), which an i.i.d. bootstrap
    destroys and which would make the interval far too narrow. ``block_size``
    should exceed the dependence horizon of the series; report the sensitivity of
    the interval to it rather than trusting a single choice.
    """
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    n = r.size
    if n == 0 or block_size < 1:
        return {}
    block_size = min(block_size, n)
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block_size))

    samples = np.empty(n_resamples, dtype=float)
    idx_base = np.arange(block_size)
    for i in range(n_resamples):
        starts = rng.integers(0, n, size=n_blocks)
        # Circular indexing so every position is equally likely to start a block.
        idx = ((starts[:, None] + idx_base[None, :]) % n).reshape(-1)[:n]
        samples[i] = statistic(r[idx])

    finite = samples[np.isfinite(samples)]
    if finite.size == 0:
        return {}
    return {
        "point_estimate": float(statistic(r)),
        "ci_low": float(np.quantile(finite, alpha / 2)),
        "ci_high": float(np.quantile(finite, 1 - alpha / 2)),
        "bootstrap_mean": float(finite.mean()),
        "bootstrap_std": float(finite.std(ddof=1)) if finite.size > 1 else 0.0,
        "block_size": float(block_size),
        "n_resamples": float(finite.size),
        "alpha": alpha,
        # Share of resamples with a statistic <= 0: an informal one-sided read on
        # whether the effect could plausibly be non-positive.
        "share_non_positive": float(np.mean(finite <= 0.0)),
    }


def drop_best_trades(trade_returns: np.ndarray, *, k: int) -> dict[str, float]:
    """Recompute the aggregate outcome after removing the ``k`` best trades.

    A result that collapses once a couple of trades are removed is a story about
    those trades, not about the strategy.
    """
    t = np.asarray(trade_returns, dtype=float)
    t = t[np.isfinite(t)]
    if t.size == 0:
        return {}
    k = max(0, min(k, t.size))
    kept = np.sort(t)[: t.size - k] if k else t
    return {
        "k_removed": float(k),
        "n_trades_kept": float(kept.size),
        "total_return_all": float(np.prod(1.0 + t) - 1.0),
        "total_return_without_best": float(np.prod(1.0 + kept) - 1.0),
        "mean_trade_all": float(t.mean()),
        "mean_trade_without_best": float(kept.mean()) if kept.size else 0.0,
    }


def concentration_analysis(trade_returns: np.ndarray) -> dict[str, float]:
    """How concentrated the profit is across trades."""
    t = np.asarray(trade_returns, dtype=float)
    t = t[np.isfinite(t)]
    if t.size == 0:
        return {}
    out: dict[str, float] = {"n_trades": float(t.size)}
    for k in (1, 5, 10):
        out.update(
            {f"drop_top{k}_total_return": drop_best_trades(t, k=k)["total_return_without_best"]}
        )
    wins = t[t > 0]
    gross_profit = float(wins.sum())
    if gross_profit > 0:
        ranked = np.sort(wins)[::-1]
        for k in (1, 5, 10):
            out[f"top{k}_profit_share"] = float(ranked[:k].sum() / gross_profit)
    return out


@dataclass
class RobustnessBattery:
    """Run the standard scenario set over one concatenated OOS ledger."""

    ledger: pl.DataFrame
    timeframe: str
    days_per_year: int = 365
    reports: list[RobustnessReport] = field(default_factory=list)

    def run(
        self,
        *,
        cost_multipliers: tuple[float, ...] = (1.0, 1.5, 2.0),
        slippage_multipliers: tuple[float, ...] = (1.0, 2.0, 5.0),
        delays: tuple[int, ...] = (1, 2),
    ) -> list[RobustnessReport]:
        self.reports = []
        for m in cost_multipliers:
            self.reports.append(
                stress_costs(
                    self.ledger,
                    timeframe=self.timeframe,
                    fee_multiplier=m,
                    slippage_multiplier=m,
                    days_per_year=self.days_per_year,
                )
            )
        for m in slippage_multipliers:
            if m == 1.0:
                continue
            self.reports.append(
                stress_costs(
                    self.ledger,
                    timeframe=self.timeframe,
                    slippage_multiplier=m,
                    days_per_year=self.days_per_year,
                )
            )
        for d in delays:
            self.reports.append(
                stress_execution_delay(
                    self.ledger,
                    timeframe=self.timeframe,
                    delay_bars=d,
                    days_per_year=self.days_per_year,
                )
            )
        return self.reports

    def to_dict(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self.reports]
