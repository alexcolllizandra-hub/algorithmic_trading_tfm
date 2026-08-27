# Metric definitions used in Chapter 6 (verified against source code)

Every formula below was read from the implementation, not from documentation.
File references point at the code that actually produced the reported numbers.

## 1. Per-bar returns (the series everything is computed on)

`src/perp_lab/backtesting/engine.py` produces **net simple returns per 1h bar**:
gross position return minus transaction costs (4 bps taker fee + 1 bps slippage
per side, charged on position changes) minus realized funding transferred
`as_of_past` (only funding events already published at bar open). No leverage
compounding tricks: the equity curve is the cumulative product of
`(1 + net_return)`.

## 2. Sharpe ratio — engine variant (per run/fold)

`src/perp_lab/backtesting/metrics.py`:

```
sharpe = mean(net_returns) / std(net_returns, ddof=1) * sqrt(bars_per_year)
bars_per_year = 365 * 24 = 8760   # 1h bars, crypto trades every day
```

Risk-free rate is omitted (funding already enters the return series; the
per-bar risk-free on 1h horizons is negligible relative to cost noise).
Sortino uses downside deviation with the same annualization; Calmar is
annualized return over maximum drawdown.

## 3. Sharpe ratio — closure variants (Chapter 6 tables)

`src/perp_lab/reporting/study_closure.py`, `family_results`:

- **`sharpe_per_observation`** = mean/std (ddof=1) of the **concatenated OOS
  test net returns** of the RS engine across all 15 folds, per family and
  symbol. No annualization. This is the unit used for the family p-values.
- **`sharpe_annualised`** = `sharpe_per_observation * sqrt(8760)`.

The concatenation is deliberate: it weighs every OOS bar equally instead of
averaging fold Sharpes (which would overweight short folds), at the cost of
mixing fold-specific parameterizations into one series. Both variants appear
in the closure tables; the thesis must state which one each number is.

## 4. Family p-value (raw, before corrections)

`_bootstrap_p_value` in `study_closure.py`: one-sided stationary-bootstrap
test of `mean(OOS net returns) > 0`, null recentred to zero mean, fixed seed.
The block structure preserves autocorrelation; one p-value per family
(best symbol), 13 in total. Smallest raw p = 0.3455.

## 5. Holm–Bonferroni and Benjamini–Hochberg

`src/perp_lab/evaluation/multiple_testing.py` — standard step-down Holm
(FWER) and step-up BH (FDR) over the **13 family p-values only**. Result: 0
rejections under either at α = 0.05. Not computed over CRT or S3 (see
`INVENTARIO_MAESTRO.md`).

## 6. Deflated Sharpe Ratio (DSR)

`multiple_testing.py`, `expected_maximum_sharpe` + `deflated_sharpe_ratio`
(Bailey & López de Prado 2014): the expected maximum Sharpe among N
independent trials under the null, adjusted for skewness and kurtosis of the
return series, is used as the benchmark against which the observed best-family
Sharpe is deflated. Reported for two trial counts: N = 13 families → DSR =
0.139; N = 496,500 configurations → DSR = 1.2·10⁻⁴. Interpretation: the
probability that the best observed Sharpe exceeds what pure selection luck
would produce. Neither count includes CRT (540,000 valid evals) or S3
(60,750): those rounds were run after the closure was frozen.

## 7. PBO — probability of backtest overfitting (CSCV)

`multiple_testing.py`, `probability_of_backtest_overfitting`: combinatorially
symmetric cross-validation over the closure matrix of 13 configurations ×
32,385 OOS observations, 8 partitions → 70 split combinations. PBO = 0.4857:
the in-sample-best configuration falls in the lower half out of sample about
as often as a coin flip, i.e. selection is uninformative. Only the aggregate
was persisted (the per-split logits were not).

## 8. C2 gate — block-bootstrap Sharpe CI (per family × asset × seed cell)

`src/perp_lab/evaluation/study_robustness.py`: moving-block bootstrap of the
OOS return series with block lengths 24/168/720 bars, 500 resamples; the
promotion gate requires the **95% CI of the 168-block Sharpe to exclude 0**.
This is the only diagnostic computed for *every* confirmatory round including
CRT v1 and S3 (via each round's `study_robustness.json`).

## 9. White Reality Check / Hansen SPA

`multiple_testing.py`, `reality_check` / `superior_predictive_ability`:
stationary bootstrap, 2,000 draws, expected block length 24 (prob 1/24),
loss = negative mean OOS return vs the zero benchmark. Executed **only** for
the S1-B and S2-B pilot batches (`reports/gate_s1b/s1b_pilot_report.json`:
RC p = 0.9955, SPA p = 1.0). Not computed at study level for the closure,
CRT, or S3.

## 10. What none of these numbers licenses

- A non-rejected family is "not shown profitable under this protocol", not
  "shown unprofitable".
- Pilot-level cells (S1-B: BTC only, 1 seed; S2-B: 3 seeds) carry far less
  evidence than full-study cells; the closure treats them as tested
  hypotheses, not as equally-powered experiments.
- DSR/PBO/Holm numbers quantify selection risk **within the declared 13-family
  universe**; they say nothing about CRT or S3, whose evidence is reported
  separately with per-cell C1–C6 verdicts only.
