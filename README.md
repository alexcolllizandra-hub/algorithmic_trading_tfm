# perp-lab

**Reproducible discovery and validation of interpretable intraday trading
strategies on BTC/ETH USDT-M perpetual futures** — the research platform and
evidence base of a Master's Thesis in Data Science (La Salle — URL).

**Headline result: a rigorous negative.** Across 14 pre-registered strategy
family gates (R2–R3, S1, S2, CRT, S3) — 2 assets × 10 seeds × 15 expanding
walk-forward folds, 1.17 M candidate evaluations under realistic costs —
**no family met the six frozen promotion criteria**, and no result survives
study-level multiple-testing correction (Holm/BH, Deflated Sharpe, SPA,
PBO = 0.49). Two annexes measure why: predictability in this market lives in
the *variance* (forecastable even by a 4-parameter HAR; an LSTM adds no
separable margin) and does not extend to the *sign*. The thesis's
contribution is the machine that makes such a claim auditable.

## What is in this repository

| Layer | Where | What |
|---|---|---|
| Research code | `src/perp_lab/` | 22 packages: data contracts + causal features, vectorised backtester (next-open, fees + slippage + realized funding), RS/GA search with budget parity, walk-forward orchestration, robustness battery (C1–C6), multiple testing, meta-labeling, EDA library, run identity/tracking, read-only API |
| Tests | `tests/` | 1,560+ pytest (unit, property/invariant, integration, pinned-output, estimator-vs-synthetic); 112 vitest for the web engine |
| Notebooks | `notebooks/` | 8 executed, deterministic notebooks (generated from `scripts/build_*_notebook.py`; zero loose logic) narrating data → EDA → features → backtest → search → closure → meta-labeling → Monte Carlo |
| Frozen evidence | `reports/tables/`, `reports/metadata/`, `reports/study_closure/` | every table/figure the thesis cites, with provenance sidecars (dataset SHA-256, commit, config) |
| Thesis figure builders | `scripts/build_ch*_figures.py`, `scripts/build_*_annex*.py` | regenerate every chapter figure deterministically (seed 42) |
| Data contracts | `configs/`, `data/manifests/` | frozen YAML contracts and per-dataset SHA-256 manifests (market data itself is not committed; see below) |
| Governance | `docs/decisions/` (19 ADRs), `docs/methodology/` | pre-registrations, protocol, the outer-fold contamination incident and its correction, holdout audit status |
| Web panel | `apps/web/` | bilingual Next.js dashboard over the frozen artifacts + an in-browser strategy laboratory (TypeScript port of the engine) |

## Research-integrity principles (enforced in code)

1. **Chronological splits only** — expanding walk-forward (15 folds,
   730/90/90/90 days); purge 96 / embargo 118 bars derived, not chosen.
2. **Frozen holdout** `[2026-01-01, 2026-07-01)` — gated loader raises on any
   leak; opened exactly once (2026-08-13) on a pre-declared candidate; the
   reading is withheld pending a provenance audit and no conclusion depends
   on it (`docs/methodology/holdout_audit_status.md`).
3. **Pre-registration** — families are frozen (hypothesis, space, contract)
   before any bar is simulated; every new hypothesis pays N := N + 1.
4. **Identity, not naming** — each run records a SHA-256 fingerprint over the
   resolved config, contracts, data hashes and code state; a stale-claims
   sweep in CI fails the build if a committed document asserts a result no
   artifact backs.

## Reproducing

```bash
uv sync --extra dev          # locked Python 3.12 environment
uv run pytest -m "not network" -q
uv run python -m perp_lab.cli download   # rebuilds the data lake from data.binance.vision
                                          # (byte-identical to the recorded SHA-256 manifests)
uv run python scripts/run_notebooks.py    # re-executes the 8 notebooks
uv run python scripts/build_ch5_figures.py  # (or any other chapter builder)
```

The web panel: `npm install && npm run dev` inside `apps/web` (the strategy
laboratory is fully client-side; study pages use the read-only API:
`uv run uvicorn perp_lab.api.main:app`).

Market data is **not** committed (only its manifests are). A full
re-ingestion on 2026-08-19 reproduced every dataset with identical SHA-256 —
the recorded hashes are the ground truth the download must match.

## Scope

This is a research system, not a live-trading venue: no order-book queueing,
partial fills or latency modelling. Its purpose is that every number in the
thesis can be traced from source data to statistical verdict.
