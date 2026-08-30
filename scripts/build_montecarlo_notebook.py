"""Deterministically (re)build the Monte Carlo notebook (07).

Run with: ``uv run python scripts/build_montecarlo_notebook.py``

The notebook narrates DESCRIPTIVE resampling of the study's best -- and
rejected -- strategy. Figure and table names are frozen identifiers cited by
the thesis map (k01-k05, t01-t05 under ``montecarlo/``); the Spanish-era names
stay even though the prose is English, because renaming published artifact
identifiers breaks every reference for zero analytical gain.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import nbformat as nbf

CELLS: list = []


def md(text: str) -> None:
    CELLS.append(nbf.v4.new_markdown_cell(text.strip("\n")))


def code(src: str) -> None:
    CELLS.append(nbf.v4.new_code_cell(src.strip("\n")))


# Opening
md(
    r"""
# Monte Carlo: the best strategy inside the distribution of chance

> **ADDITIONAL NEGATIVE EVIDENCE — every block in this notebook is
> `DESCRIPTIVE`.** The strategy analysed, `volatility_breakout` on BTCUSDT
> (random_search), is **REJECTED**: raw p 0.345, study PBO 0.486, zero
> survivors under Holm or Benjamini-Hochberg — and it is, besides, the family
> that consumed the holdout. This analysis exists for two legitimate reasons:
> to demonstrate that the risk machinery works, and to quantify how little the
> study's best candidate is distinguishable from luck. Nothing below is a new
> hypothesis test or an operational use case, and nothing here can promote
> anything: the reserved partition is consumed.

**What question does this notebook answer?** How much of what the study's best
strategy shows in a backtest is what pure chance would deliver — in returns,
in sequencing, and in survival against funded-account evaluation rules,
including the published rules of real crypto prop firms and an explicit coin
flip baseline. **On what data?** The real out-of-sample ledgers of the ten
BTCUSDT/random_search seeds from the closed R3 study — Binance USDT-margined
perpetual futures, 2022-2025, the same fifteen test folds the study used. No
account, no live connection, no external trading data. **What will the reader
find?** The picture that summarises the thesis: the ten real runs falling
inside the distribution of a thousand versions of themselves with the one
thing removed that made them a "strategy" — knowing where the returns were.

**What it receives from the previous notebook.** 06 showed an economic
improvement with no predictive skill; this one generalises the suspicion: how
much positive result does chance produce entirely on its own? **What it hands
to the next.** To 08, the centrepiece of the complete visual argument.

Each resampling method is explained where it is used: what it assumes, what it
can detect and what it cannot. The honesty of the chapter lives in that fine
print.

### The local question

- **Q1.** At what percentile of its own null does the real strategy sit, and
  does anything survive rising costs, real prop-firm rules, or a comparison
  with a coin flip? (Feeds **RQ5** — robustness — and closes the argument of
  **RQ1**.)
"""
)

# Setup + contract
code(
    r"""
import os
import sys
from pathlib import Path

_root = Path.cwd()
while not (_root / "pyproject.toml").exists() and _root != _root.parent:
    _root = _root.parent
os.chdir(_root)
if str(_root / "src") not in sys.path:
    sys.path.insert(0, str(_root / "src"))
print(f"Repository root: {_root}")
"""
)

code(
    r"""
# Notebook contract: inputs and outputs declared and verified before anything
# is computed. The 01->08 chain validates itself by chaining these blocks.
import hashlib
import subprocess

NB_CONTRACT = {
    "notebook": "07_monte_carlo_nula",
    "inputs": [
        "artifacts/runs/r3_full_budget100_ga21/volatility_breakout/study_robustness.json",
    ],
    "outputs": {
        "figures": ["k01_bootstrap_distribuciones", "k02_permutacion_secuencia",
                     "k03_nula_con_la_estrategia_dentro", "k04_barrido_costes",
                     "k05_cuenta_fondeada"],
        "tables": ["t01_semillas_reales", "t02_bloque_acf", "t03_percentiles_nula",
                    "t04_barrido_costes", "t05_cuenta_fondeada"],
        "dirs": ["reports/figures/montecarlo", "reports/tables/montecarlo"],
    },
    # One seed governs every resample in the notebook.
    "seed": 42,
}

