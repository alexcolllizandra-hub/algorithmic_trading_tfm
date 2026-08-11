# Chapter 6 — Experimental Results

## 6.1 Temporal protocol and holdout

Executed phases **R1–R3** used the development partition only; **R4 was SKIPPED**. The holdout `[2026-01-01, 2026-07-01)` remained closed. After R1, search is independent per outer fold (ADR 0012). OOS windows end before holdout start (ADR 0015; R3 thesis report).

## 6.2 Gate R1 — Temporal validity restored

**Outcome: PASSED (2026-08-09).** Fold-isolation tests pass; pilot run `search_momentum_20260809T085829Z_c28e3b` reached budget parity per fold. Superseded pre-R1 results remain marked, not deleted (ADR 0012).

## 6.3 Gate R2 — Clean momentum and RS–GA comparison

Study `multiseed_momentum_r2_clean_v2`: 20 asset×seed units, 300 evaluations per fold and engine, 15 calendar folds for inference (ADR 0013).

**Momentum:** 0/40 asset×seed×engine combinations positive; all rejected.

**RS vs GA:** mean paired GA−RS = **−0.061**; 95% CI **[−0.399, +0.277]**; Cohen's d_z = **−0.100**. **No evidence of systematic GA superiority.**

## 6.4 Gate R3 — Five-family evaluation

Root `artifacts/runs/r3_full_budget100_ga21/`: 100/100 units completed; isolation audit **100/100, 0 failures** (documentary at closure). Verdict: **CLOSED_NEGATIVE**, **0 promoted, 5 rejected** (ADR 0015).

### Table 6.1 — Random Search results by family and asset

*Source: `reports/r3_gate/r3_full_budget100_ga21/thesis_report.md` (reporter_verified).*

| Family | Asset | C1 | C2 | C3 | C4 | C5 | C6 | Min-trades veto | Med. OOS ret. | Med. Sharpe | Med. B&H | Verdict |
|--------|-------|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---------|
| breakout | BTC | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 10/10 | 10/10 | −15.8% | −0.73 | +52.3% | REJECTED |
| breakout | ETH | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 10/10 | 10/10 | −25.5% | −1.05 | −21.9% | REJECTED |
| mean_reversion | BTC | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 10/10 | 10/10 | −60.0% | −0.50 | +52.3% | REJECTED |
| mean_reversion | ETH | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 10/10 | 10/10 | −79.9% | −0.89 | −21.9% | REJECTED |
| volatility_breakout | BTC | 6/10 | 0/10 | 3/10 | 2/10 | 0/10 | 6/10 | 10/10 | +6.5% | 0.22 | +52.3% | REJECTED* |
| volatility_breakout | ETH | 1/10 | 0/10 | 1/10 | 1/10 | 0/10 | 9/10 | 10/10 | −73.5% | −0.66 | −21.9% | REJECTED |
| funding | BTC | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 10/10 | 10/10 | −40.9% | −0.27 | +52.3% | REJECTED |
| funding | ETH | 1/10 | 0/10 | 1/10 | 1/10 | 0/10 | 10/10 | 10/10 | −59.9% | −0.32 | −21.9% | REJECTED |
| BTC_ETH_confirmation | BTC | 1/10 | 0/10 | 0/10 | 0/10 | 0/10 | 9/10 | 10/10 | −65.8% | −0.55 | +52.3% | REJECTED |
| BTC_ETH_confirmation | ETH | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 10/10 | 10/10 | −68.3% | −0.30 | −21.9% | REJECTED |

\* **volatility_breakout / BTC:** partial non-robust signal (6/10 positive-return seeds); **not promotion-eligible** and **not an approved strategy**.

### Table 6.2 — Gate summary R1–R4

| Gate | Question | Result | Consequence |
|------|----------|--------|-------------|
| R1 | Per-fold valid search? | PASSED | Clean protocol for R2–R3 |
| R2 | Momentum & RS–GA under clean protocol? | Momentum rejected | Baseline discarded |
| R3 | Any family promoted? | 0/5 | No holdout candidate |
| R4 | Extended robustness on promoted? | **SKIPPED** | Not executed |

## 6.5 Gate R4

**SKIPPED** — zero R3 promotions; `r4_required = false` at closure (reporter_verified). R4 machinery exists in code but was not applied as a confirmatory gate (ADR 0015).

## 6.6 Provenance note

R3 run identities record dirty worktrees and `reproducible_from_commit_alone=false` (two tracked diff states). Patch bytes were not retained. This limits exact code reconstruction but does not invalidate the numerical consistency checks (0 discrepancies in the R3 thesis reporter).
