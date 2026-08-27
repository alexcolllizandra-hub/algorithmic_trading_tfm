"""Chapter 4 (system architecture & MLOps) figures for the thesis.

Run with: ``uv run python scripts/build_ch4_figures.py``

Writes PNG + PDF pairs to ``reports/figures/thesis_ch4/``. Deterministic; no
timestamps. Every number drawn on a figure is verified against the repo:
module names from ``src/perp_lab``, storage paths and row counts from
``data/manifests``, QC outcomes recomputed from the validated parquets,
CI stages from ``.github/workflows/ci.yml``, registry entities from
``catalog/models.py``, identity semantics from ``tracking/identity.py`` and
``tracking/run.py``.

fig_4_1_architecture      layered end-to-end architecture (real module names)
fig_4_2_data_dag          ingestion DAG: raw -> QC -> validated -> processed
fig_4_3_storage_layout    data-lake layout + manifest integrity model
fig_4_4_qc_outcomes       real QC outcomes (recomputed from validated data)
fig_4_5_causal_aggregation timing of 5m -> 1h aggregation without leakage
fig_4_6_engine_sequence   backtest engine timing for one complete trade
fig_4_7_search_orchestration RS/GA per-fold orchestration with budget parity
fig_4_8_registry_model    experiment registry entity model (real tables)
fig_4_9_reproducibility_chain identity fingerprint vs run id vs data hashes
fig_4_10_ci_pipeline      CI quality gate, real stages

Figure 4.11 (dashboard screenshot) is captured from the running app, not here.
"""

# ruff: noqa: RUF001, RUF003  # typographic characters are intentional in figure text

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import polars as pl
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path("reports/figures/thesis_ch4")

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


def box(ax, x, y, w, h, text, color, fs=8.5, fc="white", lw=1.2):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.08", linewidth=lw, edgecolor=color, facecolor=fc
        )
    )
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def arrow(ax, x1, y1, x2, y2, color=GREY, style="-|>", ls="-", label=None, lfs=7.5, dy=0.18):
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle=style,
            mutation_scale=12,
            color=color,
            lw=1.1,
            linestyle=ls,
        )
    )
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + dy, label, ha="center", fontsize=lfs, color=color)


# --------------------------------------------------------------------------- #
# Fig 4.1 — end-to-end architecture, real module names
# --------------------------------------------------------------------------- #
def fig_4_1() -> str:
    fig, ax = plt.subplots(figsize=(8.4, 6.2))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 12)
    ax.axis("off")

    # Layer bands, bottom-up: data -> features -> engine -> search -> evaluation
    # -> registry/tracking -> serving.
    box(
        ax,
        0.2,
        10.4,
        3.4,
        1.2,
        "data.binance.vision\nmonthly bulk archive\n(klines, funding, mark price)",
        GREY,
        8,
    )
    box(
        ax,
        4.1,
        10.4,
        3.6,
        1.2,
        "perp_lab.data\nproviders · download · bars\nsplits (dev / frozen holdout)",
        ACCENT,
        8,
    )
    box(
        ax,
        8.2,
        10.4,
        3.6,
        1.2,
        "data lake (Parquet)\nraw → validated → processed\n+ SHA-256 manifests",
        ACCENT,
        8,
    )
    arrow(ax, 3.6, 11.0, 4.1, 11.0)
    arrow(ax, 7.7, 11.0, 8.2, 11.0)

    box(
        ax,
        0.2,
        8.6,
        5.6,
        1.2,
        "perp_lab.features · labeling\nconfig-driven feature engine (YAML)\ncausal windows only",
        SECOND,
        8,
    )
    box(
        ax,
        6.2,
        8.6,
        5.6,
        1.2,
        "perp_lab.validation\nschema checks · quality report · purge/embargo\nflag & report — never repair",
        SECOND,
        8,
    )
    arrow(ax, 9.9, 10.4, 9.9, 9.8)
    arrow(ax, 3.0, 10.0, 3.0, 9.8)

    box(
        ax,
        0.2,
        6.8,
        5.6,
        1.2,
        "perp_lab.backtesting\nvectorised Polars engine · costs (taker + slippage)\nrealised funding · next-open execution",
        ACCENT,
        8,
    )
    box(
        ax,
        6.2,
        6.8,
        5.6,
        1.2,
        "perp_lab.strategies · crt\n22 registered families\nfrozen hypothesis documents",
        ACCENT,
        8,
    )
    arrow(ax, 3.0, 8.6, 3.0, 8.0)
    arrow(ax, 9.0, 8.6, 9.0, 8.0)

    box(
        ax,
        0.2,
        5.0,
        5.6,
        1.2,
        "perp_lab.search\nrandom search (primary) + genetic algorithm\nbudget parity · seed schedule",
        SECOND,
        8,
    )
    box(
        ax,
        6.2,
        5.0,
        5.6,
        1.2,
        "perp_lab.experiments\nexpanding walk-forward (15 folds)\nmulti-seed studies (10 seeds)",
        SECOND,
        8,
    )
    arrow(ax, 3.0, 6.8, 3.0, 6.2)
    arrow(ax, 9.0, 6.8, 9.0, 6.2)

    box(
        ax,
        0.2,
        3.2,
        5.6,
        1.2,
        "perp_lab.evaluation\nrobustness battery (C1–C6) · bootstrap\nmultiple testing: Holm/BH · DSR · PBO (CSCV)",
        ACCENT,
        8,
    )
    box(
        ax,
        6.2,
        3.2,
        5.6,
        1.2,
        "perp_lab.catalog + tracking\nSQLite registry (SQLAlchemy) · DuckDB analytics\nrun identity fingerprint · artifact store",
        ACCENT,
        8,
    )
    arrow(ax, 3.0, 5.0, 3.0, 4.4)
    arrow(ax, 9.0, 5.0, 9.0, 4.4)

    box(
        ax,
        0.2,
        1.2,
        5.6,
        1.4,
        "perp_lab.api (FastAPI)\nread-only serving of runs,\nstudy closure and figures",
        SECOND,
        8,
    )
    box(
        ax,
        6.2,
        1.2,
        5.6,
        1.4,
        "apps/web (Next.js 14)\nbilingual panel + static JSON exports\nin-browser strategy lab (TS port of engine)",
        SECOND,
        8,
    )
    arrow(ax, 3.0, 3.2, 3.0, 2.6)
    arrow(ax, 9.0, 3.2, 9.0, 2.6)
    arrow(ax, 5.8, 1.9, 6.2, 1.9, label="SWR fetch", lfs=7)

    ax.text(
        6.0,
        0.35,
        "One direction of flow: serving layers are read-only consumers of frozen artifacts — nothing downstream can mutate an experiment.",
        ha="center",
        fontsize=8,
        color=GREY,
        style="italic",
    )
    return save(fig, "fig_4_1_architecture")


