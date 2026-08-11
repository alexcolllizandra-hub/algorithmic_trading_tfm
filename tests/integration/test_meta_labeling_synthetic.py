"""The M1/M2 validation itself: does the layer behave on data we already know?

EXPLORATORY / INFRASTRUCTURE-ONLY. These tests assert properties of the
*machinery*, on generated markets, and say nothing about any real asset.

Two claims are checked, and the second matters more than the first:

1. on a market with a planted edge, the meta-label layer improves the primary
   rule's economics out of sample;
2. on a pure-noise control it does **not** end up profitable — a layer that only
   ever passes claim 1 is indistinguishable from one that overfits.

The configuration is smaller than the one in
``scripts/validate_meta_labeling_synthetic.py`` so the suite stays quick; the
full run is the reported artifact.
"""

from __future__ import annotations

import numpy as np
import pytest

from perp_lab.meta_labeling.study import (
    META_ARM,
    PRIMARY_ARM,
    MetaLabelStudyConfig,
    study_from_market,
)
from perp_lab.meta_labeling.synthetic import (
    SyntheticSpec,
    generate_noise_market,
    generate_signal_market,
)
from perp_lab.reporting.meta_labeling_synthetic import (
    BANNER,
    build_synthetic_validation_report,
    render_synthetic_validation_markdown,
)

SEED = 5
SPEC = SyntheticSpec(n_bars=12_000, seed=SEED)
CONFIG = MetaLabelStudyConfig(
    models=("logistic_regression", "random_forest"),
    n_folds=3,
    test_bars=1_500,
    validation_bars=1_500,
    min_train_bars=3_000,
    seed=SEED,
)


@pytest.fixture(scope="module")
def signal_study():
    return study_from_market(generate_signal_market(SPEC), CONFIG)


@pytest.fixture(scope="module")
def noise_study():
    return study_from_market(generate_noise_market(SPEC), CONFIG)


def test_the_planted_edge_is_recovered_and_paid_for(signal_study) -> None:
    assert signal_study.arm_total(META_ARM) > signal_study.arm_total(PRIMARY_ARM)
    assert signal_study.folds_profitable >= 2
    lifts = [
        f.test_predictive.pr_auc_lift for f in signal_study.folds if f.test_predictive is not None
    ]
    assert lifts, "a fold that never acts proves nothing about the planted edge"
    assert float(np.median(lifts)) > 1.05, "the probabilities must beat the base rate"


def test_the_filter_trades_less_than_the_primary_it_filters(signal_study) -> None:
    for fold in signal_study.folds:
        assert fold.test_meta.n_trades <= fold.test_primary.n_trades
        assert fold.test_meta.turnover <= fold.test_primary.turnover + 1e-9


def test_nothing_is_manufactured_on_the_pure_noise_control(noise_study) -> None:
    assert noise_study.folds_profitable == 0, (
        "a filter that turns independent increments into profit is leaking"
    )
    assert noise_study.arm_total(META_ARM) <= 0.0
    lifts = [
        f.test_predictive.pr_auc_lift for f in noise_study.folds if f.test_predictive is not None
    ]
    assert all(lift < 1.15 for lift in lifts)


def test_the_control_still_looks_improved_which_is_why_profit_is_the_test(noise_study) -> None:
    # Filtering a rule that only pays costs always "improves" it. If the report
    # keyed off improvement rather than profit, the noise control would pass as
    # a success -- this test pins the distinction that stops that.
    assert noise_study.folds_improved >= noise_study.folds_profitable


def test_the_report_states_the_verdict_and_refuses_a_signal_only_run(
    signal_study,
    noise_study,
) -> None:
    report = build_synthetic_validation_report([signal_study], [noise_study], seeds=[SEED])
    assert report["holdout_accessed"] is False
    assert report["data"] == "synthetic"
    assert report["verdict"]["machinery_validated"] is True

    markdown = render_synthetic_validation_markdown(report)
    assert BANNER in markdown
    assert "not an operational candidate" in markdown or "not a candidate" in markdown
    assert "primary_only" in markdown and "primary_plus_meta" in markdown

    with pytest.raises(ValueError, match="noise control"):
        build_synthetic_validation_report([signal_study], [], seeds=[SEED])
