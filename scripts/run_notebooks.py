"""Execute every EDA notebook in order from a clean kernel.

Portable (pure-Python) runner used both interactively and in CI. Each notebook
is executed in-place with a fresh kernel whose working directory is the
repository root, so the notebooks' relative ``configs/`` and ``data/`` paths
resolve regardless of where this script is launched from.

Usage::

    uv run python scripts/run_notebooks.py            # run all, in order
    uv run python scripts/run_notebooks.py 02 05       # run a subset by prefix

A JSON execution report is written to
``reports/metadata/eda/notebook_execution.json``.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"
REPORT_PATH = REPO_ROOT / "reports" / "metadata" / "eda" / "notebook_execution.json"
CELL_TIMEOUT_S = 1800


def _notebooks(selectors: list[str]) -> list[Path]:
    all_nb = sorted(p for p in NOTEBOOKS_DIR.glob("*.ipynb") if ".ipynb_checkpoints" not in str(p))
    if not selectors:
        return all_nb
    chosen: list[Path] = []
    for sel in selectors:
        chosen.extend(p for p in all_nb if p.name.startswith(sel))
    return chosen


def run_one(path: Path) -> dict[str, object]:
    """Execute a single notebook in-place; return an execution record."""
    nb = nbformat.read(path, as_version=4)
    client = NotebookClient(
        nb,
        timeout=CELL_TIMEOUT_S,
        kernel_name="python3",
        resources={"metadata": {"path": str(REPO_ROOT)}},
    )
    started = datetime.now(UTC)
    t0 = time.perf_counter()
    status = "ok"
    error = ""
    try:
        client.execute()
    except CellExecutionError as exc:
        status = "error"
        error = str(exc).splitlines()[-1] if str(exc) else "CellExecutionError"
    finally:
        elapsed = time.perf_counter() - t0
        nbformat.write(nb, path)
    return {
        "notebook": path.name,
        "status": status,
        "started_at": started.isoformat(),
        "elapsed_s": round(elapsed, 1),
        "error": error,
    }


def main(argv: list[str] | None = None) -> int:
    selectors = list(argv or sys.argv[1:])
    notebooks = _notebooks(selectors)
    if not notebooks:
        print("No notebooks found to execute.")
        return 1

    records: list[dict[str, object]] = []
    overall_ok = True
    for path in notebooks:
        print(f"Executing {path.name} ...", flush=True)
        record = run_one(path)
        records.append(record)
        overall_ok = overall_ok and record["status"] == "ok"
        print(f"  -> {record['status']} in {record['elapsed_s']}s", flush=True)
        if record["error"]:
            print(f"  !! {record['error']}", flush=True)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            {"generated_at": datetime.now(UTC).isoformat(), "results": records},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nExecution report written to {REPORT_PATH.relative_to(REPO_ROOT)}")
    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
