"""Chapter 5 (EDA and stylized facts) figures, tables and values for the thesis.

Run with: ``uv run python scripts/build_ch5_figures.py``

Writes PNG + PDF pairs for Figures 5.1-5.16 to ``reports/figures/thesis_ch5/``,
plus ``values_ch5.json`` holding every number the chapter text needs and the
markdown bodies of Tables 5.1-5.3. Deterministic: seed 42 everywhere, no
timestamps in any output.

Data access goes exclusively through :class:`perp_lab.eda.DataLake` with the
``development`` partition, which raises on any holdout leakage. The final
partition is never read, not even for coverage.

Expensive intermediates (triple-barrier labels, mutual information) are cached
to parquet/JSON under ``reports/cache/eda_ch5/`` keyed by a hash of their
configuration; delete the directory to force recomputation.
"""

# ruff: noqa: RUF001  # typographic characters are intentional in figure text

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from scipy import stats as sstats

from perp_lab.config import load_data_contract, load_experiment_config
from perp_lab.eda import DataLake
from perp_lab.eda.cointegration import engle_granger_by_regime
from perp_lab.eda.dependence import (
    autocorrelation,
    hurst_rs,
    leverage_effect,
    rolling_hurst,
    variance_ratio_profile,
)
from perp_lab.eda.distributions import (
    fit_student_t,
    hill_tail_index,
    kurtosis_by_aggregation,
    survival_function,
)
from perp_lab.eda.features import (
    feature_correlation_matrix,
    high_correlation_pairs,
    label_summary,
    mutual_information_by_horizon,
    pca_scree,
)
from perp_lab.eda.funding import attach_funding
from perp_lab.eda.regimes import MARKET_REGIMES, market_regime_stats
from perp_lab.eda.returns import add_log_returns, return_stats
from perp_lab.eda.stationarity import adf_test, arch_lm_test, kpss_test, ljung_box
from perp_lab.features import build_feature_frame, feature_columns, resolve_feature_set
from perp_lab.labeling.triple_barrier import LabelCosts, TripleBarrierSpec, triple_barrier_labels

SEED = 42
OUT = Path("reports/figures/thesis_ch5")
CACHE = Path("reports/cache/eda_ch5")
BARS_PER_YEAR = 8760

plt.rcParams.update(
    {
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
    }
)

ACCENT = "#0f766e"
SECOND = "#1d4ed8"
BAD = "#b91c1c"
AMBER = "#b45309"
GREY = "#6b7280"
SYM_COLOR = {"BTCUSDT": ACCENT, "ETHUSDT": SECOND}

VALUES: dict[str, object] = {}


EDA_MIRROR = Path("reports/figures/eda")


def save(fig: plt.Figure, name: str) -> str:
    # Canonical thesis location plus a mirror in the notebook's EDA gallery,
    # so every chapter-5 figure is reachable from reports/figures/eda too.
    for out_dir in (OUT, EDA_MIRROR):
        out_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_dir / f"{name}.png", bbox_inches="tight")
        fig.savefig(out_dir / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    return f"{OUT / name}.png|.pdf"


def _cfg_hash(params: dict) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]


def cached_frame(name: str, params: dict, compute) -> pl.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{name}_{_cfg_hash(params)}.parquet"
    if path.exists():
        return pl.read_parquet(path)
    frame = compute()
    frame.write_parquet(path)
    return frame


# Data loading (development partition only, gated)
CONTRACT = load_data_contract()
EXP = load_experiment_config()
LAKE = DataLake(CONTRACT)
SYMBOLS = ("BTCUSDT", "ETHUSDT")

BARS: dict[tuple[str, str], pl.DataFrame] = {}
for sym in SYMBOLS:
    for tf in ("5m", "15m", "1h"):
        loaded = LAKE.load_klines(sym, tf, partition="development")
        BARS[(sym, tf)] = add_log_returns(loaded.frame)

FUNDING = {sym: LAKE.load_funding(sym, partition="development").frame for sym in SYMBOLS}


def rets(sym: str, tf: str = "1h") -> np.ndarray:
    arr = BARS[(sym, tf)]["log_return"].to_numpy()
    return arr[np.isfinite(arr)]


# Fig 5.1 — coverage per month + QC incidents (zero-volume bars)
def fig_5_1() -> str:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.2, 4.4), sharex=True)
    zero_months: dict[str, pl.DataFrame] = {}
    for sym in SYMBOLS:
        monthly = (
            BARS[(sym, "5m")]
            .with_columns(pl.col("open_time").dt.truncate("1mo").alias("month"))
            .group_by("month")
            .agg(
                pl.len().alias("bars"),
                (pl.col("volume") == 0).sum().alias("zero_vol"),
            )
            .sort("month")
            .with_columns(
                (pl.col("bars") / (pl.col("month").dt.month_end().dt.day() * 288) * 100).alias(
                    "coverage_pct"
                )
            )
        )
        zero_months[sym] = monthly
        ax1.plot(
            monthly["month"].to_list(),
            monthly["coverage_pct"].to_list(),
            color=SYM_COLOR[sym],
            lw=1.3,
            label=f"{sym[:3]} coverage",
        )
        ax2.bar(
            monthly["month"].to_list(),
            monthly["zero_vol"].to_list(),
            width=26 if sym == "BTCUSDT" else 18,
            color=SYM_COLOR[sym],
            alpha=0.85 if sym == "BTCUSDT" else 0.7,
            label=f"{sym[:3]} zero-volume bars",
        )
    ax1.set_ylim(99.0, 100.5)
    ax1.axhline(100, color=GREY, lw=0.6, ls=":")
    ax1.set_ylabel("coverage %")
    ax1.set_title("5-minute bar coverage per month (expected = calendar bars)", fontsize=9)
    ax1.legend(fontsize=8, loc="lower right")
    ax2.set_ylabel("bars / month")
    ax2.set_title("QC incidents: zero-volume 5m bars — flagged, kept, never repaired", fontsize=9)
    ax2.legend(fontsize=8)
    for ax in (ax1, ax2):
        ax.tick_params(labelsize=8)

    concentrated = (
        zero_months["BTCUSDT"]
        .filter(pl.col("zero_vol") > 0)
        .select(pl.col("month").dt.strftime("%Y-%m"), "zero_vol")
    )
    VALUES["zero_vol_months_btc"] = dict(concentrated.iter_rows())
    concentrated_eth = (
        zero_months["ETHUSDT"]
        .filter(pl.col("zero_vol") > 0)
        .select(pl.col("month").dt.strftime("%Y-%m"), "zero_vol")
    )
    VALUES["zero_vol_months_eth"] = dict(concentrated_eth.iter_rows())
    fig.tight_layout()
    return save(fig, "fig_5_1_coverage")


