# CH8 figure captions (English)

Common frame: BTCUSDT, random_search engine, concatenated OOS window
2022-03-31 → 2025-12-09 (32,385 hourly bars, 15 walk-forward test folds),
net returns after 4+1 bps/side and realized funding. Simulated ranges are
conditional simulation intervals on the observed record — never confidence
intervals on a true edge — and the ten seeds share one market history.

- **Figure 8.1. Observed OOS return and drawdown across RS seeds.** Each dot
  is one seed's observed record (drawdown as positive magnitude); crosses mark
  per-family means. The spread is dispersion under search randomness.
- **Figure 8.2. Conditional bootstrap equity paths for the selected BTC
  candidates.** Hierarchical primary (uniform seed pick, then stationary-block
  resampling at the ACF-derived block), 4,000 paths per family, horizon equal
  to the OOS record, start capital 1. Bands are 5–95% and 25–75% simulated
  ranges; the dashed line is the observed median-by-return seed.
- **Figure 8.3. Simulated terminal-equity distributions.** ECDF of terminal
  wealth over the 4,000 hierarchical paths per family; log x-axis keeps the
  left tail visible; vertical dashes mark initial capital 1.
- **Figure 8.4. Simulated drawdown magnitude and duration.** ECDFs of the
  maximum drawdown (positive %, left) and of the longest time under the prior
  peak (days, right) over the same paths.
- **Figure 8.5. Capital-breach probabilities across exposure levels.**
  P(min equity < barrier) for barriers 90/80/70/50% under return multipliers
  m ∈ {0.25…2.00} (r → m·r, absorption at zero if 1+m·r ≤ 0); values printed
  per cell, common color scale; Monte Carlo SE and Wilson bounds in
  `ch8_breach_probabilities.csv`.
- **Figure 8.6. Sensitivity to resampling method and block length.** Median
  (points) and 5–95% simulated range (lines) of terminal equity, and p95 of
  the maximum drawdown, for stationary vs circular moving-block bootstrap at
  blocks 24/168/720 h plus the ACF-derived primary block; 2,000 paths per
  cell.
- **Figure 8.7. Profit concentration and trade-sequence sensitivity.**
  (a) cumulative sum of sorted trade net returns (engine-trade unit, median
  seed); (b) compounded OOS return after causally removing the k best trades
  (`drop_best_trades`, the chapter-7 convention). Per-seed table in
  `ch8_trade_concentration.csv`; order-permutation results there keep the
  exact trade set and change only the sequence.
