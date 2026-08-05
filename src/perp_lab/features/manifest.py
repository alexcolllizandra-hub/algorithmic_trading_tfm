"""Machine-readable feature manifest.

A *manifest* is a JSON-serialisable description of exactly which features were
built for a run: their names, families, source columns, formulas/parameters,
lookback, warm-up, decision-time availability and missing-data rules. It is the
audit record that lets a reader reproduce and interpret a feature table without
reading the code, and it is written into every run's artifact directory.

The manifest is derived purely from resolved :class:`FeatureSpec` records (see
:mod:`perp_lab.features.spec`), so it can never drift from what the engine
actually computes.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from perp_lab.features.spec import IMPL_VERSION, FeatureSpec

MANIFEST_SCHEMA_VERSION = "1.0"

# One-line human-readable formula per kind (documentation only; the numerical
# definition lives in perp_lab.features.causal / .context).
_FORMULAS: dict[str, str] = {
    "log_return": "ln(P_t / P_{t-k})",
    "cum_return": "ln(P_t / P_0) (expanding, causal)",
    "momentum": "ln(P_t / P_{t-w})",
    "sma": "mean(P) over trailing w bars",
    "ema": "ewm_mean(P, span=w, adjust=False)",
    "ma_distance": "sma_fast / sma_slow - 1",
    "price_dist_sma": "P_t / sma_w - 1",
    "zscore": "(P_t - mean_w) / std_w",
    "roll_std": "std(P) over trailing w bars",
    "rvol": "std(log-returns) over trailing w bars",
    "atr": "mean(true_range) over trailing w bars",
    "true_range": "max(H-L, |H-C_{t-1}|, |L-C_{t-1}|)",
    "range_norm": "(H - L) / C",
    "rel_volume": "V_t / mean(V) over trailing w bars",
    "volume_zscore": "(V_t - mean_w) / std_w",
    "hour_cyclical": "sin/cos(2*pi*hour/24)",
    "dow_cyclical": "sin/cos(2*pi*dow/7)",
    "taker_buy_ratio": "lag(taker_buy_quote / quote_volume, L)",
    "taker_buy_imbalance": "lag(2 * taker_buy_quote / quote_volume - 1, L)",
    "funding_rate": "as-of-past funding rate",
    "basis": "(mark - index) / index",
    "oi_change": "ln(OI_t / OI_{t-w}) (as-of past)",
    "xasset_rel_return": "r_self - r_peer (1-bar log return)",
    "xasset_rel_momentum": "mom_self(w) - mom_peer(w)",
    "xasset_corr": "rolling corr(r_self, r_peer) over w bars",
}


def _missing_data_rule(spec: FeatureSpec) -> str:
    """Human-readable missing-data / warm-up rule for a feature."""
    parts = [spec.null_policy or "warm-up rows are null"]
    if spec.warmup:
        parts.append(f"{spec.warmup} warm-up rows null")
    if spec.requires_context:
        parts.append("null if the auxiliary input has no value at/before the bar")
    return "; ".join(parts)


def spec_manifest_entry(spec: FeatureSpec) -> dict[str, object]:
    """One manifest record for a resolved feature spec."""
    entry = spec.to_dict()
    entry["formula"] = _FORMULAS.get(spec.kind, "")
    entry["missing_data_rule"] = _missing_data_rule(spec)
    entry["required_source_columns"] = list(spec.inputs)
    entry["availability_timestamp"] = spec.availability
    return entry


def build_feature_manifest(
    specs: Sequence[FeatureSpec],
    *,
    symbol: str,
    timeframe: str,
    dataset_id: str | None = None,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    """Assemble the full, JSON-serialisable feature manifest for a run."""
    entries = [spec_manifest_entry(s) for s in specs]
    columns = [c for s in specs for c in s.columns]
    families = sorted({s.family for s in specs})
    return {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "impl_version": IMPL_VERSION,
        "generated_at": (generated_at or datetime.now(UTC)).isoformat(),
        "symbol": symbol,
        "timeframe": timeframe,
        "dataset_id": dataset_id,
        "n_features": len(specs),
        "n_columns": len(columns),
        "families": families,
        "columns": columns,
        "features": entries,
    }
