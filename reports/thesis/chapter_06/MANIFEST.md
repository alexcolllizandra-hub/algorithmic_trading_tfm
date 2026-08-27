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

---

## Extended set (added on request — choose per section)

### Chapter 6 — method-and-diagnostic figures (core + optional)

| File | Shows | Section | Suggested caption (EN) |
|---|---|---|---|
| `fig_2_6_data_snooping.png` | 10,000 random ±1 strategies on real 1h returns: the best Sharpe grows like sqrt(2 ln N / T) and crosses 1.0 at ~80 tries | 6.1/6.2 opener | *The mechanics of data snooping: the maximum Sharpe among N random strategies on the real development returns tracks the E[max] growth curve, crossing 1.0 within about eighty attempts.* |
| `i03_optimism_structure.png` | How selection optimism varies by family and fold (structure, not just the mean) | 6.2 optional | *Selection optimism is not uniform: per-family and per-fold decomposition of the validation-minus-test Sharpe gap across the 3,000 R3 fold winners.* |
| `k01_bootstrap_distribuciones.png` | Block-bootstrap distributions of OOS statistics for the real seeds (the machinery behind the C2 gate) | 6.5 method illustration | *Moving-block bootstrap distributions of the out-of-sample statistics; the C2 promotion gate requires the 168-bar-block Sharpe interval to exclude zero.* |
| `k02_permutacion_secuencia.png` | Sequence-permutation null vs the real result | 6.5 optional (or Ch. 8) | *Sequence-permutation null: destroying the temporal order of positions while keeping their marginal distribution brackets the realized result.* |
| `k03_nula_con_la_estrategia_dentro.png` | "Null with the strategy inside": circular-shift null distribution with the observed statistic marked — the closest existing analogue to a Reality-Check null plot | 6.5 optional (or Ch. 8) | *Circular-shift null with the strategy inside: 1,000 rotations of the position series against the real prices; the observed return sits inside the null mass.* |

### Chapter 7 boundary — results comparisons (use there, not in 6)

| File | Shows | Why chapter 7 |
|---|---|---|
| `j05_crt_round.png/.pdf` | CRT_INTRADAY_V1: criteria heat map (BTC) + per-seed annualised Sharpe of the concatenated OOS series, both assets; 0/18 cells promoted | Post-closure round verdict (notebook 05 §8; regenerate: `build_results_notebook.py` + `run_notebooks.py 05`) |
| `j06_overlay_and_dl.png/.pdf` | Gate S3 seed distribution vs its R2 carrier (BTC −0.71→−0.99, ETH −0.49→−0.68, not seed-paired by design) + volforecast QLIKE with DM p-values | Post-closure rounds verdict |
| `t10_crt_cells.md/.csv` | Seeds passing each criterion per CRT family×asset cell | Per-round result |
| `t11_s3_overlay.md/.csv` | S3 vs carrier seed-distribution summary (test-fold Sharpe, RS) | Per-round result |
| `t12_volforecast.md/.csv` | OOS QLIKE/MSE of naive, HAR, LSTM per asset | Annex result |
| `j01_promotion_criteria.png` | C1–C6 pass counts per family×asset cell | It is the per-round verdict, not the method |
| `j04_regime_conditioned.png` | Regime-conditioned re-evaluation of the top cells | Results comparison |
| `i04_rs_vs_ga.png` | Paired RS vs GA outcomes | Engine comparison (results) |
| `i05_seed_instability.png` | Seed dispersion of OOS results | Results dispersion |
| `i06_convergence.png` | Search convergence within budget | Search behaviour |

### Still category 3 (would need new computation — not run)

- CSCV logit distribution (only the aggregate PBO=0.486 was persisted).
- White RC / Hansen SPA null distributions (only p-values persisted).

---

## Scope of the closure diagnostics (read before citing any number)

Every study-level diagnostic in this folder — Holm/BH (t04), trial-count
sensitivity (t05), DSR (t06), PBO — covers **only the 13-family universe
closed on 2026-08-13** (496,500 unique evaluated configurations; 284
heterogeneous units = family × asset × seed × engine). That universe mixes
evidence of very different depth:

- R2 momentum and the five R3 families: full studies, 2 assets × 10 seeds,
  budgets 300/100 per fold per engine.
- The four S1 families: **pilot evidence only** (BTC, 1 seed, budget 25);
  the full-study S1-C configs exist but were never executed.
- The three S2 families: pilot evidence (2 assets, 3 seeds, budget 25).

Two later confirmatory rounds sit **outside** this closure and outside every
number above:

- **CRT_INTRADAY_V1** (9 families, 2×10×15, budget 100, ~540,000 valid
  evals): 0/18 cells promoted; per-cell C1–C6 verdicts in
  `crt_v1_gate_summary.csv/.md` (chapter 7 material). Study-level
  Holm/BH/DSR/PBO for this round: **not computed**.
- **Gate S3 macro_event_brake** (2×10×15, budget 100, 60,750 evals incl.
  pilot): 0/10 seeds positive; preregistered as N := N+1 (ADR 0019).
  Extended corrections: **not computed**.

Consequences for the text: any sentence citing "496,500 trials" or "13
families" refers to the closure only; the project-wide confirmatory total is
23 family hypotheses and ≈1,157,250 valid evaluated configurations, and no
correction has been run over that extended universe. Merging the universes
post hoc would require re-running the four corrections over a rebuilt
23-family OOS matrix — with the caveat that the designs are not exchangeable
(1–10 seeds, budgets 25–300). See `INVENTARIO_MAESTRO.md` and
`METRICAS_DEFINICIONES.md`.
