# Roadmap

The project is built in phases. Only **Phase 1** is implemented. Later phases
are listed so scope is explicit; do not implement them yet.

## Phase 1 - Foundation, Data Contract and EDA (current)

Deliverables:
- Reproducible environment (uv, Python 3.12), quality gate (Ruff, Pyright, pytest).
- Data contract ([configs/data_contract.yaml](../configs/data_contract.yaml),
  [data_contract.md](data_contract.md)).
- Acquisition: bulk `data.binance.vision` + CCXT incremental, checksum-verified.
- Layered data lake (raw/validated/processed) with committed manifests.
- Data-quality validation (gaps, duplicates, OHLC consistency, extreme flags,
  coverage).
- Reusable EDA library (`src/perp_lab/eda`).

### Acceptance criteria

- [ ] `uv sync --extra dev` reproduces the environment from `uv.lock`.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`,
      and `uv run pytest -m "not network"` all pass.
- [ ] `docs/data_contract.md` is finalized and `configs/data_contract.yaml`
      drives ingestion.
- [ ] Bulk download + checksum verification works for BTCUSDT & ETHUSDT 5m;
      15m/1h are reproducibly built and cross-checked vs native klines
      (`uv run pytest -m network`).
- [ ] Quality report generated; gaps/dupes/extremes flagged (none silently
      dropped).
- [ ] Final holdout reserved, hashed, and documented as untouched.
- [ ] Every processed dataset has a committed manifest with a stable hash.
- [ ] Governance files (AGENTS.md, rules, skills, subagents) in place.

## Phase 2 - Strategies and Backtesting (not started)

Strategy grammar (momentum, breakout, mean-reversion), benchmarks and control
signals; a transparent backtesting engine (fees, slippage, funding, realistic
timing); position sizing and risk limits; walk-forward validation with purging
and embargo.

## Phase 3 - Strategy Discovery (not started)

Random-search baseline and a constrained evolutionary search with matched
budget; multi-objective fitness with complexity penalty; candidate promotion gate.

## Phase 4 - Regimes and Meta-Labeling (not started)

Regime detection; triple-barrier labeling; meta-labeling with Logistic
Regression, Random Forest, LightGBM; probability calibration, SHAP, thresholds.

## Phase 5 - MLOps and Platform (not started)

MLflow experiment tracking, dataset versioning, reproducible pipelines
(Prefect), FastAPI backend, Next.js dashboard, paper trading / testnet, drift
and performance monitoring.
