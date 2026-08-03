"""Preliminary, descriptive market-regime tagging for the EDA.

This is exploratory characterisation (how often is the market trending vs.
ranging, calm vs. volatile), not the modelling-stage regime detector. Because
it is descriptive only, volatility terciles are computed on the full sample;
the modelling phase will use causal, past-only regime features instead.
"""

from __future__ import annotations

import polars as pl


def tag_trend_volatility_regimes(
    df: pl.DataFrame,
    *,
    trend_window: int = 96,
    vol_window: int = 96,
    price_col: str = "close",
    ret_col: str = "log_return",
    flat_band: float = 0.0,
) -> pl.DataFrame:
    """Append ``trend_regime``, ``vol_regime`` and combined ``regime`` columns.

    - trend: price relative to its ``trend_window`` moving average.
    - volatility: rolling std of returns bucketed into low/medium/high by the
      full-sample 33rd and 66th percentiles.
    """
    sma = pl.col(price_col).rolling_mean(window_size=trend_window, min_samples=trend_window)
    rolling_vol = pl.col(ret_col).rolling_std(window_size=vol_window, min_samples=vol_window)

    out = df.sort("open_time").with_columns(
        sma.alias("_sma"),
        rolling_vol.alias("_vol"),
    )

    rel = (pl.col(price_col) - pl.col("_sma")) / pl.col("_sma")
    out = out.with_columns(
        pl.when(rel > flat_band)
        .then(pl.lit("up"))
        .when(rel < -flat_band)
        .then(pl.lit("down"))
        .otherwise(pl.lit("flat"))
        .alias("trend_regime")
    )

    q33 = out.select(pl.col("_vol").quantile(0.33)).item()
    q66 = out.select(pl.col("_vol").quantile(0.66)).item()
    out = out.with_columns(
        pl.when(pl.col("_vol").is_null())
        .then(pl.lit("unknown"))
        .when(pl.col("_vol") <= q33)
        .then(pl.lit("low"))
        .when(pl.col("_vol") <= q66)
        .then(pl.lit("medium"))
        .otherwise(pl.lit("high"))
        .alias("vol_regime")
    )

    return out.with_columns(
        pl.concat_str([pl.col("trend_regime"), pl.col("vol_regime")], separator="_").alias("regime")
    ).drop("_sma", "_vol")


def tag_activity_regime(
    df: pl.DataFrame,
    *,
    value_col: str = "volume",
    window: int = 96,
    out_col: str = "activity_regime",
) -> pl.DataFrame:
    """Append a low/normal/high activity regime from a rolling-mean of ``value_col``.

    The rolling mean is bucketed by its own 33rd/66th sample percentiles. Like
    the volatility dimension this is descriptive characterisation for the EDA.
    """
    activity = pl.col(value_col).rolling_mean(window_size=window, min_samples=window)
    out = df.sort("open_time").with_columns(activity.alias("_act"))
    q33 = out.select(pl.col("_act").quantile(0.33)).item()
    q66 = out.select(pl.col("_act").quantile(0.66)).item()
    return out.with_columns(
        pl.when(pl.col("_act").is_null())
        .then(pl.lit("unknown"))
        .when(pl.col("_act") <= q33)
        .then(pl.lit("low"))
        .when(pl.col("_act") <= q66)
        .then(pl.lit("normal"))
        .otherwise(pl.lit("high"))
        .alias(out_col)
    ).drop("_act")


def regime_frequencies(df: pl.DataFrame, regime_col: str = "regime") -> pl.DataFrame:
    """Count and share of bars per regime label, most frequent first."""
    total = df.height
    return (
        df.group_by(regime_col)
        .agg(pl.len().alias("count"))
        .with_columns((pl.col("count") / total).alias("share"))
        .sort("count", descending=True)
    )


def regime_runs(df: pl.DataFrame, regime_col: str = "regime") -> pl.DataFrame:
    """Return one row per contiguous regime run with its length in bars."""
    ordered = df.sort("open_time")
    return (
        ordered.with_columns(
            (pl.col(regime_col) != pl.col(regime_col).shift(1))
            .fill_null(True)
            .cum_sum()
            .alias("_rid")
        )
        .group_by("_rid")
        .agg(pl.col(regime_col).first().alias(regime_col), pl.len().alias("run_length"))
        .sort("_rid")
        .drop("_rid")
    )


