# Literature Review: Order Flow, Signed Volume, Liquidity and Trade-Size Predictors for Binance USDT-M Perpetuals

## 0. Scope, method and integrity notes

**What I did.** Web search plus direct retrieval of primary sources (arXiv full text, publisher pages, author-hosted PDFs, SSRN abstract pages). Every DOI/URL below was returned by, or resolved through, an actual retrieval in this session. Fields I could not confirm from a retrieved primary or publisher page are marked **"not verified"**.

**Three verification failures I want to state up front:**

1. **Binance official kline field documentation could not be retrieved.** `developers.binance.com` returned a JavaScript/anti-bot wall, and the `binance-public-data` README fetched empty. So the exact semantics of `trade_count` in USDT-M futures klines — specifically whether it counts *raw trades* or *aggregated trades* (`aggTrades`, which merge same-price same-side fills against one taker order) — is **not verified here**. This matters a lot for Domain 4: `avg_trade_size = volume / trade_count` means something quite different under the two definitions. Treat this as a data-contract item to resolve before building any trade-size feature.
2. Several Elsevier DOIs are constructible from the PII but I did not resolve them independently; these are flagged inline.
3. I did **not** review the funding-rate / perpetual-basis predictability literature. It was outside the four domains you specified, so the verdict below says nothing about funding as a signal.

**One factual point that shapes everything below.** Binance klines expose `taker_buy_base` / `taker_buy_quote`. This is *exchange-reported aggressor-side volume*, derived from the `isBuyerMaker` flag on each fill. Kim and Hansen (row K) confirm this flag's semantics directly: `isBuyerMaker = False` means the buyer was the taker. Therefore:

$$\text{TI}_t \;=\; \frac{2\cdot\text{taker\_buy\_base}_t - \text{volume}_t}{\text{volume}_t}$$

is **exactly aggregated ground-truth signed volume**, not an estimate. We do *not* inherit the Lee-Ready / tick-rule / BVC misclassification error that the entire equity literature in Domain 2 spends its effort on. That is a real advantage. What we lose is (a) intra-bar sequencing, (b) the per-trade size distribution, (c) all limit-order placement and cancellation flow. That last loss is the fatal one for Domain 1's canonical measure, as row A makes clear.

---

## 1. Evidence matrix

---

### A. `cont-2014-ofi` — the canonical OFI paper

| Field | Value |
|---|---|
| **Citation** | Cont, R., Kukanov, A., Stoikov, S. (2014). "The Price Impact of Order Book Events." *Journal of Financial Econometrics* 12(1), 47–88. |
| **DOI / URL** | `10.1093/jjfinec/nbt003`; preprint `arXiv:1011.6402`; SSRN 1712822 (`10.2139/ssrn.1712822`) |
| **Peer review** | Yes, peer-reviewed journal |
| **Asset / venue** | 50 U.S. equities, randomly drawn from S&P 500 constituents; NYSE TAQ Level-1 consolidated quotes + trades |
| **Sample / frequency** | One calendar month, **April 2010**; 10-second grid; 273 half-hour subsamples per stock, ~180 observations each |
| **Variables** | OFI = net change in bid/ask queue sizes at the best quotes, aggregating limit-order arrivals, cancellations and market orders; trade imbalance (TI); average book depth |
| **Target** | **Contemporaneous** 10-second mid-price change. Not a forecast. |
| **Model** | OLS per stock per half-hour: ΔP = α + β·OFI + ε; robustness with a quadratic term and with depth-scaling |
| **Temporal validation** | **None.** Pure in-sample contemporaneous regression. Stability is shown across stocks and timescales, not across time out-of-sample. |
| **Costs modelled** | No — there is no trading strategy |
| **Reported numbers** | Average R² = **65%** for OFI. Adding a quadratic term raises it to 68% and the quadratic coefficient is insignificant in most samples. **Trade imbalance alone gives average R² = 32%.** When OFI and TI enter jointly, TI's average t-statistic falls by a factor of four and TI is significant in only 31% of subsamples. |
| **Benchmark** | Trade imbalance and the square-root volume law |
| **Variants tested** | Timescales from ~10 quote updates to 10 minutes; linear vs quadratic; OFI vs TI vs both; depth regressions. Order of ~10 specifications, all reported. |
| **Multiple-testing correction** | No — but the paper is descriptive, not a signal search, so this is not really a defect |
| **Code / data** | No code released. TAQ is licensed (WRDS). |
| **Leaks / weaknesses** | (i) **Contemporaneous, not predictive** — a 65% R² on same-interval price change is a price-formation identity, not alpha, and it is routinely misread as a forecasting result. (ii) Single month, single market, pre-2010 microstructure. (iii) No cost or execution analysis. (iv) The quote-to-trade ratio is ~40:1, so most of the explanatory power comes from events we cannot observe. |
| **Compatibility with our data** | **Low for the headline measure.** True OFI requires quote updates and cancellations. **We can only compute the TI leg.** |
| **Reproducibility grade for us** | **Low** for OFI; **High** for the TI comparison |
| **Replicable hypothesis** | Bar-level signed taker volume explains contemporaneous price change, but only about half as much as full order-book flow does — so a taker-volume-only signal starts with roughly half the information content of the literature's benchmark. |

**Why this row matters most for us:** the 65% vs 32% contrast is the single most useful verified number in this review. It quantifies, from the founding OFI paper itself, exactly what we give up by having only bar-level taker volume. And 32% is *contemporaneous* explanatory power, which is an upper bound far above anything predictive.

---

### B. `cont-2023-xofi` — multi-level and cross-asset OFI

| Field | Value |
|---|---|
| **Citation** | Cont, R., Cucuringu, M., Zhang, C. (2023). "Cross-impact of order flow imbalance in equity markets." *Quantitative Finance* 23(10), 1373–1393. |
| **DOI / URL** | `10.1080/14697688.2023.2236159`; preprint `arXiv:2112.13213` |
| **Peer review** | Yes |
| **Asset / venue** | U.S. equities (Nasdaq ITCH-type multi-level book). Exact ticker set and sample dates: **not verified** |
| **Sample / frequency** | **Not verified** (short intraday intervals) |
| **Variables** | OFI at multiple book levels; an "integrated OFI" built as the first principal component, reported to capture **over 89%** of variance across multi-level OFIs; cross-asset OFIs |
| **Target** | Contemporaneous returns and short-horizon future intraday returns |
| **Model** | OLS and LASSO, single-asset vs cross-asset specifications |
| **Temporal validation** | Forward-looking forecasts are evaluated out-of-sample (R² and an economic criterion). Exact split protocol: **not verified** |
| **Costs modelled** | **Not verified** |
| **Reported numbers** | Integrated OFI outperforms best-level OFI for contemporaneous impact; cross-impact terms add nothing contemporaneously once multi-level OFI is integrated; lagged cross-asset OFIs *do* improve return forecasts, but the effect **"manifests at short-term horizons and decays rapidly in time."** Exact R² values: **not verified** |
| **Benchmark** | Best-level (Cont 2014) OFI; sparse own-asset model |
| **Variants** | Best-level vs integrated vs cross-asset, several horizons — count **not verified** |
| **Multiple-testing correction** | LASSO provides shrinkage-based selection, not a formal family-wise or FDR correction |
| **Code / data** | **Not verified** |
| **Leaks / weaknesses** | Rapid decay means the tradable window is very short and cost-sensitive; equities only; requires L2 depth which is the whole point of the paper |
| **Compatibility with our data** | **None for the core contribution.** Multi-level OFI is definitionally an order-book object. |
| **Reproducibility grade for us** | **Low** |
| **Replicable hypothesis** | (Only the cross-asset shell survives.) Lagged BTC taker imbalance may forecast ETH returns beyond ETH's own imbalance, at short horizons that decay fast. |

