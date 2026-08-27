"""Reusable exploratory-data-analysis functions.

All logic lives here (not in notebooks) so it is testable and reusable by the
API and later phases. Notebooks narrate results by calling these functions.
"""

from perp_lab.eda.bootstrap import (
    bootstrap_ci,
    bootstrap_diff_ci,
    mean_stat,
    median_stat,
    moving_block_bootstrap,
    sharpe_stat,
    vol_stat,
)
from perp_lab.eda.calendar import monthly_returns, monthly_volatility, to_year_month_matrix
from perp_lab.eda.cointegration import engle_granger, engle_granger_by_regime
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
from perp_lab.eda.dependence import (
    autocorrelation,
    hurst_rs,
    leverage_effect,
    ljung_box_pvalue,
    rolling_hurst,
    variance_ratio,
    variance_ratio_profile,
)
from perp_lab.eda.distributions import (
    fit_student_t,
    hill_by_k,
    hill_tail_index,
    kurtosis_by_aggregation,
    survival_function,
)
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
from perp_lab.eda.features import (
    feature_correlation_matrix,
    high_correlation_pairs,
    label_summary,
    mutual_information_by_horizon,
    pca_scree,
)
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
from perp_lab.eda.regime_tests import (
    dunn_posthoc,
    kruskal_regime,
    regime_comparison,
    regime_medians_ci,
)
from perp_lab.eda.regimes import (
    MARKET_REGIMES,
    market_regime_stats,
    market_regime_windows,
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
from perp_lab.eda.stress_dependence import (
    coexceedance_summary,
    conditional_exceedance,
    normal_vs_stress_correlation,
    rolling_tail_dependence,
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
    "MARKET_REGIMES",
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
    "bootstrap_ci",
    "bootstrap_diff_ci",
    "coexceedance_rate",
    "coexceedance_summary",
    "conditional_exceedance",
    "correlation_by_sign",
    "correlation_by_vol_regime",
    "cross_correlation",
    "dataset_quality_row",
    "drawdown_episodes",
    "dunn_posthoc",
    "engle_granger",
    "engle_granger_by_regime",
    "feature_correlation_matrix",
    "fit_student_t",
    "funding_autocorr",
    "funding_dynamics",
    "funding_future_return_relation",
    "funding_sign_runs",
    "funding_summary",
    "garman_klass_volatility",
    "high_correlation_pairs",
    "hill_by_k",
    "hill_tail_index",
    "historical_var_es",
    "hurst_rs",
    "kpss_test",
    "kruskal_regime",
    "kurtosis_by_aggregation",
    "label_summary",
    "leverage_effect",
    "liquidity_summary",
    "ljung_box",
    "ljung_box_pvalue",
    "longest_gap",
    "mark_price_basis",
    "market_events_frame",
    "market_regime_stats",
    "market_regime_windows",
    "market_stress_index",
    "max_drawdown",
    "mean_stat",
    "median_stat",
    "monthly_coverage",
    "monthly_returns",
    "monthly_volatility",
    "moving_block_bootstrap",
    "mutual_information_by_horizon",
    "normal_vs_stress_correlation",
    "order_flow_summary",
    "parkinson_volatility",
    "pca_scree",
    "peak_lag",
    "rank_extreme_events",
    "realized_volatility",
    "regime_comparison",
    "regime_context",
    "regime_duration_summary",
    "regime_duration_table",
    "regime_frequencies",
    "regime_intervals",
    "regime_medians_ci",
    "regime_runs",
    "regime_transition_matrix",
    "regime_transition_matrix_full",
    "return_stats",
    "rolling_correlation",
    "rolling_hurst",
    "rolling_moments",
    "rolling_tail_dependence",
    "rolling_volatility",
    "seasonality_by_hour",
    "seasonality_by_weekday",
    "seasonality_kruskal",
    "seasonality_stats",
    "sharpe_stat",
    "spearman_correlation",
    "static_correlation",
    "stationarity_report",
    "survival_function",
    "tag_activity_regime",
    "tag_trend_volatility_regimes",
    "tail_asymmetry",
    "tail_coexceedance",
    "tail_risk_table",
    "to_year_month_matrix",
    "top_drawdowns",
    "underwater_fraction",
    "utc",
    "variance_ratio",
    "variance_ratio_profile",
    "vol_stat",
    "zero_return_fraction",
]
