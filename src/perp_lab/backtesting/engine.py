"""Minimal next-bar, cost-aware backtest engine.

Execution model (leak-free):

* A strategy emits ``side_t`` at the **close** of bar *t*.
* That position is entered at the **open of bar *t+1*** and held over the
  interval ``[open_{t+1}, open_{t+2})``, earning the open-to-open return of bar
  *t+1*. Concretely the position active during bar *b* is ``pos_b = side_{b-1}``
  and its gross return is ``pos_b * (open_{b+1}/open_b - 1)``.
* Because entry uses ``open_{b}`` (strictly after the signal's close), a signal
  is never executed at its own closing price.
* Costs (per-side fee + slippage, in bps) are charged on the traded position
  change ``|pos_b - pos_{b-1}|`` at each rebalance.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from perp_lab.backtesting.metrics import performance_metrics
from perp_lab.strategies.base import SIDE_COL


@dataclass(frozen=True)
class BacktestResult:
    """Per-bar ledger plus summary metrics for one backtest."""

    ledger: pl.DataFrame  # open_time, position, gross_return, cost, net_return, equity
    metrics: dict[str, float]
    cost_bps_per_side: float

    @property
    def final_equity(self) -> float:
        if self.ledger.height == 0:
            return 1.0
        return float(self.ledger["equity"][-1])


def run_backtest(
    signals: pl.DataFrame,
    prices: pl.DataFrame,
    *,
    timeframe: str,
    fee_bps_per_side: float,
    slippage_bps_per_side: float,
    days_per_year: int = 365,
    time_col: str = "open_time",
) -> BacktestResult:
    """Backtest a target-position series with next-bar execution and costs.

    Parameters
    ----------
    signals:
        Frame with ``time_col`` and :data:`SIDE_COL` (target position at close).
    prices:
        Frame with ``time_col`` and ``open`` (execution price).
    """
    if SIDE_COL not in signals.columns:
        raise ValueError(f"signals must contain a {SIDE_COL!r} column.")
    joined = (
        prices.select(time_col, "open")
        .join(signals.select(time_col, SIDE_COL), on=time_col, how="inner")
        .sort(time_col)
    )
    if joined.height < 3:
        empty = joined.select(
            time_col,
            pl.lit(0.0).alias("position"),
            pl.lit(0.0).alias("gross_return"),
            pl.lit(0.0).alias("cost"),
            pl.lit(0.0).alias("net_return"),
            pl.lit(1.0).alias("equity"),
        )
        return BacktestResult(ledger=empty, metrics={"n_bars": 0.0}, cost_bps_per_side=0.0)

    cost_rate = (fee_bps_per_side + slippage_bps_per_side) / 1e4

    # Open-to-open simple return of each bar; last bar has no next open.
    oo_return = (pl.col("open").shift(-1) / pl.col("open") - 1.0).alias("oo_return")
    # Position held during bar b is the side decided at the previous close.
    position = pl.col(SIDE_COL).shift(1).fill_null(0).cast(pl.Float64).alias("position")

    ledger = joined.with_columns(oo_return, position)
    ledger = ledger.with_columns(
        (pl.col("position") - pl.col("position").shift(1).fill_null(0)).abs().alias("turnover")
    )
    ledger = ledger.with_columns(
        (pl.col("position") * pl.col("oo_return")).fill_null(0.0).alias("gross_return"),
        (pl.col("turnover") * cost_rate).alias("cost"),
    )
    ledger = ledger.with_columns((pl.col("gross_return") - pl.col("cost")).alias("net_return"))
    # Drop the final bar (undefined open-to-open return) before compounding.
    ledger = ledger.filter(pl.col("oo_return").is_not_null())
    ledger = ledger.with_columns((1.0 + pl.col("net_return")).cum_prod().alias("equity"))

    metrics = performance_metrics(
        ledger["net_return"].to_numpy(),
        timeframe=timeframe,
        positions=ledger["position"].to_numpy(),
        turnover=ledger["turnover"].to_numpy(),
        days_per_year=days_per_year,
    )
    ledger_out = ledger.select(time_col, "position", "gross_return", "cost", "net_return", "equity")
    return BacktestResult(
        ledger=ledger_out,
        metrics=metrics,
        cost_bps_per_side=fee_bps_per_side + slippage_bps_per_side,
    )
