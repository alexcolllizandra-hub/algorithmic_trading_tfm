"""Fail the commit when a stale claim reappears in docs/ or scripts/.

Two stale claims already slipped into prose this month ('holdout untouched'
after the partition was consumed; 'specified but never implemented' after the
meta-labeling layer ran on real data). This check exists so the third one is
caught by the hook and not by the tribunal.

Frozen historical records (dated ADRs, frozen gate pre-specifications) keep
their original wording by design; each carries a dated status note instead.
Those exact (file, phrase) pairs are allowlisted below. Any NEW occurrence --
a new file, or a new phrase in an allowlisted file -- fails.

Run manually:  python scripts/check_stale_claims.py
Wired via:     .githooks/pre-commit  (git config core.hooksPath .githooks)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PHRASES = (
    "holdout untouched",
    "holdout intacto",
    "never opened",
    "provably untouched",
    "nunca se ha abierto",
    "specified but never implemented",
    "no promoted candidate pending",
)

SCAN_DIRS = ("docs", "scripts")
SCAN_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".txt"}


def tracked_files(root: Path) -> set[str] | None:
    """Paths git tracks under the scanned dirs; None when git is unavailable.

    Only tracked prose can reach a reader, so untracked local files are not
    this checker's business and must not fail the hook.
    """
    try:
        out = subprocess.run(
            ["git", "ls-files", "--", *SCAN_DIRS],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return {line.strip() for line in out.splitlines() if line.strip()}


# Frozen bodies whose wording is historical and governed by a dated status
# note in the same file. Path separators normalised to '/'.
ALLOWLIST: dict[str, set[str]] = {
    "docs/decisions/0003-cutoff-and-holdout-window.md": {
        "never opened",
        "holdout untouched",
        "provably untouched",
    },
    "docs/decisions/0006-experimental-vertical-slice-and-run-tracking.md": {
        "holdout untouched",
        "never opened",
    },
    "docs/decisions/0012-outer-fold-contamination-in-candidate-search.md": {"holdout untouched"},
    "docs/decisions/0015-r3-family-evaluation-negative.md": {"never opened"},
    "docs/methodology/final_holdout_evaluation.md": {"never opened"},
    "docs/methodology/gate_s1_batch_01.md": {"holdout untouched"},
    # This checker quotes the phrases in order to ban them.
    "scripts/check_stale_claims.py": set(PHRASES),
    "docs/methodology/holdout_audit_status.md": set(PHRASES),
}


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    failures: list[str] = []
    tracked = tracked_files(root)
    for scan_dir in SCAN_DIRS:
        base = root / scan_dir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            rel = path.relative_to(root).as_posix()
            if tracked is not None and rel not in tracked:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore").lower()
            except OSError:
                continue
            allowed = ALLOWLIST.get(rel, set())
            for phrase in PHRASES:
                if phrase in text and phrase not in allowed:
                    for lineno, line in enumerate(
                        path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
                    ):
                        if phrase in line.lower():
                            failures.append(f"{rel}:{lineno}: {phrase!r} -> {line.strip()[:90]}")
    if failures:
        print("Stale claims found (fix the text or, for a frozen historical record,")
        print("add a dated status note and the exact pair to ALLOWLIST):\n")
        print("\n".join(failures))
        return 1
    print(f"check_stale_claims: clean ({len(PHRASES)} phrases over {'/'.join(SCAN_DIRS)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