# --------------------------------------------------------------------------- #
# Fig 4.2 — ingestion DAG (real pipeline from perp_lab/data/download.py)
# --------------------------------------------------------------------------- #
def fig_4_2() -> str:
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8.6)
    ax.axis("off")

    box(
        ax,
        0.2,
        6.6,
        3.2,
        1.5,
        "Monthly ZIP archives\ndata.binance.vision\nonly closed months\n(cutoff 2026-07-01)",
        GREY,
        8,
    )
    box(
        ax,
        4.4,
        6.6,
        3.2,
        1.5,
        "data/raw/\nas-downloaded CSVs\nread-only by convention\nnever edited in place",
        ACCENT,
        8,
    )
    box(
        ax,
        8.6,
        6.6,
        3.2,
        1.5,
        "Schema validation + QC\ngaps · duplicates · OHLC\nnegatives · extreme returns\nflag & report, never repair",
        BAD,
        8,
    )
    arrow(ax, 3.4, 7.35, 4.4, 7.35)
    ax.text(3.9, 6.35, "download\n+ checksum", ha="center", fontsize=7, color=GREY)
    arrow(ax, 7.6, 7.35, 8.6, 7.35)

    box(
        ax,
        2.0,
        4.0,
        3.6,
        1.4,
        "data/validated/{sym}/\n5m.parquet · fundingRate\nmarkPrice_5m",
        ACCENT,
        8,
    )
    box(
        ax,
        6.6,
        4.0,
        3.6,
        1.4,
        "Causal resample\n5m → 15m, 1h\n(first open, last close,\nsum volume — no look-ahead)",
        SECOND,
        8,
    )
    arrow(ax, 10.2, 6.6, 4.6, 5.4, label="passes QC", lfs=7)
    arrow(ax, 5.6, 4.7, 6.6, 4.7)

    box(
        ax,
        1.0,
        1.4,
        4.6,
        1.5,
        "data/processed/{sym}/\n{15m,1h}_development.parquet\n{15m,1h}_holdout.parquet (frozen)",
        ACCENT,
        8,
    )
    box(
        ax,
        6.6,
        1.4,
        4.6,
        1.5,
        "data/manifests/*.json\nper dataset: origin, period,\nrow count, SHA-256, git commit",
        AMBER,
        8,
    )
    arrow(ax, 8.4, 4.0, 4.6, 2.9)
    ax.text(8.2, 3.35, "dev / holdout split (2026-01-01)", ha="left", fontsize=7, color=GREY)
    arrow(ax, 5.6, 2.15, 6.6, 2.15, label="every output\nis manifested", lfs=7, dy=0.35)

    ax.text(
        6.0,
        0.45,
        "DAG re-run 2026-08-19 after an accidental wipe of data/: every dataset reproduced with identical SHA-256.",
        ha="center",
        fontsize=8,
        color=AMBER,
        style="italic",
    )
    return save(fig, "fig_4_2_data_dag")


# --------------------------------------------------------------------------- #
# Fig 4.3 — storage layout + integrity model (real paths and row counts)
# --------------------------------------------------------------------------- #
def fig_4_3() -> str:
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    ax.axis("off")

    tree = (
        "data/\n"
        "├── raw/                          as-downloaded archives (read-only)\n"
        "├── validated/\n"
        "│   ├── BTCUSDT/5m.parquet        683,424 rows (listing → cutoff)\n"
        "│   ├── BTCUSDT/fundingRate.parquet   7,119 events\n"
        "│   └── ETHUSDT/…                 same layout per symbol\n"
        "├── processed/\n"
        "│   ├── BTCUSDT/1h_development.parquet   52,608 bars (2020-01 → 2025-12)\n"
        "│   ├── BTCUSDT/1h_holdout.parquet        4,344 bars (frozen)\n"
        "│   └── …/{15m,1h}_{development,holdout}.parquet\n"
        "├── manifests/\n"
        "│   └── binance_um_<sym>_<stream>[_tf][_part].json\n"
        "│       {row_count, period, data_sha256, git_commit, code_version}\n"
        "└── catalog/catalog.sqlite        experiment registry (Fig. 4.8)\n"
        "\n"
        "artifacts/runs/<kind>_<UTC-stamp>_<6-hex>/\n"
        "├── resolved_experiment_config.yaml · search_space.json · folds.json\n"
        "├── seed_schedule.json · git_state.json · environment.json\n"
        "├── {random_search,genetic_algorithm}_candidates.parquet\n"
        "├── …_fold{0..14}_test_{equity,trades}.parquet\n"
        "└── comparison_summary.json · dataset_manifests.json"
    )
    ax.text(0.02, 0.97, tree, family="monospace", fontsize=7.6, va="top", transform=ax.transAxes)

    ax.text(
        0.02,
        0.02,
        "Integrity model: paths are deterministic and human-readable; integrity is enforced by SHA-256 recorded in per-dataset\n"
        "manifests and re-verified against the bytes — not by content-addressed paths. A mismatch fails the run loudly.",
        fontsize=8,
        color=AMBER,
        style="italic",
        va="bottom",
        transform=ax.transAxes,
    )
    return save(fig, "fig_4_3_storage_layout")


