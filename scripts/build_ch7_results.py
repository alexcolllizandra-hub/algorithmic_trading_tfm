"""Build the chapter-7 export package (tables + figures) from closed artifacts.

Run with: ``uv run python scripts/build_ch7_results.py``

Reads ONLY archived OOS artifacts (study_robustness.json, fold-winner ledgers,
fold test-equity parquets, pilot gate reports). Executes no searches, no
training, no significance tests, and never touches the holdout. Deterministic:
no timestamps, no RNG.

Outputs under ``reports/thesis/chapter_07/``:
  ch7_results_units.csv/.md      one row per family x asset x engine x seed (full studies)
  ch7_results_pilots_s1b.csv     S1-B pilot (BTC, 1 seed, budget 25) per family x engine
  ch7_results_pilots_s2b.csv     S2-B pilot (2 assets x 3 seeds) per family x asset x seed x engine
  ch7_criteria.csv               pre-registered criteria pass counts per cell (full studies)
  ch7_seed_dispersion.csv/.md    dispersion across seeds (RS engine), aggregation stated per column
  ch7_rounds_summary.csv/.md     round -> hypothesis -> main result -> closure reason
  fig_7_1 .. fig_7_6             PNG 300 dpi + PDF
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# Freeze the PDF CreationDate so the .pdf twins are byte-reproducible.
os.environ.setdefault("SOURCE_DATE_EPOCH", "946684800")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from perp_lab.reporting import apply_house_style

apply_house_style()

OUT = Path("reports/thesis/chapter_07")
OUT.mkdir(parents=True, exist_ok=True)

SYMBOLS = ("BTCUSDT", "ETHUSDT")
ENGINES = ("random_search", "genetic_algorithm")

CRT_FAMILIES = [
    "pdl_reclaim_long",
    "pdh_reclaim_short",
    "crt_htf_range_reversal",
    "session_liquidity_sweep",
    "session_range_rotation",
    "opening_range_breakout_retest",
    "failed_breakout_reversal",
    "double_sweep_reversal",
    "crt_three_candle_model",
]
STUDIES: list[tuple[str, str, Path, int]] = [
    ("R2", "momentum", Path("artifacts/runs/multiseed_momentum_r2_clean_v2"), 300),
    *[
        ("R3", f, Path("artifacts/runs/r3_full_budget100_ga21") / f, 100)
        for f in (
            "breakout",
            "mean_reversion",
            "volatility_breakout",
            "funding",
            "BTC_ETH_confirmation",
        )
    ],
    *[
        ("CRT_INTRADAY_V1", f, Path("artifacts/runs/crt_v1_budget100") / f, 100)
        for f in CRT_FAMILIES
    ],
    ("S3", "macro_event_brake", Path("artifacts/runs/multiseed_20260826T165028Z_0d3a92"), 100),
]


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _md_table(df: pl.DataFrame, floatfmt: str = ".3f") -> str:
    def cell(v: object) -> str:
        if isinstance(v, float):
            return format(v, floatfmt)
        return "" if v is None else str(v)

    header = "| " + " | ".join(df.columns) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    lines = ["| " + " | ".join(cell(v) for v in row) + " |" for row in df.rows()]
    return "\n".join([header, sep, *lines])


def _mean_fold_sharpe(run_dir: Path, engine: str) -> tuple[float | None, int]:
    """Mean across folds of the frozen winner's test Sharpe (annualised, per fold)."""
    p = run_dir / f"{engine}_fold_winners.json"
    if not p.exists():
        return None, 0
    vals = [
        w["test_metrics"]["sharpe"]
        for w in _read_json(p)
        if w.get("test_metrics") and w["test_metrics"].get("sharpe") is not None
    ]
    return (float(np.mean(vals)) if vals else None), len(vals)


