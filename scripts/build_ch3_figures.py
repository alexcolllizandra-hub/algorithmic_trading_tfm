"""Chapter 3 (research design) figures for the thesis.

Run with: ``uv run python scripts/build_ch3_figures.py``

Writes PNG + PDF pairs to ``reports/figures/thesis_ch3/``. Deterministic; no
timestamps. Every number drawn on a figure is verified against the repo:
fold/partition dates from the committed data contract and fold export, pilot
and full-study budgets from docs/roadmap/phase_gates.md, family counts from
the closure artifacts.

fig_3_1_preregistration   the specify -> freeze -> execute -> verdict cycle
fig_3_2_temporal_layout   development window, frozen holdout, global cutoff
fig_3_3_funnel            phases A/B/C with the study's real parameters
"""

from __future__ import annotations

from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from pathlib import Path

OUT = Path("reports/figures/thesis_ch3")

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


def save(fig: plt.Figure, name: str) -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    return f"{OUT / name}.png|.pdf"


def box(ax, x, y, w, h, text, color, fs=9):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.10", linewidth=1.2, edgecolor=color, facecolor="white"
        )
    )
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def arrow(ax, x1, y1, x2, y2, color=GREY, style="-|>", ls="-", label=None, lfs=8):
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=13, color=color, lw=1.2, linestyle=ls
        )
    )
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.22, label, ha="center", fontsize=lfs, color=color)


# --------------------------------------------------------------------------- #
# Fig 3.1 — pre-registration cycle
# --------------------------------------------------------------------------- #
def fig_3_1() -> str:
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")

    box(ax, 0.3, 3.6, 2.6, 1.6, "1 · Specify\nhypothesis document:\nrationale, rules,\nparameter bounds", ACCENT, 8.5)
    box(ax, 3.4, 3.6, 2.6, 1.6, "2 · Freeze\ncommitted to version\ncontrol, dated,\nbefore any backtest", SECOND, 8.5)
    box(ax, 6.5, 3.6, 2.6, 1.6, "3 · Execute\nexactly as specified\n(fold geometry,\nbudget, both engines)", ACCENT, 8.5)
    box(ax, 9.6, 3.6, 2.2, 1.6, "4 · Verdict\npromote /\nreject /\npartial signal", SECOND, 8.5)

    arrow(ax, 2.9, 4.4, 3.4, 4.4)
    arrow(ax, 6.0, 4.4, 6.5, 4.4)
    arrow(ax, 9.1, 4.4, 9.6, 4.4)

    # Forbidden path: result-dependent retuning back into the same hypothesis.
    arrow(ax, 10.6, 3.5, 4.6, 1.9, color=BAD, ls=(0, (4, 3)))
    ax.text(
        7.6,
        2.15,
        'forbidden: retune after results and resubmit\nas the "same" hypothesis',
        ha="center",
        fontsize=8,
        color=BAD,
    )
    # Allowed path: a new registration that increments the trial count.
    box(ax, 3.9, 0.25, 4.4, 1.05, "allowed: register a NEW hypothesis, new freeze\n→ trial count N := N + 1", AMBER, 8.5)
    arrow(ax, 3.9, 0.95, 1.6, 3.5, color=AMBER)
    ax.text(
        1.9,
        1.5,
        "multiplicity corrections\n(Ch. 6) are paid on N",
        fontsize=8,
        color=AMBER,
        ha="center",
    )
    return save(fig, "fig_3_1_preregistration")


