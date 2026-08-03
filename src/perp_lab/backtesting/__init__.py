"""Cost-aware, next-bar backtesting (Chapter 5.7) — minimal slice.

This initial path is only what is needed to evaluate one baseline strategy
end to end: it executes a target position at the **next bar's open** (a signal
formed at the close of bar *t* is filled at the open of *t+1*, never at the
close of *t*), charges per-side fees and slippage on position changes, and
computes net-of-cost performance metrics. Funding payments, position sizing and
leverage limits are specified in the methodology but intentionally deferred to a
later slice; the current model holds a unit long/short/flat position.
"""

from perp_lab.backtesting.engine import BacktestResult, run_backtest
from perp_lab.backtesting.metrics import bars_per_year, performance_metrics

__all__ = ["BacktestResult", "bars_per_year", "performance_metrics", "run_backtest"]
