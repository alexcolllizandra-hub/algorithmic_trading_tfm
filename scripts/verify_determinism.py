"""Execute a notebook twice and prove its artifacts are byte-identical.

Determinism is a property this project verifies, never asserts. PNGs and CSVs
from matplotlib/polars carry no timestamps, so two honest runs of a
deterministic notebook hash identically; if they do not, a seed is leaking or
an input moved, and no amount of 'the seed is fixed' talk overrides the hash.

    uv run python scripts/verify_determinism.py \
        notebooks/05_study_closure_and_multiple_testing.ipynb \
        "reports/tables/closure/*.csv" "reports/figures/closure/*.png"

Exit 0 when every artifact matches across the two executions; exit 1 with the
list of divergent files otherwise. The executed copies are discarded.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


def _hash_matching(patterns: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for pattern in patterns:
        for p in sorted(Path().glob(pattern)):
            if p.is_file():
                out[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _execute(notebook: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "jupyter",
                "nbconvert",
                "--to",
                "notebook",
                "--execute",
                str(notebook),
                "--output-dir",
                tmp,
                "--output",
                "executed.ipynb",
            ],
            check=True,
            capture_output=True,
            text=True,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=Path)
    parser.add_argument("patterns", nargs="+", help="globs of the artifacts the notebook writes")
    args = parser.parse_args(argv)

    print(f"run 1: {args.notebook}")
    _execute(args.notebook)
    first = _hash_matching(args.patterns)
    if not first:
        print("no artifacts matched the given patterns; nothing to verify")
        return 1

    print(f"run 2: {args.notebook}")
    _execute(args.notebook)
    second = _hash_matching(args.patterns)

    divergent = sorted(
        name for name in first.keys() | second.keys() if first.get(name) != second.get(name)
    )
    if divergent:
        print(f"\nNOT deterministic: {len(divergent)} of {len(first)} artifacts differ")
        for name in divergent:
            print(f"  {name}")
        return 1
    print(f"\ndeterministic: {len(first)} artifacts byte-identical across two executions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
