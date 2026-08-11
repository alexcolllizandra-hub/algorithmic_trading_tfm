# Chapter 5 — Methodology and Experimental Design

## 5.1 Scope and data contract

This chapter operationalises the experimental contract executed in phase gates R1–R3. Assets are **BTCUSDT** and **ETHUSDT** Binance USDT-M perpetual futures. The primary modelling timeframe is **1h** bars (deterministically aggregated from 5m source data). The **development partition** spans `[2020-01-01, 2026-01-01)` UTC. A **frozen holdout** `[2026-01-01, 2026-07-01)` was never opened for design, tuning or reporting in the executed arc (ADR 0003).

All executed experiments (R1–R3) used development data only. Gate **R4 was SKIPPED** because R3 promoted zero families.

## 5.2 Walk-forward geometry and per-fold search

Validation follows **expanding-window walk-forward** with **15 chronological outer folds**. After gate R1 (ADR 0012), candidate search is **independent within each outer fold**: each engine searches using only that fold's validation window, the winner is fingerprinted, and the test slice is scored **once**. Budget parity is enforced **per fold** (100 unique objective evaluations per fold and engine in R3; 300 in R2 momentum).

**Purging and embargo** remove training samples whose label horizon overlaps validation/test windows. Development OOS windows end at latest `2025-12-09 22:00 UTC`, strictly before holdout start.

## 5.3 Interpretable strategy families

Six interpretable families were in scope: **momentum** (R2 baseline) and five R3 families — breakout, mean reversion, volatility breakout, funding, and BTC–ETH confirmation — each motivated from EDA (Chapter 3) and specified in the strategy catalogue. Random Search (RS) is the **confirmatory promotion engine**; the Genetic Algorithm (GA) is a **secondary diagnostic** under identical spaces, budgets, folds and costs.

## 5.4 Costs and next-bar execution

Backtests are **net of provisional transaction costs** (fees, slippage, funding; ADR 0005). Signals computed on bar *t* execute at the **open of bar *t+1***. Robustness criterion C3 stresses **2× fees and slippage** on development OOS ledgers.

## 5.5 Metrics, promotion criteria and veto

Family promotion (R3) required **six criteria** with a **≥6/10 seed majority per asset on both assets** (Random Search): (C1) positive total return; (C2) bootstrap Sharpe CI excludes zero; (C3) survives doubled costs; (C4) beats buy-and-hold; (C5) survives dropping top five trades; (C6) not confined to one fold. **`min_oos_trades_met`** (minimum five OOS trades per seed) is a **separate veto**, not a seventh promotion criterion.

## 5.6 Phase gates R1–R4

| Gate | Purpose | Executed outcome |
|------|---------|------------------|
| **R1** | Restore per-fold temporal validity | **PASSED** — contamination corrected (ADR 0012) |
| **R2** | Re-baseline momentum; RS vs GA | **PASSED** — momentum **rejected**; no GA superiority (ADR 0013) |
| **R3** | Five-family multi-seed evaluation | **CLOSED_NEGATIVE** — **0/5** promotions (ADR 0015) |
| **R4** | Extended robustness on **promoted** families only | **SKIPPED** — not executed |

## 5.7 Reproducibility and leakage prevention

Determinism uses global seed 42 with derived streams. Every run records commit, configuration hash, dataset manifests and resolved protocol. Development code **fails closed** on holdout access. Causal features use past-only rolling/expanding statistics; contemporaneous microstructure fields are lagged ≥1 bar. The R3 thesis reporter reads only allowlisted JSON under the study root and does not recompute backtests.

Meta-labeling (M1/M2), portfolio optimisation and paper trading remain **specified but not executed** in this thesis arc; see Chapter 8 traceability.
