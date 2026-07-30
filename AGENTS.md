# AGENTS.md

Operating contract for AI agents and contributors on **perp-lab**, the codebase
for a Master's Thesis on reproducible strategy discovery and validation for
BTC/ETH USDT-M perpetual futures.

## Mission

Build a reproducible, auditable framework. Scientific integrity and
reproducibility outrank features. A negative but rigorous result is a valid
thesis outcome; a positive result obtained by leakage or overfitting is not.

## Current phase

**Phase 1: data + EDA.** In scope: environment, data contract, acquisition,
quality validation, reusable EDA. **Out of scope (do not create yet):** strategy
grammar, search, backtesting, regime modelling, meta-labeling, MLflow, API,
frontend. See [docs/roadmap.md](docs/roadmap.md).

## Stack

- Python 3.12, managed by **uv** (`pyproject.toml` + `uv.lock`).
- Data: **Polars**, PyArrow, DuckDB. Config: **Pydantic** / pydantic-settings.
- Validation: **Pandera** (Polars). Stats/EDA: NumPy, SciPy, statsmodels, arch.
- HTTP: httpx. Exchange: CCXT (incremental only). Plots: Matplotlib, Plotly.
- Quality: **pytest**, **Ruff**, **Pyright**.

## Layout

```
src/perp_lab/{config,data,validation,eda,utils}   library code
configs/                                          YAML config (data contract, EDA)
data/{raw,validated,processed,manifests}          data lake (git-ignored except manifests)
docs/                                             data contract, protocol, roadmap, ADRs
reports/{figures,tables}                          generated artifacts
tests/{unit,integration}                          tests
```

## Canonical commands

```bash
uv sync --extra dev          # install runtime + dev deps
uv run ruff check .          # lint
uv run ruff format .         # format
uv run pyright               # type-check
uv run pytest -m "not network"   # tests (offline)
uv run perp-lab download --config configs/data_contract.yaml
uv run perp-lab validate --config configs/data_contract.yaml
```

## Non-negotiable rules (research integrity)

1. **Chronological splits only.** Never introduce random train/test splits.
2. **The holdout is frozen.** Never use it for EDA-driven decisions or parameter
   selection. It is opened once for the final report.
3. **Raw data is immutable.** Never edit files under `data/raw/`.
4. **Flag, never auto-drop** extreme observations.
5. **No look-ahead.** Features/decisions use past data only (rolling/expanding).
   Full-sample statistics are for labeled descriptive EDA only.
6. **Reproducibility.** Seed via `AppSettings.seed`; every processed dataset
   gets a manifest (provenance + SHA-256).
7. **24/7 annualization** with 365 days, not 252.

## Engineering conventions

- Business logic lives in `src/perp_lab/`, is typed, and is unit-tested.
  Notebooks narrate and call library functions; they hold no reusable logic.
- Prefer small, pure functions returning Polars frames; keep I/O at the edges.
- New/changed dependencies go through `uv add` (never hand-edit versions).
- Significant, hard-to-reverse decisions get an ADR in `docs/decisions/`.
- Timestamps are tz-aware UTC; bars are labeled by open time, left-closed.

## Definition of done for a change

- `ruff check`, `ruff format --check`, `pyright`, and `pytest -m "not network"`
  all pass.
- New behavior has tests. Docs/ADRs updated when decisions change.