missing = [f for f in NB_CONTRACT["inputs"] if not Path(f).exists()]
if missing:
    raise FileNotFoundError(f"An upstream notebook no longer produces: {missing}")

INPUT_HASHES = {
    f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in NB_CONTRACT["inputs"]
}
REPO_COMMIT = subprocess.run(
    ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
).stdout.strip() or None

for k, v in INPUT_HASHES.items():
    print(f"input  {v[:16]}  {k}")
print(f"commit {REPO_COMMIT}")
"""
)

code(
    r"""
import json

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from IPython.display import display

from perp_lab.config import Paths, load_data_contract
from perp_lab.evaluation.montecarlo import (
    PROP_FIRM_PRESETS,
    bar_net_returns,
    breakeven_multiplier,
    coin_flip_pass_probability,
    cost_multiplier_sweep,
    iid_trade_bootstrap,
    null_circular_shifts,
    path_metrics,
    permutation_paths,
    prop_firm_pass_probability,
    stationary_bar_bootstrap,
    suggest_block_length,
)
from perp_lab.evaluation.study_robustness import load_oos_ledger, load_oos_trades
from perp_lab.reporting import ArtifactContext, apply_house_style, save_figure, save_table

apply_house_style()
PATHS = Paths()
FIG_DPI = 300
SEED = NB_CONTRACT["seed"]

ROB = json.loads(Path(NB_CONTRACT["inputs"][0]).read_text(encoding="utf-8"))
UNITS = {k: v for k, v in ROB["per_run"].items() if "BTCUSDT" in k and "random_search" in k}
print(f"BTCUSDT/random_search units: {len(UNITS)}")

_contract = load_data_contract("configs/data_contract.yaml")
ctx = ArtifactContext(
    notebook=NB_CONTRACT["notebook"],
    figures_dir=PATHS.reports_root / "figures" / "montecarlo",
    tables_dir=PATHS.reports_root / "tables" / "montecarlo",
    metadata_dir=PATHS.reports_root / "metadata" / "montecarlo",
    datasets=INPUT_HASHES,
    config={
        "seed": SEED,
        "code_commit_resolved": REPO_COMMIT,
        "data_contract_cutoff": str(_contract.cutoff_date),
        "family": "volatility_breakout (REJECTED)",
        "symbol": "BTCUSDT",
        "engine": "random_search",
        "n_units": len(UNITS),
    },
    period="development walk-forward out-of-sample; holdout never loaded",
    repo_root=".",
)


def show(fig, name, caption=""):
    save_figure(fig, name, ctx, caption=caption, dpi=FIG_DPI)
    display(fig)
    plt.close(fig)
"""
)

# 1. The ten real runs
md(
    r"""
## 1. The ten real runs, and which one narrates the detail — `DESCRIPTIVE`

We load each seed's concatenated out-of-sample ledger (the fifteen test folds,
contiguous and non-overlapping). For the sections that analyse a single series
we pick **the seed whose total return is the median of the ten** — a rule fixed
before looking at any distribution, precisely so we choose neither the
flattering best nor the dramatic worst. The central figure of section 3 shows
all ten.
"""
)

code(
    r"""
ledgers = {}
trades = {}
rows = []
for key, entry in sorted(UNITS.items()):
    run_dir = entry["run_dir"]
    led = load_oos_ledger(run_dir, "random_search")
    ledgers[key] = led
    tr = load_oos_trades(run_dir, "random_search")
    trades[key] = tr["net_return"].to_numpy().astype(float)
    m = path_metrics(bar_net_returns(led))
    rows.append({
        "seed": int(key.split("seed=")[1].split("|")[0]),
        "n_bars": led.height, "n_trades": tr.height,
        "exposure": float((led["position"].to_numpy() != 0).mean()),
        **m,
    })

