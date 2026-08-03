# Temporal Validation, Costs, Metrics & Robustness (Chapter 5.7–5.8) — v0.1

Specifies how candidates are validated in time, how costs are charged, which
metrics decide performance, and which robustness tests must pass before the
single final holdout evaluation. Authoritative values:
[`configs/experiment.yaml`](../../configs/experiment.yaml). Status:
**specification only**.

## 1. Data-role separation

Information flows forward in time through four **disjoint** roles:

1. **Training** — fit strategy behaviour / meta-label models.
2. **Validation / candidate selection** — choose candidates, calibrate
   probabilities, tune the meta-label threshold. Never used to fit base models.
3. **Walk-forward OOS** — the test slice of each fold; the primary evidence.
4. **Frozen holdout** `[2026-01-01, 2026-07-01)` — opened once, at the end.

## 2. Recommended walk-forward geometry (with justification)

**Expanding (anchored) window** over the development period
`[2020-01-01, 2026-01-01)` (~6 years, 24/7):

- `initial_train_days = 730` (≥ 2 years) — enough history to span at least one
  full bull/bear cycle and to estimate longer-window features (e.g. 336-bar MAs)
  and volatility regimes before the first OOS prediction.
- `validation_days = 90`, `test_days = 90`, `step_days = 90` — quarterly,
  **non-overlapping** OOS folds give multiple independent regimes across
  2022–2025 while keeping each slice large enough for stable metrics.
- Result: ~16 chronological OOS folds (`min_folds = 8` guard).

**Why expanding, not sliding:** an anchored window uses all available past,
matching how the strategy would run live, and avoids discarding early regimes;
a sliding window is offered as a robustness variant. The geometry is a
**recommendation pending confirmation** (open decision), not a silent default.

## 3. Purging and embargo (derived, not arbitrary)

Triple-barrier labels and open positions span multiple bars, so training and
test can overlap in time. Therefore:

- **Purge:** drop training observations whose label horizon / holding period
  overlaps the validation or test window. Size = `max(label_horizon,
  max_holding)` = `max(vertical_barrier_bars, max(max_holding_bars))`. With the
  provisional 1h values (`vertical_barrier_bars = 24`, `max_holding_bars ≤ 96`)
  this is **96 bars ≈ 4 days**.
- **Embargo:** after each test window, embargo `purge_bars + 1% · test_span`
  before training resumes (~4–5 days), preventing leakage from serially
  correlated features straddling the boundary.

Both are computed at runtime from the labeling/strategy config, never hard-coded.

## 4. Cost-aware execution model

- **Next-bar execution:** signal at close *t* → fill at **open *t+1***.
- **Fees (provisional, ADR pending):** taker 0.040%/side, maker 0.020%/side;
  default assumes conservative taker fills.
- **Slippage (provisional):** 1 bp/side baseline on the fill price; robustness
  sweeps {0,1,2,5} bp.
- **Funding:** paid/received on open positions at funding timestamps, aligned
  **as-of past** (funding known before it is charged).
- **Position overlap:** single-asset backtests hold ≤ 1 position at a time by
  default (new same-direction signals do not stack; opposite signals close then
  reverse). Cross-asset portfolios sum per-asset exposure under the gross cap.
- **Leverage / exposure limits:** `risk.max_position_leverage` (provisional 3×),
  `risk.max_gross_exposure` (1× single-asset).
- **Missing-price handling:** bars with missing/zero prices are skipped for
  execution; no fabricated fills; gaps documented (EDA found none in
  development trading-price klines).
- **Overlapping triple-barrier events:** handled by purging in CV and by
  event-level (not bar-level) meta-label sampling.

## 5. Evaluation metrics

Reported **net of costs**, per **asset**, per **fold**, and per **volatility
regime**:

- Net return (cumulative and annualised).
- Annualised volatility (365-day convention).
- Sharpe ratio, Sortino ratio.
- Maximum drawdown, Calmar ratio.
- Profit factor, hit rate.
- Expected Shortfall (e.g. 95%).
- Turnover, number of trades, average holding time.
- Exposure (time in market, average leverage).

Gross metrics are shown only as context alongside net metrics.

## 6. Robustness battery

Applied to promoted candidates **before** the holdout:

- **Higher fees/slippage:** extra round-trip cost {2,5,10} bp.
- **Parameter perturbation:** ±{5,10,20}% jitter on numeric parameters; report
  performance dispersion (fragile if it collapses).
- **Delayed execution:** fill 1–2 bars later than next-bar open.
- **Subperiod stability:** metrics per calendar year.
- **Asset transfer:** fit on one asset, evaluate on the other.
- **Regime-conditioned:** metrics by causal volatility regime.
- **Trade-order bootstrap / Monte Carlo:** 1000 resamples of the trade sequence
  → distribution of Sharpe / drawdown.
- **Deflated / probabilistic Sharpe:** correct for the number of trials
  searched (multiple-testing / selection bias).
- **Benchmarks:** buy-and-hold, flat cash, random-entry matched-exposure.

## 7. Final holdout evaluation

Performed **once**, after all selection and robustness analysis: the promoted
configuration(s) are frozen, then evaluated on `[2026-01-01, 2026-07-01)` with
the identical, unchanged pipeline and cost model. No parameter, threshold or
feature is adjusted afterwards. Any divergence between OOS and holdout results is
reported honestly rather than tuned away.