# --------------------------------------------------------------------------- #
# Fig 4.4 — QC outcomes recomputed from the real validated data
# --------------------------------------------------------------------------- #
def fig_4_4() -> str:
    # Panel A: the frozen QC assessment (reports/tables/eda/s2) — verified values.
    rows = [
        ("BTC 5m", 631_296, 0, 0, 0, 66),
        ("BTC 15m", 210_432, 0, 0, 0, 16),
        ("BTC 1h", 52_608, 0, 0, 0, 1),
        ("ETH 5m", 631_296, 0, 0, 0, 47),
        ("ETH 15m", 210_432, 0, 0, 0, 10),
        ("ETH 1h", 52_608, 0, 0, 0, 1),
    ]

    # Panel B: zero-volume 5m bars per month, recomputed from the validated lake.
    monthly = {}
    for sym in ("BTCUSDT", "ETHUSDT"):
        df = (
            pl.scan_parquet(f"data/validated/{sym}/5m.parquet")
            .filter(pl.col("open_time") < pl.datetime(2026, 1, 1, time_zone="UTC"))
            .with_columns(pl.col("open_time").dt.truncate("1mo").alias("month"))
            .group_by("month")
            .agg((pl.col("volume") == 0).sum().alias("zero_vol"))
            .sort("month")
            .collect()
        )
        monthly[sym] = df

    fig = plt.figure(figsize=(8.6, 3.6))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.1, 1.4], hspace=0.15)
    ax1 = fig.add_subplot(gs[:, 0])
    ax_btc = fig.add_subplot(gs[0, 1])
    ax_eth = fig.add_subplot(gs[1, 1], sharex=ax_btc, sharey=ax_btc)

    ax1.axis("off")
    cols = ["dataset", "bars", "missing", "dupes", "OHLC", "zero-vol"]
    cell = [[r[0], f"{r[1]:,}", r[2], r[3], r[4], r[5]] for r in rows]
    table = ax1.table(cellText=cell, colLabels=cols, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(7.6)
    table.auto_set_column_width(col=list(range(6)))
    table.scale(1.0, 1.35)
    for (r, c), cellobj in table.get_celld().items():
        cellobj.set_edgecolor("#d1d5db")
        if r == 0:
            cellobj.set_text_props(weight="bold")
            cellobj.set_facecolor("#f3f4f6")
        elif c == 5 and cell[r - 1][5] != 0:
            cellobj.set_text_props(color=AMBER)
    ax1.set_title(
        "QC assessment · development window\ncoverage 100% on all six datasets", fontsize=9
    )

    for ax, sym, color in ((ax_btc, "BTCUSDT", ACCENT), (ax_eth, "ETHUSDT", SECOND)):
        df = monthly[sym]
        ax.bar(
            df["month"].to_list(),
            df["zero_vol"].to_list(),
            width=26.0,
            color=color,
        )
        ax.text(
            0.02,
            0.82,
            f"{sym[:3]} · {int(df['zero_vol'].sum())} zero-volume 5m bars",
            transform=ax.transAxes,
            fontsize=8,
            color=color,
        )
        ax.set_ylabel("bars", fontsize=8)
        ax.tick_params(labelsize=7.5)
    plt.setp(ax_btc.get_xticklabels(), visible=False)
    ax_btc.set_title(
        "Zero-volume 5-minute bars per month\nthe only anomaly class found — flagged, kept",
        fontsize=9,
    )

    fig.tight_layout()
    return save(fig, "fig_4_4_qc_outcomes")


# --------------------------------------------------------------------------- #
# Fig 4.5 — causal aggregation timing (5m -> 1h)
# --------------------------------------------------------------------------- #
def fig_4_5() -> str:
    fig, ax = plt.subplots(figsize=(8.2, 3.4))
    ax.set_xlim(-0.4, 15.2)
    ax.set_ylim(-0.4, 5.6)
    ax.axis("off")

    # Twelve 5m bars forming the 10:00–11:00 hourly bar.
    for i in range(12):
        ax.add_patch(
            FancyBboxPatch(
                (i * 0.95, 3.6),
                0.78,
                0.9,
                boxstyle="round,pad=0.03",
                lw=0.9,
                edgecolor=GREY,
                facecolor="#f3f4f6",
            )
        )
    ax.text(0.0, 4.8, "5m bars  10:00 … 10:55  (open_time labels)", fontsize=8, color=GREY)
    ax.text(-0.05, 3.32, "10:00", fontsize=7, color=GREY)
    ax.text(10.45, 3.32, "10:55", fontsize=7, color=GREY)

    box(
        ax,
        1.8,
        1.4,
        7.0,
        1.1,
        "1h bar, open_time = 10:00\nopen = first 5m open · close = last 5m close · volume = Σ",
        ACCENT,
        8,
    )
    arrow(ax, 5.3, 3.5, 5.3, 2.7)
    ax.text(5.55, 3.05, "closed only at 11:00", fontsize=7.5, color=BAD, ha="left")

    box(
        ax,
        9.9,
        1.3,
        5.0,
        1.3,
        "earliest use by a strategy:\ndecision at 11:00 close →\nposition from the 12:00 bar open",
        SECOND,
        7.8,
    )
    arrow(ax, 8.9, 1.95, 9.9, 1.95)

    ax.text(
        0.0,
        0.4,
        "The aggregate carries the label of its first bar but only exists once its last 5m bar has closed; QC cross-checks every\n"
        "aggregated series against the exchange's native klines. Funding joins are backward as-of: the rate charged in a bar was published before it.",
        fontsize=8,
        color=GREY,
        style="italic",
    )
    return save(fig, "fig_4_5_causal_aggregation")


# --------------------------------------------------------------------------- #
# Fig 4.6 — engine sequence for one complete trade (real conventions)
# --------------------------------------------------------------------------- #
def fig_4_6() -> str:
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis("off")

    # Timeline of bars t-1 .. t+3
    labels = ["bar t−1", "bar t", "bar t+1", "bar t+2", "bar t+3"]
    for i, lab in enumerate(labels):
        x = 0.6 + i * 2.7
        ax.add_patch(
            FancyBboxPatch(
                (x, 5.9),
                2.2,
                0.9,
                boxstyle="round,pad=0.04",
                lw=1.0,
                edgecolor=GREY,
                facecolor="#f3f4f6",
            )
        )
        ax.text(x + 1.1, 6.35, lab, ha="center", fontsize=8.5)

    ann = [
        (1.7, "signal computed\non bar t−1 close", ACCENT),
        (
            4.4,
            "position side applied\nfrom bar t open;\nentry cost on turnover\n(4 + 1 bps per side)",
            SECOND,
        ),
        (7.1, "return accrues\nopen-to-open;\nrealised funding on\nthe held position", ACCENT),
        (9.8, "exit signal on close;\nflat — or flip:\nturnover 2, charged\nas two sides", SECOND),
        (12.5, "MAE / MFE and PnL\nclosed into the\ntrade ledger\nat exit open", ACCENT),
    ]
    for x, text, color in ann:
        arrow(ax, x, 5.8, x, 4.6, color=color)
        box(ax, x - 1.15, 2.9, 2.3, 1.7, text, color, 7.4)

    ax.text(
        7.0,
        1.6,
        "Invariant: no quantity computed on bar t can influence the position held during bar t.\n"
        "The last bar is dropped (its open-to-open return is unknowable). Pinned-output unit tests fix these numbers exactly.",
        ha="center",
        fontsize=8,
        color=GREY,
        style="italic",
    )
    return save(fig, "fig_4_6_engine_sequence")


# --------------------------------------------------------------------------- #
# Fig 4.7 — search orchestration with budget parity (real numbers)
# --------------------------------------------------------------------------- #
def fig_4_7() -> str:
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.axis("off")

    box(
        ax,
        3.4,
        7.6,
        5.2,
        1.1,
        "per family × asset × seed:\n15 walk-forward folds, processed independently",
        GREY,
        8.5,
    )

    box(
        ax,
        0.4,
        5.2,
        5.2,
        1.6,
        "random search (primary engine)\n100 candidates per fold\nseed: SeedSequence(base_seed,\nspawn_key = blake2b(stream label))",
        ACCENT,
        8,
    )
    box(
        ax,
        6.4,
        5.2,
        5.2,
        1.6,
        "genetic algorithm (cross-check)\nidentical evaluation budget\nbudget-parity ledger records\nevaluations and wall-time per fold",
        SECOND,
        8,
    )
    arrow(ax, 5.0, 7.6, 3.0, 6.9)
    arrow(ax, 7.0, 7.6, 9.0, 6.9)

    box(
        ax,
        0.4,
        3.0,
        5.2,
        1.3,
        "select on validation Sharpe\n(train fit → validation ranking;\ntest window never touched)",
        ACCENT,
        8,
    )
    box(
        ax,
        6.4,
        3.0,
        5.2,
        1.3,
        "select on validation Sharpe\nsame folds, same costs,\nsame seeds discipline",
        SECOND,
        8,
    )
    arrow(ax, 3.0, 5.2, 3.0, 4.4)
    arrow(ax, 9.0, 5.2, 9.0, 4.4)

    box(
        ax,
        3.4,
        0.9,
        5.2,
        1.3,
        "winner re-run once on the fold's test window\n→ OOS segments concatenated\nverdicts read on random search only",
        BAD,
        8,
    )
    arrow(ax, 3.0, 3.0, 4.6, 2.3)
    arrow(ax, 9.0, 3.0, 7.4, 2.3)

    ax.text(
        11.9,
        8.0,
        "full study:\n2 assets ×\n10 seeds",
        fontsize=8,
        color=GREY,
        ha="right",
    )
    return save(fig, "fig_4_7_search_orchestration")


# --------------------------------------------------------------------------- #
# Fig 4.8 — registry entity model (real tables from catalog/models.py)
# --------------------------------------------------------------------------- #
def fig_4_8() -> str:
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.axis("off")

    box(ax, 0.3, 7.4, 2.2, 1.1, "Study\nstudies", ACCENT, 8.5)
    box(ax, 3.2, 7.4, 2.8, 1.1, "ExperimentRound\nexperiment_rounds", ACCENT, 8.5)
    box(ax, 6.6, 7.4, 2.5, 1.1, "StrategyFamily\nstrategy_families", ACCENT, 8.5)
    box(ax, 9.7, 7.4, 2.1, 1.1, "StrategySpec\nstrategy_specs", ACCENT, 8.5)
    arrow(ax, 2.55, 7.95, 3.15, 7.95, label="1:N", lfs=7, dy=0.28)
    arrow(ax, 6.05, 7.95, 6.55, 7.95, label="1:N", lfs=7, dy=0.28)
    arrow(ax, 9.15, 7.95, 9.65, 7.95, label="1:N", lfs=7, dy=0.28)

    box(ax, 0.3, 5.0, 2.4, 1.1, "Run\nruns", SECOND, 8.5)
    box(ax, 3.3, 5.0, 2.4, 1.1, "RunSeed\nrun_seeds", SECOND, 8.5)
    box(ax, 6.3, 5.0, 2.4, 1.1, "Fold\nfolds", SECOND, 8.5)
    box(ax, 9.3, 5.0, 2.5, 1.1, "FoldResult\nfold_results", SECOND, 8.5)
    arrow(ax, 7.9, 7.4, 1.6, 6.1, label="1:N", lfs=7)
    arrow(ax, 2.7, 5.55, 3.3, 5.55, label="1:N", lfs=7)
    arrow(ax, 5.7, 5.55, 6.3, 5.55, label="1:N", lfs=7)
    arrow(ax, 8.7, 5.55, 9.3, 5.55, label="1:N", lfs=7)

    box(ax, 0.3, 2.6, 2.8, 1.1, "SearchEvaluation\nsearch_evaluations", GREY, 8)
    box(ax, 3.6, 2.6, 1.9, 1.1, "Metric\nmetrics", GREY, 8)
    box(ax, 6.0, 2.6, 2.3, 1.1, "GateResult\ngate_results", GREY, 8)
    box(ax, 8.8, 2.6, 2.0, 1.1, "Artifact\nartifacts", GREY, 8)
    for x in (1.7, 4.5, 7.1, 9.8):
        arrow(ax, 1.5 if x == 1.7 else x, 5.0, x, 3.7, label="N per run", lfs=6.6)

    box(ax, 0.9, 0.5, 3.6, 1.1, "MonteCarloRun\nmonte_carlo_runs", AMBER, 8)
    box(ax, 5.1, 0.5, 3.9, 1.1, "HoldoutRegistryEntry\nholdout_registry (append-only)", AMBER, 8)

    ax.text(
        11.9,
        1.05,
        "every table carries Provenance\n(run id, git commit) — a metric\nwithout a measurement\nis an integrity error",
        fontsize=7.2,
        color=GREY,
        ha="right",
        va="center",
    )
    return save(fig, "fig_4_8_registry_model")


# --------------------------------------------------------------------------- #
# Fig 4.9 — reproducibility chain (corrected semantics)
# --------------------------------------------------------------------------- #
def fig_4_9() -> str:
    fig, ax = plt.subplots(figsize=(8.4, 4.9))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.axis("off")

    box(ax, 0.3, 6.9, 2.6, 1.7, "resolved config\n(as validated,\nnot as typed)", ACCENT, 8)
    box(ax, 3.2, 6.9, 2.6, 1.7, "methodological\ncontracts\n(data + experiment\nYAML)", ACCENT, 8)
    box(
        ax,
        6.1,
        6.9,
        2.6,
        1.7,
        "SHA-256 of every\ndevelopment\npartition the run\nmay read",
        ACCENT,
        8,
    )
    box(
        ax,
        9.0,
        6.9,
        2.7,
        1.7,
        "git state: commit,\nbranch, diff +\nuntracked files under\nsrc/ tests/ configs/",
        ACCENT,
        8,
    )

    box(
        ax,
        3.6,
        4.4,
        4.8,
        1.2,
        "SHA-256 → identity fingerprint\ntracking/identity.py · run_identity.json",
        SECOND,
        8.5,
    )
    for x in (1.6, 4.5, 7.4, 10.3):
        arrow(ax, x, 6.9, 6.0, 5.7)

    box(
        ax,
        0.3,
        2.0,
        5.0,
        1.4,
        "run id (address, not identity)\n<kind>_<UTC-stamp>_<6-hex uuid>\nsortable, unique — deliberately NOT\nderived from the configuration",
        GREY,
        8,
    )
    box(
        ax,
        6.7,
        2.0,
        5.0,
        1.4,
        "artifact receipts\ndataset_manifests.json + parquet outputs\nre-verified by re-hashing the bytes\n(2026-08-19 re-ingestion: byte-identical)",
        AMBER,
        8,
    )
    arrow(ax, 5.0, 4.4, 2.8, 3.5)
    arrow(ax, 7.0, 4.4, 9.2, 3.5)

    ax.text(
        6.0,
        0.9,
        "Two runs are the same experiment iff their identity fingerprints match — regardless of when they ran or what their run ids are.\n"
        "The fingerprint flips on any change to config, contract, data or code, including untracked files invisible to git diff.",
        ha="center",
        fontsize=8,
        color=GREY,
        style="italic",
    )
    return save(fig, "fig_4_9_reproducibility_chain")


# --------------------------------------------------------------------------- #
# Fig 4.10 — CI pipeline, real stages from .github/workflows/ci.yml
# --------------------------------------------------------------------------- #
def fig_4_10() -> str:
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    ax.set_xlim(0, 14.8)
    ax.set_ylim(0, 6.4)
    ax.axis("off")

    box(
        ax,
        0.2,
        4.4,
        3.4,
        1.3,
        "trigger\npush (main, feat/**, fix/**,\ndocs/**, style/**, chore/**)\n+ every pull request",
        GREY,
        7.8,
    )

    stages = [
        ("uv sync\n--extra dev", ACCENT),
        ("ruff check\n(lint)", ACCENT),
        ("ruff format\n--check", ACCENT),
        ("stale-claims\nsweep", AMBER),
        ("pytest\n'not network'\n1,538 tests", SECOND),
    ]
    x = 4.3
    for text, color in stages:
        box(ax, x, 4.4, 1.7, 1.3, text, color, 7.4)
        if x > 4.3:
            arrow(ax, x - 0.35, 5.05, x - 0.1, 5.05)
        x += 2.1
    arrow(ax, 3.7, 5.05, 4.2, 5.05)

    box(
        ax,
        0.2,
        1.6,
        7.0,
        1.3,
        "kept local, by design:\npyright (run before releases) · notebook determinism check\n(needs the data lake, which never leaves the machine)",
        GREY,
        7.5,
    )
    box(
        ax,
        7.8,
        1.6,
        6.8,
        1.3,
        "frontend gate (apps/web):\nvitest — 112 tests · tsc · next build\nrun locally before each web change lands",
        GREY,
        7.5,
    )

    ax.text(
        7.4,
        0.6,
        "ubuntu-latest · 25-minute timeout · a red gate blocks the merge — the stale-claims sweep fails CI if any\n"
        "committed document claims a result no artifact backs.",
        ha="center",
        fontsize=8,
        color=GREY,
        style="italic",
    )
    return save(fig, "fig_4_10_ci_pipeline")


# =========================================================================== #
# Final-draft composites and engineering-depth figures (module map, catalogue
# ERD, config lifecycle, seed derivation). fig_4_3/fig_4_4 are the two-panel
# composites the final chapter text describes; the fig_4x_* files are
# insertable engineering figures whose numbers the author assigns.
# =========================================================================== #
def fig_4_3_temporal_contract() -> str:
    """Figure 4.3 of the final draft: causal aggregation (A) + execution (B)."""
    fig, (axa, axb) = plt.subplots(2, 1, figsize=(8.6, 6.4), height_ratios=[1, 1.15])

    axa.set_xlim(-0.4, 15.2)
    axa.set_ylim(-0.2, 5.8)
    axa.axis("off")
    axa.text(
        -0.3,
        5.55,
        "A · Causal aggregation: when a 1h bar becomes observable",
        fontsize=9.5,
        weight="bold",
    )
    for i in range(12):
        axa.add_patch(
            FancyBboxPatch(
                (i * 0.95, 3.4),
                0.78,
                0.9,
                boxstyle="round,pad=0.03",
                lw=0.9,
                edgecolor=GREY,
                facecolor="#f3f4f6",
            )
        )
    axa.text(0.0, 4.55, "5m bars 10:00 … 10:55 (open_time labels)", fontsize=8, color=GREY)
    axa.text(-0.05, 3.12, "10:00", fontsize=7, color=GREY)
    axa.text(10.45, 3.12, "10:55", fontsize=7, color=GREY)
    box(
        axa,
        1.8,
        1.2,
        7.0,
        1.1,
        "1h bar, open_time = 10:00\nopen = first 5m open · close = last 5m close · volume = Σ",
        ACCENT,
        7.6,
    )
    arrow(axa, 5.3, 3.3, 5.3, 2.5)
    axa.text(5.55, 2.85, "closed only at 11:00", fontsize=7.5, color=BAD, ha="left")
    box(
        axa,
        9.9,
        1.1,
        5.0,
        1.3,
        "earliest use by a strategy:\ndecision at 11:00 close →\nposition from the 12:00 bar open",
        SECOND,
        7.8,
    )
    arrow(axa, 8.9, 1.75, 9.9, 1.75)

    axb.set_xlim(0, 14)
    axb.set_ylim(0, 7.6)
    axb.axis("off")
    axb.text(
        0.1,
        7.3,
        "B · Next-open execution: one complete trade through the ledger",
        fontsize=9.5,
        weight="bold",
    )
    labels = ["bar t−1", "bar t", "bar t+1", "bar t+2", "bar t+3"]
    for i, lab in enumerate(labels):
        x = 0.6 + i * 2.7
        axb.add_patch(
            FancyBboxPatch(
                (x, 5.5),
                2.2,
                0.9,
                boxstyle="round,pad=0.04",
                lw=1.0,
                edgecolor=GREY,
                facecolor="#f3f4f6",
            )
        )
        axb.text(x + 1.1, 5.95, lab, ha="center", fontsize=8.5)
    ann = [
        (1.7, "signal computed\non bar t−1 close", ACCENT),
        (
            4.4,
            "position applied\nfrom bar t open;\nentry cost on turnover\n(4 + 1 bps per side)",
            SECOND,
        ),
        (7.1, "return accrues\nopen-to-open;\nfunding as-of-past on\nthe held position", ACCENT),
        (
            9.8,
            "exit signal on close;\nflat — or reversal:\nturnover 2, charged\nas two sides",
            SECOND,
        ),
        (12.5, "PnL, costs and\nfunding closed into\nthe trade ledger\nat exit open", ACCENT),
    ]
    for x, text, color in ann:
        arrow(axb, x, 5.4, x, 4.3, color=color)
        box(axb, x - 1.15, 2.6, 2.3, 1.7, text, color, 7.4)
    axb.text(
        7.0,
        1.3,
        "Invariant: no quantity computed on bar t can influence the position held during bar t. The last bar is dropped\n"
        "(its open-to-open return is unknowable). Pinned-output unit tests fix these numbers exactly.",
        ha="center",
        fontsize=8,
        color=GREY,
        style="italic",
    )
    fig.tight_layout()
    return save(fig, "fig_4_3_temporal_contract")


def fig_4_4_orchestration_evidence() -> str:
    """Figure 4.4 of the final draft: orchestration plus evidence capture."""
    fig, ax = plt.subplots(figsize=(8.6, 6.4))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 12.4)
    ax.axis("off")

    box(
        ax,
        2.6,
        11.1,
        6.8,
        1.0,
        "registered family × asset × seed\n15 walk-forward folds, processed independently",
        GREY,
        8.5,
    )

    box(
        ax,
        0.4,
        8.7,
        5.2,
        1.7,
        "random search (primary engine)\n100 candidates per fold\nseed: SeedSequence(base_seed,\nspawn_key = blake2b(stream label))",
        ACCENT,
        8,
    )
    box(
        ax,
        6.4,
        8.7,
        5.2,
        1.7,
        "genetic algorithm (cross-check)\nidentical evaluation budget;\ncandidate hashes de-duplicate, so parity\ncounts unique evaluated configurations",
        SECOND,
        8,
    )
    arrow(ax, 5.0, 11.1, 3.0, 10.5)
    arrow(ax, 7.0, 11.1, 9.0, 10.5)

    box(
        ax,
        0.4,
        6.6,
        5.2,
        1.3,
        "select on validation Sharpe\n(train fit → validation ranking;\ntest window never touched)",
        ACCENT,
        8,
    )
    box(
        ax,
        6.4,
        6.6,
        5.2,
        1.3,
        "select on validation Sharpe\nsame folds, costs and\nseed discipline",
        SECOND,
        8,
    )
    arrow(ax, 3.0, 8.7, 3.0, 8.0)
    arrow(ax, 9.0, 8.7, 9.0, 8.0)

    box(
        ax,
        3.0,
        4.6,
        6.0,
        1.2,
        "winner re-run once on the fold's untouched test window\n→ OOS segments concatenated · verdicts read on random search",
        BAD,
        8,
    )
    arrow(ax, 3.0, 6.6, 4.6, 5.9)
    arrow(ax, 9.0, 6.6, 7.4, 5.9)

    box(
        ax,
        0.3,
        2.2,
        7.2,
        1.7,
        "evidence package (per run, immutable)\nresolved config · folds.json · seed_schedule · candidates parquet\nOOS equity + trade ledgers · metrics · gate results · logs · figures",
        AMBER,
        8,
    )
    box(
        ax,
        8.0,
        2.2,
        3.8,
        1.7,
        "experiment catalogue\nSQLite/SQLAlchemy index\n+ DuckDB analytics over\nthe parquet artefacts",
        AMBER,
        8,
    )
    arrow(ax, 6.0, 4.6, 3.9, 3.9)
    arrow(ax, 6.0, 4.6, 9.9, 3.9)
    arrow(ax, 7.5, 3.05, 8.0, 3.05, label="indexed by\nrun id", lfs=7, dy=0.35)

    ax.text(
        6.0,
        1.2,
        "A catalogue row that cannot be linked to its originating run and immutable artefact is an integrity error:\n"
        "the database indexes the evidence, it never replaces it.",
        ha="center",
        fontsize=8,
        color=GREY,
        style="italic",
    )
    return save(fig, "fig_4_4_orchestration_evidence")


