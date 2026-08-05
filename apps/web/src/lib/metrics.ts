// Short, plain-language explanations for quantitative metrics, surfaced as
// tooltips throughout the UI so a reader does not need the methodology open.

export const METRIC_HELP: Record<string, string> = {
  sharpe:
    "Annualised risk-adjusted return: mean bar return divided by its volatility, scaled to a year. Higher is better; negative means losing after risk.",
  mean_test_sharpe:
    "Average out-of-sample TEST Sharpe across the per-fold winners. This is the fair comparison metric between Random Search and the GA.",
  best_val_fitness:
    "Best objective value found on VALIDATION data. Used only for selection; never the out-of-sample verdict.",
  total_return:
    "Cumulative net return over the fold's test window, after fees, slippage and funding.",
  ann_return: "Return annualised from the test window; comparable across differently sized folds.",
  max_drawdown: "Worst peak-to-trough equity decline. Closer to zero is better.",
  turnover: "Sum of absolute position changes; a proxy for trading intensity and cost exposure.",
  n_trades: "Number of completed round-trip trades. Too few trades makes metrics unreliable.",
  fold_instability: "Dispersion of validation Sharpe across folds; penalises fragile candidates.",
  fitness:
    "Scalar objective combining reward (Sharpe) and penalties (drawdown, turnover, instability, complexity).",
  budget:
    "Maximum number of UNIQUE objective evaluations. Random Search and the GA share the same cap.",
  evaluated:
    "Unique candidate evaluations actually consumed. Invalid, duplicate and cached proposals do not count.",
  purge_bars:
    "Bars removed around each split so overlapping label/feature horizons cannot leak across periods.",
  embargo_bars: "Extra bars held out after a split to prevent short-horizon leakage.",
  funding:
    "Perpetual-futures funding payment applied to the position, signed by side. Never silently set to zero.",
};

export function metricHelp(key: string): string | undefined {
  return METRIC_HELP[key];
}
