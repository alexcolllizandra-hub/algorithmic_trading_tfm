# Phase gates

**Version:** 1.0 · **Date:** 2026-08-08

A phase is complete when its gate is satisfied — **not when its code compiles and
not when its tests pass.** Tests prove the code does what was intended; a gate
proves the intention was worth pursuing.

Related: [current state](current_state.md) · [master roadmap](master_roadmap.md) ·
[scientific questions](scientific_questions.md) · [future architecture](future_architecture.md)

---

## Gate structure

Every gate specifies eleven fields:

| Field | Question it answers |
|---|---|
| Objective | What is this phase for? |
| Hypothesis / question | What are we trying to learn? |
| Dependencies | What must exist first? |
| Implementation deliverables | What code must exist? |
| Tests | What must be proven about the code? |
| Experiment required | What must be run? |
| Artifacts | What must be persisted? |
| Statistical evaluation | How is the result judged? |
| Documentation | What must be written? |
| Promotion criteria | What lets us advance? |
| Rejection criteria | What stops us? |

---

## Universal invariants

These hold at **every** gate. Violating one fails the gate regardless of results.

1. **The holdout stays closed.** `[2026-01-01, 2026-07-01)` is never read outside
   Phase H. Development code must fail closed if holdout rows are requested.
2. **Chronological splits only.** No random or shuffled splits anywhere.
3. **No look-ahead.** Every decision input is computed from strictly past data.
4. **Determinism.** Results reproduce from `AppSettings.seed` and the derived
   seed streams.
5. **Provenance.** Every run records commit, config hash, dataset hashes, seed
   and cost assumptions.
6. **No retrospective tuning of a rejected result.** A family that failed its
   criterion is not re-searched until it passes.
7. **No comparison across materially different contracts** without stating the
   difference explicitly.

---

## Gate R1 — Restore temporal validity — **PASSED 2026-08-09**

**Objective.** Make candidate search independent per outer fold.

**Question.** Can a strategy be selected for fold *i* using only information
available before fold *i*'s test window?

**Dependencies.** None. This is the blocking phase.

**Implementation deliverables.**

* A single-fold view of the folds bundle, so an evaluator is bound to one fold.
* A runner loop: for each outer fold × engine → search → freeze winner →
  evaluate test exactly once.
* Budget parity asserted **per outer fold**.
* Per-fold artifacts, with the aggregated ledger retained for the dashboard.
* Removal of the duplicate test evaluation currently performed twice per winner.

**Tests.**

* A candidate's validation metrics contain exactly one fold when the evaluator is
  fold-scoped.
* Selection on fold *A* is unchanged when fold *B*'s data changes.
* The winner's test slice is evaluated exactly once per fold.
* Determinism: identical seed → identical candidate IDs, fitness and winners.
* Budget parity holds per fold for both engines.

**Experiment required.** A smoke run on synthetic data plus one real-data pilot
fold. **No full study is required at this gate** — this is a correctness gate,
and spending a full search budget to verify a contract would be wasteful.

**Artifacts.** Per-fold candidate ledgers and convergence traces; a summary
recording `search_protocol: independent_per_outer_fold` and the per-fold budget.

**Statistical evaluation.** None. This gate is about protocol correctness.

**Documentation.** An ADR recording the protocol change, why the previous
protocol was invalid, and which frozen results it affects.

**Promotion criteria.**

- [x] Fold-isolation tests pass — `tests/unit/test_search_fold_isolation.py`.
- [x] Budget parity holds per outer fold for both engines — pilot audit: 60
      evaluations per engine in each of 15 folds.
- [x] Full offline suite green (634 passed); `ruff check`, `ruff format --check`
      and `pyright` (0 errors) clean, plus frontend `tsc`, ESLint and `vitest`.
- [x] A fixed-seed run reproduces exactly — per-fold convergence traces and seed
      streams compared in `tests/integration/test_search_pipeline.py`.
- [x] The branch divergence is resolved: `fix/outer-fold-leakage` was abandoned
      and R1 re-implemented on `docs/roadmap-consolidation`, which descends from
      the multi-seed branch.

**Rejection criteria** (neither triggered).

- If per-fold search cannot reach the configured budget in a realistic space, the
  budget contract is renegotiated **in an ADR** — never silently lowered.
  *Not triggered:* both engines reached the full 60-evaluation target in all 15
  folds of the real momentum pilot.
- If enforcing isolation makes runtime infeasible for 15 folds × 10 seeds ×
  2 assets, the geometry is reduced **explicitly and symmetrically** for both
  engines, and recorded. *Not triggered:* the measured cost is 1.00x in
  backtests and 1.18x in wall-clock, not the 15x originally feared; the full
  15-fold two-engine pilot runs in 16.5 s. The geometry is unchanged.

**Evidence.**

