# Gate S2 — Batch 01 (frozen pre-specification)

**Version:** 1.0 · **Frozen:** 2026-08-11 · **Status:** S2-A passed; S2-B **not
started at the time of freezing**

This instantiates the generic Gate S1/S2 contract in
[phase_gates.md](phase_gates.md) with a concrete, limited and **frozen** batch of
three families. Everything below was written before any S2 performance result
existed. Nothing here may be edited after the first S2-B run starts; a change
requires a new batch with a new number.

Related: [gate_s1_batch_01.md](gate_s1_batch_01.md) ·
[gate_s1b_outcome.md](gate_s1b_outcome.md) ·
[../research/s2_evidence_matrix.md](../research/s2_evidence_matrix.md) ·
[../research/data_inventory.md](../research/data_inventory.md) · ADR 0017.

---

## Dependency status

| Gate | State | Consequence for S2 |
|---|---|---|
| R2 | `CLOSED_NEGATIVE` (ADR 0013) | Families not re-searched |
| R3 | `CLOSED_NEGATIVE`, 0/5 promotions (ADR 0015) | Families not re-searched |
| R4 | `SKIPPED` — zero R3 promotions | Vacuous; S2 does not reopen it |
| S1 | `S1_STOPPED_AFTER_PILOT_INCONCLUSIVE` (ADR 0017) | S1-B evidence is *not* a confirmatory rejection. S1 families are nevertheless **not** re-searched, re-parameterised or recombined in this batch |

**S1 is stopped, not refuted.** No S2 family may be justified by, derived from,
or presented as a repair of an S1 family.

---

## 1. Why this batch exists: the one unexploited data axis

The data inventory ([data_inventory.md](../research/data_inventory.md)) shows
that every family searched in R2, R3 and S1 was built from **price** (open, high,
low, close), **unsigned volume**, or the **published funding rate**. Three
columns present in every ingested kline have never been read by any strategy:

| Column | What it is | Used by R2/R3/S1? |
|---|---|---|
| `taker_buy_base` | base volume that lifted the ask | **No** |
| `taker_buy_quote` | quote volume that lifted the ask | **No** |
| `trade_count` | number of trades in the bar | **No** |

`taker_buy_quote` is the **aggressor side**, reported by the exchange. The entire
Lee–Ready, tick-rule and bulk-volume-classification literature exists to
*estimate* this quantity from anonymous prints; Binance publishes it. That is the
single largest piece of unexploited, causally-clean, already-ingested information
in the dataset, and it is the organising principle of this batch.

**Naming discipline.** This is **trade (taker) imbalance**, never "OFI". The
canonical Cont–Kukanov–Stoikov order-flow imbalance is defined over limit-order
arrivals and cancellations at the best quotes; those events are not in our data
and no family here claims to measure them.

---

## 2. Batch contents

Three families. The batch is deliberately smaller than the four permitted: two
further candidates were designed and then **discarded before any result was
computed** (section 6), which is the intended outcome of a novelty audit.

| ID | Family | Mechanism class | Signal variable | Exit governed by | Response sign |
|---|---|---|---|---|---|
| S2-01 | `taker_flow_extreme` | Aggressive-flow pressure | Windowed signed taker imbalance | Clock | **Searched** |
| S2-02 | `illiquidity_reversion` | Immediacy premium / liquidity provision | Amihud impact: \|move\| per unit traded value | Signal (illiquidity normalises), with a hard cap | Fixed (fade) |
| S2-03 | `flow_price_divergence` | Passive absorption | Sign disagreement between flow and the move it produced | Clock | **Searched** |

### Why the response sign is a searched parameter, not an assumption

For S2-01 and S2-03 the literature does not settle the direction:

* Kim & Hansen report a **positive** relation between quarter-hour opening order
  imbalance and returns at 4–12 h horizons on Binance USDT-M perpetuals.
* Chordia, Roll & Subrahmanyam report a **negative** coefficient on *lagged*
  order imbalance in equities.

