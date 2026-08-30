"""Alternative-data annex: Fear & Greed and macro-event figures + values.

Run with: ``uv run python scripts/build_altdata_annex.py``
(requires ``scripts/ingest_altdata.py`` to have been run once)

Writes PNG + PDF pairs A1-A4 to ``reports/figures/thesis_altdata/`` plus
``values_altdata.json``. Development partition only; deterministic (seed 42).
Everything here is DESCRIPTIVE: none of it enters the canonical study, and
any strategy suggested by these figures would be a new pre-registered
hypothesis paying its own multiplicity cost.
"""

# ruff: noqa: RUF001  # typographic characters are intentional in figure text

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from perp_lab.config import load_data_contract
from perp_lab.config.models import Paths
from perp_lab.eda import DataLake
from perp_lab.eda.altdata import (
    event_hour_vs_matched_control,
    event_study,
    fear_greed_conditional,
    load_fear_greed,
    load_macro_events,
)
from perp_lab.eda.returns import add_log_returns

SEED = 42
OUT = Path("reports/figures/thesis_altdata")

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

CONTRACT = load_data_contract()
PATHS = Paths()
LAKE = DataLake(CONTRACT, PATHS)
SYMBOLS = ("BTCUSDT", "ETHUSDT")

BARS = {
    sym: add_log_returns(LAKE.load_klines(sym, "1h", partition="development").frame)
    for sym in SYMBOLS
}
FG = load_fear_greed(
    Path(PATHS.data_root) / "external" / "fear_greed.parquet",
    holdout_start=LAKE.holdout_start,
)
EVENTS = load_macro_events(
    Path(PATHS.data_root) / "external" / "us_macro_events.parquet",
    holdout_start=LAKE.holdout_start,
)


def save(fig: plt.Figure, name: str) -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    return f"{OUT / name}.png|.pdf"


# Fig A1 — Fear & Greed vs BTC price and realized volatility
def fig_a1() -> str:
    fg_dev = FG.filter(pl.col("date") >= pl.datetime(2020, 1, 1, time_zone="UTC"))
    btc = BARS["BTCUSDT"]
    daily_close = (
        btc.with_columns(pl.col("open_time").dt.truncate("1d").alias("day"))
        .group_by("day")
        .agg(pl.col("close").last())
        .sort("day")
    )
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.4, 4.6), sharex=True, height_ratios=[1, 1])
    ax1.plot(daily_close["day"].to_list(), daily_close["close"].to_list(), color=GREY, lw=0.9)
    ax1.set_yscale("log")
    ax1.set_ylabel("BTC close (log)")

    dates = fg_dev["date"].to_list()
    vals = fg_dev["value"].to_numpy()
    ax2.plot(dates, vals, color=ACCENT, lw=0.8)
    ax2.axhspan(0, 25, color="#fee2e2", zorder=0)
    ax2.axhspan(75, 100, color="#dcfce7", zorder=0)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("Fear & Greed")
    ax2.text(dates[10], 8, "extreme fear", fontsize=7.5, color=BAD)
    ax2.text(dates[10], 90, "extreme greed", fontsize=7.5, color=ACCENT)
    ax2.xaxis.set_major_locator(mdates.YearLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for ax in (ax1, ax2):
        ax.tick_params(labelsize=8)

    VALUES["fg_days_dev"] = fg_dev.height
    VALUES["fg_extreme_fear_days"] = int((vals <= 25).sum())
    VALUES["fg_extreme_greed_days"] = int((vals >= 75).sum())
    VALUES["fg_mean"] = round(float(vals.mean()), 1)
    fig.tight_layout()
    return save(fig, "fig_a1_fear_greed_series")


# Fig A2 — forward return / vol conditional on F&G quintile
def fig_a2() -> str:
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.4), sharey=True)
    for ax, sym in zip(axes, SYMBOLS, strict=True):
        table = fear_greed_conditional(FG, BARS[sym], horizon_bars=24, seed=SEED)
        x = table["quantile"].to_numpy()
        mean = table["fwd_ret_bps"].to_numpy()
        lo = table["fwd_ret_lo"].to_numpy()
        hi = table["fwd_ret_hi"].to_numpy()
        ax.errorbar(
            x,
            mean,
            yerr=[mean - lo, hi - mean],
            fmt="o",
            ms=4,
            color=SYM_COLOR[sym],
            ecolor=GREY,
            capsize=3,
        )
        ax.axhline(0, color=BAD, lw=0.8, ls="--")
        labels = [
            f"Q{q}\n[{int(a)}–{int(b)}]"
            for q, a, b in zip(table["quantile"], table["fg_min"], table["fg_max"], strict=True)
        ]
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7)
        ax.set_title(sym[:3], fontsize=9)
        VALUES[f"fg_conditional_{sym[:3].lower()}"] = table.to_dicts()
    axes[0].set_ylabel("mean next-24h return (bps)")
    fig.suptitle(
        "Forward 24h return by Fear & Greed quintile · one-day availability lag · "
        "95% moving-block bootstrap CIs",
        fontsize=9,
    )
    fig.tight_layout()
    return save(fig, "fig_a2_fg_conditional")


