"""Next-bar, cost-aware backtest engine (funding-, cost- and trade-aware).

Execution model (leak-free):

* A strategy emits ``side_t`` at the **close** of bar *t*.
* That target position is entered at the **open of bar *t+1*** and held over the
  interval ``[open_{t+1}, open_{t+2})``, earning the open-to-open return of bar
  *t+1*. The position active during bar *b* is ``position_b = side_{b-1}`` and
  its gross return is ``position_b * (open_{b+1}/open_b - 1)``.
* Because entry uses ``open_b`` (strictly after the signal's close), a signal is
  never executed at its own closing price.

Cost accounting (per bar *b*):

* ``turnover_b   = |position_b - position_{b-1}|`` (a direct +1->-1 reversal is
  two units of turnover);
* ``fee_b        = turnover_b * fee_bps / 1e4``;
* ``slippage_b   = turnover_b * slippage_bps / 1e4`` (adverse: always a cost);
* ``funding_b    = position_b * funding_rate_in_bar_b`` (longs pay when the rate
  is positive), charged only on bars whose holding interval contains a funding
  settlement, aligned **as-of past**;
* ``net_return_b = gross_return_b - fee_b - slippage_b - funding_b``.

The ledger records, per bar: timestamp, asset, timeframe, raw signal, target and
executed position, execution price, gross return, fee, slippage, funding, net
return, turnover, equity, drawdown, trade id and exit reason. Whether funding
data was available and applied is recorded explicitly (never silently zeroed
when required).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from perp_lab.backtesting.metrics import performance_metrics
from perp_lab.strategies.base import SIDE_COL

_LEDGER_COLUMNS = (
    "open_time",
    "asset",
    "timeframe",
    "raw_signal",
    "target_position",
    "position",
    "execution_price",
    "gross_return",
    "fee",
    "slippage",
    "cost",
    "funding",
    "net_return",
    "turnover",
    "equity",
    "drawdown",
    "trade_id",
    "exit_reason",
)


@dataclass(frozen=True)
class BacktestResult:
    """Per-bar ledger plus summary metrics for one backtest."""

    ledger: pl.DataFrame
    metrics: dict[str, float]
    cost_bps_per_side: float
    funding_applied: bool = False

    @property
    def final_equity(self) -> float:
        if self.ledger.height == 0 or "equity" not in self.ledger.columns:
            return 1.0
        return float(self.ledger["equity"][-1])

    def trades(self) -> pl.DataFrame:
        """One row per closed/held trade: entry, exit, bars, net PnL, reason."""
        if self.ledger.height == 0 or "trade_id" not in self.ledger.columns:
            return pl.DataFrame()
        active = self.ledger.filter(pl.col("trade_id").is_not_null())
        if active.height == 0:
            return pl.DataFrame()
        return (
            active.group_by("trade_id")
            .agg(
                pl.col("open_time").first().alias("entry_time"),
                pl.col("open_time").last().alias("exit_time"),
                pl.len().alias("n_bars"),
                pl.col("position").first().alias("position"),
                pl.col("net_return").sum().alias("net_return"),
                pl.col("funding").sum().alias("funding"),
                pl.col("cost").sum().alias("cost"),
                pl.col("exit_reason").drop_nulls().last().alias("exit_reason"),
            )
            .sort("trade_id")
        )


def _funding_per_bar(bar_ns: np.ndarray, fund_ns: np.ndarray, fund_rate: np.ndarray) -> np.ndarray:
    """Sum funding rates settling inside each bar's holding interval (causal).

    Each funding event at time ``f`` is charged to the bar *b* with
    ``open_b <= f < open_{b+1}`` (the position held during that interval pays or
    receives it). Events before the first / after the last bar are ignored.
    """
    n = bar_ns.shape[0]
    out = np.zeros(n, dtype=float)
    if fund_ns.size == 0:
        return out
    idx = np.searchsorted(bar_ns, fund_ns, side="right") - 1
    valid = (idx >= 0) & (idx < n)
    np.add.at(out, idx[valid], fund_rate[valid])
    return out


def _trade_records(position: np.ndarray) -> tuple[list[int | None], list[str | None]]:
    """Assign a trade id per bar and an exit reason at each trade's last bar."""
    n = position.shape[0]
    trade_id: list[int | None] = [None] * n
    exit_reason: list[str | None] = [None] * n
    tid = 0
    for i in range(n):
        p = position[i]
        if p != 0.0:
            if i == 0 or position[i - 1] != p:
                tid += 1
            trade_id[i] = tid
        nxt = position[i + 1] if i + 1 < n else 0.0
        if p != 0.0 and nxt != p:
            if nxt == 0.0:
                exit_reason[i] = "signal_close"
            elif np.sign(nxt) != np.sign(p):
                exit_reason[i] = "signal_reverse"
    return trade_id, exit_reason