| Item | Where |
|---|---|
| Protocol decision, cost measurement, isolation argument | [ADR 0012](../decisions/0012-outer-fold-contamination-in-candidate-search.md) |
| Isolation tests | `tests/unit/test_search_fold_isolation.py` |
| Cost benchmark (old vs new, real data) | `scripts/benchmark_protocol_cost.py`, `reports/tables/protocol_cost.json` |
| Artifact-level audit of a real run | `scripts/audit_fold_isolation.py` |
| Pilot run | `artifacts/runs/search_momentum_20260809T085829Z_c28e3b` |
| Quarantine of superseded results | `scripts/mark_superseded_runs.py` (64 directories marked, none deleted) |

---

## Gate R2 — Re-baseline momentum and the engine comparison — **PASSED 2026-08-09**

**Objective.** Re-establish the frozen results under the corrected protocol.

**Question.** Do FR-1 and FR-2 survive a search that cannot see the future?

**Dependencies.** Gate R1.

**Implementation deliverables.** None beyond R1 — this is an experimental phase.

**Tests.** Existing suite remains green; the multi-seed analysis handles per-fold
artifacts.

**Experiment required.** Momentum, 2 assets × 10 derived seeds × 15 folds, full
development geometry, budget parity per fold, both engines.

**Artifacts.** A new study directory with `study_manifest.json`,
`multi_seed_analysis.json`, `study_robustness.json`, `checkpoint.json` and
per-unit run directories. **The previous study is not overwritten.**

**Statistical evaluation.**

* Unit of inference: symbol × fold with seeds averaged inside each cell.
* Paired RS-vs-GA difference with a 95 % interval and Cohen's dz.
* Seed stability: share of seeds with a positive mean metric.
* Variance decomposition and the seed-to-fold SD ratio.
* Robustness battery per unit.

**Documentation.** An ADR comparing old and new conclusions side by side, stating
plainly whether the correction changed them.

**Promotion criteria.**

- [x] Study completes at full seed coverage with parity per fold — 20/20
      asset-seed units; both engines spent 300 evaluations in every one of 15
      folds (`scripts/audit_study_isolation.py`: 20 runs, 0 failures).
- [x] The comparison against FR-1/FR-2 is documented **whichever way it falls** —
      [ADR 0013](../decisions/0013-clean-momentum-rebaseline.md). Momentum
      worsened to 0/40 profitable combinations; GA - RS moved from +0.183 to
      -0.061, 95% CI [-0.399, +0.277].
- [x] Superseded results are marked as superseded, not deleted — ADR 0011 and
      `multiseed_momentum_baseline/` remain intact with `SUPERSEDED.json`.

**Rejection criteria.** None — this gate cannot "fail" scientifically. A result
that contradicts the old conclusion is the point of running it. The gate fails
only on process grounds: incomplete seeds, broken parity or missing provenance.

**Pre-registered expectation.** Momentum is expected to remain negative or worsen;
the GA − RS point estimate is expected to move toward zero. Recording this before
the run is what makes it a test rather than a narrative.

**Outcome.** Both directional expectations were met. Momentum is now
**rejected**, not retuned. There remains no evidence of GA superiority.

**Execution note.** The first R2 launch stopped at 299/300 GA evaluations in one
fold when the 40-generation safety cap was exhausted. Parity failed closed; no
unit/result from that attempt was used. Raising only the safety cap to 200
allowed every fold to reach the unchanged 300-evaluation budget.

---

## Gate R3 — Family evaluation — **CLOSED 2026-08-10 (negative)**

**Objective.** Give every implemented family a fair, comparable hearing.

**Question.** Does any implemented family show an effect surviving multiple seeds?

**Dependencies.** Gates R1, R2.

**Implementation deliverables.** None — all six families are implemented and
tested. Any code change here is a bug fix, and a bug fix invalidates prior runs
of that family.

**Tests.** Per-family leakage tests must already pass: truncation/prefix
invariance, correct lag, next-bar execution, warm-up handling.

**Experiment required, per family.**

| Stage | Design | Purpose |
|---|---|---|
| Pilot | 1 seed, reduced budget, full geometry | Pipeline correctness only |
| Multi-seed | ≥10 derived seeds, both assets, full budget | Evidence |
| Robustness | Battery on the multi-seed OOS ledgers | Durability |

**A pilot never produces performance evidence.** Its Sharpe values are recorded
for diagnostics and must not be quoted as results.

**Pilot stage completed 2026-08-09.** Breakout, mean reversion, volatility
breakout, funding and BTC-ETH confirmation each completed 2 assets × 1 seed ×
15 folds at 60 evaluations per fold and engine. All 10 runs passed
`scripts/audit_study_isolation.py`: exact per-fold parity, fingerprinted winners
and within-fold dispersion. All five advance to the multi-seed experiment
stage on process grounds only; pilot performance was not used for selection or
ordering.

