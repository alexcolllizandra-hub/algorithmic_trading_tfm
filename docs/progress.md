# Project Progress

## Phase 1 - Foundation, Data Contract and EDA

**Status: IMPLEMENTED AND VERIFIED (offline gate green).**
The full quality gate passes locally. The only check still pending is the
opt-in network test (`pytest -m network`), which performs a real
`data.binance.vision` download and can be run on demand.

_Last updated: 2026-07-30 (gate executed)._

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
| `uv run ruff format --check .` | PASS | `63 files already formatted` |
| `uv run pyright` | PASS | `0 errors, 0 warnings, 0 informations` |
| `uv run pytest -m "not network"` | PASS | `58 passed, 1 deselected` |
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
