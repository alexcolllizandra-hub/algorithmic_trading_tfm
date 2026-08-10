# Master roadmap

**Version:** 1.0 · **Date:** 2026-08-08
**Basis:** the audited repository state in [current_state.md](current_state.md).

Related: [phase gates](phase_gates.md) · [scientific questions](scientific_questions.md) ·
[future architecture](future_architecture.md)

---

## How this roadmap differs from the original plan

The audit changed the ordering in three ways.

1. **A blocking correction was inserted before all research.** The audit found
   that candidate search pooled validation metrics across all walk-forward folds
   ([Inconsistency 1](current_state.md#inconsistency-1-outer-fold-contamination-in-candidate-search)).
   No new family may be evaluated until that is fixed, or the new evidence would
   inherit the same defect.

2. **"Evaluate the implemented families" is not one phase.** Three families are
   piloted, two have never been run at all, and one has a completed but
   contaminated multi-seed study. They enter the pipeline at different points.

3. **Robustness is not a late phase.** The battery already exists and is applied
   inside the multi-seed gate. What is missing is *coverage* (parameter
   perturbation, regime conditioning), not sequencing.

Everything below the research phases is **specification only**. Writing it down
now is what allows the project to be executed sequentially later; it is not a
commitment to build it in this thesis.

---

## Lifecycle

Every component moves through:

```
RESEARCH → BUILD → VALIDATE → PROMOTE / REJECT
```

and carries an explicit maturity:

```
SPECIFIED → IMPLEMENTED → TESTED → PILOTED → MULTI-SEED → ROBUST → PROMOTED / REJECTED
```

**Rejection is a valid, publishable outcome.** A negative result obtained
rigorously is worth more to this thesis than a positive one obtained by leakage
or overfitting.

---

## Phase overview

| # | Phase | Status | Blocks |
|---|---|---|---|
| F | Foundation | **Complete** | — |
| R1 | Restore temporal validity | **Complete (2026-08-09)** | — |
| R2 | Re-baseline momentum + RS/GA | **Complete (2026-08-09)** | — |
| **R3** | **Evaluate implemented families** | **Complete (2026-08-10, negative)** | — |
| R4 | Robustness coverage | **Skipped** (zero R3 promotions); code implemented | S1 |
| S1 | Controlled strategy expansion | Specified | M1 |
| S2 | Advanced statistical strategies | Specified | — |
| M1 | Labeling + meta-labeling | Specified | M2 |
| M2 | ML filters | Specified | P1 |
| P1 | Portfolio | Specified | P2 |
| P2 | Risk | Specified | P3 |
| P3 | System robustness / simulation | Specified | P4 |
| P4 | Funded-account research | Specified | X1 |
| X1 | Execution progression | Specified | — |
| H | Holdout evaluation | **Frozen** | final report only |

---

## F — Foundation (complete)

Delivered and verified: data ingestion with a validated contract; a 23-module EDA
library; a causal feature engine with 25 kinds in three packs; six searchable
strategy families plus six fixed baselines; a cost- and funding-aware next-bar
backtester; expanding walk-forward with purge and embargo; Random Search and a
Genetic Algorithm sharing one evaluator and one budget definition; deterministic
seed derivation; crash-safe multi-seed orchestration; a run-identity fingerprint;
and a FastAPI + Next.js research dashboard.

Evidence: [current_state.md](current_state.md#component-inventory).

**One caveat carries forward:** this foundation produced its results under a
contaminated search protocol. Phase R1 fixed the protocol on 2026-08-09; the
*results* it produced are still superseded and are re-established in R2.

---

## Phase R1 — Restore temporal validity — **COMPLETE (2026-08-09)**

**Objective.** Make candidate search independent per outer fold, so that
selecting a strategy for fold *i* cannot use information from fold *j > i*.

**Question.** Does any conclusion in this repository survive a search protocol
that respects the arrow of time?

**Why first.** Every existing result — the momentum multi-seed study, the
RS-vs-GA comparison, the four-family pilot — was produced under a fitness pooled
across all folds. Evaluating a new family before fixing this would produce
evidence with the same defect and waste the compute.

**Deliverables.**

1. Per-outer-fold search: for each fold, build a single-fold view, run each engine
   on that fold's validation only, freeze the winner, evaluate test exactly once.
2. Budget parity re-asserted **per outer fold**, so `effective_budget` means the
   same thing for both engines within each fold.
3. Per-fold artifacts (`{method}_fold{n}_candidates.parquet`,
   `{method}_fold{n}_convergence.json`) with the aggregated ledger retained for
   the dashboard.
4. Tests proving that a metric computed on fold *B* cannot change the selection
   made on fold *A*.
5. Reconciliation of the divergent branches
   ([Inconsistency 2](current_state.md#inconsistency-2-the-leakage-fix-is-on-a-divergent-branch)).

**Outcome.** All five deliverables landed on `docs/roadmap-consolidation`.
`fix/outer-fold-leakage` was abandoned rather than merged, and R1 was
re-implemented on a base that carries the multi-seed work, so it also covers
per-fold budget parity, the multi-seed protocol guard and the API/dashboard
contract — none of which the old branch could see.

Two design points were forced by isolation and are worth stating, because a
naive fix would have quietly changed the experiment:

* **The dispersion penalty had to be redefined.** Fitness penalised the spread of
  Sharpe *across folds*, which an isolated fold cannot observe. Dropping it would
  have removed the objective's robustness pressure, so it became the spread
  across contiguous sub-blocks *within* the fold's own validation window,
  computed from the existing ledger at no extra backtest cost.
* **The cost fear was wrong.** Measured on real data at the research geometry,
  the corrected protocol runs the *same* number of backtests and costs **1.18x**
  wall-clock, not the 15x the original ADR feared. The geometry was not reduced.

**Promotion criterion — met.** Fold-isolation tests pass; budget parity holds per
fold (60 evaluations per engine in each of 15 folds on a real pilot); the full
offline suite is green (634 tests); fixed-seed runs reproduce.

Evidence: [ADR 0012](../decisions/0012-outer-fold-contamination-in-candidate-search.md),
[Gate R1](phase_gates.md#gate-r1--restore-temporal-validity--passed-2026-08-09).

---

## Phase R2 — Re-baseline momentum and the engine comparison — **COMPLETE (2026-08-09)**

**Objective.** Re-establish the two frozen results under the corrected protocol.

**Question.** Do FR-1 (momentum has no edge) and FR-2 (no GA advantage) hold once
the search can no longer see the future?

**Depends on:** R1.

**Deliverables.** Re-run the momentum study — 2 assets × 10 derived seeds × 15
folds — under per-fold search; re-run the paired RS-vs-GA comparison; a new ADR
that states plainly whether the frozen conclusions changed.

**Expected outcome, stated in advance.** FR-1 is expected to hold or worsen:
removing an optimistic bias rarely improves measured performance. FR-2's point
estimate is expected to move toward zero, because the GA loses an advantage that
Random Search never had. **Recording this expectation now is what makes the
result falsifiable.**

**Promotion criterion.** The study completes at full seed coverage with budget
parity per fold, and the outcome is documented whichever way it falls.

**Handling of the old results.** FR-1 to FR-4 stay in the repository as frozen
records with a note that they predate the correction. They are **not** deleted
and **not** restated more favourably.

**Outcome.** Study `multiseed_momentum_r2_clean_v2` completed all 20 units with
300 evaluations per engine inside every one of 15 folds. All 40
asset-seed-engine combinations lost money; none beat buy-and-hold, survived
doubled costs or had a bootstrap Sharpe interval excluding zero. Momentum is
**rejected** and must not be retuned. The paired GA - RS estimate is -0.061,
95% CI [-0.399, +0.277], Cohen's dz -0.100: no engine advantage. Full evidence
and the old-vs-new qualification are in
[ADR 0013](../decisions/0013-clean-momentum-rebaseline.md).

---

## Phase R3 — Evaluate the implemented families — **COMPLETE (2026-08-10, negative)**

**Objective.** Give every implemented family a fair, comparable hearing.

**Question.** Does any of breakout, mean reversion, volatility breakout, funding
or cross-asset confirmation show an effect that survives multiple seeds?

**Answer.** **No.** All five families are `REJECTED` under the pre-registered
promotion criteria. Evidence:
[ADR 0015](../decisions/0015-r3-family-evaluation-negative.md),
`artifacts/runs/r3_full_budget100_ga21/r3_gate_verdict.json`.

**Depends on:** R1, R2.

| Family | Verdict | Strongest RS signal |
|---|---|---|
| Breakout | REJECTED | 0/10 positive seeds both assets |
| Mean reversion | REJECTED | 0/10 positive seeds both assets |
| Volatility breakout | REJECTED | BTC 6/10 positive; CI bootstrap never >0 |
| Funding | REJECTED | 0/10 BTC; 1/10 ETH |
| BTC-ETH confirmation | REJECTED | 1/10 BTC; 0/10 ETH |

**Progression completed.** Pilot → multi-seed (10 seeds, budget 100/fold/engine)
→ robustness + promotion gate → reject. No family is retuned.

**Promotion criterion for a family.** Stated fully in
[phase_gates.md](phase_gates.md#gate-r3--family-evaluation). In summary: a
majority of seeds positive on both assets, a bootstrap Sharpe CI excluding zero,
survival of doubled costs, and no dependence on a handful of trades.

**Rejection criterion.** Any family failing these is recorded as `REJECTED` with
its evidence and **is not retuned to pass**. Rejecting all five families is the
observed, reportable outcome.

**Budget discipline.** Common budget 100 per fold and engine
([ADR 0014](../decisions/0014-r3-budget-bounded-by-search-space.md)).

---

## Phase R4 — Robustness coverage — **SKIPPED as promotion gate**

**Objective.** Close the gap between the robustness this project claims and the
robustness it implements.

**Depends on:** Gate R3 with at least one **promoted** family. Completing the
multi-seed study in R3 is necessary but not sufficient. **If no family is promoted
in R3, this gate is skipped** as a confirmatory phase. Families **rejected** in R3
cannot use R4 as a rescue path; any analysis of rejected families after R3 closure
is **exploratory** and **cannot alter** the recorded `CLOSED_NEGATIVE` verdict.

**Missing today.**

| Check | Purpose |
|---|---|
| Parameter perturbation | Distinguish a genuine effect from a knife-edge parameter |
| Regime-conditional evaluation | Test whether an effect is regime-specific rather than universal |
| Trade-path resampling | Characterise the distribution of equity paths, not just the realised one |

**Explicit naming discipline.** The existing circular block bootstrap is a
**block bootstrap**. It must not be called a Monte Carlo account simulator; that
belongs to Phase P3 and requires an account model that does not yet exist.

**Promotion criterion.** Each new check has unit tests, is wired into the study
report, and is applied only to families **promoted** in Gate R3.

---

## Phase S1 — Controlled strategy expansion

**Objective.** Add new families only where EDA or the literature supplies a
mechanism, and only at a controlled cost in degrees of freedom.

**Depends on:** R3, R4.

Every new family must document, before any code is written:

```
EDA / statistical motivation
  → hypothesis
  → features
  → parameters
  → expected mechanism
  → validation experiment
  → promotion / rejection criterion
```

### Primary candidates (mechanism-driven)

| Family | Motivating finding | Hypothesised mechanism |
|---|---|---|
| Volatility contraction → expansion (squeeze) | Volatility clustering | Compressed ranges precede directional expansion |
| Failed-breakout reversal | Breakout failure rate | A rejected break signals exhausted flow |
| Funding + momentum | Funding persistence + trend | Crowded funding and trend agreement marks positioning |
| Funding + basis proxy | Funding and basis co-movement | Joint dislocation is a stronger signal than either alone |
| BTC/ETH relative strength | Cross-asset dependence | Persistent leadership rotates between the two |
| Breakout + taker-flow confirmation | Activity relates to \|returns\| | Aggressive flow separates real breaks from noise |
| Regime-conditional strategies | Identified volatility regimes | An effect exists only in part of the state space |
| Regime switching / strategy selection | Regime persistence | Choosing *which* strategy to run beats any single one |

### Secondary candidates (classical indicators)

RSI, MACD, Stochastic, Bollinger Bands, ROC, ADX and further EMA variants.

**These are gated deliberately.** They are cheap to add and therefore the fastest
route to indicator mining. Each requires a stated mechanism and enters the same
budget accounting as any other family. **No batch addition. No "try them all and
see."** If a secondary indicator is added purely because it is standard, that
motivation must be written down as such and its result interpreted accordingly.

### Research-budget accounting

Each new family records:

| Field | Why |
|---|---|
| Scientific motivation | Prevents post-hoc rationalisation |
| New degrees of freedom | Counts the parameters added |
| Search-space expansion | Quantifies the multiple-comparison burden |
| Required validation budget | Makes cost explicit before commitment |
| Promotion / rejection rule | Fixed before the result is seen |

**Hard constraint.** Optimisation stays layered. There must never be a single
Genetic Algorithm that jointly searches indicators, thresholds, timeframes,
stops, ML hyperparameters and portfolio weights. That search would be
unfalsifiable at this data scale.

---

## Phase S2 — Advanced statistical strategies (specification only)

**Objective.** Specify the statistically demanding ideas without committing to
implement them.

* **BTC-ETH spread modelling** — model the spread rather than each leg.
* **Causal hedge-ratio estimation** — rolling/expanding only; a full-sample beta
  is look-ahead.
* **Pairs trading** — conditional on a stable causal hedge ratio.
* **Cointegration** — only where a test on development data justifies it; two
  assets over four years is thin evidence for a long-run relationship.
* **Multi-timeframe confirmation** — the 15m/1h derived bars already exist.
* **Strategy ensembles** — combining signals; note this overlaps Phase P1 and the
  boundary must be decided before either is built.

**Nothing here is scheduled.** These are recorded so a future reader knows they
were considered and why they were deferred.

---

## Phase M1 — Labeling and meta-labeling (specification)

**Objective.** Build the labeling layer that a machine-learning filter needs.

**Depends on:** at least one family reaching `ROBUST`. **If no family survives R3,
this phase does not begin** — an ML filter on a signal with no edge filters noise.

**Deliverables.** Triple-barrier labeling (profit target, stop, time limit) with
causal barrier placement; meta-labels of the form *"the base strategy fired — was
it right?"*; extension of `features/predictors.py` to populate `label_time`,
which is currently always null; and leakage tests proving a label never uses
information available before its own resolution.

---

## Phase M2 — ML filters (specification)

**Objective.** Answer one narrow question:

> Given that an interpretable base strategy generated a trade, should this trade
> be accepted?

**Architecture.**

```
interpretable base strategy → signal → triple-barrier / meta-label → ML filter
```

**Models, in this order.** Logistic Regression (the interpretable baseline that
must be beaten), Random Forest, then LightGBM.

**Explicitly rejected design.** LightGBM must **not** become an unexplained
end-to-end trading oracle predicting returns from raw features. The base strategy
stays interpretable; ML only accepts or rejects its trades. This is what keeps
the thesis explainable.

**Required alongside any ML result.** Probability calibration (reliability curves,
Brier score); feature importance and permutation importance; SHAP where it adds
insight; and an ablation isolating the filter's contribution.

**Promotion criterion.** The filter must beat the *unfiltered base strategy* on
out-of-sample data across multiple seeds. Beating a random filter is not enough.

---

## Phase P1 — Portfolio (specification)

**Question the layer answers:** *What positions would we like to hold?*

Responsibilities: combining strategies; combining BTC and ETH exposure; capital
allocation; strategy allocation; correlation-aware allocation; volatility
targeting; possibly risk parity; and net/gross exposure accounting.

**Boundary.** Portfolio must never silently override strategy research logic. If
it changes what a strategy asked for, that change is explicit, recorded and
measurable in an ablation.

---

## Phase P2 — Risk (specification)

**Question the layer answers:** *Are these desired positions allowed, and at what
size?*

Risk is kept **separate from Portfolio** so that "what we want" and "what we are
permitted" never collapse into one untraceable number.

Eventual controls: position sizing; per-trade risk; per-strategy, per-asset and
gross/net exposure limits; leverage; portfolio volatility; drawdown limits; daily
loss limits; Expected Shortfall and tail-risk monitoring; stress scenarios; and
kill-switch conditions.

**Boundary.** Risk must be able to **reject or reduce** desired positions. A risk
layer that can only observe is not a risk layer.

---

## Phase P3 — System robustness and simulation (specification)

Robustness operates at **every** layer, not only at the end:

| Layer | Robustness question |
|---|---|
| Strategy | Does the effect survive seeds, costs and delay? |
| Meta-label | Does the filter survive threshold changes and calibration drift? |
| Portfolio | Does allocation survive correlation shifts? |
| Risk | Do limits bind when they should? |
| System | What is the distribution of account outcomes? |

**Only here** does genuine Monte Carlo simulation become meaningful: trade-path
resampling, equity-path simulation, stress scenarios and risk of ruin — because
only here does a full account model exist.

---

## Phase P4 — Funded-account research (specification)

A layer **above** portfolio and risk, modelling proprietary-firm account rules.

**Configurable rules** (provider-configurable, never hardcoded): daily loss
limit; maximum and trailing drawdown; profit target; consistency rules; minimum
trading days; account resets; payouts; floating-equity treatment.

**Crypto-specific considerations:** 24/7 markets with no daily close to anchor a
"trading day"; funding as a continuous cashflow; leverage; and the strong BTC/ETH
dependence, which means two positions are not two independent bets.

**Estimable quantities:** probability of passing; probability of violating the
daily drawdown; probability of violating maximum drawdown; expected time to
target; risk of ruin; expected payout; and sensitivity to risk-per-trade.

**Precondition.** This is only meaningful with a strategy that has demonstrated
an edge. Simulating a funded account for a strategy with no edge measures the
account rules, not the strategy.

---

## Phase X1 — Execution progression (specification)

```
offline research → internal paper trading → exchange demo/testnet
  → shadow live → very small real capital → controlled scaling
```

**Architectural rule.** Exchange-specific behaviour lives behind adapters.
Strategies never call an exchange.

```
Strategy → Meta-label → Portfolio → Risk → Execution → ExchangeAdapter
```

Planned adapters: Paper/Demo, Binance, Bybit, future venues.

Engineering concerns to be addressed at that time: websocket market data; order
management; fills; reconciliation; stale-data detection; API failure handling;
rate limits; tick and lot sizes; reduce-only behaviour; funding reconciliation;
position reconciliation; idempotency; logging; alerts; and a kill switch.

**No real-capital trading is in scope for this thesis.**

---

## Phase H — Holdout evaluation (frozen)

The holdout `[2026-01-01, 2026-07-01)` is opened **exactly once**, for the final
report, and only after a strategy has been frozen.

Required record at that moment: timestamp; git commit and worktree state; the
resolved configuration; dataset hashes; and the previously selected strategy —
proving selection preceded the opening.

**If no strategy is promoted, the holdout is still opened once** to report the
honest outcome of the best available candidate, clearly labelled as such.

---

## Incremental evaluation and ablations

Systems are evaluated as **layers**, never as one opaque final number:

| Layer | Configuration |
|---|---|
| A | Base strategy |
| B | A + regime filter |
| C | B + meta-labeling |
| D | C + portfolio construction |
| E | D + risk overlay |

Each step reports the change in OOS return, Sharpe, drawdown, turnover, cost
sensitivity, tail risk, and stability across folds and seeds.

**A layer that does not improve anything must be reported as such.** Complexity
without measured benefit is a finding, not an embarrassment.

---

## Reproducibility contract

Every future experiment records: code revision (commit + diff hash); config
hash; data manifests; seed and derived seed streams; asset; fold geometry;
engine; candidate; search budget; cost assumptions; artifacts; status, events
and checkpoints; and final statistical summaries.

**Two runs whose experimental contracts differ materially must never be compared
without stating the difference.** `RunIdentity` exists to enforce exactly this.

The temporal contract is part of that identity. Run summaries record
`search_protocol`, and `evaluation/multi_seed.assert_protocol()` raises rather
than pool a superseded unit with a clean one, so the two protocols cannot be
mixed by accident.

---

## Next executable phase

**Gates R1–R3 are complete; R4 experimental application is skipped.** No
searchable family demonstrated a robust development-period edge. Momentum (R2)
and all five R3 families are `REJECTED` with recorded evidence
([ADR 0013](../decisions/0013-clean-momentum-rebaseline.md),
[ADR 0015](../decisions/0015-r3-family-evaluation-negative.md)).

The holdout remains closed. There is no promoted strategy to evaluate on it.

The next *methodological* work, if the thesis scope expands, is **S1 — controlled
strategy expansion**: new families only where EDA supplies a mechanism, with
degrees of freedom and search-space expansion quantified **before** any code.
Meta-labeling (M1), portfolio (P1) and simulation (P3) remain blocked without a
robust base strategy.

For the current experimental arc, the defensible thesis outcome is a **rigorous
negative result** under corrected temporal isolation, equal budget discipline and
explicit promotion criteria — not a holdout performance claim.