T01 = pl.DataFrame(rows).sort("total_return")
save_table(T01, "t01_semillas_reales", ctx,
           caption="The ten real volatility_breakout BTCUSDT/random_search seeds on their "
                   "concatenated out-of-sample ledgers.")
display(T01)

median_row = T01.row(T01.height // 2, named=True)
MEDIAN_KEY = next(k for k in UNITS if f"seed={median_row['seed']}|" in k)
LED = ledgers[MEDIAN_KEY]
TRADES = trades[MEDIAN_KEY]
BAR_R = bar_net_returns(LED)
REAL = path_metrics(BAR_R)
print(f"\nmedian seed: {median_row['seed']} | return {REAL['total_return']:+.4f} | "
      f"trades {TRADES.size} | bars {BAR_R.size}")
"""
)

# 2. Bootstraps
md(
    r"""
## 2. Two bootstraps, and why both are needed — `DESCRIPTIVE`

The **IID trade bootstrap** resamples the bag of closed trades with
replacement. It assumes trades are exchangeable and independent; under that
assumption it answers "what paths could this collection of outcomes have
produced?", and it cannot see anything that depends on the real ordering or on
serial dependence between bars.

The **stationary block bootstrap** (Politis-Romano) resamples bars in blocks of
geometric length, preserving local autocorrelation. Its parameter is the mean
block length, and we do not pick it by eye: we derive it from the last lag
whose autocorrelation clears the 2/sqrt(n) noise band, bounded to [6, 168]
bars, and we publish the ACF so the choice is inspectable.
"""
)

code(
    r"""
block_info = suggest_block_length(BAR_R)
BLOCK = block_info["block_length"]
T02 = pl.DataFrame({
    "block_length": [BLOCK],
    "last_significant_lag": [block_info["last_significant_lag"]],
    "noise_band": [block_info["noise_band"]],
    "n_bars": [BAR_R.size],
})
save_table(T02, "t02_bloque_acf", ctx,
           caption="Stationary-bootstrap block length derived from the ACF of the median "
                   "seed's per-bar net returns.")
display(T02)

boot_iid = iid_trade_bootstrap(TRADES, n_resamples=1000, seed=SEED)
boot_bar = stationary_bar_bootstrap(BAR_R, block_length=BLOCK, n_resamples=1000, seed=SEED)
print(f"mean block: {BLOCK} bars | IID over {TRADES.size} trades | "
      f"stationary over {BAR_R.size} bars")
"""
)

code(
    r"""
# --- K01: bootstrap distributions with reality marked --------------------------
fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.6))
panels = [
    ("total_return", "compounded total return", REAL["total_return"]),
    ("sharpe", "per-observation Sharpe", REAL["sharpe"]),
    ("max_drawdown", "maximum drawdown", REAL["max_drawdown"]),
]
for ax, (key, label, real_v) in zip(axes, panels, strict=True):
    ax.hist(boot_iid[key], bins=40, density=True, histtype="step", lw=1.8,
            color="#0072B2", label="IID trades")
    ax.hist(boot_bar[key], bins=40, density=True, histtype="step", lw=1.8,
            ls="--", color="#D55E00", label="stationary blocks")
    ax.axvline(real_v, color="black", lw=2.2, label="real")
    ax.set_xlabel(label)
    ax.set_yticks([])
axes[0].legend(fontsize=8.5, loc="upper left")
fig.suptitle(
    f"One thousand resamples of the strategy's own record (median seed, {BLOCK}-bar blocks)",
    fontsize=12,
)
fig.tight_layout()
show(fig, "k01_bootstrap_distribuciones",
     caption="Bootstrap distributions of return, Sharpe and drawdown for the median seed "
             "under IID trade resampling and stationary block resampling, real value marked.")
"""
)

md(
    r"""
