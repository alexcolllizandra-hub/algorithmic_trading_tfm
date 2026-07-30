"""Reusable exploratory-data-analysis functions.

All logic lives here (not in notebooks) so it is testable and reusable by the
API and later phases. Notebooks narrate results by calling these functions.
"""

from perp_lab.eda.correlation import rolling_correlation, static_correlation
from perp_lab.eda.dependence import autocorrelation, ljung_box_pvalue
from perp_lab.eda.regimes import tag_trend_volatility_regimes
from perp_lab.eda.returns import (
    add_log_returns,
    add_simple_returns,
    annualization_factor,
    return_stats,
)
from perp_lab.eda.seasonality import funding_summary, seasonality_by_hour, seasonality_by_weekday
from perp_lab.eda.volatility import annualized_volatility, realized_volatility, rolling_volatility

__all__ = [
    "add_log_returns",
    "add_simple_returns",
    "annualization_factor",
    "annualized_volatility",
    "autocorrelation",
    "funding_summary",
    "ljung_box_pvalue",
    "realized_volatility",
    "return_stats",
    "rolling_correlation",
    "rolling_volatility",
    "seasonality_by_hour",
    "seasonality_by_weekday",
    "static_correlation",
    "tag_trend_volatility_regimes",
]
