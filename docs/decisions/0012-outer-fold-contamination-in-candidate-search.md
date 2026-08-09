# ADR 0012 -- Outer-fold contamination in candidate search

- **Status:** accepted -- **implemented 2026-08-09** (see "Implementation" below)
- **Date:** 2026-08-08 (decision), 2026-08-09 (implementation)
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

**Cost: unchanged in backtests, ~18% in wall-clock.** An earlier draft of this ADR
claimed the correction costs "roughly fifteen times the search work". That was
wrong, and the error mattered: it would have forced an unnecessary reduction of
the study geometry. The claim confused *unique evaluations* with *compute*.

Under the superseded protocol one evaluation backtested every fold's validation
slice, so a budget of `B` cost `B x F` backtests. Under the current protocol one
evaluation backtests a single fold and the budget is spent inside each of the `F`
folds, which is also `B x F` backtests. What rises fifteen-fold is the number of
*distinct parameter vectors examined*, and that is a benefit, not a cost: each
fold now explores its own `B` candidates instead of sharing one ranking. Measured
on the real development data with the research geometry
(`scripts/benchmark_protocol_cost.py`, momentum, BTCUSDT, 15 folds):

| Protocol | Unique evaluations | Validation backtests | Seconds |
|---|---|---|---|
| Superseded (pooled) | 12 | 180 | 1.114 |
| Current (per fold) | 180 | 180 | 1.309 |

Backtest ratio 1.00x, wall-clock ratio **1.18x**. The residual gap is per-fold
evaluator construction and cache setup, not extra backtesting. The full 15-fold
momentum pilot (`effective_budget = 60`, both engines, 900 evaluations each)
completes in **16.5 s**. The study geometry therefore does **not** need to be
reduced.

**Negative.** Fitness is no longer comparable across folds, so no run-level
"best fitness" exists; reporting uses the mean over folds of each fold's own best
and says so explicitly. The dispersion penalty also had to be redefined (below).

## Implementation

Landed on `docs/roadmap-consolidation`, 2026-08-09.

**Isolation is structural, not conventional.** `single_fold_bundle()`
(`src/perp_lab/search/evaluator.py`) builds a bundle holding one fold, and
`run_search()` binds one evaluator per outer fold. Another fold's data is not
filtered out at read time; it is simply absent. `evaluate_on_test()` resolves the
*global* fold index against the folds its evaluator actually holds and raises
`FoldIsolationError` otherwise, so a mis-wired call fails instead of silently
scoring the wrong window.

**The dispersion penalty was redefined, not dropped.** The old fitness penalised
the standard deviation of Sharpe *across folds* -- a quantity an isolated fold
cannot observe without look-ahead. Removing it would have deleted the robustness
pressure from the objective, so it is replaced by the standard deviation of
Sharpe across `stability_blocks` contiguous sub-blocks **within** the fold's own
validation window, computed from the ledger the backtest already produced (no
extra backtests). `objective_components` records
`dispersion_within_fold = 1.0` so any artifact states which definition produced
it.

**Selection is frozen before test is touched.** `_freeze_winner()` records a
SHA-256 `selection_fingerprint` over the fold index, candidate id and parameters
*before* the test slice is evaluated. "The strategy was chosen without seeing its
out-of-sample data" is therefore an auditable fact: altering the winner
afterwards changes the hash. The single test evaluation is retained on the
outcome, so artifact writing no longer re-runs it.

**Budget parity is enforced per fold.** `_assert_budget_parity()` runs inside
every fold and names the offending fold, because a run-level total can match
while one fold was searched unevenly -- and the fold is where selection happens.

**Contaminated artifacts are quarantined, not deleted.**
`scripts/mark_superseded_runs.py` stamped all 64 pre-existing run and study
directories with a `SUPERSEDED.json` marker recording the reason, the superseding
protocol and the original provenance (run id, git commit, seeds, budget, config
fingerprint). Runs also carry `search_protocol` in their summary; the dashboard
loader surfaces `contaminated: true` for anything else, and
`evaluation/multi_seed.assert_protocol()` raises `ContaminatedStudyError` rather
than pool a superseded unit with a clean one.

## Verification

Evidence produced on 2026-08-09.

**Tests.** `tests/unit/test_search_fold_isolation.py` (new) fails if any channel
between a fold and data it may not see is reopened: a later fold's existence
changing an earlier fold's fitness; another fold's test being reachable at all;
the test slice moving fitness (verified by scrambling test prices by 1000x and
requiring identical fitness); a winner selected on anything but validation; the
two engines searching at different effective budgets inside one fold. Each
comparison test asserts that at least one candidate was actually admissible, so a
degenerate fixture cannot make it pass vacuously.

**The tests detect the original bug.** Re-scoring the same 60 candidates under
the superseded pooled evaluator and the isolated one changed the fitness of
**44 of 60**; the isolation tests fail against the old evaluator and pass against
the new one.

**Quality gates.** `ruff check`, `ruff format --check`, `pyright` (0 errors) and
`pytest -m "not network"` (634 passed) all pass, plus the frontend `tsc`, ESLint
and `vitest` suites.

**End-to-end pilot.** `configs/search_pilot_momentum.yaml`, real development
data, 15 folds, `effective_budget = 60`, both engines, funding required, holdout
untouched. Run `search_momentum_20260809T085829Z_c28e3b`.
`scripts/audit_fold_isolation.py` reads only the artifacts and confirms: protocol
declared; both engines spent exactly 60 evaluations in each of the 15 folds
(900 each); 15/15 folds froze a fingerprinted winner selected on validation only,
each attributed to that fold's own search; all 900 scored candidates per engine
measured dispersion within their own fold.

Gate R1 criteria: `docs/roadmap/phase_gates.md`.

## What must be re-run

Every number in the repository predating this change was produced under the
superseded protocol and is invalid as inference: the momentum multi-seed baseline
(ADR 0011), the RS-vs-GA comparison including the +0.183 point estimate, and the
four-family pilot Sharpe values. They are retained, marked and traceable, but
they may not be cited as evidence.

The first experiment to repeat under the corrected protocol is the **momentum
multi-seed baseline** (10 seeds x 2 assets, unchanged geometry and budget), since
it is the pre-registered re-baseline of §5: momentum is expected to remain
negative or worsen, and the GA - RS estimate to move toward zero. No new family
is evaluated before that re-baseline exists.
