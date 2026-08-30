"""Definitive thesis figures 3.2 (partitions & access) and 3.4 (walk-forward).

Run with: ``uv run python scripts/build_ch3_validation_figures.py``

Source of truth
---------------
* Fold boundaries: ``folds.json`` of the canonical clean-rebaseline run
  ``artifacts/runs/search_momentum_20260809T212311Z_957b96`` (git commit
  aac33577, 15 folds, purge_bars=96, embargo_bars=118 recorded per fold).
* Cross-check: the same geometry regenerated live with
  ``perp_lab.validation.walk_forward.generate_walk_forward`` on the frozen
  ``configs/experiment.yaml``; the script ASSERTS both agree and fails loudly
  otherwise. No new searches, fits or backtests are executed.
* Holdout state: governance metadata only —
  ``docs/methodology/holdout_audit_status.md`` and
  ``reports/tables/closure/t08_holdout_locks``; no held-out prices or
  results are read.

Exact splitter semantics drawn (verified against both artifact and code):
the EMBARGO (118 bars) removes the tail of the nominal TRAINING window at the
train->validation boundary, and the PURGE (96 bars) removes the tail of the
nominal VALIDATION window at the validation->test boundary. They are not two
gaps around the test window. The meta-labeling layer's span-overlap purge
(``labeling.triple_barrier.purged_embargoed_mask``) is a separate mechanism
and is annotated as such, not drawn as part of this mask.

Outputs (reports/figures/thesis_ch3/): PNG at 300 dpi + SVG for both figures,
``fold_boundaries.csv`` + ``exclusion_counts.json`` with the numbers used, and
``SOURCES_fig_3_2_3_4.md`` recording provenance.
"""

# typographic characters are intentional in figure text

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch

from perp_lab.config import load_experiment_config
from perp_lab.validation.walk_forward import generate_walk_forward

CANONICAL_RUN = Path("artifacts/runs/search_momentum_20260809T212311Z_957b96")
OUT = Path("reports/figures/thesis_ch3")

DEV_START = datetime.fromisoformat("2020-01-01T00:00:00+00:00")
DEV_END = datetime.fromisoformat("2026-01-01T00:00:00+00:00")
HOLDOUT_END = datetime.fromisoformat("2026-07-01T00:00:00+00:00")
BAR = timedelta(hours=1)

plt.rcParams.update(
    {
        "figure.dpi": 110,
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "svg.fonttype": "none",
    }
)

TRAIN_C = "#9ca3af"  # grey
VAL_C = "#1d4ed8"  # blue
TEST_C = "#15803d"  # green
EMBARGO_C = "#b91c1c"  # red hatch
PURGE_C = "#b45309"  # amber hatch
GREY = "#6b7280"
BAD = "#b91c1c"
AMBER = "#b45309"


def save(fig: plt.Figure, name: str) -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return f"{OUT / name}.png|.svg"


# Load the artifact folds and cross-check against the live splitter
def load_folds() -> list[dict]:
    data = json.loads((CANONICAL_RUN / "folds.json").read_text(encoding="utf-8"))
    folds = data["folds"]
    if len(folds) != 15:
        raise AssertionError(f"Expected 15 folds in the artifact, found {len(folds)}.")
    for f in folds:
        if f["purge_bars"] != 96 or f["embargo_bars"] != 118:
            raise AssertionError(f"Fold {f['index']} guard bars differ: {f}")

    live = generate_walk_forward(load_experiment_config())
    if len(live) != len(folds):
        raise AssertionError(f"Live splitter yields {len(live)} folds vs artifact {len(folds)}.")
    for f, lf in zip(folds, live, strict=True):
        for key, attr in (
            ("train_start", "train_start"),
            ("train_end", "train_end"),
            ("val_start", "val_start"),
            ("val_end", "val_end"),
            ("test_start", "test_start"),
            ("test_end", "test_end"),
        ):
            artifact_dt = datetime.fromisoformat(f[key])
            live_dt = getattr(lf, attr)
            if artifact_dt != live_dt:
                raise AssertionError(
                    f"Fold {f['index']} {key}: artifact {artifact_dt} != splitter {live_dt}"
                )
    return folds


