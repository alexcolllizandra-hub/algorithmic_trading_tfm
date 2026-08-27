# Literature review: exogenous data sources for intraday BTCUSDT/ETHUSDT perpetuals

**Compiled:** 2026-08-11. **Scope:** on-chain, attention/sentiment, macro point-in-time,
scheduled events, intraday periodicity.
**Question being answered:** should this thesis ingest any exogenous dataset beyond the
Binance USDT-M perpetual klines / mark-price klines / funding-rate history we already hold
(BTCUSDT, ETHUSDT, 5m, 2020–2026)?

## 0. Verification conventions

Every field below was read from the source indicated. Where a field could not be read from
a primary source in this session it says **not verified**, and the "What could not be
verified" section at the end lists those gaps explicitly. No DOI, URL, author, year or
reported number in this document was inferred or reconstructed from memory.

Grades used:

| Grade | Reproducibility for *us* (BTCUSDT/ETHUSDT perps, 5m, 2020–2026, leak-free) |
|---|---|
| A | Reproducible with data we already own, no new licence, no point-in-time (PIT) risk |
| B | Reproducible with a free/cheap source whose PIT status we can establish |
| C | Reproducible only with a paid source, or PIT status is compromised for our window |
| D | Not reproducible: data unavailable, non-PIT with no remedy, or design not transferable |

"Multiple-testing correction" means an explicit statistical correction (FWER/FDR/SPA/
Harvey–Liu), not merely "we tested few variants".

---

## 1. Evidence matrix

### 1.1 Domain 1 — On-chain variables

---

**id:** `grobys-nasman-sandretto-2026-onchain-cycles`

- **Citation:** Grobys, K., Näsman, S., Sandretto, D. (2026). "Using on-chain data to predict Bitcoin cycles." *Research in International Business and Finance* 89, 103486.
- **DOI / permanent URL:** https://doi.org/10.1016/j.ribaf.2026.103486 (open access, CC BY; received 12 Feb 2026, accepted 12 May 2026, online 15 May 2026)
- **Peer-review status:** Peer-reviewed (Elsevier journal article).
- **Asset / market / venue / instrument:** Bitcoin spot price series obtained from Investing.com. No venue-specific microstructure; no futures, no perpetuals.
- **Sample period and frequency:** Daily closing prices; trading simulations span three Bitcoin market cycles, with the buy-and-hold benchmark entered on 7 December 2013 and the dataset ending 12 April 2025.
- **Variables used:** Three on-chain indicators — Net Unrealized Profit/Loss (NUPL), MVRV Z-score, Cumulative Value Days Destroyed (CVDD).
- **Predictive target:** Cycle turning points (bottoms/tops) in the Bitcoin price; long-only entry/exit timing.
- **Model or rules:** Threshold-based, interpretable contrarian rules per indicator; CVDD is used only as a bottom-detection signal (no exit rule), exits set to the cycle peak or the last close.
- **Temporal validation method:** None in the walk-forward sense. Full-sample, in-sample rule evaluation across three historically identified cycles, with a Monte Carlo random-entry benchmark and alternative-exit robustness checks. Statistical inference conducted on the full daily sample.
- **Costs / slippage / funding modelled:** Not in the main tables. Footnote 1 states an *unreported* analysis with a conservative 2% per-trade cost leaves results "qualitatively unchanged"; results only "available from the authors upon request". Funding not applicable (spot).
- **Reported return / Sharpe / drawdown:** Abstract reports Sharpe rising from **0.45** (buy-and-hold) to **1.28** (MVRV Z-score). Cumulative and annualised log returns, annualised volatility, min/max daily returns also tabulated (exact values not transcribed here).
- **Benchmark:** Buy-and-hold from 7 Dec 2013; plus Monte Carlo random-entry strategies.
- **Number of variants tested:** Three indicators; several MVRV Z-score entry variants and alternative exits. The authors state they deliberately fixed three ex-ante indicators to limit data-mining risk.
- **Multiple-testing correction:** None. Explicitly substituted by "we only tested three pre-chosen indicators".
- **Code / data availability:** Not verified — no code or data repository identified in the article text retrieved.
- **Possible leaks or weaknesses (specific):**
  1. **Cycle boundaries are defined ex post.** Exits are set to "the cycle peak", which is only knowable after the fact. The CVDD entry is argued to be real-time implementable, but the exit is not.
  2. **On-chain series are vendor-computed and, in general, retroactively revised** (see §3.1). The paper does not state that point-in-time vintages of NUPL/MVRV/CVDD were used. If mutable series were used, the entire result is contaminated by revision look-ahead.
  3. **Effective sample size is tiny**: a handful of trades across three cycles. A Sharpe of 1.28 on ~3–9 trades is not statistically distinguishable from luck without an explicit test, and none is reported.
  4. Costs are relegated to an unreported robustness check.
- **Compatibility with BTCUSDT/ETHUSDT perpetuals:** Low. Daily, cycle-horizon (months to years), long-only spot. Our unit of decision is a 5-minute bar on a perpetual with funding.
- **Reproducibility grade for us:** **D** (horizon mismatch is fatal even before the PIT problem).
- **Replicable economic hypothesis (one sentence):** When the aggregate unrealised profit of Bitcoin holders is extremely depressed relative to its own history, forward multi-month returns are positive because capitulation has exhausted marginal sellers.

---

**id:** `sakkas-urquhart-2024-blockchain-factors`

- **Citation:** Sakkas, A., Urquhart, A. (2024). "Blockchain factors." *Journal of International Financial Markets, Institutions and Money* 94, 102012.
- **DOI / permanent URL:** https://doi.org/10.1016/j.intfin.2024.102012
- **Peer-review status:** Peer-reviewed.
- **Asset / market / venue / instrument:** Cross-section of individual cryptocurrencies (spot). Venue not verified.
- **Sample period and frequency:** **Not verified** (abstract and repository records retrieved do not state them; full text not accessed).
- **Variables used:** 13 candidate factors — market, size, momentum (from Liu & Tsyvinski 2021; Liu, Tsyvinski & Wu 2022) plus ten on-chain factors. Winning on-chain characteristic is the Network Distribution Factor (NDF): supply held by addresses with at least one ten-thousandth of current supply, divided by current supply.
- **Predictive target:** Cross-sectional expected returns of individual cryptocurrencies.
- **Model or rules:** Long–short factor portfolios; two-factor asset-pricing model (value-weighted market factor + NDF).
- **Temporal validation method:** Cross-sectional asset-pricing tests. Walk-forward/out-of-sample design **not verified**.
- **Costs / slippage / funding modelled:** Not verified.
- **Reported return / Sharpe / drawdown:** Not verified (exact figures not read).
- **Benchmark:** Existing crypto factor models (market, size, momentum).
- **Number of variants tested:** 13 factors assessed.
- **Multiple-testing correction:** **Yes** — explicitly uses the Harvey & Liu (2021) methodology for factor selection under multiple testing. This is the strongest methodological feature of the paper and the reason it is included here.
- **Code / data availability:** Not verified.
- **Possible leaks or weaknesses (specific):**
  1. NDF is a *supply-concentration* characteristic computed from address balances; it depends on address-level data that vendors recompute retroactively when clustering/labelling improves (§3.1). Unless PIT vintages were used, the factor is contaminated.
  2. Cross-sectional design: BTC and ETH are explicitly reported as *always in the bottom tercile* of NDF and never in the top tercile — the premium is earned on small, concentrated coins, not on the two assets we trade.
  3. Survivorship in the coin universe is a standard hazard for this design and was not verified as addressed.
- **Compatibility with BTCUSDT/ETHUSDT perpetuals:** Very low. The paper's own result says the effect lives in the coins we do *not* trade, at a frequency far below 5 minutes.
- **Reproducibility grade for us:** **D**.
- **Replicable economic hypothesis:** Investors demand a premium for holding coins whose supply is concentrated in few addresses, because such networks are more exposed to manipulation.

---

### 1.2 Domain 2 — Attention, sentiment and news

---

**id:** `nasir-huynh-nguyen-duong-2019-search-engines`

