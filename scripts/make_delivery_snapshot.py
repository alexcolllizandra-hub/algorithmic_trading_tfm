"""Build the clean TFM delivery repository from the current commit.

Run with: ``uv run python scripts/make_delivery_snapshot.py [dest]``
(default dest: sibling directory ``../perp-lab-entrega``)

Exports the TRACKED tree of HEAD via ``git archive`` (so no local junk can
leak), prunes the internal working documents that are not part of the
deliverable, and initialises a fresh single-commit git history. The research
repository and its full history remain untouched; this produces the copy the
author pushes to the public submission GitHub.

Kept: source code, tests, scripts, notebooks, configs + data manifests,
frozen evidence (reports/), the web app, CI, the ADRs and the methodology
docs the thesis cites.

Pruned (internal scaffolding): AI-assistant configuration (.cursor, .claude,
AGENTS.md), roadmaps and progress journals, platform/research planning notes,
the thesis drafting kitchen (docs/thesis), audit scratch notes, and this
packaging script itself.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PRUNE = [
    ".cursor",
    ".claude",
    "AGENTS.md",
    "docs/audit",
    "docs/notebooks_plan.md",
    "docs/platform",
    "docs/progress.md",
    "docs/research",
    "docs/research_dashboard.md",
    "docs/roadmap",
    "docs/roadmap.md",
    "docs/thesis",
    "scripts/make_delivery_snapshot.py",
]


def run(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else repo.parent / "perp-lab-entrega"
    commit = run(["git", "rev-parse", "HEAD"], cwd=repo)
    described = run(["git", "describe", "--tags", "--always"], cwd=repo)

    if dest.exists():
        raise SystemExit(f"Destination {dest} already exists; remove it first.")

    with tempfile.TemporaryDirectory() as tmp:
        tar_path = Path(tmp) / "snapshot.tar"
        with tar_path.open("wb") as fh:
            subprocess.run(
                ["git", "archive", "--format=tar", "HEAD"],
                cwd=repo,
                stdout=fh,
                check=True,
            )
        dest.mkdir(parents=True)
        with tarfile.open(tar_path) as tar:
            tar.extractall(dest, filter="data")

    pruned: list[str] = []
    for rel in PRUNE:
        target = dest / rel
        if target.is_dir():
            shutil.rmtree(target)
            pruned.append(rel + "/")
        elif target.exists():
            target.unlink()
            pruned.append(rel)

    n_files = sum(1 for p in dest.rglob("*") if p.is_file())
    run(["git", "init", "-b", "main"], cwd=dest)
    run(["git", "add", "-A"], cwd=dest)
    run(
        [
            "git",
            "commit",
            "-m",
            f"perp-lab — TFM delivery snapshot ({described})\n\n"
            f"Clean export of research commit {commit[:12]}. The full research\n"
            "history (including working notes) is retained privately and is\n"
            "available on request.",
        ],
        cwd=dest,
    )

    print(f"delivery repo: {dest}")
    print(f"source commit: {commit[:12]} ({described})")
    print(f"files: {n_files}")
    print("pruned:", ", ".join(pruned))
    print("\nTo publish:  cd", dest)
    print("  git remote add origin <your-github-url> && git push -u origin main")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