Fixing the sign by assumption would smuggle in a choice the evidence does not
support. Both arms are therefore inside the declared space and both are charged
to the hypothesis ledger in section 4.

### Why holding periods are multi-hour

Pindza (2026) evaluates essentially these features on Binance perpetuals with
correct purging and explicit VIP-0 costs and reports **net Sharpe −10.68 to
−18.42**, driven by 124–204× daily notional turnover at a five-minute rebalance.
Kim & Hansen's positive result sits at 4–12 h. The two are consistent: the
horizon, not the feature, is what a five-minute microstructure strategy fails on.
The claim under test in S2-01 and S2-03 is therefore not "flow predicts returns"
but "flow predicts returns *by enough, and for long enough*, to survive a round
trip". `holding_bars ∈ {4, 6, 8, 12}` on 1 h bars is that band, frozen.

---

## 3. Material difference from R2/R3/S1 (novelty audit)

| S2 family | Nearest earlier relative | Shared | Different | How the difference is enforced |
|---|---|---|---|---|
| S2-01 `taker_flow_extreme` | S1-02 `funding_reversal` | Trailing-percentile extreme trigger; clock exit | Ranks *realised aggressive volume* within the bar window, not the 8-hourly published funding rate. Different input, different frequency, different economic claim (immediacy demand vs. crowded carry) | Different input columns entirely; `funding_rate` is never read |
| S2-02 `illiquidity_reversion` | R3 `mean_reversion` | Fades a move | Triggers on the move **per unit of traded value**. A large move on heavy volume triggers R3 and is deliberately *ignored* here; a modest move on thin volume is invisible to R3 and is exactly what this trades | `test_illiquidity_reversion_is_materially_different_from_mean_reversion` measures the Jaccard overlap of the two trigger sets and fails above 0.25 |
| S2-03 `flow_price_divergence` | S2-01 (within batch) | Same input columns | Fires on **sign disagreement**, not magnitude. Because windowed imbalance and windowed return correlate at ≈ +0.5 on both assets (measured, section 5), most S2-01 triggers have flow and price agreeing and are invisible here | `test_s2_families_trigger_on_different_bars` fails if any pair exceeds Jaccard 0.5 |

Material difference is **measured in the test suite**, not asserted in prose, so
a later reparameterisation that quietly collapses one family into another breaks
a test rather than passing review.

---

## 4. Frozen hypothesis count (data-snooping ledger)

Space cardinalities after validity filtering, computed by
`SearchSpace.finite_cardinality()` and pinned by
`test_recorded_cardinalities_match_the_frozen_prespecification`:

| Family | Valid configurations | Assets | Nominal hypotheses |
|---|---:|---:|---:|
| `taker_flow_extreme` | 6 912 | 2 | 13 824 |
| `illiquidity_reversion` | 5 184 | 2 | 10 368 |
| `flow_price_divergence` | 10 368 | 2 | 20 736 |
| **S2 batch total** | **22 464** | | **44 928** |

The number used for the deflated Sharpe ratio is the count of **unique valid
objective evaluations actually recorded by each run**, per family and per asset —
never the cardinality above and never the budget.

### Global hypothesis ledger (cumulative)

The development partition has now been consulted across four batches. S2 does
**not** restart the counter.

| Batch | Families | Outcome | Development consultations |
|---|---|---|---|
| R2 | 1 (`momentum`, rebaselined) | `CLOSED_NEGATIVE` (ADR 0013) | 1 |
| R3 | 5 | `CLOSED_NEGATIVE`, 0/5 promoted (ADR 0015) | 2 |
| S1 | 4 | `S1_STOPPED_AFTER_PILOT_INCONCLUSIVE` (ADR 0017) | 3 |
| **S2** | **3** | pending | **4** |