# Fig 5.2 — return distribution vs fitted normal, log scale (1h)
def fig_5_2() -> str:
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.3), sharey=True)
    for ax, sym in zip(axes, SYMBOLS, strict=True):
        r = rets(sym) * 100
        mu, sd = r.mean(), r.std(ddof=1)
        bins = np.linspace(-8 * sd, 8 * sd, 121)
        ax.hist(r, bins=bins, density=True, color=SYM_COLOR[sym], alpha=0.65, label="empirical")
        grid = np.linspace(bins[0], bins[-1], 400)
        ax.plot(grid, sstats.norm.pdf(grid, mu, sd), color=BAD, lw=1.2, label="fitted normal")
        ax.set_yscale("log")
        ax.set_ylim(1e-6, 3)
        ax.set_title(f"{sym[:3]} · 1h log-returns (%)", fontsize=9)
        ax.set_xlabel("return (%)")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("density (log scale)")
    fig.tight_layout()
    return save(fig, "fig_5_2_distribution_vs_normal")


# Fig 5.3 — QQ plots vs normal and Student-t, per timeframe (BTC)
def fig_5_3() -> str:
    fig, axes = plt.subplots(1, 3, figsize=(8.6, 3.1))
    tfits = {}
    for ax, tf in zip(axes, ("5m", "15m", "1h"), strict=True):
        r = rets("BTCUSDT", tf)
        fit = fit_student_t(r)
        tfits[tf] = fit
        probs = (np.arange(1, 2001) - 0.5) / 2000
        emp = np.quantile(r, probs)
        qn = sstats.norm.ppf(probs, r.mean(), r.std(ddof=1))
        qt = sstats.t.ppf(probs, fit["df"], fit["loc"], fit["scale"])
        ax.plot(qn, emp, ".", ms=1.5, color=GREY, label="vs normal")
        ax.plot(qt, emp, ".", ms=1.5, color=ACCENT, label=f"vs t (df={fit['df']:.1f})")
        lim = np.abs(emp).max() * 1.05
        ax.plot([-lim, lim], [-lim, lim], color=BAD, lw=0.8, ls="--")
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_title(f"BTC {tf}", fontsize=9)
        ax.set_xlabel("theoretical quantile")
        ax.tick_params(labelsize=7)
        ax.legend(fontsize=7, loc="upper left")
    axes[0].set_ylabel("empirical quantile")
    VALUES["t_fit_df"] = {tf: round(fit["df"], 2) for tf, fit in tfits.items()}
    VALUES["t_fit_df_eth_1h"] = round(fit_student_t(rets("ETHUSDT"))["df"], 2)
    fig.tight_layout()
    return save(fig, "fig_5_3_qq_plots")


# Fig 5.4 — excess kurtosis vs aggregation horizon
def fig_5_4() -> str:
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    from matplotlib.ticker import NullFormatter

    for sym in SYMBOLS:
        # Real bar series for the contract timeframes (matches Table 5.1)...
        points = {
            5: float(sstats.kurtosis(rets(sym, "5m"), fisher=True, bias=False)),
            15: float(sstats.kurtosis(rets(sym, "15m"), fisher=True, bias=False)),
            60: float(sstats.kurtosis(rets(sym, "1h"), fisher=True, bias=False)),
        }
        # ...plus one aggregated 30m point to fill the curve.
        agg = kurtosis_by_aggregation(rets(sym, "5m"), [6])
        points[30] = float(agg["excess_kurtosis"][0])
        xs = sorted(points)
        ax.plot(
            xs,
            [points[x] for x in xs],
            "o-",
            color=SYM_COLOR[sym],
            lw=1.2,
            ms=4,
            label=sym[:3],
        )
        VALUES[f"kurtosis_by_horizon_{sym[:3].lower()}"] = {x: round(points[x], 1) for x in xs}
    ax.axhline(0, color=BAD, lw=0.8, ls="--")
    ax.text(58, 12, "Gaussian = 0", color=BAD, fontsize=8, ha="right")
    ax.set_xscale("log")
    ax.set_xticks([5, 15, 30, 60])
    ax.set_xticklabels(["5m", "15m", "30m", "1h"])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("aggregation horizon")
    ax.set_ylabel("excess kurtosis")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return save(fig, "fig_5_4_kurtosis_aggregation")


def fig_5_5() -> str:
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.2), sharey=True)
    max_lag = 100
    for ax, sym in zip(axes, SYMBOLS, strict=True):
        frame = BARS[(sym, "1h")]
        n = frame.height
        band = 1.96 / np.sqrt(n)
        for transform, color, label in (
            ("identity", GREY, "returns"),
            ("abs", SYM_COLOR[sym], "|returns|"),
            ("square", AMBER, "squared returns"),
        ):
            acf = autocorrelation(frame, max_lag=max_lag, transform=transform).filter(
                pl.col("lag") > 0
            )
            ax.plot(acf["lag"].to_list(), acf["acf"].to_list(), lw=1.1, color=color, label=label)
        ax.axhspan(-band, band, color=GREY, alpha=0.15, lw=0)
        ax.axhline(0, color=GREY, lw=0.6)
        ax.set_title(f"{sym[:3]} · 1h", fontsize=9)
        ax.set_xlabel("lag (hours)")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("autocorrelation")
    fig.tight_layout()
    return save(fig, "fig_5_5_acf")


