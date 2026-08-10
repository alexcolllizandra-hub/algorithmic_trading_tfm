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
from perp_lab.reporting.r3_gate import (
    R3ReportConsistencyError,
    R3ReportError,
    build_r3_thesis_report,
    render_r3_thesis_markdown,
    write_r3_thesis_report,
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
    "R3ReportConsistencyError",
    "R3ReportError",
    "apply_house_style",
    "asset_color",
    "build_r3_thesis_report",
    "regime_color",
    "render_r3_thesis_markdown",
    "save_figure",
    "save_table",
    "timeframe_color",
    "write_r3_thesis_report",
]