# --------------------------------------------------------------------------- #
# 1. Unit-level results for the full studies
# --------------------------------------------------------------------------- #
unit_rows: list[dict] = []
crit_rows: list[dict] = []
for round_, fam, sdir, budget in STUDIES:
    rob = _read_json(sdir / "study_robustness.json")
    promo = rob.get("r3_promotion")
    if promo is not None:
        for sym in SYMBOLS:
            blk = promo["by_symbol"][sym]
            for crit, d in blk["promotion"].items():
                crit_rows.append(
                    {
                        "round": round_,
                        "family": fam,
                        "symbol": sym,
                        "criterion": crit,
                        "n_pass": int(d["n_pass"]),
                        "required": int(d["required"]),
                        "of_seeds": int(blk["n_seeds"]),
                        "met": bool(d["pass"]),
                        "verdict": promo["verdict"],
                    }
                )
    else:
        # R2 predates the r3_promotion block: its robustness artifact carries
        # only the four per-seed counts. The remaining two criteria are "not
        # computed" in that artifact (the closure dashboard evaluates them).
        crit_map = {
            "positive_total_return": "n_positive",
            "bootstrap_sharpe_ci_excludes_zero": "n_bootstrap_ci_excludes_zero",
            "survives_double_costs": "n_survive_double_costs",
            "beats_buy_and_hold": "n_beat_buy_and_hold",
        }
        for sym in SYMBOLS:
            blk = rob["by_symbol_and_engine"][f"{sym}|random_search"]
            for crit, key in crit_map.items():
                crit_rows.append(
                    {
                        "round": round_,
                        "family": fam,
                        "symbol": sym,
                        "criterion": crit,
                        "n_pass": int(blk[key]),
                        "required": 6,
                        "of_seeds": int(blk["n_seeds"]),
                        "met": int(blk[key]) >= 6,
                        "verdict": "REJECTED",
                    }
                )
    for key, v in rob["per_run"].items():
        sym, seed_s, engine = key.split("|")
        s, bh, t = v["strategy"], v["buy_and_hold"], v["tests"]
        mfs, nf = _mean_fold_sharpe(Path(v["run_dir"]), engine)
        unit_rows.append(
            {
                "round": round_,
                "family": fam,
                "symbol": sym,
                "engine": engine,
                "seed": int(seed_s.removeprefix("seed=")),
                "oos_start": str(v["oos_start"]),
                "oos_end": str(v["oos_end"]),
                "n_oos_bars": int(v["n_bars"]),
                "n_folds": 15,
                "budget_per_fold_per_engine": budget,
                "unique_evals_this_unit_engine": budget * 15,
                "total_return_net": float(s["total_return"]),
                "max_drawdown": float(s["max_drawdown"]),
                "n_trades": int(s["n_trades"]),
                "sharpe_concat_ann": float(s["sharpe"]),
                "mean_fold_test_sharpe": mfs,
                "n_folds_with_winner": nf,
                "bh_total_return": float(bh["total_return"]),
                "bh_sharpe_ann": float(bh["sharpe"]),
                "bh_max_drawdown": float(bh["max_drawdown"]),
                "pass_positive_return": bool(t["positive_total_return"]),
                "pass_beats_bh": bool(t["beats_buy_and_hold"]),
                "pass_double_costs": bool(t["survives_double_costs"]),
                "pass_bootstrap_ci": bool(t["bootstrap_sharpe_ci_excludes_zero"]),
                "run_dir": str(v["run_dir"]),
            }
        )

UNITS = pl.DataFrame(unit_rows).sort("round", "family", "symbol", "engine", "seed")
UNITS.write_csv(OUT / "ch7_results_units.csv")
CRIT = pl.DataFrame(crit_rows).sort("round", "family", "symbol", "criterion")
CRIT.write_csv(OUT / "ch7_criteria.csv")