# --------------------------------------------------------------------------- #
# Fig 3.2 — temporal layout (real contract dates)
# --------------------------------------------------------------------------- #
def fig_3_2() -> str:
    d = mdates.date2num
    dev_start = d(datetime(2020, 1, 1))
    holdout_start = d(datetime(2026, 1, 1))
    cutoff = d(datetime(2026, 7, 1))

    fig, ax = plt.subplots(figsize=(7.6, 2.7))
    ax.barh(0, holdout_start - dev_start, left=dev_start, height=0.5, color=ACCENT, alpha=0.75)
    ax.barh(
        0,
        cutoff - holdout_start,
        left=holdout_start,
        height=0.5,
        facecolor="none",
        edgecolor=AMBER,
        hatch="////",
        lw=1.2,
    )
    ax.axvline(cutoff, color=BAD, lw=1.4)

    ax.text(
        (dev_start + holdout_start) / 2,
        0.62,
        "Development window · 2020-01-01 → 2025-12-31\nall exploration, search and the 15 walk-forward folds\n52,608 hourly bars per symbol",
        ha="center",
        fontsize=8.5,
        color=ACCENT,
    )
    ax.annotate(
        "Final partition · 2026-01 → 2026-06\nfrozen (Sec. 3.4) · 4,344 hourly bars",
        xy=((holdout_start + cutoff) / 2, -0.26),
        xytext=(d(datetime(2024, 6, 1)), -0.95),
        fontsize=8,
        color=AMBER,
        ha="center",
        arrowprops={"arrowstyle": "->", "color": AMBER, "lw": 0.9},
    )
    ax.text(cutoff, 0.62, " global cutoff\n 2026-07-01", fontsize=8, color=BAD, va="bottom", ha="left")

    ax.set_ylim(-1.15, 1.15)
    ax.set_yticks([])
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_xlim(d(datetime(2019, 9, 1)), d(datetime(2027, 2, 1)))
    ax.set_xlabel("Contract v0.1.0 — configs/data_contract.yaml; bar counts from the dataset manifests")
    return save(fig, "fig_3_2_temporal_layout")


# --------------------------------------------------------------------------- #
# Fig 3.3 — three-phase funnel with the study's real parameters
# --------------------------------------------------------------------------- #
def fig_3_3() -> str:
    fig, ax = plt.subplots(figsize=(7.6, 5.4))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10.6)
    ax.axis("off")

    # Funnel trapezoid guides.
    widths = [11.2, 8.6, 6.0]
    xs = [(12 - w) / 2 for w in widths]
    ys = [8.0, 4.9, 1.8]

    box(
        ax,
        xs[0],
        ys[0],
        widths[0],
        1.9,
        "Phase A — technical validity\n"
        "synthetic smoke run + engine invariant checks + leakage tests\n"
        "produces trades, respects bounds, charges costs · says nothing about profitability",
        GREY,
        8.5,
    )
    box(
        ax,
        xs[1],
        ys[1],
        widths[1],
        1.9,
        "Phase B — development pilot (non-confirmatory)\n"
        "2 assets × 1 seed × 15 folds · 60 evaluations per fold and engine\n"
        "futility check only: pilot Sharpe is never quoted as evidence",
        SECOND,
        8.5,
    )
    box(
        ax,
        xs[2],
        ys[2],
        widths[2],
        1.9,
        "Phase C — full study\n"
        "2 assets × 10 seeds × 15 folds\n"
        "100 evaluations per fold and engine\n+ full statistical battery (Ch. 6)",
        ACCENT,
        8.5,
    )

    arrow(ax, 6, ys[0] - 0.1, 6, ys[1] + 2.0, color=GREY)
    arrow(ax, 6, ys[1] - 0.1, 6, ys[2] + 2.0, color=GREY)
    arrow(ax, 6, ys[2] - 0.1, 6, 0.9, color=GREY)

    box(ax, 3.4, 0.15, 5.2, 0.75, "Promotion: all six frozen criteria (Table 3.2) — study outcome: 0 of 15", BAD, 8.5)

    # Side annotations: real counts and the partial-signal side channel.
    ax.text(
        0.1,
        ys[1] + 0.9,
        "22 families\nimplemented\n& registered",
        fontsize=8,
        color=GREY,
        ha="left",
    )
    ax.text(
        0.1,
        ys[2] + 0.9,
        "15 families\ncompleted the\nfull study\n(R2–R3, S1,\nS2, CRT)",
        fontsize=8,
        color=GREY,
        ha="left",
    )
    ax.annotate(
        "partial signal: recorded and reported, unlocks nothing\n"
        "(volatility_breakout BTC: 6/10 positive seeds, 0/10 bootstrap CIs)",
        xy=(9.0, ys[2] + 1.75),
        xytext=(11.9, 4.25),
        fontsize=7.5,
        color=AMBER,
        ha="right",
        va="center",
        arrowprops={"arrowstyle": "->", "color": AMBER, "lw": 0.9},
    )
    return save(fig, "fig_3_3_funnel")


def main() -> int:
    for fn in (fig_3_1, fig_3_2, fig_3_3):
        print(fn())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