The important reading is not where the black line falls — it is **how wide the
distributions are**. The same bag of trades, recomposed a thousand times,
produces everything from severe losses to gains any signal seller would frame.
When the interval a strategy generates over itself is this wide, a single
backtest number is an anecdote, not a measurement.
"""
)

# 3. Permutation and the null
md(
    r"""
## 3. Isolating sequencing luck, then removing the signal entirely — `DESCRIPTIVE`

The **order permutation** shuffles the same trades without replacement. The
compounded total return is invariant by construction — reordering factors does
not change the product — so all the spread that appears in drawdown and
time-under-water is pure **sequencing luck**: the same wins and losses, in
another order, would have hurt more or less.

The **circular-shift null** goes further: it rotates the position series by a
random offset against the same bars, and re-charges costs and funding
identically. The rotation preserves exposure, trade count and turnover
exactly; the only thing it destroys is the alignment between the signal and
the returns it faced. If the real strategy cannot be told apart from a
thousand rotated versions of itself, what the backtest measured was the
market's distribution — not any skill of the rule.
"""
)

code(
    r"""
perm = permutation_paths(TRADES, n_resamples=1000, seed=SEED)

fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.8, 4.6))
axA.hist(perm["max_drawdown"], bins=40, color="#0072B2", edgecolor="white", lw=0.4)
axA.axvline(REAL["max_drawdown"], color="black", lw=2.2, label="real order")
axA.set_xlabel("maximum drawdown")
axA.set_ylabel("permutations")
axA.set_title("(a) Same outcome, other orders")
axA.legend(fontsize=9)

axB.hist(perm["time_under_water"], bins=40, color="#D55E00", hatch="///",
         edgecolor="white", lw=0.4)
axB.axvline(REAL["time_under_water"], color="black", lw=2.2, label="real order")
axB.set_xlabel("share of time below the prior peak")
axB.set_title("(b) Time under water")
axB.legend(fontsize=9)

fig.suptitle("Trade-order permutation: total return is identical in all one thousand; "
             "only the pain differs", fontsize=11.5)
fig.tight_layout()
show(fig, "k02_permutacion_secuencia",
     caption="Maximum drawdown and time under water across one thousand permutations of the "
             "median seed's trade order. Total return is invariant by construction.")
"""
)

code(
    r"""
# --- K03: THE figure -- the ten real runs inside their null --------------------
nulls = {}
for key, led in ledgers.items():
    nulls[key] = null_circular_shifts(led, n_shifts=1000, seed=SEED)

pooled_null = np.concatenate([n["null"]["total_return"] for n in nulls.values()])
reals = {k: n["real"]["total_return"] for k, n in nulls.items()}
pcts = {k: n["real_percentile"]["total_return"] for k, n in nulls.items()}

T03 = pl.DataFrame([
    {"seed": int(k.split("seed=")[1].split("|")[0]),
     "real_total_return": reals[k],
     "null_percentile": pcts[k],
     "exposure": nulls[k]["exposure_share"]}
    for k in sorted(nulls)
]).sort("null_percentile")
save_table(T03, "t03_percentiles_nula", ctx,
           caption="Percentile of each real seed inside its own circular-shift null "
                   "distribution (1,000 rotations per seed).")
display(T03)

fig, ax = plt.subplots(figsize=(11.6, 5.6))
ax.hist(pooled_null, bins=80, density=True, color="#BBBBBB", edgecolor="white", lw=0.3,
        label="null: 10 seeds x 1,000 position rotations")
for i, (_k, v) in enumerate(sorted(reals.items(), key=lambda kv: kv[1])):
    ax.axvline(v, color="#0072B2", lw=1.8,
               label="real strategy (10 seeds)" if i == 0 else None)
