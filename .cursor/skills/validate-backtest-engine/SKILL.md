---
name: validate-backtest-engine
description: Verify the cost-aware next-bar backtester in src/perp_lab/backtesting for correct execution timing, cost accounting, determinism and holdout isolation. Use after any change to the engine or a strategy it evaluates.
disable-model-invocation: true
---

# Validate the backtest engine

Owner: **verifier** (read-only preference) with strategy-backtest-engineer.

## Purpose & triggers
Confirm, with executable tests, that the backtester is leakage-free and its PnL
accounting is honest and deterministic. Trigger: engine or strategy change.

## Required inputs
- The engine entry point and its cost/slippage parameters.
- The execution convention (next-bar open) from `validation_protocol.md`.

## Files it MAY modify
- `tests/unit/test_backtesting*.py` (only to add missing verification tests).

## Files it MUST NOT modify
- `src/perp_lab/**` production code; methodology; config.

## Prerequisites
- A deterministic strategy and small synthetic price series are available.

## Procedure
Build tiny hand-checkable price/signal frames and assert each invariant below.

## Mandatory invariants / required tests
1. A signal at close *t* executes no earlier than *t+1* (delayed entry: position
   during bar *t* is flat).
2. No same-bar execution using unavailable prices (entry at next-bar open).
3. Long, short and flat transitions are accounted for correctly.
4. Fees reduce equity by the expected deterministic amount.
5. Slippage is applied in the adverse direction for buys and sells.
6. Funding timestamps (if funding is enabled) align as-of past, no look-ahead.
7. Stop-loss / take-profit precedence is correct (if implemented).
8. PnL, equity and trade accounting are internally consistent.
9. Repeating with the same data/config/seed gives identical results.
10. No data from the frozen holdout is read.

## Generated artifacts
- A pass/fail report per invariant with references.

## Stop conditions
- Any invariant fails: stop and report the exact case; do not alter cost or
  timing conventions to make a test pass.

## Completion report (exact)
- Per-invariant pass/fail; the exact commands executed and outputs; any
  convention that is provisional (e.g. funding not yet included) stated plainly.
