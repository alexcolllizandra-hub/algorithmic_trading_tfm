# Project Progress

## Phase 1 - Foundation, Data Contract and EDA

**Status: IMPLEMENTED AND VERIFIED (offline gate green).**
The full quality gate passes locally. The only check still pending is the
opt-in network test (`pytest -m network`), which performs a real
`data.binance.vision` download and can be run on demand.

_Last updated: 2026-07-30 (EDA notebook restructured to 14 sections; order-flow,
mark-price basis and market-context analyses added; deterministically rebuilt and
executed)._

### Comprehensive EDA notebook (Chapter 4) - final 14-section version

`notebooks/01_comprehensive_exploratory_data_analysis.ipynb` is now generated
deterministically by `scripts/build_eda_notebook.py` (which also ruff-formats its
output) and reorganised into exactly 14 sections:

1. Executive summary and reproducibility
2. Configuration and data loading (centralised config; holdout guard;
   expected-vs-observed count gate that stops on any mismatch)
3. Data sources and analytical scope (Summary Table 1 - dataset inventory)
4. Data integrity and coverage (Summary Table 2 - data-quality assessment;
   resampling consistency incl. trade-count; monthly coverage heatmap)
5. Price dynamics and market episodes (price/drawdown, monthly-returns calendar,
   and a NEW documented-events overlay with a price-only market-stress proxy)
6. Return distributions and tail risk (Summary Table 3 - distribution + VaR/ES)
7. Volatility and temporal dependence (Summary Table 4 - ADF/KPSS/Ljung-Box/ARCH)
8. Market activity, order flow and seasonality (NEW taker-buy imbalance analysis)
9. Funding rates and mark-price basis (NEW matched-timestamp trade-vs-mark basis)
10. BTC-ETH dependence
11. Multi-timeframe comparison (Summary Table 5) with explicit 1h selection
12. Preliminary market-regime analysis (regime figure redesigned as consolidated
    contiguous daily episodes - no per-bar barcode)
13. Main findings and methodological implications (Summary Table 6)
14. Appendix diagnostics (empty gap timeline, return box plots, volume/trade-count
    distributions, hour x weekday heatmap)

Figures are regenerated with the continuous scheme `f01`..`f20` (plus `f21`
market-context and `fa2` appendix heatmap). Two genuinely new analyses were added:
taker-buy order-flow imbalance (`f14`) and trade-vs-mark price basis (`f15`).
Corrected interpretations: gaps are reported as "no gaps detected" (no venue-outage
claim); market activity is positively associated with contemporaneous |return|
(rho~0.41 BTC / 0.40 ETH) but not monotonically with rolling annualised volatility
(rho~-0.01). Extreme returns are never winsorised; histogram axes are clipped for
readability only, with the excluded count reported.

New tested modules: `src/perp_lab/eda/orderflow.py` (taker-buy imbalance),
`src/perp_lab/eda/events.py` (curated documented events + price-only stress proxy),
plus `mark_price_basis` in `funding.py`, `regime_intervals` in `regimes.py` and a
`REGIME_COLORS`/`regime_color` house-style palette. 8 new unit tests added.

Execution: end-to-end from a clean kernel, 0 error cells; 22 PNG + 22 PDF figures
and 41 CSV/Markdown tables exported. Observed counts match the contract exactly:
BTC/ETH 5m 631,296; 15m 210,432; 1h 52,608; funding 6,576 per asset. Date range
2020-01-01 .. 2025-12-31 23:55 UTC; no 2026 observation is loaded or exported.

#### Previous 12-section version (superseded)

The earlier 12-section layout mapped 1:1 to Chapter 4:

1. Objectives, scope and research questions
2. Reproducibility and holdout protection
3. Data sources, schema and integrity (comprehensive data-quality table, monthly
   5m coverage heatmap, gap structure with no empty axes, funding/mark coverage,
   resampling-consistency test)
4. Price evolution and market episodes (+ monthly-returns calendar)
5. Return distributions and tail risk (redesigned readable distribution figure,
   full stats incl. IQR/MAD/quantiles/Jarque-Bera, historical VaR/ES, ranked
   extreme events with leak-free context)
6. Volatility and temporal dependence (ADF/KPSS/Ljung-Box/ARCH-LM, rolling
   30-day vol/skew/kurt, ACF)
7. Volume, liquidity proxies and seasonality (dollar volume, Amihud, ATR/price,
   taker-buy ratio; Kruskal-Wallis; hour x weekday heatmap)
8. Funding-rate characteristics (shares/tails, lag-1/lag-3 persistence, runs,
   yearly summary, leak-free future-return relation)
9. BTC-ETH dependence (Pearson/Spearman, conditional-on-regime/sign, tail
   co-exceedance, block-bootstrap CI, documented lead-lag sign convention)