**Multi-seed stage completed 2026-08-10.** All five families completed 2 assets
× 10 seeds × 15 folds at budget 100 per fold and engine under
`artifacts/runs/r3_full_budget100_ga21/`. All 100 runs passed the isolation audit.
**Verdict: 0 promoted, 5 rejected** ([ADR 0015](../decisions/0015-r3-family-evaluation-negative.md)).
Strongest partial signal: volatility_breakout BTC 6/10 positive seeds (RS), but
0/10 bootstrap Sharpe CIs excluding zero on either asset.

**Artifacts.** One study directory per family, rollup
(`r3_family_rollup.md`), gate verdict (`r3_gate_verdict.json`).

**Statistical evaluation.** As Gate R2, per family.

**Documentation.** Per family: the hypothesis, mechanism, parameters, the result,
and the promotion decision with its evidence.

**Promotion criteria — a family advances only if all hold.**

- [ ] A majority of seeds produce a positive mean test metric **on both assets.**
- [ ] The bootstrap Sharpe CI excludes zero on the concatenated OOS ledger for a
      majority of seeds.
- [ ] Performance survives doubled costs (2× fee, 2× slippage).
- [ ] It beats buy-and-hold on the same coverage.
- [ ] Removing the best 5 trades does not eliminate the result.
- [ ] The effect is not confined to a single fold.

**Rejection criteria — any one rejects the family.**

- Zero seeds positive on either asset.
- No bootstrap CI excluding zero on any seed.
- The result vanishes under doubled costs.
- The result depends on fewer than 5 trades.
- Performance is confined to one fold.

**Rejected families are recorded with their evidence and are not retuned.**
Rejecting most families is an expected, reportable outcome.

**Budget discipline.** Identical effective budget per fold for every family. No
family receives extra search because it looked promising.

**Budget renegotiation (ADR 0014, 2026-08-10).** The first full run proved the
declared budget 300 impossible: breakout has exactly 108 unique candidate
identities. Parity failed closed at RS=108 / GA=106 and no result was accepted.
R3 therefore uses a common budget of **100 per fold and engine** for all five
families (92.6% of the smallest space, with headroom for stochastic engines).
Spaces were not widened and pilot metrics did not influence this decision.
`run_search()` now rejects a budget above finite cardinality before loading
market data.

---

## Gate R4 — Robustness coverage — **SKIPPED (zero R3 promotions)**

**Objective.** Close the gap between claimed and implemented robustness.

**Question.** Are promoted families' results stable under parameter perturbation and
across regimes?

**Dependencies.** Gate R3 with at least one **promoted** family. **If no family is
promoted in R3, this gate is skipped** as a confirmatory phase and the thesis
reports a negative result. Families **rejected** in R3 cannot use R4 as a rescue
path. Any diagnostic run after R3 closure must be labeled **exploratory** and
**cannot alter** the recorded R3 verdict.

**Status 2026-08-10.** Skipped as a promotion gate: R3 promoted zero families.
The extended checks (regime-conditional metrics, trade-path bootstrap, parameter
perturbation replay) are implemented in `evaluation/` for methodology completeness
but were not required to pass a promoted candidate.

**Implementation deliverables.** Parameter perturbation (neighbourhood sampling
around a fold winner); regime-conditional evaluation reusing the existing regime
models; trade-path resampling for equity-path distributions.

**Tests.** Unit tests for each new check; determinism under a fixed seed.

**Experiment required.** Apply the extended battery only to families **promoted**
in Gate R3. Completing the multi-seed study in R3 is necessary but not
sufficient; rejected families are out of scope.

**Artifacts.** An extended robustness report per promoted family.

**Statistical evaluation.** Performance degradation as a function of parameter
distance; per-regime metrics with sample sizes; the equity-path distribution with
its quantiles.

**Documentation.** Update the validation protocol so claims match implementation,
and state explicitly that the block bootstrap is **not** a Monte Carlo account
simulator.

**Promotion criteria.**

- [ ] Each new check is implemented, tested and wired into the report.
- [ ] Promoted families keep their result under perturbation.
- [ ] Regime dependence is measured and reported.

**Rejection criteria.** A family whose result exists only at a knife-edge
parameter setting, or only in one regime with too few observations to support the
claim, is demoted from `ROBUST`.

---

## Gate S1 — Controlled strategy expansion

**Objective.** Add families only where a mechanism justifies the added search.

**Dependencies.** Gates R3, R4.

**Per-family prerequisites, written before any code:**

```
EDA / statistical motivation → hypothesis → features → parameters
  → expected mechanism → validation experiment → promotion / rejection criterion
```