# Fig 5.6 — rolling realized volatility with regime shading
REGIME_LABELS = {
    "covid_crash": "COVID\ncrash",
    "expansion_2020_21": "2020–21 expansion",
    "contraction_2022": "2022 contraction",
    "recovery_2023": "2023 recovery",
    "institutional_2024_25": "2024–25 institutional",
}
REGIME_TINTS = {
    "covid_crash": "#fee2e2",
    "expansion_2020_21": "#dcfce7",
    "contraction_2022": "#fef3c7",
    "recovery_2023": "#e0e7ff",
    "institutional_2024_25": "#f3f4f6",
}


def fig_5_6() -> str:
    fig, ax = plt.subplots(figsize=(8.4, 3.4))
    window = 30 * 24
    vols = {}
    for sym in SYMBOLS:
        frame = (
            BARS[(sym, "1h")]
            .with_columns(
                (
                    pl.col("log_return").rolling_std(window_size=window, min_samples=window)
                    * np.sqrt(BARS_PER_YEAR)
                ).alias("roll_vol")
            )
            .drop_nulls("roll_vol")
        )
        vols[sym] = frame
        ax.plot(
            frame["open_time"].to_list(),
            frame["roll_vol"].to_list(),
            color=SYM_COLOR[sym],
            lw=1.0,
            label=sym[:3],
        )
    import datetime as _dt

    peak = max(v["roll_vol"].max() for v in vols.values())
    for name, start_s, end_s in MARKET_REGIMES:
        start = _dt.datetime.fromisoformat(start_s)
        end = _dt.datetime.fromisoformat(end_s)
        ax.axvspan(start, end, color=REGIME_TINTS[name], zorder=0)
        ax.text(
            start + (end - start) / 2,
            peak * 1.09,
            REGIME_LABELS[name],
            ha="center",
            fontsize=7,
            color=GREY,
        )
    ax.set_ylim(0, peak * 1.16)
    ax.set_ylabel("annualised 30-day realized volatility")
    ax.legend(fontsize=8, loc="upper right")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(labelsize=8)

    btc_vol = vols["BTCUSDT"]["roll_vol"]
    VALUES["rolling_vol_min_max_btc"] = [round(btc_vol.min(), 3), round(btc_vol.max(), 3)]
    VALUES["rolling_vol_factor_btc"] = round(btc_vol.max() / btc_vol.min(), 1)
    fig.tight_layout()
    return save(fig, "fig_5_6_rolling_vol_regimes")


# Fig 5.7 — intraday profile: |return| and volume per UTC hour
def fig_5_7() -> str:
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.2))
    profiles = {}
    for sym in SYMBOLS:
        prof = (
            BARS[(sym, "1h")]
            .with_columns(pl.col("open_time").dt.hour().alias("hour"))
            .group_by("hour")
            .agg(
                (pl.col("log_return").abs().mean() * 1e4).alias("absret_bps"),
                pl.col("volume").mean().alias("volume"),
            )
            .sort("hour")
        )
        profiles[sym] = prof
        axes[0].plot(
            prof["hour"].to_list(),
            prof["absret_bps"].to_list(),
            "o-",
            ms=3,
            lw=1.1,
            color=SYM_COLOR[sym],
            label=sym[:3],
        )
        axes[1].plot(
            prof["hour"].to_list(),
            (prof["volume"] / prof["volume"].mean()).to_list(),
            "o-",
            ms=3,
            lw=1.1,
            color=SYM_COLOR[sym],
            label=sym[:3],
        )
    axes[0].set_ylabel("mean |1h return| (bps)")
    axes[1].set_ylabel("volume relative to daily mean")
    for ax in axes:
        ax.set_xlabel("UTC hour")
        ax.set_xticks(range(0, 24, 4))
        ax.legend(fontsize=8)
    btc = profiles["BTCUSDT"]
    peak = btc.sort("absret_bps", descending=True).head(3)["hour"].to_list()
    quiet = btc.sort("absret_bps").head(3)["hour"].to_list()
    VALUES["intraday_peak_hours_btc"] = sorted(peak)
    VALUES["intraday_quiet_hours_btc"] = sorted(quiet)
    fig.tight_layout()
    return save(fig, "fig_5_7_intraday_profile")


# Fig 5.8 — volatility heatmap, UTC hour x weekday
def fig_5_8() -> str:
    frame = (
        BARS[("BTCUSDT", "1h")]
        .with_columns(
            pl.col("open_time").dt.hour().alias("hour"),
            pl.col("open_time").dt.weekday().alias("weekday"),
        )
        .group_by("hour", "weekday")
        .agg((pl.col("log_return").abs().mean() * 1e4).alias("absret_bps"))
    )
    grid = np.full((7, 24), np.nan)
    for hour, weekday, val in frame.iter_rows():
        grid[weekday - 1, hour] = val

    fig, ax = plt.subplots(figsize=(8.0, 2.9))
    im = ax.imshow(grid, aspect="auto", cmap="YlGnBu")
    ax.set_yticks(range(7))
    ax.set_yticklabels(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], fontsize=8)
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels(range(0, 24, 2), fontsize=8)
    ax.set_xlabel("UTC hour")
    ax.set_title("BTC mean |1h return| (bps) by hour and weekday", fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.85, label="bps")

    weekend = np.nanmean(grid[5:, :])
    weekday_mean = np.nanmean(grid[:5, :])
    VALUES["weekend_vol_vs_weekday_pct"] = round((weekend / weekday_mean - 1) * 100, 1)
    volumes = (
        BARS[("BTCUSDT", "1h")]
        .with_columns((pl.col("open_time").dt.weekday() >= 6).alias("weekend"))
        .group_by("weekend")
        .agg(pl.col("volume").mean())
    )
    vol_map = dict(volumes.iter_rows())
    VALUES["weekend_volume_vs_weekday_pct"] = round((vol_map[True] / vol_map[False] - 1) * 100, 1)
    fig.tight_layout()
    return save(fig, "fig_5_8_heatmap_hour_weekday")