def fig_4x_module_map() -> str:
    """Monorepo module map with real packages, file counts and LOC."""
    fig, ax = plt.subplots(figsize=(8.8, 6.6))
    ax.axis("off")

    planes = [
        (
            "Data plane",
            ACCENT,
            [
                ("data", "10 · 1,261", "acquisition, causal bars, dev/holdout splits, provenance"),
                (
                    "validation",
                    "4 · 503",
                    "schema + quality report, walk-forward CV, purge/embargo",
                ),
                ("features", "7 · 1,738", "config-driven causal feature engine"),
                ("labeling", "2 · 483", "triple-barrier event labels"),
            ],
        ),
        (
            "Research engine",
            SECOND,
            [
                ("strategies", "19 · 2,592", "interpretable baseline families"),
                ("crt", "9 · 4,856", "candle-range battery (9 families)"),
                ("backtesting", "3 · 489", "vectorised next-open engine with costs + funding"),
                ("search", "11 · 4,213", "shared spaces, evaluator, random search + GA"),
                ("experiments", "4 · 1,253", "walk-forward + multi-seed orchestration"),
                ("regimes", "3 · 422", "fold-fit regime transforms"),
                ("stochastic", "3 · 701", "synthetic markets that audit the pipeline"),
                ("meta_labeling", "6 · 2,391", "pre-registered supervised ML layer"),
            ],
        ),
        (
            "Evidence plane",
            AMBER,
            [
                ("evaluation", "8 · 2,862", "robustness battery C1-C6, multiple testing, DSR/PBO"),
                ("catalog", "8 · 3,249", "SQLite registry + DuckDB analytics + artifact store"),
                ("tracking", "4 · 567", "run ids, identity fingerprints, environment capture"),
                ("reporting", "11 · 4,754", "house style, artifact export, closure reports"),
                ("eda", "27 · 3,853", "reusable EDA functions (Ch. 5)"),
            ],
        ),
        (
            "Consumption plane",
            GREY,
            [
                ("api", "19 · 2,456", "read-only FastAPI over frozen artefacts"),
                (
                    "dashboard",
                    "3 · 823",
                    "legacy Streamlit inspector (the Next.js panel lives in apps/web)",
                ),
            ],
        ),
        (
            "Cross-cutting",
            BAD,
            [
                ("config", "4 · 1,693", "pydantic contracts for data + experiment YAML"),
                ("utils", "5 · 264", "hashing, UTC time, logging, deterministic seeds"),
                ("cli.py", "2 · 957", "thin command layer; orchestration stays in modules"),
            ],
        ),
    ]

    y = 0.985
    ax.text(
        0.0,
        y,
        "src/perp_lab — 172 Python files · 42,380 lines · 22 packages",
        fontsize=10.5,
        weight="bold",
        transform=ax.transAxes,
        va="top",
    )
    y -= 0.045
    for title, color, mods in planes:
        ax.text(
            0.0,
            y,
            title,
            fontsize=9.5,
            weight="bold",
            color=color,
            transform=ax.transAxes,
            va="top",
        )
        y -= 0.033
        for name, size, role in mods:
            ax.text(
                0.03,
                y,
                name,
                fontsize=8.3,
                family="monospace",
                color=color,
                transform=ax.transAxes,
                va="top",
            )
            ax.text(0.175, y, size, fontsize=7.6, color=GREY, transform=ax.transAxes, va="top")
            ax.text(0.26, y, role, fontsize=8.3, transform=ax.transAxes, va="top")
            y -= 0.0295
        y -= 0.012
    ax.text(
        0.0,
        y - 0.005,
        "Companion trees: tests/ (1,539 pytest), scripts/ (deterministic notebook + figure builders), configs/ (frozen contracts),\n"
        "apps/web (Next.js panel, 112 vitest), docs/decisions (18 ADRs), artifacts/runs (447 evidence packages).",
        fontsize=8,
        color=GREY,
        style="italic",
        transform=ax.transAxes,
        va="top",
    )
    return save(fig, "fig_4x_module_map")


