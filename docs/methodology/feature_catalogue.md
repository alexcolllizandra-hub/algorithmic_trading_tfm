# Causal Feature Catalogue (Chapter 5.3) — v0.1

Every feature is **causal**: computed from information available at or before
the bar it is attached to, and **shifted ≥ 1 bar** before it can influence a
signal or a model. Signals derived at the close of bar *t* execute at the
**open of bar *t+1*** (see `experimental_design.md` §12). This catalogue is a
specification; the `features/` engine is **not implemented yet** (status:
*Planned*).

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
| `log_return_k` | Returns | `ln(close_t / close_{t-k})` | close | k ∈ {1,3,6,12,24} | bar close | ≥1 | warm-up NaN | BS,GA,ML | Low (past-only) | Planned |
| `abs_return`, `sq_return` | Returns | `|r_1|`, `r_1^2` | close | 1 | bar close | ≥1 | warm-up NaN | RG,ML | Low | Planned |
| `sma_w`, `ema_w` | Moving average | rolling / exp mean of close | close | w ∈ {12,24,48,96,168} | bar close | ≥1 | warm-up NaN | BS,GA | Low | Planned |
| `ma_cross` | Momentum | sign(`sma_fast` − `sma_slow`) | close | fast/slow | bar close | ≥1 | warm-up NaN | BS,GA | Low | Planned |
| `momentum_w` | Momentum | cumulative return over w | close | w ∈ {12,24,72} | bar close | ≥1 | warm-up NaN | BS,GA | Low | Planned |
| `donchian_high_w`, `donchian_low_w` | Breakout | rolling max(high)/min(low) **excluding current bar** | high, low | w ∈ {24,48,96} | bar close | ≥1 | warm-up NaN | BS,GA | Medium (must exclude bar t) | Planned |
| `breakout_flag` | Breakout | close > `donchian_high_w` (long) / < low | close, donchian | w | bar close | ≥1 | warm-up NaN | BS,GA | Medium | Planned |
| `rsi_w` | Oscillator | Wilder RSI | close | w ∈ {14,24} | bar close | ≥1 | warm-up NaN | BS,GA | Low | Planned |
| `zscore_w` | Mean reversion | `(close − sma_w) / std_w` | close | w ∈ {24,48,96} | bar close | ≥1 | warm-up NaN; std=0→NaN | BS,GA | Low | Planned |
| `atr_w` | Volatility | Wilder ATR of true range | high, low, close | w ∈ {14,24,48} | bar close | ≥1 | warm-up NaN | BS,GA,RK | Low | Planned |
| `rvol_w` | Volatility | rolling std of `log_return_1` | close | w ∈ {24,96,168} | bar close | ≥1 | warm-up NaN | BS,GA,RG,RK | Low | Planned |
| `rel_volume_w` | Activity | `volume / rolling_mean(volume, w)` | volume | w ∈ {24,96} | bar close | ≥1 | mean=0→NaN | BS,GA | Low | Planned |
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
| `taker_buy_imbalance_lag` | Order flow | `2*(taker_buy_quote/quote_volume)−1`, **lagged** | taker_buy_quote, quote_volume | 1 | bar close | ≥1 | denom=0→NaN (no inf) | ML | **High if contemporaneous** → must lag | Planned |
| `btc_eth_corr_w` | Cross-asset | rolling corr of BTC/ETH `log_return_1` | close (both) | w ∈ {168,336} | bar close | ≥1 | warm-up NaN; aligned ts | ML,RK | Medium (alignment) | Planned |
| `btc_eth_beta_w` | Cross-asset | rolling OLS beta of asset vs. BTC | close (both) | w | bar close | ≥1 | warm-up NaN | ML | Medium | Planned |
| `vol_regime` (context) | Regime | causal expanding vol-regime bucket | close | regime_vol_windows | bar close | ≥1 | warm-up→"unknown" | ML | High if full-sample | Planned |
| `hour_sin`, `hour_cos`, `dow_sin`, `dow_cos` | Temporal | cyclical UTC hour / day-of-week encodings | open_time | n/a | bar open | 0 (known ex-ante) | none | ML | None | Planned |
| `signal_side`, `signal_strength` | Signal meta | direction and magnitude of the base signal | base signal | n/a | bar close | ≥1 | none | ML | Low | Planned |
| `bars_since_last_trade` | Signal meta | recency of prior base trade | trade log | expanding | bar close | ≥1 | none | ML | Low | Planned |

## Leakage-critical rules (summary)

1. Donchian/rolling extrema for breakouts **exclude the current bar**.
2. Volatility-regime thresholds are **expanding/rolling**, never full-sample.
3. `basis_bps` and `taker_buy_imbalance` are **lagged ≥ 1 bar**; zero
   denominators become missing (no infinities).
4. Funding and mark price are joined **as-of the past** with a declared
   tolerance and never forward-filled into the future.
5. Every feature is shifted ≥ 1 bar; signals at close *t* fill at open *t+1*.
6. The `features/` engine will ship with **leakage-validation tests** (a feature
   recomputed on a truncated history must equal the same feature on the full
   history up to the truncation point).
