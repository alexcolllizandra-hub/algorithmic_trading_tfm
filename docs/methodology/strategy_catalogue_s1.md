# Strategy catalogue — Gate S1

**Version:** 1.0 · **Frozen:** 2026-08-11 · **Status:** pre-specified, not yet run

This catalogue is the scientific contract for the Gate S1 batch. It was written
**before** any S1 result was produced. Every entry states its economic
hypothesis, its exact rules, its parameter space, its falsification criterion and
the tests that must pass before the family is allowed into a study.

Related: [gate_s1_batch_01.md](../roadmap/gate_s1_batch_01.md) ·
[experimental_design.md](experimental_design.md) ·
[phase_gates.md](../roadmap/phase_gates.md) · ADR 0016.

---

## Relationship to the families closed at Gate R3

Gate R3 closed `CLOSED_NEGATIVE` with **0/5** promotions (ADR 0015). Those
families — `breakout`, `mean_reversion`, `volatility_breakout`, `funding`,
`BTC_ETH_confirmation` — and the `momentum` baseline rejected at R2 (ADR 0013)
are **not re-searched and not re-parameterised**. They remain in the registry
only so historical runs stay reproducible.

Two S1 families operate on inputs a rejected family also used. The protocol
requires stating what makes each a *new* hypothesis rather than a rename:

| S1 family | Shares an input with | Material difference |
|---|---|---|
| `funding_reversal` | `funding` (rejected) | `funding` holds a **continuous carry stance** driven by a z-score, exiting on a band. `funding_reversal` is an **event** strategy: a trailing-percentile extreme opens a position for a **fixed number of bars** and the clock closes it. Different claim (transient unwind vs persistent carry), different trade population (bounded, episodic), different exit mechanism. |
| `xasset_spread_reversion` | `BTC_ETH_confirmation` (rejected) | `BTC_ETH_confirmation` uses the peer leg as a **directional confirmation filter** and trades the target *with* its own move. `xasset_spread_reversion` trades the **relative dislocation** between the legs, entering *against* the leg that ran ahead. Opposite economic direction, different traded object; co-movement is a precondition here, not a signal. |

`mtf_trend_consensus` and `intraday_seasonality` have no R3 counterpart.

---

## Tiering

| Tier | Meaning | S1 families |
|---|---|---|
| `core` | Mechanism documented in the peer-reviewed literature and directly transferable to perpetual futures | `mtf_trend_consensus`, `funding_reversal` |
| `extended` | Mechanism documented, but the transfer to this market/frequency involves an additional assumption | `xasset_spread_reversion` |
| `experimental` | Plausible mechanism, weaker external evidence at this frequency | `intraday_seasonality` |

Tier does not change the promotion criteria. It records how much prior evidence
the hypothesis carries, which matters when interpreting a negative result.

---

## S1-01 · `mtf_trend_consensus` (core)

| Field | Value |
|---|---|
| **Identifier** | `mtf_trend_consensus` |
| **Implementation** | `src/perp_lab/strategies/mtf_trend_consensus.py` |
| **Economic hypothesis** | Directional drift worth trading net of costs is visible at **several separated horizons simultaneously**. Single-horizon signals fire on local sign changes and spend turnover on noise; requiring agreement across time scales is a filter on coherence, not on magnitude. |
| **Data required** | 1h OHLCV (primary asset only) |
| **Features** | `momentum_{h}` for each horizon in the set; `roll_std_{w}` for the volatility scale |
| **Signal rules** | For each horizon *h*, normalise `momentum_h` by `roll_std_w · sqrt(h)`. Count horizons whose normalised value is `>= min_strength` (up) or `<= -min_strength` (down). **Long** when `n_up >= min_agreement`; **short** when `n_down >= min_agreement`. |
| **Exit** | Flat when both counts fall below `exit_agreement`; an opposite entry reverses directly. |
| **Direction** | `long`, `short`, `both` |
| **Parameter space** | `horizon_sets` ∈ {(12,48,168), (6,24,96), (24,96,336), (6,24,96,336)}; `min_agreement` ∈ {2,3}; `exit_agreement` ∈ {1,2}; `min_strength` ∈ {0.0, 0.25, 0.5}; `strength_window` ∈ {48,168}; regime gate optional |
| **Costs** | Standard: fees + slippage per side, funding charged by the backtester (ADR 0005) |
| **Benchmark** | Buy-and-hold on the same OOS ledger; and the R2 `momentum` result as the prior null |
| **Frequency** | 1h bars, next-bar open execution |
| **Risks** | Multi-horizon agreement is autocorrelated across horizons, so the effective number of independent votes is below the nominal one; the volatility normaliser can collapse in very quiet windows |
| **Expected result** | Fewer trades and lower turnover than R2 momentum; net OOS Sharpe indistinguishable from zero is the null |
| **Falsification** | If drift is a scale-free artefact of return autocorrelation, agreement adds no information and net OOS performance is statistically indistinguishable from the rejected single-horizon momentum family after costs |
| **Causal tests** | Truncation invariance; warm-up flatness with a null horizon; disagreement produces flat |
| **Promotion criteria** | Gate S1 criteria C1–C6 plus the trade-count veto (see `gate_s1_batch_01.md`) |

