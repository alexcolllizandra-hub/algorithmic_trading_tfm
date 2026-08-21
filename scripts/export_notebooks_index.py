"""Export the notebook index for the /cuadernos page.

Run with: ``uv run python scripts/export_notebooks_index.py``

One JSON (``apps/web/public/data/notebooks.json``) describing the eight
analysis notebooks: title and cell count read from each ``.ipynb``, the
frozen figures and tables inventoried from ``reports/figures/<theme>`` and
``reports/tables/<theme>``, the builder script that regenerates the notebook
deterministically, and the destination chapter in the thesis as recorded in
``docs/thesis/mapa_capitulos_artefactos.md`` (the committed chapter map).
Nothing here is invented: every list is a directory listing and every label
cites its source document.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

FIGURES = Path("reports/figures")
TABLES = Path("reports/tables")
OUT = Path("apps/web/public/data/notebooks.json")

# Theme directory, builder script and thesis-chapter destination per notebook.
# Chapters come from docs/thesis/mapa_capitulos_artefactos.md ("Inventario de
# figuras existentes" table); the sintesis chain is the CHAIN list in
# scripts/build_sintesis_notebook.py.
NOTEBOOKS = [
    {
        "id": "01",
        "file": "01_comprehensive_exploratory_data_analysis.ipynb",
        "theme": "eda",
        "builder": "scripts/build_eda_notebook.py",
        "chapter": "Cap. 4 (datos) y anexo EDA",
    },
    {
        "id": "02",
        "file": "02_causal_features_and_leakage.ipynb",
        "theme": "features",
        "builder": "scripts/build_features_notebook.py",
        "chapter": "Cap. 5",
    },
    {
        "id": "03",
        "file": "03_backtesting_and_walk_forward.ipynb",
        "theme": "backtest",
        "builder": "scripts/build_backtest_notebook.py",
        "chapter": "Caps. 4–5",
    },
    {
        "id": "04",
        "file": "04_strategy_search_and_overfitting.ipynb",
        "theme": "search",
        "builder": "scripts/build_search_notebook.py",
        "chapter": "Caps. 5–6",
    },
    {
        "id": "05",
        "file": "05_study_closure_and_multiple_testing.ipynb",
        "theme": "closure",
        "builder": "scripts/build_results_notebook.py",
        "chapter": "Caps. 6–7",
    },
    {
        "id": "06",
        "file": "06_meta_etiquetado_supervisado.ipynb",
        "theme": "ml",
        "builder": "scripts/build_ml_notebook.py",
        "chapter": "Cap. 5.8 y Cap. 6 (RQ3)",
    },
    {
        "id": "07",
        "file": "07_monte_carlo_nula.ipynb",
        "theme": "montecarlo",
        "builder": "scripts/build_montecarlo_notebook.py",
        "chapter": "Cap. 6 y anexo Monte Carlo (k03 = figura resumen del TFM)",
    },
    {
        "id": "08",
        "file": "08_sintesis.ipynb",
        "theme": None,
        "builder": "scripts/build_sintesis_notebook.py",
        "chapter": "Síntesis transversal (caps. 6–9)",
        # The synthesis computes nothing; it chains these frozen figures.
        "chain": [
            "f03", "g04", "h05", "h02", "i02", "i05",
            "j02", "j03", "m01", "m02", "k03", "k05",
        ],
    },
]


def notebook_title(path: Path) -> tuple[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cells = data["cells"]
    for cell in cells:
        if cell["cell_type"] == "markdown":
            first = "".join(cell["source"]).strip().splitlines()[0]
            return first.lstrip("# ").strip(), len(cells)
    return path.stem, len(cells)


def inventory(theme: str | None) -> tuple[list[dict], list[str]]:
    if theme is None:
        return [], []
    figures = []
    fig_dir = FIGURES / theme
    if fig_dir.exists():
        for png in sorted(fig_dir.glob("*.png")):
            figures.append({"id": png.stem, "kb": png.stat().st_size // 1024})
    tables = []
    tab_dir = TABLES / theme
    if tab_dir.exists():
        tables = sorted({p.stem for p in tab_dir.glob("*.csv")})
    return figures, tables


def main() -> int:
    items = []
    for spec in NOTEBOOKS:
        nb_path = Path("notebooks") / spec["file"]
        title, n_cells = notebook_title(nb_path)
        figures, tables = inventory(spec["theme"])
        items.append(
            {
                "id": spec["id"],
                "file": spec["file"],
                "title": title,
                "n_cells": n_cells,
                "theme": spec["theme"],
                "builder": spec["builder"],
                "chapter": spec["chapter"],
                "figures": figures,
                "tables": tables,
                "chain": spec.get("chain", []),
            }
        )
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "chapter_source": "docs/thesis/mapa_capitulos_artefactos.md",
        "notebooks": items,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    n_figs = sum(len(i["figures"]) for i in items)
    n_tabs = sum(len(i["tables"]) for i in items)
    print(f"{OUT} -> {OUT.stat().st_size // 1024} KB | notebooks={len(items)} figures={n_figs} tables={n_tabs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
