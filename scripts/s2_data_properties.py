"""Reproduce the data-property measurements cited in the Gate S2 pre-specification.

Every number in ``docs/roadmap/gate_s2_batch_01.md`` section 5 comes from here.
The script reads **development data only** and asserts that boundary, and it
computes *no* returns, Sharpe ratios or PnL -- only input correlations, trigger
frequencies and a censoring rate. That is what makes these measurements
admissible as pre-specification engineering rather than result-driven tuning.

Run with `uv run python scripts/s2_data_properties.py`.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from perp_lab.config.settings import load_data_contract
from perp_lab.strategies.orderflow import flow_imbalance, window_log_return

SYMBOLS = ("BTCUSDT", "ETHUSDT")
WINDOWS = (4, 8, 24)
QUANTILES = (0.5, 0.6, 0.7, 0.85)


def _holdout_start() -> dt.datetime:
    contract = load_data_contract()
    start = contract.holdout.start_date(contract.cutoff_date)
    return dt.datetime(start.year, start.month, start.day, tzinfo=dt.UTC)


def mark_versus_last_censoring(holdout_start: dt.datetime) -> None:
    """How often does the median operator collapse the mark-minus-last gap to zero?"""
    print("== mark price versus last price, 5m development bars ==")
    for symbol in SYMBOLS:
        last = pl.read_parquet(f"data/validated/{symbol}/5m.parquet").filter(
            pl.col("open_time") < holdout_start
        )
        mark = pl.read_parquet(f"data/validated/{symbol}/markPrice_5m.parquet").filter(
            pl.col("open_time") < holdout_start
        )
        assert last["open_time"].max() < holdout_start
        assert mark["open_time"].max() < holdout_start

        joined = last.select("open_time", pl.col("close").alias("last")).join(
            mark.select("open_time", pl.col("close").alias("mark")), on="open_time", how="inner"
        )
        gap_bp = ((joined["last"] - joined["mark"]) / joined["mark"] * 10_000).drop_nulls()
        print(
            f"  {symbol}  n={gap_bp.len():>9,}  "
            f"exactly zero={float((gap_bp == 0.0).mean()):>7.2%}  "
            f"|gap|<0.1bp={float((gap_bp.abs() < 0.1).mean()):>7.2%}  "
            f"|gap|>10bp={float((gap_bp.abs() > 10.0).mean()):>7.2%}"
        )
    print()


def flow_price_relationship(holdout_start: dt.datetime) -> None:
    """Correlation of flow with the move it produced, and divergence trigger rates."""
    print("== windowed taker imbalance versus windowed return, 1h development bars ==")
    for symbol in SYMBOLS:
        bars = pl.read_parquet(f"data/processed/{symbol}/1h_development.parquet")
        assert bars["open_time"].max() < holdout_start
        for window in WINDOWS:
            prepared = bars.select(
                flow_imbalance(window, 1).alias("imbalance"),
                window_log_return(window, 1).alias("move"),
            ).drop_nulls()
            imbalance = prepared["imbalance"].to_numpy()
            move = prepared["move"].to_numpy()
            disagree = np.sign(imbalance) * np.sign(move) < 0
            correlation = float(np.corrcoef(imbalance, move)[0, 1])

            rates = []
            for quantile in QUANTILES:
                both_extreme = (
                    disagree
                    & (np.abs(imbalance) >= np.quantile(np.abs(imbalance), quantile))
                    & (np.abs(move) >= np.quantile(np.abs(move), quantile))
                )
                rates.append(f"q{quantile:g}={both_extreme.mean():.3%}")
            print(
                f"  {symbol} w={window:>2}  n={imbalance.size:>7,}  "
                f"corr={correlation:+.3f}  disagree={disagree.mean():>6.2%}  " + "  ".join(rates)
            )
    print()


def main() -> int:
    holdout_start = _holdout_start()
    print(f"holdout starts {holdout_start.isoformat()}; nothing at or after it is read.\n")
    mark_versus_last_censoring(holdout_start)
    flow_price_relationship(holdout_start)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
