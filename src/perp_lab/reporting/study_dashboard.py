"""Consolidate the whole study into one artifact the dashboard can serve.

The API is organised around a single search run: it answers "what did this run
do", which is the right question while an experiment is in flight and the wrong
one once the study is closed. The thesis result is not a run, it is thirteen
families measured against each other under a shared correction, and nothing in
the run-level artifacts expresses that.

This module reads the evidence that already exists — the gate reports, the
persisted out-of-sample ledgers and the three study-closure reports — and emits
a single payload holding, per family: the seed-averaged equity path, each
seed's own path, the promotion criteria as they were scored, and a resampling
fan showing how much of the final number is path luck.

It **recomputes no backtest** and reads no holdout row. The holdout section is
copied from the report written when the partition was opened, once, in Phase H.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from perp_lab.backtesting.metrics import bars_per_year
from perp_lab.reporting.study_closure import (
    BLOCK_PROBABILITY,
    PRIMARY_ENGINE,
    PRIMARY_SYMBOL,
    StudyUnit,
    _unit_oos_returns,
    build_inventory,
)

SECONDARY_SYMBOL = "ETHUSDT"
TIMEFRAME = "1h"
DAYS_PER_YEAR = 365

R3_GATE_REPORT = Path("reports/r3_gate/r3_full_budget100_ga21/thesis_report.json")
STUDY_LEVEL_REPORT = Path("reports/study_closure/study_level_multiple_testing.json")
REGIME_REPORT = Path("reports/study_closure/regime_conditioned.json")
HOLDOUT_REPORT = Path("reports/study_closure/final_holdout.json")

# Curves are drawn, not tabulated, so they are decimated to what a chart can
# actually resolve. Keeping 32k points per family would make the payload tens of
# megabytes to render a line a few hundred pixels wide.
EQUITY_POINTS = 600
SEED_EQUITY_POINTS = 240
MC_CHECKPOINTS = 120

MC_PATHS = 1000
MC_BATCH = 100
MC_SEED = 20260813

# What each family bets on, in the language a reader without a finance
# background can follow. These are descriptions of the hypothesis, not of the
# result.
FAMILY_THESIS: dict[str, str] = {
    "momentum": "Lo que ha subido sigue subiendo: entra a favor del movimiento reciente.",
    "mean_reversion": "Lo que se estira vuelve al centro: entra en contra del movimiento reciente.",
    "breakout": "Si el precio rompe el máximo o mínimo de las últimas N horas, empieza un movimiento.",
    "volatility_breakout": (
        "Igual que la ruptura, pero el umbral se mide en unidades de volatilidad actual, "
        "así que se adapta a mercados tranquilos y agitados."
    ),
    "funding": (
        "El funding alto indica exceso de largos apalancados; opera contra ese desequilibrio."
    ),
    "funding_reversal": "Los extremos de funding se corrigen: entra cuando el funding se dispara.",
    "BTC_ETH_confirmation": "Opera ETH solamente cuando BTC confirma la misma dirección.",
    "mtf_trend_consensus": (
        "Solo actúa cuando varias escalas temporales (1h, 4h, diario) apuntan al mismo lado."
    ),
    "intraday_seasonality": "Hay horas del día sistemáticamente mejores que otras.",
    "xasset_spread_reversion": "El diferencial entre BTC y ETH se estira y luego vuelve.",
    "taker_flow_extreme": (
        "Cuando los compradores agresivos dominan de forma extrema, la presión se agota."
    ),
    "flow_price_divergence": (
        "El flujo de órdenes compra pero el precio no acompaña: la divergencia se resuelve."
    ),
    "illiquidity_reversion": (
        "Un movimiento hecho con poco volumen es ruido y tiende a deshacerse."
    ),
}


class StudyDashboardError(RuntimeError):
    """Raised when the persisted evidence cannot support the dashboard payload."""


@dataclass(frozen=True)
class FamilySeries:
    """One family on one asset: the averaged path plus each seed's own path."""

    family: str
    gate: str
    symbol: str
    averaged: pl.DataFrame
    per_seed: dict[int, pl.DataFrame]


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise StudyDashboardError(f"Required evidence file is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# Series


def collect_series(units: list[StudyUnit], *, symbol: str, engine: str) -> list[FamilySeries]:
    """Per-family out-of-sample paths, keeping the seeds separate as well as pooled.

    ``study_closure`` needs only the seed-averaged series, because a family is
    one hypothesis and the seed is an arbitrary starting point to be integrated
    out. The dashboard needs both: the average is what was tested, and the
    spread across seeds is the most direct visual evidence that the search was
    fitting noise.
    """
    gate_of = {u.family: u.gate for u in units}
    out: list[FamilySeries] = []
    for family in sorted({u.family for u in units}):
        selected = [
            u for u in units if u.family == family and u.symbol == symbol and u.engine == engine
        ]
        per_seed: dict[int, pl.DataFrame] = {}
        for unit in selected:
            frame = _unit_oos_returns(unit.run_dir, engine)
            if frame.height:
                per_seed[unit.seed] = frame
        if not per_seed:
            continue
        averaged = (
            pl.concat(list(per_seed.values()))
            .group_by("open_time")
            .agg(pl.col("net_return").mean())
            .sort("open_time")
        )
        out.append(
            FamilySeries(
                family=family,
                gate=gate_of[family],
                symbol=symbol,
                averaged=averaged,
                per_seed=per_seed,
            )
        )
    return out


def _equity(returns: np.ndarray) -> np.ndarray:
    return np.cumprod(1.0 + returns)


def _decimate(frame: pl.DataFrame, n_points: int) -> list[dict[str, Any]]:
    """Equity path reduced to ``n_points`` samples, always keeping the endpoints.

    Sampling the equity curve rather than aggregating returns is deliberate: the
    curve is a running product, so any sampled point is still the exact equity
    at that instant. The final value is therefore the true final value, not an
    approximation of it.
    """
    returns = frame["net_return"].to_numpy().astype(float)
    equity = _equity(returns)
    times = frame["open_time"].to_list()
    n = equity.size
    if n == 0:
        return []
    idx = np.unique(np.linspace(0, n - 1, num=min(n_points, n)).round().astype(int))
    return [{"t": times[int(i)].isoformat(), "equity": float(equity[int(i)])} for i in idx]


def _summary(returns: np.ndarray) -> dict[str, float]:
    """Total return, annualised Sharpe and worst drawdown of one path."""
    if returns.size == 0:
        return {"total_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0, "n_bars": 0.0}
    equity = _equity(returns)
    peak = np.maximum.accumulate(equity)
    std = float(np.std(returns, ddof=1)) if returns.size > 1 else 0.0
    bpy = bars_per_year(TIMEFRAME, DAYS_PER_YEAR)
    sharpe = float(np.mean(returns) / std * np.sqrt(bpy)) if std > 0 else 0.0
    return {
        "total_return": float(equity[-1] - 1.0),
        "sharpe": sharpe,
        "max_drawdown": float((equity / peak - 1.0).min()),
        "n_bars": float(returns.size),
    }


# Resampling fan


def monte_carlo_fan(
    returns: np.ndarray,
    *,
    seed: int = MC_SEED,
    n_paths: int = MC_PATHS,
    n_checkpoints: int = MC_CHECKPOINTS,
) -> dict[str, Any]:
    """Stationary-bootstrap fan of equity paths built from the family's own returns.

    Each synthetic path is the same bars in a different order, drawn in blocks of
    geometric length so that volatility clustering survives the resampling. What
    the fan measures is **path risk**: how differently this same edge, or lack of
    edge, could have played out. It deliberately does not test whether the mean
    is real — resampling the observed returns bakes the observed mean in — and
    the caller must label it that way. The null-hypothesis question is answered
    separately by the bootstrap p-value and the probability of backtest
    overfitting.
    """
    n = int(returns.size)
    if n == 0:
        raise StudyDashboardError("Cannot resample an empty return series.")

    checkpoints = np.unique(np.linspace(0, n - 1, num=min(n_checkpoints, n)).round().astype(int))
    rng = np.random.default_rng(seed)
    samples = np.empty((n_paths, checkpoints.size), dtype=float)
    terminal = np.empty(n_paths, dtype=float)

    drawn = 0
    while drawn < n_paths:
        batch = min(MC_BATCH, n_paths - drawn)
        starts = rng.integers(0, n, size=(batch, n))
        restart = rng.random((batch, n)) < BLOCK_PROBABILITY
        restart[:, 0] = True
        # Within a block the index simply advances, so each position needs the
        # start drawn at the most recent restart. Accumulating the maximum over
        # restart positions propagates that origin forward without a loop.
        origin = np.maximum.accumulate(np.where(restart, np.arange(n), 0), axis=1)
        offset = np.arange(n)[None, :] - origin
        idx = (np.take_along_axis(starts, origin, axis=1) + offset) % n
        paths = np.cumprod(1.0 + returns[idx], axis=1)
        samples[drawn : drawn + batch] = paths[:, checkpoints]
        terminal[drawn : drawn + batch] = paths[:, -1]
        drawn += batch

    observed = _equity(returns)
    quantiles = {
        "p05": np.quantile(samples, 0.05, axis=0),
        "p25": np.quantile(samples, 0.25, axis=0),
        "p50": np.quantile(samples, 0.50, axis=0),
        "p75": np.quantile(samples, 0.75, axis=0),
        "p95": np.quantile(samples, 0.95, axis=0),
    }
    return {
        "method": "stationary_bootstrap",
        "n_paths": int(n_paths),
        "expected_block_bars": float(1.0 / BLOCK_PROBABILITY),
        "seed": int(seed),
        "measures": "path_risk_not_significance",
        "checkpoint_index": [int(i) for i in checkpoints],
        "bands": {k: [float(x) for x in v] for k, v in quantiles.items()},
        "observed": [float(observed[int(i)]) for i in checkpoints],
        "terminal": {
            "observed_total_return": float(observed[-1] - 1.0),
            "p05": float(np.quantile(terminal, 0.05) - 1.0),
            "p25": float(np.quantile(terminal, 0.25) - 1.0),
            "p50": float(np.quantile(terminal, 0.50) - 1.0),
            "p75": float(np.quantile(terminal, 0.75) - 1.0),
            "p95": float(np.quantile(terminal, 0.95) - 1.0),
            "probability_positive": float(np.mean(terminal > 1.0)),
        },
    }


# Assembly


def criteria_matrix(root: Path) -> dict[str, dict[str, Any]]:
    """The six R3 promotion criteria as scored, keyed ``family|symbol``.

    Only the five R3 families were scored on this grid. S1 and S2 families are
    absent because their gates asked different questions, and inventing a row
    for them would misrepresent what was tested.
    """
    payload = _read_json(root / R3_GATE_REPORT)
    matrix: dict[str, dict[str, Any]] = {}
    for row in payload["primary_table_rs"]:
        key = f"{row['family']}|{row['symbol']}"
        matrix[key] = {
            "verdict": row["verdict"],
            "note": row.get("diagnostic_note"),
            "majority_required": row["majority_required"],
            "median_oos_return": row.get("median_oos_return"),
            "median_oos_sharpe": row.get("median_oos_sharpe"),
            "median_buy_and_hold_return": row.get("median_buy_and_hold_return"),
            "min_trades_veto": {
                "passed": row["min_oos_trades_met"]["n_pass"],
                "of": row["min_oos_trades_met"]["n_seeds"],
                "triggered": row["min_oos_trades_met"]["veto_triggered"],
            },
            "criteria": [
                {
                    "key": name,
                    "label": crit["label"],
                    "passed": crit["n_pass"],
                    "of": crit["n_seeds"],
                    "required": crit["majority_required"],
                    "met": crit["pass"],
                }
                for name, crit in sorted(row["criteria"].items(), key=lambda kv: kv[1]["label"])
            ],
        }
    return matrix


def _family_payload(
    series: FamilySeries,
    *,
    stats: dict[str, Any] | None,
    corrections: dict[str, Any],
    matrix: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    returns = series.averaged["net_return"].to_numpy().astype(float)
    summary = _summary(returns)
    holm = corrections.get("holm_bonferroni", {}).get("adjusted_p_values", {})
    bh = corrections.get("benjamini_hochberg", {}).get("adjusted_p_values", {})
    grid = matrix.get(f"{series.family}|{series.symbol}")

    seeds = []
    for seed in sorted(series.per_seed):
        frame = series.per_seed[seed]
        seed_returns = frame["net_return"].to_numpy().astype(float)
        seeds.append(
            {
                "seed": seed,
                **_summary(seed_returns),
                "equity": _decimate(frame, SEED_EQUITY_POINTS),
            }
        )

    return {
        "key": f"{series.family}|{series.symbol}",
        "family": series.family,
        "gate": series.gate,
        "symbol": series.symbol,
        "thesis": FAMILY_THESIS.get(series.family, ""),
        "n_seeds": len(series.per_seed),
        **summary,
        "p_value": None if stats is None else stats["p_value"],
        "holm_adjusted_p": holm.get(series.family),
        "bh_adjusted_p": bh.get(series.family),
        "survives_correction": False,
        "verdict": "REJECTED" if grid is None else grid["verdict"],
        "gate_note": None if grid is None else grid["note"],
        "criteria": None if grid is None else grid["criteria"],
        "min_trades_veto": None if grid is None else grid["min_trades_veto"],
        "buy_and_hold_return": None if grid is None else grid["median_buy_and_hold_return"],
        "equity": _decimate(series.averaged, EQUITY_POINTS),
        "seeds": seeds,
        "monte_carlo": monte_carlo_fan(returns),
    }


def build_payload(root: Path, *, include_holdout: bool = False) -> dict[str, Any]:
    """Everything the study terminal needs, in one JSON-serialisable payload.

    The holdout reading is excluded unless asked for. It exists on disk as
    evidence and stays there, but it is not published until its provenance has
    been audited, and the cheapest way to guarantee that is to not put it in the
    file the API reads. The serving layer gates it a second time.
    """
    units = build_inventory(root)
    study = _read_json(root / STUDY_LEVEL_REPORT)
    regimes = _read_json(root / REGIME_REPORT)
    matrix = criteria_matrix(root)

    stats_by_key: dict[str, dict[str, Any]] = {
        f"{row['family']}|{row['symbol']}": row for row in study["families"] + study["secondary"]
    }
    corrections = study["corrections"]

    families: list[dict[str, Any]] = []
    for symbol in (PRIMARY_SYMBOL, SECONDARY_SYMBOL):
        for series in collect_series(units, symbol=symbol, engine=PRIMARY_ENGINE):
            key = f"{series.family}|{series.symbol}"
            families.append(
                _family_payload(
                    series,
                    stats=stats_by_key.get(key),
                    corrections=corrections if symbol == PRIMARY_SYMBOL else {},
                    matrix=matrix,
                )
            )

    holdout_path = root / HOLDOUT_REPORT
    holdout = _read_json(holdout_path) if include_holdout and holdout_path.exists() else None

    return {
        "report": "study_dashboard",
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "primary_symbol": PRIMARY_SYMBOL,
        "secondary_symbol": SECONDARY_SYMBOL,
        "primary_engine": PRIMARY_ENGINE,
        "timeframe": TIMEFRAME,
        "study": {
            "n_families": corrections["n_tests"],
            "n_units": len(units),
            "n_configurations_evaluated": corrections["n_configurations_evaluated"],
            "alpha": corrections["alpha"],
            "best_family": corrections["best_family"],
            "holm": {
                "n_rejected": corrections["holm_bonferroni"]["n_rejected"],
                "adjusted_p_values": corrections["holm_bonferroni"]["adjusted_p_values"],
            },
            "benjamini_hochberg": {
                "n_rejected": corrections["benjamini_hochberg"]["n_rejected"],
                "adjusted_p_values": corrections["benjamini_hochberg"]["adjusted_p_values"],
            },
            "pbo": corrections["probability_of_backtest_overfitting"],
            "deflated_sharpe": corrections["deflated_sharpe"],
            "sensitivity": study["sensitivity"],
            "criteria_by_gate": study["criteria"],
            "conclusion": study["conclusion"],
            "source_commit": study.get("git_commit"),
        },
        "families": families,
        "regimes": {
            "cells": regimes.get("cells", []),
            "correction": regimes.get("correction", {}),
            "candidate": regimes.get("candidate"),
            "conclusion": regimes.get("conclusion"),
            "exploratory": True,
        },
        "holdout": holdout,
        "holdout_publication": "AUDIT_PENDING" if holdout is None else "INCLUDED",
    }


__all__ = [
    "FamilySeries",
    "StudyDashboardError",
    "build_payload",
    "collect_series",
    "criteria_matrix",
    "monte_carlo_fan",
]
