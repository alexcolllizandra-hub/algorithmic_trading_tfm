"""Build the consolidated study payload the dashboard serves.

The resampling fan is the expensive part — a thousand paths over thirty
thousand bars for each of twenty-two family/asset series — so it is computed
once here and written to disk rather than on every request.

Usage:
    uv run python scripts/build_study_dashboard.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from perp_lab.reporting.study_dashboard import build_payload
from perp_lab.utils.logging import get_logger

log = get_logger("study_dashboard")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/study_closure/study_dashboard.json"),
    )
    parser.add_argument(
        "--include-holdout",
        action="store_true",
        help=(
            "Embed the holdout reading. Only for an audited publication; the "
            "API gates it independently and will still withhold it by default."
        ),
    )
    args = parser.parse_args()

    payload = build_payload(args.root, include_holdout=args.include_holdout)

    output = args.root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=1, sort_keys=False), encoding="utf-8")

    size_mb = output.stat().st_size / 1e6
    log.info(
        "Wrote %s (%d families, %.1f MB)",
        output,
        len(payload["families"]),
        size_mb,
    )
    for row in sorted(payload["families"], key=lambda r: -r["total_return"])[:5]:
        log.info(
            "  %-24s %-8s total=%+.2f%% sharpe=%+.2f mc_p50=%+.2f%%",
            row["family"],
            row["symbol"],
            100 * row["total_return"],
            row["sharpe"],
            100 * row["monte_carlo"]["terminal"]["p50"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