**Batch attempt counter: S2 attempt 1; development-partition consultation 4.**
This counter is reported alongside every S2 result. Any family-level p-value
interpreted across the S2 batch is corrected by Benjamini–Hochberg at α = 0.05
over the three families; the batch counter is reported so a reader can judge the
cumulative search burden across all four batches, which no single-batch
correction accounts for.

---

## 5. Data-property measurements made *before* the freeze

These are descriptive statistics on the development partition. They informed the
parameter grids and the family selection. **None of them consulted returns,
Sharpe ratios or PnL** — only trigger frequency and the correlation structure of
inputs — so they are pre-specification engineering, not result-driven tuning.

| Measurement | BTCUSDT | ETHUSDT | Consequence |
|---|---|---|---|
| corr(windowed taker imbalance, windowed return), w = 4/8/24 h | +0.505 / +0.525 / +0.550 | +0.509 / +0.520 / +0.503 | Confirms that sign disagreement is a genuinely informative event and not noise, justifying S2-03 |
| Bars with flow/price sign disagreement | 23.2–24.6 % | 24.3–27.9 % | Frequent enough to populate folds |
| Disagreement **and** both magnitudes above their 85th percentile | 0.021–0.074 % | 0.010–0.167 % | **Not viable**: too rare to populate a fold |
| Disagreement **and** both magnitudes above their 50th percentile | 1.05–1.88 % | 1.43–3.57 % | Viable; sets the S2-03 grid at `{0.5, 0.6, 0.7}` |
| `mark_price_close == close` (5 m, development) | 12.5 % exactly zero; 28.3 % within 0.1 bp | 11.6 % exactly zero; 23.6 % within 0.1 bp | Confirms the median operator censors the mark-minus-last gap; combined with only 1.2 % / 2.3 % of bars exceeding the 10 bp round trip, the dislocation idea is **discarded** (section 6) |

The S2-03 grid is deliberately much lower than the other two families' for this
reason, and the justification is recorded in the docstring of
`FlowPriceDivergenceFamily` so it cannot be lost.

---

## 6. Candidates designed and discarded before any result

Recording rejected candidates matters: a batch that only lists what was run
understates the search burden.

| Candidate | Why it was discarded |
|---|---|
| **Mark-vs-last dislocation reversion** | Two independent grounds. (i) *Cost*: only 1.2 % (BTC) / 2.3 % (ETH) of 5-minute bars show a gap exceeding the 10 bp round trip, and the recoverable fraction of a gap is smaller than the gap. (ii) *Measurement*: `mark = median(price1, price2, contract price)` censors the series at exactly zero whenever the traded price lies inside the index-anchored band — measured at 12.5 % / 11.6 % of bars exactly zero. The uncensored alternative (`premiumIndexKlines`) would require ingesting new market data, which is **not authorised** in this phase |
| **Funding-settlement flow event** | Would trade taker flow in the window around the 00:00 / 08:00 / 16:00 UTC settlements. Discarded for **material-equivalence risk**: S1-04 `intraday_seasonality` already searched all 24 entry hours (including the three settlement hours) with a clock exit, and S1-02 `funding_reversal` already traded the funding extreme. Adding a flow condition on top would be a conditional version of two stopped families rather than a new mechanism |
| **Perp-vs-index premium reversion** | The strongest candidate in the funding/basis literature (He et al.), but it requires `indexPriceKlines` / `premiumIndexKlines`, which are not ingested and cannot be downloaded in this phase. Recorded as the highest-value data acquisition for a future batch |
| **Anything using liquidations** | No liquidation feed exists in our data and Binance publishes no historical archive |
| **Open-interest features** | The `metrics` archive would supply them but starts only 2020-09 and is not ingested; acquisition not authorised in this phase |
| **Trade-size distribution / retail decomposition** | Requires tick data |
| **Directional families built on `trade_count`** | The literature links trade intensity and average trade size to **volatility**, not direction (Pinto 2025). `trade_count` therefore enters this batch only as a *falsification control* (section 7), never as a signal |

---

## 7. Mandatory falsification control (frozen)