def parse(f: dict) -> dict:
    out = {
        k: datetime.fromisoformat(f[k])
        for k in ("train_start", "train_end", "val_start", "val_end", "test_start", "test_end")
    }
    out["index"] = f["index"]
    return out


# Figure 3.4 — expanding walk-forward with the real exclusions
def fig_3_4(folds: list[dict]) -> str:
    parsed = [parse(f) for f in folds]
    fig = plt.figure(figsize=(6.6, 7.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[2.0, 1.0])
    ax_a = fig.add_subplot(gs[0, :])
    ax_b1 = fig.add_subplot(gs[1, 0])
    ax_b2 = fig.add_subplot(gs[1, 1], sharey=ax_b1)

    # ---- Panel A: the 15 folds -------------------------------------------- #
    h = 0.62
    for p_ in parsed:
        y = p_["index"]
        ax_a.barh(
            y,
            (p_["train_end"] - p_["train_start"]).total_seconds() / 86400,
            left=p_["train_start"],
            height=h,
            color=TRAIN_C,
            lw=0,
        )
        ax_a.barh(
            y,
            (p_["val_start"] - p_["train_end"]).total_seconds() / 86400,
            left=p_["train_end"],
            height=h,
            facecolor="white",
            edgecolor=EMBARGO_C,
            hatch="//////",
            lw=0.0,
        )
        ax_a.barh(
            y,
            (p_["val_end"] - p_["val_start"]).total_seconds() / 86400,
            left=p_["val_start"],
            height=h,
            color=VAL_C,
            lw=0,
        )
        ax_a.barh(
            y,
            (p_["test_start"] - p_["val_end"]).total_seconds() / 86400,
            left=p_["val_end"],
            height=h,
            facecolor="white",
            edgecolor=PURGE_C,
            hatch="xxxxxx",
            lw=0.0,
        )
        ax_a.barh(
            y,
            (p_["test_end"] - p_["test_start"]).total_seconds() / 86400,
            left=p_["test_start"],
            height=h,
            color=TEST_C,
            lw=0,
        )

    ax_a.axvline(DEV_END, color=BAD, lw=1.0, ls="--")
    ax_a.text(DEV_END, 13.4, " development\n end\n 2026-01-01", fontsize=6.6, color=BAD, va="top")
    ax_a.set_ylim(-0.7, 15.2)
    ax_a.set_yticks(range(15))
    ax_a.set_yticklabels([f"fold {i}" for i in range(15)], fontsize=7)
    ax_a.invert_yaxis()
    ax_a.xaxis.set_major_locator(mdates.YearLocator())
    ax_a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax_a.set_xlim(
        DEV_START - timedelta(days=30), datetime.fromisoformat("2026-03-01T00:00:00+00:00")
    )
    ax_a.tick_params(labelsize=8)
    ax_a.set_title(
        "A · The 15 expanding folds (anchored training, non-overlapping tests)",
        fontsize=9,
        loc="left",
    )

    legend_items = [
        Patch(facecolor=TRAIN_C, label="training (used)"),
        Patch(
            facecolor="white",
            edgecolor=EMBARGO_C,
            hatch="//////",
            label="embargo: 118 bars off the training tail",
        ),
        Patch(facecolor=VAL_C, label="validation (candidate ranking)"),
        Patch(
            facecolor="white",
            edgecolor=PURGE_C,
            hatch="xxxxxx",
            label="purge: 96 bars off the validation tail",
        ),
        Patch(facecolor=TEST_C, label="out-of-sample test (touched once)"),
    ]
    ax_a.legend(
        handles=legend_items,
        fontsize=6.6,
        loc="upper right",
        bbox_to_anchor=(0.995, 0.995),
        borderaxespad=0.2,
    )

    # ---- Panel B: fold 7, both boundaries at bar resolution --------------- #
    p7 = parsed[7]

    def draw_boundary(ax, lo, hi, title):
        spans = (
            (p7["train_start"], p7["train_end"], {"color": TRAIN_C, "alpha": 0.55, "lw": 0}),
            (
                p7["train_end"],
                p7["val_start"],
                {"facecolor": "white", "edgecolor": EMBARGO_C, "hatch": "//////", "lw": 0},
            ),
            (p7["val_start"], p7["val_end"], {"color": VAL_C, "alpha": 0.45, "lw": 0}),
            (
                p7["val_end"],
                p7["test_start"],
                {"facecolor": "white", "edgecolor": PURGE_C, "hatch": "xxxxxx", "lw": 0},
            ),
            (p7["test_start"], p7["test_end"], {"color": TEST_C, "alpha": 0.45, "lw": 0}),
        )
        for a, b, kw in spans:
            if b > lo and a < hi:
                ax.axvspan(max(a, lo), min(b, hi), **kw)
        ax.set_xlim(lo, hi)
        ax.set_ylim(0, 1)
        ax.set_yticks([])
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.tick_params(labelsize=6.6)
        ax.set_title(title, fontsize=8, loc="left")

    lo1 = p7["train_end"] - timedelta(days=3)
    hi1 = p7["val_start"] + timedelta(days=6)
    draw_boundary(ax_b1, lo1, hi1, "B1 · train -> validation (fold 7)")
    ticks = [p7["train_end"] + i * BAR for i in range(0, 118, 2)]
    ax_b1.vlines(ticks, 0.04, 0.12, color=EMBARGO_C, lw=0.5)
    ax_b1.annotate(
        "last training bar\n" + p7["train_end"].strftime("%m-%d %H:%M"),
        xy=(p7["train_end"], 0.55),
        xytext=(lo1 + timedelta(hours=8), 0.80),
        fontsize=6.4,
        ha="left",
        arrowprops={"arrowstyle": "->", "lw": 0.7, "color": GREY},
    )
    ax_b1.text(
        p7["train_end"] + timedelta(hours=59),
        0.34,
        "embargo\n118 bars (4.9 d)\nexcluded from\ntraining",
        ha="center",
        fontsize=6.6,
        color=EMBARGO_C,
        bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "none", "pad": 1.6},
    )
    ax_b1.annotate(
        "validation begins\n" + p7["val_start"].strftime("%m-%d %H:%M"),
        xy=(p7["val_start"], 0.55),
        xytext=(p7["val_start"] + timedelta(days=1.0), 0.80),
        fontsize=6.4,
        ha="left",
        arrowprops={"arrowstyle": "->", "lw": 0.7, "color": GREY},
    )

    lo2 = p7["val_end"] - timedelta(days=3)
    hi2 = p7["test_start"] + timedelta(days=6)
    draw_boundary(ax_b2, lo2, hi2, "B2 · validation -> test (fold 7)")
    ticks = [p7["val_end"] + i * BAR for i in range(0, 96, 2)]
    ax_b2.vlines(ticks, 0.04, 0.12, color=PURGE_C, lw=0.5)
    ax_b2.annotate(
        "last validation bar\n" + p7["val_end"].strftime("%m-%d %H:%M"),
        xy=(p7["val_end"], 0.55),
        xytext=(lo2 + timedelta(hours=6), 0.80),
        fontsize=6.4,
        ha="left",
        arrowprops={"arrowstyle": "->", "lw": 0.7, "color": GREY},
    )
    ax_b2.text(
        p7["val_end"] + timedelta(hours=48),
        0.34,
        "purge\n96 bars (4 d)\nexcluded from\nvalidation",
        ha="center",
        fontsize=6.6,
        color=PURGE_C,
        bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "none", "pad": 1.6},
    )
    ax_b2.annotate(
        "test begins\n" + p7["test_start"].strftime("%m-%d %H:%M"),
        xy=(p7["test_start"], 0.55),
        xytext=(p7["test_start"] + timedelta(days=1.0), 0.80),
        fontsize=6.4,
        ha="left",
        arrowprops={"arrowstyle": "->", "lw": 0.7, "color": GREY},
    )

    fig.text(
        0.01,
        -0.015,
        "B · Hourly-bar resolution; every 2nd excluded bar is marked. Guards trim the END of the "
        "earlier window: purge = max(label horizon, max holding) = 96 bars;\n"
        "embargo = purge + 1% of the 2,160-bar test span = 118 bars. The meta-labeling layer "
        "applies a separate span-overlap purge on triple-barrier label intervals (not this mask).",
        fontsize=6.4,
        color=GREY,
        va="top",
    )
    return save(fig, "fig_3_4_walk_forward")


