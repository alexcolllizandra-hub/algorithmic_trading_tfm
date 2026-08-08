# ADR 0012 -- Outer-fold contamination in candidate search

- **Status:** accepted
- **Date:** 2026-08-08
- **Affects:** ADR 0009 (fair RS/GA comparison), ADR 0010 (OOS evaluation),
  ADR 0011 (multi-seed baseline). It does not supersede them; it qualifies every
  experimental result they report.

## Context

A repository audit on 2026-08-08 examined how candidates are ranked during
search. `CandidateEvaluator.evaluate()` in `src/perp_lab/search/evaluator.py`
backtests a candidate on the validation slice of **every** walk-forward fold and
collapses those metrics into one scalar:

```python
for fold in self.bundle.folds:
    result = self._backtest(strategy, fold.val)
    fold_metrics.append(_fold_metrics(result))

obj = aggregate_objective(fold_metrics, ...)
candidate.fitness = obj.fitness
```

Both Random Search and the genetic algorithm rank candidates on that pooled
fitness. With the research geometry of 15 folds, the fitness used while searching
for fold 0 includes validation windows belonging to fold 14 -- windows that lie
years **after** fold 0's test period.

`_fold_winners()` partially limits the damage: it selects each fold's winner using
only that fold's own validation Sharpe, not the pooled fitness. But selection
operates on a candidate *pool*, and how that pool was produced differs by engine:

- **Random Search** samples independently of fitness. Its pool is not shaped by
  future data. Its per-fold winner is comparatively clean; only its reported
  `best` candidate inherits the pooled ranking.
- **The genetic algorithm** evolves its population *on* the pooled fitness.
  Tournament selection, elitism and convergence all read it. Its pool is directly
  shaped by validation windows in the future relative to earlier folds.

This violates rule 3 of `.cursor/rules/research-integrity.mdc` (no look-ahead) and
the temporal contract described in ADR 0004.

## Decision

### 1. The defect is recorded, not hidden

Every experimental result in this repository was produced under this protocol:
the momentum multi-seed baseline (ADR 0011), the RS-vs-GA comparison, and the
four-family pilot. They remain in the repository as frozen records. They are
**not** deleted, and they are **not** restated more favourably.

### 2. Existing conclusions are qualified, not withdrawn

The bias runs **in the genetic algorithm's favour**, because the GA consumed an
advantage that Random Search's fitness-independent sampling never received.

| Result | Effect of the defect |
|---|---|
| Momentum has no demonstrated edge (ADR 0011) | **Conservative.** Removing an optimistic bias does not create an edge. The conclusion is expected to hold or strengthen. |
| No evidence the GA beats Random Search | **Conservative as a negative.** The GA was favoured and still showed no significant advantage. However the point estimate of +0.183 must **not** be read as a real, merely-underpowered effect: part of it is bias. |
| Four-family pilot Sharpe values | Already pipeline evidence only; unchanged in status. |

### 3. Search becomes independent per outer fold before any new experiment

For each outer fold, each engine searches using only that fold's validation
slice, the winner is frozen, and the test slice is evaluated exactly once. Budget
parity is re-asserted **per fold**, so `effective_budget` means the same thing for
both engines within each fold.

### 4. No new family is evaluated until the correction lands

Evaluating breakout, mean reversion, volatility breakout, funding or cross-asset
confirmation under the current protocol would produce evidence carrying the same
defect and waste the search budget.

### 5. The re-baseline is pre-registered

Before re-running, the expectation is recorded: momentum should remain negative
or worsen, and the GA - RS point estimate should move toward zero. Writing this
down in advance is what makes the re-run a test rather than a narrative.

## Consequences

**Positive.** The temporal contract becomes enforceable by test rather than by
convention. Per-fold search also makes the walk-forward story simpler to defend:
each fold becomes a self-contained experiment.

**Negative.** Cost rises. Search runs once per outer fold per engine instead of
once per run, so a study at 15 folds performs roughly fifteen times the search
work at the same per-fold budget. If that proves infeasible for 15 folds x 10
seeds x 2 assets, the geometry or the per-fold budget must be reduced
**explicitly and symmetrically for both engines**, and recorded in a further ADR
-- never lowered silently.

**Operational.** A working implementation exists on branch
`fix/outer-fold-leakage` (`588ab8e`), adding `single_fold_bundle()`, the per-fold
runner loop and `tests/unit/test_search_fold_isolation.py`. That branch descends
from `main` via `feat/research-dashboard-redesign` and therefore lacks the
`evaluation/` package, the three newer strategy families, `effective_budget`
parity and the multi-seed orchestrator. **It cannot be merged as-is**; the fix
must be re-applied against the branch carrying the multi-seed work.

## Verification

The correction is accepted when:

- a metric computed on fold *B* provably cannot change the selection made on
  fold *A*, demonstrated by test;
- a fold-scoped evaluator yields exactly one validation metric set per candidate;
- each fold winner's test slice is evaluated exactly once;
- budget parity holds per outer fold for both engines;
- a fixed-seed run reproduces exactly.

Full criteria: `docs/roadmap/phase_gates.md`, Gate R1.