lo, hi = np.percentile(pooled_null, [2.5, 97.5])
ax.axvspan(lo, hi, color="#999999", alpha=0.18, label="central 95% of the null")
ax.set_xlabel("net total return over the out-of-sample period")
ax.set_yticks([])
ax.legend(fontsize=9, loc="upper left")
ax.set_title(
    "The study's best family, inside the distribution of its own signal-free versions",
    fontsize=12,
)
fig.tight_layout()
show(fig, "k03_nula_con_la_estrategia_dentro",
     caption="Circular-shift null distribution (positions rotated against the same bars, "
             "costs and funding re-charged) pooled over the ten seeds, with each seed's real "
             "return overlaid.")

inside = sum(1 for v in reals.values() if lo <= v <= hi)
print(f"real seeds inside the central 95% of the null: {inside}/10")
print(f"per-seed percentiles: {sorted(round(p, 3) for p in pcts.values())}")
"""
)

md(
    r"""
This is the picture that summarises the work. The blue lines — the ten real
runs of the study's best family — fall inside the grey band produced by their
own randomly rotated positions. No sophisticated statistics are needed to read
it, and all the sophisticated statistics of notebook 05 say what the eye sees:
**what the backtest measured is indistinguishable from the market's
distribution spread at random over the same exposure.**

The honest fine print: rotation preserves the exposure structure but not fine
conditional properties (a signal that only traded after specific events would
rotate onto bars without the event). For a family with a real edge that makes
this null *easy* to beat — which makes it the more informative that nobody
beats it.
"""
)

# 4. Costs
md(
    r"""
## 4. Cost sensitivity — `DESCRIPTIVE`

We re-charge the real path at multiples of the cost actually paid (fee plus
slippage), positions untouched — the same convention as the robustness
battery's 2x stress. The multiple where total return crosses zero says how
much room for error the study's cost assumption leaves.
"""
)

code(
    r"""
sweep = cost_multiplier_sweep(LED, multipliers=(0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0))
be = breakeven_multiplier(sweep)
save_table(sweep, "t04_barrido_costes", ctx,
           caption="Metrics of the median seed's real path re-charged at multiples of the "
                   "cost paid.")
display(sweep)

fig, ax = plt.subplots(figsize=(9.6, 5.0))
sw_sorted = sweep.sort("multiplier")
ax.plot(sw_sorted["multiplier"], sw_sorted["total_return"], marker="o", ms=7,
        lw=2.2, color="#0072B2")
ax.axhline(0, color="black", lw=1.2, ls="--")
if be is not None:
    ax.axvline(be, color="#D62728", lw=2.0, ls=":",
               label=f"crossing at {be:.2f}x the cost paid")
    ax.legend(fontsize=9.5)
ax.axvline(1.0, color="#999999", lw=1.4)
ax.annotate("study cost (1x)", xy=(1.0, ax.get_ylim()[0]), xytext=(6, 10),
            textcoords="offset points", fontsize=9, color="#555555", rotation=90)
ax.set_xlabel("multiple of the per-trade cost paid")
ax.set_ylabel("net total return")
ax.set_title("How much extra cost the result survives before it vanishes", fontsize=12)
fig.tight_layout()
show(fig, "k04_barrido_costes",
     caption="Total return of the median seed re-charging fee and slippage at multiples of "
             "the cost actually paid, positions untouched.")
"""
)

# 5. Funded accounts: real firm rules, and the coin flip
md(
    r"""
## 5. Funded-account rules: real firms, the strategy, and a coin flip — `DESCRIPTIVE`

Three clarifications before the numbers, because this section is easy to
misread.

**Where the rules come from.** From the published evaluation pages of real
crypto-perp prop firms, mapped on 2026-08-19 with their source URLs recorded
in code (`PROP_FIRM_PRESETS`): Breakout's 1-step Classic (10% target within
the published 9-12% range, 6% max drawdown, 3% daily loss) and HyroTrader's
2-step (10% per phase, 6% max loss, 4% daily). We model only the three
quantitative gates; the rules we do not model — consistency caps, mandatory
stop-losses, minimum trading days — would each make passing *harder*, so
every pass rate below is an optimistic upper bound. That is the safe direction
for a cautionary result.