**Research-budget record, per family:** scientific motivation; new degrees of
freedom; search-space expansion factor; required validation budget; and the
promotion rule, fixed before the result is seen.

**Promotion criteria.**

- [ ] The motivation chain is documented **before** implementation.
- [ ] Degrees of freedom and search-space expansion are quantified.
- [ ] The family passes Gate R3's criteria.
- [ ] The multiple-comparison burden across all evaluated families is stated.

**Rejection criteria.**

- No stated mechanism, or a mechanism invented after seeing the result.
- Search-space expansion that would exceed the available validation budget.
- Batch addition of indicators without individual motivation.

**Hard constraint.** No single search may jointly optimise indicators,
thresholds, timeframes, stops, ML hyperparameters and portfolio weights.
Optimisation stays layered.

---

## Gate M1 — Labeling and meta-labeling

**Objective.** Build causal labels an ML filter can consume.

**Dependencies.** At least one family at `ROBUST`. **Without one, this gate does
not open.**

**Implementation deliverables.** Triple-barrier labeling with causal barrier
placement; meta-labels of the form "the base strategy fired — was it right?";
`features/predictors.py` extended to populate `label_time`.

**Tests.** A label never uses information available before its own resolution;
barrier placement is causal; unresolved labels at the end of a sample are
excluded, not imputed.

**Promotion criteria.**

- [ ] Leakage tests pass.
- [ ] Label distribution is reported (class balance, resolution reasons).
- [ ] Labels reconcile with the backtester's realised trades.

**Rejection criteria.** Any leakage test failing; or a label distribution so
imbalanced that no filter can be trained honestly.

---

## Gate M2 — ML filters

**Objective.** Decide whether an ML filter improves an already-robust strategy.

**Question.** Given that a base strategy generated a trade, should it be accepted?

**Dependencies.** Gate M1.

**Implementation deliverables.** Logistic Regression first, then Random Forest,
then LightGBM — all consuming meta-labels, all respecting walk-forward folds, and
all trained strictly on data preceding the fold they are applied to.

**Tests.** No training data overlaps the evaluation fold; feature availability
respects `feature_time`; the filter cannot resurrect a trade the base strategy
never generated.

**Statistical evaluation.** Calibration (reliability curve, Brier score);
discrimination (AUC, precision/recall at the operating threshold); and the
**economic** effect — the change in OOS metrics versus the unfiltered base.

**Documentation.** Feature importance, permutation importance, SHAP where it adds
insight, and an ablation isolating the filter's contribution.

**Promotion criteria.**

- [ ] The filter beats the **unfiltered base strategy** OOS across multiple seeds.
- [ ] Logistic Regression is reported as the interpretable baseline, whether or
      not the more complex models beat it.
- [ ] Probabilities are calibrated, not just ranked.
- [ ] The improvement survives the robustness battery.

**Rejection criteria.**

- No improvement over the unfiltered base.
- Improvement only from a threshold tuned on the evaluation data.
- The model cannot be explained at the level the thesis requires.

**Explicitly forbidden.** An end-to-end LightGBM predicting returns from raw
features, with the interpretable base strategy discarded.

---

## Gates P1–P4 and X1 — Specification-stage gates

These phases are specified but not scheduled. Each will need a full gate written
when it is reached. The **boundary conditions** are fixed now because they are
architectural commitments:

| Gate | Boundary that must hold |
|---|---|
| P1 Portfolio | Must not silently override strategy logic; every override is explicit and measurable in an ablation |
| P2 Risk | Must be able to **reject or reduce** desired positions, not merely observe |
| P3 Simulation | Monte Carlo claims require a genuine account model; a block bootstrap is not one |
| P4 Funded accounts | Rules are provider-configurable, never hardcoded; requires a demonstrated edge first |
| X1 Execution | Strategies never call an exchange; venue behaviour lives behind adapters; no real capital in this thesis |

---

## Gate H — Holdout evaluation

**Objective.** Report the honest out-of-sample result once.

**Dependencies.** A frozen, documented strategy selection made **before** the
holdout is opened.

**Preconditions — all must hold before a single holdout row is read.**

- [ ] The strategy, its parameters and its full configuration are committed.
- [ ] The commit hash predating the holdout access is recorded.
- [ ] Dataset hashes are recorded.
- [ ] The selection rationale is documented with its development evidence.
- [ ] It is opened **once**. There is no second attempt.

**Artifacts.** Timestamp; git state; resolved configuration; dataset hashes; the
previously selected strategy; and the resulting metrics.

**Promotion criteria.** Not applicable — this gate produces the final result,
whatever it is.

**Rejection criteria.** Not applicable. **A negative holdout result is a valid
thesis outcome and must be reported as found.**

**If no strategy is promoted,** the holdout is still opened once to report the
honest outcome of the best available candidate, labelled explicitly as a
non-promoted candidate.
