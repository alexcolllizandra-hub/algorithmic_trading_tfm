"""Reporting artifact export tests (figures, tables, metadata sidecars)."""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import polars as pl

from perp_lab.reporting import (
    ArtifactContext,
    apply_house_style,
    asset_color,
    save_figure,
    save_table,
)


def _ctx(tmp_path) -> ArtifactContext:
    return ArtifactContext(
        notebook="test_nb",
        figures_dir=tmp_path / "figures",
        tables_dir=tmp_path / "tables",
        metadata_dir=tmp_path / "metadata",
        datasets={"ds1": "deadbeef"},
        config={"seed": 42},
        period="2020..2025",
        repo_root=tmp_path,
    )


def test_apply_house_style_and_colors():
    apply_house_style()
    assert asset_color("BTCUSDT") != asset_color("ETHUSDT")
    assert asset_color("UNKNOWN") == asset_color("UNKNOWN")


def test_save_figure_writes_png_and_metadata(tmp_path):
    ctx = _ctx(tmp_path)
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [0, 1, 4])
    png = save_figure(fig, "demo_fig", ctx, caption="Demo figure")
    assert png.exists()
    meta = json.loads((ctx.metadata_dir / "demo_fig.json").read_text(encoding="utf-8"))
    assert meta["kind"] == "figure"
    assert meta["datasets"] == {"ds1": "deadbeef"}
    assert meta["caption"] == "Demo figure"


def test_save_table_writes_markdown_csv_and_metadata(tmp_path):
    ctx = _ctx(tmp_path)
    df = pl.DataFrame({"metric": ["mean", "std"], "value": [0.1, 0.2]})
    md = save_table(df, "demo_table", ctx, caption="Demo table")
    assert md.exists()
    assert (ctx.tables_dir / "demo_table.csv").exists()
    content = md.read_text(encoding="utf-8")
    assert "| metric | value |" in content
    meta = json.loads((ctx.metadata_dir / "demo_table.json").read_text(encoding="utf-8"))
    assert meta["kind"] == "table"
    assert meta["n_rows"] == 2