- **Citation:** Nasir, M.A., Huynh, T.L.D., Nguyen, S.P., Duong, D. (2019). "Forecasting cryptocurrency returns and volume using search engines." *Financial Innovation* 5(1), article 2.
- **DOI / permanent URL:** https://doi.org/10.1186/s40854-018-0119-8 (open access; accepted 28 Dec 2018, published online 10 Jan 2019)
- **Peer-review status:** Peer-reviewed.
- **Asset / market / venue / instrument:** Bitcoin, spot, venue not specified in the text retrieved.
- **Sample period and frequency:** **Weekly**, 2013–2017. Bitcoin prices sampled on Sundays.
- **Variables used:** Google Trends search values for Bitcoin-related terms; Bitcoin returns; Bitcoin trading volume.
- **Predictive target:** Bitcoin weekly returns and trading volume.
- **Model or rules:** VAR, copulas, non-parametric dependence estimation, impulse responses.
- **Temporal validation method:** None (in-sample econometrics; no out-of-sample forecast evaluation, no trading simulation).
- **Costs / slippage / funding modelled:** Not applicable — no strategy is simulated.
- **Reported return / Sharpe / drawdown:** **None reported.** The paper reports statistical significance, not performance. The volume effect "fell just short of statistical significance benchmarks".
- **Benchmark:** None (no strategy).
- **Number of variants tested:** Not verified.
- **Multiple-testing correction:** None.
- **Code / data availability:** Not verified.
- **Possible leaks or weaknesses (specific):**
  1. The authors state they "adjusted some of the insufficient data collected from Google Trends to have a continuous time series" and skipped weeks with no data — an undocumented, non-reproducible preprocessing step on a series that is itself a resampled index.
  2. Google Trends is not point-in-time (§3.2); the series downloaded in 2018 is not the series a trader saw in 2014.
  3. Weekly frequency; 2013–2017 sample predates the market structure we trade.
  4. An independent public replication (GitHub, `Adeline117/Reproducing-Quantitative-Research`) reports the Granger-causality result disappears post-2020 (p ≈ 0.94). This is **not peer-reviewed** and is reported here only as a caution flag, not as evidence.
- **Compatibility with BTCUSDT/ETHUSDT perpetuals:** None at 5-minute frequency.
- **Reproducibility grade for us:** **D**.
- **Replicable economic hypothesis:** A surge in retail search interest brings uninformed buying pressure that pushes Bitcoin returns up over the following week.

---

**id:** `dastgir-demir-downing-gozgor-lau-2019-copula-attention`

- **Citation:** Dastgir, S., Demir, E., Downing, G., Gozgor, G., Lau, C.K.M. (2019). "The causal relationship between Bitcoin attention and Bitcoin returns: Evidence from the Copula-based Granger causality test." *Finance Research Letters* 28, 160–164.
- **DOI / permanent URL:** https://doi.org/10.1016/j.frl.2018.04.019 (published online 27 April 2018)
- **Peer-review status:** Peer-reviewed.
- **Asset / market / venue / instrument:** Bitcoin, spot.
- **Sample period and frequency:** Full sample 12 August 2013 – 31 December 2017; sub-samples split at a Bai–Perron structural break dated 11 August 2013. Frequency: daily (Google Trends search queries).
- **Variables used:** Change in Google Trends search queries (GSQ); Bitcoin returns (RBC).
- **Predictive target:** Bitcoin returns (and reverse direction).
- **Model or rules:** Copula-based Granger-causality-in-distribution and in-quantiles.
- **Temporal validation method:** None (in-sample causality testing).
- **Costs / slippage / funding modelled:** Not applicable.
- **Reported return / Sharpe / drawdown:** **None.**
- **Benchmark:** None.
- **Number of variants tested:** Multiple quantiles (1%, 5%, 10%, 20%–80%, 90%, 95%, 99%) plus lagged-return robustness.
- **Multiple-testing correction:** None, despite testing ~13 quantiles in two directions.
- **Code / data availability:** Not verified.
- **Possible leaks or weaknesses (specific):**
  1. The headline result is **negative in the centre of the distribution**: no significant influence between 40% and 80% quantiles over the full sample, and none at 50/60/70% in the sub-sample. Causality appears only in the tails — exactly where a ~13-quantile test with no correction is most likely to produce false positives.
  2. Causality is **bi-directional**, so this is not evidence of tradable predictability.
  3. Structural break dated 11 Aug 2013 is estimated on the full sample and then used to define sub-samples — an in-sample conditioning step.
  4. Google Trends non-PIT problem (§3.2).
- **Compatibility with BTCUSDT/ETHUSDT perpetuals:** None.
- **Reproducibility grade for us:** **D**.
- **Replicable economic hypothesis:** Attention and returns reinforce each other only during extreme market states, not in normal conditions.

---

**id:** `kristoufek-2013-trends-wikipedia`

