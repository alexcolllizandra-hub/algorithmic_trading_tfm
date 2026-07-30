---
name: create-eda-analysis
description: Structure a new exploratory-data-analysis unit so each finding drives a downstream decision. Use when adding EDA to a notebook or the perp_lab.eda library for the thesis (returns, volatility, dependence, seasonality, correlation, regimes).
disable-model-invocation: true
---

# Create EDA analysis

Every EDA unit must justify a later design decision (a feature, indicator,
horizon, cost, rule, regime, or risk control). EDA is not a gallery of plots.

## Required structure (per analysis)

```
Question:      What decision does this inform?
Method:        Which perp_lab.eda function(s) and parameters, on which data.
Result:        The computed numbers / table.
Figure/Table:  Saved to reports/figures or reports/tables.
Interpretation: What the result means for BTC/ETH intraday behaviour.
Implication:   The concrete downstream choice it supports (or rules out).
```

## Rules

- Put reusable logic in `src/perp_lab/eda/` (with a test); the notebook calls it.
- Use the development partition only. Never read the frozen holdout.
- Descriptive full-sample stats are allowed but must be labeled as descriptive
  (not to be reused as causal features).
- Log returns and 365-day annualization (`annualization_factor`).

## Available building blocks

`add_log_returns`, `return_stats`, `rolling_volatility`, `realized_volatility`,
`annualized_volatility`, `autocorrelation`, `ljung_box_pvalue`,
`seasonality_by_hour/weekday`, `funding_summary`, `static/rolling_correlation`,
`tag_trend_volatility_regimes`, and plot helpers in `perp_lab.eda.plots`.
