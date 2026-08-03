"""Taker-buy order-flow imbalance from OHLCV klines.

Binance klines expose the taker-initiated buy volume (``taker_buy_quote``) and
the total quote volume (``quote_volume``). Their ratio is the share of quote
volume that was buyer-initiated (market buys lifting the ask). We turn it into a
symmetric imbalance in ``[-1, 1]``:

    taker_buy_ratio     = taker_buy_quote / quote_volume        (in [0, 1])
    taker_buy_imbalance = 2 * taker_buy_ratio - 1               (in [-1, 1])

This is an *activity/order-flow proxy*, not a full order-book measure: it says
nothing about resting liquidity or depth. Bars with zero quote volume have an
undefined ratio and are treated as missing (never as +/-inf).
"""

from __future__ import annotations

import numpy as np
import polars as pl


def add_order_flow_imbalance(
    df: pl.DataFrame,
    *,
    quote_col: str = "quote_volume",
    taker_buy_quote_col: str = "taker_buy_quote",
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Append ``taker_buy_ratio`` and ``taker_buy_imbalance`` columns.

    Zero (or null) ``quote_col`` denominators yield a null ratio/imbalance so no
    infinite value ever enters downstream statistics.
    """
    out = df.sort(time_col)
    ratio = (
        pl.when(pl.col(quote_col) > 0)
        .then(pl.col(taker_buy_quote_col) / pl.col(quote_col))
        .otherwise(None)
    )
    return out.with_columns(ratio.alias("taker_buy_ratio")).with_columns(
        (2.0 * pl.col("taker_buy_ratio") - 1.0).alias("taker_buy_imbalance")
    )


def order_flow_summary(
    df: pl.DataFrame,
    *,
    symbol: str,
    timeframe: str,
    ret_col: str = "log_return",
    time_col: str = "open_time",
) -> dict[str, object]:
    """Distribution, persistence and return co-movement of the imbalance.

    Reports the median and dispersion of the taker-buy imbalance, the share of
    net-buy bars, its lag-1 autocorrelation (persistence) and its Spearman rank
    correlation with the contemporaneous return. The return relationship is
    descriptive only and must not be read as evidence of predictive power.
    """
    enriched = add_order_flow_imbalance(df, time_col=time_col)
    imb = enriched.select("taker_buy_imbalance").drop_nulls().to_series().to_numpy()
    n = int(imb.size)
    if n < 3:
        return {"symbol": symbol, "timeframe": timeframe, "n": n}

    q25, q75 = np.quantile(imb, [0.25, 0.75])
    lag1 = float(np.corrcoef(imb[1:], imb[:-1])[0, 1]) if n > 2 else float("nan")

    joint = (
        enriched.select("taker_buy_imbalance", ret_col)
        .drop_nulls()
        .filter(pl.col(ret_col).is_finite())
    )
    if joint.height > 2:
        a = joint["taker_buy_imbalance"].to_numpy()
        b = joint[ret_col].to_numpy()
        # Spearman via rank-Pearson to avoid scipy warnings on constant inputs.
        if np.std(a) == 0 or np.std(b) == 0:
            spearman = float("nan")
        else:
            ra = np.argsort(np.argsort(a))
            rb = np.argsort(np.argsort(b))
            spearman = float(np.corrcoef(ra, rb)[0, 1])
    else:
        spearman = float("nan")

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "n": n,
        "median_imbalance": round(float(np.median(imb)), 4),
        "iqr_imbalance": round(float(q75 - q25), 4),
        "std_imbalance": round(float(np.std(imb, ddof=1)), 4),
        "share_net_buy": round(float(np.mean(imb > 0)), 4),
        "acf_lag1": round(lag1, 4),
        "spearman_with_return": round(spearman, 4),
    }
