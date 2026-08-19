"""Validate the M1/M2 meta-labeling machinery on synthetic markets.

EXPLORATORY / INFRASTRUCTURE-ONLY. This script generates its own data, so it
loads no market file and cannot touch the frozen holdout. It runs the whole
layer -- cost-aware triple-barrier labels, purged and embargoed walk-forward
folds, three competing classifiers, calibration, a validation-only decision
threshold, and the primary_only vs primary_plus_meta_labeling comparison -- on a
market with a planted edge and on a pure-noise control, and writes the report to
`reports/meta_labeling_synthetic/`.

    uv run python scripts/validate_meta_labeling_synthetic.py
    uv run python scripts/validate_meta_labeling_synthetic.py --seeds 42 --quick

Nothing it produces is a trading result or an operational candidate.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from perp_lab.meta_labeling.study import MetaLabelStudyConfig, study_from_market
from perp_lab.meta_labeling.synthetic import (
    SyntheticSpec,
    generate_noise_market,
    generate_signal_market,
)
from perp_lab.reporting.meta_labeling_synthetic import (
    build_synthetic_validation_report,
    write_synthetic_validation_report,
)

OUTPUT_DIR = Path("reports/meta_labeling_synthetic")
DEFAULT_SEEDS = (42, 43, 44)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(DEFAULT_SEEDS),
        help="Seeds to repeat both markets over (default: 42 43 44).",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Smaller markets and fewer folds, for a fast smoke run.",
    )
    parser.add_argument(
        "--no-shap",
        action="store_true",
        help="Skip the SHAP explanation of the last winning model.",
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.quick:
        spec_kwargs = {"n_bars": 12_000}
        config = MetaLabelStudyConfig(
            n_folds=3, test_bars=1_500, validation_bars=1_500, min_train_bars=3_000
        )
    else:
        spec_kwargs = {"n_bars": 20_000}
        config = MetaLabelStudyConfig()

    signal_studies = []
    noise_studies = []
    for seed in args.seeds:
        spec = SyntheticSpec(seed=seed, **spec_kwargs)
        run_config = MetaLabelStudyConfig(**{**config.__dict__, "seed": seed})
        for generate, bucket in (
            (generate_signal_market, signal_studies),
            (generate_noise_market, noise_studies),
        ):
            market = generate(spec)
            study = study_from_market(
                market, run_config, explain_winner=not args.no_shap and seed == args.seeds[0]
            )
            summary = study.summary()
            print(
                f"seed {seed} {market.name:6s} "
                f"primary {summary['primary_only_total_return']:+.2%} "
                f"meta {summary['primary_plus_meta_total_return']:+.2%} "
                f"acted {summary['folds_acted']}/{summary['n_folds']} "
                f"profitable {summary['folds_profitable']}/{summary['n_folds']}"
            )
            bucket.append(study)

    report = build_synthetic_validation_report(signal_studies, noise_studies, seeds=args.seeds)
    written = write_synthetic_validation_report(report, args.output_dir)
    verdict = report["verdict"]
    print(f"\nmachinery_validated: {verdict['machinery_validated']}")
    for name, passed in verdict["checks"].items():
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
    for kind, path in written.items():
        print(f"wrote {kind}: {path}")
    return 0 if verdict["machinery_validated"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
