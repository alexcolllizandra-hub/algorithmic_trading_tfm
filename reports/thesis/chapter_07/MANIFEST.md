# Chapter 7 — Experimental Rounds and Results
## Export manifest

Everything in this folder derives from **closed artifacts only** (no new
searches, no training, no significance tests, no holdout access). Regenerate
with `uv run python scripts/build_ch7_results.py` (deterministic: no
timestamps, no RNG; verified byte-identical across two runs). Chapter 6 owns
the method figures (optimism, DSR/PBO, RS-vs-GA, multiple testing) — none is
repeated here.

**Benchmark convention (binding for every equity figure and table).** The
buy-and-hold columns and curves are the study's FUNDED always-long perp
baseline: `oo_return − funding_rate_in_bar` per bar, minus one 5 bps entry at
the contract cost rate (`evaluation/baselines.py::_evaluate`). BTC +52.3%,
ETH −21.9% over the OOS window; the price-only return (+100.7% / +0.9%) is a
different quantity and is drawn nowhere. The builder asserts, on every
regeneration, that each drawn curve's final equity equals its tabulated total
(44 checks, absolute tolerance 1e-6 on final equity) — a mismatch aborts the
build. Earlier discrepancies (benchmark convention, the withdrawn S1-B
p=0.06, round-interpretation fixes) were resolved before this package was
frozen.

## Documents

| File | Contents | Proposed location |
|---|---|---|
| `ch7_hypotheses_rules.md` | Hypothesis, entry/exit rules, searched grids, active execution controls, and code/config/prereg paths for every executed family (R2, R3, S1-B, S2-B, CRT v1, S3), plus the R1 contamination note and known documentation gaps | Backbone of sections 7.1–7.6 |
| `ch7_rounds_summary.md/.csv` | One row per round: hypothesis → main result → closure reason | Opening table of the chapter |

## Tables

