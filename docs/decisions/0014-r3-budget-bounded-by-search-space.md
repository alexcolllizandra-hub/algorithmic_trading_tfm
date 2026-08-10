# ADR 0014 -- R3 budget is bounded by the smallest finite search space

- **Status:** accepted
- **Date:** 2026-08-10
- **Affects:** Gate R3 family comparison
- **Depends on:** ADR 0012 (per-fold isolation), ADR 0013 (clean baseline)

## Context

R3 was pre-registered with an identical effective budget of 300 unique objective
evaluations per fold and engine for every family. The first full R3 launch failed
closed before completing its first fold:

- family: breakout;
- requested budget: 300;
- exact unique valid candidate identities: 108;
- Random Search exhausted the space at 108 after 60,000 proposals;
- the GA converged at 106;
- `BudgetParityError` aborted the run and no test winner was accepted.

Raising `ga.max_generations` cannot solve a finite-space contradiction. No engine
can evaluate 300 unique breakout candidates when only 108 exist. Widening the
parameter space after observing this failure would change the pre-registered
strategy family and create researcher degrees of freedom. Lowering only
breakout's budget would violate R3's cross-family budget parity.

The exact cardinalities, computed by applying each space's real repair,
validation, conditional-activation and canonical-hash rules, are:

| Family | Unique valid identities |
|---|---:|
| momentum | 540 |
| breakout | 108 |
| mean_reversion | 432 |
| volatility_breakout | 7,776 |
| funding | 1,296 |
| BTC_ETH_confirmation | 7,776 |

Evidence: `scripts/audit_search_space_cardinality.py` and
`reports/tables/search_space_cardinality.json`.

## Decision

1. **R3 uses a common effective budget of 100 evaluations per fold and engine.**
   This is the largest round budget below the smallest space's cardinality. It
   covers 92.6% of breakout while leaving eight identities of headroom, avoiding
   a requirement that stochastic engines solve a coupon-collector exhaustion
   problem merely to satisfy accounting.
2. **Every R3 family receives exactly the same 100-evaluation budget.** No family
   gets more search because its space is larger or because a pilot looked
   promising.
3. **The strategy spaces are not widened.** Their hypotheses and parameter grids
   remain those specified before R3.
4. **Impossible budgets fail before market data is loaded.**
   `SearchSpace.finite_cardinality()` now computes exact cardinality for finite
   spaces, and `run_search()` raises `SearchSpaceBudgetError` when the declared
   budget exceeds it.
5. The failed budget-300 attempt under `artifacts/runs/r3_full/` is retained as
   process evidence.
6. **GA convergence does not waive budget parity.** A budget-100 preflight then
   found a second process defect: in one seed/fold the GA population converged at
   97/100 while RS reached 100. GA 2.1 injects globally unseen random immigrants
   after five stalled generations and resumes evolution. Immigrants consume the
   same unique-evaluation budget; they are not extra work. If no unseen identity
   can be sampled, the run terminates explicitly as `finite_space_exhausted` and
   still fails parity.
7. Both failed roots are retained (`r3_full/` and `r3_full_budget100/`). The
   final contract starts fresh under `r3_full_budget100_ga21/`; no checkpoint is
   reused across budgets or algorithm versions.

## Consequences

The R3 comparison remains fair in its declared sense: equal unique objective
evaluations per fold and engine. It is not equal in *fraction of each search
space explored* (92.6% for breakout, much less for larger spaces). Equalising
fractions would instead give different computational budgets and answer a
different question. Both facts must be stated when families are compared.

R3 is no longer directly budget-matched to momentum R2, which used 300
evaluations. Momentum is a rejected baseline, not one of the cross-family R3
competitors. Any numerical comparison between momentum and an R3 family must
state this contract difference and must not attribute it solely to strategy
quality.