# Markdown digest of the unit table: RS engine, per family x symbol.
DISP = (
    UNITS.filter(pl.col("engine") == "random_search")
    .group_by("round", "family", "symbol", maintain_order=True)
    .agg(
        pl.len().alias("n_seeds"),
        pl.col("sharpe_concat_ann").mean().alias("sharpe_concat_ann_mean_across_seeds"),
        pl.col("sharpe_concat_ann").std().alias("sharpe_concat_ann_sd_across_seeds"),
        pl.col("sharpe_concat_ann").min().alias("sharpe_concat_ann_min"),
        pl.col("sharpe_concat_ann").max().alias("sharpe_concat_ann_max"),
        pl.col("mean_fold_test_sharpe").mean().alias("mean_fold_test_sharpe_mean_across_seeds"),
        pl.col("total_return_net").mean().alias("total_return_net_mean_across_seeds"),
        (pl.col("total_return_net") > 0).sum().alias("seeds_positive_return"),
        pl.col("bh_total_return").first().alias("bh_total_return_same_window"),
        pl.col("n_trades").mean().alias("n_trades_mean_across_seeds"),
    )
    .sort("round", "family", "symbol")
)
DISP.write_csv(OUT / "ch7_seed_dispersion.csv")

with (OUT / "ch7_seed_dispersion.md").open("w", encoding="utf-8") as fh:
    fh.write(
        "# Seed dispersion per family-asset cell (RS engine, full studies)\n\n"
        "Aggregations, stated exactly: `sharpe_concat_ann_*` summarise, across seeds, "
        "the annualised Sharpe of each seed's concatenated OOS test series "
        "(`study_robustness.json` -> `per_run.strategy.sharpe`); "
        "`mean_fold_test_sharpe_mean_across_seeds` averages, across seeds, each seed's "
        "mean of the 15 frozen-winner fold-test Sharpes (`*_fold_winners.json`). "
        "The two aggregations differ by construction (bars-weighted vs folds-weighted); "
        "never compare one against the other. Ranges are dispersion across seeds, "
        "not confidence intervals. Benchmark = buy & hold over the same OOS window.\n\n"
    )
    fh.write(_md_table(DISP))
    fh.write("\n")

with (OUT / "ch7_results_units.md").open("w", encoding="utf-8") as fh:
    fh.write(
        "# Unit-level results, full studies (one row per family x asset x engine x seed)\n\n"
        "Digest of `ch7_results_units.csv` (RS engine only; the CSV carries both "
        "engines and all columns). `sharpe_concat_ann` = annualised Sharpe of the "
        "concatenated OOS test series; `mean_fold_test_sharpe` = mean across folds of "
        "the frozen winner's fold-test Sharpe. Benchmark columns are buy & hold over "
        "the same OOS bars.\n\n"
    )
    digest = UNITS.filter(pl.col("engine") == "random_search").select(
        "round",
        "family",
        "symbol",
        "seed",
        "total_return_net",
        "max_drawdown",
        "n_trades",
        "sharpe_concat_ann",
        "mean_fold_test_sharpe",
        "bh_total_return",
        "pass_positive_return",
        "pass_bootstrap_ci",
    )
    fh.write(_md_table(digest))
    fh.write("\n")

# --------------------------------------------------------------------------- #
# 2. Pilot tables (their own contracts; not the 10-seed rules)
# --------------------------------------------------------------------------- #
s1b = _read_json(Path("reports/gate_s1b/s1b_pilot_report.json"))
s1_rows = []
for fam, famblk in sorted(s1b["per_family"].items()):
    for engine in ENGINES:
        e = famblk["engines"][engine]
        s1_rows.append(
            {
                "round": "S1-B (pilot)",
                "family": fam,
                "symbol": "BTCUSDT",
                "n_seeds": 1,
                "engine": engine,
                "budget_per_fold": e["budget_per_fold"],
                "n_folds": e["n_folds"],
                "unique_evaluations": e["n_unique_evaluations"],
                "oos_bars": e["oos_bars"],
                "median_fold_test_sharpe": e["median_test_sharpe"],
                "folds_positive_return": e["folds_positive_return"],
                "folds_with_trades": e["folds_with_trades"],
                "total_test_trades": e["total_test_trades"],
                "oos_mean_net_return_per_bar": e["oos_mean_net_return"],
                "oos_bootstrap_p_value": e["oos_bootstrap_p_value"],
                "mechanically_viable": e["mechanically_viable"],
                "run_dir": e["run_dir"],
            }
        )