# Fig 5.9 — funding distribution and autocorrelation (BTC)
def fig_5_9() -> str:
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.1))
    fr = FUNDING["BTCUSDT"]["funding_rate"].to_numpy() * 1e4
    axes[0].hist(fr, bins=120, color=ACCENT, alpha=0.8)
    axes[0].axvline(1.0, color=BAD, lw=1.0, ls="--")
    axes[0].text(1.15, axes[0].get_ylim()[1] * 0.75, "baseline\n1 bp", color=BAD, fontsize=7.5)
    axes[0].set_yscale("log")
    axes[0].set_xlabel("funding rate per 8h settlement (bps)")
    axes[0].set_ylabel("count (log)")
    axes[0].set_title("BTC funding distribution", fontsize=9)

    frame = pl.DataFrame({"log_return": fr})
    acf = autocorrelation(frame, max_lag=60).filter(pl.col("lag") > 0)
    band = 1.96 / np.sqrt(fr.size)
    axes[1].bar(acf["lag"].to_list(), acf["acf"].to_list(), color=ACCENT, width=0.8)
    axes[1].axhspan(-band, band, color=GREY, alpha=0.2, lw=0)
    axes[1].set_xlabel("lag (8h settlements)")
    axes[1].set_ylabel("autocorrelation")
    axes[1].set_title("BTC funding ACF", fontsize=9)

    acf_vals = acf["acf"].to_numpy()
    above = np.where(acf_vals < band)[0]
    VALUES["funding_acf_lags_above_band"] = int(above[0]) if above.size else 60
    VALUES["funding_acf_lag1"] = round(float(acf_vals[0]), 3)
    fig.tight_layout()
    return save(fig, "fig_5_9_funding")


# Fig 5.10 — mean forward return conditional on funding quantile
def fig_5_10() -> str:
    horizon = 8  # hours after each settlement
    n_boot, block = 500, 24
    rng = np.random.default_rng(SEED)
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.3), sharey=True)
    results = {}
    for ax, sym in zip(axes, SYMBOLS, strict=True):
        bars = BARS[(sym, "1h")]
        with_funding = attach_funding(bars, FUNDING[sym])
        ret = with_funding["log_return"].to_numpy()
        csum = np.concatenate([[0.0], np.cumsum(np.nan_to_num(ret))])
        fwd = csum[1 + horizon :] - csum[1:-horizon]
        rate = with_funding["funding_rate"].to_numpy()[: fwd.size]
        valid = np.isfinite(rate) & np.isfinite(fwd)
        rate, fwd_v = rate[valid], fwd[valid]
        # Rank-based deciles: quantile edges collapse at the 1 bp baseline mass.
        order = np.argsort(rate, kind="stable")
        which = np.empty(rate.size, dtype=int)
        which[order] = np.arange(rate.size) * 10 // rate.size
        means, lo, hi = [], [], []
        for d in range(10):
            sample = fwd_v[which == d]
            means.append(sample.mean() * 1e4)
            # Moving-block bootstrap to respect serial dependence.
            n = sample.size
            n_blocks = max(1, n // block)
            boots = np.empty(n_boot)
            starts_max = max(1, n - block)
            for b in range(n_boot):
                starts = rng.integers(0, starts_max, n_blocks)
                idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n]
                boots[b] = sample[idx].mean() * 1e4
            lo.append(np.quantile(boots, 0.025))
            hi.append(np.quantile(boots, 0.975))
        results[sym] = (means, lo, hi)
        x = np.arange(1, 11)
        ax.errorbar(
            x,
            means,
            yerr=[np.array(means) - np.array(lo), np.array(hi) - np.array(means)],
            fmt="o",
            ms=4,
            color=SYM_COLOR[sym],
            ecolor=GREY,
            capsize=3,
        )
        ax.axhline(0, color=BAD, lw=0.8, ls="--")
        ax.set_title(f"{sym[:3]}", fontsize=9)
        ax.set_xlabel("funding decile (1 = most negative)")
        ax.set_xticks(range(1, 11))
        ax.tick_params(labelsize=8)
    axes[0].set_ylabel(f"mean return over next {horizon}h (bps)")
    fig.suptitle(
        "Forward returns conditional on funding decile · 95% moving-block bootstrap CIs",
        fontsize=9,
    )
    VALUES["funding_conditional"] = {
        sym: {
            "top_decile_mean_bps": round(res[0][9], 1),
            "top_decile_ci_bps": [round(res[1][9], 1), round(res[2][9], 1)],
            "bottom_decile_mean_bps": round(res[0][0], 1),
            "bottom_decile_ci_bps": [round(res[1][0], 1), round(res[2][0], 1)],
            "horizon_hours": horizon,
        }
        for sym, res in results.items()
    }
    fig.tight_layout()
    return save(fig, "fig_5_10_funding_conditional")


