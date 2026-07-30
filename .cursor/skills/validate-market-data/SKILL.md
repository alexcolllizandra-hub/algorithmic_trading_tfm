---
name: validate-market-data
description: Run and interpret data-quality checks on ingested klines (gaps, duplicates, OHLC consistency, extreme-move flags, coverage per asset/timeframe). Use when verifying dataset quality or diagnosing anomalies in the perp-lab thesis data.
disable-model-invocation: true
---

# Validate market data

## Workflow

1. Run the report: `uv run perp-lab validate --config configs/data_contract.yaml`.
   It writes `reports/tables/quality_report.csv` and prints a summary.
2. For deeper inspection, use `perp_lab.validation.quality` directly:
   - `find_gaps(df, timeframe)` -> missing-candle spans,
   - `find_duplicates(df)` -> repeated timestamps,
   - `check_ohlc_consistency(df)` -> invalid bars,
   - `flag_extreme_returns(df, sigma, window)` -> flagged (not dropped) moves,
   - `coverage_summary(df, timeframe, start, end)` -> present vs expected.
3. Structural validation: `validate_klines(df)` / `validate_funding(df)`.

## Interpretation rules

- **Flag, never auto-drop.** Decide per case whether an extreme move is a data
  error or a real event, and document the decision (ADR or notebook cell).
- Gaps around exchange incidents are expected; record them rather than hiding
  them.
- Cross-check derived 15m/1h bars against Binance native klines when in doubt.