**Where the trading data comes from.** From nowhere new: the strategy arm
resamples the strategy's own per-bar net returns (stationary bootstrap, block
length from section 2); the coin-flip arm keeps the real ledger's trade timing,
sizes and cost rate and flips a fair coin for the *direction* of every trade.
Same activity, zero information — the baseline any strategy has to beat.

**What the comparison can show.** Whether the strategy's pass rate is
distinguishable from the coin flip's. If it is not, an evaluation pass carries
no evidence of skill — which is the educational point of the platform's
funded-account simulator.
"""
)

code(
    r"""
rows = []
for firm, preset in PROP_FIRM_PRESETS.items():
    rules = preset["rules"]
    strat = prop_firm_pass_probability(
        BAR_R, rules=rules, block_length=BLOCK, n_paths=1000, seed=SEED
    )
    coin = coin_flip_pass_probability(LED, rules=rules, n_paths=1000, seed=SEED)
    for arm, res in (("strategy", strat), ("coin_flip", coin)):
        rows.append({
            "firm": firm, "arm": arm,
            "pass_phase1": res["pass_phase1"], "pass_both": res["pass_both"],
            "profit_target": rules.profit_target,
            "max_total_drawdown": rules.max_total_drawdown,
            "max_daily_loss": rules.max_daily_loss,
            "source": preset["source"],
        })
T05 = pl.DataFrame(rows)
save_table(T05, "t05_cuenta_fondeada", ctx,
           caption="Published prop-firm rules (mapped 2026-08-19, sources in code) applied to "
                   "bootstrap paths of the median seed and to coin flips with the same "
                   "timing and costs.")
display(T05)
"""
)

code(
    r"""
# --- K05: strategy vs coin flip under real firm rules --------------------------
firms = list(PROP_FIRM_PRESETS)
x = np.arange(len(firms))
width = 0.19

def col(arm, metric):
    return [
        T05.filter((pl.col("firm") == f) & (pl.col("arm") == arm))[metric][0]
        for f in firms
    ]

fig, ax = plt.subplots(figsize=(10.6, 5.2))
ax.bar(x - 1.5 * width, col("strategy", "pass_phase1"), width, color="#0072B2",
       label="strategy - passes phase 1")
ax.bar(x - 0.5 * width, col("coin_flip", "pass_phase1"), width, color="#0072B2",
       hatch="///", alpha=0.55, label="coin flip - passes phase 1")
ax.bar(x + 0.5 * width, col("strategy", "pass_both"), width, color="#D55E00",
       label="strategy - passes both")
ax.bar(x + 1.5 * width, col("coin_flip", "pass_both"), width, color="#D55E00",
       hatch="///", alpha=0.55, label="coin flip - passes both")
for xi, f in zip(x, firms, strict=True):
    for dx, arm, metric in ((-1.5, "strategy", "pass_phase1"),
                             (-0.5, "coin_flip", "pass_phase1"),
                             (0.5, "strategy", "pass_both"),
                             (1.5, "coin_flip", "pass_both")):
        v = T05.filter((pl.col("firm") == f) & (pl.col("arm") == arm))[metric][0]
        ax.annotate(f"{v:.0%}", xy=(xi + dx * width, v), xytext=(0, 4),
                    textcoords="offset points", ha="center", fontsize=8.5)
ax.set_xticks(x)
ax.set_xticklabels([f.replace("_", " ") for f in firms], fontsize=10)
ax.set_ylim(0, 1)
ax.set_ylabel("estimated pass probability (1,000 paths)")
ax.set_title("A rejected strategy vs a coin flip, under real published evaluation rules",
             fontsize=12)
ax.legend(fontsize=8.5, ncols=2)
ax.grid(axis="x", visible=False)
fig.tight_layout()
show(fig, "k05_cuenta_fondeada",
     caption="Pass probabilities under the mapped rules of two real crypto prop firms, for "
             "the median-seed strategy (bootstrap paths) and for a coin flip with the same "
             "trade timing and costs. Unmodelled qualitative rules would lower all bars.")

