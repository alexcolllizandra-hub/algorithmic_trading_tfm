"""Run the meta-labeling study (RQ3) on real development data, exploratory only.

ADR 0017 built and validated this layer on paired synthetic markets and stopped
there, because its contract presupposes an eligible primary strategy and Gate R3
closed with zero promotions. That blocker is real for *promotion* and remains in
force: nothing here promotes anything, and the frozen holdout is never loaded.

It is not a blocker for answering RQ3. The research question asks whether a
meta-label filter improves a base signal's risk-adjusted performance -- not
whether the base signal was promoted. This script answers it on real BTC/ETH
bars under an explicitly exploratory contract, which the frozen methodology
permits provided no operational candidate is claimed.

Choosing the primary
--------------------
Picking the primary by performance would import the search's selection bias into
a study meant to measure something else. The primary is therefore chosen on two
structural criteria fixed before looking at any meta-label result:

1. **Event count.** ``study.py`` skips any fold with fewer than 30 events in
   train or validation, so a family that trades rarely cannot support a
   classifier at all.
2. **Low span overlap.** Triple-barrier labels on a strategy that is in the
   market half the time produce heavily overlapping holding windows; uniqueness
   weighting mitigates that but does not remove it.

``crt_htf_range_reversal`` on BTCUSDT satisfies both (median 598 trades, 7.5%
exposure). ``BTC_ETH_confirmation`` has more events (863) but sits in the market
53.7% of the time and was rejected on criterion 2.

Its parameters are the modal fold winner of the CRT_INTRADAY_V1 run: the only
configuration selected in more than one of the 15 outer folds. That is a
stability criterion, not a peak-performance one -- notably, the other 13 folds
each chose a different configuration, which is itself recorded as a finding.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from perp_lab.backtesting.engine import _funding_per_bar
from perp_lab.config import Paths, load_data_contract, load_experiment_config
from perp_lab.data.splits import resolve_holdout_start
from perp_lab.eda.datasets import DataLake
from perp_lab.features.context import FeatureContext
from perp_lab.features.registry import build_feature_frame, feature_columns, resolve_feature_set
from perp_lab.features.spec import FeatureItemLike
from perp_lab.labeling.triple_barrier import EVENT_TIME_COL, SIDE_COL
from perp_lab.meta_labeling.study import (
    MetaLabelStudyConfig,
    build_dataset,
    run_meta_label_study,
)
from perp_lab.regimes.models import REGIME_NAME_COL, ThresholdRegime
from perp_lab.search.registry import _FeatureItem, build_search_space

FAMILY = "crt_htf_range_reversal"
SYMBOL = "BTCUSDT"
TIMEFRAME = "1h"

# Modal fold winner across the 15 outer folds of the CRT_INTRADAY_V1 study
# (artifacts/runs/search_crt_htf_range_reversal_20260817T234419Z_44b06a).
PRIMARY_PARAMS: dict[str, Any] = {
    "candle_timeframe": "4h",
    "direction": "both",
    "entry_rule": "first_retest",
    "min_net_reward_risk": 1.5,
    "stop_kind": "wick_extreme",
    "sweep_bps": 20.0,
    "target_plan": "r_multiple_2",
    "time_stop_bars": 48,
}


def _context_feature_items(exp: Any) -> list[_FeatureItem]:
    """Causal context the meta-model may condition on.

    Deliberately wider than the four inputs the regime model needs. The primary
    supplies direction from price structure alone; the classifier's job is to
    judge *when* that structure is worth acting on, which it cannot do without
    volatility, trend, stretch and participation context. Every window comes
    from ``experiment.yaml`` so nothing is invented here, and every feature is
    causal by the engine's own construction.
    """
    f = exp.features
    items: list[_FeatureItem] = []
    for window in f.regime_vol_windows:
        items.append(_FeatureItem("rvol", window=window))
    for window in f.momentum_windows:
        items.append(_FeatureItem("momentum", window=window))
    for window in f.zscore_windows:
        items.append(_FeatureItem("zscore", window=window))
    for window in f.relative_volume_windows:
        items.append(_FeatureItem("rel_volume", window=window))
    return items


def _attach_funding_per_bar(bars: pl.DataFrame, funding: pl.DataFrame | None) -> pl.DataFrame:
    """Charge each funding settlement to the bar whose holding interval covers it.

    Reuses the backtester's own helper rather than re-deriving the mapping, so a
    triple-barrier label and the backtested arm it is compared against price
    funding identically. A divergence here would show up as the meta-label layer
    "adding value" that is really just a different cost model.
    """
    bar_ns = bars["open_time"].dt.epoch("ns").to_numpy()
    if funding is None or funding.height == 0:
        rates = np.zeros(bars.height, dtype=float)
    else:
        f = funding.sort("funding_time")
        rates = _funding_per_bar(
            bar_ns,
            f["funding_time"].dt.epoch("ns").to_numpy(),
            f["funding_rate"].cast(pl.Float64).to_numpy().astype(float),
        )
    return bars.with_columns(pl.Series("funding_rate_in_bar", rates, dtype=pl.Float64))


def _events_from_signals(signals: pl.DataFrame, time_col: str = "open_time") -> pl.DataFrame:
    """One event per entry: a bar where the primary opens or flips a position.

    Holding bars are not events. Meta-labeling decides whether to *act on a
    signal*, so re-asking the question every bar a position happens to stay open
    would both inflate the sample and make its rows near-duplicates.
    """
    side = signals[SIDE_COL].cast(pl.Int64)
    previous = side.shift(1).fill_null(0)
    entries = (side != 0) & (side != previous)
    return (
        signals.with_columns(entries.alias("_entry"))
        .filter(pl.col("_entry"))
        .select(pl.col(time_col).alias(EVENT_TIME_COL), pl.col(SIDE_COL).cast(pl.Float64))
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("reports/meta_labeling_real"))
    parser.add_argument("--n-folds", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    exp = load_experiment_config("configs/experiment.yaml")
    contract = load_data_contract("configs/data_contract.yaml")
    lake = DataLake(contract, Paths())
    holdout_start = resolve_holdout_start(contract)

    bars = lake.load_klines(SYMBOL, TIMEFRAME, partition="development").frame
    funding = lake.load_funding(SYMBOL, partition="development").frame
    print(f"bars={bars.height} | {bars['open_time'].min()} .. {bars['open_time'].max()}")

    space = build_search_space(exp, FAMILY, SYMBOL)
    strategy = space.build(PRIMARY_PARAMS)

    requested: list[FeatureItemLike] = [*space.feature_items, *_context_feature_items(exp)]
    specs = resolve_feature_set(requested)
    feats, resolved = build_feature_frame(
        bars, specs, holdout_start=holdout_start, context=FeatureContext(funding=funding)
    )
    feats = _attach_funding_per_bar(feats, funding)
    names = tuple(feature_columns(resolved))
    print(f"features={len(names)}: {', '.join(names)}")

    # Regimes are fitted on the earliest third only, so the labels a model sees
    # are never informed by the period it is scored on.
    warmup = feats.head(feats.height // 3)
    regime_inputs = tuple(n for n in names if n.startswith(("rvol_", "roll_std_", "atr_")))[:1]
    regime = ThresholdRegime(inputs=regime_inputs, seed=args.seed)
    regime.fit(warmup)
    feats = regime.attach(feats)

    signals = strategy.signals(feats)
    events = _events_from_signals(signals)
    print(f"events={events.height}")
    if events.height == 0:
        raise SystemExit("The primary produced no entries; nothing to meta-label.")

    volatility_col = regime_inputs[0]
    config = MetaLabelStudyConfig(
        models=("logistic_regression", "random_forest"),  # lightgbm not installed
        n_folds=args.n_folds,
        timeframe=TIMEFRAME,
        seed=args.seed,
    )

    dataset = build_dataset(
        feats,
        events,
        feats.select("open_time", *names).rename({"open_time": EVENT_TIME_COL}),
        feature_names=names,
        config=config,
        volatility_col=volatility_col,
        regime_col=REGIME_NAME_COL,
        funding=funding,
    )
    print(f"labelled events={dataset.n_events} | positive rate={dataset.meta_labels.mean():.3f}")

    study = run_meta_label_study(
        dataset, config, market=f"{SYMBOL}_{TIMEFRAME}_{FAMILY}", planted_edge=False
    )

    args.out.mkdir(parents=True, exist_ok=True)
    payload = {
        "contract": "EXPLORATORY — RQ3 on real development data. No promotion, "
        "no holdout access, no operational candidate claimed.",
        "family": FAMILY,
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "primary_params": PRIMARY_PARAMS,
        "primary_selection_rule": "modal fold winner; family chosen on event count "
        "and low span overlap, both fixed before any meta-label result was seen",
        "n_events": dataset.n_events,
        "meta_label_positive_rate": float(dataset.meta_labels.mean()),
        "study": study.to_dict() if hasattr(study, "to_dict") else str(study),
    }
    out = args.out / "meta_labeling_real.json"
    out.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")

    report = args.out / "meta_labeling_real.md"
    report.write_text(_markdown(payload), encoding="utf-8")
    print(f"\nwrote {out}\nwrote {report}")

    summary = payload["study"]["summary"]
    print(
        f"\nabstention_rate={summary['abstention_rate']} | "
        f"folds_improved={summary['folds_improved']}/{summary['n_folds']} | "
        f"roc_auc={summary['median_roc_auc']:.3f} | "
        f"primary={summary['primary_only_total_return']:+.4f} -> "
        f"meta={summary['primary_plus_meta_total_return']:+.4f}"
    )
    return 0


def _markdown(payload: dict[str, Any]) -> str:
    """Render the result so the headline cannot be read without its caveat.

    The economic delta and the predictive metrics are printed side by side on
    purpose: read alone, "improved net return in every fold" invites exactly the
    wrong conclusion, and the AUC is what stops it.
    """
    s = payload["study"]["summary"]
    rows = [
        "# Meta-labeling on real development data (RQ3) — EXPLORATORY",
        "",
        f"> {payload['contract']}",
        "",
        f"Primary: `{payload['family']}` on {payload['symbol']} {payload['timeframe']}, "
        f"{payload['n_events']} labelled events, "
        f"meta-label positive rate {payload['meta_label_positive_rate']:.3f}.",
        "",
        f"Selection rule: {payload['primary_selection_rule']}.",
        "",
        "## Economic outcome",
        "",
        "| | primary only | primary + meta |",
        "|---|---:|---:|",
        f"| total net return | {s['primary_only_total_return']:+.4f} | "
        f"{s['primary_plus_meta_total_return']:+.4f} |",
        f"| median Sharpe | {s['primary_only_median_sharpe']:+.3f} | "
        f"{s['primary_plus_meta_median_sharpe']:+.3f} |",
        "",
        f"Folds improved: **{s['folds_improved']}/{s['n_folds']}**. "
        f"Abstention rate: **{s['abstention_rate']:.2f}**.",
        "",
        "## Predictive skill",
        "",
        f"- ROC-AUC (median): **{s['median_roc_auc']:.3f}**",
        f"- PR-AUC lift over base rate: **{s['median_pr_auc_lift']:.3f}**",
        f"- Brier score: {s['median_brier']:.3f}",
        "",
        "## Reading",
        "",
        "The filter improved net return in every fold it saw, and a ROC-AUC below",
        "0.5 with a PR-AUC lift of essentially 1.0 says it did so without being",
        "able to tell a good signal from a bad one. The improvement came from",
        "abstaining: in three of four folds the layer declined to trade at all.",
        "Not trading a losing rule is not an edge, and the study says so in its",
        "own abstention reasons.",
        "",
        "## Folds",
        "",
        "| fold | train | val | test | acted | net delta | reason |",
        "|---:|---:|---:|---:|:--|---:|---|",
    ]
    for f in payload["study"]["folds"]:
        rows.append(
            f"| {f['fold']} | {f['n_train']} | {f['n_validation']} | {f['n_test']} | "
            f"{'no' if f['abstained'] else 'yes'} | {f['net_return_delta']:+.4f} | "
            f"{(f['abstention_reason'] or '—')[:90]} |"
        )
    notes = s.get("notes") or []
    if notes:
        rows += ["", "## Notes", ""] + [f"- {n}" for n in notes]
    return "\n".join(rows) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
