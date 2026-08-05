"""Cross-asset and derivatives feature builders (causal, context-aware).

These features need information beyond a single symbol's own OHLCV bars:

* **Cross-asset** features relate the primary symbol to a peer (e.g. BTC vs ETH)
  sampled on the *same* timeframe grid. Both bars close at the same instant, so a
  peer value at bar *t* is available at the close of *t* (usable for a decision
  at *t+1*, exactly like the symbol's own close). Alignment is an **exact** inner
  join on ``open_time`` -- never a forward/nearest join that could import a
  future peer bar.
* **Derivatives** features (funding rate, mark-index basis, open-interest change)
  arrive on their own irregular clock. They are attached with a **backward**
  as-of join (``strategy="backward"``): each bar receives the most recent value
  whose timestamp is ``<= open_time``. This is the ``funding.align == as_of_past``
  rule from the experiment contract and can never look ahead.

If a required input frame is missing, the caller is expected to report the
feature as *unavailable* rather than fabricate values (see
:mod:`perp_lab.features.registry`); these builders raise ``ValueError`` on
missing columns instead of silently substituting zeros.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

TIME_COL = "open_time"


@dataclass(frozen=True)
class FeatureContext:
    """Auxiliary inputs required by cross-asset / derivatives feature kinds.

    Every field is optional. A context feature whose input is ``None`` is treated
    as *unavailable* by the engine (it raises rather than fabricating values),
    honouring the contract rule "report the feature as unavailable instead of
    fabricating". Frames are expected on the primary timeframe grid (peer, mark,
    index) or on their native clock (funding, open_interest) with a timestamp
    column named ``open_time`` (or ``funding_time`` for funding).
    """

    peer: pl.DataFrame | None = None
    peer_symbol: str | None = None
    funding: pl.DataFrame | None = None
    mark: pl.DataFrame | None = None
    index: pl.DataFrame | None = None
    open_interest: pl.DataFrame | None = None

    def has(self, context_kind: str) -> bool:
        """Whether the auxiliary input for ``context_kind`` is present."""
        if context_kind == "peer":
            return self.peer is not None
        if context_kind == "funding":
            return self.funding is not None
        if context_kind == "mark_index":
            return self.mark is not None and self.index is not None
        if context_kind == "open_interest":
            return self.open_interest is not None
        return False


def _require(df: pl.DataFrame, columns: tuple[str, ...], *, what: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{what} is missing required columns {missing}.")


def _log_return(price_col: str) -> pl.Expr:
    logp = pl.col(price_col).log()
    return logp - logp.shift(1)


def add_relative_return(
    df: pl.DataFrame,
    peer: pl.DataFrame,
    *,
    price_col: str = "close",
    peer_price_col: str = "close",
    out_col: str = "xasset_rel_return",
    time_col: str = TIME_COL,
) -> pl.DataFrame:
    """Append the 1-bar log-return difference ``r_self - r_peer`` (causal).

    The peer is aligned by an **exact** inner join on ``time_col`` so no future
    peer bar can leak in. Warm-up is one row (the first return is null).
    """
    _require(df, (time_col, price_col), what="primary frame")
    _require(peer, (time_col, peer_price_col), what="peer frame")
    peer_ret = peer.sort(time_col).select(time_col, _log_return(peer_price_col).alias("__peer_ret"))
    out = df.sort(time_col).join(peer_ret, on=time_col, how="left")
    return out.with_columns((_log_return(price_col) - pl.col("__peer_ret")).alias(out_col)).drop(
        "__peer_ret"
    )


def add_relative_momentum(
    df: pl.DataFrame,
    peer: pl.DataFrame,
    window: int,
    *,
    price_col: str = "close",
    peer_price_col: str = "close",
    out_col: str | None = None,
    time_col: str = TIME_COL,
) -> pl.DataFrame:
    """Append relative momentum ``mom_self(w) - mom_peer(w)`` (causal).

    Momentum is ``ln(P_t / P_{t-w})`` for each asset. Warm-up is ``w`` rows.
    """
    if window < 1:
        raise ValueError("relative-momentum window must be >= 1.")
    name = out_col or f"xasset_rel_momentum_{window}"
    _require(df, (time_col, price_col), what="primary frame")
    _require(peer, (time_col, peer_price_col), what="peer frame")

    def _mom(col: str) -> pl.Expr:
        logp = pl.col(col).log()
        return logp - logp.shift(window)

    peer_mom = peer.sort(time_col).select(time_col, _mom(peer_price_col).alias("__peer_mom"))
    out = df.sort(time_col).join(peer_mom, on=time_col, how="left")
    return out.with_columns((_mom(price_col) - pl.col("__peer_mom")).alias(name)).drop("__peer_mom")


def add_rolling_xcorr(
    df: pl.DataFrame,
    peer: pl.DataFrame,
    window: int,
    *,
    price_col: str = "close",
    peer_price_col: str = "close",
    out_col: str | None = None,
    time_col: str = TIME_COL,
) -> pl.DataFrame:
    """Append the trailing Pearson correlation of 1-bar log returns (causal).

    Correlation over the last ``window`` returns of the primary symbol and the
    peer. A degenerate window (zero variance in either series) maps to null, not
    an infinity. Warm-up is ``window`` rows (the first return is null, then
    ``window`` non-null pairs are needed).
    """
    if window < 2:
        raise ValueError("rolling correlation window must be >= 2.")
    name = out_col or f"xasset_corr_{window}"
    _require(df, (time_col, price_col), what="primary frame")
    _require(peer, (time_col, peer_price_col), what="peer frame")

    peer_ret = peer.sort(time_col).select(time_col, _log_return(peer_price_col).alias("__peer_ret"))
    out = df.sort(time_col).join(peer_ret, on=time_col, how="left")
    out = out.with_columns(_log_return(price_col).alias("__self_ret"))
    corr = pl.rolling_corr(
        pl.col("__self_ret"), pl.col("__peer_ret"), window_size=window, min_samples=window
    )
    # Guard against numerical overshoot outside [-1, 1] and non-finite results.
    corr = pl.when(corr.is_finite()).then(corr.clip(-1.0, 1.0)).otherwise(None)
    return out.with_columns(corr.alias(name)).drop("__peer_ret", "__self_ret")


def attach_funding_rate(
    df: pl.DataFrame,
    funding: pl.DataFrame,
    *,
    funding_time_col: str = "funding_time",
    funding_rate_col: str = "funding_rate",
    out_col: str = "funding_rate",
    time_col: str = TIME_COL,
) -> pl.DataFrame:
    """Attach the most recent funding rate known at each bar's open (as-of past).

    Backward as-of join: bar *t* receives the funding rate whose timestamp is the
    latest ``<= open_time_t``. Bars before the first funding observation get
    null (never a fabricated zero). This mirrors ``costs.funding.align`` =
    ``as_of_past``.
    """
    _require(df, (time_col,), what="primary frame")
    _require(funding, (funding_time_col, funding_rate_col), what="funding frame")
    right = funding.sort(funding_time_col).select(
        pl.col(funding_time_col).alias("__ft"),
        pl.col(funding_rate_col).alias(out_col),
    )
    out = df.sort(time_col).join_asof(right, left_on=time_col, right_on="__ft", strategy="backward")
    return out.drop("__ft")


def add_basis(
    df: pl.DataFrame,
    mark: pl.DataFrame,
    index: pl.DataFrame,
    *,
    mark_price_col: str = "close",
    index_price_col: str = "close",
    out_col: str = "basis",
    time_col: str = TIME_COL,
) -> pl.DataFrame:
    """Append the scale-free mark-index basis ``(mark - index) / index`` (causal).

    Mark and index prices are aligned to the bar grid by exact join (same
    timeframe). A non-positive index maps to null. Warm-up is zero.
    """
    _require(df, (time_col,), what="primary frame")
    _require(mark, (time_col, mark_price_col), what="mark-price frame")
    _require(index, (time_col, index_price_col), what="index-price frame")
    m = mark.sort(time_col).select(time_col, pl.col(mark_price_col).alias("__mark"))
    i = index.sort(time_col).select(time_col, pl.col(index_price_col).alias("__index"))
    out = df.sort(time_col).join(m, on=time_col, how="left").join(i, on=time_col, how="left")
    expr = (
        pl.when(pl.col("__index") > 0)
        .then((pl.col("__mark") - pl.col("__index")) / pl.col("__index"))
        .otherwise(None)
    )
    return out.with_columns(expr.alias(out_col)).drop("__mark", "__index")


def add_open_interest_change(
    df: pl.DataFrame,
    open_interest: pl.DataFrame,
    window: int,
    *,
    oi_time_col: str = "open_time",
    oi_col: str = "open_interest",
    out_col: str | None = None,
    time_col: str = TIME_COL,
) -> pl.DataFrame:
    """Append the log change in open interest over ``window`` bars (causal).

    Open interest is attached by a backward as-of join, then differenced against
    its own ``window``-lagged value. A non-positive OI maps to null. Warm-up is
    ``window`` rows.
    """
    if window < 1:
        raise ValueError("open-interest change window must be >= 1.")
    name = out_col or f"oi_change_{window}"
    _require(df, (time_col,), what="primary frame")
    _require(open_interest, (oi_time_col, oi_col), what="open-interest frame")
    right = open_interest.sort(oi_time_col).select(
        pl.col(oi_time_col).alias("__oit"), pl.col(oi_col).alias("__oi")
    )
    out = df.sort(time_col).join_asof(
        right, left_on=time_col, right_on="__oit", strategy="backward"
    )
    log_oi = pl.when(pl.col("__oi") > 0).then(pl.col("__oi").log()).otherwise(None)
    return out.with_columns((log_oi - log_oi.shift(window)).alias(name)).drop("__oit", "__oi")
