# Reproducing this package

From the repository root (Python 3.12, `uv sync --extra dev` once):

```bash
uv run python scripts/build_ch7_results.py
```

- Reads only closed artifacts (`artifacts/runs/**`, pilot gate reports); no
  new searches, no training, no holdout access.
- Deterministic: `SOURCE_DATE_EPOCH` pinned, no RNG, no timestamps. Verified
  byte-identical across two consecutive full runs (31 files).
- Self-checking: 44 curve-vs-table consistency assertions (every drawn seed
  curve against `total_return_net`, every funded benchmark against
  `bh_total_return`), absolute tolerance 1e-6 on final equity; any mismatch
  aborts the build.

Traceability: the per-study commits and run identities are listed in
`NOTA_ACLARACIONES.md` §4; the closure artifact is
`reports/study_closure/` (commit 232bc372). Source data for every row is the
`run_dir` column of `ch7_results_units.csv`.

Pertinent tests: `uv run pytest tests -k "baseline or robustness or
montecarlo or closure or metrics"` (108 tests) plus the repository gates
(ruff, pyright, full pytest).