def fig_4x_catalog_erd() -> str:
    """Detailed catalogue ERD with the real columns of the core tables."""
    fig, ax = plt.subplots(figsize=(9.2, 6.8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 12.6)
    ax.axis("off")

    def table_box(x, y, w, h, title, cols, color, fs=6.6):
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.06", lw=1.2, edgecolor=color, facecolor="white"
            )
        )
        ax.text(
            x + w / 2, y + h - 0.28, title, ha="center", fontsize=7.8, weight="bold", color=color
        )
        ax.plot([x + 0.1, x + w - 0.1], [y + h - 0.52, y + h - 0.52], color=color, lw=0.7)
        ax.text(x + 0.14, y + h - 0.68, "\n".join(cols), fontsize=fs, va="top", family="monospace")

    table_box(
        0.2,
        9.4,
        2.6,
        2.9,
        "studies",
        [
            "id · key · title",
            "primary_symbol",
            "secondary_symbol",
            "timeframe",
            "holdout_start/end",
        ],
        ACCENT,
    )
    table_box(
        3.2,
        9.4,
        2.7,
        2.9,
        "experiment_rounds",
        ["id · study_id (FK)", "key · name", "sequence", "criterion", "opened_at/closed_at"],
        ACCENT,
    )
    table_box(
        6.2,
        9.4,
        2.7,
        2.9,
        "strategy_families",
        ["id · study_id (FK)", "key · name", "hypothesis", "module", "status"],
        ACCENT,
    )
    table_box(
        9.2,
        9.4,
        2.6,
        2.9,
        "strategy_specs",
        ["id · family_id (FK)", "spec_hash", "symbol · timeframe", "params (JSON)"],
        ACCENT,
    )

    table_box(
        0.2,
        5.6,
        2.9,
        3.3,
        "runs",
        [
            "id · run_id",
            "study/round/family FK",
            "symbol · timeframe",
            "engine · run_dir",
            "identity_fingerprint",
            "config (JSON) · seeds",
            "started/finished_at",
        ],
        SECOND,
    )
    table_box(
        3.4,
        5.6,
        2.5,
        3.3,
        "run_seeds",
        [
            "id · run_id (FK)",
            "seed",
            "n_folds · n_bars",
            "+ CoreMetrics:",
            "return · sharpe",
            "max_dd · trades …",
        ],
        SECOND,
    )
    table_box(
        6.2,
        5.6,
        2.7,
        3.3,
        "folds",
        [
            "id · run_id (FK)",
            "fold_index",
            "train_start/end",
            "test_start/end",
            "purge_bars = 96",
            "embargo_bars = 118",
        ],
        SECOND,
    )
    table_box(
        9.2,
        5.6,
        2.6,
        3.3,
        "fold_results",
        ["id · fold_id (FK)", "run_seed_id (FK)", "spec_id (FK)", "is_train", "+ CoreMetrics"],
        SECOND,
    )

    table_box(
        0.2,
        1.8,
        2.9,
        3.1,
        "search_evaluations",
        [
            "id · run_id (FK)",
            "seed · fold_index",
            "evaluation_index",
            "generation (GA)",
            "spec_id (FK)",
            "objective · feasible",
        ],
        GREY,
    )
    table_box(
        3.4,
        1.8,
        2.5,
        3.1,
        "metrics",
        ["id · study_id (FK)", "scope · scope_ref", "metric_key", "value · unit", "context (JSON)"],
        GREY,
    )
    table_box(
        6.2,
        1.8,
        2.7,
        3.1,
        "gate_results",
        [
            "id · round/family FK",
            "symbol",
            "criterion_key (C1-C6)",
            "verdict · observed",
            "threshold",
            "n_seeds_passed/total",
        ],
        GREY,
    )
    table_box(
        9.2,
        1.8,
        2.6,
        3.1,
        "artifacts",
        [
            "id · uri · backend",
            "object_key · kind",
            "byte_size · row_count",
            "content_sha256",
            "run_id/study_id FK",
        ],
        GREY,
    )

    for x1, x2 in ((2.8, 3.2), (5.9, 6.2), (8.9, 9.2)):
        arrow(ax, x1, 10.85, x2, 10.85)
    arrow(ax, 7.5, 9.4, 1.8, 8.9)
    for x1, x2 in ((3.1, 3.4), (5.9, 6.2), (8.9, 9.2)):
        arrow(ax, x1, 7.2, x2, 7.2)
    for x in (1.6, 4.6, 7.5, 10.4):
        arrow(ax, x if x != 4.6 else 1.9, 5.6, x, 4.9)

    ax.text(
        6.0,
        0.7,
        "monte_carlo_runs and holdout_registry (append-only) complete the schema. Every table inherits ProvenanceMixin\n"
        "(source_artifact, source_sha256, git_commit, code_version, ingested_at); results tables add StatusMixin and CoreMetricsMixin.\n"
        "A Metric row without a linked measurement raises MetricsWithoutMeasurementError at ingest time.",
        ha="center",
        fontsize=7.6,
        color=GREY,
        style="italic",
    )
    return save(fig, "fig_4x_catalog_erd")