# Fig 5.11 — rolling BTC-ETH correlation + lagged cross-correlation
def fig_5_11() -> str:
    joined = (
        BARS[("BTCUSDT", "1h")]
        .select("open_time", pl.col("log_return").alias("r_btc"))
        .join(
            BARS[("ETHUSDT", "1h")].select("open_time", pl.col("log_return").alias("r_eth")),
            on="open_time",
        )
        .drop_nulls()
    )
    r_btc = joined["r_btc"].to_numpy()
    r_eth = joined["r_eth"].to_numpy()
    VALUES["btc_eth_corr_full_1h"] = round(float(np.corrcoef(r_btc, r_eth)[0, 1]), 3)

    window = 30 * 24
    rolled = joined.with_columns(
        pl.rolling_corr(
            pl.col("r_btc"), pl.col("r_eth"), window_size=window, min_samples=window
        ).alias("corr")
    ).drop_nulls("corr")
    VALUES["btc_eth_rolling_corr_band"] = [
        round(rolled["corr"].quantile(0.05), 2),
        round(rolled["corr"].quantile(0.95), 2),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.2), width_ratios=[1.7, 1])
    axes[0].plot(rolled["open_time"].to_list(), rolled["corr"].to_list(), color=ACCENT, lw=0.9)
    axes[0].set_ylim(0.4, 1.0)
    axes[0].set_ylabel("30-day rolling correlation")
    axes[0].xaxis.set_major_locator(mdates.YearLocator())
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[0].tick_params(labelsize=8)

    lags = range(-12, 13)
    cross = []
    for lag in lags:
        if lag < 0:
            c = np.corrcoef(r_btc[:lag], r_eth[-lag:])[0, 1]
        elif lag > 0:
            c = np.corrcoef(r_btc[lag:], r_eth[:-lag])[0, 1]
        else:
            c = np.corrcoef(r_btc, r_eth)[0, 1]
        cross.append(float(c))
    axes[1].bar(list(lags), cross, color=SECOND, width=0.8)
    axes[1].set_xlabel("lag (hours) · >0 = BTC leads")
    axes[1].set_ylabel("cross-correlation")
    axes[1].tick_params(labelsize=8)
    off_peak = max(abs(c) for lag, c in zip(lags, cross, strict=True) if lag != 0)
    VALUES["btc_eth_max_offzero_crosscorr"] = round(off_peak, 3)
    fig.tight_layout()
    return save(fig, "fig_5_11_cross_asset")


# Feature matrix (shared by 5.12 and 5.16)
def _feature_frame() -> tuple[pl.DataFrame, list[str]]:
    specs = resolve_feature_set(EXP.features.feature_set)
    frame, resolved = build_feature_frame(
        BARS[("BTCUSDT", "1h")], specs, holdout_start=LAKE.holdout_start
    )
    cols = feature_columns(resolved)
    return frame, cols


# Fig 5.12 — feature correlation matrix + PCA scree
def fig_5_12() -> str:
    frame, cols = _feature_frame()
    corr = feature_correlation_matrix(frame, cols)
    pairs = high_correlation_pairs(corr, threshold=0.9)
    VALUES["feature_pairs_above_09"] = pairs.height
    VALUES["feature_pairs_list"] = [f"{a} ~ {b} ({rho:.3f})" for a, b, rho in pairs.iter_rows()]
    scree = pca_scree(frame, cols)
    n90 = int(scree.filter(pl.col("cumulative_share") >= 0.9)["component"].min())
    VALUES["pca_components_90pct"] = n90
    VALUES["pca_first3_share_pct"] = round(scree["cumulative_share"][2] * 100, 1)
    VALUES["n_features"] = len(cols)

    matrix = np.array(
        [
            [
                corr.filter((pl.col("feature_a") == a) & (pl.col("feature_b") == b))[
                    "spearman"
                ].item()
                for b in cols
            ]
            for a in cols
        ]
    )
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.6), width_ratios=[1.5, 1])
    im = axes[0].imshow(matrix, cmap="RdBu_r", vmin=-1, vmax=1)
    axes[0].set_xticks(range(len(cols)))
    axes[0].set_xticklabels(cols, rotation=90, fontsize=6)
    axes[0].set_yticks(range(len(cols)))
    axes[0].set_yticklabels(cols, fontsize=6)
    fig.colorbar(im, ax=axes[0], shrink=0.8, label="Spearman")
    axes[0].set_title("Feature correlation (BTC 1h, development)", fontsize=9)

    axes[1].bar(
        scree["component"].to_list(), (scree["explained_share"] * 100).to_list(), color=ACCENT
    )
    axes[1].plot(
        scree["component"].to_list(),
        (scree["cumulative_share"] * 100).to_list(),
        "o-",
        ms=3,
        color=AMBER,
        label="cumulative",
    )
    axes[1].axhline(90, color=BAD, lw=0.7, ls="--")
    axes[1].set_xlabel("principal component")
    axes[1].set_ylabel("% variance")
    axes[1].legend(fontsize=8)
    axes[1].set_title("PCA scree", fontsize=9)
    fig.tight_layout()
    return save(fig, "fig_5_12_features")


# Fig 5.13 — survival function log-log + Hill fit
def fig_5_13() -> str:
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    tail_fraction = 0.02
    for sym in SYMBOLS:
        r = rets(sym)
        surv = survival_function(r).filter(pl.col("abs_return") >= 1e-4)
        hill = hill_tail_index(r, tail_fraction=tail_fraction)
        VALUES[f"hill_alpha_{sym[:3].lower()}"] = round(hill["alpha"], 2)
        VALUES[f"hill_se_{sym[:3].lower()}"] = round(hill["se"], 2)
        ax.loglog(
            surv["abs_return"].to_list(),
            surv["survival"].to_list(),
            ".",
            ms=2.5,
            color=SYM_COLOR[sym],
            label=f"{sym[:3]} (Hill α = {hill['alpha']:.2f} ± {hill['se']:.2f})",
        )
        # Hill fit line anchored at the tail threshold.
        x0, p0 = hill["threshold"], tail_fraction
        grid = np.logspace(np.log10(x0), np.log10(surv["abs_return"].max()), 50)
        ax.loglog(grid, p0 * (grid / x0) ** (-hill["alpha"]), color=SYM_COLOR[sym], lw=1.0, ls="--")
    VALUES["hill_tail_fraction_pct"] = tail_fraction * 100
    ax.set_xlabel("|1h log-return|")
    ax.set_ylabel("P(|r| > x)")
    ax.legend(fontsize=8)
    ax.set_title(
        "Empirical survival of absolute returns, log-log · dashed = Hill power-law fit", fontsize=9
    )
    fig.tight_layout()
    return save(fig, "fig_5_13_tails_hill")


