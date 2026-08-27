# Gate S2 — evidence base and selection rationale

**Compiled:** 2026-08-11 · Feeds [../roadmap/gate_s2_batch_01.md](../roadmap/gate_s2_batch_01.md)

This is the index and the verdict layer over three domain reviews. The full
per-paper evidence matrices — DOI, peer-review status, venue and instrument,
sample and frequency, variables, target, model, temporal validation, costs,
reported performance, benchmark, number of variants, multiple-testing treatment,
code and data availability, weaknesses, compatibility with our instrument,
reproducibility grade and the replicable economic hypothesis — live in:

| Review | File | Papers |
|---|---|---|
| Order flow, signed volume, liquidity, trade size | [literature/orderflow_and_liquidity.md](literature/orderflow_and_liquidity.md) | 15 |
| Funding, basis, dislocation, liquidations, volatility, regimes | [literature/funding_basis_and_volatility.md](literature/funding_basis_and_volatility.md) | 19 |
| On-chain, attention/sentiment, macro, event studies | [literature/exogenous_data.md](literature/exogenous_data.md) | — |

Method: web search plus direct retrieval of primary sources. Each review
separates **what the paper reports**, **how strong the statistical evidence is**,
**whether we could replicate it**, **whether it is compatible with our frozen
contract**, and **what new hypothesis it licenses**. Unverified claims are
labelled as such in the source files rather than silently promoted to fact.

---

## 1. What the evidence actually supports

### It does not support a fast microstructure strategy

The one paper testing close to our exact setup — Binance perpetuals, order-flow
features, correct purging, explicit VIP-0 costs — reports **gross Sharpe 0.96 and
net Sharpe −10.68 to −18.42**, destroyed by 124–204× daily notional turnover at a
five-minute rebalance. This is the most useful result in the entire review
because it is a well-executed negative that identifies the *mechanism* of
failure: horizon, not feature.

The only papers reporting attractive Sharpe ratios at very short horizons make
costs optional, model no latency, and report information ratios that rise as
liquidity falls (0.07 on LTC, 8.97 on ETC) — a pattern we read as an artifact of
untradeable size rather than a finding.

### It weakly supports a multi-hour flow horizon

Kim & Hansen find quarter-hour opening order imbalance on Binance USDT-M
perpetuals predicts returns positively at **4–12 hour horizons**, significant at
95% for four of six contracts at every horizon in that band, with a placebo test
on shifted grids ruling out a generic even-spacing artifact. Three caveats are
carried into the pre-specification rather than discarded: the 4–12 h result is
**in-sample**; their imbalance is measured over the first **10 seconds** of the
boundary, which 1 h bars cannot resolve; and at multi-hour holding, **funding
becomes a first-order cost** that no paper in the review models. Our pilot
configs therefore set `require_funding: true`.

### The direction of the flow effect is genuinely unsettled

Kim & Hansen find a positive relation; Chordia, Roll & Subrahmanyam find a
**negative** coefficient on *lagged* order imbalance in equities. We therefore
search the response sign instead of assuming it, and charge both arms to the
hypothesis ledger.

### Flow is conditional on liquidity state, and asymmetric across our two assets

Jeon reports that on Binance BTCUSDT and ETHUSDT (2023–2026) the pre-event
liquidity state was the first-order predictor and order flow added value only as
an overlay conditional on state, rising monotonically from calm to stressed for
ETH — while **BTC never cleared its flow-shuffle null at either horizon**. This
is pre-declared in the batch as expectation S2-c, so an ETH-only result is a
predicted asymmetry rather than a post-hoc story, and a BTC-only result would be
*surprising* and treated with more suspicion, not less.

### Trade intensity is a control, not a signal

Andersen & Bondarenko showed VPIN's apparent predictive content was "due
primarily to a mechanical relation with the underlying trading intensity". We
hold `trade_count` directly, so the same objection applies to us. This became the
mandatory intensity-placebo falsification in the batch (section 7). Separately,
Pinto's mixture-of-distributions result on our exact instrument links trade count
and average trade size to **volatility**, not direction — which is why no
directional family here is built on `trade_count`.

### Funding is a positioning gauge, not a return forecast

Three independent sources converge: Christin et al. and He et al. establish that
positive funding is levered-long demand; Schmeling et al. link high carry to
subsequent crash risk; a practitioner note establishes that single-asset
directional predictability from funding is approximately zero. R3
(`funding`) and S1 (`funding_reversal`) already tested the directional reading
and neither promoted. S2 does not retest it.

---

## 2. Papers reporting a positive Sharpe — critical evaluation

