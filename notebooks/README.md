# EDA notebooks (v0.1)

Six narrative, reproducible notebooks that constitute the first exploratory
data-analysis iteration for the thesis. They are **analytically deep but
technically thin**: all statistical, validation and plotting logic lives in
tested modules under `src/perp_lab/`; the notebooks load configuration, call
those functions, arrange results and provide academic interpretation.

| # | Notebook | Question it answers |
|---|----------|---------------------|
| 01 | `01_data_acquisition_and_quality.ipynb` | Is the data fit for analysis? Provenance, coverage, integrity. |
| 02 | `02_price_and_return_dynamics.ipynb` | How do prices and returns behave and aggregate? |
| 03 | `03_volatility_and_temporal_dependence.ipynb` | Is volatility persistent and clustered? Are returns predictable? |
| 04 | `04_volume_funding_and_market_activity.ipynb` | How do activity, seasonality and funding behave? |
| 05 | `05_cross_asset_and_multitimeframe_relationships.ipynb` | How do BTC and ETH co-move across timeframes? |
| 06 | `06_exploratory_regime_analysis.ipynb` | Can we characterise interpretable market regimes? |

## Research-integrity rules

- **Frozen holdout** `[2026-01-01 00:00 UTC, 2026-07-01 00:00 UTC)` is never used
  for decisions. Notebooks 2–6 load only the `development` partition; a runtime
  guard (`assert_no_holdout`) raises if any holdout timestamp leaks in.
- Notebook 1 may inspect neutral properties of the holdout (existence, hashes,
  schema, coverage) but never computes anything that influences indicators,
  thresholds, features or modelling decisions.
- Every notebook prints its active period and states explicitly whether the
  holdout was excluded.

## How to run

Notebooks are generated from a single source of truth and executed from clean
kernels:

```powershell
# 1. Ensure the data lake exists (bulk download, cached under data/raw/)
uv run perp-lab download --config configs/data_contract.yaml

# 2. (Re)generate the notebook files from scripts/build_notebooks.py
uv run python scripts/build_notebooks.py

# 3. Execute every notebook in order from a clean kernel
uv run python scripts/run_notebooks.py
```

`scripts/run_notebooks.py` writes an execution report to
`reports/metadata/eda/notebook_execution.json`. Figures, tables and their
reproducibility metadata are written under `reports/figures/eda/`,
`reports/tables/eda/` and `reports/metadata/eda/`.

## Outputs

Generated artefacts (figures `*.png` at 300 DPI, tables `*.md`/`*.csv`, metadata
`*.json`) are ignored by Git by default; regenerate them by running the
notebooks. Committed narrative lives in `docs/eda_findings_v0.1.md`.