S1B = pl.DataFrame(s1_rows).sort("family", "engine")
S1B.write_csv(OUT / "ch7_results_pilots_s1b.csv")

s2b = _read_json(Path("reports/gate_s2b/s2b_pilot_report.json"))
s2_rows = []
for arm in s2b["arms"]:
    for engine in ENGINES:
        e = arm["engines"][engine]
        s2_rows.append(
            {
                "round": "S2-B (pilot)",
                "family": arm["family"],
                "symbol": arm["symbol"],
                "seed": arm["seed"],
                "engine": engine,
                "budget_per_fold": e["budget_per_fold"],
                "n_folds": e["n_folds"],
                "unique_evaluations": e["n_unique_evaluations"],
                "oos_bars": e["oos_bars"],
                "compounded_oos_return": e.get("compounded_oos_return"),
                "median_fold_test_sharpe": e["median_test_sharpe"],
                "folds_positive_return": e["folds_positive_return"],
                "folds_with_trades": e["folds_with_trades"],
                "total_test_trades": e["total_test_trades"],
                "oos_bootstrap_p_value": e["oos_bootstrap_p_value"],
                "mechanically_viable": e["mechanically_viable"],
                "run_dir": e["run_dir"],
            }
        )
S2B = pl.DataFrame(s2_rows).sort("family", "symbol", "seed", "engine")
S2B.write_csv(OUT / "ch7_results_pilots_s2b.csv")

# --------------------------------------------------------------------------- #
# 3. Round summary: hypothesis -> main result -> closure reason
# --------------------------------------------------------------------------- #
ROUNDS = pl.DataFrame(
    [
        {
            "round": "R1 (superseded)",
            "hypothesis": "Baseline momentum on BTC/ETH 1h has positive net OOS performance",
            "main_result": "INVALID as evidence: outer-fold contamination in candidate search "
            "(later folds could influence earlier selections)",
            "closure": "Superseded by R2 under ADR 0011/0012/0013; contaminated numbers never cited",
        },
        {
            "round": "R2 (full study)",
            "hypothesis": "Momentum, searched independently per outer fold, survives realistic costs",
            "main_result": "0/10 seeds positive on either asset (RS); mean concatenated Sharpe "
            "negative on both",
            "closure": "Family rejected under the pre-registered C1-C6 majority rules",
        },
        {
            "round": "R3 (full study, 5 families)",
            "hypothesis": "At least one of five diversified price/funding families has an edge",
            "main_result": "0/10 promotions; volatility_breakout BTC is the closest cell "
            "(6/10 seeds positive) but fails the bootstrap-CI criterion",
            "closure": "All five rejected; feeds the 13-family closure",
        },
        {
            "round": "S1-B (pilot: BTC, 1 seed, budget 25)",
            "hypothesis": "Four cheaper structural families are mechanically viable and worth a "
            "full study",
            "main_result": "All four mechanically viable; no performance case (best raw "
            "bootstrap p = 0.06 for funding_reversal); RC p = 0.9955, SPA p = 1.0",
            "closure": "Full S1-C study configs written but NOT executed (human decision "
            "pending); pilots entered the closure as tested hypotheses",
        },
        {
            "round": "S2-B (pilot: 2 assets, 3 seeds, budget 25)",
            "hypothesis": "Three microstructure/flow families justify a full study",
            "main_result": "No family reaches the pre-registered partial-signal bar "
            "(majority of seeds positive with >=5 trades across >1 fold)",
            "closure": "No promotion to full study; pilots entered the closure",
        },
        {
            "round": "CRT_INTRADAY_V1 (full study, 9 families)",
            "hypothesis": "Intraday liquidity patterns (prior-day level reclaims, session "
            "sweeps, opening ranges) carry structure that survives costs",
            "main_result": "0/18 cells promoted; pdl_reclaim_long BTC positive on 10/10 seeds "
            "but 0/10 bootstrap CIs exclude zero and profits concentrate in few "
            "trades (2/10 survive drop-top-trades)",
            "closure": "All rejected under the same C1-C6 contract; outside the 13-family "
            "closure, extended corrections not computed",
        },
        {
            "round": "S3 (full study, news overlay)",
            "hypothesis": "Suspending the R2 momentum carrier around scheduled US macro "
            "releases improves it (event windows carry 2.5-3.2x volatility)",
            "main_result": "0/10 seeds positive; seed distribution of test-fold Sharpe shifts "
            "BELOW the carrier on both assets (BTC -0.71 -> -0.99, "
            "ETH -0.49 -> -0.68; not seed-paired by design)",
            "closure": "Hypothesis falsified as pre-registered (N := N+1); outside the closure",
        },
    ]
)
ROUNDS.write_csv(OUT / "ch7_rounds_summary.csv")
with (OUT / "ch7_rounds_summary.md").open("w", encoding="utf-8") as fh:
    fh.write("# Rounds at a glance: hypothesis -> main result -> closure\n\n")
    fh.write(_md_table(ROUNDS))
    fh.write(
        "\n\nStudy-level Holm/BH/DSR/PBO exist for the 13-family closure only; "
        "for CRT and S3 they are **not computed** (chapter 6, MANIFEST scope note).\n"
    )