| File | Grain | Key columns / units | Source |
|---|---|---|---|
| `ch7_results_units.csv` (+ `.md` RS digest) | family × asset × engine × seed, 640 rows (16 full-study families) | OOS window, 15 folds, budget/fold/engine, unique evals per unit-engine (budget×15), net total return, max drawdown, n_trades, `sharpe_concat_ann` (annualised Sharpe of the concatenated OOS series), `mean_fold_test_sharpe` (mean across folds of the frozen winner's fold-test Sharpe — a different aggregation, never comparable to the former), buy & hold return/Sharpe/DD over the same bars, four per-seed criterion booleans | `study_robustness.json` per_run + `*_fold_winners.json` of each run |
| `ch7_criteria.csv` | family × asset × criterion (full studies) | seeds passing / required (6 of 10) / met, per-round verdict. R2 rows carry only the four criteria its artifact computed; the other two are **not computed** in that artifact | `r3_promotion.by_symbol` (R2: `by_symbol_and_engine`) |
| `ch7_seed_dispersion.csv/.md` | family × asset (RS) | mean/sd/min/max across seeds of `sharpe_concat_ann`; mean across seeds of `mean_fold_test_sharpe`; seeds with positive return; aggregation named in every column header. Dispersion, not confidence intervals | derived from `ch7_results_units.csv` |
| `ch7_results_pilots_s1b.csv` | family × engine (BTC, **1 seed**, budget 25, 375 unique evals per family-engine) | median fold-test Sharpe, folds positive, trades, per-bar mean OOS net return, bootstrap p, mechanical viability — the pilot's own contract; 10-seed criteria do NOT apply | `reports/gate_s1b/s1b_pilot_report.json` |
| `ch7_results_pilots_s2b.csv` | family × asset × seed ({42,43,44}) × engine, 36 rows | compounded OOS return, median fold-test Sharpe, folds positive, trades, bootstrap p, viability; partial-signal rule (P1–P3) lives in the report | `reports/gate_s2b/s2b_pilot_report.json` |

## Figures (PNG 300 dpi + PDF twins)

Seed policy in every figure: **all seeds drawn, none selected**; spread is
dispersion across seeds, never a confidence interval.

| File | Shows | Section |
|---|---|---|
| `fig_7_1_r2_oos_equity` | R2 momentum: concatenated OOS test equity of all 10 RS seeds vs buy & hold on the same bars, BTC and ETH | 7.2 |
| `fig_7_2_r3_families` | R3: per-seed annualised Sharpe (concatenated OOS, RS) of the five families, both assets, mean dash | 7.3 |
| `fig_7_3_volbreakout_partial_signal` | volatility_breakout BTC: (a) criteria pass counts vs the 6/10 majority; (b) OOS equity of all 10 seeds vs buy & hold | 7.3 |
| `fig_7_4_crt_complementary` | (a) pdl_reclaim_long BTC equity, all 10 seeds (positive yet unpromotable); (b) ETH criteria heat map — complements `j05_crt_round` (chapter 6), which shows BTC | 7.5 |
| `fig_7_5_s3_seed_distributions` | Gate S3: per-seed test-fold Sharpe of overlay vs carrier, labelled NOT seed-paired (reduced carrier grid, budget shared with gate parameters) | 7.6 |
| `fig_7_6_rounds_synthesis` | All 16 full-study families: mean and min–max across seeds of the concatenated-OOS annualised Sharpe, colored by round; pilots deliberately excluded (different design) | 7.7 |
| `fig_7_7_crt_example_illustrative` | ILLUSTRATIVE pdl_reclaim_long mechanics on one real archived trade (first trade, fold 0, seed 891022, RS — fixed selection rule, a losing trade): PDL, sweep, reclaim, next-bar-open entry, engine-recorded exit. Not additional evidence | 7.5 (didactic inset) |

Additional tables/docs: `ch7_activity_veto.csv` (min-trades veto per cell —
disqualifier, never a seventh criterion; 0/30 triggered),
`ch7_figure_captions.md` (English captions with engine/assets/seeds/period/
aggregation per figure).

`i06_convergence` is intentionally NOT included: its "unique evaluations"
axis exceeds the per-fold budget of 100 and remains unexplained; do not cite
it until reconciled.

## Reconciliation of counts (verified against candidates parquets)

- Closure: **496,500** = R2 180,000 + R3 300,000 + S1-B pilots 3,000 + S2-B
  pilots 13,500.
- CRT_INTRADAY_V1 valid: **540,000** (9 × 60,000, each family summed over its
  20 run dirs).
- S3 valid study: **60,000** (20 run dirs × 3,000). The S3 pilot
  (`search_macro_event_brake_20260826T164228Z_d02e91`, 750 evals) is excluded
  like every superseded pilot.
- **Project confirmatory total: 1,096,500** (= 496,500 + 540,000 + 60,000).
  A previously circulated 1,157,250 was an arithmetic error, now corrected in
  the chapter-6 inventory. 1,097,250 is the figure if the S3 pilot is counted.
- Discarded (never evidence): CRT aborted/dirty-tree **93,000 across 31 run
  dirs** (24,000 + 9,000 + 60,000); abandoned S3 checkpoint 18,000; smoke 621;
  development 9,244; R2/R3 pilots 20,760.
- CRT family names: the canonical nine are the `frozen_order` of
  `crt_v1_execution.json` (pdl_reclaim_long, pdh_reclaim_short,
  crt_htf_range_reversal, session_liquidity_sweep, session_range_rotation,
  opening_range_breakout_retest, failed_breakout_reversal,
  double_sweep_reversal, crt_three_candle_model). Earlier inventory rows using
  other names (crt_turtle_soup, crt_po3_expansion, …) were wrong and have been
  corrected — they were never aliases.

## Scope guards

The 13-family closure and its diagnostics stay separate from CRT and S3; no
extended global correction has been computed (see chapter 6 MANIFEST).
DSR/PBO are study-level numbers and never appear as per-family columns here.
Meta-labeling, HAR/LSTM and alt-data are annex layers on the same development
data — not main-strategy rounds and not external validation.
