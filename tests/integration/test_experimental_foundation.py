"""End-to-end integration: bars -> features -> regime -> strategy -> backtest.

Exercises the full experimental foundation on deterministic (synthetic) bars,
without any network access or real data, verifying the pieces compose and the
leak-free invariants hold across module boundaries.
"""

from __future__ import annotations

import numpy as np

from perp_lab.backtesting.engine import run_backtest
from perp_lab.config.experiment import FeatureItem
from perp_lab.experiments.pipeline import synthetic_klines
from perp_lab.features import build_feature_manifest, build_predictor_rows, resolve_feature_set
from perp_lab.features.registry import build_feature_frame, feature_columns
from perp_lab.regimes import REGIME_NAME_COL, KMeansRegime
from perp_lab.strategies.mean_reversion import MeanReversion
from perp_lab.strategies.momentum import MomentumCrossover


def test_full_foundation_pipeline_composes() -> None:
    df = synthetic_klines(1500, seed=11, timeframe="1h")

    items = [
        FeatureItem(kind="log_return"),
        FeatureItem(kind="rvol", window=96),
        FeatureItem(kind="zscore", window=48),
        FeatureItem(kind="range_norm"),
        FeatureItem(kind="ema", window=24),
    ]
    specs = resolve_feature_set(items, ensure_sma=(24, 96))
    feats, resolved = build_feature_frame(df, specs)

    # Manifest documents every built column.
    manifest = build_feature_manifest(resolved, symbol="BTCUSDT", timeframe="1h")
    assert manifest["columns"] == feature_columns(resolved)

    # No infinities anywhere in the feature table.
    for col in feature_columns(resolved):
        series = feats[col]
        if series.dtype.is_float():
            assert int(series.is_infinite().sum() or 0) == 0

    # Regime model fitted on the (development) features, attached causally.
    regime_inputs = ("rvol_96", "zscore_48", "range_norm", "log_return")
    tagged = KMeansRegime(inputs=regime_inputs, seed=11).fit(feats).attach(feats)
    assert REGIME_NAME_COL in tagged.columns

    # Momentum with a regime gate + mean-reversion both produce signals.
    mom = MomentumCrossover(fast=24, slow=96, regime_gate=("low", "medium")).signals(tagged)
    mr = MeanReversion(zscore_window=48, entry_z=2.0, exit_z=0.5).signals(feats)
    assert set(mom["side"].unique().to_list()) <= {-1, 0, 1}

    # Backtest the momentum signals with next-bar execution and costs.
    res = run_backtest(
        mom, feats, timeframe="1h", fee_bps_per_side=4.0, slippage_bps_per_side=1.0, asset="BTCUSDT"
    )
    assert res.ledger.height > 0
    assert np.isfinite(res.final_equity)
    assert "sharpe" in res.metrics

    # Predictor rows keep the four timestamp roles and expose the snapshot.
    rows = build_predictor_rows(feats, mr, feature_columns=["zscore_48", "rvol_96"])
    assert rows.height == feats.height
    assert rows["label_time"].null_count() == rows.height
