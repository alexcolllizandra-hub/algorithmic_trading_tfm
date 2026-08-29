# CH8 table captions (English)

- **Table 8.1. Simulation design, uncertainty layers and evaluation units.**
  The three layers (search / path / combined), what varies in each, the unit
  of analysis, the path budget, and whether the layer was frozen or is a
  post-hoc diagnostic. The combined layer mixes seeds by design and is not
  ten market replications.
- **Table 8.2. Observed OOS characteristics of the selected BTC candidates.**
  One row per seed: net total return, annualised concatenated Sharpe, maximum
  drawdown (positive magnitude), longest drawdown duration (days), time under
  water, trades. Observed record only — no simulation.
- **Table 8.3. Conditional bootstrap outcomes under the primary
  specification.** Hierarchical stationary-block simulation (4,000 paths per
  family, ACF-derived block): terminal-equity quantiles, P(terminal < 1) with
  Monte Carlo SE, P(loss > 20%), 5% expected shortfall of terminal return and
  recovery probability. Conditional on the observed record.
- **Table 8.4. Profit concentration and trade-sequence diagnostics.**
  Per-family medians over the 10 seeds: top-5 share of positive P&L, seeds
  still positive after removing their 5 best trades (matches the chapter-7
  criterion), win rate, worst losing streak, and where the chronological
  drawdown sits inside the order-permutation distribution. Per-seed detail in
  `ch8_trade_concentration.csv`.
- **Table 8.5. Capital-breach probabilities across exposure multipliers.**
  P(min equity < 90/80/70/50%) per multiplier under r → m·r with zero
  absorption; hierarchical primary paths; MC SE and Wilson bounds in the
  companion CSV.
- **Table 8.6. Sensitivity to bootstrap method and block length.** Terminal
  and drawdown quantiles per method × block cell (2,000 paths each); the
  primary cell is flagged.
- **Table 8.7. Account-threshold outcomes (illustrative).** Verbatim from the
  executed notebook-07 prop-firm simulation (frozen published-rule configs,
  volatility_breakout only; pdl_reclaim_long NOT EVALUATED under this
  scenario). Illustrative pass rates conditional on the recorded history —
  not guaranteed future probabilities.
