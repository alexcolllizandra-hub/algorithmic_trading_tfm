# Reproducing the chapter-8 package

From the repository root (Python 3.12, `uv sync --extra dev` once):

```bash
uv run python scripts/build_ch8_results.py
```

- Inputs: only archived run artifacts under `artifacts/runs/**` (fold test
  equity/trade parquets of the closed studies) plus the chapter-7 CSVs for
  reconciliation. The holdout parquets are never opened.
- Determinism: master seed 20260829; every scenario draws from
  `SeedSequence([master, blake2b(candidate|scenario|method|block|seed|chunk)])`,
  so results are independent of execution order. `SOURCE_DATE_EPOCH` is pinned
  for the PDF twins. Two consecutive runs must produce byte-identical CSV and
  PNG files (verified at packaging time; see CH8_VERIFICATION.md).
- Self-checking: the builder runs the mandatory checklist (series start at 1,
  ledger/CSV/ch7 reconciliation at 1e-9, 15 folds × 32,385 bars per seed, no
  duplicate timestamps, probability bounds, breach monotonicity, percentile
  ordering, permutation exactness) and ABORTS on any failure.
- Budgets: 1,000 paths per seed × 10 seeds × 2 candidates (path layer),
  4,000 hierarchical primary paths per candidate (with the exposure grid),
  2,000 per sensitivity cell (2 methods × ≤4 blocks × 2 candidates), 1,000
  resamples per trade-level secondary, 1,000 order permutations per seed for
  the concentration table.

Table 8.7 is not recomputed: it cites the executed notebook-07 account
simulation verbatim (`reports/tables/montecarlo/t05_cuenta_fondeada.md`);
regenerate that one with `uv run python scripts/build_montecarlo_notebook.py
&& uv run python scripts/run_notebooks.py 07`.
