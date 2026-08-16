# perp-lab

Reproducible framework for **discovering and validating interpretable intraday
trading strategies** on Bitcoin and Ether **USDT-M perpetual futures**.

This repository accompanies a Master's Thesis (TFM). It is being built in
phases; the code currently covers **Phase 1** only:

- Project foundation and reproducible environment.
- A formal **data contract** for the market data used throughout the thesis.
- Bulk data acquisition from `data.binance.vision` (+ CCXT for incrementals).
- Data-quality validation.
- A reusable **exploratory data analysis (EDA)** library.

Strategy grammar, search, backtesting, market-regime detection, meta-labeling,
MLOps, API and dashboard are intentionally **out of scope** for Phase 1. See
[docs/roadmap.md](docs/roadmap.md).

## Research-integrity principles

These principles are enforced by the project rules in `.cursor/rules/` and must
never be violated:

1. **Chronological splits only.** No random train/test splits.
2. **The final holdout is frozen against EDA-driven decisions and parameter
   selection**, and is opened at most once. It *was* opened, on 2026-08-13, over
   a candidate that the study-level correction had already rejected. That reading
   is withheld pending a provenance audit, the partition is now consumed, and no
   conclusion in this repository depends on it. See
   [docs/methodology/holdout_audit_status.md](docs/methodology/holdout_audit_status.md).
3. **Raw data is immutable.** `data/raw/` is written once and never edited.
4. **No silent outlier removal.** Extreme observations are flagged and
   investigated, not automatically dropped.
5. **Everything is reproducible.** Deterministic seeds, pinned environment,
   and a manifest (source, symbol, timeframe, period, timestamp, hash) for
   every processed dataset.
6. **Crypto is 24/7.** Annualization uses 365 days, not the 252-day equity
   convention.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/) for environment and dependency management.

## Setup

> Note: an older stray virtualenv (`Lib/`, `Scripts/`, `pyvenv.cfg`) may exist
> at the repository root from a previous project. It is git-ignored and can be
> deleted. The commands below create a clean `.venv/` managed by uv.

```bash
# 1. Create the environment and install dependencies (runtime + dev)
uv sync --extra dev

# 2. Run the quality gate
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest -m "not network"

# 3. (optional) register the Jupyter kernel for the EDA notebooks (later phase)
uv run python -m ipykernel install --user --name perp-lab
```

## Repository layout

```
src/perp_lab/        # library code (importable, testable)
  config/            # pydantic-settings models loaded from configs/*.yaml
  data/              # providers, download, bar construction, manifests
  validation/        # pandera schemas + data-quality reporting
  eda/               # reusable EDA statistics and plotting functions
  utils/             # time, hashing, logging, seeds
configs/             # YAML configuration (data_contract.yaml, eda.yaml)
data/                # raw / validated / processed / manifests (git-ignored except manifests)
docs/                # data contract, experimental protocol, roadmap, ADRs
reports/             # generated figures and tables
tests/               # unit + integration tests
.cursor/             # project rules, skills and subagents (project governance)
```

## Command reference

| Task | Command |
|------|---------|
| Install env | `uv sync --extra dev` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
| Type-check | `uv run pyright` |
| Tests (offline) | `uv run pytest -m "not network"` |
| Tests (incl. network) | `uv run pytest` |
| Download data | `uv run perp-lab download --config configs/data_contract.yaml` |

## License

MIT