# Fig 5.14 — variance ratios + rolling Hurst
def fig_5_14() -> str:
    horizons = [2, 4, 8, 16, 24, 48]
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.3))
    for sym in SYMBOLS:
        r = rets(sym)
        profile = variance_ratio_profile(r, horizons)
        se = np.where(
            profile["z_robust"].to_numpy() != 0,
            np.abs((profile["vr"].to_numpy() - 1) / profile["z_robust"].to_numpy()),
            np.nan,
        )
        axes[0].errorbar(
            profile["q"].to_list(),
            profile["vr"].to_list(),
            yerr=1.96 * se,
            fmt="o-",
            ms=4,
            lw=1.0,
            capsize=3,
            color=SYM_COLOR[sym],
            label=sym[:3],
        )
        VALUES[f"vr_{sym[:3].lower()}"] = {
            int(q): {"vr": round(v, 3), "z": round(z, 2)}
            for q, v, z in zip(
                profile["q"].to_list(),
                profile["vr"].to_list(),
                profile["z_robust"].to_list(),
                strict=True,
            )
        }
        VALUES[f"hurst_global_{sym[:3].lower()}"] = round(hurst_rs(r), 3)
    axes[0].axhline(1.0, color=BAD, lw=0.8, ls="--")
    axes[0].set_xlabel("horizon q (hours)")
    axes[0].set_ylabel("variance ratio VR(q)")
    axes[0].set_title("Lo–MacKinlay VR, robust 95% bands", fontsize=9)
    axes[0].legend(fontsize=8)

    for sym in SYMBOLS:
        rh = rolling_hurst(BARS[(sym, "1h")].drop_nulls("log_return"))
        axes[1].plot(
            rh["time"].to_list(), rh["hurst"].to_list(), lw=1.0, color=SYM_COLOR[sym], label=sym[:3]
        )
        VALUES[f"rolling_hurst_range_{sym[:3].lower()}"] = [
            round(rh["hurst"].min(), 3),
            round(rh["hurst"].max(), 3),
        ]
    axes[1].axhline(0.5, color=BAD, lw=0.8, ls="--")
    axes[1].set_ylabel("Hurst (180-day window)")
    axes[1].set_title("Rolling Hurst exponent", fontsize=9)
    axes[1].legend(fontsize=8)
    axes[1].xaxis.set_major_locator(mdates.YearLocator(2))
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[1].tick_params(labelsize=8)
    fig.tight_layout()
    return save(fig, "fig_5_14_variance_ratio_hurst")


# Fig 5.15 — volume vs |return| (contemporaneous)
def fig_5_15() -> str:
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.4), sharey=True)
    for ax, sym in zip(axes, SYMBOLS, strict=True):
        frame = (
            BARS[(sym, "1h")]
            .drop_nulls("log_return")
            .filter((pl.col("volume") > 0) & (pl.col("log_return") != 0))
        )
        absret = (frame["log_return"].abs() * 1e4).to_numpy()
        volume = frame["volume"].to_numpy()
        rho = sstats.spearmanr(volume, absret).statistic
        VALUES[f"volume_absret_spearman_{sym[:3].lower()}"] = round(float(rho), 3)
        hb = ax.hexbin(
            volume, absret, xscale="log", yscale="log", gridsize=45, cmap="YlGnBu", mincnt=1
        )
        ax.set_xlabel("hourly volume")
        ax.set_title(f"{sym[:3]} · Spearman ρ = {rho:.3f}", fontsize=9)
        ax.tick_params(labelsize=8)
    axes[0].set_ylabel("|1h return| (bps)")
    fig.colorbar(hb, ax=axes, shrink=0.85, label="bars")
    return save(fig, "fig_5_15_volume_volatility")