## S1-02 · `funding_reversal` (core)

| Field | Value |
|---|---|
| **Identifier** | `funding_reversal` |
| **Implementation** | `src/perp_lab/strategies/funding_reversal.py` |
| **Economic hypothesis** | An extreme funding rate is a **positioning** observation: one side of the book is crowded enough to pay to stay there. Crowding resolves through de-leveraging within a bounded horizon, producing short-lived drift **against** the paying side. |
| **Data required** | 1h OHLCV + funding rate history |
| **Features** | `funding_rate` (backward as-of join on the publication timestamp) |
| **Signal rules** | Compute trailing rolling quantiles of the rate over `rank_window` bars. **Short** when `rate >= quantile(extreme_pct)`; **long** when `rate <= quantile(1 - extreme_pct)`. A `min_abs_rate` floor suppresses triggers in numerically flat regimes. |
| **Exit** | After exactly `holding_bars` bars. The clock closes the position, never the signal. |
| **Direction** | `long`, `short`, `both` |
| **Parameter space** | `rank_window` ∈ {168, 336, 720}; `extreme_pct` ∈ {0.90, 0.95, 0.99}; `holding_bars` ∈ {4, 8, 24, 48}; `min_abs_rate` ∈ {0.0, 5e-5}; regime gate optional. Constraint: `holding_bars < rank_window` |
| **Costs** | Standard. Note the family **shorts into positive funding**, so it earns carry through the backtester's funding column; the strategy never adds a cashflow itself |
| **Benchmark** | Buy-and-hold; and a same-trigger strategy holding the *opposite* side, to separate the reversal claim from the carry claim |
| **Frequency** | 1h bars, next-bar open execution |
| **Risks** | Funding extremes cluster, so episodes chain and the realised holding period can exceed `holding_bars`; the reversal and the carry point the same way for the upper tail, so a positive result is not automatically evidence of reversal |
| **Expected result** | Few, well-separated trades; any edge concentrated in the highest `extreme_pct` setting |
| **Falsification** | If extreme funding reflects information rather than crowding, the post-event drift continues **with** the paying side and the family produces negative net OOS returns symmetric to the carry |
| **Causal tests** | Truncation invariance; no exposure without a triggering extreme within `holding_bars`; upper-tail extreme produces a short held for exactly `holding_bars` |
| **Promotion criteria** | Gate S1 criteria C1–C6 plus the trade-count veto |

## S1-03 · `xasset_spread_reversion` (extended)

| Field | Value |
|---|---|
| **Identifier** | `xasset_spread_reversion` |
| **Implementation** | `src/perp_lab/strategies/xasset_spread_reversion.py` |
| **Economic hypothesis** | BTC and ETH perpetuals share a dominant common factor. When one leg runs ahead of the other over a short window without a change in that factor, the dislocation is a **relative mispricing** and reverts. |
| **Data required** | 1h OHLCV for both legs on the same grid |
| **Features** | `xasset_rel_momentum_{w}`; `xasset_corr_{w}` for the co-movement precondition |
| **Signal rules** | **Short** the target when `rel_momentum >= entry_spread`; **long** when `rel_momentum <= -entry_spread`. Trades are suppressed when `xasset_corr < min_corr`: below the floor the legs are not coupled and there is no spread to revert. |
| **Exit** | Flat when `abs(rel_momentum) <= exit_spread`; an opposite extreme reverses. |
| **Direction** | `long`, `short`, `both` |
| **Parameter space** | `lookback` ∈ {6,12,24,48}; `entry_spread` ∈ {0.005, 0.01, 0.02}; `exit_spread` ∈ {0.0, 0.002, 0.005}; optional `min_corr` ∈ {0.3,0.5,0.7} with `corr_window` ∈ {48,168}; regime gate optional |
| **Costs** | Standard. **Only the target leg is traded**; this is a single-leg expression of a relative view, so it carries directional market risk that a two-leg spread would not |
| **Benchmark** | Buy-and-hold on the target leg; and the same rule with the sign flipped, to distinguish reversion from relative momentum |
| **Frequency** | 1h bars, next-bar open execution |
| **Risks** | The single-leg expression leaves unhedged beta; a genuine repricing of one asset looks identical to a dislocation until it is too late; the correlation floor is itself an estimated quantity |
| **Expected result** | Modest hit rate with small average wins; sensitivity to `entry_spread` is the main diagnostic |
| **Falsification** | If the relative move is information rather than dislocation, the spread continues and the family loses; a positive result under the sign-flipped benchmark would indicate relative **momentum**, falsifying the reversion claim specifically |
| **Causal tests** | Truncation invariance; correlation floor suppresses trades; the family refuses to run without the reference leg instead of degrading to single-asset |
| **Promotion criteria** | Gate S1 criteria C1–C6 plus the trade-count veto |

## S1-04 · `intraday_seasonality` (experimental)

