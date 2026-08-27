"""Chapter 2 (state of the art) figures for the thesis.

Run with: ``uv run python scripts/build_ch2_figures.py``

Writes PNG + PDF pairs to ``reports/figures/thesis_ch2/``. Deterministic:
fixed seed, fixed data segments, no timestamps in the output. Real-data
figures (2.2, 2.4, 2.6) read only the development partition; diagram figures
(2.1, 2.3, 2.5) are schematic and labelled as such, except 2.3's walk-forward
panel, which draws the study's real fold dates from the committed run.

Figures
-------
fig_2_1_funding_mechanism      diagram: how funding anchors perp to spot
fig_2_2_funding_rates          real BTC/ETH funding series + marginals
fig_2_3_validation_geometries  walk-forward (real folds) vs naive/purged K-fold
fig_2_4_triple_barrier         real BTCUSDT 5m segment with the three barriers
fig_2_5_meta_labeling          architecture diagram (primary -> meta)
fig_2_6_data_snooping          max Sharpe of N random strategies vs theory
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path("reports/figures/thesis_ch2")
SEED = 42
HOLDOUT_START = datetime(2026, 1, 1, tzinfo=UTC)
FOLDS_RUN = Path("artifacts/runs/search_volatility_breakout_20260810T165249Z_2b3547")

plt.rcParams.update(
    {
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
    }
)

ACCENT = "#0f766e"  # teal, prints as a solid mid grey
SECOND = "#1d4ed8"  # blue
BAD = "#b91c1c"  # red
GREY = "#6b7280"


def save(fig: plt.Figure, name: str) -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    return f"{OUT / name}.png|.pdf"


# --------------------------------------------------------------------------- #
# Fig 2.1 — funding mechanism (schematic)
# --------------------------------------------------------------------------- #
def fig_2_1() -> str:
    rng = np.random.default_rng(SEED)
    t = np.linspace(0, 6, 400)
    spot = 100 + np.cumsum(rng.normal(0, 0.25, t.size))
    gap = 1.6 * np.sin(t * 1.05) + 0.4 * np.sin(t * 3.1)
    perp = spot + gap

    fig, (ax, ax2) = plt.subplots(
        2, 1, figsize=(7.2, 4.2), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]}
    )
    ax.plot(t, spot, color=GREY, lw=1.4, label="Spot index")
    ax.plot(t, perp, color=ACCENT, lw=1.4, label="Perpetual price")
    ax.fill_between(t, spot, perp, where=perp > spot, color=BAD, alpha=0.12)
    ax.fill_between(t, spot, perp, where=perp < spot, color=SECOND, alpha=0.12)
    ax.annotate(
        "perp > spot:\nlongs pay shorts",
        xy=(1.15, float(np.interp(1.15, t, (spot + perp) / 2))),
        xytext=(0.4, float(perp.max()) + 1.2),
        fontsize=8,
        color=BAD,
        arrowprops={"arrowstyle": "->", "color": BAD, "lw": 0.9},
    )
    ax.annotate(
        "perp < spot:\nshorts pay longs",
        xy=(4.2, float(np.interp(4.2, t, (spot + perp) / 2))),
        xytext=(4.9, float(spot.min()) - 1.6),
        fontsize=8,
        color=SECOND,
        arrowprops={"arrowstyle": "->", "color": SECOND, "lw": 0.9},
    )
    ax.set_ylabel("Price")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_title(
        "Illustrative diagram (synthetic path, not market data)",
        fontsize=8,
        loc="right",
        color=GREY,
    )

    funding = np.clip(gap / 8, -0.4, 0.4)
    ax2.axhline(0, color=GREY, lw=0.8)
    ax2.fill_between(t, 0, funding, where=funding > 0, color=BAD, alpha=0.5, step="mid")
    ax2.fill_between(t, 0, funding, where=funding < 0, color=SECOND, alpha=0.5, step="mid")
    # 8-hour settlement ticks.
    for x in np.linspace(0.4, 5.8, 8):
        ax2.axvline(x, color=GREY, lw=0.5, ls=":", alpha=0.6)
    ax2.set_ylabel("Funding rate")
    ax2.set_xlabel("Time (funding settles at fixed 8-hour marks, dotted)")
    ax2.set_yticks([])
    fig.align_ylabels()
    return save(fig, "fig_2_1_funding_mechanism")


# --------------------------------------------------------------------------- #
# Fig 2.2 — real funding rates with marginal distributions
# --------------------------------------------------------------------------- #
def fig_2_2() -> str:
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(7.6, 4.6),
        sharey="row",
        gridspec_kw={"width_ratios": [3.2, 1], "wspace": 0.04, "hspace": 0.32},
    )
    for row, (symbol, color) in enumerate([("BTCUSDT", ACCENT), ("ETHUSDT", SECOND)]):
        f = (
            pl.read_parquet(f"data/validated/{symbol}/fundingRate.parquet")
            .filter(pl.col("funding_time") < HOLDOUT_START)
            .sort("funding_time")
        )
        times = f["funding_time"].to_list()
        rate = f["funding_rate"].to_numpy() * 100  # percent per 8h
        ann = float(rate.mean() / 100 * 3 * 365 * 100)

        ax = axes[row][0]
        ax.plot(times, rate, color=color, lw=0.35, alpha=0.8)
        ax.axhline(0, color=GREY, lw=0.7)
        ax.axhline(0.01, color=GREY, lw=0.7, ls="--")
        ax.annotate(
            "baseline 0.01% / 8h",
            xy=(times[-1], 0.01),
            xytext=(-4, 0),
            textcoords="offset points",
            fontsize=7,
            color=GREY,
            ha="right",
            va="bottom",
        )
        ax.set_ylabel(f"{symbol.replace('USDT', '')} funding (% / 8h)")
        ax.set_title(
            f"mean {rate.mean():.4f}% per 8h  ≈  {ann:+.1f}% annualised against longs",
            fontsize=8,
            loc="left",
        )
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

        axh = axes[row][1]
        bins = np.linspace(np.percentile(rate, 0.2), np.percentile(rate, 99.8), 80)
        axh.hist(rate, bins=bins, orientation="horizontal", color=color, alpha=0.75)
        axh.axhline(0, color=GREY, lw=0.7)
        axh.set_xscale("log")
        axh.set_xlabel("count (log)", fontsize=7)
        axh.tick_params(labelleft=False)
    axes[1][0].set_xlabel("Development partition (2020-01 … 2025-12); holdout excluded")
    return save(fig, "fig_2_2_funding_rates")


# --------------------------------------------------------------------------- #
# Fig 2.3 — validation geometries (walk-forward panel uses real fold dates)
# --------------------------------------------------------------------------- #
def fig_2_3() -> str:
    meta = json.loads((FOLDS_RUN / "folds.json").read_text(encoding="utf-8"))
    folds = meta["folds"]

    def ts(s: str) -> float:
        return mdates.date2num(datetime.fromisoformat(s))

    fig, axes = plt.subplots(3, 1, figsize=(7.6, 6.2), sharex=False)

    # Panel A: the study's real expanding walk-forward.
    ax = axes[0]
    for k, f in enumerate(folds):
        y = len(folds) - 1 - k
        ax.barh(
            y,
            ts(f["train_end"]) - ts(f["train_start"]),
            left=ts(f["train_start"]),
            height=0.72,
            color=GREY,
            alpha=0.35,
        )
        ax.barh(
            y,
            ts(f["val_end"]) - ts(f["val_start"]),
            left=ts(f["val_start"]),
            height=0.72,
            color=SECOND,
            alpha=0.75,
        )
        ax.barh(
            y,
            ts(f["test_end"]) - ts(f["test_start"]),
            left=ts(f["test_start"]),
            height=0.72,
            color=ACCENT,
            alpha=0.9,
        )
        # purge gaps (train->val and val->test) as hatched bands
        ax.barh(
            y,
            ts(f["val_start"]) - ts(f["train_end"]),
            left=ts(f["train_end"]),
            height=0.72,
            color="none",
            edgecolor=BAD,
            hatch="////",
            lw=0,
        )
        ax.barh(
            y,
            ts(f["test_start"]) - ts(f["val_end"]),
            left=ts(f["val_end"]),
            height=0.72,
            color="none",
            edgecolor=BAD,
            hatch="////",
            lw=0,
        )
    ax.set_yticks([len(folds) - 1, 0], ["fold 0", f"fold {len(folds) - 1}"])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_title(
        "A — Expanding walk-forward: the study's real 15 folds "
        f"(purge {folds[0]['purge_bars']} bars, embargo {folds[0]['embargo_bars']} bars, hatched)",
        fontsize=9,
        loc="left",
    )
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=GREY, alpha=0.35),
        plt.Rectangle((0, 0), 1, 1, color=SECOND, alpha=0.75),
        plt.Rectangle((0, 0), 1, 1, color=ACCENT, alpha=0.9),
        plt.Rectangle((0, 0), 1, 1, facecolor="none", edgecolor=BAD, hatch="////"),
    ]
    ax.legend(
        handles,
        ["train", "validation", "test", "purge/embargo"],
        loc="lower left",
        bbox_to_anchor=(0.0, 1.08),
        fontsize=7,
        ncols=4,
    )

    # Panel B: naive K-fold on the same span (schematic).
    ax = axes[1]
    K = 5
    for k in range(K):
        y = K - 1 - k
        for j in range(K):
            color = ACCENT if j == k else GREY
            alpha = 0.9 if j == k else 0.35
            ax.barh(y, 1, left=j, height=0.72, color=color, alpha=alpha)
    ax.set_yticks([K - 1, 0], ["fold 0", f"fold {K - 1}"])
    ax.set_xticks([])
    ax.set_title(
        "B — Naive K-fold (schematic): test blocks (solid) sit between training data drawn from their own future",
        fontsize=9,
        loc="left",
    )

    # Panel C: purged K-fold with embargo (schematic).
    ax = axes[2]
    purge = 0.12
    embargo = 0.18
    for k in range(K):
        y = K - 1 - k
        for j in range(K):
            left = float(j)
            if j == k:
                ax.barh(y, 1, left=left, height=0.72, color=ACCENT, alpha=0.9)
            else:
                ax.barh(y, 1, left=left, height=0.72, color=GREY, alpha=0.35)
        if k > 0:
            ax.barh(
                y,
                purge,
                left=k - purge,
                height=0.72,
                color="none",
                edgecolor=BAD,
                hatch="////",
                lw=0,
            )
        if k < K - 1:
            ax.barh(
                y,
                purge + embargo,
                left=k + 1,
                height=0.72,
                color="none",
                edgecolor=BAD,
                hatch="////",
                lw=0,
            )
    ax.set_yticks([K - 1, 0], ["fold 0", f"fold {K - 1}"])
    ax.set_xticks([])
    ax.set_title(
        "C — Purged K-fold with embargo (schematic): hatched observations are removed around every test block",
        fontsize=9,
        loc="left",
    )
    fig.tight_layout()
    return save(fig, "fig_2_3_validation_geometries")


# --------------------------------------------------------------------------- #
# Fig 2.4 — triple barrier on a real BTCUSDT 5m segment
# --------------------------------------------------------------------------- #
def fig_2_4() -> str:
    bars = (
        pl.read_parquet("data/validated/BTCUSDT/5m.parquet")
        .filter(
            (pl.col("open_time") >= datetime(2024, 3, 4, 0, 0, tzinfo=UTC))
            & (pl.col("open_time") < datetime(2024, 3, 6, 0, 0, tzinfo=UTC))
        )
        .sort("open_time")
    )
    close = bars["close"].to_numpy()
    times = bars["open_time"].to_list()

    # Entry at a fixed offset; barrier width from the trailing 24h (288-bar)
    # std of 5m returns — the same volatility-scaled construction the
    # meta-labeling module uses.
    entry_idx = 288
    rets = np.diff(np.log(close[: entry_idx + 1]))
    sigma = float(np.std(rets[-288:], ddof=1))
    width = 12 * sigma  # k=12 five-minute sigmas ≈ an intraday move
    entry = close[entry_idx]
    upper = entry * (1 + width)
    lower = entry * (1 - width)
    vertical = entry_idx + 288  # 24h vertical barrier

    # First touch.
    touch_idx, touch_kind = vertical, "vertical"
    for i in range(entry_idx + 1, min(vertical + 1, close.size)):
        if close[i] >= upper:
            touch_idx, touch_kind = i, "profit-taking"
            break
        if close[i] <= lower:
            touch_idx, touch_kind = i, "stop-loss"
            break

    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    ax.plot(times, close, color=GREY, lw=0.9)
    ax.plot(
        times[entry_idx : touch_idx + 1], close[entry_idx : touch_idx + 1], color=ACCENT, lw=1.4
    )
    ax.hlines(
        [upper],
        times[entry_idx],
        times[min(vertical, len(times) - 1)],
        color=ACCENT,
        ls="--",
        lw=1.1,
    )
    ax.hlines(
        [lower], times[entry_idx], times[min(vertical, len(times) - 1)], color=BAD, ls="--", lw=1.1
    )
    ax.axvline(times[min(vertical, len(times) - 1)], color=SECOND, ls=":", lw=1.2)
    ax.scatter([times[entry_idx]], [entry], color="black", zorder=5, s=22, label="entry")
    ax.scatter(
        [times[touch_idx]],
        [close[touch_idx]],
        color=ACCENT
        if touch_kind == "profit-taking"
        else BAD
        if touch_kind == "stop-loss"
        else SECOND,
        zorder=5,
        s=34,
        marker="X",
        label=f"first touch: {touch_kind}",
    )
    ax.text(
        times[entry_idx], upper, " profit-taking barrier", fontsize=8, color=ACCENT, va="bottom"
    )
    ax.text(times[entry_idx], lower, " stop-loss barrier", fontsize=8, color=BAD, va="top")
    ax.text(
        times[min(vertical, len(times) - 1)],
        entry,
        " vertical barrier (24 h)",
        fontsize=8,
        color=SECOND,
        rotation=90,
        va="center",
        ha="right",
    )
    ax.set_ylabel("BTCUSDT close (5m)")
    ax.set_xlabel("2024-03-04 … 2024-03-05 UTC — real 5-minute bars, development partition")
    ax.legend(loc="upper left", fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %Hh"))
    return save(fig, "fig_2_4_triple_barrier")


# --------------------------------------------------------------------------- #
# Fig 2.5 — meta-labeling architecture (diagram)
# --------------------------------------------------------------------------- #
def fig_2_5() -> str:
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")

    def box(x, y, w, h, text, color, fs=8.5):
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.08",
                linewidth=1.1,
                edgecolor=color,
                facecolor="white",
            )
        )
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color="black")

    def arrow(x1, y1, x2, y2, label=None, color=GREY):
        ax.add_patch(
            FancyArrowPatch(
                (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12, color=color, lw=1.1
            )
        )
        if label:
            ax.text(
                (x1 + x2) / 2, (y1 + y2) / 2 + 0.16, label, ha="center", fontsize=7.5, color=color
            )

    box(0.2, 3.3, 2.1, 1.2, "Market data\n(OHLCV, funding)", GREY)
    box(
        3.2, 3.3, 2.6, 1.2, "Primary strategy\ninterpretable rule\n→ direction (long/short)", ACCENT
    )
    box(3.2, 0.4, 2.6, 1.5, "Triple-barrier labels\non net returns\n(PT / SL / vertical)", SECOND)
    box(
        6.8, 3.3, 2.9, 1.2, "Secondary classifier\nLR / RF / LightGBM\n→ participate? size?", SECOND
    )
    box(
        6.8,
        0.55,
        2.9,
        1.2,
        "Execution\nonly trades the classifier\naccepts; abstains otherwise",
        ACCENT,
    )

    arrow(2.3, 3.9, 3.2, 3.9)
    arrow(1.2, 3.3, 3.1, 1.2, label="features", color=GREY)
    arrow(4.5, 3.3, 4.5, 1.9, label="candidate events", color=ACCENT)
    arrow(5.8, 1.5, 7.2, 3.3, label="labels (training)", color=SECOND)
    arrow(5.8, 3.9, 6.8, 3.9, label="direction", color=ACCENT)
    arrow(8.25, 3.3, 8.25, 1.75, label="participate / abstain", color=SECOND)
    ax.set_title(
        "Meta-labeling: direction and participation are decided by different models "
        "(diagram; the study's real instantiation is notebook 06)",
        fontsize=8.5,
        loc="left",
    )
    return save(fig, "fig_2_5_meta_labeling")


# --------------------------------------------------------------------------- #
# Fig 2.6 — data snooping: max Sharpe of N random strategies vs theory
# --------------------------------------------------------------------------- #
def fig_2_6() -> str:
    bars = pl.read_parquet("data/processed/BTCUSDT/1h_development.parquet").sort("open_time")
    close = bars["close"].to_numpy()
    rets = np.diff(close) / close[:-1]
    n = rets.size
    bpy = 8760.0

    rng = np.random.default_rng(SEED)
    n_strats = 10_000
    # Random ±1 position per bar on the real return stream: pure noise
    # strategies with realistic return texture and zero expected edge.
    sharpes = np.empty(n_strats)
    for i in range(n_strats):
        signs = rng.choice(np.array([-1.0, 1.0]), size=n)
        r = signs * rets
        mean = r.mean()
        std = r.std(ddof=1)
        sharpes[i] = (mean / std) * np.sqrt(bpy) if std > 0 else 0.0

    running_max = np.maximum.accumulate(sharpes)
    N = np.arange(1, n_strats + 1)
    theory = np.sqrt(2 * np.log(np.maximum(N, 2)) / n) * np.sqrt(bpy)

    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.plot(
        N, running_max, color=ACCENT, lw=1.4, label="observed max Sharpe among N random strategies"
    )
    ax.plot(
        N,
        theory,
        color=GREY,
        lw=1.2,
        ls="--",
        label=r"theoretical $E[\max] \approx \sqrt{2\ln N\,/\,T}$ (annualised)",
    )
    ax.set_xscale("log")
    ax.set_xlabel("N — number of no-edge strategies tried (log scale)")
    ax.set_ylabel("Best annualised Sharpe found")
    ax.axhline(1.0, color=BAD, lw=0.9, ls=":")
    ax.text(
        1.3,
        1.02,
        'Sharpe 1.0 — a level often marketed as "good"',
        fontsize=7.5,
        color=BAD,
        va="bottom",
    )
    ax.legend(loc="lower right", fontsize=8)
    ax.set_title(
        f"Real BTCUSDT 1h development returns (n={n:,} bars), random ±1 positions, seed {SEED}",
        fontsize=8,
        loc="left",
    )
    return save(fig, "fig_2_6_data_snooping")


def main() -> int:
    for fn in (fig_2_1, fig_2_2, fig_2_3, fig_2_4, fig_2_5, fig_2_6):
        print(fn())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
