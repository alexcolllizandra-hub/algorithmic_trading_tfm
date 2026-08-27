# Volatility-forecasting experiment (deep learning annex) — pre-specification

**Status: FROZEN before any model is fitted.** This annex experiment tests
the one place where Chapter 5 measured real predictable structure —
volatility, not direction — and asks whether a deep sequence model adds
anything over the classical benchmark. It is an annex: it produces no
trading strategy, touches no promotion gate, and never loads the holdout.

## Question

Does an LSTM improve out-of-sample forecasts of next-24h realized volatility
over the HAR-RV benchmark and a persistence baseline, on BTC and ETH hourly
bars, under the study's own walk-forward geometry?

## Design (frozen)

- **Data:** development partition only (2020-01 → 2025-12), 1h bars, both
  symbols, loaded through the gated `DataLake`.
- **Target:** `log RV(t+1..t+24)`, where RV is the square root of the sum of
  squared 1h log-returns over the next 24 bars (annualisation constant
  irrelevant to ranking; logs stabilise the heavy right tail).
- **Folds:** the study's expanding walk-forward exactly as configured
  (`configs/experiment.yaml: walk_forward` — 730/90/90/90 days, 15 folds,
  purge 24 bars for this experiment: the target horizon; no label overlap
  beyond it). Fit on train, tune early stopping on validation, evaluate once
  on test, concatenate test segments.
- **Models:**
  1. `naive` — persistence: forecast log RV of the next 24h with the
     realized log RV of the last 24h.
  2. `har` — HAR-RV (Corsi 2009): OLS of the target on log RV over the past
     24h, 168h and 720h. Fitted per fold on train+validation.
  3. `lstm` — single-layer LSTM, hidden size 32, input = per-bar features
     (log |return|, log return, log RV-24 level) over a 96-bar window,
     linear head; Adam lr 1e-3, batch 256, max 40 epochs, early stopping on
     validation QLIKE with patience 5; seeds {42, 43, 44}, reported as
     mean ± range across seeds. Inputs standardised with train-only moments.
- **Metrics:** MSE on log RV, QLIKE (evaluated on RV levels), and
  out-of-sample R² against the naive baseline
  (R²_oos = 1 − MSE_model / MSE_naive), all computed on the concatenated
  test segments per symbol; Diebold–Mariano test (squared-error loss,
  Newey–West with lag 24) for HAR vs LSTM.
- **Decision rule (written in advance):** the LSTM "adds value" only if it
  beats HAR on QLIKE on the concatenated OOS series for BOTH symbols and the
  DM test rejects at 5% in its favour on at least one. Anything less is
  reported as "no material improvement over the classical benchmark".

## What this is not

Not a trading strategy, not a promotion candidate, and not evidence about
direction. If the LSTM wins, the correct thesis statement is that variance
structure is learnable — which Chapter 5 already established with mutual
information — and that the margin over HAR is [whatever it measures].