| Field | Value |
|---|---|
| **Identifier** | `intraday_seasonality` |
| **Implementation** | `src/perp_lab/strategies/intraday_seasonality.py` |
| **Economic hypothesis** | The market trades continuously but its participants do not. Session opens, the daily settlement cycle and the 8-hour funding timestamps concentrate hedging and rebalancing into recurring windows of the UTC day, leaving a small repeatable drift. |
| **Data required** | 1h OHLCV; timestamps only for the entry rule |
| **Features** | None for the base rule; `sma_{w}` when the optional trend gate is enabled |
| **Signal rules** | Open a position of side `side_mode` on every bar whose UTC hour equals `entry_hour`. There is **no price predictor** in the entry. |
| **Exit** | After exactly `holding_bars` bars. |
| **Direction** | Fixed by `side_mode`; the shared `direction` parameter is not exposed, because it could only produce empty combinations |
| **Parameter space** | `entry_hour` ∈ {0..23}; `holding_bars` ∈ {1,2,4,8}; `side_mode` ∈ {long, short}; optional `trend_filter_ma` ∈ {168, 336}; regime gate optional |
| **Costs** | Standard. This family is the most cost-sensitive of the batch: it trades on a fixed schedule regardless of expected move size |
| **Benchmark** | Buy-and-hold; and the average across **all** 24 entry hours, which is the correct null for "one hour is special" |
| **Frequency** | 1h bars, next-bar open execution |
| **Risks** | 24 hours × 2 sides × 4 holding periods is a large number of near-identical hypotheses, so this family carries the batch's heaviest selection burden; a winning hour found on validation data is the textbook data-snooping failure |
| **Expected result** | Most hours indistinguishable from zero; the null is that the best hour is the best of 192 draws from a null distribution |
| **Falsification** | If the effect is real, the selected hour is stable **across outer folds**; an hour that changes fold to fold falsifies the seasonality claim regardless of aggregate performance |
| **Causal tests** | Truncation invariance; entries occur only at the configured hour and with the configured side; an empty `direction`/`side_mode` combination is rejected at construction |
| **Promotion criteria** | Gate S1 criteria C1–C6, the trade-count veto, **and** the fold-stability requirement above. This family additionally requires the deflated Sharpe ratio computed against the full 192-configuration trial count |

---

## Literature grounding

These references motivate the mechanisms above. **Verification status is stated
explicitly**: entries marked *bibliographic* are established published work cited
from the literature; they were **not** retrieved online during this session, and
the exact pages/DOIs must be confirmed before any of them is quoted in a
manuscript. Entries marked *primary, unverified* must be fetched and hashed by
the source collector before being used as a factual claim.

| # | Source | Used for | Verification status |
|---|---|---|---|
| 1 | Moskowitz, Ooi & Pedersen (2012), "Time series momentum", *Journal of Financial Economics* 104(2) | Multi-horizon trend persistence | bibliographic |
| 2 | Hurst, Ooi & Pedersen (2017), "A Century of Evidence on Trend-Following Investing", *Journal of Portfolio Management* | Horizon diversification in trend systems | bibliographic |
| 3 | Gatev, Goetzmann & Rouwenhorst (2006), "Pairs Trading: Performance of a Relative-Value Arbitrage Rule", *Review of Financial Studies* 19(3) | Relative-value reversion | bibliographic |
| 4 | Makarov & Schoar (2020), "Trading and arbitrage in cryptocurrency markets", *Journal of Financial Economics* 135(2) | Segmentation and dislocations in crypto | bibliographic |
| 5 | Heston, Korajczyk & Sadka (2010), "Intraday Patterns in the Cross-section of Stock Returns", *Journal of Finance* 65(4) | Recurring intraday effects | bibliographic |
| 6 | López de Prado (2018), *Advances in Financial Machine Learning*, Wiley | Purging, embargo, meta-labeling, triple barrier | bibliographic |
| 7 | Bailey & López de Prado (2014), "The Deflated Sharpe Ratio", *Journal of Portfolio Management* 40(5) | Selection-bias correction | bibliographic; implemented in `evaluation/multiple_testing.py` |
| 8 | Bailey, Borwein, López de Prado & Zhu (2017), "The Probability of Backtest Overfitting", *Journal of Computational Finance* 20(4) | CSCV overfitting estimate | bibliographic; implemented |
| 9 | White (2000), "A Reality Check for Data Snooping", *Econometrica* 68(5) | Multiple-comparison control | bibliographic; **not yet implemented** |
| 10 | Hansen (2005), "A Test for Superior Predictive Ability", *JBES* 23(4) | Multiple-comparison control | bibliographic; **not yet implemented** |
| 11 | Harvey, Liu & Zhu (2016), "…and the Cross-Section of Expected Returns", *Review of Financial Studies* 29(1) | Significance thresholds under many tests | bibliographic |
| 12 | Benjamini & Hochberg (1995), *JRSS B* 57(1) | False-discovery-rate control | bibliographic; implemented |
| 13 | Binance USDⓈ-M Futures documentation — funding rate mechanism and settlement schedule | Funding semantics and 8-hour cadence | **primary, unverified** — must be fetched, dated and hashed by the funded-source collector before being cited as fact |

No blog or vendor-marketing source is used anywhere in this catalogue.
