# Chapter 8 — ready-to-write brief (verified numbers, per-section)

Every number below is read from the exported CSVs (regenerable with
`uv run python scripts/build_ch8_results.py`; 92 automatic checks pass on
every build). Global frame: BTCUSDT, random_search, concatenated OOS
2022-03-31 → 2025-12-09 (32,385 hourly bars), net of 4+1 bps/side and
realized funding. **All simulations are conditional diagnostics on the
observed development record: they validate no edge, correct no snooping, and
change no chapter-7 verdict. The holdout was never touched.**

## 8.1 Purpose and scope

- Facts: two descriptively interesting REJECTED candidates from chapter 7 —
  `pdl_reclaim_long` (CRT, 10/10 seeds positive yet unpromotable) and
  `volatility_breakout` (R3, the study's closest cell). R2 momentum BTC
  appears only as observed negative reference in `ch8_observed_seed_metrics.csv`.
- Tables/figures: Table 8.1; audit in CH8_AUDIT.md; contract in
  ch8_method_contract.md.
- Allowed: "risk anatomy of what the search produced, conditional on the
  recorded history". Avoid: any wording implying validation, promotion or
  probability statements about future markets.

## 8.2 Simulation inputs and uncertainty layers

- Inputs reconciled to chapter 7 at 1e-9 (per-seed equity endpoints) and to
  the assignment's reference values (0 discrepancies — CH8_DISCREPANCIES.md).
  Funded benchmark BTC +52.27% (terminal 1.522748) confirmed.
- Observed (Table 8.2, Fig 8.1): pdl — 10/10 positive, mean +14.3%
  (range +7.6%…+21.0%), mean concatenated Sharpe 0.471, mean MDD 10.3%;
  volb — 6/10 positive, mean +10.9% (range −56.2%…+131.4%), mean Sharpe
  0.116. Criteria counts (6/10, 2/10, 0/10, 9/10 / 3/10, 2/10, 0/10, 6/10)
  match ch7_criteria.csv exactly.
- Three layers (Table 8.1): search (10 observed seeds), path (resampling
  within a seed), combined (uniform seed pick → path resample). Say
  explicitly: ten seeds = ten searches over ONE market history; the combined
  layer is a joint sensitivity, not ten market replications; no seed
  averaging into a synthetic strategy anywhere.

## 8.3 Conditional return-path simulation

- Primary spec (frozen core): stationary block bootstrap, ACF-derived blocks —
  167 bars (pdl), 168 bars (volb); hierarchical layer 4,000 paths/family,
  horizon 32,385 bars, W_0 = 1. Master seed 20260829 (retrospective streams).
- Headline (Table 8.3, Figs 8.2–8.3): pdl terminal p05/p50/p95 =
  0.880 / 1.142 / 1.504; P(terminal<1) = 0.204 ± 0.006 (MC SE);
  P(loss>20%) = 0.013; ES5% of terminal return = −0.172.
  volb: 0.265 / 0.962 / 3.786; P(terminal<1) = 0.519 ± 0.008;
  P(loss>20%) = 0.405; ES5% = −0.801.
- Per-seed layer: P(terminal<1) ranges 0.133–0.335 across pdl seeds and
  0.110–0.893 across volb seeds — search uncertainty dominates volb.
- Convergence (ch8_monte_carlo_convergence.csv): estimates stable from 1k to
  4k paths within MC error (pdl P(<1): 0.199→0.204; volb 0.534→0.519).
- Allowed: "simulated outcome ranges conditional on the record". Avoid:
  calling the percentiles confidence intervals on the true edge.

## 8.4 Drawdown and trade-sequence risk

- Table/figs: ch8_drawdown_summary.csv, Fig 8.4; Table 8.4, Fig 8.7,
  ch8_trade_concentration.csv, ch8_trade_secondary_bootstraps.csv.
- pdl: simulated MDD p50 = 11.8%, p95 = 22.1%; P(MDD>20%) = 0.079,
  P(MDD>30%) = 0.004; longest-under-peak duration p50 ≈ 585 days.
  volb: MDD p50 = 49.1%, p95 = 79.8%; P(MDD>30%) = 0.926, P(MDD>50%) = 0.480;
  duration p50 ≈ 844 days.
- Concentration (medians across seeds): top-5 trades carry 31.1% (pdl) vs
  51.3% (volb) of positive P&L; seeds positive after removing their 5 best
  trades: 2/10 (pdl) and 0/10 (volb) — exactly the chapter-7 counts. Worst
  losing streak 10 (pdl) / 11 (volb). The chronological drawdown sits at the
  0.38 (pdl) / 0.27 (volb) percentile of order-permutations (unit: engine
  trade; permutation preserves the trade set exactly, only the order moves;
  IID trade bootstrap destroys temporal dependence — both said in the text).
- Unit caveat: engine-trade episodes; CRT partials live inside an episode;
  stops/R-multiples/exit causes are NOT persisted and are not invented.

## 8.5 Exposure scaling and capital-breach risk

- Table 8.5, Fig 8.5, ch8_exposure_sensitivity.csv (+ MC SE/Wilson in
  ch8_breach_probabilities.csv). Transformation r → m·r (a RETURN multiplier,
  not risk-per-trade, not stop-sizing — both not evaluable from the ledgers);
  absorption at zero if 1+m·r ≤ 0 (never triggered at these multipliers:
  prob_absorbed = 0 everywhere).
- pdl at m=1: P(<90%) = 0.22, P(<80%) = 0.030, P(<50%) = 0.000; at m=2:
  P(<80%) = 0.214, P(<50%) = 0.004. volb at m=1: P(<80%) = 0.686,
  P(<50%) = 0.292; at m=2: P(<50%) = 0.637.
- Breach probabilities are monotone in barrier and multiplier (checked).
- Table 8.7: only the executed notebook-07 prop-firm results
  (volatility_breakout; illustrative, frozen configs); pdl NOT EVALUATED
  under that scenario.

## 8.6 Sensitivity analysis

- Table 8.6, Fig 8.6, ch8_method_sensitivity.csv: stationary vs circular
  moving-block × blocks {24, 168, 720, primary}, 2,000 paths per cell.
- Result to state: conclusions are insensitive — terminal p50 moves within
  1.132–1.143 (pdl) and 0.951–0.973 (volb); P(terminal<1) within
  0.188–0.219 and 0.513–0.530. Method choice and block length do not change
  the qualitative picture.
- Trade-level secondaries agree (median seed 671194 for both, a genuine
  coincidence of the shared seed schedule): e.g. pdl block-trade p05/p95 =
  +0.3%…+50.8% vs observed +23.5%; permutation returns the observed total
  exactly (check enforced).

## 8.7 Interpretation and limitations

- Permitted reading: conditional on the recorded 2022–2025 OOS history, the
  pdl profile is a modest-but-fragile positive (one path in five ends below
  start; profits concentrated in few trades) and volb is a coin flip with
  deep, year-scale drawdowns; leverage magnifies breach risk monotonically.
- Mandatory caveats (all already in the outputs): conditional simulation
  intervals, not CIs on edge; one market history; retrospective elements
  labelled (ch8_method_contract.md); chapter-7 verdicts untouched (both
  candidates remain rejected/unpromotable); holdout untouched and consumed
  for confirmatory use; account scenario illustrative only.