- **Citation:** Kristoufek, L. (2013). "BitCoin meets Google Trends and Wikipedia: Quantifying the relationship between phenomena of the Internet era." *Scientific Reports* 3, 3415.
- **DOI / permanent URL:** https://doi.org/10.1038/srep03415
- **Peer-review status:** Peer-reviewed (Nature Portfolio, open access).
- **Asset / market / venue / instrument:** Bitcoin, spot. Venue **not verified**.
- **Sample period and frequency:** **Not verified** (article full text not retrieved in this session; citation and DOI confirmed via the reference lists of Grobys et al. 2026 and Dastgir et al. 2019, and via Hansen/Kim/Kim's reference list).
- **Variables used:** Google Trends search volume; Wikipedia page-view counts.
- **Predictive target:** Bitcoin price.
- **Model or rules:** Correlation/causality analysis; described in the citing literature as documenting a "strong bi-directional relationship" and positive association between attention and price.
- **Temporal validation method:** Not verified.
- **Costs / slippage / funding modelled:** Not verified; almost certainly not applicable (no strategy).
- **Reported return / Sharpe / drawdown:** Not verified. No performance metric is attributed to this paper by any source read.
- **Benchmark / variants / multiple-testing correction:** Not verified.
- **Code / data availability:** Not verified.
- **Possible leaks or weaknesses:** Included here only as the canonical origin of the crypto-attention literature. Its sample (2011–2013) is a different market. **It is cited in this review as a landmark, not as evidence for a trading decision.**
- **Compatibility with BTCUSDT/ETHUSDT perpetuals:** None.
- **Reproducibility grade for us:** **D**.
- **Replicable economic hypothesis:** Public attention and Bitcoin price are mutually reinforcing during bubble episodes.

---

**id:** `guegan-renault-2021-stocktwits-intraday`

- **Citation:** Guégan, D., Renault, T. "Does investor sentiment on social media provide robust information for Bitcoin returns predictability?" *Finance Research Letters*, article 101494 (available online 19 March 2020). Volume/issue **not verified**.
- **DOI / permanent URL:** https://doi.org/10.1016/j.frl.2020.101494
- **Peer-review status:** Peer-reviewed.
- **Asset / market / venue / instrument:** Bitcoin, spot; exchange **not verified**.
- **Sample period and frequency:** 988,622 StockTwits messages sent 2017–2019; sentiment indicators built at frequencies from **1 minute to 24 hours**. Reported regressions have 1,228,320 observations at 1-minute and 245,664 at 5-minute frequency.
- **Variables used:** Average message sentiment per interval (StockTwits, classified following Renault 2017); message count as an attention proxy; lagged returns; volume.
- **Predictive target:** Next-interval Bitcoin return.
- **Model or rules:** Predictive regressions plus Granger causality, run separately at each frequency.
- **Temporal validation method:** In-sample regressions with a bubble/non-bubble sub-sample split (August 2017 – April 2018 flagged as the bubble period). No walk-forward, no out-of-sample.
- **Costs / slippage / funding modelled:** Costs are discussed, not simulated — and the discussion is the paper's main contribution.
- **Reported return / Sharpe / drawdown:** No Sharpe. Effect sizes are reported directly: a one-unit rise in sentiment (neutral → positive) raises the next-period return by **0.0035% to 0.0087%**. At 5-minute frequency, mean return is **−0.0035%** after negative sentiment and **+0.0025%** after positive sentiment. Adjusted R² is 1.841% at 1 min, 0.027% at 5 min, 0.015% at 15 min.
- **Benchmark:** Implicit zero-return / no-trade.
- **Number of variants tested:** 10 frequencies × 2–3 specifications, plus sub-samples.
- **Multiple-testing correction:** None.
- **Code / data availability:** Not verified.
- **Possible leaks or weaknesses (specific):**
  1. The authors themselves conclude the effect is **too small to be profitable after reasonable transaction costs**, and explicitly decline to conclude that Bitcoin is intraday-inefficient.
  2. Effect concentrated in the 2017–2018 bubble window — a regime that does not recur in our 2020–2026 sample.
  3. Predictability vanishes beyond 15 minutes.
  4. StockTwits historical message archives are not obviously re-obtainable today under an academic licence (**not verified**).
- **Compatibility with BTCUSDT/ETHUSDT perpetuals:** Frequency is compatible (5m/15m). Data is not: we would need a historical StockTwits/X archive back to 2020.
- **Reproducibility grade for us:** **C→D** — the design is compatible, but the input data is not obtainable on the evidence gathered, and the paper's own conclusion is that the effect does not survive costs.
- **Replicable economic hypothesis:** Retail sentiment posted in the previous 5 minutes moves the next 5-minute return by an economically negligible amount that is smaller than the round-trip fee.

---

### 1.3 Domain 3 — Macro variables and point-in-time

---

**id:** `karau-2023-monetary-policy-and-bitcoin`

- **Citation:** Karau, S. (2023). "Monetary policy and Bitcoin." *Journal of International Money and Finance* 137, 102880.
- **DOI / permanent URL:** https://doi.org/10.1016/j.jimonfin.2023.102880
- **Peer-review status:** Peer-reviewed.
- **Asset / market / venue / instrument:** Bitcoin (high-frequency price data; venue **not verified**), compared against equities, FX and gold.
- **Sample period and frequency:** Event study uses **high-frequency intraday** prices in narrow windows around announcements; the complementary SVAR uses **daily** data from mid-2013 until early 2023.
- **Variables used:** FOMC announcement surprises (Target / Path / LSAP factors in the Gürkaynak et al. tradition), US CPI release surprises; Bitcoin returns and realized volatility.
- **Predictive target:** Contemporaneous Bitcoin return and realized volatility in the announcement window; longer-horizon impulse responses in the SVAR.
- **Model or rules:** Event-study regressions (MacKinlay 1997) plus SVAR identified with external instruments.
- **Temporal validation method:** Sub-sample split (pre-2018 / pre-2020 vs post-2020). No out-of-sample forecast evaluation, no trading simulation.
- **Costs / slippage / funding modelled:** Not applicable.
- **Reported return / Sharpe / drawdown:** **No strategy performance is reported.** Findings are qualitative: realized volatility around FOMC windows started to increase some time after the COVID outbreak in late 2020; post-2020 Bitcoin responds to monetary news like other risky assets, "quantitatively even more strongly"; post-2020 Bitcoin also reacts to CPI surprises, but co-moves with risky assets rather than benefiting from positive inflation surprises.
- **Benchmark:** Stocks, FX, gold.
- **Number of variants tested:** Multiple event windows and sub-samples; count not verified.
- **Multiple-testing correction:** None.
- **Code / data availability:** Not verified.
- **Possible leaks or weaknesses (specific):**
  1. The paper documents a **volatility** response far more clearly than a directional return response. A volatility result does not translate into a directional strategy.
  2. The post-2020 finding is a sub-sample chosen after inspecting the data.
  3. Requires monetary-policy *surprises* constructed from federal funds and eurodollar futures — a dataset we do not have and which is itself vintage-sensitive.
- **Compatibility with BTCUSDT/ETHUSDT perpetuals:** Moderate for the *event-timing* component only. FOMC and CPI release timestamps are published in advance and are historically verifiable, so a "volatility rises in the announcement window" feature is causal by construction.
- **Reproducibility grade for us:** **B** for a pure calendar-event feature (announcement timestamps only, no surprise data); **D** for the surprise-based version.
- **Replicable economic hypothesis:** Since late 2020, Bitcoin's realized volatility rises in a narrow window around scheduled US monetary-policy and inflation releases.

---

**id:** `benigno-rosa-2023-bitcoin-macro-disconnect`

- **Citation:** Benigno, G., Rosa, C. (2023). "The Bitcoin–Macro Disconnect." *Federal Reserve Bank of New York Staff Reports*, no. 1052, February 2023. JEL: F3, F4, G1.
- **DOI / permanent URL:** https://www.newyorkfed.org/research/staff_reports/sr1052
- **Peer-review status:** **Not peer-reviewed** (central-bank staff report). Companion blog post: Benigno & Rosa, "Is There a Bitcoin–Macro Disconnect?", Liberty Street Economics, 8 February 2023.
- **Asset / market / venue / instrument:** Bitcoin, plus EUR/USD, gold and the S&P 500 for comparison. Venue for Bitcoin **not verified**.
- **Sample period and frequency:** Intraday event windows (the companion blog and press coverage describe 30-minute windows). 2000–2022 for the comparison assets; **2017–2022 for Bitcoin**.
- **Variables used:** Ten sets of macro announcements (real activity, inflation) plus three monetary-policy surprise dimensions — Target, Path, LSAP — constructed from five non-overlapping federal funds and eurodollar futures contracts.
- **Predictive target:** Contemporaneous asset return in the announcement window.
- **Model or rules:** Standard high-frequency announcement event study.
- **Temporal validation method:** None (event study).
- **Costs / slippage / funding modelled:** Not applicable.
- **Reported return / Sharpe / drawdown:** **None.** Headline result is a **null**: unlike other US asset classes, Bitcoin is orthogonal to monetary and macroeconomic news.
- **Benchmark:** EUR/USD, gold, S&P 500.
- **Number of variants tested:** Ten announcement sets × four assets × three policy factors.
- **Multiple-testing correction:** Not verified.
- **Code / data availability:** Not verified.
- **Possible leaks or weaknesses (specific):** The sample ends in 2022 and includes the COVID period; the null may be a low-power result rather than a true zero, and it is in tension with Karau (2023), who finds a *post-2020* response. Both cannot be fully right; the honest reading is that the directional macro→Bitcoin link is at best unstable.
- **Compatibility with BTCUSDT/ETHUSDT perpetuals:** Directly relevant as a **negative** result for our Domain 3.
- **Reproducibility grade for us:** **D** for replication (needs futures-based surprise data); **A** as a citable prior that lowers our expectations.
- **Replicable economic hypothesis:** Bitcoin returns do not respond systematically to scheduled US macroeconomic surprises.

---

### 1.4 Domain 4 — Events with verifiable advance timestamps (funding, carry)

---

**id:** `christin-routledge-soska-zetlinjones-crypto-carry-trade`

- **Citation:** Christin, N., Routledge, B.R., Soska, K., Zetlin-Jones, A. "The Crypto Carry Trade." Working paper (version 1.0), hosted at Carnegie Mellon University. Year of the retrieved version **not verified**; cited by Schmeling, Schrimpf & Todorov as "Christin et al. (2022)".
- **DOI / permanent URL:** https://www.andrew.cmu.edu/user/azj/files/CarryTrade.v1.0.pdf (no DOI verified)
- **Peer-review status:** **Not peer-reviewed** on the evidence gathered.
- **Asset / market / venue / instrument:** **Binance** perpetual futures — both USDT-margined and coin-margined ("inverse") — plus the corresponding spot index. 18 cryptocurrencies, BTC contracts the focus.
- **Sample period and frequency:** **2020-08-11 to 2022-06-20.** Underlying data at minute frequency, aggregated to the **8-hour funding period**.
- **Variables used:** Perpetual futures price, funding rate, spot index price.
- **Predictive target:** Return to a delta-hedged trade: long spot, short perpetual, held across funding periods.
- **Model or rules:** Mechanical carry: collect funding when positive, bear the basis change. Not a forecasting model.
- **Temporal validation method:** None. Full-sample in-sample, with a four-sub-period stability table.
- **Costs / slippage / funding modelled:** **Funding is the entire signal** and is modelled exactly (Binance's own formula). The paper explicitly states it "abstracts from margin, leverage, transaction costs, and other details particular to the exchange" in the main derivation, revisiting them later; the risk-free rate is set to zero (justified: 1-month T-bill averaged 0.05% p.a. over the sample).
- **Reported return / Sharpe / drawdown:** **In-sample annualised Sharpe ratios of 12.8 and 7.0** for the two BTC contracts (USDT-settled and coin-settled respectively). Drawdown not verified.
- **Benchmark:** Buy-and-hold BTC (reported as growing more in level terms but far more volatile).
- **Number of variants tested:** 18 coins × 2 contract types; 4 sub-periods.
- **Multiple-testing correction:** None (not really needed — this is a mechanical cash-flow, not a mined rule).
- **Code / data availability:** Not verified.
- **Possible leaks or weaknesses (specific):**
  1. A Sharpe of 12.8 with no transaction costs, no margin, no liquidation modelling, and no borrow cost for the spot leg is **not an achievable Sharpe**. Schmeling et al. show independently that at 10× leverage the futures leg of the analogous fixed-maturity trade would have been liquidated in over half the months of their sample.
  2. Requires a **spot leg** we do not have. Our dataset is perpetual klines only.
  3. Sample stops mid-2022, before the current funding regime.
  4. Tether de-peg risk is acknowledged but not priced.
- **Compatibility with BTCUSDT/ETHUSDT perpetuals:** **Highest of any paper in this review** — same exchange, same instruments, same 8-hour funding clock, overlapping window with ours.
- **Reproducibility grade for us:** **C** — we have the funding-rate history and the perp klines, but not the spot leg. A funding-*timing* study (behaviour of perp returns around settlement) is grade **A**; the carry trade itself is not.
- **Replicable economic hypothesis:** Leveraged long demand on Binance perpetuals is persistently paid for through positive funding, so the short-perpetual side of a delta-neutral position earns that premium.

---

**id:** `schmeling-schrimpf-todorov-crypto-carry`

- **Citation:** Schmeling, M., Schrimpf, A., Todorov, K. "Crypto Carry." Published in *Management Science* (article DOI 10.1287/mnsc.2024.05069; INFORMS listing shows 2026, volume/issue not yet assigned). Earlier versions: BIS Working Papers no. 1087 (2023); CEPR Discussion Paper 20719 (2025); SSRN 3774118 (posted 2021).
- **DOI / permanent URL:** https://doi.org/10.1287/mnsc.2024.05069 ; working paper: https://www.bis.org/publ/work1087.pdf
- **Peer-review status:** Peer-reviewed (Management Science), accepted by Agostino Capponi.
- **Asset / market / venue / instrument:** **Fixed-maturity** crypto futures (1- and 3-month constant maturity) on Binance, OKEx, FTX, Huobi, BitMEX, Deribit and the CME. BTC and ETH. Note: the published paper studies fixed-date futures, *not* perpetuals; perpetual results appear in the earlier SSRN abstract and should not be attributed to the published version.
- **Sample period and frequency:** Main sample **March 2019 – July 2024** (BTC on OKEx starts March 2019; CME basis starts August 2020). Daily basis data; monthly liquidation regressions.
- **Variables used:** Futures–spot basis (carry), Google Trends index for "BTC"/"bitcoin"/"bitcoin futures"/"bitcoin price"/"bitcoin leverage", CFTC positioning, implied volatility, exchange liquidation data.
- **Predictive target:** Level and variation of crypto carry; liquidations; cash-and-carry returns.
- **Model or rules:** Panel regressions, difference-in-differences around the CME micro-futures launch and the spot-BTC-ETF launch, cash-and-carry strategy simulation.
- **Temporal validation method:** None in the walk-forward sense; sub-sample and event-based identification.
- **Costs / slippage / funding modelled:** Explicitly assessed and dismissed as explanations: spot bid-ask < 0.2% on crypto-native exchanges, CME futures bid-ask < 3%, exchange fees 0.1%–0.25% (citing Makarov & Schoar 2020). Collateral financed at LIBOR (results similar with SOFR).
- **Reported return / Sharpe / drawdown:** Carry "sometimes exceeding 40% per annum"; roughly **7% p.a. average** crypto carry vs ~0.7% for the S&P 500 and lower for Treasuries. Sharpe **not verified**. Critically: at 10× leverage, the futures leg **would have been liquidated in over half the months** of the sample.
- **Benchmark:** Carry in equities, US Treasuries, oil and gold (Online Appendix Table A.2).
- **Number of variants tested:** Multiple exchanges, maturities and specifications; count not verified.
- **Multiple-testing correction:** Not verified.
- **Code / data availability:** Online appendix and data files stated to be available at the article DOI.
- **Possible leaks or weaknesses (specific):**
  1. FTX is in the sample; its collapse creates a survivorship/venue-continuity issue for any replication.
  2. The Google Trends regressor is non-PIT (§3.2); the reported R² of 12% for OKEx carry vs 1% for CME carry is therefore an upper bound.
  3. Fixed-maturity futures ≠ perpetuals. The convergence mechanism the paper relies on does not exist for perps.
- **Compatibility with BTCUSDT/ETHUSDT perpetuals:** Moderate. Same asset and era, different instrument. Its liquidation finding is the strongest available reality-check on the Christin et al. Sharpe.
- **Reproducibility grade for us:** **D** for replication (needs multi-venue fixed-maturity basis data); **A** as a citable constraint on carry-style claims.
- **Replicable economic hypothesis:** Trend-chasing retail demand for leveraged long exposure, combined with regulatory and margin limits on arbitrage capital, keeps crypto futures persistently expensive relative to spot.

---

**id:** `hudson-urquhart-2021-technical-trading`

- **Citation:** Hudson, R., Urquhart, A. (2021). "Technical trading and cryptocurrencies." *Annals of Operations Research* 297(1), 191–220.
- **DOI / permanent URL:** https://doi.org/10.1007/s10479-019-03357-1
- **Peer-review status:** Peer-reviewed.
- **Asset / market / venue / instrument:** Bitcoin (two markets), Litecoin, Ethereum, Ripple. Spot.
- **Sample period and frequency:** **Daily**, "longest data period available for each individual cryptocurrency" (exact dates not verified).
- **Variables used:** Price only — five classes of technical trading rules.
- **Predictive target:** Next-day direction / excess return.
- **Model or rules:** **14,919** technical trading rules across five families (following Hsu et al. 2016).
- **Temporal validation method:** In-sample rule evaluation plus a separate out-of-sample period.
- **Costs / slippage / funding modelled:** Break-even transaction costs computed and reported as "substantially higher than those typically found in cryptocurrency markets".
- **Reported return / Sharpe / drawdown:** Risk-adjusted returns reported as substantially higher than buy-and-hold, with protection against long drawdowns. Exact figures not verified. **Crucially: no predictability for Bitcoin in the out-of-sample period**, though it persists in the other coins.
- **Benchmark:** Buy-and-hold.
- **Number of variants tested:** 14,919.
- **Multiple-testing correction:** **Yes** — Sullivan, Timmermann & White reality-check-style bootstrap plus **family-wise error rate (FWER)** and **false discovery rate (FDR)** procedures.
- **Code / data availability:** Not verified.
- **Possible leaks or weaknesses (specific):** Daily frequency; spot; sample includes the pre-2018 era when the market was structurally different. The in-sample/out-of-sample split is a single chronological cut, not walk-forward.
- **Compatibility with BTCUSDT/ETHUSDT perpetuals:** Indirect. This paper is included as the **methodological benchmark** our own search must meet or exceed: ~15k rules, explicit FWER/FDR, break-even cost reporting, and honest reporting of the out-of-sample failure on Bitcoin.
- **Reproducibility grade for us:** **A** (price-only; our data suffices; the design transfers directly to 5m bars).
- **Replicable economic hypothesis:** Simple price-based rules capture short-lived trends in crypto, but the effect on Bitcoin does not survive out-of-sample.

---

### 1.5 Domain 5 — Intraday periodicity

---

**id:** `hansen-kim-kim-2024-periodicity`

- **Citation:** Hansen, P.R., Kim, C., Kim, W. (2024). "Periodicity in Cryptocurrency Volatility and Liquidity." *Journal of Financial Econometrics* 22(1), 224–251.
- **DOI / permanent URL:** https://doi.org/10.1093/jjfinec/nbac034
- **Peer-review status:** Peer-reviewed.
- **Asset / market / venue / instrument:** BTC and ETH on **Binance** and Coinbase Pro (CEX) and Uniswap V2 (DEX). Spot markets (perpetuals not stated).
- **Sample period and frequency:** High-frequency intraday. Exact sample dates **not verified**.
- **Variables used:** Realized volatility, trading volume, time-of-day / day-of-week / within-hour dummies.
- **Predictive target:** Volatility and volume (**not returns**).
- **Model or rules:** Periodicity decomposition; GARCH-type models augmented with periodic components.
- **Temporal validation method:** In-sample **and out-of-sample** forecast evaluation — the paper reports that incorporating periodicity improves both.
- **Costs / slippage / funding modelled:** Not applicable (no trading strategy).
- **Reported return / Sharpe / drawdown:** **None** — this is a volatility-modelling paper.
- **Benchmark:** GARCH without periodic terms.
- **Number of variants tested:** Not verified.
- **Multiple-testing correction:** Not verified.
- **Code / data availability:** Not verified.
- **Possible leaks or weaknesses (specific):** Because the target is volatility and not return, no leakage-sensitive trading claim is made. The attribution of the patterns to "algorithmic trading and funding times in futures markets" is stated as a conjecture ("presumably related to"), not a tested channel.
- **Compatibility with BTCUSDT/ETHUSDT perpetuals:** **Very high.** Same assets, same exchange family, same frequency band, and the effect it documents (within-hour and 8-hour funding-clock periodicity) is directly measurable in the data we already hold.
- **Reproducibility grade for us:** **A**.
- **Replicable economic hypothesis:** Crypto volatility and volume follow stable day-of-week, hour-of-day and within-hour cycles that have strengthened over time and cluster around futures funding settlement times.

---

**id:** `brauneis-mestel-theissen-2025-tea-time`

- **Citation:** Brauneis, A., Mestel, R., Theissen, E. (2025). "The crypto world trades at tea time: intraday evidence from centralized exchanges across the globe." *Review of Quantitative Finance and Accounting* 64(1), 275–304 (January 2025).
- **DOI / permanent URL:** https://doi.org/10.1007/s11156-024-01304-1
- **Peer-review status:** Peer-reviewed.
- **Asset / market / venue / instrument:** **1,940 currency pairs on 38 cryptocurrency exchanges** across five continents. Spot.
- **Sample period and frequency:** Intraday. Exact dates **not verified**.
- **Variables used:** Trading activity, volatility, liquidity measures; exchange location; pair characteristics.
- **Predictive target:** Intraday levels of activity/volatility/illiquidity (**not returns**).
- **Model or rules:** Descriptive intraday pattern estimation plus cross-sectional explanation of commonality.
- **Temporal validation method:** None (descriptive).
- **Costs / slippage / funding modelled:** Not applicable.
- **Reported return / Sharpe / drawdown:** **None.** Headline: trading activity, volatility and illiquidity all peak between **16:00 and 17:00 UTC**, and the pattern is remarkably similar across exchanges, time zones and pairs.
- **Benchmark:** Cross-exchange comparison.
- **Number of variants tested:** Not verified.
- **Multiple-testing correction:** Not verified.
- **Code / data availability:** Not verified.
- **Possible leaks or weaknesses (specific):** Purely descriptive; establishes a *liquidity/volatility* clock, not a return anomaly. Exchange characteristics explain "some, but not all" of the commonality — so the mechanism is not pinned down.
- **Compatibility with BTCUSDT/ETHUSDT perpetuals:** High. 16:00 UTC coincides with a Binance funding settlement and with the US equity session, which is a useful confound to disentangle.
- **Reproducibility grade for us:** **A**.
- **Replicable economic hypothesis:** Despite 24/7 operation, crypto liquidity and volatility peak during the European–US overlap, so execution costs are time-of-day dependent.

---

**id:** `baur-cahill-godfrey-liu-2019-time-of-day`

- **Citation:** Baur, D.G., Cahill, D., Godfrey, K., Liu, Z. (2019). "Bitcoin time-of-day, day-of-week and month-of-year effects in returns and trading volume." *Finance Research Letters* 31, 78–92.
- **DOI / permanent URL:** https://doi.org/10.1016/j.frl.2019.04.023 (SSRN preprint: https://doi.org/10.2139/ssrn.3088472)
- **Peer-review status:** Peer-reviewed.
- **Asset / market / venue / instrument:** Bitcoin spot on **seven global, continuously traded exchanges**.
- **Sample period and frequency:** More than **15 million observations**; intraday. Exact dates **not verified**.
- **Variables used:** Calendar dummies (time-of-day, day-of-week, month-of-year); returns; trading volume.
- **Predictive target:** Returns **and** trading volume.
- **Model or rules:** Calendar-anomaly regressions.
- **Temporal validation method:** Cross-exchange and cross-time consistency checks (the paper's central discipline).
- **Costs / slippage / funding modelled:** Not applicable.
- **Reported return / Sharpe / drawdown:** **None.** The key finding is deliberately deflationary: **time-specific anomalies exist in returns but are NOT persistent across time**, whereas differences in trading *activity* are persistent across all exchanges (lower during local evening hours and at weekends).
- **Benchmark:** Cross-exchange replication.
- **Number of variants tested:** 24 hours × 7 days × 12 months × 7 exchanges × 2 targets — a very large implicit family.
- **Multiple-testing correction:** Not verified. The authors instead use cross-exchange and cross-period persistence as the robustness filter, which is arguably the better test.
- **Code / data availability:** Not verified.
- **Possible leaks or weaknesses (specific):** None material for our purposes; this is a negative result and negative results are less prone to selection bias. Sample predates 2020.
- **Compatibility with BTCUSDT/ETHUSDT perpetuals:** High — and it is the single most important caution for Domain 5.
- **Reproducibility grade for us:** **A**.
- **Replicable economic hypothesis:** Calendar effects in Bitcoin *volume* are stable, but calendar effects in Bitcoin *returns* are not, so time-of-day return anomalies discovered in one period should not be expected to survive into the next.

---

## 2. Papers reporting a positive Sharpe ratio — critical evaluation

Only three of the fourteen papers report a Sharpe ratio at all. This is itself informative:
the attention, sentiment and macro literature overwhelmingly reports *statistical
significance*, not *performance*, and cannot be used to justify a data purchase.

| Paper | Reported Sharpe | Verdict |
|---|---|---|
| Grobys, Näsman & Sandretto (2026) | 1.28 (MVRV Z) vs 0.45 buy-and-hold | Not usable |
| Christin, Routledge, Soska & Zetlin-Jones | 12.8 and 7.0 (BTC perp contracts, annualised, in-sample) | Not achievable as stated |
| Schmeling, Schrimpf & Todorov | Sharpe not verified; carry ~7% p.a. average, >40% p.a. peaks | Usable as a constraint, not a strategy |

**Grobys, Näsman & Sandretto (2026), Sharpe 1.28.** The comparison to buy-and-hold at 0.45 is
apples-to-oranges: the strategy sits in cash for long stretches, so it is a lower-exposure
portfolio and its Sharpe is mechanically flattered. The effective sample is a handful of
trades over three cycles, and no test of the difference between 1.28 and 0.45 is reported —
even though the paper's own reference list includes Opdyke (2007), "Comparing Sharpe ratios:
So where are the p-values?". Exits are anchored to cycle peaks that are only identifiable ex
post. Transaction costs appear only in an unreported footnote. Finally, and decisively for
us, the on-chain inputs are almost certainly retroactively revised vendor series (§3.1). The
result is interesting as behavioural evidence and inadmissible as strategy evidence.

**Christin et al., Sharpe 12.8 / 7.0.** These are the highest Sharpe numbers in this review
and the paper is transparent that they exclude margin, leverage, transaction costs and
liquidation. Three independent reasons to discount them: (i) the trade needs a spot leg
funded and margined separately, and Schmeling et al. show that at 10× leverage the futures
leg of the analogous trade would have been liquidated in **more than half the months** of a
2019–2024 sample; (ii) the sample is 22 months (Aug 2020 – Jun 2022) spanning one boom and
one bust, and includes the pre-July-2021 period when Binance still allowed 125× leverage — a
regime that no longer exists, and whose removal the authors themselves associate with a drop
in carry returns; (iii) Tether settlement risk is acknowledged and not priced. The *economic
mechanism* (longs pay for leverage) is real and is visible in our own funding-rate history.
The Sharpe is not.

**Schmeling, Schrimpf & Todorov.** This is the most rigorous of the three and it is the one
that argues *against* naive carry harvesting. It quantifies why the trade is not free: the
futures leg is liquidation-prone under realistic leverage, arbitrage capital is constrained
by regulation and margin, and carry itself predicts short-side liquidations. It also shows
that the retail-attention proxy (Google Trends) explains 12% of carry variation on an
unregulated venue but only 1% on the CME — which is a clean statement that the phenomenon is
a retail-leverage phenomenon, not a macro one.

**What no paper in this review demonstrates:** a cost-aware, walk-forward-validated,
multiple-testing-corrected, directional intraday strategy on BTC/ETH perpetuals driven by
on-chain, sentiment or macro inputs. Not one.

---

## 3. Data acquisition assessment

### 3.1 Domain 1 — On-chain

The central finding of this review is here, and it is documented by the vendors themselves.

Glassnode's own research states that **address clustering forces full historical
recomputation** of affected metrics: "As new addresses of a cluster are detected, the newly
acquired clustering data makes it necessary to refresh the full historic data of a metric",
and manual label additions can trigger recomputation "potentially reaching back the entire
history". They quantify the consequence for state-based metrics: for BTC Illiquid Supply,
"the values for the last ~30 days in the metric are still subject to change by more than one
percent", and they cite an independent analysis concluding that most changes occur in the
first three months while full convergence takes about four years. Activity-based clustering
metrics converge faster, in roughly two hours. Glassnode explicitly frames this as
look-ahead bias, citing Luo et al.'s "Seven sins of quantitative investing", and states:
"All systematic use cases (e.g. algorithmic trading, quantitative models, historical
backtesting) **should rely on PIT metrics** for historical data."

The problem for us is the **start date of PIT history**. Glassnode's documentation states
that PIT history "is only available from the exact date we began tracking it for a given
metric": before July 2025 PIT tracking was limited to BTC, ETH and select tokens on a
specific metric list; the platform-wide expansion began **27 June 2025**; the `computed_at`
field has been recorded only since September 2024. There is therefore **no point-in-time
on-chain history for 2020–2024** — the period that constitutes most of our sample. Buying
Glassnode Professional would not fix this, because the vintages simply were not recorded.

Coin Metrics documents the same class of problem from a different angle. Their FAQ defines
look-ahead bias, distinguishes `time` (exchange event time) from `collect_time` (websocket
receipt) and `database_time` (persisted to their DB), and states the rule directly: "A
point-in-time-correct backtest for decision time T admits only observations whose collection
timestamp is at or before T, not those whose `time` is at or before T. The difference
between the two is exactly the window in which look-ahead bias hides." They also flag
backfilled market history, retroactive reference-data changes, reference-rate/index
revisions under a published revision policy, and derived metrics that inherit upstream
delays. On methodology: exchange flows use the common-input-ownership heuristic, which
"requires at least one seed address for every exchange, limiting coverage to a predetermined
universe" and "is broken by CoinJoins and peeling chains"; miner flows use a hop-distance
heuristic which is "less precise". A Coin Metrics methodology PDF states they avoid entity
clustering for adjusted-volume metrics because "it can introduce subjectivity to the data",
while their wallet-metrics documentation states wallets are grouped using "a clustering
methodology based on well-established industry standards" — these are different metric
families, but the tension should be checked before relying on either.

| Question | Answer |
|---|---|
| Free/affordable source with genuine intraday history back to 2020? | Partially. CryptoQuant's BTC exchange-flow API documents `window` values of `day`, `hour` and `block`, and API access requires a Professional or Premium subscription. Glassnode offers up to 10-minute resolution on the Professional plan. Coin Metrics Community is daily. So intraday history *exists* commercially. |
| Point-in-time or restated? | **Restated.** Vendor-documented full-history recomputation on clustering/label updates. PIT variants exist at Glassnode but their history starts ~Sept 2024 / June 2025, not 2020. |
| Licence for academic use | Glassnode Advanced ($49/mo) is **Personal Use** licence, no redistribution, no API beyond a 14-day/daily/50-calls-per-day Light API. Commercial use and redistribution require Professional (custom terms). Academic licences are not advertised; sales contact required. |
| Realistic cost | Glassnode Advanced **$49/mo** (verified on Glassnode's pricing page) but useless for us (24h resolution, 4 years, no API, no PIT). Glassnode Professional: **"Contact Sales"** — the widely quoted $999/mo figure comes from a third-party aggregator and is **not verified**. CryptoQuant tiers quoted by a third-party aggregator as Free / $29 / $99 / $699 per month — **not verified** against CryptoQuant's own pricing page, which is JavaScript-rendered and could not be read. |
| Coverage and gaps | Exchange-flow coverage is bounded by the vendor's labelled-address universe and degrades with CoinJoin/peeling-chain usage. Miner-flow heuristics are explicitly lower precision. Neither vendor claims completeness. |
| Could a backtest be honestly claimed leak-free? | **No**, not for 2020–2024. Any 2020–2026 on-chain backtest would silently consume 2025-vintage clustering knowledge applied to 2021 timestamps. |

### 3.2 Domain 2 — Attention, sentiment and news

Google's own Trends FAQ is unambiguous that the series is not a measurement: it is "a largely
unfiltered **sample** of actual search requests"; each point is "divided by the total searches
of the geography and time range it represents" and then "scaled on a range of 0 to 100";
low-volume terms are reported as 0; duplicate searches from the same person are removed;
queries with special characters are filtered; searches made by Google's own products
"including internal searches made by AI Mode and AI Overviews" are excluded. Critically:
"To protect your privacy, we incorporate **statistical noise** that includes small and random
fluctuations that don't represent actual search behavior." And on granularity and time zone:
ranges of 30 days or longer are returned in UTC at daily-or-coarser granularity, while ranges
of **7 days or shorter** — the only way to get sub-daily data — are returned in **the
browser's local time zone**.

The consequences for us are severe and compound: (a) hourly data can only be obtained in
7-day windows, so a 2020–2026 hourly series must be stitched from ~320 separately-rescaled
windows, each with its own 0–100 normalisation; (b) each window's values depend on which
sample Google drew that day, so re-downloading produces different numbers; (c) the local-
time-zone behaviour for short ranges is a silent timestamp-alignment trap against our UTC
bars; (d) injected statistical noise means the series is not even deterministic. There is no
vintage archive. A Google Trends backtest is **not reproducible and not point-in-time**, and
saying otherwise in a thesis would be false.

The Crypto Fear & Greed Index (alternative.me) is free, has a documented REST endpoint
(`https://api.alternative.me/fng/`, `limit=0` returns all history), and permits commercial
use with attribution. But it is **daily**, and its published composition — volatility 25%,
market momentum/volume 25%, social media 15%, surveys 15% **"currently paused"**, dominance
10%, trends 10% — means (i) the methodology has changed over time, (ii) 50% of the index is
computed from price/volume/dominance we can already compute ourselves, and (iii) 10% is
Google Trends, inheriting every problem above. It is a derived, non-versioned composite.

X/Twitter historical access could **not be verified** in this session: `developer.x.com` and
`docs.x.com` both returned HTTP 403. I will not state pricing or availability I could not
read. What can be said from the peer-reviewed record is that Guégan & Renault's intraday
result used **StockTwits**, not Twitter, and that their own conclusion is that the effect is
too small to overcome transaction costs.

| Question | Answer |
|---|---|
| Free/affordable intraday history to 2020? | Google Trends: hourly only in 7-day windows, must be stitched, free. Fear & Greed: free but daily. X/Twitter archive: **not verified**. News sentiment vendors: not investigated. |
| Point-in-time or restated? | **Neither, and worse than restated.** Google Trends is re-sampled and noise-injected on every download; there are no vintages. Fear & Greed's composition has changed (surveys paused). |
| Licence for academic use | Google Trends: no bulk/API licence for research verified. Fear & Greed: free, commercial use allowed **with prominent attribution**, no impersonation. |
| Realistic cost | €0 for Google Trends and Fear & Greed; unknown for X/Twitter and news vendors. The real cost is engineering time on a stitching pipeline that still would not be PIT. |
| Coverage and gaps | Google Trends returns 0 for low-volume terms, so keyword choice silently changes coverage. Fear & Greed starts in 2018 (earliest date **not verified**). |
| Could a backtest be honestly claimed leak-free? | **No** for Google Trends. **Marginally, with caveats** for Fear & Greed, but only at daily frequency and only if we accept a composite whose recipe changed mid-sample. |

### 3.3 Domain 3 — Macro, point-in-time

This is the one domain where genuine point-in-time infrastructure exists and is free.
ALFRED (Archival FRED, St. Louis Fed) states plainly: "ALFRED allows you to retrieve each
economic data release (**vintage**) that was available on a specific date in history",
covering releases since 2006. That is exactly the vintage discipline the on-chain vendors
cannot offer for our window.

The problem is not integrity — it is relevance and frequency. Macro series are daily at best
and mostly monthly/quarterly, with publication lags of weeks. Market-based macro proxies
(DXY, VIX, equity indices) are higher-frequency but are **not on FRED at intraday
granularity for free**, and they stop trading at night and at weekends while our perpetuals
do not. And the two most relevant papers disagree about whether the effect exists at all:
Benigno & Rosa (2023) find Bitcoin **orthogonal** to macro and monetary news over 2017–2022,
while Karau (2023) finds a response emerging **after late 2020** — and Karau's clearest
result is about *volatility*, not direction.

| Question | Answer |
|---|---|
| Free/affordable intraday history to 2020? | **No** for intraday. FRED/ALFRED are free but the series we would want intraday (DXY, VIX, S&P) are not available intraday there. |
| Point-in-time or restated? | **Genuinely point-in-time** via ALFRED vintages — the best PIT story of any domain here. |
| Licence for academic use | FRED/ALFRED are public, free, US federal-government-adjacent data. No barrier. |
| Realistic cost | €0 for FRED/ALFRED. Intraday DXY/VIX/futures data would need a commercial vendor (cost not investigated). |
| Coverage and gaps | Macro series have publication lags and are not defined outside business hours; crypto trades 24/7 including weekends and holidays, so the series is missing for a large fraction of our bars. |
| Could a backtest be honestly claimed leak-free? | **Yes, in principle**, using ALFRED vintages — but only at daily-or-coarser frequency, which is the wrong frequency for us. |

### 3.4 Domain 4 — Scheduled events with advance, verifiable timestamps

This domain is different in kind, because the *data* is a calendar, not a measurement. FOMC
meeting dates and CPI release dates and times are published months in advance and are
historically verifiable; funding settlement times on Binance are contractual. There is no
revision, no sampling, no clustering heuristic and no vendor.

We already hold the two most valuable event series in this domain: **funding-rate history**
(which gives us the exact settlement timestamps *and* the realised rate) and **5-minute
klines** around them. Christin et al. establish that Binance transfers funding every eight
hours, and Hansen, Kim & Kim independently attribute part of the observed intraday
periodicity to "funding times in futures markets". A non-peer-reviewed research PDF
(resistance.money) reports the specific settlement clock as 00:00 / 08:00 / 16:00 UTC for
Binance and Bybit and documents volume spikes in the first five minutes of those hours; I
could not confirm the exact UTC times from Binance's own FAQ, which blocks automated
retrieval. **This must be verified directly against our own funding-rate table before it is
asserted in the thesis** — and it is trivially verifiable from data we already own.

Exchange listings and index rebalances are a different story. The listing-effect evidence I
found is almost entirely **industry analysis, not peer-reviewed research** (Ren & Heinrich,
Animoca Research, The Big Whale, RockawayX, CoinDesk), the estimates conflict violently
(+41% day-1 vs a −50% median), and — decisively — the effect concerns *newly listed altcoins*,
not BTCUSDT/ETHUSDT perpetuals that have been listed since 2019/2020. Options expiries on
Deribit would require options data we do not have.

| Question | Answer |
|---|---|
| Free/affordable intraday history to 2020? | **Yes, and we already own most of it.** Funding timestamps and rates are in our dataset. FOMC/CPI calendars are public. |
| Point-in-time or restated? | **Point-in-time by construction.** A scheduled announcement date known in advance cannot be revised into existence. Funding rates settle and are final. |
| Licence for academic use | No licence issue for public calendars. Binance data is already under whatever terms we ingested it. |
| Realistic cost | €0 for FOMC/CPI calendars and funding. Options-expiry data: not investigated. Listing announcements: would require scraping Binance's announcement archive, with a real risk of an incomplete/retroactively edited archive. |
| Coverage and gaps | FOMC ~8 meetings/year, CPI ~12/year → roughly 20 events/year, ~120 events over 2020–2026. That is a small event sample for 5-minute inference. Funding settlements: ~3/day × ~2,100 days × 2 symbols ≈ 12,600 events — a genuinely large sample. |
| Could a backtest be honestly claimed leak-free? | **Yes** for funding-settlement and macro-calendar events. **No** for listings without a verified, immutable announcement archive. |

### 3.5 Domain 5 — Intraday periodicity

No external data at all is required. Time-of-day, day-of-week and within-hour features are
deterministic functions of the bar's own UTC open time, which we already have and which the
project already treats as tz-aware UTC, left-closed, labelled by open time.

| Question | Answer |
|---|---|
| Free/affordable intraday history to 2020? | **Already owned.** Zero marginal data. |
| Point-in-time or restated? | **Point-in-time by construction** — a calendar cannot be revised. |
| Licence for academic use | None required. |
| Realistic cost | €0. |
| Coverage and gaps | None. Every bar has a timestamp. |
| Could a backtest be honestly claimed leak-free? | **Yes** — provided the periodic effect is *estimated* causally (rolling/expanding windows, never full-sample hour-of-day means used as a decision input) and the multiple-testing problem of 24 hours × 7 days is handled explicitly. |

---

## 4. Verdict for our project

### Domain 1 — On-chain: **DECLARE OUT OF SCOPE**

This is not a close call. The vendors themselves document that on-chain metrics are
retroactively recomputed across their entire history whenever address clustering or entity
labelling improves, and that this is a look-ahead bias. The one clean remedy — point-in-time
vintages — did not begin being recorded until roughly September 2024 for a narrow metric set
and 27 June 2025 platform-wide. Our sample starts in 2020. **The vintages we would need do
not exist and cannot be bought at any price.** Any on-chain backtest over 2020–2026 would be
consuming 2026-vintage clustering knowledge applied to 2021 decisions, and we would have no
way to bound the size of the resulting bias.

On top of that, the literature does not motivate the purchase: the best peer-reviewed
on-chain result available (Grobys et al. 2026) is a daily, cycle-horizon, long-only spot
strategy with a handful of trades, and the best multiple-testing-corrected on-chain factor
result (Sakkas & Urquhart 2024) explicitly finds that BTC and ETH are *never* in the
high-premium tercile. Neither is compatible with 5-minute perpetuals.

**Recommended thesis language:** declare the domain unavailable on point-in-time grounds,
cite the Glassnode PIT documentation and the Coin Metrics look-ahead FAQ, and state that the
project preferred to exclude a data source rather than run a backtest on restated data. That
is a defensible and, frankly, publishable methodological position.

### Domain 2 — Attention and sentiment: **DECLARE OUT OF SCOPE**

Google Trends fails on reproducibility before it even reaches point-in-time: it is a sampled,
rescaled, noise-injected index with no vintage archive, whose only sub-daily granularity
comes in 7-day windows returned in the *local* time zone. Two downloads a week apart give
different numbers. We could not honestly write "reproducible" next to a Google Trends
backtest.

Social-media sentiment fails on data availability (X/Twitter historical access could not be
verified; StockTwits archive availability not verified) and, more importantly, on the
literature's own verdict: Guégan & Renault find statistically significant intraday
predictability up to 15 minutes with an R² of 0.027% at 5-minute frequency and coefficients
of 0.0035%–0.0087%, and conclude the effect cannot cover transaction costs. Our provisional
cost assumptions are already documented in ADR 0005; the reported effect is an order of
magnitude below any plausible round-trip.

The Fear & Greed index is the only cheap, licensable option, and it is daily, half-composed
of price/volume/dominance we can compute ourselves, 10% Google Trends, and its recipe has
changed mid-sample (surveys "currently paused"). Not worth the integrity risk for a daily
feature.

### Domain 3 — Macro point-in-time: **OUT OF SCOPE for features; IN SCOPE as a cited prior**

ALFRED gives us genuine vintages for free, so this domain is the one where the integrity
story would be clean. But the frequency is wrong (daily at best, publication lags of weeks),
the intraday market proxies are not free, and the series are undefined for the nights and
weekends during which our perpetuals keep trading. And the two best-identified studies
disagree: Benigno & Rosa find Bitcoin **orthogonal** to macro news 2017–2022; Karau finds a
response only **after late 2020**, and mostly in volatility rather than direction.

Spending licence money and pipeline effort on intraday DXY/VIX to chase an effect that a New
York Fed staff report says is absent and a JIMF article says is unstable, at a frequency
where the paper that finds it reports volatility rather than returns, is not a good trade.

**Keep the calendar, drop the levels.** See Domain 4.

### Domain 4 — Scheduled events: **PURSUE NOW, narrowly**

This is the one domain that is worth doing, and most of it costs nothing because we already
own the data.

- **Funding settlement events: pursue.** We hold the funding-rate history and 5-minute
  klines. Funding timestamps are contractual, known in advance, and final — point-in-time by
  construction. Hansen, Kim & Kim attribute part of the documented intraday periodicity to
  futures funding times; Christin et al. show on Binance, over a window overlapping ours,
  that the funding cash-flow is economically large. We can study perpetual return, volume and
  volatility behaviour around settlement with ~12,600 events across BTCUSDT and ETHUSDT, with
  zero new data, zero licence, and no PIT risk. **First action: verify the actual settlement
  clock empirically from our own funding table rather than trusting any secondary source.**
- **Funding rate as a causal feature: pursue.** The realised rate at settlement *t* is known
  at *t* and can lawfully condition a decision at *t+1*. This is a genuinely exogenous-ish
  variable we already own and have not exploited.
- **FOMC/CPI calendar dummies: pursue cautiously.** Timestamps are public and verifiable in
  advance. But with ~120 events over 2020–2026 the sample is thin for 5-minute inference, the
  expected effect is on volatility rather than direction, and the two headline papers
  disagree. Treat as a low-priority robustness/regime feature, pre-registered, not as a
  strategy family.
- **Exchange listings, index rebalances, options expiries: out of scope.** The listing
  evidence is industry analysis with wildly conflicting estimates and concerns newly listed
  altcoins, not BTC/ETH perpetuals. Options expiry needs Deribit data we do not have.

### Domain 5 — Intraday periodicity: **PURSUE NOW**

Zero data cost, zero licence, zero point-in-time risk. Time-of-day and day-of-week are
deterministic functions of a timestamp we already have.

But pursue it with the discipline the literature demands, not the enthusiasm the headlines
invite. Baur, Cahill, Godfrey & Liu (2019), using more than 15 million observations across
seven exchanges, found time-specific anomalies in **returns** that were **not persistent
across time**, while finding persistent patterns in **volume**. Hansen, Kim & Kim (2024) and
Brauneis, Mestel & Theissen (2025) both document strong and strengthening periodicity — again
in **volatility, volume and liquidity**, not returns. The honest prior is therefore:

- Periodicity in **volatility and liquidity** is real, replicated across venues and periods,
  and should be used — for volatility scaling, for cost modelling, and as a regime/conditioning
  variable.
- Periodicity in **returns** is the classic overfitting trap. Twenty-four hour-of-day dummies
  × seven day-of-week dummies × two assets is a large implicit family, and Baur et al. is
  direct evidence that the survivors do not persist. Any return-based time-of-day rule must
  be pre-registered, walk-forward validated, and multiple-testing corrected, and we should
  expect it to fail.

The 16:00–17:00 UTC peak documented by Brauneis et al. coincides with both a Binance funding
settlement and the US equity session, so Domains 4 and 5 are confounded and must be
disentangled rather than treated as independent evidence.

### Summary

| Domain | Verdict | Reason in one line |
|---|---|---|
| 1. On-chain | **Out of scope** | Point-in-time vintages for 2020–2024 do not exist and cannot be purchased |
| 2. Attention / sentiment | **Out of scope** | Google Trends is not even reproducible, let alone point-in-time; sentiment effects are smaller than costs |
| 3. Macro | **Out of scope as features** | Clean vintages (ALFRED) but wrong frequency; the two best studies disagree on whether the effect exists |
| 4. Scheduled events | **Pursue (funding first)** | Timestamps known in advance, data already owned, ~12,600 funding events, zero PIT risk |
| 5. Intraday periodicity | **Pursue (volatility/liquidity first)** | Free and PIT by construction, but return-based calendar effects are documented as non-persistent |

**Net recommendation: ingest nothing new.** Both domains worth pursuing are already fully
covered by the Binance perpetual klines, mark-price klines and funding-rate history we hold.

---

## 5. What could not be verified

Stated explicitly so that no reader mistakes a gap for a fact.

- **Sample periods** for Sakkas & Urquhart (2024), Kristoufek (2013), Hudson & Urquhart (2021),
  Hansen, Kim & Kim (2024), Brauneis, Mestel & Theissen (2025) and Baur et al. (2019). Only
  abstracts, repository records and citing reference lists were read for these.
- **Exact performance figures** (Sharpe, drawdown, returns) for Sakkas & Urquhart (2024),
  Hudson & Urquhart (2021) and Schmeling, Schrimpf & Todorov.
- **Volume/issue** for Guégan & Renault; only the article number (101494), DOI and online
  publication date were confirmed.
- **Year and publication venue** of the retrieved version of Christin, Routledge, Soska &
  Zetlin-Jones. The PDF is v1.0 hosted at CMU; Schmeling et al. cite it as "(2022)".
- **Kristoufek (2013)** full text was not retrieved; its citation and DOI were confirmed only
  via the reference lists of three other papers read in full.
- **X/Twitter API pricing, tiers and historical-archive availability in 2026.**
  `developer.x.com` and `docs.x.com` both returned HTTP 403.
- **CryptoQuant pricing.** Their pricing page is JavaScript-rendered and returned no content.
  The tier figures quoted in §3.1 come from a third-party aggregator and are flagged as
  unverified. There is also an unresolved contradiction between CryptoQuant's user guide
  (which documents `window=hour` and `window=block` for BTC exchange flows) and the
  third-party claim that the Professional API is limited to 24-hour resolution.
- **Glassnode Professional price.** Glassnode's own pricing page says "Contact Sales". The
  $999/mo figure circulating on aggregator sites is unverified.
- **Binance's official funding settlement times (00:00/08:00/16:00 UTC).** Binance's own FAQ
  blocks automated retrieval. The 8-hour cadence is confirmed by Christin et al. and by
  Schmeling et al.; the specific UTC hours come from a non-peer-reviewed research PDF and
  must be confirmed against our own funding-rate table.
- **Fear & Greed index start date** and whether historical values were ever recomputed after
  the surveys component was paused.
- **Options-expiry and index-rebalance literature** was not systematically searched; the
  domain was ruled out on data-availability grounds (no options data) rather than on
  evidence.
- The GitHub repositories surfaced by search (`Adeline117/Reproducing-Quantitative-Research`,
  `Kaleb0719/funding-timestamp-event-study`, `kimlage/crypto-edge-search`) and the industry
  listing analyses (Ren & Heinrich, Animoca Research, The Big Whale, RockawayX) are **not
  peer-reviewed** and are cited above only as caution flags, never as evidence.
