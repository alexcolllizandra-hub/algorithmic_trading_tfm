# Chapter 7 figure captions (English)

Common frame unless stated: engine = random_search (the study's confirmatory
engine); assets = BTCUSDT and ETHUSDT; 10 seeds per cell; OOS window =
concatenated walk-forward test slices 2022-03-31 to 2025-12-09 (32,385 bars of
1h); unit of analysis = one seed's concatenated OOS series. Spread across
seeds is DISPERSION under search randomness, never a confidence interval, and
seeds are not independent market histories (they share the same bars).
Benchmark in every equity figure = the study's funded always-long perp
baseline (real per-bar funding + 5 bps entry at the contract cost rate), the
same series behind `bh_total_return`; a price-only benchmark would differ
(+100.7% vs +52.3% on BTC) and is deliberately not drawn.

- **Fig 7.1 (fig_7_1_r2_oos_equity).** R2 momentum: concatenated OOS equity of
  all 10 RS seeds against the funded buy-and-hold baseline on the same bars,
  BTC and ETH. Curve endpoints equal the tabulated totals (checked, tol 1e-6).
- **Fig 7.2 (fig_7_2_r3_families).** R3: per-seed annualised Sharpe of the
  concatenated OOS series for the five families, both assets; dash = mean
  across seeds. Aggregation differs from the fold-mean Sharpe used in Fig 7.5.
- **Fig 7.3 (fig_7_3_volbreakout_partial_signal).** volatility_breakout on
  BTC: (a) seeds passing each evaluated criterion vs the 6/10 majority;
  (b) OOS equity of all 10 seeds vs the funded benchmark.
- **Fig 7.4 (fig_7_4_crt_complementary).** CRT round: (a) pdl_reclaim_long BTC
  equity, all 10 seeds vs funded benchmark - positive on every seed yet
  unpromotable (no bootstrap CI excludes zero); (b) ETHUSDT criteria map,
  complementing the BTC map in chapter 6 (j05).
- **Fig 7.5 (fig_7_5_s3_seed_distributions).** Gate S3: per-seed MEAN
  FOLD-TEST Sharpe (each seed: mean over its 15 fold-test evaluations) of the
  overlay vs the R2 carrier. NOT seed-paired and not a causal isolation of the
  calendar filter (reduced carrier grid; budget shared with gate parameters).
  This fold-weighted aggregation differs numerically from the bar-weighted
  concatenated Sharpe of Figs 7.2/7.6.
- **Fig 7.6 (fig_7_6_rounds_synthesis).** All sixteen full-study families:
  mean and min-max across seeds of the concatenated-OOS annualised Sharpe,
  by round. S1/S2 pilots excluded (1 and 3 seeds, budget 25 - different
  design; see the pilot tables).
- **Fig 7.7 (fig_7_7_crt_example_illustrative).** Mechanics of
  pdl_reclaim_long on one real archived trade (first trade of fold 0, seed
  891022, RS - selection rule fixed in advance, not by outcome): previous-day
  low, sweep, reclaim, next-bar-open entry and the engine-recorded exit. The
  engine ledger does not label CRT-internal exits (stop/target/time), so the
  exit is annotated only as recorded. Illustrative; not additional evidence.