# Figure 3.2 — data partitions and access rules (governance metadata only)
def fig_3_2(folds: list[dict]) -> str:
    fig = plt.figure(figsize=(6.6, 6.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 1, height_ratios=[0.85, 1.55])
    ax_t = fig.add_subplot(gs[0])
    ax_r = fig.add_subplot(gs[1])

    # ---- Timeline of the two partitions ----------------------------------- #
    ax_t.barh(
        0.62,
        (DEV_END - DEV_START).days,
        left=DEV_START,
        height=0.34,
        color="#0f766e",
        alpha=0.75,
        lw=0,
    )
    ax_t.barh(
        0.62,
        (HOLDOUT_END - DEV_END).days,
        left=DEV_END,
        height=0.34,
        facecolor="white",
        edgecolor=AMBER,
        hatch="////",
        lw=1.0,
    )
    last_test_end = datetime.fromisoformat(folds[-1]["test_end"])
    ax_t.text(
        DEV_START + (DEV_END - DEV_START) / 2,
        0.88,
        "development [2020-01-01, 2026-01-01) UTC\n"
        "52,608 hourly bars per symbol · every activity below",
        ha="center",
        fontsize=7.6,
        color="#0f766e",
    )
    ax_t.text(
        DEV_END + (HOLDOUT_END - DEV_END) / 2,
        0.885,
        "final partition\n[2026-01-01,\n2026-07-01)",
        ha="center",
        fontsize=7.0,
        color=AMBER,
    )
    ax_t.axvline(HOLDOUT_END, color=BAD, lw=1.1)
    ax_t.text(
        HOLDOUT_END,
        0.42,
        " global cutoff 2026-07-01\n (only closed months ingested)",
        fontsize=6.8,
        color=BAD,
        va="top",
    )
    ax_t.annotate(
        "last walk-forward test ends " + last_test_end.strftime("%Y-%m-%d"),
        xy=(last_test_end, 0.45),
        xytext=(datetime(2024, 6, 1), 0.06),
        ha="center",
        fontsize=6.8,
        color=GREY,
        arrowprops={"arrowstyle": "->", "lw": 0.7, "color": GREY},
    )
    ax_t.text(
        DEV_START,
        0.30,
        "development-only, enforced in code (gated loader raises on any leak):\n"
        "EDA · feature selection · strategy search · 15-fold walk-forward · all diagnostics",
        fontsize=7.0,
        color=GREY,
        va="top",
    )
    ax_t.set_ylim(0, 1.05)
    ax_t.set_yticks([])
    ax_t.xaxis.set_major_locator(mdates.YearLocator())
    ax_t.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax_t.set_xlim(DEV_START - timedelta(days=40), HOLDOUT_END + timedelta(days=170))
    ax_t.tick_params(labelsize=8)
    ax_t.set_title("A · The two partitions", fontsize=9, loc="left")

    # ---- Access rules: authorised path vs executed history ---------------- #
    ax_r.set_xlim(0, 10)
    ax_r.set_ylim(0, 10)
    ax_r.axis("off")
    ax_r.set_title(
        "B · Final-partition access: protocol vs executed history", fontsize=9, loc="left"
    )

    def box(x, y, w, hh, text, color, fs=6.9):
        ax_r.add_patch(
            FancyBboxPatch(
                (x, y), w, hh, boxstyle="round,pad=0.09", lw=1.1, edgecolor=color, facecolor="white"
            )
        )
        ax_r.text(x + w / 2, y + hh / 2, text, ha="center", va="center", fontsize=fs)

    def arrow(x1, y1, x2, y2, color=GREY):
        ax_r.add_patch(
            FancyArrowPatch(
                (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=11, color=color, lw=1.0
            )
        )

    ax_r.text(
        2.45,
        9.55,
        "authorised path (protocol)",
        fontsize=8,
        ha="center",
        weight="bold",
        color="#0f766e",
    )
    box(
        0.3,
        7.5,
        4.3,
        1.5,
        "eligibility BEFORE any access:\nfrozen configuration and promotion\n"
        "criteria passed on development\n(all six gates, majority of seeds)",
        "#0f766e",
    )
    box(
        0.3,
        5.3,
        4.3,
        1.5,
        "single-shot opening:\nexplicit token OPEN_FINAL_HOLDOUT ·\n"
        "append-only registry entry (time,\ncode state, candidate, purpose)",
        "#0f766e",
    )
    box(
        0.3,
        3.1,
        4.3,
        1.5,
        "one reading, then closure:\nno retuning, no second attempt —\n"
        "a post-hoc problem becomes a\ndocumented protocol deviation",
        "#0f766e",
    )
    arrow(2.45, 7.5, 2.45, 6.8)
    arrow(2.45, 5.3, 2.45, 4.6)

    ax_r.text(
        7.45,
        9.55,
        "executed history (registry)",
        fontsize=8,
        ha="center",
        weight="bold",
        color=AMBER,
    )
    box(
        5.2,
        7.5,
        4.5,
        1.5,
        "study closed on development:\n0 of 13 families promoted —\n"
        "no candidate met the eligibility\nbar of the authorised path",
        AMBER,
    )
    box(
        5.2,
        5.3,
        4.5,
        1.5,
        "opened ONCE: 2026-08-13T11:13Z\non a pre-declared candidate\n"
        "(volatility_breakout · BTC · 1h · RS),\nrecorded in the access registry",
        AMBER,
    )
    box(
        5.2,
        3.1,
        4.5,
        1.5,
        "current state: HOLDOUT_LOCKED —\nreading exists on disk, WITHHELD,\n"
        "unpublished pending provenance audit;\nthree independent controls block it",
        BAD,
        6.8,
    )
    arrow(7.45, 7.5, 7.45, 6.8)
    arrow(7.45, 5.3, 7.45, 4.6)

    ax_r.text(
        5.0,
        2.3,
        "The partition is CONSUMED: it is not available for any further hypothesis, comparison or\n"
        "confirmation. No promotion and no validated holdout result exist; none is drawn here.",
        ha="center",
        fontsize=7.2,
        color=BAD,
    )
    ax_r.text(
        5.0,
        0.9,
        "Sources: configs/data_contract.yaml · docs/methodology/holdout_audit_status.md ·\n"
        "closure table t08 (holdout locks). Governance metadata only — no held-out prices or results were read.",
        ha="center",
        fontsize=6.6,
        color=GREY,
        style="italic",
    )
    return save(fig, "fig_3_2_partitions_access")


# Sidecar data + sources note
def write_sidecars(folds: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "fold_boundaries.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "index",
                "train_start",
                "train_end",
                "val_start",
                "val_end",
                "test_start",
                "test_end",
                "purge_bars",
                "embargo_bars",
            ],
        )
        writer.writeheader()
        for f in folds:
            writer.writerow({k: f[k] for k in writer.fieldnames})

    p0 = parse(folds[0])
    counts = {
        "n_folds": len(folds),
        "purge_bars_per_fold": 96,
        "embargo_bars_per_fold": 118,
        "embargo_position": "removed from the END of the nominal training window (train->val boundary)",
        "purge_position": "removed from the END of the nominal validation window (val->test boundary)",
        "bars_excluded_total_embargo": 118 * len(folds),
        "bars_excluded_total_purge": 96 * len(folds),
        "fold0_train_end_effective": folds[0]["train_end"],
        "fold0_nominal_train_end": (p0["val_start"]).isoformat(),
        "last_test_end": folds[-1]["test_end"],
        "development_days_never_tested_at_the_end": (
            DEV_END - datetime.fromisoformat(folds[-1]["test_end"])
        ).days,
    }
    (OUT / "exclusion_counts.json").write_text(json.dumps(counts, indent=2), encoding="utf-8")

    git_state = json.loads((CANONICAL_RUN / "git_state.json").read_text(encoding="utf-8"))
    note = f"""# Sources — Figures 3.2 and 3.4 (definitive)

Generated by `scripts/build_ch3_validation_figures.py` (deterministic, no
searches or fits executed).

| Input | Source |
|---|---|
| Fold boundaries (15 folds) | `{CANONICAL_RUN}/folds.json` |
| Producing code version | commit `{git_state.get("commit", "?")[:12]}` (branch `{git_state.get("branch", "?")}`, dirty={git_state.get("dirty")}) — run identity in `run_identity.json` |
| Cross-check | `perp_lab.validation.walk_forward.generate_walk_forward` on frozen `configs/experiment.yaml` — asserted equal to the artifact, fold by fold and boundary by boundary |
| Guard semantics | `generate_folds`: `train_end_eff = train_end_raw - embargo`, `val_end_eff = val_end_raw - purge` (guards trim the END of the earlier window) |
| Guard derivation | `configs/experiment.yaml`: purge = max(label_horizon, max_holding) = 96 bars; embargo = purge + 1% of the 2,160-bar test window -> 118 bars |
| Partitions | `configs/data_contract.yaml` (development / final partition / cutoff) |
| Holdout state | `docs/methodology/holdout_audit_status.md` + closure table t08 — metadata only |

Verified findings recorded while building:

1. The artifact and the live splitter agree exactly on every boundary of all
   15 folds (purge 96 / embargo 118 on each).
2. The guards are NOT two gaps around the test window: the embargo removes the
   last 118 bars of nominal training, the purge the last 96 bars of nominal
   validation. Thesis text describing them generically as "separating" the
   windows is compatible, but any drawing with guards after the test would be
   wrong.
3. The final walk-forward test window ends {folds[-1]["test_end"][:10]}; the last
   {(DEV_END - datetime.fromisoformat(folds[-1]["test_end"])).days} days of the development period are never used as test
   (geometry: a further 90-day step would cross the development end).
4. The meta-labeling layer uses a different exclusion mechanism
   (span-overlap purge over triple-barrier label intervals,
   `perp_lab.labeling.triple_barrier.purged_embargoed_mask`); it is annotated
   in Figure 3.4-B and deliberately not merged into the walk-forward mask.
"""
    (OUT / "SOURCES_fig_3_2_3_4.md").write_text(note, encoding="utf-8")


def main() -> int:
    folds = load_folds()
    print("artifact folds verified against the live splitter: 15/15 boundaries equal")
    print(fig_3_4(folds))
    print(fig_3_2(folds))
    write_sidecars(folds)
    print(OUT / "fold_boundaries.csv")
    print(OUT / "exclusion_counts.json")
    print(OUT / "SOURCES_fig_3_2_3_4.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
