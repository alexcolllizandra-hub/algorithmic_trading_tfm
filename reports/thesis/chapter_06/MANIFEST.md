# Chapter 6 — Statistical Validation and Multiple-Testing Control
## Figure/table manifest (copies; originals untouched)

All PNGs are 300 dpi with a vector PDF twin. Regeneration commands re-run the
deterministic notebook builders; none executes new searches or touches the
holdout.

| File | Shows | Original path | Data source | Regenerate with | Section |
|---|---|---|---|---|---|
| `i01_space_vs_budget.png/.pdf` | Exact parameter-space cardinality per family vs the 100-candidate budget (trial accounting input) | `reports/figures/search/i01_*` | `reports/tables/search/t01` ← R3 run artifacts | `uv run python scripts/build_search_notebook.py && uv run python scripts/run_notebooks.py 04` | 6.1 |
| `i02_selection_optimism.png/.pdf` | 3,000 R3 fold winners: validation Sharpe (selector) vs test Sharpe (earned); slope +0.277, mean optimism +4.04, 95% of winners underperform their selection score | `reports/figures/search/i02_*` | `*_fold_winners.json` + fold test ledgers of the closed R3 runs | same as above | 6.2 |
| `j02_multiple_testing.png/.pdf` | (a) raw vs BH vs Holm p-values for the 13 families at α=0.05 — nothing approaches the threshold; (b) Bonferroni threshold vs how trials are counted (13 → 496,500), smallest raw p = 0.345 | `reports/figures/closure/j02_*` | `reports/study_closure/study_level_multiple_testing.json` | `uv run python scripts/build_results_notebook.py && uv run python scripts/run_notebooks.py 05` | 6.4 |
| `j03_deflated_sharpe_pbo.png/.pdf` | (a) observed Sharpe of the best family vs the expected-maximum-Sharpe luck benchmark under 13 and 496,500 trials (DSR 0.139 / 0.0001); (b) CSCV PBO = 0.486 on 70 splits × 32,385 obs | `reports/figures/closure/j03_*` | same closure JSON | same as above | 6.2 / 6.3 |
| `t04_multiple_testing.md/.csv` | Rejections at α=0.05 before/after each correction (0 / 0 / 0) | `reports/tables/closure/t04` | closure JSON | notebook 05 builder | 6.4 (table) |
| `t05_test_count_sensitivity.md/.csv` | Conclusion under four trial definitions: 13 / 22 / 142 / 496,500 | `reports/tables/closure/t05` | closure JSON | notebook 05 builder | 6.1 (table) |
| `t06_deflated_sharpe.md/.csv` | DSR of the best family under both trial counts | `reports/tables/closure/t06` | closure JSON | notebook 05 builder | 6.2 (table) |
| `t02_selection_optimism.md/.csv` | Validation vs test Sharpe of all fold winners (mean optimism +4.04) | `reports/tables/search/t02` | R3 fold winners | notebook 04 builder | 6.2 (table) |

## Suggested captions (English)

- **Fig 6.x (i01):** Exact cardinality of each family's parameter space against
  the per-fold evaluation budget of 100 unique candidates. Trial accounting
  starts here: budgets are defined over unique evaluated configurations, with
  duplicates rejected by candidate hashing.
- **Fig 6.x (i02):** Selection optimism in the closed R3 study. Each point is
  one of 3,000 fold winners; the score that selected it (validation Sharpe)
  systematically overstates the score it earned out of sample (slope 0.277;
  mean optimism +4.04 Sharpe units; 95% of winners underperform their
  selection score).
- **Fig 6.x (j03):** Two selection-aware diagnostics agree. (a) The best
  family's out-of-sample Sharpe against the expected maximum Sharpe that pure
  luck would produce under 13 and 496,500 trials: the deflated Sharpe ratio is
  0.139 and 1.2·10⁻⁴. (b) Combinatorially symmetric cross-validation places
  the probability of backtest overfitting at 0.486 — selection is
  statistically uninformative.
- **Fig 6.x (j02):** Multiple-testing control across the 13 pre-registered
  families. (a) No raw p-value (smallest 0.345) approaches α=0.05 even before
  correction; Holm and Benjamini–Hochberg leave zero rejections. (b) The
  conclusion is insensitive to how the number of hypotheses is counted, from
  13 families to all 496,500 evaluated configurations.

## Verified sources

Closure evidence: `reports/study_closure/study_level_multiple_testing.json`
(generated 2026-08-13, commit 232bc372, holdout_accessed=False). Search
evidence: notebook 04 tables/figures over the closed R3 runs. Implementations:
`src/perp_lab/evaluation/multiple_testing.py` (expected_maximum_sharpe,
deflated_sharpe_ratio, probability_of_backtest_overfitting,
holm_bonferroni, benjamini_hochberg_correction, stationary_bootstrap_indices,
reality_check, superior_predictive_ability) and
`src/perp_lab/evaluation/study_robustness.py` (block-bootstrap Sharpe CI,
blocks 24/168/720, 500 resamples; the C2 gate reads block_168).
