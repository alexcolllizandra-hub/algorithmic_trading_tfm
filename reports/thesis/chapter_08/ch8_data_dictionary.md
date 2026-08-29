# CH8 data dictionary

## ch8_input_returns.csv (+ .parquet, identical content)

One row per candidate × seed × OOS bar. 2 candidates × 10 seeds × 32,385 bars.
Source: `random_search_fold{0..14}_test_equity.parquet` under each run dir
(paths in `ch7_results_units.csv`), concatenated chronologically per seed.

| Column | Unit / sign | Definition | Provenance |
|---|---|---|---|
| family, symbol, engine, seed | — | identifiers (engine always random_search here) | run dir |
| fold_id | 0–14 | outer walk-forward test fold the bar belongs to | file name |
| timestamp | UTC, bar open | `open_time` of the holding interval [open_t, open_{t+1}) | ledger |
| oo_return_net | simple return/bar, ± | the strategy's NET per-bar return (`net_return`): position × market − fees − slippage − funding. Costs/funding already inside — never re-charge them | ledger |
| equity | multiple of initial capital | cumprod(1 + oo_return_net) over the concatenated series, recomputed (the per-fold ledger `equity` restarts at 1 each fold and is NOT used) | derived, exact |
| position | −1/0/+1 (CRT may be fractional intrabar) | position held during the bar | ledger |
| exposure | \|position\| | absolute exposure | derived |
| turnover | units of position change | \|Δposition\| charged at the cost rate | ledger |
| fees / slippage | return units/bar, ≥0 | the bar's fee and slippage charges (separate columns exist at bar level) | ledger |
| funding | return units/bar, ± | realized funding transfer for the held position (as-of-past) | ledger |
| market_oo_return | simple return/bar | the asset's open-to-open return (no costs) — context only | ledger |

## ch8_input_trades.csv

One row per ENGINE TRADE (contiguous episode of non-zero position as the
backtester records it; CRT partial exits happen inside an episode and are NOT
separate rows). Source: `random_search_fold{0..14}_test_trades.parquet`.

| Column | Unit / sign | Definition |
|---|---|---|
| trade_id, fold_id | — | identifiers within the run |
| entry_time / exit_time | UTC | first/last bar of the episode |
| side | long/short | sign of the recorded position |
| holding_bars | bars | `n_bars` as persisted |
| net_return | simple return, ± | compounded net return of the episode (costs and funding inside) |
| funding | return units, ± | funding transferred during the episode |
| fees_plus_slippage | return units, ≥0 | `cost` — fees and slippage are persisted COMBINED at trade level |
| exit_reason | engine label | e.g. `signal_close`; CRT-internal reasons (stop/target/time) are NOT persisted |

**NOT AVAILABLE (never estimated):** entry/exit prices, fees vs slippage
split at trade level, gross_return, net_pnl in currency, equity_before/after,
initial_stop, risk_distance, r_multiple. The ledgers do not persist them; any
figure or table needing them is declared not evaluable.

## Result files

- `ch8_observed_seed_metrics.csv` — one row per candidate×seed (plus R2
  momentum BTC as negative reference, observed columns only). `max_drawdown_pos`
  is the POSITIVE magnitude (chapter-7's `max_drawdown` column is negative);
  `mdd_duration_*` = longest contiguous run strictly below the running peak.
- `ch8_simulation_summary.csv` — per-seed layer rows + hierarchical-primary
  rows; every probability carries `_mc_se` and Wilson 95% bounds.
- `ch8_path_quantiles.csv` — cross-path equity quantiles (p05/p25/p50/p75/p95)
  every 74 bars, plus the observed median-seed curve.
- `ch8_primary_path_metrics.parquet` — the full per-path metric table of the
  hierarchical primary (traceability; figures 8.3/8.4 derive from it).
- `ch8_exposure_sensitivity.csv` / `ch8_breach_probabilities.csv` — the
  multiplier grid; transformation r → m·r with absorption at zero whenever
  1 + m·r ≤ 0 (rule stated in the method contract).
- `ch8_method_sensitivity.csv` — method × block grid.
- `ch8_monte_carlo_convergence.csv` — same stream at budgets 1k/2k/4k.
- `ch8_trade_concentration.csv` — per candidate×seed; definitions in the
  method contract (shares over the SUM OF POSITIVE trade returns; removals
  recompute the compounded product causally via `drop_best_trades`).
- `ch8_trade_secondary_bootstraps.csv` — iid / block-of-trades / permutation
  on the median seed (unit: engine trade).
