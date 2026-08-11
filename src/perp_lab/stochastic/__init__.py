"""Stochastic benchmarks: synthetic markets used to audit the research pipeline.

**No process in this package is a strategy and none of them is a source of
alpha.** They exist to calibrate our own instruments:

* geometric Brownian motion supplies markets with nothing to find, so the
  selection procedure's false-positive rate can be measured;
* Ornstein-Uhlenbeck supplies a market where reversion genuinely exists, so the
  pipeline's power can be measured;
* first-passage simulation gives the triple-barrier labeler a ground truth;
* the stationary block bootstrap — not GBM — is the primary generator for
  drawdown and ruin estimates.

See :mod:`perp_lab.stochastic.processes` for the documented limitations of GBM
and why it may not be used to claim predictability.
"""

from perp_lab.stochastic.benchmarks import (
    DrawdownReport,
    FirstPassageSummary,
    NullSelectionReport,
    bootstrap_return_paths,
    compare_risk_estimates,
    drawdown_distribution,
    first_passage_summary,
    max_drawdowns,
    reversion_detection_power,
    ruin_probability,
    search_false_positive_rate,
)
from perp_lab.stochastic.processes import (
    BARS_PER_YEAR_1H,
    BARS_PER_YEAR_5M,
    BARS_PER_YEAR_15M,
    GbmParameters,
    OuParameters,
    calibrate_gbm,
    calibrate_ou,
    simulate_gbm,
    simulate_ou,
)

__all__ = [
    "BARS_PER_YEAR_1H",
    "BARS_PER_YEAR_5M",
    "BARS_PER_YEAR_15M",
    "DrawdownReport",
    "FirstPassageSummary",
    "GbmParameters",
    "NullSelectionReport",
    "OuParameters",
    "bootstrap_return_paths",
    "calibrate_gbm",
    "calibrate_ou",
    "compare_risk_estimates",
    "drawdown_distribution",
    "first_passage_summary",
    "max_drawdowns",
    "reversion_detection_power",
    "ruin_probability",
    "search_false_positive_rate",
    "simulate_gbm",
    "simulate_ou",
]
