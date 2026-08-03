# Causal Feature Catalogue (Chapter 5.3) — v0.1

Every feature is **causal**: computed from information available at or before
the bar it is attached to, and **shifted ≥ 1 bar** before it can influence a
signal or a model. Signals derived at the close of bar *t* execute at the
**open of bar *t+1*** (see `experimental_design.md` §12).

**Implementation status (v0.2 — config-driven engine).** The `features/`
package is now a small **configuration-driven registry**:
`features/spec.py` declares every feature *kind* and its full contract
(`KIND_REGISTRY` + serialisable `FeatureSpec`); `features/causal.py` holds the
pure, causal column builders; `features/registry.py` resolves a requested set
(`resolve_feature_set`) and builds it (`build_feature_frame`). The concrete set
built by the development pipeline is selected in
`configs/experiment.yaml → features.feature_set` and validated at load time
(unknown kind / bad window / bad lag → hard error). The resolved metadata is
written to each run's `feature_metadata.json`.

The default set is **14 columns** (BTCUSDT/ETHUSDT 1h, same code, no
duplication): `log_return`, `momentum_12`, `momentum_24`, `sma_24`, `sma_96`,
`price_dist_sma_48`, `zscore_48`, `rvol_96`, `atr_14`, `range_norm`,
`rel_volume_24`, `hour_sin`, `hour_cos`, plus the lagged `taker_buy_imbalance`
context feature. `volume_zscore_w` and `dow_sin/dow_cos` are **registered and
available** but excluded from the default set to avoid redundancy. Each shipped
feature has causal-invariance tests
(`tests/unit/test_features_causal.py`, `tests/unit/test_features_registry.py`).
The remaining rows below stay *Planned*.

Conventions:
- **Timeframe:** primary = 1h unless noted. Windows are in bars of that
  timeframe. Values come from `configs/experiment.yaml → features`.
- **Availability timestamp:** the earliest wall-clock time the input is known.
  For a bar closing at `t_close`, close-based inputs are available at `t_close`.
- **Required shift:** additional lag applied before use (≥ 1 bar for all).
- **Missing-value policy:** how NaNs (warm-up, zero-denominator, unmatched
  auxiliary timestamps) are treated. Auxiliary streams are joined **as-of past**
  and never forward-filled into the future.
- **Consumer:** BS = baseline strategy, GA = genetic strategy, ML = meta-label,
  RG = regime model, RK = risk.

## A. Interpretable strategy features

Built from OHLCV klines only. These define the shared strategy space searched by
Random Search and the GA.

| Feature | Family | Formula / calculation | Input columns | Lookback | Availability | Shift | Missing policy | Consumer | Leakage risk | Status |
|---------|--------|-----------------------|---------------|----------|--------------|-------|----------------|----------|--------------|--------|
| `log_return_k` | Returns | `ln(close_t / close_{t-k})` | close | k ∈ {1,3,6,12,24} | bar close | ≥1 | warm-up NaN | BS,GA,ML | Low (past-only) | Implemented (k=1) |
| `abs_return`, `sq_return` | Returns | `|r_1|`, `r_1^2` | close | 1 | bar close | ≥1 | warm-up NaN | RG,ML | Low | Planned |
| `sma_w`, `ema_w` | Moving average | rolling / exp mean of close | close | w ∈ {12,24,48,96,168} | bar close | ≥1 | warm-up NaN | BS,GA | Low | sma Implemented; ema Planned |
| `ma_cross` | Momentum | sign(`sma_fast` − `sma_slow`) | close | fast/slow | bar close | ≥1 | warm-up NaN | BS,GA | Low | Planned |
| `momentum_w` | Momentum | `ln(close_t / close_{t-w})` over w | close | w ∈ {12,24,72} | bar close | ≥1 | warm-up NaN | BS,GA | Low | Implemented (12, 24) |
| `price_dist_sma_w` | Trend | `close_t / sma_w − 1` (scale-free) | close | w ∈ {12,24,48,96,168} | bar close | ≥1 | warm-up NaN; sma≤0→NaN | BS,GA,ML | Low | Implemented (48) |
| `donchian_high_w`, `donchian_low_w` | Breakout | rolling max(high)/min(low) **excluding current bar** | high, low | w ∈ {24,48,96} | bar close | ≥1 | warm-up NaN | BS,GA | Medium (must exclude bar t) | Planned |
| `breakout_flag` | Breakout | close > `donchian_high_w` (long) / < low | close, donchian | w | bar close | ≥1 | warm-up NaN | BS,GA | Medium | Planned |
| `rsi_w` | Oscillator | Wilder RSI | close | w ∈ {14,24} | bar close | ≥1 | warm-up NaN | BS,GA | Low | Planned |
| `zscore_w` | Mean reversion | `(close − sma_w) / std_w` (sample std) | close | w ∈ {24,48,96} | bar close | ≥1 | warm-up NaN; std=0→NaN | BS,GA | Low | Implemented (48) |
| `atr_w` | Volatility | trailing mean of true range (uses prev close) | high, low, close | w ∈ {14,24,48} | bar close | ≥1 | warm-up NaN | BS,GA,RK | Low | Implemented (14; SMA of TR) |
| `range_norm` | Range | `(high − low) / close` (current bar) | high, low, close | 1 | bar close | ≥1 | close≤0→NaN | BS,GA,ML,RG | Low | Implemented |
| `rvol_w` | Volatility | rolling std of 1-bar log return | close | w ∈ {24,96,168} | bar close | ≥1 | warm-up NaN | BS,GA,RG,RK | Low | Implemented (96) |
| `rel_volume_w` | Activity | `volume / rolling_mean(volume, w)` | volume | w ∈ {24,96} | bar close | ≥1 | mean≤0→NaN | BS,GA | Low | Implemented (24) |
| `volume_zscore_w` | Activity | `(volume − mean_w) / std_w` | volume | w ∈ {24,96} | bar close | ≥1 | warm-up NaN; std=0→NaN | GA,ML,RG | Low | Implemented (available, off by default) |
| `vol_regime` | Regime filter | past-only bucket of `rvol_w` into low/med/high via **expanding** quantiles | close | regime_vol_windows | bar close | ≥1 | warm-up→"unknown" | BS,GA,RG | **High if full-sample** → must be expanding | Planned |