def run_backtest(
    signals: pl.DataFrame,
    prices: pl.DataFrame,
    *,
    timeframe: str,
    fee_bps_per_side: float,
    slippage_bps_per_side: float,
    days_per_year: int = 365,
    time_col: str = "open_time",
    asset: str = "",
    funding: pl.DataFrame | None = None,
    funding_time_col: str = "funding_time",
    funding_rate_col: str = "funding_rate",
    require_funding: bool = False,
) -> BacktestResult:
    """Backtest a target-position series with next-bar execution, costs, funding.

    Parameters
    ----------
    signals:
        Frame with ``time_col`` and :data:`SIDE_COL` (target position at close).
    prices:
        Frame with ``time_col`` and ``open`` (execution price).
    funding:
        Optional frame with ``funding_time_col`` and ``funding_rate_col``. When
        ``require_funding`` is True and this is ``None``, a ``ValueError`` is
        raised rather than silently assuming zero funding.
    """
    if SIDE_COL not in signals.columns:
        raise ValueError(f"signals must contain a {SIDE_COL!r} column.")
    if require_funding and funding is None:
        raise ValueError(
            "Funding data is required by this experiment but no funding frame was provided; "
            "refusing to substitute zero funding."
        )

    joined = (
        prices.select(time_col, "open")
        .join(signals.select(time_col, SIDE_COL), on=time_col, how="inner")
        .sort(time_col)
    )
    funding_applied = funding is not None
    if joined.height < 3:
        empty = joined.select(
            time_col,
            pl.lit(asset).alias("asset"),
            pl.lit(timeframe).alias("timeframe"),
            pl.col(SIDE_COL).cast(pl.Float64).alias("raw_signal"),
            pl.col(SIDE_COL).cast(pl.Float64).alias("target_position"),
            pl.lit(0.0).alias("position"),
            pl.col("open").alias("execution_price"),
            pl.lit(0.0).alias("gross_return"),
            pl.lit(0.0).alias("fee"),
            pl.lit(0.0).alias("slippage"),
            pl.lit(0.0).alias("cost"),
            pl.lit(0.0).alias("funding"),
            pl.lit(0.0).alias("net_return"),
            pl.lit(0.0).alias("turnover"),
            pl.lit(1.0).alias("equity"),
            pl.lit(0.0).alias("drawdown"),
            pl.lit(None, dtype=pl.Int64).alias("trade_id"),
            pl.lit(None, dtype=pl.String).alias("exit_reason"),
        )
        return BacktestResult(
            ledger=empty, metrics={"n_bars": 0.0}, cost_bps_per_side=0.0, funding_applied=False
        )

    fee_rate = fee_bps_per_side / 1e4
    slip_rate = slippage_bps_per_side / 1e4

    oo_return = (pl.col("open").shift(-1) / pl.col("open") - 1.0).alias("oo_return")
    position = pl.col(SIDE_COL).shift(1).fill_null(0).cast(pl.Float64).alias("position")
    ledger = joined.with_columns(oo_return, position)
    ledger = ledger.with_columns(
        (pl.col("position") - pl.col("position").shift(1).fill_null(0)).abs().alias("turnover")
    )

    # Funding aligned to each bar's holding interval (as-of past); 0 if absent.
    bar_ns = ledger[time_col].dt.epoch("ns").to_numpy()
    if funding is not None:
        f = funding.sort(funding_time_col)
        fund_ns = f[funding_time_col].dt.epoch("ns").to_numpy()
        fund_rate = f[funding_rate_col].cast(pl.Float64).to_numpy().astype(float)
        funding_rate_in_bar = _funding_per_bar(bar_ns, fund_ns, fund_rate)
    else:
        funding_rate_in_bar = np.zeros(ledger.height, dtype=float)

    ledger = ledger.with_columns(
        pl.Series("funding_rate_in_bar", funding_rate_in_bar, dtype=pl.Float64)
    )
    ledger = ledger.with_columns(
        (pl.col("turnover") * fee_rate).alias("fee"),
        (pl.col("turnover") * slip_rate).alias("slippage"),
        (pl.col("position") * pl.col("oo_return")).fill_null(0.0).alias("gross_return"),
        (pl.col("position") * pl.col("funding_rate_in_bar")).alias("funding"),
    )
    ledger = ledger.with_columns((pl.col("fee") + pl.col("slippage")).alias("cost"))
    ledger = ledger.with_columns(
        (pl.col("gross_return") - pl.col("cost") - pl.col("funding")).alias("net_return")
    )
    # Drop the final bar (undefined open-to-open return) before compounding.
    ledger = ledger.filter(pl.col("oo_return").is_not_null())
    ledger = ledger.with_columns((1.0 + pl.col("net_return")).cum_prod().alias("equity"))
    ledger = ledger.with_columns(
        (pl.col("equity") / pl.col("equity").cum_max() - 1.0).alias("drawdown")
    )

    pos_arr = ledger["position"].to_numpy()
    trade_id, exit_reason = _trade_records(pos_arr)
    ledger = ledger.with_columns(
        pl.lit(asset).alias("asset"),
        pl.lit(timeframe).alias("timeframe"),
        pl.col(SIDE_COL).cast(pl.Float64).alias("raw_signal"),
        pl.col(SIDE_COL).cast(pl.Float64).alias("target_position"),
        pl.col("open").alias("execution_price"),
        pl.Series("trade_id", trade_id, dtype=pl.Int64),
        pl.Series("exit_reason", exit_reason, dtype=pl.String),
    )

    metrics = performance_metrics(
        ledger["net_return"].to_numpy(),
        timeframe=timeframe,
        positions=ledger["position"].to_numpy(),
        turnover=ledger["turnover"].to_numpy(),
        days_per_year=days_per_year,
    )
    metrics["funding_total"] = float(ledger["funding"].sum())
    metrics["gross_return_total"] = float((ledger["gross_return"]).sum())

    ledger_out = ledger.select(_LEDGER_COLUMNS)
    return BacktestResult(
        ledger=ledger_out,
        metrics=metrics,
        cost_bps_per_side=fee_bps_per_side + slippage_bps_per_side,
        funding_applied=funding_applied,
    )
