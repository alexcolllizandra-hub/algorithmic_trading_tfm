---
name: define-data-contract
description: Define or amend the project data contract (exchange, contracts, timeframes, period, holdout, integrity) in configs/data_contract.yaml and docs/data_contract.md. Use when adding a symbol, changing the period/cutoff, altering timeframes, or revising holdout/integrity rules for the perp-lab thesis.
disable-model-invocation: true
---

# Define data contract

The data contract is the single source of truth for which market data the
thesis uses. Changing it is a versioned decision.

## Workflow

1. Read the current `docs/data_contract.md` and `configs/data_contract.yaml`.
2. Confirm the change with the user if any of these move: exchange, symbols,
   base/derived timeframes, cutoff, or holdout policy.
3. Edit `configs/data_contract.yaml` (machine-readable) AND
   `docs/data_contract.md` (rationale) together. Keep them consistent.
4. Bump `version` in both files (semver).
5. Add an ADR under `docs/decisions/` explaining context, decision, consequences.
6. Validate: `uv run python -c "from perp_lab.config import load_data_contract; print(load_data_contract('configs/data_contract.yaml'))"`.

## Invariants to preserve

- Base timeframe is downloaded; derived timeframes are integer multiples built
  by resampling.
- `cutoff_date` is exclusive and after every contract's listing date.
- The holdout is the final block before the cutoff and is frozen.
- Every field has a rationale in `docs/data_contract.md`.
