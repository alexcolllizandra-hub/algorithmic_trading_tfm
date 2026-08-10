"""Statistical evaluation and robustness analysis of out-of-sample evidence.

Everything in this package operates on *already persisted* development
out-of-sample artifacts (per-bar ledgers and trade tables). It never re-runs a
search, never re-selects a candidate and never touches the frozen holdout.
"""

from perp_lab.evaluation.robustness import (
    RobustnessReport,
    block_bootstrap_ci,
    concentration_analysis,
    drop_best_trades,
    reconstruct_bar_returns,
    regime_conditional_metrics,
    stress_costs,
    stress_execution_delay,
    trade_return_bootstrap,
)

__all__ = [
    "RobustnessReport",
    "block_bootstrap_ci",
    "concentration_analysis",
    "drop_best_trades",
    "reconstruct_bar_returns",
    "regime_conditional_metrics",
    "stress_costs",
    "stress_execution_delay",
    "trade_return_bootstrap",
]
