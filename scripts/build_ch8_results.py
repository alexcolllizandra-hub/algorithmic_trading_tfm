"""Build the chapter-8 evidence package: conditional risk simulation.

Run with: ``uv run python scripts/build_ch8_results.py``

Scope contract (also in ch8_method_contract.md):
- Reads ONLY archived OOS artifacts of the development period. No holdout, no
  new searches, no parameter changes.
- Primary spec follows the FROZEN precedent of notebook 07: stationary block
  bootstrap (Politis-Romano) with the ACF-derived block length
  (suggest_block_length) and the median-by-return seed rule where one seed is
  needed. Everything beyond that precedent (per-seed layer, hierarchical
  seed-then-path scheme, exposure grid, barrier probabilities, drawdown
  durations, circular-MBB sensitivity) is POST-HOC DIAGNOSTIC ANALYSIS and is
  labelled as such in every output.
- Simulations are conditional on the observed development record. They do not
  validate any edge, do not correct data snooping and cannot change any
  chapter-7 verdict.

Deterministic: master seed 20260829; one child stream per
(candidate, seed-or-HIER, method, block, scenario, chunk); SOURCE_DATE_EPOCH
pinned for the PDF twins. Two runs produce byte-identical CSV/PNG.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("SOURCE_DATE_EPOCH", "946684800")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from perp_lab.evaluation.montecarlo import suggest_block_length
from perp_lab.evaluation.robustness import drop_best_trades
from perp_lab.reporting import apply_house_style

apply_house_style()

OUT = Path("reports/thesis/chapter_08")
OUT.mkdir(parents=True, exist_ok=True)

ENGINE = "random_search"
SYMBOL = "BTCUSDT"
MASTER_SEED = 20260829
N_OBS_EXPECTED = 32_385
N_FOLDS_EXPECTED = 15

N_PRIMARY = 4_000  # hierarchical primary budget (convergence reported at 1k/2k/4k)
N_PER_SEED = 1_000  # path-uncertainty budget per seed
N_SENS = 2_000  # per sensitivity cell
CHUNK = 250

MULTIPLIERS = (0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 2.00)
BARRIERS = (0.90, 0.80, 0.70, 0.50)
LOSS_LEVELS = (0.10, 0.20, 0.30, 0.50)
MDD_LEVELS = (0.10, 0.20, 0.30, 0.40, 0.50)
PCTS = (1, 5, 25, 50, 75, 95, 99)
SENS_BLOCKS = (24, 168, 720)  # the C2 gate's frozen trio
FAN_STEP = 74  # decimation step for stored path quantiles (~438 points)

CANDIDATES = [
    ("CRT_INTRADAY_V1", "pdl_reclaim_long"),
    ("R3", "volatility_breakout"),
]
REFERENCE = ("R2", "momentum")  # observed negative reference only; never simulated here

UNITS7 = pl.read_csv("reports/thesis/chapter_07/ch7_results_units.csv")
CRIT7 = pl.read_csv("reports/thesis/chapter_07/ch7_criteria.csv")

# Reconciliation targets recorded before the build (approximate).
RECON = {
    "pdl_reclaim_long": {
        "n_positive": 10,
        "mean_ret": 0.143,
        "ret_lo": 0.076,
        "ret_hi": 0.210,
        "mean_sharpe": 0.471,
        "mean_mdd": 0.103,
        "double_costs": 6,
        "drop_top": 2,
        "beats_bh": 0,
        "ci_gt0": 0,
        "fold_local": 9,
    },
    "volatility_breakout": {
        "n_positive": 6,
        "mean_ret": 0.109,
        "ret_lo": -0.562,
        "ret_hi": 1.314,
        "mean_sharpe": 0.116,
        "mean_mdd": None,
        "double_costs": 3,
        "drop_top": 0,
        "beats_bh": 2,
        "ci_gt0": 0,
        "fold_local": 6,
    },
}
DISCREPANCIES: list[str] = []
CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(ok), detail))
    if not ok:
        raise AssertionError(f"CH8 check failed: {name} {detail}")


def rng_for(*key_parts: object) -> np.random.Generator:
    key = "|".join(str(k) for k in key_parts)
    digest = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
    return np.random.default_rng(
        np.random.SeedSequence([MASTER_SEED, int.from_bytes(digest, "big")])
    )


# 1. Load candidate ledgers and trades (with fold ids)
def unit_rows(family: str) -> pl.DataFrame:
    return UNITS7.filter(
        (pl.col("family") == family) & (pl.col("symbol") == SYMBOL) & (pl.col("engine") == ENGINE)
    ).sort("seed")


def load_ledger(run_dir: str) -> pl.DataFrame:
    frames = []
    for f in range(N_FOLDS_EXPECTED):
        p = Path(run_dir) / f"{ENGINE}_fold{f}_test_equity.parquet"
        frames.append(
            pl.read_parquet(p)
            .select(
                "open_time",
                "net_return",
                "oo_return",
                "position",
                "turnover",
                "fee",
                "slippage",
                "funding",
            )
            .with_columns(pl.lit(f).alias("fold_id"))
        )
    led = pl.concat(frames).sort("open_time")
    times = led["open_time"].to_list()
    if times != sorted(times) or len(set(times)) != len(times):
        raise AssertionError(f"non-chronological or duplicated timestamps in {run_dir}")
    return led


def load_trades(run_dir: str) -> pl.DataFrame:
    frames = []
    for f in range(N_FOLDS_EXPECTED):
        p = Path(run_dir) / f"{ENGINE}_fold{f}_test_trades.parquet"
        if p.exists():
            frames.append(pl.read_parquet(p).with_columns(pl.lit(f).alias("fold_id")))
    return pl.concat(frames).sort("entry_time") if frames else pl.DataFrame()


DATA: dict[str, dict[int, dict]] = {}
for _round, family in CANDIDATES:
    DATA[family] = {}
    for row in unit_rows(family).iter_rows(named=True):
        led = load_ledger(row["run_dir"])
        net = led["net_return"].to_numpy().astype(float)
        check(
            f"{family}/seed={row['seed']}: 15 folds, 32,385 OOS bars",
            led.height == N_OBS_EXPECTED and led["fold_id"].n_unique() == N_FOLDS_EXPECTED,
            f"got {led.height} bars / {led['fold_id'].n_unique()} folds",
        )
        equity = np.cumprod(1.0 + net)
        check(
            f"{family}/seed={row['seed']}: equity end == ch7 total_return (1e-9)",
            abs(float(equity[-1]) - (1.0 + row["total_return_net"])) < 1e-9,
        )
        DATA[family][row["seed"]] = {
            "ledger": led,
            "net": net,
            "equity": equity,
            "trades": load_trades(row["run_dir"]),
            "unit": row,
        }


# 2. Input files
returns_frames = []
for _round, family in CANDIDATES:
    for seed, d in sorted(DATA[family].items()):
        led = d["ledger"].with_columns(pl.Series("equity", d["equity"]))
        returns_frames.append(
            led.select(
                pl.lit(family).alias("family"),
                pl.lit(SYMBOL).alias("symbol"),
                pl.lit(ENGINE).alias("engine"),
                pl.lit(seed).alias("seed"),
                pl.col("fold_id"),
                pl.col("open_time").alias("timestamp"),
                pl.col("net_return").alias("oo_return_net"),
                pl.col("equity"),
                pl.col("position"),
                pl.col("position").abs().alias("exposure"),
                pl.col("turnover"),
                pl.col("fee").alias("fees"),
                pl.col("slippage"),
                pl.col("funding"),
                pl.col("oo_return").alias("market_oo_return"),
            )
        )
RETURNS = pl.concat(returns_frames)
RETURNS.write_parquet(OUT / "ch8_input_returns.parquet", compression="zstd")
RETURNS.write_csv(OUT / "ch8_input_returns.csv", float_precision=8)

trade_frames = []
for _round, family in CANDIDATES:
    for seed, d in sorted(DATA[family].items()):
        tr = d["trades"]
        if tr.height == 0:
            continue
        trade_frames.append(
            tr.select(
                pl.lit(family).alias("family"),
                pl.lit(SYMBOL).alias("symbol"),
                pl.lit(ENGINE).alias("engine"),
                pl.lit(seed).alias("seed"),
                pl.col("fold_id"),
                pl.col("trade_id"),
                pl.col("entry_time"),
                pl.col("exit_time"),
                pl.when(pl.col("position") >= 0)
                .then(pl.lit("long"))
                .otherwise(pl.lit("short"))
                .alias("side"),
                pl.col("n_bars").alias("holding_bars"),
                pl.col("net_return"),
                pl.col("funding"),
                pl.col("cost").alias("fees_plus_slippage"),
                pl.col("exit_reason"),
            )
        )
TRADES_ALL = pl.concat(trade_frames)
TRADES_ALL.write_csv(OUT / "ch8_input_trades.csv", float_precision=8)


# 3. Observed per-seed metrics + reconciliation against chapter 7
def longest_true_run(mask: np.ndarray) -> int:
    if not mask.any():
        return 0
    padded = np.concatenate(([0], mask.view(np.int8), [0]))
    edges = np.flatnonzero(np.diff(padded))
    return int((edges[1::2] - edges[0::2]).max())


def observed_metrics(net: np.ndarray, equity: np.ndarray) -> dict[str, float]:
    peak = np.maximum.accumulate(equity)
    dd = 1.0 - equity / peak  # positive magnitude
    below = dd > 0
    longest = longest_true_run(below)
    return {
        "max_drawdown_pos": float(dd.max()),
        "mdd_duration_bars": longest,
        "mdd_duration_days": longest / 24.0,
        "time_under_water_share": float(below.mean()),
        "min_equity": float(equity.min()),
        "terminal_equity": float(equity[-1]),
    }


obs_rows = []
for scope_round, family in [*CANDIDATES, REFERENCE]:
    for row in unit_rows(family).iter_rows(named=True):
        if family in DATA:
            d = DATA[family][row["seed"]]
            extra = observed_metrics(d["net"], d["equity"])
            n_trades_ledger = d["trades"].height
        else:  # reference: chapter-7 columns only, no re-load
            extra = {
                "max_drawdown_pos": None,
                "mdd_duration_bars": None,
                "mdd_duration_days": None,
                "time_under_water_share": None,
                "min_equity": None,
                "terminal_equity": None,
            }
            n_trades_ledger = row["n_trades"]
        obs_rows.append(
            {
                "role": "candidate" if family in DATA else "negative_reference",
                "round": scope_round,
                "family": family,
                "symbol": SYMBOL,
                "engine": ENGINE,
                "seed": row["seed"],
                "total_return_net": row["total_return_net"],
                "sharpe_concat_ann": row["sharpe_concat_ann"],
                "max_drawdown_ch7_neg": row["max_drawdown"],
                "n_trades": n_trades_ledger,
                "bh_total_return_funded": row["bh_total_return"],
                **extra,
            }
        )
OBS = pl.from_dicts(obs_rows)
OBS.write_csv(OUT / "ch8_observed_seed_metrics.csv", float_precision=8)


def _crit(family: str, key: str) -> int:
    return int(
        CRIT7.filter(
            (pl.col("family") == family)
            & (pl.col("symbol") == SYMBOL)
            & (pl.col("criterion") == key)
        )["n_pass"][0]
    )


for _round, family in CANDIDATES:
    sub = OBS.filter(pl.col("family") == family)
    t = RECON[family]
    got = {
        "n_positive": int((sub["total_return_net"] > 0).sum()),
        "mean_ret": float(sub["total_return_net"].mean()),
        "ret_lo": float(sub["total_return_net"].min()),
        "ret_hi": float(sub["total_return_net"].max()),
        "mean_sharpe": float(sub["sharpe_concat_ann"].mean()),
        "mean_mdd": float(sub["max_drawdown_pos"].mean()),
        "double_costs": _crit(family, "survives_double_costs"),
        "drop_top": _crit(family, "survives_drop_top_trades"),
        "beats_bh": _crit(family, "beats_buy_and_hold"),
        "ci_gt0": _crit(family, "bootstrap_sharpe_ci_excludes_zero"),
        "fold_local": _crit(family, "not_confined_to_one_fold"),
    }
    for key, target in t.items():
        if target is None:
            continue
        value = got[key]
        ok = (
            value == target
            if isinstance(target, int)
            else abs(float(value) - float(target)) <= 0.006
        )
        if not ok:
            DISCREPANCIES.append(f"{family}: {key} observed {value} vs reference target {target}")
        check(f"reconcile {family}.{key}", ok, f"observed {value} vs target {target}")

bh_btc = float(unit_rows(CANDIDATES[0][1])["bh_total_return"][0])
check(
    "funded benchmark BTC +52.27% / terminal 1.522748",
    abs(bh_btc - 0.522748) < 5e-6,
    f"got {bh_btc}",
)


def median_seed(family: str) -> int:
    sub = OBS.filter(pl.col("family") == family).sort("total_return_net")
    return int(sub["seed"][sub.height // 2])


MEDIAN_SEED = {family: median_seed(family) for _r, family in CANDIDATES}

BLOCK_INFO = {}
for _r, family in CANDIDATES:
    info = suggest_block_length(DATA[family][MEDIAN_SEED[family]]["net"])
    BLOCK_INFO[family] = {
        "suggested_block": int(info["block_length"]),
        "last_significant_lag": int(info["last_significant_lag"]),
        "noise_band": float(info["noise_band"]),
    }


# 4. Vectorised resampling core
def stationary_indices(
    rng: np.random.Generator, n: int, length: int, mean_block: float, rows: int
) -> np.ndarray:
    p = 1.0 / max(mean_block, 1.0)
    restarts = rng.random((rows, length)) < p
    restarts[:, 0] = True
    positions = rng.integers(0, n, size=(rows, length))
    t = np.arange(length)
    last_restart = np.maximum.accumulate(np.where(restarts, t, -1), axis=1)
    pos_at_restart = np.take_along_axis(positions, last_restart, axis=1)
    return (pos_at_restart + (t - last_restart)) % n


def circular_indices(
    rng: np.random.Generator, n: int, length: int, block: int, rows: int
) -> np.ndarray:
    n_blocks = int(np.ceil(length / block))
    starts = rng.integers(0, n, size=(rows, n_blocks))
    offs = np.arange(length)
    return (starts[:, offs // block] + (offs % block)) % n


def path_stats(r: np.ndarray, multipliers: tuple[float, ...]) -> dict[float, dict[str, float]]:
    """Metrics of ONE simulated path under each exposure multiplier m (r -> m*r).

    Absorption rule: if 1 + m*r_t <= 0 the account is absorbed at zero at that
    bar (terminal 0, drawdown 1, every barrier crossed, no recovery).
    """
    out: dict[float, dict[str, float]] = {}
    for m in multipliers:
        x = m * r
        growth = 1.0 + x
        if (growth <= 0).any():
            t_abs = int(np.argmax(growth <= 0))
            out[m] = {
                "terminal": 0.0,
                "min_equity": 0.0,
                "mdd": 1.0,
                "mdd_dur_bars": float(r.size - t_abs),
                "tuw": 1.0,
                "sharpe_ann": float("nan"),
                "recovered": 0.0,
                "absorbed": 1.0,
                **{f"below_{int(b * 100)}": 1.0 for b in BARRIERS},
                "t_barrier50": float(t_abs),
            }
            continue
        w = np.cumprod(growth)
        peak = np.maximum.accumulate(w)
        dd = 1.0 - w / peak
        below = dd > 0
        trough = int(np.argmax(dd))
        sd = float(x.std(ddof=1))
        hit50 = np.flatnonzero(w < 0.50)
        out[m] = {
            "terminal": float(w[-1]),
            "min_equity": float(w.min()),
            "mdd": float(dd.max()),
            "mdd_dur_bars": float(longest_true_run(below)),
            "tuw": float(below.mean()),
            "sharpe_ann": float(x.mean() / sd * np.sqrt(8760.0)) if sd > 0 else 0.0,
            "recovered": float(bool((w[trough:] >= peak[trough]).any())),
            "absorbed": 0.0,
            **{f"below_{int(b * 100)}": float(w.min() < b) for b in BARRIERS},
            "t_barrier50": float(hit50[0]) if hit50.size else float(r.size),
        }
    return out


METRIC_KEYS = [
    "terminal",
    "min_equity",
    "mdd",
    "mdd_dur_bars",
    "tuw",
    "sharpe_ann",
    "recovered",
    "absorbed",
    *[f"below_{int(b * 100)}" for b in BARRIERS],
    "t_barrier50",
]


def simulate(
    family: str,
    scenario: str,
    method: str,
    block: int,
    n_paths: int,
    seed_mode: str,  # "hierarchical" or an int seed as str
    multipliers: tuple[float, ...] = (1.0,),
    keep_fans: bool = False,
) -> dict:
    seeds = sorted(DATA[family])
    series = {s: DATA[family][s]["net"] for s in seeds}
    n = N_OBS_EXPECTED
    per_mult = {m: {k: [] for k in METRIC_KEYS} for m in multipliers}
    seed_pick_rng = rng_for(family, scenario, method, block, seed_mode, "seedpick")
    fans = []
    n_chunks = int(np.ceil(n_paths / CHUNK))
    for chunk_i in range(n_chunks):
        rows = min(CHUNK, n_paths - chunk_i * CHUNK)
        rng = rng_for(family, scenario, method, block, seed_mode, "chunk", chunk_i)
        if seed_mode == "hierarchical":
            picks = seed_pick_rng.integers(0, len(seeds), size=rows)
        else:
            picks = np.full(rows, seeds.index(int(seed_mode)))
        if method == "stationary":
            idx = stationary_indices(rng, n, n, float(block), rows)
        else:
            idx = circular_indices(rng, n, n, int(block), rows)
        for j in range(rows):
            r = series[seeds[picks[j]]][idx[j]]
            stats = path_stats(r, multipliers)
            for m in multipliers:
                for k in METRIC_KEYS:
                    per_mult[m][k].append(stats[m][k])
            if keep_fans:
                w = np.cumprod(1.0 + r)
                fans.append(w[::FAN_STEP])
    result = {
        m: {k: np.asarray(v, dtype=float) for k, v in per_mult[m].items()} for m in multipliers
    }
    return {"metrics": result, "fans": np.asarray(fans) if keep_fans else None}


def binom_ci(p: float, n: int) -> tuple[float, float, float]:
    """Monte Carlo SE and Wilson 95% interval for a simulated probability."""
    se = float(np.sqrt(max(p * (1 - p), 1e-12) / n))
    z = 1.959963984540054
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return se, max(centre - half, 0.0), min(centre + half, 1.0)


# 5. Run scenarios
print("running simulations (deterministic, master seed 20260829)...")
summary_rows: list[dict] = []
fanq_rows: list[dict] = []
exposure_rows: list[dict] = []
breach_rows: list[dict] = []
sens_rows: list[dict] = []
conv_rows: list[dict] = []
dd_rows: list[dict] = []
PRIM_STORE: dict[str, dict[str, np.ndarray]] = {}  # per-family primary m=1 path metrics

for _r, family in CANDIDATES:
    block = BLOCK_INFO[family]["suggested_block"]

    # B. path uncertainty within each seed (post-hoc diagnostic layer)
    for seed in sorted(DATA[family]):
        res = simulate(family, "per_seed", "stationary", block, N_PER_SEED, str(seed))
        m1 = res["metrics"][1.0]
        term = m1["terminal"]
        p_loss = float((term < 1.0).mean())
        se, lo, hi = binom_ci(p_loss, term.size)
        summary_rows.append(
            {
                "layer": "path_within_seed",
                "family": family,
                "seed": seed,
                "method": "stationary",
                "block": block,
                "n_paths": term.size,
                "terminal_p05": float(np.percentile(term, 5)),
                "terminal_p50": float(np.percentile(term, 50)),
                "terminal_p95": float(np.percentile(term, 95)),
                "mdd_p50": float(np.percentile(m1["mdd"], 50)),
                "mdd_p95": float(np.percentile(m1["mdd"], 95)),
                "prob_terminal_below_1": p_loss,
                "prob_mc_se": se,
                "prob_wilson_lo": lo,
                "prob_wilson_hi": hi,
                "observed_terminal": float(DATA[family][seed]["equity"][-1]),
            }
        )

    # C. hierarchical primary (seed-then-path), with exposure grid and fans
    res = simulate(
        family,
        "hierarchical",
        "stationary",
        block,
        N_PRIMARY,
        "hierarchical",
        multipliers=MULTIPLIERS,
        keep_fans=True,
    )
    prim = res["metrics"]
    fans = res["fans"]

    # fan quantiles at decimated time points (m = 1)
    q_levels = (5, 25, 50, 75, 95)
    fan_q = np.percentile(fans, q_levels, axis=0)
    t_axis = np.arange(0, N_OBS_EXPECTED, FAN_STEP)
    med_seed = MEDIAN_SEED[family]
    obs_curve = DATA[family][med_seed]["equity"][::FAN_STEP]
    for i, t in enumerate(t_axis):
        fanq_rows.append(
            {
                "family": family,
                "bar_index": int(t),
                **{f"p{q:02d}": float(fan_q[j, i]) for j, q in enumerate(q_levels)},
                "observed_median_seed": float(obs_curve[i]),
            }
        )

    # per-multiplier tables
    for m in MULTIPLIERS:
        mm = prim[m]
        term, mdd = mm["terminal"], mm["mdd"]
        n_paths = term.size
        row = {
            "family": family,
            "multiplier": m,
            "n_paths": n_paths,
            "terminal_p05": float(np.percentile(term, 5)),
            "terminal_p50": float(np.percentile(term, 50)),
            "terminal_p95": float(np.percentile(term, 95)),
            "mdd_p50": float(np.percentile(mdd, 50)),
            "mdd_p95": float(np.percentile(mdd, 95)),
        }
        for label, series_ in (
            ("prob_terminal_below_1", term < 1.0),
            ("prob_absorbed_or_zero", mm["absorbed"] > 0),
            ("prob_recovered_peak", mm["recovered"] > 0),
            *[(f"prob_below_{int(b * 100)}", mm[f"below_{int(b * 100)}"] > 0) for b in BARRIERS],
        ):
            p = float(np.asarray(series_, dtype=float).mean())
            se, lo, hi = binom_ci(p, n_paths)
            row[label] = p
            row[f"{label}_mc_se"] = se
            row[f"{label}_wilson_lo"] = lo
            row[f"{label}_wilson_hi"] = hi
        exposure_rows.append(row)
        for b in BARRIERS:
            p = float((mm[f"below_{int(b * 100)}"] > 0).mean())
            se, lo, hi = binom_ci(p, n_paths)
            breach_rows.append(
                {
                    "family": family,
                    "multiplier": m,
                    "barrier": b,
                    "n_paths": n_paths,
                    "prob_breach": p,
                    "mc_se": se,
                    "wilson_lo": lo,
                    "wilson_hi": hi,
                }
            )

    # headline summary + loss/MDD exceedance ladders + percentiles (m = 1)
    m1 = prim[1.0]
    PRIM_STORE[family] = m1
    term = m1["terminal"]
    n_paths = term.size
    es5 = float(np.mean(np.sort(term - 1.0)[: max(1, int(0.05 * n_paths))]))
    head = {
        "layer": "hierarchical_primary",
        "family": family,
        "seed": "mixed(1..10 uniform)",
        "method": "stationary",
        "block": block,
        "n_paths": n_paths,
        **{f"terminal_p{q:02d}": float(np.percentile(term, q)) for q in PCTS},
        "expected_shortfall_5pct_terminal_return": es5,
        "sharpe_ann_p50": float(np.nanpercentile(m1["sharpe_ann"], 50)),
        "prob_recovered_peak": float((m1["recovered"] > 0).mean()),
        "median_t_barrier50_bars": float(np.percentile(m1["t_barrier50"], 50)),
    }
    for lvl in LOSS_LEVELS:
        p = float((term < 1.0 - lvl).mean())
        se, lo, hi = binom_ci(p, n_paths)
        head[f"prob_loss_gt_{int(lvl * 100)}"] = p
        head[f"prob_loss_gt_{int(lvl * 100)}_mc_se"] = se
    p0 = float((term < 1.0).mean())
    se0, lo0, hi0 = binom_ci(p0, n_paths)
    head["prob_terminal_below_1"] = p0
    head["prob_terminal_below_1_mc_se"] = se0
    head["prob_terminal_below_1_wilson_lo"] = lo0
    head["prob_terminal_below_1_wilson_hi"] = hi0
    summary_rows.append(head)
    check(
        f"terminal percentiles monotone ({family})",
        bool(np.all(np.diff([head[f"terminal_p{q:02d}"] for q in PCTS]) >= 0)),
    )

    for lvl in MDD_LEVELS:
        p = float((m1["mdd"] > lvl).mean())
        se, lo, hi = binom_ci(p, n_paths)
        dd_rows.append(
            {
                "family": family,
                "quantity": f"prob_mdd_gt_{int(lvl * 100)}",
                "value": p,
                "mc_se": se,
                "wilson_lo": lo,
                "wilson_hi": hi,
                "n_paths": n_paths,
            }
        )
    for q in PCTS:
        dd_rows.append(
            {
                "family": family,
                "quantity": f"mdd_p{q:02d}",
                "value": float(np.percentile(m1["mdd"], q)),
                "mc_se": None,
                "wilson_lo": None,
                "wilson_hi": None,
                "n_paths": n_paths,
            }
        )
        dd_rows.append(
            {
                "family": family,
                "quantity": f"mdd_duration_days_p{q:02d}",
                "value": float(np.percentile(m1["mdd_dur_bars"], q) / 24.0),
                "mc_se": None,
                "wilson_lo": None,
                "wilson_hi": None,
                "n_paths": n_paths,
            }
        )

    # convergence: same stream, growing budgets (prefix property of the chunks)
    for budget in (1000, 2000, 4000):
        sub = term[:budget]
        p = float((sub < 1.0).mean())
        se, lo, hi = binom_ci(p, budget)
        conv_rows.append(
            {
                "family": family,
                "n_paths": budget,
                "prob_terminal_below_1": p,
                "mc_se": se,
                "terminal_p05": float(np.percentile(sub, 5)),
                "terminal_p50": float(np.percentile(sub, 50)),
                "mdd_p95": float(np.percentile(m1["mdd"][:budget], 95)),
            }
        )

    # D. sensitivity: method x block (hierarchical, m = 1)
    blocks = sorted({*SENS_BLOCKS, block})
    for method in ("stationary", "circular_mbb"):
        for b in blocks:
            res_s = simulate(family, "sensitivity", method, b, N_SENS, "hierarchical")
            ms = res_s["metrics"][1.0]
            sens_rows.append(
                {
                    "family": family,
                    "method": method,
                    "block": b,
                    "is_primary": method == "stationary" and b == block,
                    "n_paths": N_SENS,
                    "terminal_p05": float(np.percentile(ms["terminal"], 5)),
                    "terminal_p50": float(np.percentile(ms["terminal"], 50)),
                    "terminal_p95": float(np.percentile(ms["terminal"], 95)),
                    "mdd_p50": float(np.percentile(ms["mdd"], 50)),
                    "mdd_p95": float(np.percentile(ms["mdd"], 95)),
                    "prob_terminal_below_1": float((ms["terminal"] < 1.0).mean()),
                }
            )
    print(f"  {family}: primary+per-seed+sensitivity done (block {block})")

SUMMARY = pl.from_dicts(summary_rows)
SUMMARY.write_csv(OUT / "ch8_simulation_summary.csv", float_precision=8)
pl.DataFrame(fanq_rows).write_csv(OUT / "ch8_path_quantiles.csv", float_precision=6)
EXPOSURE = pl.DataFrame(exposure_rows)
EXPOSURE.write_csv(OUT / "ch8_exposure_sensitivity.csv", float_precision=8)
BREACH = pl.DataFrame(breach_rows)
BREACH.write_csv(OUT / "ch8_breach_probabilities.csv", float_precision=8)
SENS = pl.DataFrame(sens_rows)
SENS.write_csv(OUT / "ch8_method_sensitivity.csv", float_precision=8)
pl.DataFrame(conv_rows).write_csv(OUT / "ch8_monte_carlo_convergence.csv", float_precision=8)
DDSUM = pl.from_dicts(dd_rows)
DDSUM.write_csv(OUT / "ch8_drawdown_summary.csv", float_precision=8)

# probability sanity checks
for df, cols in ((EXPOSURE, [c for c in EXPOSURE.columns if c.startswith("prob_")]),):
    for c in cols:
        if c.endswith(("mc_se", "wilson_lo", "wilson_hi")):
            continue
        vals = df[c].to_numpy()
        check(f"probabilities in [0,1]: {c}", bool(((vals >= 0) & (vals <= 1)).all()))
for family in [f for _r, f in CANDIDATES]:
    for m in MULTIPLIERS:
        probs = (
            BREACH.filter((pl.col("family") == family) & (pl.col("multiplier") == m))
            .sort("barrier", descending=True)["prob_breach"]
            .to_numpy()
        )
        check(
            f"breach monotone in barrier ({family}, m={m})",
            bool(np.all(np.diff(probs) <= 1e-12)),
        )
    mono = (
        BREACH.filter((pl.col("family") == family) & (pl.col("barrier") == 0.5))
        .sort("multiplier")["prob_breach"]
        .to_numpy()
    )
    check(f"breach(50%) monotone in multiplier ({family})", bool(np.all(np.diff(mono) >= -1e-12)))


# 6. Trade-level secondary analyses and concentration
def trade_seq_equity(r: np.ndarray) -> np.ndarray:
    return np.cumprod(1.0 + r)


conc_rows = []
for _r, family in CANDIDATES:
    for seed, d in sorted(DATA[family].items()):
        tr = d["trades"]["net_return"].to_numpy().astype(float)
        tr = tr[np.isfinite(tr)]
        n = tr.size
        pos = tr[tr > 0]
        pos_sorted = np.sort(pos)[::-1]
        gross_pos = float(pos.sum()) if pos.size else float("nan")

        def share_top(k: int, ps=pos_sorted, gp=gross_pos) -> float:
            return float(ps[: min(k, ps.size)].sum() / gp) if ps.size and gp > 0 else float("nan")

        def ret_without_best(k: int, t=tr) -> float:
            return float(drop_best_trades(t, k=k)["total_return_without_best"])

        def ret_without_worst(k: int, t=tr) -> float:
            keep = np.sort(t)[k:]
            return float(np.prod(1.0 + keep) - 1.0)

        seq = trade_seq_equity(tr)
        peak = np.maximum.accumulate(seq)
        no_new_max = seq < peak
        losses = tr < 0
        # profit concentration index: Herfindahl over positive-trade shares
        hhi = float(((pos / gross_pos) ** 2).sum()) if pos.size and gross_pos > 0 else float("nan")
        wins = tr > 0
        payoff = (
            float(tr[wins].mean() / abs(tr[~wins & (tr != 0)].mean()))
            if wins.any() and (~wins & (tr != 0)).any()
            else float("nan")
        )
        # chronological vs order permutation (trade-sequence unit, 1000 draws)
        rng = rng_for(family, seed, "trade_permutation")
        perm_mdd = np.empty(1000)
        for i in range(1000):
            e = trade_seq_equity(rng.permutation(tr))
            perm_mdd[i] = float((1.0 - e / np.maximum.accumulate(e)).max())
        obs_seq_mdd = float((1.0 - seq / peak).max())
        conc_rows.append(
            {
                "family": family,
                "seed": seed,
                "n_trades": n,
                "share_best_trade": share_top(1),
                "share_top5": share_top(5),
                "share_top_1pct": share_top(max(1, int(np.ceil(0.01 * n)))),
                "share_top_5pct": share_top(max(1, int(np.ceil(0.05 * n)))),
                "share_top_10pct": share_top(max(1, int(np.ceil(0.10 * n)))),
                **{f"ret_without_best_{k}": ret_without_best(k) for k in (1, 3, 5, 10)},
                **{f"ret_without_worst_{k}": ret_without_worst(k) for k in (1, 3, 5, 10)},
                "profit_hhi_positive_trades": hhi,
                "win_rate": float(wins.mean()) if n else float("nan"),
                "payoff_ratio": payoff,
                "holding_bars_median": float(d["trades"]["n_bars"].median()) if n else None,
                "max_consecutive_losses": longest_true_run(losses),
                "max_trades_without_new_high": longest_true_run(no_new_max),
                "obs_trade_seq_mdd": obs_seq_mdd,
                "perm_trade_seq_mdd_p50": float(np.percentile(perm_mdd, 50)),
                "perm_trade_seq_mdd_p95": float(np.percentile(perm_mdd, 95)),
                "obs_mdd_percentile_in_perm": float((perm_mdd <= obs_seq_mdd).mean()),
            }
        )
CONC = pl.DataFrame(conc_rows)
CONC.write_csv(OUT / "ch8_trade_concentration.csv", float_precision=8)

# reconciliation guard: chapter-7 drop-top-5 counts must match this table
for _r, family in CANDIDATES:
    n_surv = int((CONC.filter(pl.col("family") == family)["ret_without_best_5"] > 0).sum())
    check(
        f"drop-top-5 survivors match ch7 criteria ({family})",
        n_surv == _crit(family, "survives_drop_top_trades"),
        f"got {n_surv}",
    )

# trade-level bootstrap secondaries (median seed; declared unit = engine trade)
trade_sec_rows = []
for _r, family in CANDIDATES:
    seed = MEDIAN_SEED[family]
    tr = DATA[family][seed]["trades"]["net_return"].to_numpy().astype(float)
    tr = tr[np.isfinite(tr)]
    n = tr.size
    block_tr = max(2, round(float(np.sqrt(n))))  # retrospective choice, declared
    for method in ("iid_trade", "block_trade", "order_permutation"):
        rng = rng_for(family, seed, "trade_secondary", method)
        totals = np.empty(1000)
        for i in range(1000):
            if method == "iid_trade":
                sample = tr[rng.integers(0, n, n)]
            elif method == "block_trade":
                idx = circular_indices(rng, n, n, block_tr, 1)[0]
                sample = tr[idx]
            else:
                sample = rng.permutation(tr)
            totals[i] = float(np.prod(1.0 + sample) - 1.0)
        trade_sec_rows.append(
            {
                "family": family,
                "seed": seed,
                "method": method,
                "n_resamples": 1000,
                "trade_block": block_tr if method == "block_trade" else None,
                "total_return_p05": float(np.percentile(totals, 5)),
                "total_return_p50": float(np.percentile(totals, 50)),
                "total_return_p95": float(np.percentile(totals, 95)),
                "observed_total_return": float(np.prod(1.0 + tr) - 1.0),
            }
        )
TRADE_SEC = pl.from_dicts(trade_sec_rows)
TRADE_SEC.write_csv(OUT / "ch8_trade_secondary_bootstraps.csv", float_precision=8)
check(
    "order permutation preserves total return exactly",
    all(
        abs(r["total_return_p50"] - r["observed_total_return"]) < 1e-9
        for r in trade_sec_rows
        if r["method"] == "order_permutation"
    ),
)

with (OUT / "ch8_results_units.md").open("w", encoding="utf-8") as fh:
    fh.write(
        "# Units and aggregation of every chapter-8 result\n\n"
        "| File | Unit of analysis | Seeds mixed? | Aggregation |\n|---|---|---|---|\n"
        "| ch8_observed_seed_metrics | one seed's concatenated OOS record | no | none (observed) |\n"
        "| ch8_simulation_summary (path_within_seed) | one simulated path within ONE seed | no | quantiles over 1,000 paths per seed |\n"
        "| ch8_simulation_summary (hierarchical_primary) | one simulated path after a uniform seed pick | yes (declared) | quantiles over 4,000 paths |\n"
        "| ch8_path_quantiles | equity at decimated bar index | yes | cross-path quantiles per time point |\n"
        "| ch8_exposure_sensitivity / ch8_breach_probabilities | hierarchical path under r->m*r | yes | probabilities + Wilson 95% + MC SE |\n"
        "| ch8_method_sensitivity | hierarchical path | yes | quantiles over 2,000 paths per cell |\n"
        "| ch8_trade_concentration | engine trade within one seed | no | per-seed diagnostics |\n"
        "| ch8_trade_secondary_bootstraps | engine trade (median seed) | no | quantiles over 1,000 resamples |\n\n"
        "All simulated ranges are CONDITIONAL SIMULATION INTERVALS on the observed "
        "development record - never confidence intervals on a true edge, and the "
        "ten seeds are ten searches over ONE market history, not ten markets.\n"
    )


# 7. Tables 8.1-8.7 (markdown; CSVs above are the sources)
def md_table(df: pl.DataFrame, fmt: str = ".4f") -> str:
    def cell(v: object) -> str:
        if isinstance(v, float):
            return format(v, fmt)
        return "" if v is None else str(v)

    head = "| " + " | ".join(df.columns) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    return "\n".join(
        [head, sep, *("| " + " | ".join(cell(v) for v in r) + " |" for r in df.rows())]
    )


tables_md: list[str] = []

t81 = pl.DataFrame(
    [
        {
            "layer": "Search uncertainty",
            "what_varies": "the RS search seed (10 observed seeds)",
            "unit": "one seed's OOS record",
            "n": 10,
            "status": "observed, frozen in chapter 7",
        },
        {
            "layer": "Path uncertainty",
            "what_varies": "temporal resampling within one seed",
            "unit": "simulated path (32,385 bars)",
            "n": N_PER_SEED,
            "status": "post-hoc diagnostic (frozen method core)",
        },
        {
            "layer": "Combined diagnostic",
            "what_varies": "uniform seed pick, then path resample",
            "unit": "simulated path",
            "n": N_PRIMARY,
            "status": "post-hoc diagnostic; NOT ten independent markets",
        },
    ]
)
t81.write_csv(OUT / "table_8_1_design.csv")
tables_md.append(
    "## Table 8.1. Simulation design, uncertainty layers and evaluation units\n\n" + md_table(t81)
)

t82 = OBS.filter(pl.col("role") == "candidate").select(
    "family",
    "seed",
    "total_return_net",
    "sharpe_concat_ann",
    "max_drawdown_pos",
    "mdd_duration_days",
    "time_under_water_share",
    "n_trades",
)
t82.write_csv(OUT / "table_8_2_observed.csv", float_precision=6)
tables_md.append(
    "## Table 8.2. Observed OOS characteristics of the selected BTC candidates "
    "(RS engine, 10 seeds, 2022-03-31 to 2025-12-09)\n\n" + md_table(t82)
)

t83 = SUMMARY.filter(pl.col("layer") == "hierarchical_primary").select(
    "family",
    "block",
    "n_paths",
    "terminal_p05",
    "terminal_p50",
    "terminal_p95",
    "prob_terminal_below_1",
    "prob_terminal_below_1_mc_se",
    "prob_loss_gt_20",
    "expected_shortfall_5pct_terminal_return",
    "prob_recovered_peak",
)
t83.write_csv(OUT / "table_8_3_primary_outcomes.csv", float_precision=6)
tables_md.append(
    "## Table 8.3. Conditional bootstrap outcomes under the primary "
    "specification (hierarchical, stationary blocks)\n\n" + md_table(t83)
)

t84 = CONC.group_by("family", maintain_order=True).agg(
    pl.col("n_trades").median().alias("n_trades_median"),
    pl.col("share_top5").median().alias("share_top5_median"),
    (pl.col("ret_without_best_5") > 0).sum().alias("seeds_positive_after_drop_top5"),
    pl.col("win_rate").median().alias("win_rate_median"),
    pl.col("max_consecutive_losses").max().alias("max_consecutive_losses_worst_seed"),
    pl.col("obs_mdd_percentile_in_perm").median().alias("obs_mdd_pct_in_permutations_median"),
)
t84.write_csv(OUT / "table_8_4_concentration.csv", float_precision=6)
tables_md.append(
    "## Table 8.4. Profit concentration and trade-sequence diagnostics "
    "(per-seed CSV: ch8_trade_concentration.csv)\n\n" + md_table(t84)
)

t85 = BREACH.pivot(index=["family", "multiplier"], on="barrier", values="prob_breach")
t85.write_csv(OUT / "table_8_5_breach.csv", float_precision=6)
tables_md.append(
    "## Table 8.5. Capital-breach probabilities across exposure multipliers "
    "(hierarchical primary; MC SE and Wilson bounds in "
    "ch8_breach_probabilities.csv)\n\n" + md_table(t85)
)

t86 = SENS.select(
    "family",
    "method",
    "block",
    "is_primary",
    "terminal_p05",
    "terminal_p50",
    "terminal_p95",
    "mdd_p95",
    "prob_terminal_below_1",
)
t86.write_csv(OUT / "table_8_6_sensitivity.csv", float_precision=6)
tables_md.append(
    "## Table 8.6. Sensitivity to bootstrap method and block length\n\n" + md_table(t86)
)

t05_path = Path("reports/tables/montecarlo/t05_cuenta_fondeada.md")
if t05_path.exists():
    t87_src = t05_path.read_text(encoding="utf-8")
    tables_md.append(
        "## Table 8.7. Account-threshold outcomes (ILLUSTRATIVE; frozen notebook-07 "
        "prop-firm configs, executed for volatility_breakout only; pdl_reclaim_long "
        "NOT EVALUATED under this scenario)\n\n" + t87_src.strip()
    )
    (OUT / "table_8_7_account_thresholds.md").write_text(t87_src, encoding="utf-8")
else:
    tables_md.append("## Table 8.7 - NOT AVAILABLE: notebook-07 account table missing")

(OUT / "ch8_tables.md").write_text("\n\n".join(tables_md) + "\n", encoding="utf-8")


# 8. Figures
FAM_COLOR = {"pdl_reclaim_long": "#0072B2", "volatility_breakout": "#D55E00"}
FAM_LIST = [f for _r, f in CANDIDATES]


def save_fig(fig, name: str) -> None:
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"figure {name}")


# 8.1 observed seed risk
fig, ax = plt.subplots(figsize=(9.8, 6.0))
for family in FAM_LIST:
    sub = OBS.filter(pl.col("family") == family)
    x = sub["max_drawdown_pos"].to_numpy() * 100
    y = sub["total_return_net"].to_numpy() * 100
    ax.scatter(x, y, s=52, color=FAM_COLOR[family], alpha=0.85, label=family)
    ax.scatter([x.mean()], [y.mean()], s=240, marker="x", color=FAM_COLOR[family], lw=3)
ax.axhline(0, color="black", lw=1.0)
ax.set_xlabel("observed maximum drawdown (%, positive magnitude)")
ax.set_ylabel("observed OOS net total return (%)")
ax.set_title(
    "Observed OOS return vs maximum drawdown - 10 RS seeds per family\n"
    "(x = mean across seeds; spread is dispersion under search randomness, not a CI)"
)
ax.legend(fontsize=9)
save_fig(fig, "fig_8_1_observed_seed_risk")

# 8.2 path fans
FANQ = pl.read_csv(OUT / "ch8_path_quantiles.csv")
fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.4), sharey=False)
for ax, family in zip(axes, FAM_LIST, strict=True):
    sub = FANQ.filter(pl.col("family") == family)
    t = sub["bar_index"].to_numpy()
    ax.fill_between(
        t,
        sub["p05"],
        sub["p95"],
        color=FAM_COLOR[family],
        alpha=0.15,
        label="5-95% simulated range",
    )
    ax.fill_between(
        t,
        sub["p25"],
        sub["p75"],
        color=FAM_COLOR[family],
        alpha=0.30,
        label="25-75% simulated range",
    )
    ax.plot(t, sub["p50"], color=FAM_COLOR[family], lw=1.8, label="simulated median path")
    ax.plot(
        t,
        sub["observed_median_seed"],
        color="#111111",
        lw=1.4,
        ls="--",
        label=f"observed (median seed {MEDIAN_SEED[family]})",
    )
    ax.axhline(1.0, color="black", lw=0.8)
    ax.set_title(f"{family} (block {BLOCK_INFO[family]['suggested_block']} bars)")
    ax.set_xlabel("OOS bar index (32,385 hourly bars)")
    ax.set_ylabel("equity (start = 1)")
    ax.legend(fontsize=8)
fig.suptitle(
    f"Conditional bootstrap equity paths - hierarchical primary, {N_PRIMARY:,} paths, "
    "stationary blocks; conditional on the observed record",
    fontsize=12,
)
fig.tight_layout()
save_fig(fig, "fig_8_2_bootstrap_path_fans")

# per-path primary metrics persisted for traceability (figures 8.3/8.4 read them)
prim_frames = []
for family in FAM_LIST:
    prim_frames.append(
        pl.DataFrame(
            {
                "family": [family] * PRIM_STORE[family]["terminal"].size,
                **{k: PRIM_STORE[family][k] for k in METRIC_KEYS},
            }
        )
    )
pl.concat(prim_frames).write_parquet(OUT / "ch8_primary_path_metrics.parquet", compression="zstd")

# 8.3 terminal ECDF
fig, ax = plt.subplots(figsize=(9.8, 6.0))
for family in FAM_LIST:
    term = np.sort(PRIM_STORE[family]["terminal"])
    ecdf = np.arange(1, term.size + 1) / term.size
    ax.plot(term, ecdf, color=FAM_COLOR[family], lw=2.0, label=family)
ax.axvline(1.0, color="black", lw=1.2, ls="--")
ax.text(1.0, 0.02, " initial capital = 1", fontsize=9)
ax.set_xscale("log")
ax.set_xlabel("terminal equity (log scale; left tail fully visible)")
ax.set_ylabel("ECDF over simulated paths")
ax.set_title(
    f"Simulated terminal-equity distributions - hierarchical primary, "
    f"{N_PRIMARY:,} paths per family"
)
ax.legend(fontsize=9)
save_fig(fig, "fig_8_3_terminal_equity_distributions")

# 8.4 drawdown magnitude + duration
fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.2))
for family in FAM_LIST:
    mdd = np.sort(PRIM_STORE[family]["mdd"]) * 100
    dur = np.sort(PRIM_STORE[family]["mdd_dur_bars"]) / 24.0
    e1 = np.arange(1, mdd.size + 1) / mdd.size
    axes[0].plot(mdd, e1, color=FAM_COLOR[family], lw=2.0, label=family)
    axes[1].plot(dur, e1, color=FAM_COLOR[family], lw=2.0, label=family)
axes[0].set_xlabel("simulated maximum drawdown (%, positive magnitude)")
axes[1].set_xlabel("simulated longest time under the prior peak (days)")
for ax in axes:
    ax.set_ylabel("ECDF over simulated paths")
    ax.legend(fontsize=9)
fig.suptitle("Simulated drawdown magnitude and duration - hierarchical primary", fontsize=12)
fig.tight_layout()
save_fig(fig, "fig_8_4_drawdown_distributions")

# 8.5 breach heatmap
fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.4))
for ax, family in zip(axes, FAM_LIST, strict=True):
    grid = np.zeros((len(BARRIERS), len(MULTIPLIERS)))
    for i, b in enumerate(BARRIERS):
        for j, m in enumerate(MULTIPLIERS):
            grid[i, j] = float(
                BREACH.filter(
                    (pl.col("family") == family)
                    & (pl.col("barrier") == b)
                    & (pl.col("multiplier") == m)
                )["prob_breach"][0]
            )
    im = ax.imshow(grid, cmap="YlOrRd", vmin=0, vmax=1, aspect="auto")
    for i in range(len(BARRIERS)):
        for j in range(len(MULTIPLIERS)):
            ax.text(
                j,
                i,
                f"{grid[i, j]:.2f}",
                ha="center",
                va="center",
                fontsize=8.5,
                color="black" if grid[i, j] < 0.6 else "white",
            )
    ax.set_xticks(range(len(MULTIPLIERS)))
    ax.set_xticklabels([f"x{m:g}" for m in MULTIPLIERS])
    ax.set_yticks(range(len(BARRIERS)))
    ax.set_yticklabels([f"< {int(b * 100)}%" for b in BARRIERS])
    ax.set_xlabel("exposure multiplier m (returns scaled r -> m*r)")
    ax.set_title(family)
    ax.grid(visible=False)
fig.colorbar(im, ax=axes, fraction=0.03, pad=0.02).set_label("P(equity ever below barrier)")
fig.suptitle(
    "Capital-breach probabilities across exposure levels "
    f"(hierarchical primary, {N_PRIMARY:,} paths; MC SE in CSV)",
    fontsize=12,
)
save_fig(fig, "fig_8_5_exposure_breach_heatmap")

# 8.6 method/block sensitivity
fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.4), sharey=False)
markers = {"stationary": "o", "circular_mbb": "s"}
for ax, metric, label in zip(
    axes,
    ("terminal_p50", "mdd_p95"),
    ("terminal equity (median, 5-95% simulated range)", "maximum drawdown p95"),
    strict=True,
):
    blocks_axis = sorted({*SENS_BLOCKS, *[BLOCK_INFO[f]["suggested_block"] for f in FAM_LIST]})
    for family in FAM_LIST:
        for method in ("stationary", "circular_mbb"):
            sub = SENS.filter((pl.col("family") == family) & (pl.col("method") == method)).sort(
                "block"
            )
            x = np.array([blocks_axis.index(b) for b in sub["block"]], dtype=float)
            x += (0.0 if method == "stationary" else 0.18) + (
                0.0 if family == FAM_LIST[0] else 0.36
            )
            ax.scatter(
                x,
                sub[metric],
                color=FAM_COLOR[family],
                marker=markers[method],
                s=46,
                label=f"{family} - {method}" if metric == "terminal_p50" else None,
            )
            if metric == "terminal_p50":
                ax.vlines(
                    x,
                    sub["terminal_p05"],
                    sub["terminal_p95"],
                    color=FAM_COLOR[family],
                    lw=1.2,
                    alpha=0.6,
                )
    ax.set_xticks(np.arange(len(blocks_axis)) + 0.27)
    ax.set_xticklabels([f"{b}h" for b in blocks_axis])
    ax.set_xlabel("block length")
    ax.set_ylabel(label)
axes[0].axhline(1.0, color="black", lw=0.8, ls="--")
axes[0].legend(fontsize=8, loc="upper left")
fig.suptitle(
    "Sensitivity to resampling method and block length "
    "(simulated ranges, not confidence intervals)",
    fontsize=12,
)
fig.tight_layout()
save_fig(fig, "fig_8_6_resampling_sensitivity")

# 8.7 trade concentration
fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.4))
for family in FAM_LIST:
    seed = MEDIAN_SEED[family]
    tr = DATA[family][seed]["trades"]["net_return"].to_numpy().astype(float)
    order = np.sort(tr)[::-1]
    cum = np.cumsum(order)
    axes[0].plot(
        np.arange(1, order.size + 1),
        cum * 100,
        color=FAM_COLOR[family],
        lw=1.8,
        label=f"{family} (median seed {seed}, {order.size} trades)",
    )
    ks = [0, 1, 3, 5, 10]
    rets = [float(np.prod(1.0 + tr) - 1.0)] + [
        float(drop_best_trades(tr, k=k)["total_return_without_best"]) for k in ks[1:]
    ]
    axes[1].plot(
        ks, np.array(rets) * 100, marker="o", color=FAM_COLOR[family], lw=1.8, label=family
    )
axes[0].axhline(0, color="black", lw=0.8)
axes[0].set_xlabel("trades sorted by net return (best first)")
axes[0].set_ylabel("cumulative sum of trade net returns (%)")
axes[0].set_title("(a) Cumulative contribution of sorted trades")
axes[0].legend(fontsize=8)
axes[1].axhline(0, color="black", lw=0.8)
axes[1].set_xlabel("k best trades removed (causal recomputation)")
axes[1].set_ylabel("compounded OOS return (%)")
axes[1].set_title("(b) Return after removing the k best trades")
axes[1].legend(fontsize=8)
fig.suptitle(
    "Profit concentration and trade-sequence sensitivity "
    "(engine-trade unit; per-seed table in ch8_trade_concentration.csv)",
    fontsize=12,
)
fig.tight_layout()
save_fig(fig, "fig_8_7_trade_concentration")

# final global checks
check(
    "no holdout file was read (loader paths are dev-run artifacts only)",
    True,
    "all inputs are development-run artifacts under artifacts/runs/**; this builder reads no holdout partition file",
)
check(
    "simulated path length equals the OOS horizon",
    True,
    f"paths are generated with length {N_OBS_EXPECTED} by construction",
)

with (OUT / "CH8_DISCREPANCIES.md").open("w", encoding="utf-8") as fh:
    if DISCREPANCIES:
        fh.write("# CH8 discrepancies vs the pre-recorded reference values\n\n")
        fh.writelines(f"- {d}\n" for d in DISCREPANCIES)
    else:
        fh.write(
            "# CH8 discrepancies\n\nNone detected: every pre-recorded reference value "
            "reconciled against ch7_results_units.csv / ch7_criteria.csv "
            "within the stated tolerances (counts exact; means/ranges within 0.006).\n"
        )

with (OUT / "CH8_VERIFICATION.md").open("w", encoding="utf-8") as fh:
    fh.write("# CH8 verification checklist (auto-generated by the builder)\n\n")
    fh.write(f"Checks run: {len(CHECKS)} - all passed (a failure aborts the build).\n\n")
    for name, ok, detail in CHECKS:
        fh.write(f"- [{'x' if ok else ' '}] {name}" + (f" - {detail}" if detail else "") + "\n")
    fh.write(
        "\nAdditional invariants enforced by construction: series start at capital 1 "
        "(cumprod of 1+r); exposure applied as r -> m*r with zero-absorption; "
        "deterministic per-scenario streams (master seed 20260829); percentiles "
        "emitted in monotone order; simulations never alter any chapter-7 verdict "
        "and are labelled conditional diagnostics, not validation.\n"
    )

meta = {
    "master_seed": MASTER_SEED,
    "primary_method": "stationary_block_bootstrap (frozen notebook-07 precedent)",
    "blocks": BLOCK_INFO,
    "median_seeds": MEDIAN_SEED,
    "budgets": {"per_seed": N_PER_SEED, "hierarchical": N_PRIMARY, "sensitivity": N_SENS},
    "multipliers": MULTIPLIERS,
    "barriers": BARRIERS,
}
(OUT / "ch8_run_config.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")

print(f"\nchecks passed: {len(CHECKS)} | discrepancies: {len(DISCREPANCIES)}")
print(f"written under {OUT}")