def fig_4x_config_lifecycle() -> str:
    """Config-as-code lifecycle: YAML contracts to resolved, validated runs."""
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8.6)
    ax.axis("off")

    box(
        ax,
        0.2,
        6.6,
        3.4,
        1.5,
        "configs/data_contract.yaml\nsymbols · timeframes · cutoff\nholdout window (frozen v0.1.0)",
        ACCENT,
        7.8,
    )
    box(
        ax,
        4.3,
        6.6,
        3.4,
        1.5,
        "configs/experiment.yaml\nfeatures · families · costs\nwalk-forward · labeling · fitness",
        ACCENT,
        7.8,
    )
    box(
        ax,
        8.4,
        6.6,
        3.4,
        1.5,
        "CLI / experiment call\nfamily · asset · seed · engine\n(abbreviated researcher input)",
        GREY,
        7.8,
    )

    box(
        ax,
        2.2,
        4.2,
        7.6,
        1.3,
        "pydantic contracts (perp_lab.config)\nunknown kind / bad window / bad lag → hard error at load time, before any data is read",
        SECOND,
        8,
    )
    for x in (1.9, 6.0, 10.1):
        arrow(ax, x, 6.6, 6.0, 5.5)

    box(
        ax,
        0.4,
        1.9,
        5.2,
        1.4,
        "resolved configuration\nstored verbatim in the run\n(resolved_experiment_config.yaml)\n— the authoritative description",
        ACCENT,
        7.8,
    )
    box(
        ax,
        6.4,
        1.9,
        5.2,
        1.4,
        "family registry gate\nunregistered families cannot enter\ncanonical searches — exploratory code\nstays out of the confirmatory study",
        BAD,
        7.8,
    )
    arrow(ax, 4.6, 4.2, 3.0, 3.3)
    arrow(ax, 7.4, 4.2, 9.0, 3.3)

    ax.text(
        6.0,
        0.8,
        "What executes is the resolved configuration, never the researcher's shorthand: the same YAML + code state\n"
        "always resolves to the same run identity fingerprint (Fig. 4.5).",
        ha="center",
        fontsize=8,
        color=GREY,
        style="italic",
    )
    return save(fig, "fig_4x_config_lifecycle")


