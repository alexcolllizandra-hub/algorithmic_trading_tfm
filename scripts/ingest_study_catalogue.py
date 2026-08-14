"""Index the closed study into the catalogue without rewriting any artifact.

Usage::

    uv run python scripts/ingest_study_catalogue.py
    uv run python scripts/ingest_study_catalogue.py --root .

Safe to run twice. The second pass updates rows in place and must report the
same counts. The frozen holdout is registered as ``HOLDOUT_LOCKED``; its
observations are not read.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from perp_lab.catalog.ingest import ingest_study
from perp_lab.catalog.session import build_engine, session_scope
from perp_lab.utils.logging import get_logger

log = get_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path())
    parser.add_argument(
        "--skip-parquets",
        action="store_true",
        help="Index structure and metrics only; do not hash every ledger.",
    )
    args = parser.parse_args()

    engine = build_engine()
    with session_scope(engine) as session:
        report = ingest_study(session, args.root, register_parquets=not args.skip_parquets)
    log.info("ingest complete: %s", json.dumps(report.as_dict(), indent=2))
    if report.mismatches:
        log.error("catalogue disagrees with the source artifacts; do not point the dashboard at it")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
