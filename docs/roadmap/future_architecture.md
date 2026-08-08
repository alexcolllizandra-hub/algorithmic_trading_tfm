# Future architecture

**Version:** 1.0 · **Date:** 2026-08-08

The dependency structure of the system, showing what exists today and what is
specified for later. **No directory is created before the phase that implements
it** — empty packages would misrepresent the project's maturity.

Related: [current state](current_state.md) · [master roadmap](master_roadmap.md) ·
[phase gates](phase_gates.md) · [scientific questions](scientific_questions.md)

---

## Pipeline

Legend: **[built]** implemented and tested · **[spec]** specified only

```
DATA [built]
  src/perp_lab/data — ingestion, validation, partitioning, manifests
  ↓
EDA [built]
  src/perp_lab/eda — 23 modules; descriptive, motivates hypotheses
  ↓
FEATURES [built]
  src/perp_lab/features — 25 causal kinds, core/extended/experimental packs
  ↓
STRATEGIES [built]
  src/perp_lab/strategies — 6 searchable families + 6 fixed baselines
  ↓
BACKTESTER [built]
  src/perp_lab/backtesting — next-bar execution, fees, slippage, funding
  ↓
WALK-FORWARD [built]
  src/perp_lab/validation — expanding folds, purge + embargo, holdout guards
  ↓
SEARCH [built, being corrected]
  src/perp_lab/search — Random Search, Genetic Algorithm, budget parity
  ⚠ currently pools validation across outer folds — Phase R1 fixes this
  ↓
MULTI-SEED [built]
  src/perp_lab/experiments/multi_seed — seed grid, checkpoint/resume
  src/perp_lab/evaluation/multi_seed — fold-level inference
  ↓
BASE ROBUSTNESS [built, partial]
  src/perp_lab/evaluation/robustness — bootstrap, cost/slippage/delay, concentration
  ✗ missing: parameter perturbation, regime conditioning, path resampling
  ↓
╔═══════════════════════════════════════════════════════╗
║  STRATEGY PROMOTION / REJECTION                       ║
║  The decision point. Nothing below proceeds without   ║
║  at least one family reaching ROBUST.                 ║
╚═══════════════════════════════════════════════════════╝
  ↓
TRIPLE BARRIER / META-LABELING [spec]        → models/labeling
  ↓
LOGISTIC / RANDOM FOREST / LIGHTGBM [spec]   → models/
  ↓
PORTFOLIO [spec]                             → portfolio/
  "What positions would we like to hold?"
  ↓
RISK [spec]                                  → risk/
  "Are these positions allowed, and at what size?"
  ↓
SYSTEM ROBUSTNESS / SIMULATION [spec]        → simulation/
  ↓
FUNDED-ACCOUNT SIMULATOR [spec]              → funded/
  ↓
PAPER / DEMO / SHADOW EXECUTION [spec]       → execution/
  ↓
EVENTUAL LIVE DEPLOYMENT [out of thesis scope]
```

---

## Robustness is a cross-cutting layer

The linear diagram above is misleading in one respect: **robustness is not a
single stage.** It applies at every level, asking a different question each time.

```
                    ┌─────────────────────────────────────┐
   STRATEGY ────────┤ seeds · costs · delay · concentration │  [built]
   META-LABEL ──────┤ threshold · calibration drift         │  [spec]
   PORTFOLIO ───────┤ correlation shift · allocation        │  [spec]
   RISK ────────────┤ do limits bind when they should?      │  [spec]
   SYSTEM ──────────┤ account outcome distribution          │  [spec]
                    └─────────────────────────────────────┘
                          cross-cutting concern
```

**Naming discipline.** The implemented circular block bootstrap is a **block
bootstrap**. Calling it a Monte Carlo account simulator would be false: genuine
Monte Carlo requires an account model with rules, sizing and path dependence,
which only exists at the simulation layer.

---

## Module boundaries

### Existing packages

| Package | Responsibility | Must not |
|---|---|---|
| `data/` | Acquire, validate, partition, hash | Compute features |
| `eda/` | Describe the development period | Feed decisions or parameters |
| `features/` | Causal predictors with declared warm-up | Use future data |
| `strategies/` | Target position at bar close | **Call an exchange**; apply costs; size positions |
| `backtesting/` | Execution, costs, funding, metrics | Choose strategies |
| `validation/` | Fold geometry, purge/embargo, holdout guards | Know about strategies |
| `search/` | Propose and rank candidates | Touch test or holdout during selection |
| `evaluation/` | Score persisted OOS artifacts | Re-run search; open the holdout |
| `experiments/` | Orchestrate studies, checkpoint/resume | Compute statistics |
| `tracking/` | Run identity, journal, artifacts | Interpret results |
| `regimes/` | Fit on train, apply causally | Fit on validation or test |
| `api/`, `dashboard/` | Present persisted artifacts read-only | Compute new results |

### Future packages

Introduced **only** at their implementing phase.

