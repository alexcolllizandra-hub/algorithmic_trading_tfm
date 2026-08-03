# ADR 0005: Provisional transaction-cost assumptions

- Status: Proposed (provisional — must be confirmed before final results)
- Date: 2026-08-03

## Context

Net-of-cost performance is central to every Chapter 5 hypothesis, so the
backtester needs an explicit transaction-cost model. The exact Binance USDT-M
perpetual fee schedule applicable to this account tier over the study period has
**not yet been confirmed and approved**. Fabricating a precise fee silently
would compromise research integrity.

## Decision

Adopt the following **provisional** values in `configs/experiment.yaml → costs`,
clearly flagged `provisional: true`, until confirmed:

- Taker fee: **0.040% per side** (VIP-0 style).
- Maker fee: **0.020% per side**.
- Baseline slippage: **1 bp per side** on the next-bar open; robustness sweep
  {0, 1, 2, 5} bp.
- Funding: realised on open positions at funding timestamps, aligned as-of past.
- Default execution assumption: **taker** (conservative).

## Consequences

- All development-phase backtests are labelled as using *provisional* costs.
- Before any number is reported as final (and before the holdout evaluation),
  the fee schedule must be verified against Binance's published USDT-M futures
  fees for the relevant tier and period; this ADR is then updated to *Accepted*
  (or superseded) and `experiment.yaml` costs are set to `provisional: false`.
- Robustness tests already stress higher costs, so conclusions should be
  reported with explicit sensitivity to the cost assumption.
