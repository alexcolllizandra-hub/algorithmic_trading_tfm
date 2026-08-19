# Data inventory, gaps and novelty audit (Gate S2)

**Date:** 2026-08-11 · **Partition:** development only · **Holdout:** not read

Every number below was measured from the repository, not quoted from
documentation. The measuring scripts filtered to `open_time < 2026-01-01` and
asserted the bound before computing anything, so no figure on this page is a
function of holdout data.

This is a **data-contract** audit — what exists, how much of it, at what
resolution, with what gaps. It contains no return, no Sharpe and no performance
statistic of any kind, because selecting an S2 family on development performance
is exactly what the pre-specification protocol forbids.

---

## 1. What we already have

### 1.1 Processed klines (partitioned, ready for the search engine)

| Symbol | Timeframe | Partition | Rows | Span |
|---|---|---|---:|---|
| BTCUSDT | 15m | development | 210 432 | 2020-01-01 → 2025-12-31 23:45 |
| BTCUSDT | 15m | holdout | 17 376 | 2026-01-01 → 2026-06-30 23:45 |
| BTCUSDT | 1h | development | 52 608 | 2020-01-01 → 2025-12-31 23:00 |
| BTCUSDT | 1h | holdout | 4 344 | 2026-01-01 → 2026-06-30 23:00 |
| ETHUSDT | 15m | development | 210 432 | 2020-01-01 → 2025-12-31 23:45 |
| ETHUSDT | 15m | holdout | 17 376 | 2026-01-01 → 2026-06-30 23:45 |
| ETHUSDT | 1h | development | 52 608 | 2020-01-01 → 2025-12-31 23:00 |
| ETHUSDT | 1h | holdout | 4 344 | 2026-01-01 → 2026-06-30 23:00 |

The holdout rows are listed for completeness of the contract. They have not been
opened.

### 1.2 Validated source streams

| Symbol | Stream | Rows | Span (full, incl. holdout) |
|---|---|---:|---|
| BTCUSDT | klines 5m | 683 424 | 2020-01-01 → 2026-06-30 23:55 |
| BTCUSDT | markPrice 5m | 680 818 | 2020-01-01 → 2026-06-30 23:55 |
| BTCUSDT | fundingRate | 7 119 | 2020-01-01 → 2026-06-30 16:00 |
| ETHUSDT | klines 5m | 683 424 | 2020-01-01 → 2026-06-30 23:55 |
| ETHUSDT | markPrice 5m | 682 545 | 2020-01-01 → 2026-06-30 23:55 |
| ETHUSDT | fundingRate | 7 119 | 2020-01-01 → 2026-06-30 16:00 |

### 1.3 Columns per kline bar — and which have ever driven a signal

This is the most consequential table in the document.

| Column | Available since 2020 | Used as a *feature* | Used as a *signal* by any R2/R3/S1 family |
|---|---|---|---|
| `open`, `high`, `low`, `close` | yes | yes | **yes** — all of R2/R3, and S1-01/03/04 |
| `volume` | yes | yes | no |
| `quote_volume` | yes | yes (denominator only) | **no** |
| `trade_count` | yes | **no** | **no** |
| `taker_buy_base` | yes | no | **no** |
| `taker_buy_quote` | yes | yes (`taker_buy_ratio`, `taker_buy_imbalance`) | **no** |
| mark price (separate stream) | yes | no | **no** |
| `funding_rate` | yes | yes | **yes** — R3 `funding`, S1-02 `funding_reversal` |

`taker_buy_imbalance` already exists in the feature engine
(`features/causal.py`, registered in `experiment.yaml` as *lagged order-flow
context*), but **no strategy has ever read it to decide a trade**. `trade_count`
is not even wired into the feature engine. Neither is the mark price.

The practical consequence: **order flow and the mark-price dislocation are
unexploited axes that require zero new data acquisition.** They are already
ingested, already validated, already partitioned and already covered by the
existing manifests and holdout guard.

### 1.4 Measured properties of the unused streams

Development partition only.

**Mark price versus last price**, expressed as
`(last − mark) / mark` in basis points:

| Symbol | Aligned bars | Coverage | mean | sd | p01 | p50 | p99 | min | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BTCUSDT | 628 978 | 99.633% | −0.114 | 3.359 | −7.50 | −0.01 | +9.09 | −384.0 | +228.6 |
| ETHUSDT | 630 705 | 99.906% | +0.168 | 4.155 | −7.65 | +0.00 | +12.82 | −1346.3 | +396.8 |

**Bar-level taker flow.** Imbalance is
`2 · taker_buy_quote / quote_volume − 1`, so +1 is an entirely buyer-initiated
bar and −1 an entirely seller-initiated one. Average trade size is
`quote_volume / trade_count`, in USDT.