for f in firms:
    s1 = T05.filter((pl.col("firm") == f) & (pl.col("arm") == "strategy"))["pass_phase1"][0]
    c1 = T05.filter((pl.col("firm") == f) & (pl.col("arm") == "coin_flip"))["pass_phase1"][0]
    se = float(np.sqrt(s1 * (1 - s1) / 1000 + c1 * (1 - c1) / 1000))
    print(f"{f}: strategy-coin gap phase1 = {s1 - c1:+.3f} (binomial SE ~{se:.3f})")
"""
)

md(
    r"""
The reading, in one sentence: **under both firms' published rules, a certified
no-edge strategy and a literal coin flip pass evaluations at material rates,
and the gap between them is of the order of its own sampling error.** Whether
the strategy edges the coin or the coin edges the strategy on a given preset
is noise — which is precisely the point. An evaluation pass, at these rule
settings, is not evidence that the trader knows anything; it is a draw from a
distribution that hands out passes to randomness one time in several.

One scope note rather than an excuse: this notebook does not touch **risk
management overlays** — position sizing, volatility targeting, drawdown-scaled
exposure. Those change *which* paths a given signal produces, and evaluating
them properly belongs to future work with its own pre-registration; bolting
them on here would be a second search wearing a helmet.
"""
)

# Close
md(
    r"""
## 6. What this notebook establishes — and what would have contradicted it

Three things. First: the risk machinery — four resamplers, a cost sweep, a
funded-account simulator with real published rule presets and a coin-flip
baseline — works end to end on real ledgers, single-seeded and deterministic.
Second: the study's best family lives inside its own null; what notebook 05
established by inference is visible here in one image. Third: a strong
standalone backtest number is compatible with all of it being noise — the
section 2 distributions show how much variation the strategy produces over
itself without changing anything.

What would have contradicted this reading, and did not happen: the ten real
seeds clustered in the right tail of the null (high, consistent percentiles);
a return that survived 2-3x costs comfortably; or a strategy pass rate that
separated from the coin flip's by more than sampling error under either
firm's rules.

And what this notebook does **not** say: it does not say no strategy can pass
a funded evaluation — it says *this* one, the best of a study closed negative,
offers the probabilities shown above under rules mapped from real firms, and
that a coin flip with the same activity does about as well. Changing the rules
changes the numbers; it does not change which side of the null the strategy
lives on.

### From the local question to the thesis

| Local question | Feeds | How |
|---|---|---|
| Q1 (null percentile; survival vs costs, real rules, coin flip) | RQ5 and the close of RQ1 | additional negative evidence in visual form; k03 is the thesis-summary figure, k05 the platform's educational number |

---

**What this notebook leaves behind, and where it goes.** Figures `k01`-`k05`
and tables `t01`-`t05` under `reports/{figures,tables}/montecarlo/`. `k03` is
the central figure of chapter 6 and the Monte Carlo annex; `k04` feeds the
cost section of chapter 7; `k05` feeds the funded-account simulator's
discussion on the platform. Notebook 08 chains the key figures of 01-07 into
the complete argument, in one reading.
"""
)


def _write() -> None:
    nb = nbf.v4.new_notebook()
    nb["cells"] = CELLS
    nb["metadata"] = {
        "language_info": {"name": "python"},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    }
    out = Path("notebooks/07_monte_carlo_nula.ipynb")
    out.write_text(nbf.writes(nb), encoding="utf-8")
    subprocess.run(["ruff", "check", "--fix", "--quiet", str(out)], check=False)
    subprocess.run(["ruff", "format", "--quiet", str(out)], check=False)
    print(f"Wrote {out} with {len(CELLS)} cells (ruff-formatted).")


if __name__ == "__main__":
    _write()