---

### C. `easley-2012-vpin` — VPIN / flow toxicity

| Field | Value |
|---|---|
| **Citation** | Easley, D., López de Prado, M., O'Hara, M. (2012). "Flow Toxicity and Liquidity in a High Frequency World." *Review of Financial Studies* 25(5), 1457–1493. |
| **DOI / URL** | SSRN 1695596 (`10.2139/ssrn.1695596`). RFS DOI: **not verified**. Note the article is cited in the literature under both "…and Liquidity…" and "…and Volatility…" — the SSRN title uses *Liquidity*. |
| **Peer review** | Yes |
| **Asset / venue** | E-mini S&P 500 futures, CME (per Andersen & Bondarenko's description, row D — I could not verify this from the primary abstract page) |
| **Sample / frequency** | **Not verified**. Method operates in **volume time**: fixed-size volume buckets, not calendar bars |
| **Variables** | Bucketed buy/sell volume imbalance; bulk volume classification (BVC) using the standardised price change across the bucket |
| **Target** | Short-term, toxicity-induced **volatility** — explicitly not returns or direction |
| **Model** | VPIN = mean absolute bucket imbalance over a rolling window of buckets, normalised by bucket size |
| **Temporal validation** | **Not verified**; the original papers are largely descriptive/event-study in character |
| **Costs modelled** | No |
| **Reported numbers** | Claim: VPIN is "a useful indicator of short-term, toxicity-induced volatility," and high readings preceded the 2010 Flash Crash. Exact statistics: **not verified**. **See row D — the Flash Crash timing claim is disputed and appears to be wrong.** |
| **Benchmark** | The original PIN (Easley, Kiefer, O'Hara, Paperman 1996) |
| **Variants** | Bucket size, window length, classification rule — count **not verified** |
| **Multiple-testing correction** | No |
| **Code / data** | No official release. Many third-party implementations exist and they disagree with each other on bucketing details. |
| **Leaks / weaknesses** | (i) **The Flash Crash claim was contradicted by Andersen and Bondarenko** (row D). (ii) VPIN is highly sensitive to bucket size and window length, which are free parameters — a large researcher-degrees-of-freedom surface. (iii) Andersen and Bondarenko attribute the apparent predictive content to a **mechanical relation with trading intensity**, which is a direct warning for us. (iv) Easley et al. themselves later conceded (2017 comment on Ke and Lin) that their estimator can be improved by using bucket fill *time*. |
| **Compatibility with our data** | **Medium, with an important caveat.** We can build a bar-level analogue using true taker volumes — arguably *better* than BVC, since BVC exists only to *estimate* what our data reports directly. But we cannot form genuine equal-volume buckets from 5m bars, so a "5m VPIN" is a *different estimator* with different statistical properties, not a replication. |
| **Reproducibility grade for us** | **Medium** (analogue only, not replication) |
| **Replicable hypothesis** | Sustained absolute taker-volume imbalance, normalised by total volume, forecasts near-term realised volatility — **but only if it beats a trade-intensity control**. |

---

### D. `andersen-2014-vpin` — the VPIN refutation

| Field | Value |
|---|---|
| **Citation** | Andersen, T.G., Bondarenko, O. (2014). "VPIN and the flash crash." *Journal of Financial Markets* 17(C), 1–46. |
| **DOI / URL** | DOI **not verified**; ScienceDirect PII `S1386418113000189`; RePEc `RePEc:eee:finmar:v:17:y:2014:i:c:p:1-46`. Earlier version: CREATES Research Paper 2011-50, Aarhus University. |
| **Peer review** | Yes |
| **Asset / venue** | E-mini S&P 500 futures, CME |
| **Sample / frequency** | Includes the 6 May 2010 Flash Crash. Exact window: **not verified**. Both calendar-time and volume-time |
| **Variables** | TR-VPIN (tick-rule classified) and BV-VPIN (bulk-volume classified); trading intensity; VIX |
| **Target** | Short-run realised volatility; flash-crash early warning |
| **Model** | Forecasting regressions against volatility benchmarks |
| **Temporal validation** | Comparative forecast evaluation against benchmarks. Exact protocol **not verified** |
| **Costs modelled** | No |
| **Reported numbers** | Three verified qualitative findings: VPIN is **"a poor predictor of short run volatility"**; it **"did not reach an all-time high prior, but rather after, the flash crash"**; its predictive content is **"due primarily to a mechanical relation with the underlying trading intensity."** Exact coefficients: **not verified** |
| **Benchmark** | Standard volatility models and VIX — the paper's methodological point is precisely that a toxicity metric must be benchmarked |
| **Variants** | TR-VPIN and BV-VPIN, multiple parameterisations — count **not verified** |
| **Multiple-testing correction** | No |
| **Code / data** | **Not verified** |
| **Leaks / weaknesses** | Single contract, single event. Nothing here says order-flow toxicity is meaningless — it says the *specific VPIN estimator*, as published, failed against proper benchmarks. |
| **Compatibility with our data** | The *methodological lesson* transfers completely |
| **Reproducibility grade for us** | **High** — as a mandatory control, not as a signal |
| **Replicable hypothesis** | Any imbalance-based toxicity feature must be shown to add explanatory power **over and above trade count / trade intensity**, or its apparent power is mechanical. |

**This row is a pre-specified falsification test for our project, not a signal source.** Any VPIN-like feature we build gets a horse race against `trade_count` before it enters a strategy.

---

### E. `easley-2016-bvc` — does aggregated data carry the same information?

| Field | Value |
|---|---|
| **Citation** | Easley, D., López de Prado, M., O'Hara, M. (2016). "Discerning information from trade data." *Journal of Financial Economics* 120(2), 269–286. |
| **DOI / URL** | `10.1016/j.jfineco.2016.01.018`; SSRN 1989555 (`10.2139/ssrn.1989555`) |
| **Peer review** | Yes |
| **Asset / venue** | U.S. futures/equities. Exact instruments: **not verified** |
| **Sample / frequency** | **Not verified**. Aggregation into time or volume blocks is central |
| **Variables** | BVC-estimated buy fraction; tick rule; aggregated tick rule; true aggressor side as ground truth |
| **Target** | Two distinct targets: (a) accuracy of aggressor-side classification; (b) correlation with proxies for information-based trading |
| **Model** | A Bayesian model of inference from executions, plus empirical accuracy comparisons |
| **Temporal validation** | Not applicable — this is a measurement-accuracy study |
| **Costs modelled** | No |
| **Reported numbers** | Verified qualitative finding: **"tick rule approaches and BVC are relatively good classifiers of the aggressor side of trading, but bulk volume classifications are better linked to proxies of information-based trading."** Exact accuracy percentages: **not verified** |
| **Benchmark** | Tick rule, aggregated tick rule |
| **Variants** | Three algorithms × block definitions — count **not verified** |
| **Multiple-testing correction** | No |
| **Code / data** | **Not verified** |
| **Leaks / weaknesses** | The claim "better linked to proxies of informed trading" is circular in an uncomfortable way: the proxies (VPIN and relatives) are themselves BVC-constructed in the authors' own prior work. Directly contested by row F. |
| **Compatibility with our data** | **This is the theoretical charter for our entire Domain-2 approach** — it is the paper arguing that *aggregated* volume classification retains informational content |
| **Reproducibility grade for us** | **High** — and we can do better than the paper, since we have the true aggressor split and do not need BVC at all |
| **Replicable hypothesis** | Volume aggregated to a bar and split by aggressor side retains information about informed trading even though individual trade identities are lost. |

---

### F. `chakrabarty-2015-horserace` — the counter-evidence on BVC

| Field | Value |
|---|---|
| **Citation** | Chakrabarty, B., Pascual, R., Shkilko, A. (2015). "Evaluating trade classification algorithms: Bulk volume classification versus the tick rule and the Lee-Ready algorithm." *Journal of Financial Markets* 25, 52–79. |
| **DOI / URL** | `10.1016/j.finmar.2015.06.001`; working-paper version SSRN 2182819 (`10.2139/ssrn.2182819`) |
| **Peer review** | Yes |
| **Asset / venue** | U.S. equities with HFT presence, stratified by size |
| **Sample / frequency** | **Not verified** |
| **Variables** | BVC, tick rule, Lee-Ready; true aggressor side |
| **Target** | Classification accuracy |
| **Model** | Direct accuracy comparison |
| **Temporal validation** | Not applicable |
| **Costs modelled** | No |
| **Reported numbers** | Verified qualitative finding: the tick rule and Lee-Ready **outperform BVC across all stock size groups**, and BVC produces **significantly higher misclassification rates**. Exact percentages: **not verified** |
| **Benchmark** | Tick rule, Lee-Ready |
| **Variants** | Size groups × algorithms — count **not verified** |
| **Multiple-testing correction** | No |
| **Code / data** | **Not verified** |
| **Leaks / weaknesses** | Measures aggressor accuracy, which Easley et al. (row E) argue is the *wrong* objective; a related independent study (Chakrabarty/Shohfi-hosted, *JBF* 2019, `10.1016/j.jbankfin.2019.04.001`) partially sides with Easley by finding BVC is the only algorithm related to informed-trading proxies. The two camps are measuring different things. |
| **Compatibility with our data** | **The dispute is moot for us — and that is the point.** Binance reports the aggressor side, so we sidestep the entire debate. |
| **Reproducibility grade for us** | **Not applicable** (methodological context) |
| **Replicable hypothesis** | None directly; establishes that our exchange-reported taker split is strictly superior to what the equity literature works with. |

---

### G. `chordia-2002-oib` — aggregate order imbalance and returns

| Field | Value |
|---|---|
| **Citation** | Chordia, T., Roll, R., Subrahmanyam, A. (2002). "Order imbalance, liquidity, and market returns." *Journal of Financial Economics* 65(1), 111–130. |
| **DOI / URL** | DOI constructible as `10.1016/S0304-405X(02)00136-8` from the Elsevier PII, but **not independently verified**; RePEc `RePEc:eee:jfinec:v:65:y:2002:i:1:p:111-130` |
| **Peer review** | Yes |
| **Asset / venue** | NYSE-listed stocks, aggregated to market level; S&P 500 index return as the dependent variable |
| **Sample / frequency** | **1988–1998 inclusive; 2,779 daily observations.** ISSM data 1988–1992, TAQ 1993–1998. **Daily** |
| **Variables** | OIBNUM (buy trades minus sell trades) and dollar-value imbalance, signed with **Lee-Ready**; aggregate volume; liquidity measures |
| **Target** | Daily market return, contemporaneous and next-day |
| **Model** | OLS with day-of-week dummies, lagged returns split into positive/negative parts, and five lags of imbalance; Newey-West-type corrections |
| **Temporal validation** | **In-sample only.** No out-of-sample split, no walk-forward |
| **Costs modelled** | **No** |
| **Reported numbers** | Adjusted R² of **0.477** and **0.408** in the two reported specifications of the table I retrieved — these include *contemporaneous* imbalance, so they are not forecasting R². Contemporaneous imbalance is highly significant; **lagged imbalance carries a significant negative coefficient**, consistent with inventory-driven reversal. Verified abstract claim: **"Market returns reverse themselves after high-negative-imbalance, large-negative-return days."** |
| **Benchmark** | Volume and liquidity controls |
| **Variants** | ~6+ regression specifications reported in the main tables; unreported specifications: **not verified** |
| **Multiple-testing correction** | **No** |
| **Code / data** | No |
| **Leaks / weaknesses** | (i) **The headline R² is contemporaneous and cannot be traded.** (ii) In-sample only, one market, one regime, an era of specialist market-making that no longer exists. (iii) A secondary summary I retrieved states that imbalances "do not predict next-day market returns" — I could not confirm that phrasing in the primary text, so treat it as unverified, but it is consistent with the negative lagged coefficient. (iv) Lee-Ready signing error. |
| **Compatibility with our data** | **High conceptually.** Our TI is the direct crypto analogue of OIBNUM/dollar imbalance — with exact rather than estimated signing. |
| **Reproducibility grade for us** | **High** |
| **Replicable hypothesis** | Signed order imbalance moves prices contemporaneously, and the *lagged* component predicts **reversal**, not continuation — so the naive "buy when taker buying is high" rule has the sign backwards at the aggregate level. |

**This is the strongest theoretical case for a contrarian rather than momentum reading of taker imbalance,** and it directly contradicts the folk-wisdom crypto "CVD trend-following" narrative.

---

### H. `boehmer-2021-retail` — signed retail flow as a predictor

| Field | Value |
|---|---|
| **Citation** | Boehmer, E., Jones, C.M., Zhang, Xiaoyan, Zhang, Xinran (2021). "Tracking Retail Investor Activity." *The Journal of Finance* 76(5), 2249–2305. |
| **DOI / URL** | `10.1111/jofi.13033` |
| **Peer review** | Yes |
| **Asset / venue** | U.S. equities, off-exchange (TRF) retail prints identified by sub-penny price improvement |
| **Sample / frequency** | Working-paper version: **January 2010 – December 2015** (six years). Whether the published *JF* version uses the same window: **not verified**. Weekly aggregation |
| **Variables** | Marketable retail order imbalance; order-flow persistence; contrarian-trading proxy; public news sentiment |
| **Target** | Cross-sectional stock returns, 1 week to 12 weeks ahead |
| **Model** | Portfolio sorts and cross-sectional regressions with a decomposition into persistence / liquidity provision / information |
| **Temporal validation** | Full-sample cross-sectional predictive regressions. **Not a walk-forward design** |
| **Costs modelled** | **No** |
| **Reported numbers** | Published *JF* abstract: net-buying stocks outperform negative-imbalance stocks by **approximately 10 bps over the following week**; less than half is attributable to order-flow persistence. **A retrieved earlier working-paper version states 20 bps / ~10% annualised, and the ABFER version states 10 bps / ~5% annualised.** The estimate therefore roughly halved between drafts. Predictability persists to about 12 weeks. **Aggregate retail imbalance does not predict future market returns** — no market-timing ability. |
| **Benchmark** | Standard cross-sectional controls |
| **Variants** | "A battery of robustness checks" — count **not verified** |
| **Multiple-testing correction** | **No** |
| **Code / data** | The identification algorithm is published and widely reimplemented; TAQ is licensed |
| **Leaks / weaknesses** | (i) **The halving of the headline number across drafts is a red flag** — it is exactly the pattern you expect when a first-draft specification does not survive refereeing. (ii) 10 bps/week is below realistic round-trip costs for a rebalancing long/short book in most implementations. (iii) The identification rule itself has been challenged in later literature (I did not verify that literature here). (iv) Purely cross-sectional — and the paper is explicit that it does **not** work as a time-series market-timing signal. |
| **Compatibility with our data** | **Low.** We cannot separate retail from institutional flow. We have two assets, so there is essentially no cross-section. And the paper's own negative result on aggregate timing is the case that maps onto our setting. |
| **Reproducibility grade for us** | **Low** |
| **Replicable hypothesis** | Signed flow from a *specific identifiable clientele* predicts cross-sectional returns; undifferentiated aggregate signed flow **does not predict the time series**. |

---

### I. `barclay-1993-stealth` — trade size as an informedness proxy

| Field | Value |
|---|---|
| **Citation** | Barclay, M.J., Warner, J.B. (1993). "Stealth trading and volatility: Which trades move prices?" *Journal of Financial Economics* 34(3), 281–305. |
| **DOI / URL** | `10.1016/0304-405X(93)90029-B` |
| **Peer review** | Yes |
| **Asset / venue** | NYSE firms — a sample of tender-offer targets |
| **Sample / frequency** | ~105–108 NYSE tender-offer targets, **1981–1984** (per the retrieved Chakravarty *JFE* 2001 description); transaction data |
| **Variables** | Trade-size buckets (small / medium 500–9,999 shares / large); cumulative price change attributable to each bucket |
| **Target** | Share of cumulative price change by trade-size category |
| **Model** | Accounting decomposition of cumulative price change |
| **Temporal validation** | **None.** In-sample event-window decomposition |
| **Costs modelled** | No |
| **Reported numbers** | Medium-size trades (500–9,999 shares) account for an estimated **92.8%** of the cumulative price change in the pre-tender-offer-announcement period. (Number taken from Chakravarty's *JFE* 2001 restatement, not from the 1993 original — **verified as a restatement, not from the primary text**.) Chakravarty (2001) later attributed this to **institutional** medium-size trades, finding ~79% cumulative price change concentrated there. |
| **Benchmark** | The trade-count and volume share of each bucket |
| **Variants** | Bucket boundaries and subsamples — count **not verified** |
| **Multiple-testing correction** | **No** |
| **Code / data** | No |
| **Leaks / weaknesses** | (i) **Severe selection**: the sample is *tender-offer targets*, i.e. events chosen because informed trading occurred. This is close to conditioning on the outcome. (ii) 1981–1984, pre-decimalisation, pre-electronic — trade-size bucket boundaries have no meaning in a market where algorithms slice orders into hundreds of child fills. (iii) Descriptive attribution, not prediction. (iv) No costs, no out-of-sample. |
| **Compatibility with our data** | **Very low.** We have `volume/trade_count` — a *mean*, not a distribution — and even that is contaminated by the `aggTrades` question flagged in §0. Modern order slicing largely destroys the size-informedness link. |
| **Reproducibility grade for us** | **Low** |
| **Replicable hypothesis** | Informed participation concentrates in a particular part of the trade-size distribution, so shifts in average trade size proxy for changes in the informed/uninformed participation mix. **Our data can express this only as a crude first moment.** |

---

### J. `easley-2026-crypto` — microstructure metrics on Binance crypto

| Field | Value |
|---|---|
| **Citation** | Easley, D., O'Hara, M., Yang, S., Zhang, Z. "Microstructure and market dynamics in crypto markets." *Journal of Financial Markets*. Working paper dated April 30, 2024. |
| **DOI / URL** | SSRN 4814346 (`10.2139/ssrn.4814346`); journal version `10.1016/j.finmar.2026.101071`, ScienceDirect PII `S1386418126000261`. Author-hosted PDF: `stoye.economics.cornell.edu/docs/Easley_ssrn-4814346.pdf`. Volume/issue/pages: **not verified** |
| **Peer review** | **Yes** for the *JFM* version; the numbers I quote below are from the **April 2024 working paper**, and I could not verify they are unchanged in the published article |
| **Asset / venue** | **Binance**, five cryptocurrencies: BTC, ETH, XRP, SOL, ADA. Spot vs perpetual: **not verified** |
| **Sample / frequency** | **January 2021 – July 2023**, spanning the "crypto winter". **One-minute time bars** — chosen explicitly because "that is the highest granularity bar data the public exchanges offer" |
| **Variables** | Roll measure, Roll impact measure, **Amihud illiquidity, Kyle's lambda, VPIN** — computed from Binance prices and volumes at 1-minute bars |
| **Target** | **Not returns.** Five binary labels: sign of change in (1) volatility, (2) autocorrelation of realised returns, (3) absolute skewness, (4) kurtosis, (5) the Jarque-Bera statistic |
| **Model** | Random forest, own-market and cross-market features |
| **Temporal validation** | Machine-learning classification with AUC evaluation, citing López de Prado (2018) on evaluation. **Exact train/test protocol and whether purging/embargo were used: not verified** |
| **Costs modelled** | **No** — and the paper does not construct a trading strategy |
| **Reported numbers** | Averaging across currencies and variables, **AUC > 0.55**. Range **0.54–0.61** across the outcomes, **except skewness where AUC = 0.50** (no predictability). Predictability is driven by the **Roll measure and VPIN**; BTC and ETH Roll and VPIN have strong **cross-asset** predictive power. Results are **"little changed during crypto winter."** |
| **Benchmark** | AUC = 0.50 (random); comparison to their earlier futures-market results (ELOZ 2021) |
| **Variants** | 5 assets × 5 outcomes × own/cross specifications ≈ 25+ reported cells |
| **Multiple-testing correction** | **No** — this is a real weakness given ~25+ AUC cells with a threshold as low as 0.55 |
| **Code / data** | **Not verified.** Underlying data is public Binance kline/trade data, which is a genuine plus |
| **Leaks / weaknesses** | (i) **AUC 0.54–0.61 on binary sign-of-change labels is a weak effect**, and no multiple-testing correction is applied across many cells. (ii) The targets are **distributional moments, not returns** — this is not a directional alpha result and should never be cited as one. (iii) The autocorrelation and Roll-measure targets are partly mechanically linked (the Roll measure *is* a function of return autocovariance), which risks a near-tautology in the autocorrelation cell. (iv) No costs, no strategy. (v) One venue. |
| **Compatibility with our data** | **Very high.** Binance, BTC/ETH, 1-minute bars, and every feature is computable from kline OHLCV plus volume. |
| **Reproducibility grade for us** | **High** — the closest thing in the peer-reviewed literature to a template for what we can actually build |
| **Replicable hypothesis** | Bar-level illiquidity and toxicity measures (Amihud, Kyle's lambda, VPIN-analogue, Roll) predict the *sign of changes in volatility and return autocorrelation* — i.e. they are **regime/state predictors, not return predictors**. |

---

### K. `kim-hansen-2026-quarterhour` — the most directly exploitable result found

| Field | Value |
|---|---|
| **Citation** | Kim, C., Hansen, P.R. (2026). "The Quarter-Hour Effect: Periodic Algorithmic Trading and Return Predictability in Cryptocurrency Futures." arXiv preprint. |
| **DOI / URL** | `arXiv:2607.09426`; HTML at `arxiv.org/html/2607.09426` |
| **Peer review** | **No — preprint.** Mitigating: Hansen is a senior econometrician (h-index 39 per the retrieved metadata) and the paper reports an **independent data validation and replication study by Wade Kimbrough** |
| **Asset / venue** | **Binance USDT-margined perpetual futures.** Six contracts: BTC, ETH, XRP, SOL, DOGE, ADA |
| **Sample / frequency** | **January 1, 2021 – October 31, 2024** (1,400 calendar days). Aggregate trade data with `isBuyerMaker`; **10-second bars**; forecasting sample for the OOS section is **2021-07-01 to 2024-10-31, ~117,000 observations per asset** |
| **Variables** | Signed order flow and volume-normalised **order imbalance** from `isBuyerMaker`; 12 quarter-hour-spaced lags of the opening 10s return; **28 technical indicators computed on a 15-minute OHLCV grid** ("TI28"); trade-size roundness |
| **Target** | (a) Opening 10-second return at quarter-hour boundaries, continuous and directional; (b) cumulative forward returns at horizons 30s, 1m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 24h |
| **Model** | Rolling-window walk-forward **LASSO** (continuous) and L1-penalised logistic regression (direction); separately, horizon-specific OLS predictive regressions with nested clock-time interactions |
| **Temporal validation** | **Genuine walk-forward.** Re-estimated **each month on the trailing six months**, forecasting the following month; λ chosen on the chronological 20% tail of each training window. Diebold-Mariano tests with HAC (lag 6). Predictive regressions use HAC Bartlett-kernel errors with bandwidth increasing in horizon to handle overlap. **Placebo test**: shifted 15-minute grids anchored at non-boundary phases (e.g. minutes 2, 17, 32, 47) — the effect concentrates only under true alignment. |
| **Costs modelled** | **No.** No fees, no slippage, no funding, no strategy backtest. **This is the paper's biggest gap for us.** |
| **Reported numbers** | **Return forecasting:** lag-only model cross-sectional mean R²_OOS = **2.464%**, positive for all six assets; TI28 alone = **2.090%**; **Lag + TI28 = 3.37%**, best for all six assets; ADA has the largest lag-only R²_OOS at **5.2%**. Direction: best average **AUC = 0.6011**, best average accuracy at the 0.5 threshold = **57.12%**. **Order imbalance:** baseline and one-minute-opening imbalance show little predictive association; the quarter-hour coefficient is **small or negative at short horizons but becomes positive at medium horizons in every market**; between **4 and 12 hours** it is significant at 95% for **four of six** contracts at every horizon, SOL (4h, 12h) and ADA (4h) at 90%, with **SOL at 8h the only insignificant cell**. Roundness: for BTC at z≥2 the effect strengthens from −0.04 SD at ordinary openings to **−0.20 SD** at the top of the hour. |
| **Benchmark** | Zero forecast (for R²_OOS); AUC 0.5; placebo shifted grids; nested DM tests |
| **Variants** | 3 predictor specifications × 6 assets, plus 11 horizons × 4 clock-time regimes × 6 assets. Order of **250+ estimated cells** |
| **Multiple-testing correction** | **No formal FDR or family-wise correction.** Partially mitigated by the placebo-grid design and by DM tests, but with 250+ cells this remains a genuine concern |
| **Code / data** | Code: **not verified**. Data is public Binance aggregate trade data. Independent replication by a third party is acknowledged |
| **Leaks / weaknesses** | (i) **No transaction costs anywhere** — an R²_OOS of 3.37% on a 10-second return is almost certainly not tradable, since a 10-second horizon at 10 bps round trip requires an enormous edge. (ii) The economically interesting result — the 4–12h order-imbalance effect — is **estimated on the full sample in-sample**, not walk-forward; only the opening-return forecast is genuinely out-of-sample. That asymmetry is easy to miss and matters. (iii) 250+ cells without correction. (iv) The predictive-regression design (following Boehmer et al. 2021) uses overlapping forward returns — handled with HAC, but overlapping long-horizon predictive regressions are notoriously prone to over-rejection. (v) Signed flow is taker-side only; the authors are explicit that they cannot observe liquidity provision. |
| **Compatibility with our data** | **Very high in substance, partially blocked in form.** Same venue, same instrument type, same assets, and the order-imbalance variable is exactly our `taker_buy_base` construction. **But the effect is defined on the first 10 seconds of a quarter-hour**, and our finest bar is 5m (1m klines are obtainable). We can construct a 5m-bar approximation of "the bar opening at :00/:15/:30/:45" — but that is a **different, coarser variable**, and the paper's own finding that effects at finer clock frequencies are "much weaker" means the phase precision may be load-bearing. |
| **Reproducibility grade for us** | **Medium.** High for the mechanism, medium for the exact measurement |
| **Replicable hypothesis** | Taker-side order imbalance measured at quarter-hour clock boundaries predicts returns at **4- to 12-hour horizons** — a slow enough horizon that fees need not dominate — whereas the same imbalance at ordinary times carries little predictive content. |

**This is the single most promising row for our project,** because it is the only verified result that (a) uses exactly our instrument and exactly our signed-flow variable and (b) locates the predictability at a **holding horizon slow enough for costs to be survivable**. Its untested cost treatment is precisely the gap our protocol is designed to fill.

---

### L. `pindza-2026-microalpha` — the closest existing test of our exact setup, and it is negative

| Field | Value |
|---|---|
| **Citation** | Pindza, E. (2026). "Microstructure alpha: hierarchical learning and cross-asset transfer in cryptocurrency markets." *Frontiers in Blockchain* 9:1811716. Published 11 June 2026. Dept. of Decision Sciences, University of South Africa |
| **DOI / URL** | `10.3389/fbloc.2026.1811716`; supplementary data `10.3389/fbloc.2026.1811716.s001` |
| **Peer review** | Yes (Frontiers open-access; note that Frontiers' review model is lighter than a top finance journal's) |
| **Asset / venue** | **Binance spot AND USDT-M perpetual futures**, six assets: BTC, ETH, SOL, AVAX, LINK, DOT — twelve asset-venue pairs |
| **Sample / frequency** | **August 2025 – February 2026** (~6.5 months); **3,417,972 minute-level bars**, ~285,000 per pair. Target: **5-minute forward log return** |
| **Variables** | **All nine features are computable from klines alone** and the paper says so explicitly ("In the absence of direct order book data"): Corwin-Schultz-style high-low range spread proxy; 60-bar realised volatility; **trade intensity = trade count / 60-min rolling mean**; volume intensity; **VPIN proxy from taker buy volume over a 50-min rolling window**; **Kyle's lambda over 30 min using quote volume**; **Amihud over 30 min**; **depth imbalance = taker-buy-volume ratio**; **30-min rolling order flow imbalance**; plus 5/30/60-min momentum |
| **Target** | 5-minute forward log return |
| **Model** | Hierarchical mixed-effects linear model; randomised-Lasso stability selection; **LightGBM** with SHAP; MAML meta-learning; OLS |
| **Temporal validation** | **Purged, embargoed walk-forward cross-validation** following López de Prado (2018): **5-minute purge + 60-minute embargo** around each test block. Diebold-Mariano with Newey-West against a random walk. Hyperparameters tuned inside the training window |
| **Costs modelled** | **Yes, explicitly.** Binance **VIP-0** schedule: 10 bps/side spot (20 bps round trip); **2 bps maker / 5 bps taker futures (4–10 bps round trip)**, plus a conservative **half-spread slippage equal to the contemporaneous Corwin-Schultz spread proxy**. Bootstrap CIs via stationary block bootstrap with one-day blocks. **Funding costs and short-borrow are explicitly excluded**, so the paper calls its net Sharpes an upper bound |
| **Reported numbers** | **Forecasting (Table 3):** random walk RMSE 36.85; AR(1) and 5-min momentum both R²_OOS = **0.09%**, DM = 0.28 (insignificant); **OLS on microstructure features R²_OOS = 1.23%, DM = 1.28 — not significant**; **LightGBM R²_OOS = −10.94%, DM = −6.83, significant in the wrong direction** (in-sample R² was 35.9%). **Economics (Table 4):** gross Sharpe AR(1)/momentum **0.43**, OLS **−0.31**, LightGBM **0.96**. **Net Sharpe futures: −10.68 (AR1/momentum), −18.42 (OLS), −16.98 (LightGBM).** Net Sharpe spot −31.29 / −52.05 / −50.30. **Average daily two-way turnover 124–204× notional.** Stability selection: realised vol 0.84, 5-min momentum 0.83, spread proxy 0.79, VPIN 0.65, trade intensity 0.60, depth imbalance 0.60, Kyle's λ 0.56, OFI 0.55, volume intensity 0.51, Amihud 0.51. **Regime split**: LightGBM purged R² collapses in high-volatility and down-market regimes |
| **Benchmark** | Random walk, AR(1), 5-minute momentum — a genuinely honest benchmark set |
| **Variants** | 12 features × 12 asset-venue pairs × 5 models × regime splits — order of **hundreds** |
| **Multiple-testing correction** | **No formal correction**, but stability selection (Meinshausen-Bühlmann) plays a partly analogous role, and the DM tests are properly benchmarked |
| **Code / data** | A **replication package** is referenced in-text (`paper9_data/tables/transfer.tex`) and there is a data availability statement plus a supplementary CSV with its own DOI. Whether code is actually public: **not verified** |
| **Leaks / weaknesses** | (i) **Only 6.5 months, entirely within a 2025–2026 expansion phase** — the author concedes it "may not generalise to bear markets or to the high-volatility crash episodes of 2020–2022." (ii) Single-author Frontiers paper; the review bar is lower than a finance journal's. (iii) The 5-minute rebalance is imposed by design rather than optimised, so the negative result is partly self-inflicted — the paper itself lists "a longer holding horizon" as the obvious fix. (iv) Sharpe ratios of −52 are so extreme they indicate the strategy construction (rebalancing every 5 minutes with ~200× daily turnover) is a strawman rather than a serious implementation. (v) Funding costs excluded. |
| **Compatibility with our data** | **Essentially perfect.** Same exchange, same instrument, overlapping assets, and **every single feature is built from exactly our five kline columns.** |
| **Reproducibility grade for us** | **High** — the highest of any paper here |
| **Replicable hypothesis** | Kline-derived microstructure features carry weak but genuine forecasting information at minute frequency (OLS R²_OOS ≈ +1.2%, not statistically significant), which is **completely destroyed by transaction costs at a 5-minute holding horizon**; and flexible ML models **overfit catastrophically** under purged validation despite excellent in-sample fit. |

**This paper should be treated as our pre-registered null hypothesis.** It is the closest published attempt at what we are doing, it used our exact data, it applied purging and embargo correctly, it modelled costs, and it found nothing tradable at 5m. Any positive result we produce at a 5-minute holding horizon must explain why Pindza found the opposite.

---

### M. `jeon-2026-orderflow-state` — when does order flow matter?

| Field | Value |
|---|---|
| **Citation** | Jeon, J. (2026). "When Does Order Flow Matter? State-Dependent L2 Liquidity-State Transitions in Crypto Futures." Korea University. arXiv preprint. |
| **DOI / URL** | `arXiv:2607.09230` |
| **Peer review** | **No — preprint.** Single author |
| **Asset / venue** | **Binance BTCUSDT and ETHUSDT futures** |
| **Sample / frequency** | **2023–2026**; top-20 L2 order book, trade-flow records, macro-event windows; horizons of **1 and 5 minutes** |
| **Variables** | Discrete pre-event liquidity state (calm/mixed/stressed terciles of relative spread, top-20 depth, top-20 imbalance); continuous L2 features; **local order flow as an overlay** |
| **Target** | **Post-event discrete L2 liquidity state** — explicitly *not* price direction |
| **Model** | Coarse-state baseline, multinomial logit, ordered logit, shallow nonlinear L2-shape model, plus an order-flow overlay. Each layer admitted only if it beats the layer below |
| **Temporal validation** | **Rolling monthly out-of-sample folds**, event-clustered resampling, **blocked permutation tests**, per-asset **flow-shuffle null**, 90% event-cluster bootstrap intervals. Methodologically the most careful design in this review |
| **Costs modelled** | **No** — no strategy |
| **Reported numbers** | Coarse state vs marginal: **+0.034** (1m) / **+0.045** (5m). Multinomial logit **−0.048 / −0.034**, ordered logit **−0.052 / −0.047** — both intervals entirely below zero. Nonlinear L2-shape **+0.044 / +0.060**. **Order-flow overlay: pooled +0.010 / +0.010 against a null 95th percentile of +0.004 / +0.003; BTC +0.001 / +0.003 against nulls of +0.002 / +0.002 — not established; ETH +0.020 / +0.016 against nulls of +0.006 / +0.003 — clears.** ETH by regime: **+0.004 (calm), +0.020 (mixed), +0.038 (stressed)** at 1m; **+0.004 / +0.015 / +0.030** at 5m |
| **Benchmark** | Staged nested baselines plus per-asset flow-shuffle nulls — an unusually strong benchmark design |
| **Variants** | 4 model layers × 2 horizons × 2 assets × 3 regimes ≈ 48 principal cells |
| **Multiple-testing correction** | No formal FDR, but permutation nulls and cluster-bootstrap intervals substantially mitigate this |
| **Code / data** | **Not verified** |
| **Leaks / weaknesses** | (i) **The target is liquidity state, not returns** — no directional or economic claim is made, and it must not be cited as evidence of alpha. (ii) Single-author preprint. (iii) L2 top-20 book data is proprietary/expensive and is the backbone of the paper. (iv) Restricted to macro-event windows, so external validity to ordinary trading is unestablished. |
| **Compatibility with our data** | **Low for the L2 backbone, high for the conclusion.** We cannot build any of the L2 state features. |
| **Reproducibility grade for us** | **Low** |
| **Replicable hypothesis** | **Order flow adds predictive value only conditionally** — on top of a liquidity-state model, and only in stressed states, and (over 2023–2026 Binance data) **for ETH but not BTC**. |

**This is the second-most decision-relevant row for us.** An independent, methodologically careful study using our exact instruments found that order flow's incremental value is regime-conditional and asset-specific, and that **BTC order flow did not clear its null**. If we pre-specify an order-flow strategy family, we should expect asymmetry between BTC and ETH and should build a stress-regime conditioner in from the start.

---

### N. `brauneis-2021-liquidity` — which liquidity proxies actually work in crypto

| Field | Value |
|---|---|
| **Citation** | Brauneis, A., Mestel, R., Riordan, R., Theissen, E. (2021). "How to measure the liquidity of cryptocurrency markets?" *Journal of Banking & Finance* 124, 106041. |
| **DOI / URL** | `10.1016/j.jbankfin.2020.106041` |
| **Peer review** | Yes — a top-tier finance journal |
| **Asset / venue** | Bitcoin and Ethereum on Bitfinex, Bitstamp, Coinbase Pro. **Spot exchanges, not perpetual futures** |
| **Sample / frequency** | Continuous transactions data plus **order book snapshots of the 50 best bids/asks**; evaluated at **minute, hourly and daily** frequency. Exact date range: **not verified** |
| **Variables** | Low-frequency proxies — **Amihud (2002)**, **Kyle-Obizhaeva (2016)**, **Corwin-Schultz (2012)**, **Abdi-Ranaldo (2017)** — benchmarked against high-frequency ground truth: quoted spread, effective spread, price impact, cost of a round trip |
| **Target** | **Not returns.** How well each cheap proxy reproduces true (order-book-measured) liquidity, in time series and in levels |
| **Model** | Correlation and rank-correlation of proxies against high-frequency benchmarks |
| **Temporal validation** | Not applicable — a measurement-validation study |
| **Costs modelled** | Not applicable |
| **Reported numbers** | **Corwin-Schultz and Abdi-Ranaldo best capture time-series variation**, robust across observation frequency, venue, benchmark and currency, and in both high and low return/volatility/volume periods. **Kyle-Obizhaeva and Amihud are best for estimating liquidity levels** and for ranking venues. Conclusion: "there is not yet a universally best measure but there are reasonably good low-frequency measures." Exact correlation coefficients: **not verified** |
| **Benchmark** | True high-frequency order-book liquidity — the correct benchmark |
| **Variants** | ~4+ proxies × 3 frequencies × 3 venues × 4 benchmarks × 2 currencies ≈ 200+ cells |
| **Multiple-testing correction** | No — but this is a measurement study, so the concern is much reduced |
| **Code / data** | **Not verified** |
| **Leaks / weaknesses** | (i) **Spot exchanges only**; perpetual futures have a different maker/taker population, and the result may not transfer. (ii) Pre-dates the current market structure. (iii) Says nothing about return predictability — it validates *measurement*, not *signal*. (iv) Corwin-Schultz assumes properties of the high-low range that may be violated during crypto volatility spikes. |
| **Compatibility with our data** | **High.** Every recommended proxy is computable from OHLCV + quote volume |
| **Reproducibility grade for us** | **High** — for feature construction; we cannot re-run the validation itself without order-book ground truth |
| **Replicable hypothesis** | Amihud and Kyle-Obizhaeva measure liquidity *levels* well and Corwin-Schultz / Abdi-Ranaldo track liquidity *variation* well — so **the right kline-derived illiquidity feature depends on whether you want a level or a change**. |

**Practical consequence:** this row tells us *which* illiquidity feature to reach for and why, and it is peer-reviewed in a top journal. It is the best-quality evidence in Domain 3 that transfers to us.

---

### O. `pinto-2025-btcfutures` — trade size and volatility on our exact instrument

| Field | Value |
|---|---|
| **Citation** | Pinto, M.G. de F. (2025). "High-frequency dynamics of Bitcoin futures: An examination of market microstructure." *Borsa Istanbul Review*. |
| **DOI / URL** | `10.1016/j.bir.2025.07.016`; author copy at `repositorio.usp.br` |
| **Peer review** | Yes |
| **Asset / venue** | **Bitcoin and Ethereum perpetual futures on Binance** |
| **Sample / frequency** | **January 2020 – December 2024**, all executed transactions; aggregated to **1, 5, 10, 15, 30, 60-minute and daily** levels |
| **Variables** | Average transaction price; **transaction rate (trades per time unit)**; average percentage return variance; **average unsigned number of contracts per transaction (trade size)**; cumulative volume — all in logs |
| **Target** | **Return volatility per transaction as a function of trade size** — testing the Mixture of Distributions Hypothesis against the Intraday Trading Invariance Hypothesis |
| **Model** | Log-log regressions of volatility on trade size and transaction rate; MDH predicts a different exponent than ITIH |
| **Temporal validation** | **In-sample across aggregation levels.** No out-of-sample or walk-forward. Stability is assessed across *frequencies*, not across *time* |
| **Costs modelled** | No — no strategy |
| **Reported numbers** | **"We find evidence favoring the MDH in the crypto futures market"**, i.e. **larger trade sizes are associated with higher return variance**. Exact exponents, standard errors and R²: **not verified** |
| **Benchmark** | ITIH (Andersen et al. 2020) as the competing hypothesis — a genuine structural horse race |
| **Variants** | 7 aggregation levels × 2 assets × 2 hypotheses ≈ 28 principal specifications |
| **Multiple-testing correction** | **No** |
| **Code / data** | **Not verified.** Underlying Binance trade data is public |
| **Leaks / weaknesses** | (i) **Volatility, not returns** — no directional content whatsoever. (ii) In-sample only. (iii) The author himself flags that 1-minute data "might be too noisy and lead to distortions." (iv) Contemporaneous relationship, so it does not establish that trade size *forecasts* anything. (v) MDH/ITIH are structural hypotheses about volume-volatility co-determination, not tradable claims. |
| **Compatibility with our data** | **High.** Trade count and `volume/trade_count` are directly available — subject to the `aggTrades` caveat in §0, which is exactly the kind of definitional issue that would shift the estimated exponent |
| **Reproducibility grade for us** | **High** for the feature construction, **Medium** for the test (we have bar aggregates, the author had every transaction) |
| **Replicable hypothesis** | On Binance BTC/ETH perpetuals, **average trade size and transaction rate co-determine return variance** — so these variables belong in a **volatility model or a regime classifier**, not in a directional signal. |

---

## 2. Papers reporting positive Sharpe — critical evaluation

Only **two** of the fifteen papers report a Sharpe-like statistic at all. That is itself the headline finding: the serious literature in these four domains overwhelmingly reports *explanatory power*, *AUC*, or *R²*, not risk-adjusted trading returns. Anything claiming a Sharpe from these signals is doing something the literature has not validated.

### L. Pindza (2026) — gross Sharpe 0.96 (LightGBM), 0.43 (AR1/momentum); **net Sharpe −10.68 to −18.42 on futures**

The gross figures are the only positive Sharpes, and the paper's entire point is that they are illusory. **Would it survive our protocol? It already didn't survive the author's own, which is stricter than most.** Costs: modelled, at VIP-0 futures rates (2 bps maker / 5 bps taker) plus half-spread slippage — reasonable, though funding and borrow are excluded so the true net figures are *worse*. Walk-forward: yes, purged and embargoed. Multiple testing: no formal correction, but the negative result means correction would only strengthen the conclusion. The gross Sharpe of 0.96 for LightGBM is not even meaningful, since the same model has R²_OOS = −10.94% — a strong hint that the gross Sharpe is an artifact of the sign structure of an overfit forecast rather than genuine edge. **Verdict: this is a validated negative result at a 5-minute holding horizon, and we should adopt it as our null.**

### O2. Bieganowski & Ślepaczuk (2026), `arXiv:2602.00776`, "Explainable Patterns in Cryptocurrency Microstructure" — information ratios of **0.25 (BTC), 6.58 (ENJ), 8.97 (ETC), 0.07 (LTC), 5.28 (ROSE)** on a taker backtest

*(University of Warsaw; Binance Futures perpetual order books and trades at 1-second frequency, 1 Jan 2022 – 12 Oct 2025; CatBoost with a GMADL direction-aware objective; walk-forward CV with purging; 3-second mid-price return target.)*

I am **highly sceptical** and would not build on this. Specific objections:

- **The IR pattern is inverted relative to liquidity.** BTC — the most liquid, most competitively traded contract — gets IR* = 0.25 and ARC = 0.13, while ENJ, ETC and ROSE (small caps) get IR* of 6.58, 8.97 and 5.28. Their secondary "IR**" metric reaches **213.58** for ETC. Information ratios in that range on a taker-fee-paying strategy are not credible; they are the signature of a backtest artifact, most plausibly the illiquidity of small-cap perpetuals combined with a 3-second horizon where crossing the spread should dominate.
- **Costs are optional.** The paper says: "Optional proportional costs can be introduced to reflect taker fees; we report gross and fee adjusted returns." The summary table I retrieved does not label which is which, and latency is explicitly not modelled ("results should be interpreted as an upper bound in the fastest regime"). At a 3-second horizon with event-driven position management, fees and latency are not a detail — they are the whole problem.
- **A 3-second horizon is categorically out of reach for us.** It requires co-location, sub-second book data, and queue modelling. None of it maps to 5m bars.
- **Requires L2 order book data.** The top features are order-book imbalance and VWAP-to-mid deviation. We have neither.
- **Would it survive our protocol? No — it cannot even be run under our protocol.** The signal is undefined at our data frequency.

### Papers with no Sharpe but that are sometimes *misread* as positive results

- **Cont, Kukanov & Stoikov (row A), R² = 65%.** Contemporaneous. Not tradable. Not a Sharpe.
- **Chordia, Roll & Subrahmanyam (row G), adjusted R² = 0.477.** Contains contemporaneous imbalance. Not tradable. The *lagged* coefficient is negative, i.e. reversal.
- **Easley, O'Hara, Yang & Zhang (row J), AUC 0.54–0.61.** Predicts sign-of-change in volatility/autocorrelation/kurtosis, not returns. No strategy, no costs, ~25 uncorrected cells.
- **Kim & Hansen (row K), R²_OOS = 3.37%.** Genuinely walk-forward and genuinely out-of-sample, but on a **10-second** return with **zero costs modelled**. At 10 seconds, 3.37% R²_OOS is almost certainly worth less than 5 bps of taker fee. **The medium-horizon (4–12h) order-imbalance result is the economically interesting part — and it is estimated in-sample, not walk-forward.** This distinction is the crux of whether we can use this paper, and it is easy to conflate the two results.

---

## 3. Verdict for our project

### The honest bottom line

**Domain 1 (canonical OFI) is not implementable with our data, and we should say so explicitly in the thesis rather than approximate it and call it OFI.** Cont-Kukanov-Stoikov OFI is defined over limit-order arrivals and cancellations at the best quotes; the quote-to-trade ratio in their data is ~40:1, so we are missing the large majority of the events. Their own decomposition puts trade imbalance at R² = 32% versus OFI's 65% *contemporaneously* — and when both enter jointly, trade imbalance loses significance in 69% of subsamples. Calling `(2·taker_buy − volume)/volume` "OFI" would be a misnomer we should avoid; the correct name is **trade imbalance** or **taker imbalance**, and Chordia et al.'s OIB is its proper ancestor.

**Domain 3 (order book depth, true Kyle's lambda, liquidity shocks) is likewise not directly implementable** — but its *low-frequency proxies* are, and Brauneis et al. (2021, *JBF*) is peer-reviewed evidence that Amihud and Kyle-Obizhaeva are adequate for levels and Corwin-Schultz / Abdi-Ranaldo for variation, in crypto specifically.

**Domain 4 (trade-size distribution) is the weakest.** We have only the first moment, `volume/trade_count`, whose meaning depends on the unresolved `aggTrades` question. Barclay-Warner's stealth-trading result rests on 1981–1984 NYSE tender-offer targets and does not plausibly transfer to a market where algorithms slice orders. The only crypto-native trade-size evidence (Pinto 2025) links trade size to **volatility**, not direction.

**Domain 2 is where we are actually advantaged.** The entire Lee-Ready / tick-rule / BVC literature exists to *estimate* the aggressor side. Binance reports it. Our bar-level signed volume is exact.

### Three signal ideas worth pre-specifying

**1. Medium-horizon taker-imbalance persistence at clock boundaries (primary candidate).**

Pre-specify a signal built from normalised taker imbalance accumulated over a window of 5m bars, with entries conditioned on quarter-hour phase and **holding periods in the 4–12 hour range**. Rationale, all from verified sources: Kim & Hansen find that quarter-hour opening order imbalance on Binance USDT-M perpetuals predicts returns positively at 4–12h, significant at 95% for four of six contracts at every horizon in that band, with "much weaker effects at finer clock-time frequencies" — and their placebo test on shifted grids rules out a generic even-spacing artifact. Pindza demonstrates, with correct purging and explicit VIP-0 costs, that the *same underlying features* produce net Sharpes of −10 to −18 at a 5-minute rebalance driven by 124–204× daily turnover. The two results are consistent and point the same way: **the horizon, not the feature, is what kills 5-minute microstructure strategies.** A 4–12h holding period reduces turnover by roughly two orders of magnitude, which is exactly the margin Pindza identifies as the fix ("a longer holding horizon that amortises the round-trip cost").

Honest caveats to record before running anything: (i) the 4–12h result in Kim & Hansen is **in-sample**, not walk-forward — only their 10-second opening-return forecast is genuinely out-of-sample, and we must not inherit the OOS credibility of one result for the other; (ii) they measure imbalance over the **first 10 seconds** of the boundary, which our 5m bars cannot resolve — our version is a coarser proxy of unknown fidelity, and their own finding that finer clock frequencies are weaker suggests phase precision may matter; (iii) at 4–12h holding, **funding payments (every 8 hours) become a first-order cost**, and no paper in this review models them; (iv) Chordia et al. found the *lagged* imbalance coefficient to be **negative** in equities, so the sign is not theoretically settled and must be an estimated parameter, not an assumption.

**2. Liquidity/toxicity state as a conditioning gate, not as a directional signal.**

Build Amihud illiquidity (|r| / quote_volume over 30–60 min), a Kyle-lambda analogue (price impact per unit quote volume), a Corwin-Schultz-style high-low range spread proxy, realised volatility, and trade intensity — then use them to **classify a regime** rather than to predict direction. Jeon's result is the direct motivation: on Binance BTCUSDT and ETHUSDT over 2023–2026, the pre-event liquidity state was the first-order predictor, and **order flow added value only as an overlay conditional on state** — rising monotonically from +0.004 (calm) to +0.020 (mixed) to +0.038 (stressed) for ETH, while **BTC never cleared its flow-shuffle null at either horizon**. Easley, O'Hara, Yang & Zhang independently show these same kline-computable measures predict the *sign of changes in volatility and autocorrelation* on Binance (AUC 0.54–0.61) but not returns. Brauneis et al. tells us which specific proxy to use for levels versus variation.

Pre-specify accordingly: expect the directional signal in idea 1 to **work on ETH and possibly fail on BTC**, and expect it to be concentrated in stressed liquidity states. Building that asymmetry in as a hypothesis rather than discovering it post hoc is the difference between a finding and a data-mining artifact.

**3. Trade intensity as a mandatory control — and as a volatility feature, not a return feature.**

This is a falsification requirement more than a signal. Andersen & Bondarenko showed VPIN's apparent predictive content was **"due primarily to a mechanical relation with the underlying trading intensity."** We have `trade_count` directly. Therefore: **every imbalance- or toxicity-derived feature we build must be shown to add explanatory power over a trade-count control before it is allowed into a strategy.** Separately, Pinto's MDH result on our exact instrument (Binance BTC/ETH perpetuals, 2020–2024) supports using trade count and average trade size in a **volatility** model — which is useful for position sizing and for regime definition even though it carries no directional content.

### What we should *not* attempt

- Any feature named "OFI" in the Cont-Kukanov-Stoikov sense — the data does not exist for us.
- Integrated multi-level OFI (Cont, Cucuringu & Zhang) — definitionally an L2 object.
- Genuine volume-bucketed VPIN — we can build a bar-level analogue, but it is a different estimator and must be labelled as such.
- Trade-size *distribution* features, roundness diagnostics, or retail-versus-institutional decomposition — all require tick data.
- Anything at a 3-second to 1-minute holding horizon — the only paper reporting attractive Sharpes there (Bieganowski & Ślepaczuk) has optional costs, no latency model, and information ratios that are inversely related to liquidity, which I read as an artifact rather than a finding.
- Cross-sectional signals — we have two assets.

### One methodological commitment I'd suggest adding

Both of the two most methodologically careful papers here (Kim & Hansen with 250+ cells; Jeon with ~48) apply **no formal multiple-testing correction**, relying instead on permutation nulls and placebo designs. Given that our methodology already commits to Random Search and a Genetic Algorithm — which will generate far more specifications than either — the **flow-shuffle / block-permutation null used by Jeon is a directly borrowable and well-suited technique**: shuffle the taker-imbalance series within blocks, re-run the full search, and require the real result to beat the 95th percentile of the shuffled-search distribution. That tests the search procedure, not just a single specification, which is the right unit of analysis for our design.