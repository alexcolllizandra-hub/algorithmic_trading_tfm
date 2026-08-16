# Thesis notebooks

Five narrative, reproducible notebooks that carry the thesis from raw market data to the closed
study. They are **analytically deep but technically thin**: every statistical, validation and plotting
routine lives in tested modules under `src/perp_lab/`; the notebooks load configuration, call those
functions, arrange results and provide academic interpretation.

Each notebook is a **generated artifact**. Do not edit the `.ipynb` by hand — edit its builder under
`scripts/` and regenerate, so the narrative and the code stay in one source of truth.

| # | Notebook | Builder | Question it answers |
|---|----------|---------|---------------------|
| 01 | `01_comprehensive_exploratory_data_analysis.ipynb` | `build_eda_notebook.py` | What does the market data look like, and is it fit for analysis? |
| 02 | `02_causal_features_and_leakage.ipynb` | `build_features_notebook.py` | What is the model allowed to know, and when? What does leakage cost? |
| 03 | `03_backtesting_and_walk_forward.ipynb` | `build_backtest_notebook.py` | How does a signal become a filled position, what does it cost, and what makes a fold out-of-sample? |
| 04 | `04_strategy_search_and_overfitting.ipynb` | `build_search_notebook.py` | How much of a searched result is genuine structure and how much is selection bias? |
| 05 | `05_study_closure_and_multiple_testing.ipynb` | `build_results_notebook.py` | What did the whole study find, and does anything survive correction? |

Notebooks 01–03 compute from the local data lake. Notebook 04 reads the closed R3 study under
`artifacts/runs/r3_full_budget100_ga21/`. Notebook 05 reads the closure artifacts under
`reports/study_closure/`.

## Research-integrity rules

- **Frozen holdout** `[2026-01-01 00:00 UTC, 2026-07-01 00:00 UTC)` is never used for any decision.
  Notebooks 02–04 load only the `development` partition, and a runtime guard (`assert_no_holdout`)
  raises if any holdout timestamp leaks in.
- **The holdout reading is not published.** It was opened once on a pre-declared candidate, but the
  repository records that opening as `HOLDOUT_LOCKED` pending a provenance audit
  (`docs/methodology/holdout_audit_status.md`). Notebook 05 explains the lock and reports no holdout
  metric.
- **No silent outlier removal.** Extreme observations are flagged, never winsorised. Figure axes are
  clipped for readability only, with the excluded count reported.
- Every notebook prints its active period and states explicitly whether the holdout was excluded.

## How to run

```bash
uv run python scripts/build_features_notebook.py
```

```bash
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/02_causal_features_and_leakage.ipynb
```

Figures (`*.png` at 300 DPI plus vector `*.pdf`), tables (`*.md`/`*.csv`) and reproducibility metadata
(`*.json`) are written under `reports/{figures,tables,metadata}/<area>`, where `<area>` is `eda`,
`features`, `backtest`, `search` or `closure`.
