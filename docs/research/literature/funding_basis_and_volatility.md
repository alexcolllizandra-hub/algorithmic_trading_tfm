# Literature evidence matrix: perpetual funding, basis, dislocation, liquidations, volatility & regimes

**Scope of verification.** Every DOI/URL below was opened during this review unless the field says "not verified". Where a page was blocked (binance.com serves a JS/robot wall to non-browser clients) I say so and name the mirror or secondary source I actually read. Reported numbers are transcribed from the document text I read; numbers I could not locate in the source are marked "not verified".

**One correction to your stated data constraint, verified against Binance's own S3 bucket** (this changes several "not implementable" verdicts): listing `data/futures/um/daily/` on `data.binance.vision` returns `aggTrades, bookDepth, bookTicker, indexPriceKlines, klines, markPriceKlines, metrics, premiumIndexKlines, trades`. The `metrics/BTCUSDT/` prefix has daily files from **2020-09-01** onward (~12 KB/day, consistent with 288 five-minute rows), and Binance's own issue tracker (`binance/binance-public-data` issue #276) confirms those files carry `sum_open_interest` and `sum_open_interest_value`. So **open-interest history at 5 min IS in the bulk archive**, as are the **premium index** and the **spot index price**. Column names come from the issue thread plus a third-party schema, not from a file I downloaded — verify by unzipping one day before relying on it.

---

## Evidence matrix

### 1. `he2024-perp-noarb`

- **citation**: Songrun He, Asaf Manela, Omri Ross, Victor von Wachter (2024). *Fundamentals of Perpetual Futures*. Working paper (first draft Dec 2022; draft read: v6, July 2024 text).
- **DOI / URL**: [arXiv:2212.06888](https://arxiv.org/abs/2212.06888); [10.2139/ssrn.4301150](https://doi.org/10.2139/ssrn.4301150)
- **peer-review status**: Preprint / working paper. I searched for a journal version and found none; treat as **not peer-reviewed**.
- **asset / market / venue / instrument**: BTC, ETH, BNB, DOGE, ADA; Binance; USDT perpetual futures **and** Binance spot.
- **sample period and frequency**: Hourly. BTC and ETH **2020-01-08 → 2024-03-11** (36,578 hourly obs); BNB from 2020-02-10; DOGE from 2020-07-10; ADA from 2020-01-31.
- **variables used**: Perpetual price, spot price, realized 8-hour funding rate, Binance maker fee tiers, borrow/lend rates. One month of Kaiko 30-second order-book snapshots used only to bound indirect costs.
- **predictive target**: Convergence of the perpetual-to-spot deviation ρ toward the theoretical no-arbitrage level; not a return forecast.
- **model or trading rules**: Random-maturity no-arbitrage bound \(F_t = \frac{\kappa}{\kappa-(r-r')}S_t\) with \(\kappa = 3\times365 = 1095\). Open the spot/perp pair when the deviation exceeds the cost-adjusted bound; close when it returns inside the zero-cost relation.
- **temporal validation**: **None in the walk-forward sense.** A fixed threshold rule applied over the whole sample; no train/test split, no parameter re-estimation. Year-by-year performance is reported, which is a weak substitute.
- **costs modelled**: Yes, explicitly and well. Maker fees by tier: spot/futures = 2.25/0.18 bps (low), 4.5/0.72 (medium), 6.75/1.44 (high). Bid-ask spread estimated < 0.05 bps and impact < 0.3 bps for a \$0.5M trade, so indirect costs are argued to be second-order. Funding is the mechanism, not a cost.
- **reported return / Sharpe / drawdown**: BTC, unrestricted, **high**-cost tier, full sample: **SR 1.80**, return 6.38%, volatility 3.55%, MaxDD −4.43%, active 20.06% of hours, mean open-to-close 134.94 h. By year, BTC SR = 2.26 (2020), 2.39 (2021), **0.70 (2022)**, 1.32 (2023), 11.52 (2024 partial). ETH full sample SR 2.55. With **zero** trading costs, BTC SR **6.72** and "above 10" for the other four coins. Sharpe annualization follows Lucca–Moench scaling for a sometimes-inactive strategy.
- **benchmark**: Liu–Tsyvinski–Wu 3-factor and Cong et al. 5-factor alphas (reported significant).
- **number of variants tested**: Small and disclosed: 3 cost tiers × {unrestricted, long-spot-only} × 5 coins, plus a zero-cost case.
- **multiple-testing correction**: None. Newey-West adjusted p-values are used for the ρ means, not for strategy selection.
- **code/data availability**: Not verified.
- **possible leaks / weaknesses**: (i) The κ = 1095 constant assumes funding is proportional to the spread and paid every 8 h; Binance's actual rule has a ±0.05% clamp, a time-weighted premium average, an order-book impact-price input, and a cap/floor — the authors acknowledge all four in a footnote, so ρ is a proxy, not the funding rate. (ii) The strategy is a **two-legged spot+perp trade on one venue**; the headline Sharpe is a low-volatility carry-like series, so the SR is high while the *return* is 6.38%/yr — do not read SR 1.8 as "big money". (iii) Its 2022 collapse to SR 0.70 is exactly the regime a thesis must survive. (iv) Deviations "diminish over time" (~11%/yr), i.e. the edge is decaying by the authors' own estimate. (v) Threshold and exit rule are chosen with full-sample knowledge.
- **compatibility with BTCUSDT/ETHUSDT perps**: Same venue, same instruments, and the two headline assets. Highest compatibility of any paper here.
- **reproducibility grade for us**: **Medium.** The perp leg is fully in our data. The **spot leg is not** — and the strategy is defined by the spot–perp pair. We can reconstruct the *signal* (using `indexPriceKlines` as the spot proxy) but not the *trade*.
- **replicable economic hypothesis (one sentence)**: When the Binance perpetual price deviates from its index-anchored fundamental by more than round-trip costs, that deviation subsequently reverts, so the signed deviation predicts the sign of the perp's excess return over the index at horizons of hours to days.

### 2. `christin2023-crypto-carry-trade`

- **citation**: Nicolas Christin, Bryan R. Routledge, Kyle Soska, Ariel Zetlin-Jones (2023). *The Crypto Carry Trade*. Working paper dated 18 August 2023 (Carnegie Mellon; Ramiel Capital).
- **DOI / URL**: PDF read at `https://gerbil.life/papers/CarryTrade.v1.2.pdf`. **This is not a permanent archival URL** — a stable DOI/SSRN/NBER identifier was **not verified**. Cite with caution; the paper is referenced by BIS WP 1087 and by He et al. as "Christin et al. (2022)".
- **peer-review status**: Working paper, **not peer-reviewed**. Presented at NBER Big Data/HPC in Financial Economics, SED, and WFA per its own acknowledgements.
- **asset / market / venue / instrument**: 18 cryptocurrencies × 2 contract types = 36 contracts (USDT-margined and coin-margined perpetuals), **Binance**, plus Binance spot index prices.
- **sample period and frequency**: **2020-08-11 → 2023-06-23**. Minute data, analysed at the 8-hour funding period.
- **variables used**: Perpetual price, spot index price, realized funding rate, exchange leverage limits.
- **predictive target**: Realized return of a short-perp/long-spot carry position; not a directional price forecast.
- **model or trading rules**: Static: long 1 unit spot, short 1 unit perpetual, hold, collect funding. No signal, no timing.
- **temporal validation**: None (no signal to validate). Subsample splits by BTC up/down periods and around the July 2021 leverage cut, which is a genuine quasi-experiment.
- **costs modelled**: **Not verified that transaction costs are deducted** in the headline Sharpe. I found no fee schedule in the sections I read. Treat the Sharpe as **gross**.
- **reported return / Sharpe / drawdown**: Full-sample annualized **Sharpe 8.76** for the BTC Tether-denominated contract and **4.93** for the coin-denominated contract. Same-period benchmarks in the paper: long-BTC buy-and-hold SR **0.46**, US equities **0.33**. Sharpes are "much smaller" in the later subsample containing FTX. Max drawdown: **not verified**.
- **benchmark**: BTC buy-and-hold and US equities (above).
- **number of variants tested**: 36 contracts, no parameter search.
- **multiple-testing correction**: None (and it matters little — there is no parameter to tune).
- **code/data availability**: Not verified.
- **possible leaks / weaknesses**: (i) A Sharpe of 8.76 on a two-legged, high-leverage, single-venue position with **no cost accounting and no margin/liquidation modelling** is not an economically meaningful risk-adjusted return — it is a measure of how smooth a carry cash-flow is between blow-ups. (ii) The sample is heavily weighted to the 2020-21 leverage boom, i.e. the period the authors themselves identify as anomalous. (iii) Counterparty and stablecoin-peg risk (FTX, Terra, SVB all inside the sample) are the true left tail and are not priced. (iv) No holdout. (v) The economic interpretation (long side pays for leverage) is well supported and is the durable contribution — the Sharpe is not.
- **compatibility with BTCUSDT/ETHUSDT perps**: Direct — same venue, both instruments, funding-period frequency.
- **reproducibility grade for us**: **Low for the trade, High for the fact.** We cannot trade the spot leg. We *can* reproduce, exactly, the descriptive claim that Binance BTCUSDT/ETHUSDT funding is positive on average, from our funding history alone.
- **replicable economic hypothesis**: The average Binance perpetual funding rate is positive because levered-long demand persistently pays, so an unconditionally short-perp position earns a positive funding carry that is unrelated to the underlying's direction.

### 3. `schmeling2025-crypto-carry`

- **citation**: Maik Schmeling, Andreas Schrimpf, Karamfil Todorov (2025). *Crypto Carry*. **Management Science** (accepted by Agostino Capponi, finance). Earlier: BIS Working Paper 1087 (2023); CEPR DP 20719.
- **DOI / URL**: [10.1287/mnsc.2024.05069](https://doi.org/10.1287/mnsc.2024.05069); working-paper text read at [bis.org/publ/work1087.pdf](https://www.bis.org/publ/work1087.pdf)
- **peer-review status**: **Peer-reviewed**, top-5 business journal. The numbers below are transcribed from the BIS working-paper version, which may differ from the published version.
- **asset / market / venue / instrument**: BTC and ETH; **fixed-maturity (1-month and 3-month) futures**, not perpetuals; Binance, OKEx, FTX, Huobi, BitMEX, Deribit, CME. Plus Aave/Binance borrow rates, CFTC Commitments of Traders, Google Trends, options-implied vol.
- **sample period and frequency**: **Daily, March 2019 → July 2024** (CME basis starts Aug 2020; CME cash-and-carry analysis uses Bloomberg data from Jan 2018).
- **variables used**: Annualized constant-maturity futures basis, spot price, open interest, volume, buy/sell liquidations, borrow/lend rates, implied and realized vol, retail-proxy demand.
- **predictive target**: The level and time variation of carry; and carry as a predictor of future crash risk / price declines.
- **model or trading rules**: Panel regressions, variance decompositions, and two difference-in-differences designs (CME micro-futures introduction 2021; spot BTC ETF launch 2024). Cash-and-carry return accounting.
- **temporal validation**: Not a forecasting paper; identification comes from the DiD event structure, which is stronger than an out-of-sample split for the causal claims made.
- **costs modelled**: Margin and regulatory frictions are the *subject*; explicit per-trade slippage is not the focus.
- **reported return / Sharpe / drawdown**: Carry "sometimes exceeding **40% per annum**". Mean 1-month BTC basis ≈ **8%** on OKEx and **6.4%** on CME, maxima ≈ 55% and 45%. Futures-leg mean excess return on the basis trade **2–3% per month** with monthly volatility **≈17%**. Carry correlations across unregulated venues **>90%**; CME least correlated. Spot-ETF DiD: carry falls **≈3 pp** across exchanges and a further **≈5 pp** on CME (36% and 97% of mean carry). Sharpe ratio and drawdown: **not verified** (the paper reports moments, not a strategy Sharpe).
- **benchmark**: Traditional-asset futures returns via Heston–Todorov; commodity convenience-yield literature.
- **number of variants tested**: Many specifications, standard for the genre; disclosed in tables.
- **multiple-testing correction**: None reported; not a data-mining paper.
- **code/data availability**: Online appendix and data files stated to be available at the Management Science DOI. I did not open them.
- **possible leaks / weaknesses**: (i) **Fixed-maturity futures, not perpetuals** — the mechanism (convergence at expiry) is different from ours, and the authors say so explicitly. (ii) Data are vendor-aggregated ("Skew", Coinmetrics), i.e. not reconstructible from exchange primitives. (iii) Daily frequency — silent on intraday. (iv) Carry is **right-skewed**, which the authors flag as a large-drawdown risk for the arbitrageur; any thesis borrowing this logic must model that tail.
- **compatibility with BTCUSDT/ETHUSDT perps**: **Conceptual only.** Right assets, wrong instrument.
- **reproducibility grade for us**: **Low.** We have no fixed-maturity futures and no spot; and the DiD designs are not something a 5-minute intraday backtest can speak to.
- **replicable economic hypothesis**: Crypto carry is driven by levered retail demand meeting binding limits to arbitrage, so periods of high carry mark crowded long positioning and elevated subsequent crash risk rather than a risk-free yield.

### 4. `alexander2020-bitmex`

- **citation**: Carol Alexander, Jaehyuk Choi, Heungju Park, Sungbin Sohn (2020). *BitMEX bitcoin derivatives: Price discovery, informational efficiency, and hedging effectiveness*. **Journal of Futures Markets** 40(1), 23–43.
- **DOI / URL**: [10.1002/fut.22050](https://doi.org/10.1002/fut.22050)
- **peer-review status**: **Peer-reviewed.**
- **asset / market / venue / instrument**: BTC; BitMEX perpetual swap and futures vs major spot exchanges, CME/CBOE.
- **sample period and frequency**: Minute-by-minute. Exact dates **not verified** (abstract-level access only).
- **variables used**: Minute prices, bid-ask spreads, inter-exchange spreads, relative volumes.
- **predictive target**: Information share / price leadership, not tradable return.
- **model or trading rules**: Price-discovery econometrics (information shares, spillovers), hedge-ratio estimation. No trading strategy.
- **temporal validation**: Not applicable.
- **costs modelled**: Not applicable.
- **reported return / Sharpe / drawdown**: None (not a strategy paper). Reported findings: BitMEX derivatives **lead** major spot exchanges; spreads, inter-exchange spreads and relative volume explain price-discovery share; derivatives are informationally more efficient than spot and hedge spot vol effectively.
- **benchmark**: Spot exchanges, CME/CBOE futures.
- **number of variants tested**: Standard specification set.
- **multiple-testing correction**: Not applicable.
- **code/data availability**: Resampled minute series "available from the corresponding author on reasonable request".
- **possible leaks / weaknesses**: BitMEX 2018-19, an inverse coin-margined contract on a venue that has since collapsed in share — external validity to 2020s Binance USDT-M is an assumption, not a result. Price leadership is a statistical lead-lag, **not** an exploitable signal after costs, and the paper makes no such claim.
- **compatibility with BTCUSDT/ETHUSDT perps**: Medium — right instrument class, wrong venue/era, BTC only.
- **reproducibility grade for us**: **Low.** We have no spot series and no second venue, so we cannot compute information shares at all.
- **replicable economic hypothesis**: The perpetual swap, not spot, is where BTC price discovery happens, so perp-side order flow leads index moves at minute horizons.

### 5. `alexanderheck2020-pricediscovery`

- **citation**: Carol Alexander, Daniel F. Heck (2020). *Price discovery in Bitcoin: The impact of unregulated markets*. **Journal of Financial Stability** 50, 100776.
- **DOI / URL**: [10.1016/j.jfs.2020.100776](https://doi.org/10.1016/j.jfs.2020.100776)
- **peer-review status**: **Peer-reviewed.**
- **asset / market / venue / instrument**: BTC; **perpetual swaps** and futures on Huobi, OKEx, BitMEX; CME futures; Bitfinex/Bitstamp/Coinbase spot.
- **sample period and frequency**: Minute-level. Exact window **not verified**.
- **variables used**: Minute prices across ≥7 venues, multi-dimensional information flows.
- **predictive target**: Price-discovery leadership.
- **model or trading rules**: Multi-dimensional information-share estimation. No strategy.
- **temporal validation**: Not applicable.
- **costs modelled**: Not applicable.
- **reported return / Sharpe / drawdown**: None. Findings: perpetual swaps and futures on unregulated venues are "much the strongest instruments for bitcoin price discovery"; CME futures and US spot **react** rather than lead, sometimes slowly; in a multi-dimensional setting CME has "a very minor effect", less than Bitfinex/Bitstamp/Coinbase.
- **benchmark**: CME, regulated spot.
- **number of variants tested**: Not verified.
- **multiple-testing correction**: Not applicable.
- **code/data availability**: Not verified.
- **possible leaks / weaknesses**: Same era/venue caveat as row 4; conclusions about "unregulated venues lead" are partly a liquidity artefact and the paper's policy framing (SEC/ETF) is now dated. Being a price leader does **not** imply predictability of your own future price.
- **compatibility with BTCUSDT/ETHUSDT perps**: Medium-high conceptually (perpetual swaps are the leading instrument), low mechanically (not Binance, BTC only).
- **reproducibility grade for us**: **Low** (multi-venue data required).
- **replicable economic hypothesis**: Perpetual-swap prices on high-volume unregulated venues incorporate information first, so the index (a spot average) lags the perp — implying the perp-minus-index gap is partly *information*, not only *dislocation*.

### 6. `deblasis2022-perp-microstructure`

- **citation**: Riccardo De Blasis, Alexander Webb (2022). *Arbitrage, contract design, and market structure in Bitcoin futures markets*. **Journal of Futures Markets** 42(3), 492–524.
- **DOI / URL**: [10.1002/fut.22305](https://doi.org/10.1002/fut.22305)
- **peer-review status**: **Peer-reviewed.**
- **asset / market / venue / instrument**: BTC; **Binance** perpetual **and** quarterly futures. Keywords confirm: arbitrage, Binance, Bitcoin, cash-and-carry, perpetual futures.
- **sample period and frequency**: Intraday (hour-of-day analysis). Exact dates and bar size **not verified**.
- **variables used**: Intraday volume, volatility, prices of perpetual and quarterly contracts; basis.
- **predictive target**: Intraday patterns in volume/volatility; existence of cash-and-carry arbitrage.
- **model or trading rules**: Intraday seasonality estimation; spillover tests; arbitrage-bound accounting for quarterly futures.
- **temporal validation**: Not a forecasting paper.
- **costs modelled**: Arbitrage bounds are cost-aware; exact assumptions **not verified**.
- **reported return / Sharpe / drawdown**: None reported. Findings: Binance **perpetual futures exhibit multiple "u-shaped" intraday curves, seasonal effects, and "opening" effects despite having no open or close**; suggestive perpetual↔quarterly spillovers; quarterly futures offer cash-and-carry opportunities **primarily during market dislocations** (consistent with Hattori & Ishida 2021).
- **benchmark**: Quarterly futures; equity-market intraday stylized facts.
- **number of variants tested**: Not verified.
- **multiple-testing correction**: Not verified. Intraday-seasonality studies are highly exposed to hour-of-day multiplicity — treat any single significant hour sceptically.
- **code/data availability**: Not verified.
- **possible leaks / weaknesses**: BTC only; sample almost certainly ends 2021, before the 2022-25 regime changes and before Binance's 2025 funding-interval and mark-price rule changes. "Opening effects" in a 24/7 market invite a mechanical explanation (funding clock, Asian/US session overlap) that the paper labels but does not fully identify.
- **compatibility with BTCUSDT/ETHUSDT perps**: **High** — Binance USDT-M perpetual, intraday, which is exactly our instrument and frequency.
- **reproducibility grade for us**: **High.** Hour-of-day and funding-clock seasonality in volume, volatility, `trade_count` and taker-buy share is computable from our 5m klines alone, with no extra data.
- **replicable economic hypothesis**: Binance perpetual activity and volatility follow a stable time-of-day pattern anchored to session overlaps and the 8-hour funding clock, so hour-of-day is a legitimate conditioning variable for intraday strategies.

### 7. `frino2025-jury-out`

- **citation**: Alex Frino, Robert Gaudiosi, Robert I. Webb, Z. Ivy Zhou (2025). *Price discovery in Bitcoin spot or futures? The jury is out*. **Journal of Futures Markets** 45(4), 269–288.
- **DOI / URL**: DOI **not verified** (the publisher field was truncated on the pages I read). Permanent record: [Macquarie University research portal entry](https://researchers.mq.edu.au/en/publications/price-discovery-in-bitcoin-spot-or-futures-the-jury-is-out/), which states "Contribution to journal › Article › peer-review", vol. 45(4), 269–288.
- **peer-review status**: **Peer-reviewed** per the institutional record.
- **asset / market / venue / instrument**: BTC; regulated futures vs spot exchanges.
- **sample period and frequency**: **1-second** sampling. Dates **not verified**.
- **variables used**: 1-second prices; microstructure-noise adjustments; macro surprises; Tether-minting tweets.
- **predictive target**: Price-discovery share.
- **model or trading rules**: Information shares with explicit noise correction; sensitivity to measure, frequency, window, contract and spot venue choice.
- **temporal validation**: Not applicable.
- **costs modelled**: Not applicable.
- **reported return / Sharpe / drawdown**: None. Findings: futures generally lead spot, but leadership **fluctuates daily**, and prior contradictory results are explained by choices of price-discovery measure, sampling frequency, modelling window, contract and spot venue. Futures' share rises around macro surprises and Tether-minting tweets.
- **benchmark**: Prior literature's conflicting estimates.
- **number of variants tested**: Deliberately many — that is the point of the paper.
- **multiple-testing correction**: Not applicable; the paper is a robustness audit.
- **code/data availability**: Not verified.
- **possible leaks / weaknesses**: Regulated futures, not Binance perps. But the **methodological** lesson is the most transferable thing in this whole matrix: **the same data produce opposite lead-lag conclusions depending on sampling frequency and window**. Any dislocation signal we build at 5m must be shown to survive a frequency sweep.
- **compatibility with BTCUSDT/ETHUSDT perps**: Low mechanically, high methodologically.
- **reproducibility grade for us**: **Not applicable** (needs 1-second multi-venue data).
- **replicable economic hypothesis**: Lead-lag and dislocation estimates are sampling-frequency artefacts unless demonstrated to be invariant across frequencies and windows.

### 8. `bitcoin-price-discovery-binance-perp` (SSRN)

- **citation**: *Where is the Price of Bitcoin Determined? Price Discovery in a Fragmented Market*. Authors **not verified** (the SSRN page I read did not render the author block).
- **DOI / URL**: [papers.ssrn.com/sol3/papers.cfm?abstract_id=5070964](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5070964)
- **peer-review status**: SSRN working paper, **not peer-reviewed**.
- **asset / market / venue / instrument**: BTC; **spot and perpetual futures** in fiat and stablecoin markets, multiple venues including **Binance** and Coinbase.
- **sample period and frequency**: High-frequency trade data; dates **not verified**.
- **variables used**: Trade prices, transaction costs, volumes, intraday clock.
- **predictive target**: Price-discovery share.
- **model or trading rules**: Information shares plus intraday decomposition.
- **temporal validation**: Not applicable.
- **costs modelled**: Transaction costs used as an explanatory variable, not as a P&L deduction.
- **reported return / Sharpe / drawdown**: None. Findings: **Binance spot and perpetual futures are the primary source of price discovery**; lower transaction costs and higher volumes enhance discovery; **Coinbase spot becomes relatively more influential around the New York 4 pm fixing**.
- **benchmark**: Regulated spot venues.
- **number of variants tested**: Not verified.
- **multiple-testing correction**: Not verified.
- **code/data availability**: Not verified.
- **possible leaks / weaknesses**: Unrefereed; author identities unverified by me, which is a citation risk for a thesis; the 4 pm fixing result is a single intraday window and invites multiplicity concerns.
- **compatibility with BTCUSDT/ETHUSDT perps**: **High** (Binance perps explicitly), BTC only.
- **reproducibility grade for us**: **Low** (multi-venue), except the intraday-clock claim, which we can test with our klines as an hour-of-day effect.
- **replicable economic hypothesis**: Binance perpetual prices lead the index most of the day, but around the 16:00 New York fixing regulated spot venues gain influence — implying the sign and information content of the perp-minus-index gap is time-of-day dependent.

### 9. `math2026-two-tiered-funding`

- **citation**: *The Two-Tiered Structure of Cryptocurrency Funding Rate Markets*. **Mathematics** (MDPI) 14(2), 346, 2026. Authors **not verified**.
- **DOI / URL**: [10.3390/math14020346](https://doi.org/10.3390/math14020346)
- **peer-review status**: Peer-reviewed (MDPI). Fast-turnaround open-access venue; weight accordingly.
- **asset / market / venue / instrument**: 749 perpetual symbols across **26 exchanges** (11 CEX, 15 DEX).
- **sample period and frequency**: **1-minute** panel, **35.7 million observations**, spanning **eight consecutive days**. The eight-day window is the paper's central weakness.
- **variables used**: Funding rates across venues; cross-venue spreads.
- **predictive target**: Funding-rate co-movement, integration, Granger-causal direction; profitability of cross-venue funding spreads.
- **model or trading rules**: Correlation/integration measures, Granger causality, delta-neutral cross-venue portfolio simulation with costs.
- **temporal validation**: Effectively none — eight days cannot support out-of-sample claims.
- **costs modelled**: **Yes**, and this is the paper's best contribution: transaction costs and spread-reversal risk are applied to the arbitrage simulation.
- **reported return / Sharpe / drawdown**: No Sharpe. Reported: CEX price-discovery integration **61% higher** than DEX; **all** significant information flow runs CEX→DEX with zero reverse causality; **17%** of observations show spreads ≥ 20 bps; **only 40%** of top opportunities are profitable after costs and reversals; **forced exits in 95%** of opportunities.
- **benchmark**: Zero-cost arbitrage assumption.
- **number of variants tested**: Not verified.
- **multiple-testing correction**: None reported, and with 749 symbols × 26 venues Granger tests this is a serious omission.
- **code/data availability**: Not verified.
- **possible leaks / weaknesses**: **Eight days of data.** Granger causality over eight days across 749 symbols with no multiplicity control should be read as descriptive only. Perpetual funding rates are step functions between settlements, which inflates measured correlation and autocorrelation mechanically.
- **compatibility with BTCUSDT/ETHUSDT perps**: Medium — Binance is in the panel, but the unit of analysis is cross-venue.
- **reproducibility grade for us**: **Not reproducible** (single venue, no DEX data).
- **replicable economic hypothesis**: Funding-rate dislocations persist because arbitrage is capacity- and duration-constrained, not because they are unobserved — so an observed extreme funding print is not by itself a profit opportunity.

### 10. `corsi2009-harrv`

- **citation**: Fulvio Corsi (2009). *A Simple Approximate Long-Memory Model of Realized Volatility*. **Journal of Financial Econometrics** 7(2), 174–196.
- **DOI / URL**: [10.1093/jjfinec/nbp001](https://doi.org/10.1093/jjfinec/nbp001)
- **peer-review status**: **Peer-reviewed.** Foundational (the HAR-RV reference).
- **asset / market / venue / instrument**: USD/CHF FX (in the earlier working version); equity/FX realized-volatility series. **Not crypto.**
- **sample period and frequency**: High-frequency intraday returns aggregated to daily realized volatility; exact sample **not verified** from the published version.
- **variables used**: Realized volatility at daily, weekly, monthly aggregations.
- **predictive target**: Future realized volatility (1-day and longer).
- **model or trading rules**: \(RV_{t+1} = c + \beta^{(d)}RV^{(d)}_t + \beta^{(w)}RV^{(w)}_t + \beta^{(m)}RV^{(m)}_t + \varepsilon\). Linear, three regressors, OLS.
- **temporal validation**: Out-of-sample forecast comparison against standard models; "remarkably good out-of-sample forecasting performance" (working-paper wording).
- **costs modelled**: Not applicable (no trading).
- **reported return / Sharpe / drawdown**: None — this is a forecasting paper, and that is precisely why it is the right citation for **position sizing rather than alpha**.
- **benchmark**: GARCH-type and long-memory (ARFIMA) alternatives.
- **number of variants tested**: Small, fixed lag structure (1/5/22).
- **multiple-testing correction**: Not applicable.
- **code/data availability**: Not applicable (the model is three lines).
- **possible leaks / weaknesses**: For our use: realized volatility from 5-minute bars is contaminated by microstructure noise and by jumps; the 24/7 crypto clock has no natural "day" boundary, so the d/w/m cascade must be redefined (and annualization must use 365, per our project rules). The model is a *conditional-variance* forecast, not a return forecast — using it for direction would be an abuse.
- **compatibility with BTCUSDT/ETHUSDT perps**: **High**, as a risk model.
- **reproducibility grade for us**: **High.** Fully computable from 5m klines with a causal rolling window; no extra data.
- **replicable economic hypothesis**: Realized volatility is persistent and forecastable from its own past at multiple horizons, so a causal HAR forecast can size positions to a volatility target.

### 11. `alsamaani2026-har-vs-garch-crypto`

- **citation**: Abdulrahman Alsamaani, Huda Aldhahi (2026). *Predicting the Volatility of Cryptocurrencies' Returns Using High-Frequency Data: A Comparative Analysis of GARCH, EGARCH, IGARCH, GJR-GARCH, LRE, and HAR Models*. **International Journal of Financial Studies** 14(4), 90. Received 25 Jan 2026, accepted 25 Mar 2026, published 3 Apr 2026.
- **DOI / URL**: [10.3390/ijfs14040090](https://doi.org/10.3390/ijfs14040090)
- **peer-review status**: Peer-reviewed (MDPI, ~2-month turnaround). Weight accordingly.
- **asset / market / venue / instrument**: **Twelve** cryptocurrencies (dominant and less dominant). Venue **not verified**; instrument is spot returns, **not perpetuals**.
- **sample period and frequency**: **5-minute** returns, **September 2018 → September 2020**. The authors themselves warn this is a "pre-institutionalization phase" that "may not fully generalize".
- **variables used**: 5-minute returns → realized volatility; no exogenous variables.
- **predictive target**: Realized volatility at **1-day, 7-day, 30-day** horizons.
- **model or trading rules**: Six competing forecasters (LRE, GARCH, EGARCH, IGARCH, GJR-GARCH, HAR).
- **temporal validation**: **Yes** — out-of-sample evaluation with RMSE and QLIKE, Mincer–Zarnowitz regressions, encompassing regressions, and **Diebold–Mariano** tests. This is the right methodology.
- **costs modelled**: Not applicable.
- **reported return / Sharpe / drawdown**: None. Findings: **HAR most accurate at short horizons**; EGARCH relatively better at long horizons; **no single model wins across all coins**; explanatory power declines with horizon; HAR+EGARCH combinations improve explanatory power at all horizons; DM tests favour HAR for most coins.
- **benchmark**: The five non-HAR models against each other.
- **number of variants tested**: 6 models × 12 coins × 3 horizons = 216 comparisons.
- **multiple-testing correction**: **None reported** across the 216 comparisons — a real weakness. A Model Confidence Set (as in Caporale & Zekokh) would have been the correct tool.
- **code/data availability**: Not verified.
- **possible leaks / weaknesses**: Two-year sample ending 2020; no perpetual-futures data; the "no single model wins" result plus no multiplicity control means the pro-HAR conclusion is suggestive rather than decisive. Realized-volatility proxy construction from 5-minute data (jump handling, overnight/24-7 treatment) is **not verified** by me.
- **compatibility with BTCUSDT/ETHUSDT perps**: **High** in method and frequency (5-minute), medium in instrument (spot, not perp).
- **reproducibility grade for us**: **High.** Directly re-runnable on BTCUSDT/ETHUSDT perpetual 5m klines.
- **replicable economic hypothesis**: At short horizons a HAR specification on 5-minute realized volatility forecasts crypto volatility better than GARCH-family alternatives, so HAR is the default risk model for intraday position sizing.

### 12. `harvey2018-voltargeting`

- **citation**: Campbell R. Harvey, Edward Hoyle, Russell Korgaonkar, Sandy Rattray, Matthew Sargaison, Otto Van Hemert (2018). *The Impact of Volatility Targeting*. **Journal of Portfolio Management** 45(1), 14–33.
- **DOI / URL**: [10.3905/jpm.2018.45.1.014](https://doi.org/10.3905/jpm.2018.45.1.014)
- **peer-review status**: **Peer-reviewed** practitioner-academic journal.
- **asset / market / venue / instrument**: **60+ assets** — equities, credit, bonds, currencies, commodities; plus 60/40 and risk-parity portfolios. **No crypto.**
- **sample period and frequency**: Daily data "beginning as early as 1926" through 2017.
- **variables used**: Realized volatility estimates at several half-lives; asset returns.
- **predictive target**: Risk-adjusted performance of volatility-scaled versus constant-notional exposure.
- **model or trading rules**: Position = target vol / forecast vol, applied at asset and portfolio level.
- **temporal validation**: Long multi-decade, multi-asset out-of-sample-by-construction evidence; robustness across volatility half-lives.
- **costs modelled**: Turnover is discussed; the exact cost treatment of the headline results is **not verified** by me. Related work (Research Affiliates) argues turnover costs can negate most of the Sharpe gain — an important caveat.
- **reported return / Sharpe / drawdown**: Sharpe ratios **higher** with volatility scaling **for risk assets only** (equities, credit) and for portfolios with large risk-asset weight; **negligible** for bonds, currencies, commodities. Across **all** asset classes, volatility targeting **reduces the likelihood of extreme returns**, especially left-tail, and reduces excess kurtosis. Exact Sharpe deltas: **not verified** (the 40-Sharpe-point figure I saw for crypto is from a Man Group note, not this paper).
- **benchmark**: Constant-notional versions of the same assets.
- **number of variants tested**: 60+ assets × several volatility half-lives; fully disclosed.
- **multiple-testing correction**: None formally, but the breadth of assets is itself the robustness argument.
- **code/data availability**: Not verified.
- **possible leaks / weaknesses**: (i) The Sharpe benefit is attributed to the **leverage effect** (negative return-volatility relation); crypto's return-volatility relation is not stably negative — Ardia et al. find an **inverted** leverage effect in both Bitcoin volatility regimes, which **directly undercuts** the Sharpe-improvement channel for our asset. (ii) Cederburg, O'Doherty, Wang & Yan (as summarized by Alpha Architect) report volatility management outperformed in only 53 of 103 cases and consistently helps only momentum/profitability/BAB — so **do not pre-specify a Sharpe improvement**. (iii) Costs and turnover are the main practical objection.
- **compatibility with BTCUSDT/ETHUSDT perps**: Medium — the mechanism is asset-agnostic, the empirical support is not crypto.
- **reproducibility grade for us**: **High** as a risk overlay on any strategy we build; zero extra data.
- **replicable economic hypothesis**: Scaling exposure inversely to forecast volatility stabilizes realized risk and reduces left-tail severity, with Sharpe improvement conditional on a negative return-volatility relation that may not hold for crypto.

### 13. `ardia2019-msgarch-btc`

- **citation**: David Ardia, Keven Bluteau, Maxime Rüede (2019). *Regime changes in Bitcoin GARCH volatility dynamics*. **Finance Research Letters** 29, 266–271.
- **DOI / URL**: [10.1016/j.frl.2018.08.009](https://doi.org/10.1016/j.frl.2018.08.009) (open access, CC-BY)
- **peer-review status**: **Peer-reviewed.**
- **asset / market / venue / instrument**: Bitcoin **daily log returns** (spot). Venue **not verified**.
- **sample period and frequency**: Daily. Exact window **not verified**.
- **variables used**: Returns only.
- **predictive target**: One-day-ahead **Value-at-Risk** — a risk target, not a return target.
- **model or trading rules**: **18** GARCH/MSGARCH specifications (scedastic function × distribution × 1–2 regimes), Bayesian estimation via the MSGARCH R package.
- **temporal validation**: Out-of-sample VaR backtesting on a rolling basis.
- **costs modelled**: Not applicable.
- **reported return / Sharpe / drawdown**: None. Findings: strong evidence of regime changes; best in-sample fit is a **two-regime asymmetric Student specification**; **MSGARCH clearly outperforms single-regime GARCH for VaR forecasting**; an **inverted leverage effect in both low- and high-volatility regimes**.
- **benchmark**: Single-regime GARCH.
- **number of variants tested**: 18, fully disclosed.
- **multiple-testing correction**: Not formally applied, but VaR backtests are the discipline.
- **code/data availability**: Open-source `MSGARCH` R package (author-maintained). **The best code availability in this matrix.**
- **possible leaks / weaknesses**: Daily, spot, pre-2019 Bitcoin; a two-regime daily model says nothing directly about 5-minute regimes. Regime *identification* is done with the filtered (causal) probability in forecasting, but the *model selection* (which of the 18) uses full-sample in-sample fit — a mild selection leak if we copy their choice without re-selecting causally.
- **compatibility with BTCUSDT/ETHUSDT perps**: Medium (right asset family, wrong frequency and instrument).
- **reproducibility grade for us**: **Medium-High** for a risk model; the inverted-leverage finding is directly testable on our data and is important because it contradicts the Harvey et al. Sharpe channel.
- **replicable economic hypothesis**: Bitcoin volatility switches between persistent regimes, so a two-regime conditional-variance model produces better tail-risk forecasts than a single-regime one — a risk-management gain, not an alpha.

### 14. `caporale2019-msgarch-crypto`

- **citation**: Guglielmo Maria Caporale, Timur Zekokh (2019). *Modelling volatility of cryptocurrencies using Markov-Switching GARCH models*. **Research in International Business and Finance** 48, 143–155.
- **DOI / URL**: [10.1016/j.ribaf.2018.12.009](https://doi.org/10.1016/j.ribaf.2018.12.009) (open access, CC-BY)
- **peer-review status**: **Peer-reviewed.**
- **asset / market / venue / instrument**: Bitcoin, Ethereum, Ripple, Litecoin; exchange-rate log returns (spot).
- **sample period and frequency**: Daily. Exact window **not verified**.
- **variables used**: Returns only.
- **predictive target**: One-step-ahead **VaR and Expected Shortfall**.
- **model or trading rules**: **More than 1,000** GARCH specifications fitted per asset, rolling-window one-step-ahead risk forecasts.
- **temporal validation**: Rolling-window out-of-sample; VaR/ES backtesting.
- **costs modelled**: Not applicable.
- **reported return / Sharpe / drawdown**: None. Findings: standard GARCH can yield **incorrect** VaR/ES; specifications allowing **asymmetries and regime switching** are preferred.
- **benchmark**: Standard single-regime GARCH.
- **number of variants tested**: **>1,000 per asset** — explicitly disclosed.
- **multiple-testing correction**: **Yes — Model Confidence Set (Hansen–Lunde–Nason)** plus VaR/ES backtests. This is the **only paper in the matrix that properly handles its own multiplicity**, and it should be the template for our own model-selection reporting.
- **code/data availability**: Not verified (likely `rugarch`/`MSGARCH`).
- **possible leaks / weaknesses**: Daily spot returns, four coins, pre-2019; nothing intraday; nothing about perpetuals or funding. The MCS protects the *ranking*, not the *external validity*.
- **compatibility with BTCUSDT/ETHUSDT perps**: Medium.
- **reproducibility grade for us**: **Medium-High** for the methodology; the MCS discipline is directly transplantable to our HAR/GARCH comparison and to our Random-Search/GA phase later.
- **replicable economic hypothesis**: Among a large family of volatility models, regime-switching and asymmetric specifications survive a Model Confidence Set for crypto tail-risk forecasting, whereas plain GARCH does not.

### 15. `agakishiev2025-regime-rl` — the honest negative

- **citation**: Ilyas Agakishiev, Wolfgang Karl Härdle, Denis Becker, Xiaorui Zuo (2025). *Regime switching forecasting for cryptocurrencies*. **Digital Finance** 7, 107–131. Received 10 Oct 2024, accepted 29 Dec 2024, published 29 Jan 2025. (Author order as listed on the publisher page.)
- **DOI / URL**: [10.1007/s42521-024-00123-2](https://doi.org/10.1007/s42521-024-00123-2)
- **peer-review status**: **Peer-reviewed.**
- **asset / market / venue / instrument**: CRIX cryptocurrency index; spot. Not perpetuals.
- **sample period and frequency**: **Not verified** (I read the abstract, author block and conclusions).
- **variables used**: Price returns, volatility and return quantiles defining three regimes, plus "cryptocurrency metadata".
- **predictive target**: Portfolio weight (share allocated to CRIX) maximizing wealth — an allocation target.
- **model or trading rules**: Two-stage: regime classification (three regimes from volatility/return quantiles), then reinforcement learning conditioned on the regime prediction or its probabilities.
- **temporal validation**: **Yes — explicit train/out-of-sample separation, and this is the paper's value.**
- **costs modelled**: Not verified.
- **reported return / Sharpe / drawdown**: The reported result is a **negative**: "While the results were promising during the training process, with both the regimes and the probabilities achieving higher reward values with the same architecture and hyperparameters. However, **for out-of-sample data, an improvement could not be detected.**"
- **benchmark**: The same RL model **without** regime information.
- **number of variants tested**: Regime labels vs regime probabilities; architecture held fixed.
- **multiple-testing correction**: Not applicable (the finding is null).
- **code/data availability**: Materials referenced on Quantlet/Quantinar (Härdle group convention). Not verified by me.
- **possible leaks / weaknesses**: For *our* purposes the weakness is scope (index, not perps; no intraday). But the paper is the single most useful data point in domain 6: **regime information that looks valuable in-sample did not survive out-of-sample**, in the hands of a serious econometrics group who published the null.
- **compatibility with BTCUSDT/ETHUSDT perps**: Low mechanically; high as a prior.
- **reproducibility grade for us**: Medium (the RL layer is out of scope for Chapter 5).
- **replicable economic hypothesis**: Adding a regime-state variable to an allocation model improves in-sample reward but does not improve out-of-sample performance — so any regime feature we add must be justified by an out-of-sample gain, not by in-sample regime separation.

### 16. `garciaseuma2026-cascades` (Parts I & II) — low-tier, included for domain 4

- **citation**: Ramon Marc Garcia Seuma (2026). Part I: *Where does the criticality live? Early-warning signals are event-heterogeneous across seven crypto-perpetual liquidation cascades*. Part II: *Measuring the engine of a liquidation cascade: subcritical branching inside a first-order transition*.
- **DOI / URL**: [arXiv:2607.27070](https://arxiv.org/abs/2607.27070); [arXiv:2608.03616](https://arxiv.org/abs/2608.03616)
- **peer-review status**: **Preprints, not peer-reviewed.** Single author, personal Gmail correspondence address, no institutional affiliation. Cite only as hypothesis-generating.
- **asset / market / venue / instrument**: **Binance USDⓈ-M perpetuals** (BTCUSDT plus a panel of 22→30 liquid names) and Hyperliquid (on-chain fill log from 2025-05-25).
- **sample period and frequency**: **1-minute klines and 5-minute derivatives metrics** around seven cascades: May 2022 (LUNA/UST), Nov 2022 (FTX), Aug 2024 (yen-carry), Dec 2024, Feb 2025, Apr 2025, **Oct 2025** ($19B). ~2-month window per event.
- **variables used**: Price, aggregate **open interest**, long/short positioning of ordinary and top accounts, **taker aggressor side**, quoted impact prices, on-chain forced fills. Note: these are exactly the fields in Binance's public `metrics` archive plus klines.
- **predictive target**: Pre-cascade early-warning detectability; in-cascade branching ratio.
- **model or trading rules**: Rolling variance and lag-1 autocorrelation of detrended residuals; Kendall-τ trend tests; **39 analysis configurations per variable per event**; a 300-onset placebo test; Kyle-style impact regressions; Galton–Watson branching estimates.
- **temporal validation**: **Unusually good for a preprint**: a hypothesis formed in-sample on Oct 2025 is tested out-of-sample on other events, and the author reports that it **inverts**.
- **costs modelled**: Not applicable (no strategy).
- **reported return / Sharpe / drawdown**: No strategy, no Sharpe. Reported: no variable is event-invariant; price shows critical slowing down in **5 of 7** events but is silent in the two sudden-news shocks; the one surviving regularity is a **compression of taker order-flow variance** (Fisher-combined *p* ≈ 5×10⁻⁶ against a 300-onset placebo) but it is described as a **population-level precursor, not a per-event alarm**. Part II: Kyle impact coefficient elevated ×1.2–3.5 (regressed) and ×3.2–9.1 (quoted) during cascades; open interest clears by **25–70%**; branching ratio λ̂ ≈ 0.1–0.2 (deeply subcritical); 88% of post-onset forced selling within 30 minutes.
- **benchmark**: Explicit placebo null of ordinary market windows.
- **number of variants tested**: 39 configurations × variables × events — **disclosed and swept**, which is better practice than most peer-reviewed papers here.
- **multiple-testing correction**: Placebo test and cross-event out-of-sample testing; no formal FWER control.
- **code/data availability**: States that all data are public and the pipeline is scripted (repository named `critical-phenomena-in-crypto-perps`). **Repository existence not verified.**
- **possible leaks / weaknesses**: Unreviewed, single-author, no institutional affiliation; seven events is a tiny effective sample no matter how many configurations are swept; the "surviving" order-flow result is a pooled effect and the author explicitly refuses to call it tradable. Do not build a thesis claim on this — but the **negative** result (no reliable per-event early warning) is a useful prior and is stated against the author's own interest.
- **compatibility with BTCUSDT/ETHUSDT perps**: **Very high** — same venue, same symbol, same 1m/5m frequency, and it uses only public data.
- **reproducibility grade for us**: **High for the price and taker-flow parts** (our 5m klines contain `taker_buy_base`/`taker_buy_quote`, so taker order-flow imbalance and its variance are directly computable). **Medium for OI** — needs the `metrics` archive. **Impossible for the forced-fill parts** (no liquidation feed).
- **replicable economic hypothesis**: There is no single reliable pre-cascade alarm; cascade severity is set by shock × leverage-in-path × liquidity withdrawal, so leverage/flow state variables are better used to *size down risk* than to *predict crashes*.

### 17. `ijebmr2026-leverage-crash` — low-tier, cite with a warning or not at all

- **citation**: *Systemic Risk from Financial Leverage in Digital Asset Markets: Evidence From Perpetual Futures*. **International Journal of Economics, Business and Management Research** (2026). Authors **not verified**.
- **DOI / URL**: `https://ijebmr.com/uploads/pdf/archivepdf/2026/IJEBMR_1847.pdf` — no DOI; **IJEBMR is a low-credibility, pay-to-publish venue.** Do not use as authority in a thesis.
- **peer-review status**: Nominally peer-reviewed; **venue quality low**.
- **asset / market / venue / instrument**: **Binance**, 10 major cryptocurrencies, perpetual futures.
- **sample period and frequency**: **2.65 million 8-hour observations, 2023–2024.** (2.65M / (10 coins × ~2,190 eight-hour periods) does not reconcile cleanly — the observation count is **suspect**.)
- **variables used**: Realized volatility, **open-interest changes**, **cumulative funding rates**, basis spreads, behavioural and calendar controls, cross-asset (BTC) versions of the same.
- **predictive target**: Binary **crash** = ≥5% decline within 8 hours.
- **model or trading rules**: Panel logit with coin fixed effects; BIC model selection; Random Forest comparison.
- **temporal validation**: **Out-of-sample AUROC/AUPRC reported** — methodologically the right thing.
- **costs modelled**: No strategy, so none.
- **reported return / Sharpe / drawdown**: No Sharpe. Reported: out-of-sample **AUROC 0.76**, **AUPRC 0.27**; strongest predictor is **BTC open-interest change (OR = 1.48)**; robustness across 3/5/7/10% crash thresholds.
- **benchmark**: Random classification (AUROC 0.5); Random Forest.
- **number of variants tested**: 4 crash thresholds × several specifications × 2 model families.
- **multiple-testing correction**: BIC for specification choice; no FWER control.
- **code/data availability**: Not verified.
- **possible leaks / weaknesses**: (i) Venue credibility. (ii) Coin fixed effects with a pooled 2023–24 sample and cross-asset BTC regressors invites look-ahead through contemporaneous alignment — whether the BTC OI change is strictly *prior* to the crash window is **not verified**. (iii) A 5%-in-8-hours crash label is highly autocorrelated; without block-wise or purged splits, the "out-of-sample" AUROC is optimistic. (iv) AUPRC 0.27 on a rare event is a modest signal, honestly reported.
- **compatibility with BTCUSDT/ETHUSDT perps**: High in principle (Binance perps, funding + OI, 8-hour).
- **reproducibility grade for us**: **Medium** — requires the OI `metrics` archive; funding and returns we already have. But given the venue, treat as a *hypothesis source*, never as evidence.
- **replicable economic hypothesis**: Accumulated leverage — measured by open-interest growth and cumulative funding — raises the probability of a large adverse 8-hour move, so leverage state is a risk-conditioning variable rather than a directional signal.

### 18. `presto2023-funding-predictability` — practitioner note, decisive negative

- **citation**: Presto Research, *#7 Can Funding Rate Predict Price Change?* Author(s) and date **not verified**.
- **DOI / URL**: [prestolabs.io/research/can-funding-rate-predict-price-change](https://www.prestolabs.io/research/can-funding-rate-predict-price-change); PDF mirror at `assets.ctfassets.net/.../Can_Funding_Rate_Predict_Price_Change.pdf`
- **peer-review status**: **Not peer-reviewed** — proprietary trading-firm research note.
- **asset / market / venue / instrument**: Perpetual futures; universe and venue **not verified**.
- **sample period and frequency**: **Not verified.** This is a fatal reporting gap.
- **variables used**: Funding rate and funding-rate changes; prices.
- **predictive target**: Next-period price change; and a cross-sectional relative-return alpha.
- **model or trading rules**: Univariate regression of Δfunding(T) on Δprice(T+1); then a cross-sectional stat-arb alpha.
- **temporal validation**: **Not verified** — no described train/test split.
- **costs modelled**: Not in the P&L, but turnover is flagged as the binding constraint.
- **reported return / Sharpe / drawdown**: Single-asset: "**near-zero correlation**", "**zero R-squared and large p-value**", "the model has **no prediction power**". Contemporaneous/short-window: funding-rate changes explain **12.5%** of price variation over a 7-day window, decaying sharply thereafter. Cross-sectional alpha: "annualized return and Sharpe ratio appear highly favorable" — **the actual Sharpe number is not disclosed**, and daily turnover is described as "extremely high".
- **benchmark**: None.
- **number of variants tested**: Not verified.
- **multiple-testing correction**: None.
- **code/data availability**: None.
- **possible leaks / weaknesses**: Undisclosed sample, undisclosed universe, undisclosed Sharpe, no cost accounting on the one strategy that "works", and a marketing incentive. **However**: the negative single-asset result is (a) directionally consistent with He et al.'s framing (funding tracks the *contemporaneous* basis by construction, so it is nearly mechanically related to *past* returns, not future ones) and (b) exactly the result a two-asset intraday project should assume as its null.
- **compatibility with BTCUSDT/ETHUSDT perps**: High in spirit; the cross-sectional part is **inapplicable to us** (two assets is not a cross-section).
- **reproducibility grade for us**: **High for the negative test** — we can and should run exactly this regression on BTCUSDT/ETHUSDT as a falsification check before building anything funding-directional.
- **replicable economic hypothesis**: The funding rate contains no exploitable information about the *sign* of a single asset's next-period return; its information is contemporaneous and cross-sectional.

### 19. `aalto2022-eth-funding-thesis` — included as a critical counter-example

- **citation**: *Predicting Ethereum price with perpetual futures contract funding rates*. Master's thesis, Aalto University. Author and exact year **not verified** (the repository page I read did not render the author field).
- **DOI / URL**: [aaltodoc.aalto.fi/handle/123456789/119037](https://aaltodoc.aalto.fi/handle/123456789/119037)
- **peer-review status**: **Student thesis — not peer-reviewed.**
- **asset / market / venue / instrument**: ETH; **Binance and FTX** perpetual futures.
- **sample period and frequency**: **2019-12-12 → 2022-09-20.** Frequency **not verified** (likely 8-hourly or daily).
- **variables used**: Funding rate; ETH market price.
- **predictive target**: ETH price change.
- **model or trading rules**: Granger causality tests; then a strategy backtest driven by **forecasted funding rates**.
- **temporal validation**: **Not verified** — no described walk-forward.
- **costs modelled**: **Not verified.** Almost certainly not, and for a strategy trading around 8-hour funding this is disqualifying.
- **reported return / Sharpe / drawdown**: Claims Granger causality from funding to price and that "forecasted funding rates offered a noticeable edge in a trading strategy backtest". **No Sharpe, return or drawdown number verified.**
- **benchmark**: Not verified.
- **number of variants tested**: Not verified.
- **multiple-testing correction**: None.
- **code/data availability**: Not verified.
- **possible leaks or weaknesses**: This is the paper to be most sceptical of, and it is instructive precisely because it reaches the **opposite** conclusion to Presto and to He et al.'s framing. Specific concerns: (i) **Granger causality is not economic predictability** and is badly behaved when one series (funding) is a step function computed from a time-weighted average of the other series' basis — a mechanical dependence that will register as "causality". (ii) A strategy driven by *forecasted* funding stacks a second unvalidated model on top. (iii) The sample includes **FTX**, which failed two months after the sample ends, and spans the 2021 mania — a period where any long-biased rule works. (iv) No costs, no correction, no holdout, single asset. **Do not cite this as evidence that funding predicts returns.** Cite it as an example of how the claim arises.
- **compatibility with BTCUSDT/ETHUSDT perps**: Right asset and venue; wrong methodology.
- **reproducibility grade for us**: **High and worth doing as a falsification**: re-run the Granger test on our data, show the mechanical-dependence artefact, and report the null.
- **replicable economic hypothesis**: Funding rates Granger-cause perpetual price changes — a hypothesis we should attempt to **falsify**, because the causality is plausibly an artefact of funding being constructed from the trailing basis.

---

## Papers reporting positive Sharpe — critical evaluation

Only three sources in this matrix report a Sharpe ratio at all. That is itself the finding: **the credible literature in these six domains is overwhelmingly about mechanism, price discovery and risk forecasting, not about profitable directional strategies.**

**He et al. (2024) — BTC SR 1.80 (high cost), 6.72 (zero cost); ETH 2.55.**
This is the most defensible positive result here, and it still should not be read as an alpha we can inherit. Reasons: (1) It is a **two-legged spot+perp convergence trade**. Take away the spot leg — which we do not have — and it becomes a directional bet on the perp reverting toward the index, with the volatility of the perp rather than the volatility of the basis. The Sharpe does not survive that transformation, and nothing in the paper says it would. (2) The Sharpe is high because the *volatility* is 3.55%/yr, not because the return is large (6.38%/yr). A thesis reporting a Sharpe of 1.8 on a 6% return must show the margin, funding and liquidation mechanics that make that leverage survivable. (3) **The result decays inside the sample**: BTC SR falls to 0.70 in 2022 and deviations shrink ~11%/yr by the authors' own estimate. (4) There is **no walk-forward and no multiple-testing correction**; the entry/exit thresholds are chosen with full-sample knowledge. (5) Cost modelling is the paper's strength — maker fees by tier, spreads and impact bounded with real order-book data — so the *cost* criticism does not apply, and that is why this is the one result worth taking seriously.

**Christin et al. (2023) — BTC SR 8.76 (USDT contract), 4.93 (coin contract), vs BTC buy-and-hold 0.46.**
A Sharpe of 8.76 should be treated as a **red flag about the metric**, not a finding about the trade. It is the Sharpe of an 8-hourly carry cash-flow that is smooth until a discrete counterparty/peg/liquidation event, sampled over a window (Aug 2020 – Jun 2023) that contains the largest levered-long boom in the instrument's history and the leverage-cap change the authors use for identification. **I could not verify that transaction costs are deducted**, and margin, liquidation and stablecoin-peg risk are not modelled at all. The sample contains Terra, 3AC, FTX and SVB — the paper notes Sharpes are "much smaller" in that later subsample, which is the honest part. What survives criticism is the **economic claim**, not the number: Binance perpetual funding is persistently positive because levered longs pay for access to leverage. That claim is corroborated by He et al. and by Schmeling et al. through a different instrument, and it is directly verifiable in our own funding history.

**Schmeling et al. (2025) — carry "sometimes exceeding 40% p.a.", futures-leg 2–3%/month.**
Peer-reviewed in Management Science and, crucially, **the authors do not present this as a Sharpe**. They report 2–3%/month mean excess return against **~17%/month volatility** — an annualized Sharpe on the order of 0.5, i.e. unremarkable — and they emphasize that carry is right-skewed, so the cash-and-carry arbitrageur faces a high risk of large drawdowns. This is the most intellectually honest treatment of "crypto basis returns" in the matrix, and it should anchor our expectations. It also does not apply to us mechanically: fixed-maturity futures, daily data, vendor-aggregated bases.

**Presto Research (undated) — "highly favorable" cross-sectional Sharpe, number withheld.**
Uninterpretable and should not be cited for the positive claim. Its value is entirely in the negative single-asset result.

**Aalto thesis — "noticeable edge", no number.**
Not evidence. See row 19.

**What no paper in this matrix demonstrates:** a positive, cost-aware, walk-forward-validated, multiplicity-corrected Sharpe from a **single-leg directional** intraday strategy on Binance BTCUSDT/ETHUSDT perpetuals using funding, basis or mark-price information. If our thesis produces one, it will be a novel claim and will need a correspondingly high evidentiary bar. If it produces a rigorous null, that is consistent with the entire literature above.

---

## Binance funding / mark price mechanics (verified from official docs)

**Primary source, read in full**: *Introduction to Binance Futures Funding Rates*, official Binance support FAQ, published 2019-09-09, **last updated 2026-03-06 07:01**.
Canonical URL: `https://www.binance.com/en/support/faq/detail/360033525031`
The `binance.com` host returns a JavaScript/anti-bot wall to non-browser clients; I read the identical content on the official mirror **`https://www.binance.info/en/support/faq/detail/360033525031`**. Independent corroboration that this is the canonical funding-rate reference: He et al. (2024) and Christin et al. (2023) both cite exactly this URL.

**Funding interval and settlement timestamps.**
- Default interval is **every 8 hours**, at **00:00 UTC, 08:00 UTC and 16:00 UTC**. Contract-specific intervals are set in each Contract Specification.
- You pay or receive **only if you hold a position at the pre-specified funding time**; closing before it means no payment.
- There is a documented **15-second deviation in the actual funding transaction time** — "when you open a position at 08:00:05 (UTC), the funding fee could still apply".
- Binance reserves the right to change the interval. **From 2025-05-02 08:00 UTC**, if a USDⓈ-M perpetual's funding settlement **reaches its cap or floor**, the interval switches to **hourly**, starting the next hour, with the change completed within ~15 minutes and **no announcement**. **From 2026-01-02 12:00 UTC**, an hourly contract reverts to **4-hourly** on the 17th cycle if |rate| ≤ 0.025% for 16 consecutive cycles. Query the current interval via `GET /fapi/v1/fundingInfo`.
- **Implication for us**: the funding interval for BTCUSDT/ETHUSDT is *not* a constant across our sample. Any code that hard-codes 3 settlements/day or an ×3×365 annualization is wrong during cap-triggered hourly episodes. The FAQ example gives BTCUSDT's cap/floor as **±0.3%**.

**Funding payment.**
- `Funding Amount = Nominal Value of Positions × Funding Rate`, with `Nominal Value = Mark Price × Size of Contract`.
- Binance charges **no fee** on funding; it is a peer-to-peer transfer.
- **Documented inconsistency, flagged honestly**: the separate fees FAQ (`https://www.binance.info/en/support/faq/detail/98488a516eb84e3eb34605683dffd554`) states `Notional Value = Number of Contracts × Trade Price` for the funding fee, whereas the funding FAQ says **Mark Price**. The funding FAQ is the authoritative one for funding. Our backtester should use **mark price** for funding notional (which we have) and last/trade price for commissions.

**Interest-rate component.**
- Fixed at **0.03% per day by default = 0.01% per 8-hour interval**. Exceptions exist (ETHBTC is 0%). Binance may adjust it.

**Premium index (the exact formula).**

```
Premium Index (P) = [ Max(0, Impact Bid Price − Price Index)
                    − Max(0, Price Index − Impact Ask Price) ] / Price Index
```

- **Impact Bid / Ask Price** = the average fill price to execute the **Impact Margin Notional** against the bid / ask side of the order book.
- **Impact Margin Notional (IMN)** = `200 USDT / initial margin rate at the maximum leverage level`. Worked example in the FAQ: BNBUSDT at 20× max leverage → 5% initial margin → IMN = 4,000 USDT. A second worked example uses a 125×-max contract with a default IMN of 25,000 USDT.
- **Price Index** = weighted average of the underlying on major spot exchanges.
- **Sampling**: the premium index is computed **every 5 seconds** (12 points per minute). Points per funding window `n = (60/5) × 60 × hours`; for an 8-hour interval **n = 5,760**.
- **Averaging**: for intervals **> 1 hour**, a **time-to-funding-weighted** average with linear weights,
  `Average P = (1·P₁ + 2·P₂ + … + n·Pₙ) / (1+2+…+n)`, so **later observations dominate**. For a **1-hour** interval the average is **equally weighted** (n = 720).

**Funding rate formula.**

```
Funding Rate (F) = [ Average Premium Index (P)
                   + clamp(Interest Rate − P, 0.05%, −0.05%) ] / (8 / N)
```

- `N` = funding interval in hours; the interest rate here is the **8-hour** rate (0.01% for most symbols).
- The FAQ defines `clamp(x, min, max)` but passes the arguments as `(x, 0.05%, −0.05%)` — an ordering inconsistency **in Binance's own document**. The operative behaviour is stated unambiguously in words: the adjustment is bounded to **±0.05%**, so **if the premium index lies between −0.04% and +0.06%, F equals the interest rate, 0.01%**. This dead zone is the single most important fact for anyone modelling funding: **most of the time funding is a constant, not a signal.**
- Worked example from the FAQ (2020-08-28 08:00 UTC): 8-hour weighted average P = 0.0429% → F = 0.0429% + clamp(0.01% − 0.0429%, ±0.05%) = 0.0429% − 0.0329% = **0.0100%**.
- **Cap and floor**: `Floor = −0.75 × Maintenance Margin Ratio`, `Cap = +0.75 × MMR` at the maximum leverage tier; `Capped Funding Rate = clamp(F, Floor, Cap)`. This applies to a listed set that **includes BTCUSDT and ETHUSDT**; all other USDⓈ-M perpetuals are capped at **±2%**.
- **Timing / causality note (important for us)**: the FAQ states that the displayed funding rate "represents an estimation of the last 8 hours of the premium index — for example, at 09:00 (UTC), the funding rate calculation uses the premium index dataset from 01:00 to 09:00 (rather than from 08:00 to 09:00)". So the rate settled at timestamp *T* is determined **from data up to and including T**, using **no future information**. It is therefore causally usable at *T*, but must be lagged by at least one bar before it can drive an order — which is exactly what our next-bar execution rule enforces.

**Mark price — partially verified, and I flag the gap.**
I could **not** open Binance's own mark-price documentation: `developers.binance.com` and `binance.com` both returned the anti-bot wall, and I did not find an official mirror of the mark-price page. What follows is from **secondary sources reporting Binance's official announcement** of 2025-09-16, effective **2025-09-18 16:01 (UTC+8)**, corroborated across two independent reports and consistent with OKX's analogous published formula:

```
Mark Price (USDⓈ-M and COIN-M perpetuals) = Median(Price 1, Price 2, Contract Price)
Price 2 = Price Index + Moving Average(30-second basis)
MA(30-second basis) = mean over 30 one-second points of [ (best bid + best ask)/2 − Price Index ]
```

- The basis moving-average window was **shortened from 1 minute to 30 seconds** on 2025-09-18; before that date the same structure held with a 60-second window. **The definition of "Price 1" is not verified and I will not guess it.**
- For **delivery** (non-perpetual) futures the announcement gives `Mark Price = Price Index + MA(30-second basis)` with no median.
- Sources actually read: `https://www.cointech2u.com/binance-will-adjust-the-contract-funding-rate-calculation-formula-and-mark-price/` (verbatim reproduction of the announcement) and `https://www.ainvest.com/news/binance-futures-sept-18-funding-rate-update-implications-stablecoin-pegged-perpetuals-2509/`. Analogous official formula: `https://www.okx.com/en-au/help/ii-mark-price-and-last-price`.
- **Verify this yourself before it enters the thesis.** Open the Binance mark-price FAQ in a browser and confirm the Price 1 definition and the 30-second window.

**Official API endpoints (verified via Binance's own connector repositories and developer-docs links).**
`GET /fapi/v1/premiumIndex` (mark price, index price, last funding rate, interest rate, next funding time), `GET /fapi/v1/fundingRate`, `GET /fapi/v1/fundingInfo`, `GET /fapi/v1/markPriceKlines`, `GET /fapi/v1/premiumIndexKlines`, `GET /fapi/v1/indexPriceKlines`, `GET /futures/data/openInterestHist` (period 5m…1d, **"only the data of the latest 1 month is available"** — which is the constraint you correctly identified for the REST route, and which the bulk archive bypasses).

---

## Verdict for our project

### First, the literature answer on the mark-price-vs-last-price gap

**I found no peer-reviewed paper — and no working paper — that studies the mark-price-minus-last-price gap on Binance (or any venue) as a predictive signal.** I searched for it directly and the entire first page of results was exchange documentation and trading blogs (Perpmate, Bitsgap, Orderly, Greeks.live, OKX). The closest academic work is: He et al. (perp **last** minus **spot/index**, which is a different and larger quantity), Alexander & Heck and the SSRN Binance price-discovery paper (perp leads index, so part of the gap is *information*, not dislocation), and De Blasis & Webb (perp-vs-quarterly and intraday seasonality on Binance).

So the gap is genuinely unexploited in the literature. But before treating that as an opportunity, note what the formula implies — and I present this as **an inference from the (secondary-source) mark-price formula, not as a verified empirical fact**:

Since `mark = Median(Price 1, Price 2, contract price)`, whenever the last traded price lies **between** Price 1 and Price 2 the median **is** the last price, and the gap is **exactly zero**. The mark-minus-last series is therefore expected to be **censored at zero with occasional one-sided spikes**, non-zero only when the traded price moves outside the band set by the index-anchored inputs. Its 5-minute close-to-close version will be mostly zeros, and its distribution will be dominated by the median switch, not by a smooth premium.

**The actionable consequence**: do not build the dislocation feature from `mark − last`. Build it from `premiumIndexKlines` and `indexPriceKlines`, both of which are in the Binance bulk archive and both of which give the **signed, uncensored** premium directly. That is strictly better data for the same economic idea. First diagnostic to run: measure the fraction of 5-minute bars where `markPrice_close == close` for BTCUSDT and ETHUSDT. If it is high, the gap idea is dead and you will have killed it in an afternoon instead of a chapter.

### Three signals worth pre-specifying

**S1 — Perp-vs-index premium reversion (the strongest candidate).**
Feature: `dev_t = (close_t − indexClose_t) / indexClose_t` at 5m, from `klines` + `indexPriceKlines`; cross-checked against `premiumIndexKlines`. Rule: enter against the sign of `dev` when `|dev|` exceeds a pre-specified cost-aware threshold; exit on reversion toward zero or on a time stop.
Grounding: this is He et al.'s ρ, computed on the same venue and the same two assets, using their own no-arbitrage logic (their κ = 1095 relation gives the fair level). Their reported BTC SR of 1.80 after realistic maker fees is the closest thing to positive evidence in this literature.
**Honest limits, stated up front**: (i) We cannot hedge with spot, so this is **not** their arbitrage — it is a directional bet on convergence, carrying full perp volatility, and their Sharpe **does not transfer**. Pre-specify this expectation. (ii) Their edge decays ~11%/yr and collapsed to SR 0.70 in 2022. (iii) Part of the deviation is information (Alexander & Heck: perps lead the index), so some of it should *not* revert. (iv) Frino et al.'s lesson applies: show the result is invariant across 5m/15m/1h before believing it.

**S2 — Funding/leverage crowding as a state variable, not as a direction.**
Feature: settled funding rate history (lagged to the settlement timestamp, then by one bar), its rolling sum over 3/9/21 settlements, and its position within a causal rolling quantile; plus, if you ingest the `metrics` archive, open-interest change over the same windows.
Use: **conditioning and risk sizing** — reduce or veto exposure when the crowded side is the side you would take, in the spirit of Schmeling et al. (high carry marks crowded levered demand and elevated crash risk) and the leverage-crash logic. Do **not** trade it directionally.
Grounding: Christin et al. and He et al. establish that positive funding is levered-long demand; Schmeling et al. link high carry to subsequent crash risk; Presto establishes that single-asset directional predictability from funding is ~zero. The convergent reading across three independent sources is: **funding is a positioning gauge, not a return forecast.**
**Honest limits**: the ±0.05% clamp means funding equals 0.01% most of the time, so the feature is informative only in its tails; the interval is not constant across the sample (cap-triggered hourly switching from 2025-05-02, 1h→4h reversion from 2026-01-02); and you should run the Presto/Aalto falsification regression first and report the null.

**S3 — HAR-RV volatility forecast driving volatility-targeted position sizing.**
Feature: realized volatility from 5-minute log returns, aggregated into a causal HAR cascade (Corsi), re-specified for a 24/7 clock with 365-day annualization per our project rules. Use: `position = target_vol / forecast_vol`, applied as an overlay to whatever baseline strategy exists.
Grounding: Corsi (2009) for the model; Alsamaani & Aldhahi (2026) for the crypto-specific, out-of-sample, Diebold-Mariano-tested finding that HAR beats the GARCH family **at short horizons** on 5-minute crypto data; Harvey et al. (2018) for what volatility targeting does and does not deliver.
**Honest limits, and this one matters**: Harvey et al. attribute the Sharpe improvement to the **leverage effect**, and Ardia et al. document an **inverted** leverage effect in Bitcoin in *both* volatility regimes. So **pre-specify the tail/drawdown reduction as the hypothesis, and explicitly pre-specify that a Sharpe improvement is not expected.** Cederburg et al.'s finding (volatility management helps in only ~half of 103 cases) is the right prior. Also pre-commit to reporting turnover cost, which is the standard objection.

### What is honestly not implementable

- **Anything using liquidations.** No liquidation feed exists in our data and Binance publishes no historical liquidation archive. Every domain-4 result that depends on forced-fill volume, liquidation intensity or liquidation clustering is out of reach. The taker-flow part is not: `taker_buy_base`/`taker_buy_quote` in our 5m klines give a taker order-flow imbalance, and its **variance compression** is the one cross-event regularity the cascade preprints report — computable, and worth a descriptive EDA figure, but the source is unreviewed and the author himself calls it a population-level precursor rather than an alarm.
- **True cash-and-carry / basis arbitrage.** Requires spot execution. Christin et al., Schmeling et al. and He et al.'s actual trade are all off the table.
- **Reconstructing the premium index ourselves.** It needs impact bid/ask prices computed against the order book at an Impact Margin Notional. No book, no reconstruction. Use `premiumIndexKlines` instead — Binance publishes the output.
- **Cross-sectional funding stat-arb.** Two assets is not a cross-section. This kills the only version of the funding signal that Presto found promising.
- **Cross-venue funding or price-discovery work.** Single venue, no DEX data. Rules out the two-tiered-market paper and all information-share studies.
- **Mark-minus-last as a smooth dislocation measure.** Expected to be censored at zero by the median operator (see above) — verify empirically, then most likely discard in favour of the premium index.
- **Open interest** was on this list; based on the S3 listing above, it should not be. `data/futures/um/daily/metrics/BTCUSDT/` from 2020-09-01 at 5-minute resolution appears to give `sum_open_interest`, `sum_open_interest_value`, top-trader and account long/short ratios and taker long/short volume ratio. Confirm the schema by unzipping one day, check the known 2023-09-18 gap (fixed by Binance in Nov 2023), and note that these series exist only from Sept 2020 — which will constrain the start of any OI-dependent experiment and must be reconciled with the data contract's development window.

**On research-integrity constraints for all three signals**: every feature above is a causal, past-only transformation, but two need explicit care. The funding rate must be attached to its **settlement timestamp** and then lagged, never forward-filled backwards into the window it was computed over. The premium index and index price are 5-minute bars labelled by open time on the same left-closed convention as the klines, so they align, but the alignment must be asserted in a test rather than assumed. And none of the three may be tuned, thresholded or regime-classified using any data at or after `holdout_start`.