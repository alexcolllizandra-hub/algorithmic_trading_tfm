"""Preliminary, descriptive market-regime tagging for the EDA.

This is exploratory characterisation (how often is the market trending vs.
ranging, calm vs. volatile), not the modelling-stage regime detector. Because
it is descriptive only, volatility terciles are computed on the full sample;
the modelling phase will use causal, past-only regime features instead.
"""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import polars as pl
from scipy import stats as sstats


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
        # regime name breaks occupancy ties: two regimes can share an occupancy
        # and polars does not promise a stable order, which made the exported
        # table swap rows between runs
        .sort(["occupancy", regime_col], descending=[True, False])
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


# Date-defined market regimes (Chapter 5, Figure 5.6 and Table 5.3).
#
# These windows are fixed BY DATE in code — not fitted to the data — so that
# any later chapter that conditions on "the 2022 contraction" refers to exactly
# the same bars. Boundaries follow the market narrative the thesis text uses:
# the COVID crash, the 2020-21 expansion, the 2022 contraction with its credit
# failures, the 2023 recovery and the progressively institutionalised 2024-25
# market. End dates are exclusive.
MARKET_REGIMES: tuple[tuple[str, str, str], ...] = (
    ("covid_crash", "2020-01-01", "2020-04-01"),
    ("expansion_2020_21", "2020-04-01", "2021-12-01"),
    ("contraction_2022", "2021-12-01", "2023-01-01"),
    ("recovery_2023", "2023-01-01", "2024-01-01"),
    ("institutional_2024_25", "2024-01-01", "2026-01-01"),
)


def market_regime_windows() -> pl.DataFrame:
    """The frozen date windows as a frame (name, start, end — end exclusive)."""
    return pl.DataFrame(
        {
            "regime": [r[0] for r in MARKET_REGIMES],
            "start": [datetime.fromisoformat(r[1]).replace(tzinfo=UTC) for r in MARKET_REGIMES],
            "end": [datetime.fromisoformat(r[2]).replace(tzinfo=UTC) for r in MARKET_REGIMES],
        }
    )


def market_regime_stats(
    btc: pl.DataFrame,
    eth: pl.DataFrame,
    *,
    col: str = "log_return",
    time_col: str = "open_time",
    bars_per_year: int = 8760,
) -> pl.DataFrame:
    """Conditional statistics per date-defined regime (Table 5.3).

    Annualised mean and volatility, excess kurtosis and the BTC-ETH return
    correlation, computed on exactly the bars inside each frozen window.
    """
    joined = (
        btc.select(pl.col(time_col), pl.col(col).alias("r_btc"))
        .join(eth.select(pl.col(time_col), pl.col(col).alias("r_eth")), on=time_col, how="inner")
        .drop_nulls()
    )
    rows = []
    for name, start_s, end_s in MARKET_REGIMES:
        start = datetime.fromisoformat(start_s).replace(tzinfo=UTC)
        end = datetime.fromisoformat(end_s).replace(tzinfo=UTC)
        sub = joined.filter((pl.col(time_col) >= start) & (pl.col(time_col) < end))
        if sub.height < 100:
            continue
        r_btc = sub["r_btc"].to_numpy()
        r_eth = sub["r_eth"].to_numpy()
        rows.append(
            {
                "regime": name,
                "start": start_s,
                "end": end_s,
                "n_bars": sub.height,
                "btc_ann_return": float(np.mean(r_btc) * bars_per_year),
                "btc_ann_vol": float(np.std(r_btc, ddof=1) * np.sqrt(bars_per_year)),
                "btc_exc_kurtosis": float(sstats.kurtosis(r_btc, fisher=True, bias=False)),
                "eth_ann_return": float(np.mean(r_eth) * bars_per_year),
                "eth_ann_vol": float(np.std(r_eth, ddof=1) * np.sqrt(bars_per_year)),
                "eth_exc_kurtosis": float(sstats.kurtosis(r_eth, fisher=True, bias=False)),
                "btc_eth_corr": float(np.corrcoef(r_btc, r_eth)[0, 1]),
            }
        )
    return pl.DataFrame(rows)