# Fig 5.16 — mutual information vs horizon with permutation floor
def fig_5_16() -> str:
    frame, cols = _feature_frame()
    # Raw price-level features (moving averages, ATR in price units) are
    # non-stationary: their apparent MI against long-horizon returns reflects
    # shared drift across epochs, not predictive structure. The MI analysis is
    # restricted to the stationary members of the set.
    level_features = {"sma_24", "sma_96", "atr_14"}
    cols = [c for c in cols if c not in level_features]
    VALUES["mi_excluded_level_features"] = sorted(level_features)
    # Deterministic 1-in-2 subsample keeps the kNN MI estimator tractable.
    sub = frame.gather_every(2)
    params = {"cols": cols, "sub": 2, "seed": SEED, "horizons_stage_a": [1, 4, 24], "v": 2}

    stage_a = cached_frame(
        "mi_all_features",
        params,
        lambda: mutual_information_by_horizon(
            sub, cols, horizons=[1, 4, 24], n_permutations=3, seed=SEED
        ),
    )
    top = (
        stage_a.group_by("feature")
        .agg(pl.col("mi_nats").max().alias("mi_max"))
        .sort("mi_max", descending=True)
        .head(4)["feature"]
        .to_list()
    )
    horizons = [1, 2, 4, 8, 12, 24, 48]
    curve = cached_frame(
        "mi_top_curve",
        {**params, "top": top, "horizons": horizons},
        lambda: mutual_information_by_horizon(
            sub, top, horizons=horizons, n_permutations=5, seed=SEED
        ),
    )

    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    palette = [ACCENT, SECOND, AMBER, "#7c3aed"]
    for color, feat in zip(palette, top, strict=True):
        sub_curve = curve.filter(pl.col("feature") == feat).sort("horizon_bars")
        ax.plot(
            sub_curve["horizon_bars"].to_list(),
            (sub_curve["mi_nats"] * 1000).to_list(),
            "o-",
            ms=3.5,
            lw=1.1,
            color=color,
            label=feat,
        )
    floor = curve.group_by("horizon_bars").agg(pl.col("noise_floor_max").max()).sort("horizon_bars")
    ax.fill_between(
        floor["horizon_bars"].to_list(),
        0,
        (floor["noise_floor_max"] * 1000).to_list(),
        color=GREY,
        alpha=0.25,
        label="permutation noise floor (max of 5)",
    )
    ax.set_xscale("log")
    ax.set_xticks(horizons)
    ax.set_xticklabels(horizons)
    ax.set_xlabel("prediction horizon (1h bars)")
    ax.set_ylabel("mutual information (millinats)")
    ax.legend(fontsize=7.5)
    ax.set_title(
        "MI between strongest features and forward returns · BTC 1h, development", fontsize=9
    )

    mi_range = stage_a.filter(pl.col("mi_nats") > 0)
    VALUES["mi_range_nats"] = [
        round(float(stage_a["mi_nats"].min()), 4),
        round(float(stage_a["mi_nats"].max()), 4),
    ]
    VALUES["mi_top_features"] = top
    VALUES["mi_above_floor_h1"] = int(
        stage_a.filter(
            (pl.col("horizon_bars") == 1) & (pl.col("mi_nats") > pl.col("noise_floor_max"))
        ).height
    )
    _ = mi_range
    fig.tight_layout()
    return save(fig, "fig_5_16_mutual_information")


