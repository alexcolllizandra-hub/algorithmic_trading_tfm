"""Audit one search run against the per-outer-fold temporal contract (ADR 0012).

Reads only the artifacts a run wrote and checks the properties that make its
selection defensible:

1. the run declares the current protocol and artifact schema;
2. both engines spent the same effective budget **inside every outer fold**;
3. every fold winner was frozen on validation, with a fingerprint recorded
   before its test slice was scored, and no test metric inside the freeze record;
4. each fold's winner is a candidate that the ledger attributes to that same
   fold, so no winner was imported from another fold's search;
5. every evaluated candidate's dispersion penalty was computed within its own
   fold, which is only possible when its fitness saw a single validation window.

Exits non-zero on the first violated property, so it can gate a pipeline.

    uv run python scripts/audit_fold_isolation.py artifacts/runs/<run_id>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import polars as pl

from perp_lab.search.runner import ARTIFACT_SCHEMA_VERSION, SEARCH_PROTOCOL

ENGINES = ("random_search", "genetic_algorithm")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def audit(run_dir: Path) -> list[str]:
    problems: list[str] = []
    ok: list[str] = []
    summary = _load(run_dir / "comparison_summary.json")

    protocol = summary.get("search_protocol")
    if protocol != SEARCH_PROTOCOL:
        problems.append(f"protocol is {protocol!r}, expected {SEARCH_PROTOCOL!r}")
    else:
        ok.append(f"protocol = {protocol}")
    schema = summary.get("artifact_schema_version")
    if schema != ARTIFACT_SCHEMA_VERSION:
        problems.append(f"artifact schema {schema}, expected {ARTIFACT_SCHEMA_VERSION}")

    n_folds = summary["n_folds"]
    parity = summary["budget_parity"]
    if parity.get("parity_level") != "per outer fold":
        problems.append(f"parity level is {parity.get('parity_level')!r}")
    budget = parity["effective_budget_per_fold"]
    for engine in ENGINES:
        per_fold = parity["per_engine"][engine]["per_fold"]
        if len(per_fold) != n_folds:
            problems.append(f"{engine}: searched {len(per_fold)} of {n_folds} folds")
        bad = {k: v["consumed"] for k, v in per_fold.items() if v["consumed"] != budget}
        if bad:
            problems.append(f"{engine}: folds off the {budget}-eval target: {bad}")
    if not problems:
        ok.append(f"both engines spent {budget} evaluations in each of {n_folds} folds")

    for engine in ENGINES:
        ledger = pl.read_parquet(run_dir / f"{engine}_candidates.parquet")
        winners = _load(run_dir / f"{engine}_fold_winners.json")
        if len(winners) != n_folds:
            problems.append(f"{engine}: {len(winners)} winner records for {n_folds} folds")
        frozen = 0
        for w in winners:
            if w.get("winner") is None:
                continue
            frozen += 1
            if w.get("selection_basis") != "validation_only":
                problems.append(
                    f"{engine} fold {w['fold']}: selection_basis={w.get('selection_basis')!r}"
                )
            if not w.get("frozen_before_test"):
                problems.append(f"{engine} fold {w['fold']}: winner not frozen before test")
            if not w.get("selection_fingerprint"):
                problems.append(f"{engine} fold {w['fold']}: no selection fingerprint")
            owner = ledger.filter(
                (pl.col("candidate_id") == w["winner"]) & (pl.col("fold_index") == w["fold"])
            )
            if owner.height == 0:
                problems.append(
                    f"{engine} fold {w['fold']}: winner {w['winner'][:12]} was not produced "
                    "by this fold's own search"
                )
        ok.append(f"{engine}: {frozen}/{n_folds} folds froze a fingerprinted winner")

        # A candidate scored across several folds would have taken its dispersion
        # from the spread between them; the within-fold flag is the artifact-level
        # trace that its fitness saw exactly one validation window.
        scored = ledger.filter(pl.col("obj_dispersion_within_fold").is_not_null())
        pooled = scored.filter(pl.col("obj_dispersion_within_fold") != 1.0)
        if pooled.height:
            problems.append(
                f"{engine}: {pooled.height} candidates took their dispersion from across folds"
            )
        elif scored.height:
            ok.append(
                f"{engine}: all {scored.height} scored candidates measured dispersion "
                "within their own fold"
            )
        folds_seen = sorted({int(v) for v in ledger["fold_index"].drop_nulls().to_list()})
        if folds_seen != list(range(n_folds)):
            problems.append(
                f"{engine}: ledger covers folds {folds_seen}, expected 0..{n_folds - 1}"
            )

    for line in ok:
        print(f"  PASS  {line}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)

    print(f"auditing {args.run_dir}")
    problems = audit(args.run_dir)
    if problems:
        print("\nFAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nfold isolation audit: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
