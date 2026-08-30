"""Volatility-forecasting annex figures (V1-V3) + verdict values.

Run with: ``uv run python scripts/build_volforecast_figures.py``
(requires ``scripts/run_volforecast_experiment.py`` to have completed)

Reads ``artifacts/volforecast/results.json`` and the OOS prediction parquets;
writes PNG+PDF pairs to ``reports/figures/thesis_volforecast/`` with mirror
copies in ``reports/figures/eda/``, plus ``values_volforecast.json`` holding
every number the annex text needs, including the frozen decision rule's
verdict computed here — not asserted by hand.
"""

# typographic characters are intentional in figure text

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

RESULTS = Path("artifacts/volforecast/results.json")
OUT = Path("reports/figures/thesis_volforecast")
EDA_MIRROR = Path("reports/figures/eda")
SYMBOLS = ("BTCUSDT", "ETHUSDT")
SEEDS = (42, 43, 44)

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


def save(fig: plt.Figure, name: str) -> str:
    for out_dir in (OUT, EDA_MIRROR):
        out_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_dir / f"{name}.png", bbox_inches="tight")
        fig.savefig(out_dir / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    return f"{OUT / name}.png|.pdf"


RES = json.loads(RESULTS.read_text(encoding="utf-8"))


# Fig V1 — per-fold QLIKE, HAR vs the three LSTM seeds
def fig_v1() -> str:
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.4), sharey=False)
    for ax, sym in zip(axes, SYMBOLS, strict=True):
        folds = RES[sym]["folds"]
        x = [f["fold"] for f in folds]
        ax.plot(x, [f["har"]["qlike"] for f in folds], "o-", ms=4, lw=1.2, color=AMBER, label="HAR")
        for i, seed in enumerate(SEEDS):
            ax.plot(
                x,
                [f[f"lstm_seed{seed}"]["qlike"] for f in folds],
                "o-",
                ms=2.5,
                lw=0.8,
                alpha=0.8,
                color=SYM_COLOR[sym],
                label=f"LSTM seed {seed}" if i == 0 else None,
            )
        ax.set_title(sym[:3], fontsize=9)
        ax.set_xlabel("walk-forward fold")
        ax.legend(fontsize=7.5)
    axes[0].set_ylabel("QLIKE (test window, lower = better)")
    fig.suptitle("Per-fold QLIKE: HAR benchmark vs LSTM (3 seeds)", fontsize=9)
    fig.tight_layout()
    return save(fig, "fig_v1_per_fold_qlike")


# Fig V2 — a sample OOS window: predicted vs realized log RV
def fig_v2() -> str:
    frame = pl.read_parquet("artifacts/volforecast/oos_predictions_BTCUSDT.parquet").sort(
        "open_time"
    )
    lstm_mean = frame.select(pl.mean_horizontal([f"lstm_seed{s}" for s in SEEDS]).alias("lstm"))[
        "lstm"
    ]
    frame = frame.with_columns(lstm_mean)
    # Sample window: 60 days around the most volatile OOS stretch.
    peak_idx = int(frame["true_log_rv"].arg_max())
    lo = max(0, peak_idx - 720)
    hi = min(frame.height, peak_idx + 720)
    window = frame.slice(lo, hi - lo)

    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    t = window["open_time"].to_list()
    ax.plot(t, window["true_log_rv"].to_list(), color=GREY, lw=1.2, label="realized (next-24h)")
    ax.plot(t, window["naive"].to_list(), color="#9ca3af", lw=0.8, ls=":", label="naive")
    ax.plot(t, window["har"].to_list(), color=AMBER, lw=1.0, label="HAR")
    ax.plot(t, window["lstm"].to_list(), color=ACCENT, lw=1.0, label="LSTM (seed mean)")
    ax.set_ylabel("log RV (next 24h)")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=8, ncol=4)
    start = t[0].strftime("%Y-%m-%d") if isinstance(t[0], datetime) else str(t[0])[:10]
    ax.set_title(
        f"BTC out-of-sample forecasts around the most volatile stretch (from {start})", fontsize=9
    )
    fig.tight_layout()
    return save(fig, "fig_v2_oos_sample")


