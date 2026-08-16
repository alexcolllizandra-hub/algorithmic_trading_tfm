# Roadmap and project state

Entry point for understanding **what this project is, what has actually been
built, what has actually been demonstrated, and what comes next.**

Consolidated on 2026-08-08 from a direct audit of the repository. Where earlier
documentation contradicted the code, the code was taken as the source of truth.

---

## Read in this order

| # | Document | Answers |
|---|---|---|
| 1 | [current_state.md](current_state.md) | What exists, what is tested, what has been experimentally evaluated, what failed |
| 2 | [scientific_questions.md](scientific_questions.md) | Why each strategy family exists, traced to measured EDA findings |
| 3 | [master_roadmap.md](master_roadmap.md) | What comes next and in what order |
| 4 | [phase_gates.md](phase_gates.md) | What must be demonstrated before each phase advances |
| 5 | [future_architecture.md](future_architecture.md) | How the layers fit together, and the boundaries between them |

---

## The 60-second summary

**What the project is trying to discover.** Whether interpretable, cost-aware
intraday strategies on BTC/ETH USDT-M perpetual futures can produce a
demonstrable out-of-sample edge, and whether a Genetic Algorithm discovers such
strategies better than Random Search at an equal evaluation budget.

**What has been built.** A complete research pipeline: data ingestion, EDA, a
causal feature engine, six strategy families, a cost- and funding-aware next-bar
backtester, walk-forward validation with purge and embargo, Random Search and a
Genetic Algorithm at enforced budget parity, deterministic multi-seed
orchestration, a robustness battery, run-provenance tracking, and a FastAPI +
Next.js research dashboard.

**What has been demonstrated.** Very little, and that is the honest finding.

* Momentum has **no demonstrated edge** across 10 seeds and 15 folds.
* There is **no evidence** the Genetic Algorithm beats Random Search.
* **Zero of 40** run/engine combinations produced a bootstrap Sharpe confidence
  interval excluding zero.
* Single-seed conclusions in this problem are unreliable by measurement, not by
  assumption.

**What failed.** The momentum family, and the apparent single-seed advantage of
the Genetic Algorithm. Both are recorded as frozen results and **must not be
retuned** to look better.

**What remains inconclusive.** Five of six strategy families: breakout and mean
reversion have never been run on real data; volatility breakout, funding and
cross-asset confirmation have only a single-seed pilot that establishes pipeline
correctness, not performance.

**What comes next, and why.** [Phase R1](master_roadmap.md#phase-r1--restore-temporal-validity-blocking):
the audit found that candidate search optimised a fitness pooled across *all*
walk-forward folds, including folds later than the one being scored. Every
existing result carries this defect. No new family may be evaluated until it is
fixed, or the new evidence inherits the same flaw.

**What must be demonstrated before advancing.** See
[phase_gates.md](phase_gates.md). In short: fold isolation proven by test, budget
parity per fold, and a byte-reproducible run.

---

## Status at a glance

| Layer | Implementation | Validation |
|---|---|---|
| Data · EDA · Features | Tested | n/a |
| Strategies (6 families) | Tested | 1 multi-seed (negative), 3 piloted, 2 never run |
| Backtester · Walk-forward | Tested | n/a |
| Search (RS + GA) | Tested | Multi-seed — no engine advantage; **protocol being corrected** |
| Multi-seed · Robustness | Tested | Applied once; coverage incomplete |
| Tracking · Dashboard | Tested | n/a |
| ML / meta-labeling | **Not implemented** | — |
| Portfolio · Risk · Simulation · Funded · Execution | **Not implemented** | — |
| Holdout `[2026-01-01, 2026-07-01)` | — | **Opened once (2026-08-13), consumed; reading withheld** |

---

## Ground rules

1. The holdout is opened **once**, for the final report, after a strategy is
   frozen.
2. Implementation status and validation status are tracked **separately**. A
   strategy being implemented says nothing about whether it works.
3. A rejected result is **not retuned** until it passes.
4. A negative but rigorous result is a valid thesis outcome. A positive result
   obtained through leakage or overfitting is not.

---

## Superseded documents

* `docs/roadmap.md` — stated that only Phase 1 was implemented; superseded by
  this directory.
* `docs/architecture.md` — module status table predates the shipped search,
  evaluation and tracking layers; see
  [future_architecture.md](future_architecture.md).