| Symbol | TF | Bars | Zero-volume bars | mean | sd | p01 | p99 | min | max | lag-1 autocorr. | median trade size |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BTCUSDT | 1h | 52 608 | 1 | −0.0049 | 0.0879 | −0.219 | +0.211 | −0.490 | +0.443 | +0.020 | 3 808 |
| BTCUSDT | 15m | 210 432 | 16 | −0.0053 | 0.1532 | −0.368 | +0.358 | −0.712 | +0.781 | +0.031 | 3 684 |
| ETHUSDT | 1h | 52 608 | 1 | −0.0088 | 0.0855 | −0.214 | +0.204 | −0.674 | +0.538 | +0.011 | 2 006 |
| ETHUSDT | 15m | 210 432 | 10 | −0.0086 | 0.1501 | −0.366 | +0.351 | −0.884 | +0.864 | +0.026 | 1 931 |

Three implementation consequences, recorded before any family is written:

1. **Zero-volume bars exist** and make the imbalance undefined. The feature
   engine already guards this (`features/causal.py` returns null when
   `quote_volume <= 0`); any S2 family reading flow must inherit that guard
   rather than reinvent it.
2. **The imbalance is almost serially uncorrelated at bar level** — lag-1
   autocorrelation of 0.02–0.03. Whatever the tick-level order-flow literature
   reports about persistence, at 1-hour aggregation it is nearly absent here.
   A family assuming flow *persists* is contradicted by our own data before it
   is written; a family reacting to a flow *extreme* is not.
3. **Scale for parameter grids.** A "one standard deviation" flow event is
   ≈0.09 at 1h and ≈0.15 at 15m; the 99th percentile is ≈0.21 and ≈0.36. Search
   ranges should be quoted in these units rather than in round numbers.

**Funding rate**, verified against our own table rather than against
documentation:

| Symbol | Settlements | Hour-of-day histogram | Interval | mean (bp) | sd (bp) | p99 (bp) | min/max (bp) | share \|rate\| > 5bp |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| BTCUSDT | 6 576 | 00:00 → 2192, 08:00 → 2192, 16:00 → 2192 | 8h, all rows | +1.170 | 2.184 | +10.84 | −30.00 / +30.00 | 5.19% |
| ETHUSDT | 6 576 | 00:00 → 2192, 08:00 → 2192, 16:00 → 2192 | 8h, all rows | +1.399 | 2.849 | +14.32 | −35.63 / +37.50 | 6.98% |

Two facts worth stating plainly:

1. **The settlement clock is exactly 00:00 / 08:00 / 16:00 UTC**, uniformly, for
   the whole development period, on both symbols, with `funding_interval_hours`
   equal to 8 on every row. A secondary source asserted this; we did not take its
   word for it. It is now verified from the ingested data.
2. **Longs pay on average.** +1.17 bp per 8-hour settlement on BTC is ≈ 3.5 bp
   per day, on the order of 12–13% per year transferred from longs to shorts.
   This is a large, persistent, directional cash flow and it is the strongest
   documented economic asymmetry in the instrument.

---

## 2. The cost constraint, and what it rules out

`configs/experiment.yaml` sets provisional taker fees of 4.0 bp per side plus
1.0 bp per side of slippage (ADR 0005). **A round trip therefore costs ≈ 10 bp**,
before any adverse selection.

Placing that next to section 1.4 kills one otherwise attractive idea:

> The mark-price dislocation has a standard deviation of 3.4 bp (BTC) and a 99th
> percentile of 9.1 bp. **A round trip costs more than the 99th percentile of the
> signal.** A mean-reversion strategy on the premium cannot pay for itself except
> in a tail thinner than 1% of bars, and that tail is dominated by exchange
> stress episodes in which the 10 bp assumption is itself optimistic.

This is recorded as a **negative data finding**, not as a hypothesis to be tested
at budget. It is the kind of result that should stop a family before it is
implemented rather than after 100 evaluations per fold.

---

## 3. What we do not have

| Data | Why it matters | Status | Blocking reason |
|---|---|---|---|
| Order book / depth snapshots | true order-flow imbalance, Kyle's lambda, queue dynamics | **not held** | not in the bulk archive; would need a paid vendor or forward collection, which cannot recreate 2020 |
| Tick / aggTrade data | exact trade signing, VPIN, trade-size distribution | **not held** | available in the archive but is terabyte-scale; bar-level `taker_buy_*` is the intended aggregate |
| Open interest history | positioning, crowding, deleveraging | **not held** | excluded by the data contract: Binance's REST endpoint serves only ~30 days and the bulk archive has no OI series. Cannot be reconstructed backwards **at any price** |
| Liquidation feed | forced-deleveraging cascades | **not held** | no complete historical archive; the public stream is sampled |
| Spot klines | true spot-perpetual basis | **not held** | *would be* cheap to add from the same archive; the mark price is an index-anchored proxy we already hold |
| On-chain metrics | flows, holder behaviour | **not held** | **point-in-time integrity failure** — vendors retroactively recompute history when clustering improves; vintages start ~2024/2025, our sample starts 2020 |
| Google Trends / social sentiment | attention | **not held** | **not reproducible** — sampled, rescaled, revision-prone, no vintage archive; two downloads a week apart differ |
| Macro intraday (DXY, VIX) | risk-on/off | **not held** | ALFRED gives genuine point-in-time vintages but only at daily-or-coarser frequency, and the series are undefined on the weekends crypto trades through |
| Options / implied volatility | risk-neutral expectations | **not held** | Deribit data not ingested; out of contract scope |