| Claim | Reported | Why we do not inherit it |
|---|---|---|
| Perp-vs-spot deviation arbitrage, BTC | Sharpe 1.80 after realistic maker fees | It is a **hedged** arbitrage requiring simultaneous spot execution. We cannot short or hold spot, so our version would be a directional bet on convergence carrying full perp volatility. The Sharpe does not transfer. Edge also decays ≈11%/yr and fell to 0.70 in 2022 |
| Crypto carry / cash-and-carry | Positive across studies | Same objection: requires spot execution. Also cross-sectional, and two assets is not a cross-section |
| Microstructure ML on Binance perps | Gross Sharpe 0.96 | **Net Sharpe −10.68 to −18.42** on futures once VIP-0 costs are applied. The paper's own headline result is negative |
| Explainable crypto microstructure patterns | Information ratios 0.25 (BTC) to 8.97 (ETC) | Costs optional, no latency model, IR inversely related to liquidity. Read as an artifact |
| Volatility targeting | Sharpe improvement | Attributed by the authors to the **leverage effect**; Bitcoin exhibits an *inverted* leverage effect in both volatility regimes. A separate study finds volatility management helps in only ≈half of 103 cases |

**No paper in this review provides a positive, cost-aware, out-of-sample,
peer-reviewed result on a directional intraday strategy for BTC/ETH USDT-M
perpetuals that we could implement with our data.** That is the honest state of
the literature, and it is the correct prior going into S2-B.

---

## 3. What the evidence rules out for this project

| Domain | Verdict | Reason |
|---|---|---|
| Cont–Kukanov–Stoikov OFI, multi-level OFI | **Impossible** | Defined over limit-order arrivals and cancellations; no L2 data. Quote-to-trade ratio ≈40:1, so we are missing most events |
| Genuine volume-bucketed VPIN | **Impossible as specified** | A bar-level analogue is a different estimator and must be labelled as such |
| Trade-size distribution, retail decomposition | **Impossible** | Requires tick data; we hold only the first moment |
| Liquidations, forced-fill volume, cascade intensity | **Impossible** | No liquidation feed; Binance publishes no historical archive |
| Cash-and-carry, basis arbitrage | **Impossible** | Requires spot execution |
| Cross-sectional funding stat-arb | **Impossible** | Two assets is not a cross-section |
| Cross-venue price discovery | **Impossible** | Single venue, no DEX data |
| Reconstructing the premium index | **Impossible** | Needs impact bid/ask against the order book |
| On-chain variables | **Out of scope** | Point-in-time integrity cannot be established for restated chain analytics |
| Attention / sentiment / news | **Out of scope** | Reproducibility and point-in-time integrity failures |
| Perp-vs-index premium reversion | **Blocked on data, not on merit** | Needs `indexPriceKlines` / `premiumIndexKlines`, which are not ingested and cannot be downloaded in this phase. **Highest-value acquisition for a future batch** |
| Open interest | **Blocked on data** | The `metrics` archive would supply it from 2020-09 but is not ingested |
| Mark-minus-last dislocation | **Discarded on measurement and cost** | See below |

### The mark-minus-last measurement, resolved

No peer-reviewed or working paper studies the mark-price-minus-last-price gap as
a predictive signal on any venue. The reviews predicted it would be *censored at
zero* because `mark = median(price1, price2, contract price)` returns the last
price exactly whenever the traded price lies inside the index-anchored band.

Measured on development data (`scripts/s2_data_properties.py`): **12.5 % (BTC) /
11.6 % (ETH) of 5-minute bars have an exactly zero gap**, and 28.3 % / 23.6 % lie
within 0.1 bp. Only **1.17 % / 2.27 %** of bars show a gap exceeding the 10 bp
round trip — and the recoverable fraction of a gap is smaller than the gap. The
prediction is confirmed and the idea is discarded on a stated mechanism, not on a
vague appeal to cost.

---

## 4. From evidence to the S2 batch

| Evidence | Family it licensed |
|---|---|
| Aggressor side is exact in our data; the whole Lee-Ready/BVC literature exists to estimate it. Kim & Hansen (4–12 h, positive) vs. Chordia (lagged, negative). Pindza (horizon is what kills it) | **S2-01 `taker_flow_extreme`** — flow magnitude extreme, multi-hour clock exit, response sign searched |
| Brauneis et al. validate Amihud for liquidity *levels* in crypto against order-book ground truth. Immediacy premium is the mechanism | **S2-02 `illiquidity_reversion`** — fade a move whose impact per unit traded value is extreme; signal exit |
| Windowed flow and windowed return correlate at ≈+0.5 (measured), so sign disagreement is a rare, informative absorption event | **S2-03 `flow_price_divergence`** — sign disagreement, response sign searched |
| Andersen & Bondarenko's VPIN refutation | The **intensity placebo** falsification requirement (batch section 7) |
| Jeon's ETH-vs-BTC asymmetry | Pre-declared expectation S2-c |
| Corsi HAR-RV, Harvey volatility targeting, Ardia inverted leverage in BTC | **Not a family.** A sizing overlay with a pre-declared expectation of drawdown reduction and *no* Sharpe improvement. Deferred: there is no promoted primary strategy to overlay |

Two further candidates were designed and discarded before any result was
computed (funding-settlement flow, for material-equivalence risk with S1-02 and
S1-04; and mark-vs-last dislocation, above). Batch section 6 records them.