Andersen & Bondarenko showed that VPIN's apparent predictive content was "due
primarily to a mechanical relation with the underlying trading intensity". We
hold `trade_count` directly, so the same objection applies to every family here.

**Frozen requirement.** Any S2 family that reaches a promotion discussion must
first be shown to add performance over a **trade-intensity placebo**: the same
family geometry, the same budget and the same folds, triggering on the trailing
percentile of `trade_count` instead of on the flow variable. A family that does
not beat its own intensity placebo is not promoted regardless of its absolute
metrics.

This control is **not** required to run the S2-B pilot, because a pilot that
shows no signal at all does not need a placebo to explain it.

---

## 8. Evaluation funnel

### S2-A — Technical validity · **PASSED 2026-08-11**

* Implementation: `src/perp_lab/strategies/{orderflow,taker_flow_extreme,illiquidity_reversion,flow_price_divergence}.py`
* Config: `src/perp_lab/config/experiment.py` (three validated family models)
* Registry: `src/perp_lab/search/registry.py` (`S2_FAMILIES`, space version 1.2.0)
* Tests: `tests/unit/test_strategies_s2.py` (36), `tests/unit/test_search_registry_s2.py` (17)
* Properties proven: truncation invariance, future-mutation invariance, warm-up
  flatness, zero-volume safety, **the flow lag is real** (a single-bar flow spike
  moves the position on the *next* bar, never its own), direction constraints,
  holding-cap enforcement, and measured material difference from
  `mean_reversion` and within the batch.

### S2-B — Development pilot · geometry frozen here

* Development partition only; the holdout `[2026-01-01, 2026-07-01)` is never
  loaded.
* Both assets (BTCUSDT, ETHUSDT), 1 h primary timeframe.
* Full development walk-forward geometry, purge and embargo from
  `configs/experiment.yaml` — unchanged from R3 and S1-B so results remain
  comparable.
* Costs, execution timing, fitness and annualisation from
  `configs/experiment.yaml` — unchanged.
* Seeds **{42, 43, 44}** per family per asset.
* **`effective_budget = 25`** unique valid non-cached evaluations per fold per
  engine, spent exactly by both Random Search and the Genetic Algorithm. This is
  the same per-fold budget S1-B used, so the unit of search is comparable.
* Total: 3 families × 2 assets × 3 seeds = **18 comparison runs**, each running
  both engines over the full development fold geometry.
* Purpose: screen whether any family shows enough development signal to justify a
  full S2-C study. It is **not** a promotion decision and a winner here carries
  no evidential weight on its own.

**Honest note on scale.** S1-B was one asset and one seed; S2-B is two assets and
three seeds at the same per-fold budget. S2-B is therefore a *larger* screen than
S1-B was, and the two are comparable in their unit of search but not in their
total search. This is recorded here rather than glossed, because a larger screen
has more opportunity to produce a favourable-looking result by chance. The
multi-seed design is used as a **robustness requirement** (a family must work
across seeds), never to select the best seed.

### PBO by common candidate set (frozen design)

S1-B could not compute the probability of backtest overfitting: CSCV needs one
performance matrix of the *same* configurations across all time blocks, and under
ADR 0012 the search is independent per outer fold, so no configuration is shared
between folds. S2-B closes that gap with an explicitly separate computation.

For each family × asset:

1. Draw **N = 120** unique valid configurations from the frozen search space with
   a fixed seed (2026), independently of anything the search selected.
2. Evaluate every one of them over the **whole development partition** with the
   frozen costs, next-bar execution and funding — one backtest per configuration.
3. Split the resulting per-bar net-return series into **8 contiguous
   chronological blocks** and record each configuration's Sharpe ratio in each
   block, giving an 8 × 120 matrix.
4. Feed that matrix to `probability_of_backtest_overfitting`.

This candidate set **selects nothing and promotes nothing**. It measures how
likely *the selection procedure itself* is to pick a configuration that lands at
or below the median out of sample. Because the candidate set is common across
blocks by construction, the CSCV assumption holds. The configurations, the seed,
the count and the block count are frozen here, before any S2 result exists.