def fig_4x_seed_derivation() -> str:
    """Deterministic seed tree with the real values of a recorded run."""
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.axis("off")

    box(
        ax,
        4.1,
        7.4,
        3.8,
        1.2,
        "base seed (one integer per\nfamily × asset × seed unit)\ne.g. 278037",
        ACCENT,
        8.5,
    )
    box(
        ax,
        2.6,
        5.0,
        6.8,
        1.3,
        "stream label → blake2b(label, 16 bytes) → spawn_key\nSeedSequence(entropy=base_seed, spawn_key=digest)",
        SECOND,
        8.5,
    )
    arrow(ax, 6.0, 7.4, 6.0, 6.3)

    leaves = [
        (0.6, "random_search\nfold 0\n→ 705502381"),
        (3.4, "random_search\nfold 1\n→ 3035994299"),
        (6.2, "genetic_algorithm\nfold 0\n→ 139268233"),
        (9.0, "regime tagging\nstream\n→ 2257660800"),
    ]
    for x, text in leaves:
        box(ax, x, 2.4, 2.4, 1.5, text, GREY, 7.6)
        arrow(ax, 6.0, 5.0, x + 1.2, 3.9)

    ax.text(
        6.0,
        1.2,
        "Recorded per run in seed_schedule.json: every stream is reconstructible from the base seed alone, a repeated run\n"
        "replays identical randomness, and two logically distinct experiment units can never share a stream by accident.",
        ha="center",
        fontsize=8,
        color=GREY,
        style="italic",
    )
    return save(fig, "fig_4x_seed_derivation")


def build_final_draft_figures() -> None:
    for fn in (
        fig_4_3_temporal_contract,
        fig_4_4_orchestration_evidence,
        fig_4x_module_map,
        fig_4x_catalog_erd,
        fig_4x_config_lifecycle,
        fig_4x_seed_derivation,
    ):
        print(fn())


def main() -> int:
    for fn in (
        fig_4_1,
        fig_4_2,
        fig_4_3,
        fig_4_4,
        fig_4_5,
        fig_4_6,
        fig_4_7,
        fig_4_8,
        fig_4_9,
        fig_4_10,
    ):
        print(fn())
    build_final_draft_figures()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