10. Multi-timeframe comparison and explicit 1h selection (decision table)
11. Preliminary market regimes (vol-regime price shading, full transition matrix
    incl. self-transitions + conditional-on-leaving, duration/characteristics
    tables, threshold+window sensitivity)
12. Main findings and methodological implications (findings table with downstream
    component mapping; Chapter-4 mapping)

New reusable, tested modules under `src/perp_lab/eda`: `coverage`, `stationarity`,
`rolling`, `extremes`, `liquidity`, `calendar`, plus extensions to `correlation`,
`funding`, `seasonality`, `regimes`. Artifact system extended to export vector
PDF alongside PNG. Development window 2020-01 .. 2025-12 (holdout frozen at
2026-01-01, never loaded). Notebook executes end-to-end from a clean kernel with
0 error cells (~215 s); generates 19 figures (PNG+PDF), 40 tables (CSV+Markdown)
and 59 metadata sidecars under `reports/{figures,tables,metadata}/eda`.

Gate after the upgrade: `ruff check` and `ruff format --check` clean; `pyright`
0 errors; `pytest -m "not network"` 121 passed.


### Implemented (code written, not yet executed)

- Project scaffold: `pyproject.toml` (uv, Phase-1 deps), `.python-version`,
  `.gitignore`, `README.md`, `.env.example`.
- Config: pydantic models + YAML loaders (`src/perp_lab/config`, `configs/`).
- Data layer: `ExchangeDataProvider` ABC, `BinanceVisionBulkProvider`,
  `CcxtIncrementalProvider`, `bars.py`, `splits.py`, `manifest.py`, `download.py`.
- Validation: pandera schemas + quality report (`src/perp_lab/validation`).
- EDA library: returns, volatility, dependence, seasonality, correlation,
  regimes, plots (`src/perp_lab/eda`).
- CLI: `perp-lab download` / `perp-lab validate`.
- Tests: unit + offline integration; opt-in network test marked `network`.
- Docs: data contract, experimental protocol, roadmap, ADRs 0001-0003.
- Governance: `AGENTS.md`, 5 rules, 6 skills, 4 subagents.

### Quality gate (real results)

| Check | Status | Result |
|-------|--------|--------|
| `uv sync --extra dev` | PASS | `.venv/` created, `uv.lock` generated (149 pkgs, CPython 3.12.3) |
| `uv run ruff check .` | PASS | `All checks passed!` |
| `uv run ruff format --check .` | PASS | `104 files already formatted` |
| `uv run pyright` | PASS | `0 errors, 0 warnings, 0 informations` |
| `uv run pytest -m "not network"` | PASS | `129 passed, 1 deselected` |
| `uv run pytest -m network` (optional) | PENDING | on-demand real download |

Scaffold fixes applied to reach green: removed an unused import; replaced 5
unused/blind lint directives; `dict()` -> literals in 2 tests; typed schema dicts
as `DataType | type[DataType]`; `matplotlib.figure.Figure` import; `np.asarray`
around `acf`; typed `scipy.jarque_bera` result; `cast(datetime, ...)` for Polars
`.max()/.min()` in tests; corrected a `.item()` misuse in one bar-resampling test.

Note: one harmless `DeprecationWarning` from pandera internals (`pl.concat`
`how='horizontal'`); not from project code.

### Terminal-dependent tasks

1. [DONE] Re-confirmed and deleted the legacy virtualenv (`Lib/`, `Scripts/`,
   `pyvenv.cfg`). New env = `.venv/` managed by uv only.
2. [DONE] Generated `.venv/` and `uv.lock` via `uv sync --extra dev`.
3. [DONE] Ran the full quality gate; fixed only scaffold errors; re-ran until green.
4. [DONE] Recorded the real output above.
5. [IN PROGRESS] Initialize Git and prepare a private GitHub repo (no push
   without explicit confirmation).

### Decisions locked

- Data source: Binance USDT-M via `data.binance.vision` (+ CCXT incremental).
- Symbols: `BTCUSDT`, `ETHUSDT`. Base 5m; derived 15m/1h from 5m.
- Cutoff: `2026-07-01` (exclusive) -> last bar opens 2026-06-30 23:55 UTC.
- Frozen holdout: `[2026-01-01 00:00 UTC, 2026-07-01)`. See ADR 0003.

### Git / versioning

- `.gitignore` hardened to exclude secrets, virtualenvs, heavy data
  (zip/parquet/csv/db), logs, caches and temp artifacts; manifests, code,
  configs, docs and `uv.lock` are tracked.
- Repository initialization and the private-remote connection are handled in the
  Git step (local commit only; no push/publish without explicit confirmation).
