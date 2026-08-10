"""Execute the three *advanced dependence* EDA analyses and save their artifacts.

This runner appends inferential depth to the descriptive EDA without touching any
existing figure/table:

1. **Block-bootstrap confidence intervals** for the mean return, realised
   volatility, Sharpe ratio, the BTC-ETH correlation and the differences between
   volatility regimes and between sampling frequencies (figure ``f22``, table
   ``t37``).
2. **Non-parametric regime comparison** (Kruskal-Wallis + Dunn post-hoc with a
   Benjamini-Hochberg correction and epsilon-squared effect size) of absolute
   return, high-low range, volume, funding and drawdown across the low/medium/
   high volatility regimes (figure ``f23``, tables ``t38`` / ``t38b``).
3. **Extreme-tail dependence** between BTC and ETH: normal-versus-stress
   correlation, conditional crash probabilities, 5%/1% co-exceedance ratios and
   their time evolution (figure ``f24``, tables ``t39`` / ``t39b``).

All computations run strictly on the *development* partition (the frozen holdout
is excluded on load and re-checked). Everything else the notebook already
produced is left untouched.

Run with: ``uv run python scripts/run_eda_advanced.py``
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from perp_lab import eda
from perp_lab.config import load_data_contract, load_eda_config, load_settings
from perp_lab.config.models import Paths
from perp_lab.eda import DataLake
from perp_lab.eda.bootstrap import bootstrap_ci, bootstrap_diff_ci, mean_stat, sharpe_stat, vol_stat
from perp_lab.reporting import (
    ArtifactContext,
    apply_house_style,
    asset_color,
    regime_color,
    save_figure,
    save_table,
)

REGIMES = ("low", "medium", "high")
BLOCK = 24  # 24 one-hour bars = one 24/7 day
N_BOOT = 1000


def _setup() -> tuple[ArtifactContext, dict, dict, dict, int]:
    # Run from the repository root so relative data/ and reports/ paths resolve,
    # and force a non-interactive backend for headless figure export.
    os.chdir(Path(__file__).resolve().parents[1])
    if str(Path.cwd() / "src") not in sys.path:
        sys.path.insert(0, str(Path.cwd() / "src"))
    plt.switch_backend("Agg")
    apply_house_style()
    settings = load_settings()
    seed = settings.seed
    np.random.seed(seed)
    contract = load_data_contract()
    eda_cfg = load_eda_config()
    paths = Paths()
    lake = DataLake(contract, paths)

    symbols = list(contract.symbol_names())
    timeframes = list(contract.all_timeframes())
    ret: dict[str, dict[str, pl.DataFrame]] = {s: {} for s in symbols}
    funding: dict[str, pl.DataFrame] = {}

    ctx = ArtifactContext(
        notebook="01_comprehensive_exploratory_data_analysis",
        figures_dir=paths.reports_root / "figures" / "eda",
        tables_dir=paths.reports_root / "tables" / "eda",
        metadata_dir=paths.reports_root / "metadata" / "eda",
        config={
            "seed": seed,
            "contract_version": contract.version,
            "holdout_start": lake.holdout_start.isoformat(),
            "days_per_year": eda_cfg.trading_days_per_year,
            "block_bars": BLOCK,
            "n_boot": N_BOOT,
            "analysis": "advanced_dependence (bootstrap CIs, regime tests, tail dependence)",
        },
        repo_root=".",
    )
    for sym in symbols:
        for tf in timeframes:
            ds = lake.load_klines(sym, tf, partition="development")
            eda.assert_no_holdout(ds.frame, lake.holdout_start, time_col="open_time")
            ret[sym][tf] = eda.add_log_returns(ds.frame)
            ctx.datasets[ds.dataset_id] = ds.sha256 or ""
        fds = lake.load_funding(sym, partition="development")
        funding[sym] = fds.frame

    btc = symbols[0]
    dev = ret[btc]["1h"]
    ctx.period = (
        f"{dev.select(pl.col('open_time').min()).item()} .. "
        f"{dev.select(pl.col('open_time').max()).item()} (development, holdout excluded)"
    )
    meta = {
        "symbols": symbols,
        "timeframes": timeframes,
        "days_per_year": eda_cfg.trading_days_per_year,
    }
    return ctx, ret, funding, meta, seed


def _logret(ret: dict, sym: str, tf: str) -> np.ndarray:
    return ret[sym][tf].select("log_return").drop_nulls().to_series().to_numpy()


# --------------------------------------------------------------------------- #
# Analysis 1 - block-bootstrap confidence intervals
# --------------------------------------------------------------------------- #
def analysis_bootstrap(ctx: ArtifactContext, ret: dict, meta: dict) -> pl.DataFrame:
    symbols = meta["symbols"]
    timeframes = meta["timeframes"]
    dpy = meta["days_per_year"]
    rows: list[dict[str, object]] = []

    def _row(stat: str, group: str, tf: str, ci: dict, *, scale: float = 1.0) -> None:
        if not ci:
            return
        rows.append(
            {
                "statistic": stat,
                "group": group,
                "timeframe": tf,
                "estimate": round(float(ci["estimate"]) * scale, 6),
                "ci_low": round(float(ci["ci_low"]) * scale, 6),
                "ci_high": round(float(ci["ci_high"]) * scale, 6),
                "prob_positive": round(float(ci["prob_positive"]), 4)
                if "prob_positive" in ci
                else None,
                "n": float(ci.get("n", ci.get("n_a", float("nan")))),
            }
        )

    for sym in symbols:
        r1h = _logret(ret, sym, "1h")
        _row(
            "mean_return_bps",
            sym,
            "1h",
            bootstrap_ci(r1h, mean_stat, block=BLOCK, n_boot=N_BOOT),
            scale=1e4,
        )
        _row(
            "sharpe_annualised",
            sym,
            "1h",
            bootstrap_ci(r1h, sharpe_stat(24 * dpy), block=BLOCK, n_boot=N_BOOT),
        )
        for tf in timeframes:
            arr = _logret(ret, sym, tf)
            factor = eda.annualization_factor(tf, dpy)
            _row(
                "volatility_annualised",
                sym,
                tf,
                bootstrap_ci(arr * factor, vol_stat, block=BLOCK, n_boot=N_BOOT),
            )

    # BTC-ETH return correlation CI (existing helper).
    corr = eda.block_bootstrap_corr_ci(
        ret[symbols[0]]["1h"], ret[symbols[1]]["1h"], block=BLOCK, n_boot=N_BOOT
    )
    if corr:
        rows.append(
            {
                "statistic": "corr_btc_eth",
                "group": f"{symbols[0]}-{symbols[1]}",
                "timeframe": "1h",
                "estimate": corr["corr"],
                "ci_low": corr["ci_low"],
                "ci_high": corr["ci_high"],
                "prob_positive": None,
                "n": corr["n"],
            }
        )

    # Difference between frequencies: BTC annualised volatility 5m minus 1h.
    f5m, f1h = eda.annualization_factor("5m", dpy), eda.annualization_factor("1h", dpy)
    _row(
        "diff_ann_vol_5m_minus_1h",
        symbols[0],
        "5m-1h",
        bootstrap_diff_ci(
            _logret(ret, symbols[0], "5m") * f5m,
            _logret(ret, symbols[0], "1h") * f1h,
            vol_stat,
            block=BLOCK,
            n_boot=N_BOOT,
        ),
    )

    table = pl.DataFrame(rows)
    save_table(
        table,
        "t37_bootstrap_confidence_intervals",
        ctx,
        caption="Block-bootstrap 95% confidence intervals (24-bar moving blocks, "
        f"{N_BOOT} resamples) for return, volatility, Sharpe, BTC-ETH correlation and frequency differences (development).",
    )
    _plot_bootstrap(ctx, table, symbols, timeframes)
    return table


def _errorbar(ax, labels, est, lo, hi, colors, title, ylabel) -> None:
    x = np.arange(len(labels))
    yerr = np.vstack([np.array(est) - np.array(lo), np.array(hi) - np.array(est)])
    ax.errorbar(x, est, yerr=yerr, fmt="o", capsize=4, color="black", ecolor="grey", zorder=3)
    for xi, c in zip(x, colors, strict=True):
        ax.scatter([xi], [est[x.tolist().index(xi)]], color=c, s=40, zorder=4)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.axhline(0.0, color="red", lw=0.8, ls="--", alpha=0.5)


def _plot_bootstrap(ctx: ArtifactContext, table: pl.DataFrame, symbols, timeframes) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), constrained_layout=True)

    vol = table.filter(pl.col("statistic") == "volatility_annualised")
    labels = [f"{r['group']}\n{r['timeframe']}" for r in vol.iter_rows(named=True)]
    colors = [asset_color(r["group"]) for r in vol.iter_rows(named=True)]
    _errorbar(
        axes[0],
        labels,
        vol["estimate"].to_list(),
        vol["ci_low"].to_list(),
        vol["ci_high"].to_list(),
        colors,
        "(a) Annualised volatility by frequency",
        "ann. volatility",
    )

    mean = table.filter(pl.col("statistic") == "mean_return_bps")
    _errorbar(
        axes[1],
        mean["group"].to_list(),
        mean["estimate"].to_list(),
        mean["ci_low"].to_list(),
        mean["ci_high"].to_list(),
        [asset_color(s) for s in mean["group"].to_list()],
        "(b) Mean 1h log-return",
        "mean return (bps)",
    )

    shp = table.filter(pl.col("statistic") == "sharpe_annualised")
    _errorbar(
        axes[2],
        shp["group"].to_list(),
        shp["estimate"].to_list(),
        shp["ci_low"].to_list(),
        shp["ci_high"].to_list(),
        [asset_color(s) for s in shp["group"].to_list()],
        "(c) Annualised Sharpe (1h)",
        "Sharpe",
    )

    fig.suptitle(
        "Block-bootstrap 95% confidence intervals | development (holdout excluded)", fontsize=12
    )
    save_figure(
        fig,
        "f22_bootstrap_confidence_intervals",
        ctx,
        caption="Block-bootstrap 95% CIs for annualised volatility (by frequency), mean 1h return and annualised Sharpe (development).",
    )
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Analysis 2 - regime comparison (Kruskal-Wallis + Dunn + effect size)
# --------------------------------------------------------------------------- #
def analysis_regimes(ctx: ArtifactContext, ret: dict, funding: dict, meta: dict) -> pl.DataFrame:
    btc = meta["symbols"][0]
    tagged = eda.tag_trend_volatility_regimes(ret[btc]["1h"], trend_window=168, vol_window=24)
    tagged = eda.add_drawdown(tagged)
    tagged = eda.attach_funding(tagged, funding[btc], tolerance="8h")
    tagged = tagged.with_columns(
        pl.col("log_return").abs().alias("abs_ret"),
        ((pl.col("high") - pl.col("low")) / pl.col("close")).alias("hl_range"),
    ).filter(pl.col("vol_regime").is_in(REGIMES))

    value_cols = ["abs_ret", "hl_range", "volume", "funding_rate", "drawdown"]
    summary = eda.regime_comparison(tagged, value_cols)
    save_table(
        summary,
        "t38_regime_kruskal",
        ctx,
        caption="Kruskal-Wallis test across low/medium/high volatility regimes (BTC 1h, development): H, p-value and epsilon-squared effect size.",
    )

    posthoc_frames = []
    for col in value_cols:
        ph = eda.dunn_posthoc(tagged, col).with_columns(pl.lit(col).alias("variable"))
        posthoc_frames.append(ph)
    posthoc = pl.concat(posthoc_frames).select(
        "variable", "group_a", "group_b", "n_a", "n_b", "z", "p_raw", "p_adj", "reject"
    )
    save_table(
        posthoc,
        "t38b_regime_dunn_posthoc",
        ctx,
        caption="Dunn post-hoc pairwise comparisons across volatility regimes with Benjamini-Hochberg correction (BTC 1h, development).",
    )

    _plot_regimes(ctx, tagged, summary)
    return summary


def _regime_box(
    ax, tagged: pl.DataFrame, col: str, transform, ylabel: str, summary: pl.DataFrame
) -> None:
    data, colors = [], []
    for reg in REGIMES:
        v = (
            tagged.filter(pl.col("vol_regime") == reg)
            .select(col)
            .drop_nulls()
            .to_series()
            .to_numpy()
        )
        v = v[np.isfinite(v)]
        data.append(transform(v))
        colors.append(regime_color(reg))
    bp = ax.boxplot(
        data, tick_labels=list(REGIMES), showfliers=False, patch_artist=True, whis=(5, 95)
    )
    for patch, c in zip(bp["boxes"], colors, strict=True):
        patch.set_facecolor(c)
        patch.set_alpha(0.55)
    row = summary.filter(pl.col("variable") == col)
    ann = ""
    if row.height:
        r = row.row(0, named=True)
        ann = f"H={r['H']:.0f}, p={r['pvalue']:.1e}, eps2={r['epsilon_squared']:.3f}"
    ax.set_title(f"{col}\n{ann}", fontsize=10)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("volatility regime")


def _plot_regimes(ctx: ArtifactContext, tagged: pl.DataFrame, summary: pl.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    _regime_box(axes[0, 0], tagged, "abs_ret", lambda v: v * 1e4, "|log return| (bps)", summary)
    _regime_box(axes[0, 1], tagged, "hl_range", lambda v: v * 1e2, "high-low range (%)", summary)
    _regime_box(axes[1, 0], tagged, "volume", lambda v: np.log10(v[v > 0]), "log10 volume", summary)
    _regime_box(axes[1, 1], tagged, "drawdown", lambda v: v * 1e2, "drawdown (%)", summary)
    fig.suptitle(
        "Distributional differences across volatility regimes | BTC 1h | development", fontsize=12
    )
    save_figure(
        fig,
        "f23_regime_statistical_comparison",
        ctx,
        caption="Per-regime distributions (5th-95th whiskers) with Kruskal-Wallis H, p-value and epsilon-squared effect size (BTC 1h, development).",
    )
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Analysis 3 - extreme-tail dependence
# --------------------------------------------------------------------------- #
def analysis_stress(ctx: ArtifactContext, ret: dict, meta: dict) -> pl.DataFrame:
    btc, eth = meta["symbols"][0], meta["symbols"][1]
    left, right = ret[btc]["1h"], ret[eth]["1h"]

    coex = eda.coexceedance_summary(left, right, quantiles=(0.05, 0.01))
    save_table(
        coex,
        "t39_extreme_dependence_coexceedance",
        ctx,
        caption="BTC-ETH joint tail behaviour at the 5% and 1% quantiles (1h, development): joint probabilities, exceedance ratios vs independence and conditional crash probabilities.",
    )

    nvs = eda.normal_vs_stress_correlation(left, right, stress_quantile=0.10)
    ce05 = eda.conditional_exceedance(left, right, quantile=0.05, tail="lower")
    ce01 = eda.conditional_exceedance(left, right, quantile=0.01, tail="lower")
    corr_table = pl.DataFrame(
        [
            {"metric": "corr_all", "value": round(nvs["corr_all"], 4)},
            {"metric": "corr_calm", "value": round(nvs["corr_calm"], 4)},
            {"metric": "corr_stress", "value": round(nvs["corr_stress"], 4)},
            {"metric": "corr_stress_btc_only", "value": round(nvs["corr_stress_left"], 4)},
            {"metric": "p_eth_crash_given_btc_5pct", "value": round(ce05["p_right_given_left"], 4)},
            {"metric": "lift_vs_independence_5pct", "value": round(ce05["lift"], 4)},
            {"metric": "p_eth_crash_given_btc_1pct", "value": round(ce01["p_right_given_left"], 4)},
            {"metric": "lift_vs_independence_1pct", "value": round(ce01["lift"], 4)},
        ]
    )
    save_table(
        corr_table,
        "t39b_extreme_dependence_correlation",
        ctx,
        caption="Normal-vs-stress BTC-ETH correlation and conditional crash probabilities (1h, development). Stress = either asset in its lower decile.",
    )

    rolling = eda.rolling_tail_dependence(left, right, window=24 * 90, step=24 * 30, quantile=0.05)
    _plot_stress(ctx, nvs, coex, rolling)
    return coex


def _plot_stress(
    ctx: ArtifactContext, nvs: dict, coex: pl.DataFrame, rolling: pl.DataFrame
) -> None:
    fig = plt.figure(figsize=(13, 4.4), constrained_layout=True)
    gs = fig.add_gridspec(1, 3)

    ax0 = fig.add_subplot(gs[0, 0])
    labels = ["all", "calm", "stress"]
    vals = [nvs["corr_all"], nvs["corr_calm"], nvs["corr_stress"]]
    ax0.bar(labels, vals, color=["#4C72B0", "#55A868", "#C44E52"], alpha=0.85)
    ax0.set_ylim(0, 1)
    ax0.set_title("(a) BTC-ETH correlation:\ncalm vs stress")
    ax0.set_ylabel("Pearson correlation")

    ax1 = fig.add_subplot(gs[0, 1])
    q = [str(v) for v in coex["quantile"].to_list()]
    x = np.arange(len(q))
    w = 0.38
    ax1.bar(
        x - w / 2,
        coex["lower_ratio"].to_list(),
        width=w,
        label="lower tail",
        color="#C44E52",
        alpha=0.85,
    )
    ax1.bar(
        x + w / 2,
        coex["upper_ratio"].to_list(),
        width=w,
        label="upper tail",
        color="#4C72B0",
        alpha=0.85,
    )
    ax1.axhline(1.0, color="black", ls="--", lw=0.8, label="independence")
    ax1.set_xticks(x)
    ax1.set_xticklabels(q)
    ax1.set_xlabel("tail quantile")
    ax1.set_ylabel("co-exceedance ratio")
    ax1.set_title("(b) Joint co-exceedance\nvs independence")
    ax1.legend(fontsize=8)

    ax2 = fig.add_subplot(gs[0, 2])
    if rolling.height:
        ax2.plot(
            rolling["window_end"].to_list(),
            rolling["lower_ratio"].to_list(),
            color="#C44E52",
            marker="o",
            ms=3,
        )
    ax2.axhline(1.0, color="black", ls="--", lw=0.8)
    ax2.set_title("(c) Lower-tail co-exceedance\nover time (90d windows)")
    ax2.set_ylabel("lower-tail ratio")
    ax2.set_xlabel("window end (UTC)")
    ax2.tick_params(axis="x", rotation=30)

    fig.suptitle("BTC-ETH extreme-tail dependence | 1h | development", fontsize=12)
    save_figure(
        fig,
        "f24_extreme_tail_dependence",
        ctx,
        caption="BTC-ETH tail dependence: calm-vs-stress correlation, 5%/1% co-exceedance ratios and their time evolution (1h, development).",
    )
    plt.close(fig)


def main() -> int:
    ctx, ret, funding, meta, seed = _setup()
    print(f"Advanced EDA dependence analyses | seed={seed} | period: {ctx.period}")
    t37 = analysis_bootstrap(ctx, ret, meta)
    print(f"[1/3] bootstrap CIs -> {t37.height} rows (f22, t37)")
    t38 = analysis_regimes(ctx, ret, funding, meta)
    print(f"[2/3] regime tests  -> {t38.height} variables (f23, t38, t38b)")
    t39 = analysis_stress(ctx, ret, meta)
    print(f"[3/3] tail dependence -> {t39.height} quantiles (f24, t39, t39b)")
    print(f"Done at {datetime.now(UTC).isoformat()}. Figures/tables written under reports/**/eda.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
