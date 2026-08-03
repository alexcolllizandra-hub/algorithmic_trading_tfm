"""Reusable exploratory-data-analysis functions.

All logic lives here (not in notebooks) so it is testable and reusable by the
API and later phases. Notebooks narrate results by calling these functions.
"""

from perp_lab.eda.calendar import monthly_returns, monthly_volatility, to_year_month_matrix
from perp_lab.eda.correlation import (
    block_bootstrap_corr_ci,
    correlation_by_sign,
    correlation_by_vol_regime,
    rolling_correlation,
    spearman_correlation,
    static_correlation,
)
from perp_lab.eda.coverage import dataset_quality_row, longest_gap, monthly_coverage
from perp_lab.eda.datasets import DataLake, LoadedDataset, assert_no_holdout, utc
from perp_lab.eda.dependence import autocorrelation, ljung_box_pvalue
from perp_lab.eda.drawdown import (
    add_drawdown,
    drawdown_episodes,
    max_drawdown,
    top_drawdowns,
    underwater_fraction,
)
from perp_lab.eda.events import (
    CRYPTO_MARKET_EVENTS,
    market_events_frame,
    market_stress_index,
)
from perp_lab.eda.extremes import coexceedance_rate, rank_extreme_events
from perp_lab.eda.funding import (
    attach_funding,
    basis_summary,
    funding_autocorr,
    funding_dynamics,
    funding_future_return_relation,
    funding_sign_runs,
    mark_price_basis,
)
from perp_lab.eda.leadlag import cross_correlation, peak_lag, tail_coexceedance
from perp_lab.eda.liquidity import add_liquidity_proxies, liquidity_summary, zero_return_fraction
from perp_lab.eda.orderflow import add_order_flow_imbalance, order_flow_summary
from perp_lab.eda.regimes import (
    regime_context,
    regime_duration_summary,
    regime_duration_table,
    regime_frequencies,
    regime_intervals,
    regime_runs,
    regime_transition_matrix,
    regime_transition_matrix_full,
    tag_activity_regime,
    tag_trend_volatility_regimes,
)
from perp_lab.eda.returns import (
    add_log_returns,
    add_simple_returns,
    annualization_factor,
    return_stats,
)
from perp_lab.eda.rolling import rolling_moments
from perp_lab.eda.seasonality import (
    funding_summary,
    seasonality_by_hour,
    seasonality_by_weekday,
    seasonality_kruskal,
    seasonality_stats,
)
from perp_lab.eda.stationarity import (
    adf_test,
    arch_lm_test,
    kpss_test,
    ljung_box,
    stationarity_report,
)
from perp_lab.eda.tailrisk import historical_var_es, tail_asymmetry, tail_risk_table
from perp_lab.eda.volatility import (
    annualized_volatility,
    garman_klass_volatility,
    parkinson_volatility,
    realized_volatility,
    rolling_volatility,
)

__all__ = [
    "CRYPTO_MARKET_EVENTS",
    "DataLake",
    "LoadedDataset",
    "add_drawdown",
    "add_liquidity_proxies",
    "add_log_returns",
    "add_order_flow_imbalance",
    "add_simple_returns",
    "adf_test",
    "annualization_factor",
    "annualized_volatility",
    "arch_lm_test",
    "assert_no_holdout",
    "attach_funding",
    "autocorrelation",
    "basis_summary",
    "block_bootstrap_corr_ci",
    "coexceedance_rate",
    "correlation_by_sign",
    "correlation_by_vol_regime",
    "cross_correlation",
    "dataset_quality_row",
    "drawdown_episodes",
    "funding_autocorr",
    "funding_dynamics",
    "funding_future_return_relation",
    "funding_sign_runs",
    "funding_summary",
    "garman_klass_volatility",
    "historical_var_es",
    "kpss_test",
    "liquidity_summary",
    "ljung_box",
    "ljung_box_pvalue",
    "longest_gap",
    "mark_price_basis",
    "market_events_frame",
    "market_stress_index",
    "max_drawdown",
    "monthly_coverage",
    "monthly_returns",
    "monthly_volatility",
    "order_flow_summary",
    "parkinson_volatility",
    "peak_lag",
    "rank_extreme_events",
    "realized_volatility",
    "regime_context",
    "regime_duration_summary",
    "regime_duration_table",
    "regime_frequencies",
    "regime_intervals",
    "regime_runs",
    "regime_transition_matrix",
    "regime_transition_matrix_full",
    "return_stats",
    "rolling_correlation",
    "rolling_moments",
    "rolling_volatility",
    "seasonality_by_hour",
    "seasonality_by_weekday",
    "seasonality_kruskal",
    "seasonality_stats",
    "spearman_correlation",
    "static_correlation",
    "stationarity_report",
    "tag_activity_regime",
    "tag_trend_volatility_regimes",
    "tail_asymmetry",
    "tail_coexceedance",
    "tail_risk_table",
    "to_year_month_matrix",
    "top_drawdowns",
    "underwater_fraction",
    "utc",
    "zero_return_fraction",
]