See [`literature_review_exogenous_data.md`](literature_review_exogenous_data.md)
for the sourced argument behind the on-chain, sentiment and macro exclusions.

**Recommended acquisition priority.** The only cheap, point-in-time-clean
addition is **spot klines from the same Binance archive**, which would turn the
mark-price proxy into a true spot-perpetual basis. It is deliberately *not*
proposed for this batch: section 2 shows the dislocation is smaller than costs,
so buying a better measurement of it would not change the conclusion. Everything
else on the list either cannot be bought (open interest, on-chain vintages) or
cannot be made reproducible (Trends, social).

---

## 4. Novelty audit

Every previously evaluated family, with the input it actually reads, so a
proposed S2 family can be checked against all of them at once.

| Gate | Family | Mechanism class | Signal input | Outcome |
|---|---|---|---|---|
| R2 | `momentum` | trend | close only | REJECTED (ADR 0013) |
| R3 | `breakout` | trend / range | high, low, close | REJECTED (ADR 0015) |
| R3 | `mean_reversion` | reversion | close | REJECTED (ADR 0015) |
| R3 | `volatility_breakout` | trend / volatility | high, low, close, ATR | REJECTED (ADR 0015) |
| R3 | `funding` | carry | funding rate | REJECTED (ADR 0015) |
| R3 | `BTC_ETH_confirmation` | cross-asset lead-lag | close of two symbols | REJECTED (ADR 0015) |
| S1 | `mtf_trend_consensus` | trend, multi-horizon | close at several horizons | PILOTED, stopped (ADR 0017) |
| S1 | `funding_reversal` | carry unwind | funding rate | PILOTED, stopped (ADR 0017) |
| S1 | `xasset_spread_reversion` | relative value | close of two symbols | PILOTED, stopped (ADR 0017) |
| S1 | `intraday_seasonality` | calendar | bar timestamp | PILOTED, stopped (ADR 0017) |

**Nine of the ten read only price.** The tenth reads funding. **None reads
volume, taker flow, trade counts or the mark price.**

### 4.1 Rules a proposed S2 family must survive

Stated before any S2 family was chosen, so they can be applied without
discretion:

1. **A new input, or a new mechanism.** Re-parameterising an existing family is
   not a new family. Explicitly barred, per instruction: renaming momentum;
   adding an indicator to breakout or mean reversion; changing funding
   parameters; restating `funding_reversal`; substituting a plain
   Ornstein-Uhlenbeck for `xasset_spread_reversion`; combining rejected
   strategies and calling the result an ensemble.
2. **The mechanism must be economic**, stated before implementation, and must
   explain *who* is on the other side and *why* they accept the loss.
3. **The signal must be causal** — computable from bars strictly before the
   decision bar, and executed on the next bar's open.
4. **The signal must be plausibly larger than 10 bp round trip**, or the family
   must trade rarely enough that its per-trade edge can clear that hurdle.
   Section 2 is the precedent for rejecting a family on this ground alone.
5. **Point-in-time data only.** A family requiring a restated or
   irreproducible series is not implementable, regardless of its literature.

### 4.2 Ideas rejected before pre-specification

Recorded so the batch's selection is auditable, and so these are not quietly
revived later.

| Idea | Why rejected |
|---|---|
| Mark-vs-last premium reversion | signal p99 (9.1 bp BTC) below the 10 bp round trip — section 2 |
| Spot-perpetual basis carry | needs spot klines, and would face the same cost wall |
| On-chain flow signals | point-in-time vintages do not exist for 2020–2024 |
| Google Trends / social attention | not reproducible; published intraday effect (R² ≈ 0.027%) is orders of magnitude below costs |
| Open-interest crowding | data cannot be reconstructed backwards at any price |
| Liquidation-cascade following | no complete historical liquidation archive |
| Macro-announcement drift | ≈120 events over six years is too small for 5-minute inference, and macro series are undefined on weekends |
| Time-of-day / day-of-week effects | **already evaluated** as S1-04 `intraday_seasonality`; re-proposing it would violate rule 1 |
| Regime-switching overlay (HMM) | a filter on existing families, not a family; and every family it would filter is rejected or stopped |
| Ensemble of R3/S1 families | explicitly barred; no new mechanism |