# --------------------------------------------------------------------------- #
# 4. Figures
# --------------------------------------------------------------------------- #
FIG_DPI = 300


def _save(fig, name: str) -> None:
    fig.savefig(OUT / f"{name}.png", dpi=FIG_DPI, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"figure {name}")


def _concat_ledger(run_dir: Path, engine: str) -> pl.DataFrame:
    frames = []
    for f in range(15):
        p = run_dir / f"{engine}_fold{f}_test_equity.parquet"
        if p.exists():
            frames.append(pl.read_parquet(p).select("open_time", "net_return", "oo_return"))
    return pl.concat(frames).sort("open_time")


def _equity_curves(
    round_: str, family: str, symbol: str
) -> tuple[list[tuple[int, np.ndarray, np.ndarray]], np.ndarray, np.ndarray]:
    """Per-seed cumulative equity (RS engine) plus buy & hold on the union of bars."""
    sub = UNITS.filter(
        (pl.col("round") == round_)
        & (pl.col("family") == family)
        & (pl.col("symbol") == symbol)
        & (pl.col("engine") == "random_search")
    ).sort("seed")
    curves = []
    bench_t, bench_v = None, None
    for row in sub.iter_rows(named=True):
        led = _concat_ledger(Path(row["run_dir"]), "random_search")
        t = led["open_time"].to_numpy()
        eq = np.cumprod(1.0 + led["net_return"].to_numpy())
        curves.append((row["seed"], t, eq))
        if bench_t is None or t.size > bench_t.size:
            bench_t = t
            bench_v = np.cumprod(1.0 + led["oo_return"].to_numpy())
    return curves, bench_t, bench_v


SEED_NOTE = "all 10 seeds drawn (no selection); spread = dispersion across seeds, not a CI"

