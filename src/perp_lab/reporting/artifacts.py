"""Export figures and tables with reproducibility metadata sidecars.

Every saved artifact gets a JSON sidecar under ``reports/metadata/eda/`` that
records enough context to regenerate it: the originating notebook, dataset ids
and content hashes, configuration, the exact temporal range, the generation
timestamp, the code commit (when available) and the output path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
from matplotlib.figure import Figure

from perp_lab.data.manifest import read_git_commit


@dataclass
class ArtifactContext:
    """Shared provenance for the artifacts produced by one notebook.

    Parameters
    ----------
    notebook:
        Notebook identifier, e.g. ``"01_data_acquisition_and_quality"``.
    figures_dir, tables_dir, metadata_dir:
        Output directories (created on demand).
    datasets:
        Mapping ``dataset_id -> sha256`` for the datasets the notebook uses.
    config:
        A small JSON-serialisable snapshot of the active configuration.
    period:
        Human-readable active temporal range, e.g.
        ``"2020-01-01 .. 2025-12-31 (development)"``.
    repo_root:
        Root used to read the current git commit (best effort).
    """

    notebook: str
    figures_dir: Path = Path("reports/figures/eda")
    tables_dir: Path = Path("reports/tables/eda")
    metadata_dir: Path = Path("reports/metadata/eda")
    datasets: dict[str, str] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    period: str = ""
    repo_root: str | Path = "."

    def __post_init__(self) -> None:
        self.figures_dir = Path(self.figures_dir)
        self.tables_dir = Path(self.tables_dir)
        self.metadata_dir = Path(self.metadata_dir)

    def _base_metadata(self, analysis_id: str, caption: str, output_path: Path) -> dict[str, Any]:
        return {
            "notebook": self.notebook,
            "analysis_id": analysis_id,
            "caption": caption,
            "period": self.period,
            "datasets": self.datasets,
            "config": self.config,
            "generated_at": datetime.now(UTC).isoformat(),
            "code_commit": read_git_commit(self.repo_root),
            "output_path": str(output_path).replace("\\", "/"),
        }

    def _write_metadata(self, name: str, metadata: dict[str, Any]) -> Path:
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        meta_path = self.metadata_dir / f"{name}.json"
        meta_path.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
        return meta_path


def save_figure(
    fig: Figure,
    name: str,
    ctx: ArtifactContext,
    *,
    caption: str = "",
    dpi: int = 300,
    vector: bool = True,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Save ``fig`` as a >=300 DPI PNG (plus a vector PDF) and a metadata sidecar.

    Returns the PNG path. When ``vector`` is true a thesis-ready ``.pdf`` is also
    written next to the PNG so figures can be embedded without rasterisation.
    """
    ctx.figures_dir.mkdir(parents=True, exist_ok=True)
    out_path = ctx.figures_dir / f"{name}.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight")
    formats = ["png"]
    if vector:
        fig.savefig(ctx.figures_dir / f"{name}.pdf", bbox_inches="tight")
        formats.append("pdf")

    metadata = ctx._base_metadata(name, caption, out_path)
    metadata["kind"] = "figure"
    metadata["dpi"] = dpi
    metadata["formats"] = formats
    if extra:
        metadata["extra"] = extra
    ctx._write_metadata(name, metadata)
    return out_path


def _to_markdown(df: pl.DataFrame, float_precision: int = 6) -> str:
    """Render a small Polars dataframe as a GitHub-flavoured Markdown table."""
    cols = df.columns

    def fmt(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:.{float_precision}g}"
        return str(value)

    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.iter_rows()]
    return "\n".join([header, sep, *rows]) + "\n"


def save_table(
    df: pl.DataFrame,
    name: str,
    ctx: ArtifactContext,
    *,
    caption: str = "",
    also_csv: bool = True,
    float_precision: int = 6,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Save a small dataframe as a versionable Markdown table (+ optional CSV).

    Returns the Markdown path. A metadata sidecar is written alongside. Large
    tables should not be committed; keep exported tables compact and summarise
    instead.
    """
    ctx.tables_dir.mkdir(parents=True, exist_ok=True)
    md_path = ctx.tables_dir / f"{name}.md"
    title = f"**Table — {caption}**\n\n" if caption else ""
    md_path.write_text(title + _to_markdown(df, float_precision), encoding="utf-8")

    if also_csv:
        df.write_csv(ctx.tables_dir / f"{name}.csv")

    metadata = ctx._base_metadata(name, caption, md_path)
    metadata["kind"] = "table"
    metadata["n_rows"] = df.height
    metadata["columns"] = df.columns
    if extra:
        metadata["extra"] = extra
    ctx._write_metadata(name, metadata)
    return md_path
