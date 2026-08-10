# ADR 0015 — Gate R3 closes with zero promotions

- **Status:** accepted
- **Date:** 2026-08-10
- **Affects:** Gate R3 family evaluation, Gate R4 scope
- **Depends on:** ADR 0012 (per-fold isolation), ADR 0014 (budget 100)

## Context

Gate R3 gave every implemented family a fair, comparable hearing under the clean
per-outer-fold protocol. The frozen contract was:

- assets: BTCUSDT and ETHUSDT;
- seeds: 10 derived from base seed 42;
- geometry: 15 chronological outer folds;
- budget: 100 unique objective evaluations per fold and engine (RS and GA);
- primary promotion engine: random_search;
- holdout: never opened.

All five families completed the full multi-seed study on 2026-08-10 under
`artifacts/runs/r3_full_budget100_ga21/`. Each study passed
`scripts/audit_study_isolation.py` (100/100 runs). Promotion was evaluated with
**six documented promotion criteria** in
[phase_gates.md](../roadmap/phase_gates.md#gate-r3--family-evaluation), including
drop-top-5 trades and fold-locality checks recorded before the studies finished.
**`min_oos_trades_met` is a separate veto** (minimum OOS trade count); it is not
one of the six promotion criteria and does not enter the `≥6/10` majority tally.
The promoted-only Gate R4 scope rule was harmonised in documentation **after**
R3 closed with zero promotions; it was not part of the executed R3 contract.

## Evidence

Rollup:
`artifacts/runs/r3_full_budget100_ga21/r3_family_rollup.md`

Gate verdict:
`artifacts/runs/r3_full_budget100_ga21/r3_gate_verdict.json`

| Family | Verdict | BTC seeds positive (RS) | ETH seeds positive (RS) | Median OOS return BTC | Median OOS return ETH |
|---|---|---:|---:|---:|---:|
| breakout | REJECTED | 0/10 | 0/10 | −15.8% | −25.5% |
| mean_reversion | REJECTED | 0/10 | 0/10 | −60.0% | −79.9% |
| volatility_breakout | REJECTED | 6/10 | 1/10 | +6.5% | −73.5% |
| funding | REJECTED | 0/10 | 1/10 | −40.9% | −59.9% |
| BTC_ETH_confirmation | REJECTED | 1/10 | 0/10 | −65.8% | −68.3% |

No family met the promotion bar on **both** assets. The strongest partial signal
was volatility_breakout on BTC (6/10 seeds with positive total return), but **0/10**
seeds had a bootstrap Sharpe CI excluding zero on either asset, and the family
failed cost-stress, buy-and-hold, drop-top-5 and ETH-side positivity criteria.

Common failure modes across families:

1. bootstrap Sharpe CI never excluded zero (0/10 seeds per asset for every family);
2. median OOS returns negative on at least one asset for every family;
3. no family beat buy-and-hold on a majority of seeds on both assets.

Momentum was already rejected in Gate R2 ([ADR 0013](0013-clean-momentum-rebaseline.md))
and was not one of the five R3 competitors.

## Decision

1. **Gate R3 status is `CLOSED_NEGATIVE`.** The question — does any implemented
   family show an effect surviving multiple seeds? — is answered **no**, with
   recorded evidence. This is a valid thesis outcome.
2. **All five families are `REJECTED`.** They are not retuned to pass.
3. **Gate R4 experimental application is skipped.** All five families completed the
   multi-seed evaluation, but **none met the promotion criteria**, so the extended
   robustness battery is not applied as a promotion gate. The R4 *machinery*
   (regime-conditional metrics, trade-path bootstrap, parameter perturbation replay)
   remains implemented for methodology and future work.
4. **The holdout stays closed.** With no promoted strategy, there is no candidate
   to freeze for a final holdout evaluation in this experimental arc.
5. Failed process roots (`r3_full/`, `r3_full_budget100/`) and the successful root
   (`r3_full_budget100_ga21/`) are all retained for provenance.

## Consequences

The thesis can report a rigorous negative result: six searchable families (including
the rejected momentum baseline) were evaluated under a corrected temporal protocol,
equal budget discipline and explicit promotion criteria, and none demonstrated a
robust development-period edge. The next roadmap phases (controlled expansion S1,
meta-labeling M1, portfolio P1) remain blocked until a new, mechanism-driven
hypothesis justifies additional search budget.