def regime_duration_summary(df: pl.DataFrame, regime_col: str = "regime") -> pl.DataFrame:
    """Mean/median/max run length (bars) and number of runs per regime."""
    runs = regime_runs(df, regime_col)
    return (
        runs.group_by(regime_col)
        .agg(
            pl.len().alias("n_runs"),
            pl.col("run_length").mean().alias("mean_bars"),
            pl.col("run_length").median().alias("median_bars"),
            pl.col("run_length").max().alias("max_bars"),
        )
        .sort("n_runs", descending=True)
    )


def regime_transition_matrix(
    df: pl.DataFrame, regime_col: str = "regime", *, normalize: bool = True
) -> pl.DataFrame:
    """First-order transition counts (or row-normalised probabilities).

    Self-transitions between identical consecutive bars are excluded so the
    matrix describes moves *between* regimes; the diagonal therefore reflects
    only genuine re-entries after a change.
    """
    ordered = df.sort("open_time").with_columns(pl.col(regime_col).shift(-1).alias("_to"))
    trans = (
        ordered.drop_nulls("_to")
        .filter(pl.col(regime_col) != pl.col("_to"))
        .group_by([regime_col, "_to"])
        .agg(pl.len().alias("count"))
        .rename({regime_col: "from", "_to": "to"})
        .sort(["from", "to"])
    )
    if normalize and trans.height:
        trans = trans.with_columns(
            (pl.col("count") / pl.col("count").sum().over("from")).alias("probability")
        )
    return trans


def regime_transition_matrix_full(
    df: pl.DataFrame, regime_col: str = "regime", *, normalize: bool = True
) -> pl.DataFrame:
    """First-order transition counts INCLUDING self-transitions (bar-to-bar).

    Unlike :func:`regime_transition_matrix`, the diagonal here counts staying in
    the same regime between consecutive bars, so rows describe the full one-step
    dynamics (persistence on the diagonal, switches off-diagonal).
    """
    ordered = df.sort("open_time").with_columns(pl.col(regime_col).shift(-1).alias("_to"))
    trans = (
        ordered.drop_nulls("_to")
        .group_by([regime_col, "_to"])
        .agg(pl.len().alias("count"))
        .rename({regime_col: "from", "_to": "to"})
        .sort(["from", "to"])
    )
    if normalize and trans.height:
        trans = trans.with_columns(
            (pl.col("count") / pl.col("count").sum().over("from")).alias("probability")
        )
    return trans


def regime_duration_table(df: pl.DataFrame, regime_col: str = "regime") -> pl.DataFrame:
    """Episode count, occupancy share and duration quantiles per regime (bars)."""
    runs = regime_runs(df, regime_col)
    total_bars = df.height
    return (
        runs.group_by(regime_col)
        .agg(
            pl.len().alias("n_episodes"),
            pl.col("run_length").sum().alias("_bars"),
            pl.col("run_length").mean().alias("mean_bars"),
            pl.col("run_length").median().alias("median_bars"),
            pl.col("run_length").quantile(0.90).alias("p90_bars"),
            pl.col("run_length").max().alias("max_bars"),
        )
        .with_columns(
            (pl.col("_bars") / total_bars).alias("occupancy")
            if total_bars
            else pl.lit(0.0).alias("occupancy")
        )
        .drop("_bars")
        .sort("occupancy", descending=True)
    )


def regime_intervals(
    df: pl.DataFrame, regime_col: str = "regime", *, time_col: str = "open_time"
) -> pl.DataFrame:
    """Contiguous regime episodes with start/end timestamps and length.

    Consolidates bar-level labels into contiguous intervals so a price chart can
    be shaded with a handful of solid blocks per regime instead of thousands of
    single-bar stripes. Returns ``regime``, ``start``, ``end`` (timestamps of the
    first and last bar of the run) and ``run_length`` (in bars), in time order.
    """
    ordered = df.sort(time_col)
    return (
        ordered.with_columns(
            (pl.col(regime_col) != pl.col(regime_col).shift(1))
            .fill_null(True)
            .cum_sum()
            .alias("_rid")
        )
        .group_by("_rid")
        .agg(
            pl.col(regime_col).first().alias(regime_col),
            pl.col(time_col).first().alias("start"),
            pl.col(time_col).last().alias("end"),
            pl.len().alias("run_length"),
        )
        .sort("_rid")
        .drop("_rid")
    )


def regime_context(
    df: pl.DataFrame,
    value_cols: list[str],
    regime_col: str = "regime",
) -> pl.DataFrame:
    """Mean of each ``value_cols`` entry per regime (e.g. return, vol, volume)."""
    aggs = [pl.col(c).mean().alias(f"mean_{c}") for c in value_cols]
    return (
        df.group_by(regime_col).agg(pl.len().alias("count"), *aggs).sort("count", descending=True)
    )