# --- fig 7.1: R2 momentum, OOS equity vs buy & hold --------------------------
fig, axes = plt.subplots(1, 2, figsize=(13.4, 5.2), sharey=False)
for ax, sym in zip(axes, SYMBOLS, strict=True):
    curves, bt, bv = _equity_curves("R2", "momentum", sym)
    for i, (_seed, t, eq) in enumerate(curves):
        ax.plot(
            t,
            eq,
            lw=0.9,
            alpha=0.65,
            color="#0072B2",
            label="strategy, one curve per seed" if i == 0 else None,
        )
    ax.plot(bt, bv, lw=1.8, color="#555555", ls="--", label="buy & hold (same OOS bars)")
    ax.axhline(1.0, color="black", lw=0.8)
    ax.set_title(f"{sym} - {len(curves)} RS seeds")
    ax.set_ylabel("growth of 1 unit (net of costs)")
    ax.legend(fontsize=8.5, loc="upper left")
fig.suptitle(f"R2 momentum: concatenated OOS test equity vs benchmark ({SEED_NOTE})", fontsize=12)
fig.autofmt_xdate()
fig.tight_layout()
_save(fig, "fig_7_1_r2_oos_equity")

# --- fig 7.2: R3, five families compared -------------------------------------
R3_FAMS = ["breakout", "mean_reversion", "volatility_breakout", "funding", "BTC_ETH_confirmation"]
fig, axes = plt.subplots(1, 2, figsize=(13.4, 5.2), sharey=True)
for ax, sym in zip(axes, SYMBOLS, strict=True):
    for i, fam in enumerate(R3_FAMS):
        vals = UNITS.filter(
            (pl.col("round") == "R3")
            & (pl.col("family") == fam)
            & (pl.col("symbol") == sym)
            & (pl.col("engine") == "random_search")
        )["sharpe_concat_ann"].to_numpy()
        offs = np.linspace(-0.18, 0.18, vals.size)
        ax.scatter(np.full(vals.size, i) + offs, vals, s=26, alpha=0.8, color="#0072B2")
        ax.scatter(
            [i],
            [vals.mean()],
            s=90,
            marker="_",
            color="#D62728",
            lw=2.4,
            label="mean across seeds" if i == 0 else None,
        )
    ax.axhline(0, color="black", lw=1.1)
    ax.set_xticks(range(len(R3_FAMS)))
    ax.set_xticklabels(R3_FAMS, rotation=25, ha="right", fontsize=8.5)
    ax.set_title(sym)
axes[0].set_ylabel("annualised Sharpe, concatenated OOS series (RS)")
axes[0].legend(fontsize=8.5, loc="upper right")
fig.suptitle(f"R3: the five families, all seeds shown ({SEED_NOTE})", fontsize=12)
fig.tight_layout()
_save(fig, "fig_7_2_r3_families")

# --- fig 7.3: volatility_breakout BTC, the partial signal --------------------
fig, (axA, axB) = plt.subplots(1, 2, figsize=(13.4, 5.2), gridspec_kw={"width_ratios": [1.0, 1.35]})
vb = CRIT.filter(
    (pl.col("family") == "volatility_breakout") & (pl.col("symbol") == "BTCUSDT")
).sort("criterion")
labels = vb["criterion"].to_list()
npass = vb["n_pass"].to_numpy()
req = vb["required"].to_numpy()
yy = np.arange(len(labels))
axA.barh(yy, npass, height=0.55, color="#0072B2", label="seeds passing (of 10)")
for j, r in enumerate(req):
    axA.plot(
        [r, r],
        [j - 0.32, j + 0.32],
        color="#D62728",
        lw=2.2,
        label="required majority (6)" if j == 0 else None,
    )
axA.set_yticks(yy)
axA.set_yticklabels([label.replace("_", " ") for label in labels], fontsize=8.5)
axA.invert_yaxis()
axA.set_xlim(0, 10)
axA.set_xlabel("seeds passing")
axA.set_title("(a) Criteria: where promotion fails")
axA.legend(fontsize=8.5, loc="lower right")
axA.grid(axis="y", visible=False)