> Note on `vol_regime`: the EDA `regimes.py` tag uses **full-sample** quantiles
> and is *descriptive only*. The Chapter 5 causal version must use **expanding /
> rolling** quantiles so no future information sets the thresholds.

## B. Contextual meta-labeling features

Used **only** by the meta-labeling model to decide whether/how much to act on a
base signal. Contemporaneous microstructure variables are **lagged** and treated
as context, never as contemporaneous predictors.

| Feature | Family | Formula / calculation | Input columns | Lookback | Availability | Shift | Missing policy | Consumer | Leakage risk | Status |
|---------|--------|-----------------------|---------------|----------|--------------|-------|----------------|----------|--------------|--------|
| `funding_rate` | Funding | latest funding rate as-of past | fundingRate | event (8h) | funding time | ≥1 bar after funding time | as-of past join; no ffill to future | ML,RK | Medium (align as-of past) | Planned |
| `funding_change_w` | Funding | change in funding over w intervals | fundingRate | w ∈ {3,8,24} | funding time | ≥1 | as-of past | ML | Medium | Planned |
| `funding_sign_run` | Funding | length of current same-sign funding run (past) | fundingRate | expanding | funding time | ≥1 | as-of past | ML | Medium | Planned |
| `basis_bps_lag` | Basis | `1e4*(trade_close−mark_close)/mark_close`, **lagged** | close, mark close | matched ts | bar close | ≥1 | matched ts only; no imputation | ML | **High if contemporaneous** → must lag | Planned |
| `taker_buy_imbalance_lag` | Order flow | `2*(taker_buy_quote/quote_volume)−1`, **lagged** | taker_buy_quote, quote_volume | 1 | bar close | ≥1 | denom=0→NaN (no inf) | ML | **High if contemporaneous** → must lag | Implemented (context) |
| `btc_eth_corr_w` | Cross-asset | rolling corr of BTC/ETH `log_return_1` | close (both) | w ∈ {168,336} | bar close | ≥1 | warm-up NaN; aligned ts | ML,RK | Medium (alignment) | Planned |
| `btc_eth_beta_w` | Cross-asset | rolling OLS beta of asset vs. BTC | close (both) | w | bar close | ≥1 | warm-up NaN | ML | Medium | Planned |
| `vol_regime` (context) | Regime | causal expanding vol-regime bucket | close | regime_vol_windows | bar close | ≥1 | warm-up→"unknown" | ML | High if full-sample | Planned |
| `hour_sin`, `hour_cos` | Temporal | cyclical UTC hour-of-day encoding | open_time | n/a | bar open | 0 (known ex-ante) | none | ML,RG | None | Implemented |
| `dow_sin`, `dow_cos` | Temporal | cyclical UTC day-of-week encoding | open_time | n/a | bar open | 0 (known ex-ante) | none | ML,RG | None | Implemented (available, off by default) |
| `signal_side`, `signal_strength` | Signal meta | direction and magnitude of the base signal | base signal | n/a | bar close | ≥1 | none | ML | Low | Planned |
| `bars_since_last_trade` | Signal meta | recency of prior base trade | trade log | expanding | bar close | ≥1 | none | ML | Low | Planned |

## Leakage-critical rules (summary)

1. Donchian/rolling extrema for breakouts **exclude the current bar**.
2. Volatility-regime thresholds are **expanding/rolling**, never full-sample.
3. `basis_bps` and `taker_buy_imbalance` are **lagged ≥ 1 bar**; zero
   denominators become missing (no infinities).
4. Funding and mark price are joined **as-of the past** with a declared
   tolerance and never forward-filled into the future.
5. **Shift semantics.** Close-based indicators are recorded with `shift = 0`
   and *availability = "close t"*; the mandatory decision→execution delay to the
   **open of bar *t+1*** is applied once, by the backtester (not by an extra
   feature shift). Contextual microstructure variables carry an explicit
   `shift = lag ≥ 1`. Cyclical calendar encodings are the ex-ante exception
   (`shift = 0`, known before the bar). This is enforced by
   `test_availability_metadata_is_consistent`.
6. The `features/` engine ships **leakage-validation tests** covering the 15
   invariants (truncation invariance, future-mutation invariance, exact-once
   shift, deterministic warm-up/null, no infinities, flat/zero/constant safety,
   alignment, input immutability, deterministic column order, multi-asset
   independence, reproducibility, holdout isolation) in
   `tests/unit/test_features_causal.py` and `tests/unit/test_features_registry.py`.
7. Each implemented feature registers a full, serialisable contract
   (`features/spec.py`): name, family, inputs, asset/timeframe dependency,
   params/lookback, availability, shift, warm-up, null/inf policy, consumers,
   leakage risk, output dtype and an implementation version, written into every
   run's `feature_metadata.json`.