# Fig A3 — event study around CPI and FOMC (BTC, 1h)
def fig_a3() -> str:
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.4), sharey=True)
    baseline = float(np.nanmean(np.abs(BARS["BTCUSDT"]["log_return"].to_numpy())) * 1e4)
    for ax, kind, color in (
        (axes[0], "cpi_release", ACCENT),
        (axes[1], "fomc_decision", SECOND),
    ):
        times = EVENTS.filter(pl.col("event_type") == kind)["datetime_utc"]
        study = event_study(BARS["BTCUSDT"], times, window_bars=12)
        ax.bar(
            study["offset_bars"].to_list(),
            study["mean_absret_bps"].to_list(),
            color=color,
            width=0.8,
        )
        ax.axhline(baseline, color=BAD, lw=0.9, ls="--")
        n_ev = study["n_events"][0]
        ax.set_title(f"{kind.replace('_', ' ')} · {n_ev} events", fontsize=9)
        ax.set_xlabel("hours from event bar")
        VALUES[f"event_study_{kind}"] = {
            "n_events": int(n_ev),
            "event_bar_absret_bps": round(
                study.filter(pl.col("offset_bars") == 0)["mean_absret_bps"].item(), 1
            ),
            "next_bar_absret_bps": round(
                study.filter(pl.col("offset_bars") == 1)["mean_absret_bps"].item(), 1
            ),
            "baseline_absret_bps": round(baseline, 1),
        }
    axes[0].set_ylabel("mean |1h return| (bps)")
    axes[0].text(
        -11.5,
        baseline * 1.08,
        "unconditional mean",
        fontsize=7.5,
        color=BAD,
    )
    fig.suptitle("BTC hourly volatility around scheduled US macro events", fontsize=9)
    fig.tight_layout()
    return save(fig, "fig_a3_event_study")


# Fig A4 — event bar vs seasonality-matched control
def fig_a4() -> str:
    fig, ax = plt.subplots(figsize=(6.8, 3.4))
    kinds = ("cpi_release", "fomc_decision")
    width = 0.35
    for i, sym in enumerate(SYMBOLS):
        stats = []
        for kind in kinds:
            times = EVENTS.filter(pl.col("event_type") == kind)["datetime_utc"]
            result = event_hour_vs_matched_control(BARS[sym], times, seed=SEED)
            stats.append(result)
            VALUES[f"matched_{kind}_{sym[:3].lower()}"] = {
                k: round(v, 4) for k, v in result.items()
            }
        x = np.arange(len(kinds)) + (i - 0.5) * width
        ax.bar(
            x,
            [s["ratio"] for s in stats],
            width=width,
            color=SYM_COLOR[sym],
            label=sym[:3],
        )
        for xi, s in zip(x, stats, strict=True):
            ax.text(
                xi,
                s["ratio"] + 0.05,
                ("p<0.001" if s["p_value"] < 0.001 else f"p={s['p_value']:.3f}"),
                ha="center",
                fontsize=7.5,
            )
    ax.axhline(1.0, color=BAD, lw=0.9, ls="--")
    ax.set_xticks(np.arange(len(kinds)))
    ax.set_xticklabels(["CPI release", "FOMC decision"])
    ax.set_ylabel("event-bar |return| / matched control")
    ax.set_title(
        "Event-hour volatility vs same-UTC-hour non-event bars · permutation p-values",
        fontsize=9,
    )
    ax.legend(fontsize=8)
    fig.tight_layout()
    return save(fig, "fig_a4_matched_control")


def main() -> int:
    for fn in (fig_a1, fig_a2, fig_a3, fig_a4):
        print(fn())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "values_altdata.json").write_text(
        json.dumps(VALUES, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(OUT / "values_altdata.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