curves, bt, bv = _equity_curves("R3", "volatility_breakout", "BTCUSDT")
for i, (_seed, t, eq) in enumerate(curves):
    axB.plot(
        t,
        eq,
        lw=0.9,
        alpha=0.7,
        color="#0072B2",
        label="strategy, one curve per seed" if i == 0 else None,
    )
axB.plot(bt, bv, lw=1.8, color="#555555", ls="--", label="buy & hold")
axB.axhline(1.0, color="black", lw=0.8)
axB.set_ylabel("growth of 1 unit")
axB.set_title("(b) OOS equity, all 10 RS seeds")
axB.legend(fontsize=8.5, loc="upper left")
fig.suptitle(f"volatility_breakout on BTC: the study's closest cell ({SEED_NOTE})", fontsize=12)
fig.autofmt_xdate()
fig.tight_layout()
_save(fig, "fig_7_3_volbreakout_partial_signal")

# --- fig 7.4: CRT complementary view -----------------------------------------
fig, (axA, axB) = plt.subplots(1, 2, figsize=(13.6, 5.6), gridspec_kw={"width_ratios": [1.25, 1.0]})
curves, bt, bv = _equity_curves("CRT_INTRADAY_V1", "pdl_reclaim_long", "BTCUSDT")
for i, (_seed, t, eq) in enumerate(curves):
    axA.plot(
        t,
        eq,
        lw=0.9,
        alpha=0.7,
        color="#0072B2",
        label="strategy, one curve per seed" if i == 0 else None,
    )
axA.plot(bt, bv, lw=1.8, color="#555555", ls="--", label="buy & hold")
axA.axhline(1.0, color="black", lw=0.8)
axA.set_ylabel("growth of 1 unit")
axA.set_title(
    "(a) pdl_reclaim_long BTC: 10/10 seeds end positive,\nyet no bootstrap CI excludes zero"
)
axA.legend(fontsize=8.5, loc="upper left")