| Package | Responsibility | Boundary |
|---|---|---|
| `models/` | Labeling and ML filters | May only accept/reject or size base-strategy trades; never invents signals |
| `portfolio/` | Combine strategies and assets into desired positions | Must not silently override strategy logic |
| `risk/` | Approve, reduce or reject desired positions | Must be able to say **no** |
| `simulation/` | Account-level Monte Carlo, stress, risk of ruin | Requires a real account model |
| `funded/` | Provider-configurable prop-firm rules | Rules are data, never hardcoded |
| `execution/` | Consume approved targets, manage orders | Venue behaviour lives behind adapters |

---

## Architectural rules

These are commitments, not preferences.

### 1. Strategies never call an exchange

A strategy emits a target position. Nothing else. This keeps it testable offline,
comparable across venues, and free of latency and connectivity concerns.

### 2. Portfolio must not silently override strategy research logic

If the portfolio layer changes what a strategy asked for, that change is
explicit, recorded and measurable in an ablation. Otherwise strategy research
becomes unfalsifiable — you can no longer tell whether the strategy or the
allocator produced the result.

### 3. Risk must be able to reject or reduce

A risk layer that only observes is monitoring, not risk management. It sits
between desired and executed positions with the authority to shrink or refuse.

### 4. Execution consumes approved target positions

Execution receives a target that has already passed portfolio and risk. It never
reaches back for a signal.

### 5. Exchange behaviour lives behind adapters

```
Strategy → Meta-label → Portfolio → Risk → Execution → ExchangeAdapter
                                                          ├── Paper / Demo
                                                          ├── Binance
                                                          ├── Bybit
                                                          └── future venues
```

Tick sizes, lot sizes, rate limits, reduce-only semantics and funding
reconciliation are adapter concerns. No `if exchange == "binance"` above the
adapter line.

### 6. The holdout is opened once, from one place

Development code loads the development partition and asserts
`max(open_time) < holdout_start`. Touching the holdout requires a separate,
explicit path that records commit, config, dataset hashes and the
previously-frozen strategy.

---

## Data flow through the future stack

```
                bars + funding
                      │
                      ▼
              causal features ──────────────┐
                      │                     │
                      ▼                     ▼
            base strategy signal      meta-features
                      │                     │
                      └──────┬──────────────┘
                             ▼
                    triple-barrier label
                             │
                             ▼
                    ML filter: accept / reject
                             │
                             ▼
                  filtered signal per strategy
                             │
                             ▼
      PORTFOLIO: combine strategies × {BTC, ETH}
        correlation-aware · vol targeting · gross/net
                             │
                             ▼
                   desired target positions
                             │
                             ▼
      RISK: sizing · exposure caps · leverage · drawdown
            daily loss · tail monitoring · kill switch
                             │
                             ▼
                   approved target positions
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
      BACKTESTER (research)         EXECUTION (future)
              │                             │
              ▼                             ▼
       OOS ledger + metrics         ExchangeAdapter
              │
              ▼
      evaluation · robustness · simulation · funded-account
```

**One invariant worth stating explicitly:** the backtester and the future
execution layer must consume the **same** approved target positions. If research
and execution diverge here, backtest results stop describing the live system.

---

## Incremental evaluation

Layers are measured one at a time. This is what the diagram is *for*.

| Config | Stack |
|---|---|
| A | Base strategy |
| B | A + regime filter |
| C | B + meta-labeling |
| D | C + portfolio construction |
| E | D + risk overlay |

Each step reports the change in OOS return, Sharpe, drawdown, turnover, cost
sensitivity, tail risk and stability across folds and seeds.

**Never present only configuration E.** A single opaque final number cannot be
attributed to any component, and a layer that contributes nothing must be
reported as contributing nothing.

---

## Current architectural debt

| Item | Impact | Resolution |
|---|---|---|
| Search pools validation across outer folds | Invalidates the temporal contract | [Phase R1](master_roadmap.md#phase-r1--restore-temporal-validity-blocking) |
| Leakage fix on a divergent branch | The fix cannot be merged as-is | Re-apply against the multi-seed branch |
| Two dashboards (Streamlit + Next.js) | Duplicate presentation logic | Streamlit already marked legacy |
| `docs/roadmap.md` / `docs/architecture.md` stale | Misleads a future reader | Superseded by this directory |
| Robustness claims exceed implementation | Over-claiming | [Phase R4](master_roadmap.md#phase-r4--robustness-coverage) |
| Dashboard cannot express maturity | Implementation is confused with validation | Add an evidence surface |

---

## Dashboard: what it must eventually show

The research dashboard is an **educational and traceability** surface, not an
engineering admin panel. Without redesigning the UI, it should eventually make
visible:

* what is implemented, versus what has actually been experimentally evaluated;
* whether evidence is positive, negative or inconclusive — **negative results
  displayed as prominently as positive ones**;
* the current research phase and its gate;
* frozen holdout status (closed, and provably untouched);
* the chain EDA → hypothesis → feature → strategy → experiment → result.

The last item is the one that turns the dashboard from a results viewer into an
explanation of *why* each strategy exists.