### S2-C — Full study · **NOT AUTHORISED**

Requires a separate human authorisation. Would use all planned outer folds, 10
seeds per asset per family, Random Search confirmatory and the GA as a secondary
diagnostic, at 100 evaluations per fold per engine.

---

## 9. Pre-specified decision criteria (frozen)

### Partial-signal criterion (the S2-B trigger)

S2-C is prepared **only** if at least one family, on **Random Search**, on **at
least one asset**, satisfies *all* of:

| # | Condition |
|---|---|
| P1 | Positive compounded net out-of-sample return over the pilot folds, on a **majority of seeds** (≥ 2 of 3) |
| P2 | At least 5 out-of-sample trades in total (the S1 `min_oos_trades` veto), on every seed counted under P1 |
| P3 | The positive result is not confined to a single fold |

P1 is stated over a majority of seeds precisely so that a single lucky seed
cannot trigger S2-C. Preparing S2-C is **not** running it: executing S2-C, and
executing the `primary_only` versus `primary_plus_meta_labeling` comparison,
each require a separate human authorisation.

### Promotion criteria (would apply at S2-C, frozen now)

Reused unchanged from R3 and S1 so results stay comparable. A family is promoted
only if, on Random Search and on **both** assets, at least **6 of 10 seeds**
satisfy all six criteria:

| # | Criterion |
|---|---|
| C1 | Positive total net OOS return |
| C2 | Bootstrap Sharpe confidence interval excludes zero |
| C3 | Survives doubled fees and slippage |
| C4 | Beats buy-and-hold on the same OOS ledger |
| C5 | Survives dropping the top five trades |
| C6 | Result is not confined to a single fold |

**Separate veto:** at least five OOS trades per seed.

**Addition S2-a — selection-bias correction.** Deflated Sharpe ratio above 0.95
using the recorded count of unique valid evaluations as the trial count; PBO
below 0.5 over the family's per-fold performance matrix; Benjamini–Hochberg FDR
control at α = 0.05 across the three families.

**Addition S2-b — the intensity placebo** of section 7 must be beaten.

**Addition S2-c — the asymmetry is pre-declared.** Jeon reports that order flow
added value on ETHUSDT conditional on liquidity state while **BTCUSDT never
cleared its flow-shuffle null**. We therefore pre-declare the expectation that,
if anything works, it is more likely on ETH than on BTC. Recording this in
advance means an ETH-only result is a *predicted* asymmetry rather than a
post-hoc rationalisation — and, equally, that a BTC-only result would be
*surprising* and must be treated with more suspicion, not less.

**If S2 promotes nothing**, the result is recorded as a negative outcome. It may
not be rescued by relaxing a criterion, re-tuning a rejected family, or adding a
family after seeing results.

---

## 10. Invariants for this batch

1. The holdout `[2026-01-01, 2026-07-01)` is **not** read, loaded, summarised or
   used to inform any choice in this batch.
2. Search remains independent per outer fold (ADR 0012).
3. Purge and embargo unchanged from the R3 geometry.
4. R2-, R3- and S1-family parameters are not re-searched, re-parameterised or
   recombined.
5. Every flow input is lagged ≥ 1 bar; no configuration reachable by the search
   can violate this (`test_no_sampled_candidate_can_read_flow_contemporaneously`).
6. Criteria in section 9 are frozen; changing one requires a new batch number.
7. No new market data is downloaded and no exchange endpoint is contacted.
8. Every run records commit, resolved config, dataset manifests, seed schedule,
   budget accounting and the batch attempt counter.

---

## 11. Freeze record

The commit that adds this file also adds the implementation, the configuration
models, the registry entries, the S2-A test suite and the pilot configurations.
No S2-B run existed at the time it was made. The commit hash is the freeze
timestamp and is quoted in the S2-B outcome document.
