"""Publication-quality reporting helpers: house style and artifact export.

Notebooks call these helpers so every figure and table is exported with a
consistent academic style and an accompanying reproducibility metadata sidecar
(dataset ids/hashes, configuration, temporal range, code commit, output path).
"""

from perp_lab.reporting.artifacts import (
    ArtifactContext,
    save_figure,
    save_table,
)
from perp_lab.reporting.style import (
    ASSET_COLORS,
    REGIME_COLORS,
    TIMEFRAME_COLORS,
    apply_house_style,
    asset_color,
    regime_color,
    timeframe_color,
)

__all__ = [
    "ASSET_COLORS",
    "REGIME_COLORS",
    "TIMEFRAME_COLORS",
    "ArtifactContext",
    "apply_house_style",
    "asset_color",
    "regime_color",
    "save_figure",
    "save_table",
    "timeframe_color",
]