# Fig V3 — concatenated-OOS summary + the frozen decision rule
def fig_v3() -> str:
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.6))
    models = ["naive", "har", "lstm_mean_of_seeds"]
    labels = ["naive", "HAR", "LSTM"]
    colors = ["#9ca3af", AMBER, ACCENT]

    width = 0.35
    for i, sym in enumerate(SYMBOLS):
        qlikes = [RES[sym][m]["qlike"] for m in models]
        r2s = [RES[sym][m]["r2_oos_vs_naive"] for m in models]
        x = np.arange(3) + (i - 0.5) * width
        axes[0].bar(x, qlikes, width=width, color=colors, alpha=1.0 if i == 0 else 0.55)
        axes[1].bar(x, r2s, width=width, color=colors, alpha=1.0 if i == 0 else 0.55)
        dm = RES[sym]["dm_har_vs_lstm_mean"]
        axes[0].text(
            1.5 + (i - 0.5) * width,
            max(qlikes) * 1.04,
            f"{sym[:3]}: DM p={dm['p_value']:.3f}",
            ha="center",
            fontsize=7.5,
        )
    for ax, title in zip(
        axes, ("QLIKE (lower = better)", "R² OOS vs naive (higher = better)"), strict=True
    ):
        ax.set_xticks(np.arange(3))
        ax.set_xticklabels(labels)
        ax.set_title(title, fontsize=9)
    axes[1].axhline(0, color=BAD, lw=0.8, ls="--")
    fig.suptitle(
        "Concatenated OOS (15 folds) · solid = BTC, faded = ETH · DM: HAR vs LSTM(seed-mean)",
        fontsize=9,
    )
    fig.tight_layout()
    return save(fig, "fig_v3_summary")


def compute_verdict() -> None:
    """Apply the frozen decision rule mechanically and store every input."""
    per_symbol = {}
    lstm_beats_qlike_both = True
    dm_rejects_any = False
    for sym in SYMBOLS:
        har_q = RES[sym]["har"]["qlike"]
        lstm_q = RES[sym]["lstm_mean_of_seeds"]["qlike"]
        dm = RES[sym]["dm_har_vs_lstm_mean"]
        beats = lstm_q < har_q
        # dm_stat > 0 means model B (LSTM) has lower squared-error loss.
        rejects_for_lstm = dm["p_value"] < 0.05 and dm["dm_stat"] > 0
        lstm_beats_qlike_both &= beats
        dm_rejects_any |= rejects_for_lstm
        per_symbol[sym] = {
            "har_qlike": round(har_q, 4),
            "lstm_qlike": round(lstm_q, 4),
            "lstm_beats_har_qlike": beats,
            "dm_stat": round(dm["dm_stat"], 3),
            "dm_p": round(dm["p_value"], 4),
            "dm_rejects_for_lstm": rejects_for_lstm,
            "har_r2_vs_naive": round(RES[sym]["har"]["r2_oos_vs_naive"], 4),
            "lstm_r2_vs_naive": round(RES[sym]["lstm_mean_of_seeds"]["r2_oos_vs_naive"], 4),
            "lstm_qlike_per_seed": {
                s: round(RES[sym]["lstm_per_seed"][s]["qlike"], 4)
                for s in RES[sym]["lstm_per_seed"]
            },
            "n_oos": RES[sym]["n_oos"],
        }
    VALUES["per_symbol"] = per_symbol
    VALUES["rule_lstm_beats_qlike_both_symbols"] = lstm_beats_qlike_both
    VALUES["rule_dm_rejects_for_lstm_any_symbol"] = dm_rejects_any
    VALUES["verdict_lstm_adds_value"] = bool(lstm_beats_qlike_both and dm_rejects_any)


def main() -> int:
    for fn in (fig_v1, fig_v2, fig_v3):
        print(fn())
    compute_verdict()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "values_volforecast.json").write_text(
        json.dumps(VALUES, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(OUT / "values_volforecast.json")
    print("VERDICT lstm_adds_value =", VALUES["verdict_lstm_adds_value"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
