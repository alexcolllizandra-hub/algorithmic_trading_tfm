"""Liquidity and activity proxies from OHLCV data.

These are *proxies*: OHLCV klines do not expose the order book, so measures such
as dollar volume, the Amihud illiquidity ratio, the normalised high-low range
and ATR/price only approximate liquidity and activity. Quote volume is treated
as dollar (USDT) volume because these are USDT-margined linear contracts.
"""

from __future__ import annotations

import polars as pl


def add_liquidity_proxies(
    df: pl.DataFrame,
    *,
    window: int = 24,
    price_col: str = "close",
    vol_col: str = "volume",
    quote_col: str = "quote_volume",
    ret_col: str = "log_return",
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Append dollar-volume, relative-volume, range, ATR/price, Amihud and taker-ratio columns."""
    out = df.sort(time_col)
    prev_close = pl.col(price_col).shift(1)
    true_range = pl.max_horizontal(
        pl.col("high") - pl.col("low"),
        (pl.col("high") - prev_close).abs(),
        (pl.col("low") - prev_close).abs(),
    )
    out = out.with_columns(
        pl.col(quote_col).alias("dollar_volume"),
        pl.col(quote_col).log1p().alias("log_dollar_volume"),
        (pl.col(vol_col) / pl.col(vol_col).rolling_median(window, min_samples=window)).alias(
            "rel_volume"
        ),
        ((pl.col("high") - pl.col("low")) / pl.col(price_col)).alias("hl_range"),
        true_range.alias("_tr"),
        (pl.col("taker_buy_base") / pl.col(vol_col)).alias("taker_buy_ratio"),
    )
    out = out.with_columns(
        (pl.col("_tr").rolling_mean(window, min_samples=window) / pl.col(price_col)).alias(
            "atr_over_price"
        ),
        # Amihud illiquidity: price impact per unit dollar volume (scaled to 1e6 USDT).
        (pl.col(ret_col).abs() / (pl.col("dollar_volume") / 1e6)).alias("amihud_illiq"),
    )
    return out.drop("_tr")


def zero_return_fraction(df: pl.DataFrame, ret_col: str = "log_return") -> float:
    """Fraction of bars with exactly zero return (a staleness / inactivity proxy)."""
    vals = df.select(pl.col(ret_col)).drop_nulls()
    if vals.height == 0:
        return 0.0
    return float(vals.select((pl.col(ret_col) == 0).mean()).item())


def liquidity_summary(
    df: pl.DataFrame,
    *,
    symbol: str,
    timeframe: str,
    ret_col: str = "log_return",
) -> dict[str, object]:
    """Median-based summary of the liquidity proxies for one asset/timeframe."""
    enriched = add_liquidity_proxies(df, ret_col=ret_col)
    med = enriched.select(
        pl.col("dollar_volume").median().alias("median_dollar_volume"),
        pl.col("hl_range").median().alias("median_hl_range"),
        pl.col("atr_over_price").median().alias("median_atr_over_price"),
        pl.col("amihud_illiq").median().alias("median_amihud"),
        pl.col("taker_buy_ratio").median().alias("median_taker_buy_ratio"),
    ).to_dicts()[0]
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "zero_return_pct": round(100 * zero_return_fraction(df, ret_col), 4),
        **{k: (round(float(v), 6) if v is not None else None) for k, v in med.items()},
    }