# Tables and remaining values
def compute_table_5_1() -> str:
    lines = [
        "| Symbol | Timeframe | n | Mean (bps) | Std (bps) | Skew | Exc. kurtosis | Min (%) | Max (%) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for sym in SYMBOLS:
        for tf in ("5m", "15m", "1h"):
            stats_d = return_stats(BARS[(sym, tf)])
            lines.append(
                f"| {sym} | {tf} | {int(stats_d['n']):,} | {stats_d['mean'] * 1e4:.3f} | "
                f"{stats_d['std'] * 1e4:.2f} | {stats_d['skew']:.2f} | {stats_d['excess_kurtosis']:.1f} | "
                f"{stats_d['min'] * 100:.2f} | {stats_d['max'] * 100:.2f} |"
            )
            if tf == "1h":
                VALUES[f"exc_kurtosis_1h_{sym[:3].lower()}"] = round(stats_d["excess_kurtosis"], 1)
                VALUES[f"skew_1h_{sym[:3].lower()}"] = round(stats_d["skew"], 2)
    return "\n".join(lines)


def compute_table_5_2() -> str:
    rows = []
    for sym in SYMBOLS:
        frame = BARS[(sym, "1h")]
        r = rets(sym)
        prices = frame["close"].log().to_numpy()
        stats_d = return_stats(frame)
        lb_r = ljung_box(r, lags=24)
        lb_sq = ljung_box(r**2, lags=24)
        arch = arch_lm_test(r)
        adf_p = adf_test(prices)
        adf_r = adf_test(r)
        kpss_p = kpss_test(prices)
        kpss_r = kpss_test(r)
        hurst = hurst_rs(r)
        rows.append(
            {
                "symbol": sym,
                "jb_stat": stats_d["jarque_bera"],
                "jb_p": stats_d["jarque_bera_pvalue"],
                "lb_ret_stat": lb_r["lb_stat"],
                "lb_ret_p": lb_r["lb_pvalue"],
                "lb_sq_p": lb_sq["lb_pvalue"],
                "arch_p": arch["lm_pvalue"],
                "adf_price_p": adf_p["pvalue"],
                "adf_ret_p": adf_r["pvalue"],
                "kpss_price_p": kpss_p["pvalue"],
                "kpss_ret_p": kpss_r["pvalue"],
                "hurst": hurst,
            }
        )
        VALUES[f"lb_returns_p_{sym[:3].lower()}"] = float(lb_r["lb_pvalue"])
        VALUES[f"adf_price_p_{sym[:3].lower()}"] = round(float(adf_p["pvalue"]), 4)
    VALUES["hurst_table"] = {row["symbol"]: round(row["hurst"], 3) for row in rows}

    lines = [
        "| Test | Series | BTC | ETH | Reading |",
        "|---|---|---|---|---|",
    ]
    b, e = rows[0], rows[1]

    def _p(x: float) -> str:
        return "< 1e-16" if x < 1e-16 else f"{x:.3g}"

    lines.append(
        f"| Jarque–Bera | returns | {b['jb_stat']:.3g} (p {_p(b['jb_p'])}) | "
        f"{e['jb_stat']:.3g} (p {_p(e['jb_p'])}) | normality rejected |"
    )
    lines.append(
        f"| Ljung–Box (24) | returns | p = {_p(b['lb_ret_p'])} | p = {_p(e['lb_ret_p'])} | "
        "rejects — but the underlying ACF is economically negligible (lag-1 ≈ −0.02) |"
    )
    lines.append(
        f"| Ljung–Box (24) | squared returns | p {_p(b['lb_sq_p'])} | p {_p(e['lb_sq_p'])} | "
        "strong volatility clustering |"
    )
    lines.append(
        f"| ARCH-LM (12) | returns | p {_p(b['arch_p'])} | p {_p(e['arch_p'])} | "
        "conditional heteroskedasticity |"
    )
    lines.append(
        f"| ADF | log price | p = {b['adf_price_p']:.3f} | p = {e['adf_price_p']:.3f} | "
        "unit root kept (ETH borderline at 5%) |"
    )
    lines.append(
        f"| ADF | returns | p {_p(b['adf_ret_p'])} | p {_p(e['adf_ret_p'])} | returns stationary |"
    )
    lines.append(
        f"| KPSS | log price | p = {b['kpss_price_p']:.3f} | p = {e['kpss_price_p']:.3f} | "
        "stationarity rejected on prices |"
    )
    lines.append(
        f"| KPSS | returns | p = {b['kpss_ret_p']:.3f} | p = {e['kpss_ret_p']:.3f} | "
        "stationarity kept on returns |"
    )
    lines.append(
        f"| Hurst (R/S) | returns | {b['hurst']:.3f} | {e['hurst']:.3f} | close to memoryless 0.5 |"
    )
    return "\n".join(lines)


def compute_table_5_3() -> str:
    table = market_regime_stats(BARS[("BTCUSDT", "1h")], BARS[("ETHUSDT", "1h")])
    VALUES["regime_table"] = table.to_dicts()
    lines = [
        "| Regime | Window | Bars | BTC ann. ret | BTC ann. vol | BTC exc. kurt | ETH ann. vol | BTC–ETH corr |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in table.iter_rows(named=True):
        lines.append(
            f"| {row['regime']} | {row['start']} → {row['end']} | {row['n_bars']:,} | "
            f"{row['btc_ann_return'] * 100:+.0f}% | {row['btc_ann_vol'] * 100:.0f}% | "
            f"{row['btc_exc_kurtosis']:.1f} | {row['eth_ann_vol'] * 100:.0f}% | "
            f"{row['btc_eth_corr']:.3f} |"
        )
    return "\n".join(lines)


def compute_extra_values() -> None:
    # Leverage effect (5.3): corr(r_t, forward 24h realized vol).
    for sym in SYMBOLS:
        lev = leverage_effect(BARS[(sym, "1h")].drop_nulls("log_return"), forward_bars=24)
        VALUES[f"leverage_effect_{sym[:3].lower()}"] = round(lev["corr"], 3)

    # Largest losses vs gains (5.2).
    for sym in SYMBOLS:
        r = np.sort(rets(sym))
        losses, gains = -r[:10], r[-10:][::-1]
        VALUES[f"top10_loss_vs_gain_{sym[:3].lower()}"] = {
            "mean_loss_pct": round(float(losses.mean() * 100), 2),
            "mean_gain_pct": round(float(gains.mean() * 100), 2),
            "max_loss_pct": round(float(losses[0] * 100), 2),
            "max_gain_pct": round(float(gains[0] * 100), 2),
        }

    # Engle-Granger (5.6).
    eg = engle_granger_by_regime(BARS[("BTCUSDT", "1h")], BARS[("ETHUSDT", "1h")])
    VALUES["engle_granger"] = eg.select("window", "pvalue", "n").to_dicts()

    # Triple-barrier labels at the protocol's parameters (5.7), BTC 1h,
    # every-bar long-side events, study costs incl. realized funding.
    def _labels() -> pl.DataFrame:
        bars = BARS[("BTCUSDT", "1h")]
        with_funding = attach_funding(bars, FUNDING["BTCUSDT"]).with_columns(
            pl.when(
                pl.col("funding_time").is_not_null()
                & (pl.col("funding_time") > pl.col("open_time") - pl.duration(hours=1))
            )
            .then(pl.col("funding_rate"))
            .otherwise(0.0)
            .alias("funding_rate_in_bar")
        )
        tr = pl.max_horizontal(
            pl.col("high") - pl.col("low"),
            (pl.col("high") - pl.col("close").shift(1)).abs(),
            (pl.col("low") - pl.col("close").shift(1)).abs(),
        )
        with_vol = with_funding.with_columns(
            (tr.rolling_mean(window_size=14, min_samples=14) / pl.col("close")).alias("atr_frac")
        ).drop_nulls("atr_frac")
        events = with_vol.select(
            pl.col("open_time").alias("event_time"), pl.lit(1).cast(pl.Int64).alias("side")
        ).head(with_vol.height - 26)
        spec = TripleBarrierSpec(
            upper_barrier_atr=EXP.labeling.upper_barrier_atr,
            lower_barrier_atr=EXP.labeling.lower_barrier_atr,
            vertical_barrier_bars=EXP.labeling.vertical_barrier_bars,
            min_return_bps=EXP.labeling.min_return_bps,
            exit_fill="next_open",
        )
        costs = LabelCosts(
            fee_bps_per_side=4.0, slippage_bps_per_side=1.0, funding_rate_col="funding_rate_in_bar"
        )
        return triple_barrier_labels(with_vol, events, spec, volatility_col="atr_frac", costs=costs)

    labels = cached_frame(
        "labels_btc_1h",
        {
            "barriers": [
                EXP.labeling.upper_barrier_atr,
                EXP.labeling.lower_barrier_atr,
                EXP.labeling.vertical_barrier_bars,
            ],
            "costs": [4.0, 1.0, "funding"],
            "events": "all_bars_long",
        },
        _labels,
    )
    VALUES["labels_btc"] = {k: round(v, 3) for k, v in label_summary(labels).items()}


def main() -> int:
    builders = (
        fig_5_1,
        fig_5_2,
        fig_5_3,
        fig_5_4,
        fig_5_5,
        fig_5_6,
        fig_5_7,
        fig_5_8,
        fig_5_9,
        fig_5_10,
        fig_5_11,
        fig_5_12,
        fig_5_13,
        fig_5_14,
        fig_5_15,
        fig_5_16,
    )
    for fn in builders:
        print(fn())
    tables = {
        "table_5_1": compute_table_5_1(),
        "table_5_2": compute_table_5_2(),
        "table_5_3": compute_table_5_3(),
    }
    compute_extra_values()
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {"values": VALUES, "tables": tables}
    (OUT / "values_ch5.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(OUT / "values_ch5.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