crit_keys = [
    "positive_total_return",
    "bootstrap_sharpe_ci_excludes_zero",
    "survives_double_costs",
    "beats_buy_and_hold",
    "survives_drop_top_trades",
    "not_confined_to_one_fold",
]
crit_labels = [
    "positive\nnet return",
    "bootstrap CI\nexcludes 0",
    "survives\n2x costs",
    "beats\nbuy & hold",
    "survives drop\ntop trades",
    "not confined\nto one fold",
]
eth = (
    CRIT.filter((pl.col("round") == "CRT_INTRADAY_V1") & (pl.col("symbol") == "ETHUSDT"))
    .pivot(index="family", on="criterion", values="n_pass")
    .sort("family")
)
fams_e = eth["family"].to_list()
Me = np.array([[eth.filter(pl.col("family") == f)[k][0] / 10 for k in crit_keys] for f in fams_e])
im = axB.imshow(Me, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
for i in range(len(fams_e)):
    for j in range(len(crit_keys)):
        axB.text(j, i, f"{round(Me[i, j] * 10)}/10", ha="center", va="center", fontsize=7.5)
axB.set_xticks(range(len(crit_keys)))
axB.set_xticklabels(crit_labels, fontsize=7.5)
axB.set_yticks(range(len(fams_e)))
axB.set_yticklabels(fams_e, fontsize=8)
axB.grid(visible=False)
axB.set_title("(b) ETHUSDT criteria map\n(BTC map: figure j05, chapter 6)")
fig.suptitle(f"CRT_INTRADAY_V1, complementary views ({SEED_NOTE})", fontsize=12)
fig.tight_layout()
_save(fig, "fig_7_4_crt_complementary")

# --- fig 7.5: S3 overlay vs carrier, seed distributions ----------------------
fig, ax = plt.subplots(figsize=(9.6, 5.4))
arms = [
    ("R2", "momentum", "carrier: R2 momentum", "#0072B2"),
    ("S3", "macro_event_brake", "overlay: macro_event_brake", "#D62728"),
]
for i, sym in enumerate(SYMBOLS):
    for j, (round_, fam, label, color) in enumerate(arms):
        vals = UNITS.filter(
            (pl.col("round") == round_)
            & (pl.col("family") == fam)
            & (pl.col("symbol") == sym)
            & (pl.col("engine") == "random_search")
        )["mean_fold_test_sharpe"].to_numpy()
        x = i + (j - 0.5) * 0.32
        offs = np.linspace(-0.06, 0.06, vals.size)
        ax.scatter(
            np.full(vals.size, x) + offs,
            vals,
            s=30,
            alpha=0.8,
            color=color,
            label=label if i == 0 else None,
        )
        ax.scatter([x], [np.nanmean(vals)], s=140, marker="_", color=color, lw=2.6)
ax.axhline(0, color="black", lw=1.1)
ax.set_xticks(range(len(SYMBOLS)))
ax.set_xticklabels(SYMBOLS)
ax.set_ylabel("test-fold Sharpe (per seed: mean across the 15 folds; RS)")
ax.set_title(
    "Gate S3: seed distributions of overlay vs carrier - "
    "NOT seed-paired\n(reduced carrier grid; budget shared with gate parameters); "
    "all 10 seeds per arm shown, dash = mean"
)
ax.legend(fontsize=9, loc="upper right", frameon=True, framealpha=0.95)
fig.tight_layout()
_save(fig, "fig_7_5_s3_seed_distributions")

# --- fig 7.6: synthesis across full-study families ---------------------------
fig, axes = plt.subplots(1, 2, figsize=(13.6, 7.2), sharey=True)
ROUND_COLOR = {"R2": "#0072B2", "R3": "#009E73", "CRT_INTRADAY_V1": "#D55E00", "S3": "#CC79A7"}
fam_order = (
    UNITS.filter(pl.col("engine") == "random_search")
    .group_by("round", "family", maintain_order=True)
    .agg(pl.len())
    .sort("round", "family")
)
fams_all = fam_order.select("round", "family").rows()
for ax, sym in zip(axes, SYMBOLS, strict=True):
    for i, (round_, fam) in enumerate(fams_all):
        vals = UNITS.filter(
            (pl.col("round") == round_)
            & (pl.col("family") == fam)
            & (pl.col("symbol") == sym)
            & (pl.col("engine") == "random_search")
        )["sharpe_concat_ann"].to_numpy()
        c = ROUND_COLOR[round_]
        ax.plot([vals.min(), vals.max()], [i, i], color=c, lw=1.6, alpha=0.65)
        ax.scatter([vals.mean()], [i], s=52, color=c, zorder=3)
    ax.axvline(0, color="black", lw=1.1)
    ax.set_title(sym)
    ax.set_xlabel(
        "annualised Sharpe, concatenated OOS (RS);\ndot = mean, line = min-max across 10 seeds"
    )
axes[0].set_yticks(range(len(fams_all)))
axes[0].set_yticklabels([f"{fam}  [{r}]" for r, fam in fams_all], fontsize=8.5)
axes[0].invert_yaxis()
handles = [
    plt.Line2D([0], [0], marker="o", ls="-", color=c, label=r) for r, c in ROUND_COLOR.items()
]
axes[0].legend(
    handles=handles, fontsize=8.5, loc="lower left", title="round", frameon=True, framealpha=0.95
)
fig.suptitle(
    "All sixteen full-study families (S1/S2 pilots excluded: different design "
    "and seed count; see pilot tables)",
    fontsize=12,
)
fig.tight_layout()
_save(fig, "fig_7_6_rounds_synthesis")

print(
    f"\nUnits: {UNITS.height} rows | criteria: {CRIT.height} | "
    f"S1-B: {S1B.height} | S2-B: {S2B.height}"
)
print(f"Written under {OUT}")
