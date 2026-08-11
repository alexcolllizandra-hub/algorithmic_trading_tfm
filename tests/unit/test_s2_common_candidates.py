"""Common-candidate PBO for Gate S2: determinism, causal labelling and scoring.

The candidate set exists only to make PBO computable; it selects nothing. What
must hold is that it is reproducible from its frozen seed, that the regime labels
the candidates are gated on were never fitted on the bars they score, and that
the scored window is exactly the causal one.
"""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from perp_lab.config.settings import load_experiment_config
from perp_lab.experiments.pipeline import synthetic_klines
from perp_lab.reporting.s2_common_candidates import (
    CommonCandidateError,
    _block_sharpes,
    build_pbo_frame,
    common_candidate_pbo,
    sample_common_candidates,
)
from perp_lab.search.registry import S2_FAMILIES, build_search_space
from perp_lab.strategies.filters import DEFAULT_REGIME_COL
from perp_lab.validation.walk_forward import generate_walk_forward

SYMBOL = "BTCUSDT"
TIMEFRAME = "1h"


@pytest.fixture(scope="module")
def exp():
    return load_experiment_config()


@pytest.fixture(scope="module")
def dev_bars(exp) -> pl.DataFrame:
    """Synthetic klines spanning exactly the development period. Not real data."""
    span = exp.periods.development_end_exclusive - exp.periods.development_start
    n = int(span.total_seconds() // 3600)
    return synthetic_klines(n, seed=7, start=exp.periods.development_start, timeframe=TIMEFRAME)


# --------------------------------------------------------------------------- #
# The candidate set
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("family", S2_FAMILIES)
def test_the_candidate_set_is_reproducible_from_its_frozen_seed(exp, family: str) -> None:
    space = build_search_space(exp, family, SYMBOL)
    first = sample_common_candidates(space, n_candidates=20, seed=2026)
    second = sample_common_candidates(space, n_candidates=20, seed=2026)
    assert first == second


@pytest.mark.parametrize("family", S2_FAMILIES)
def test_every_drawn_candidate_is_unique_and_valid(exp, family: str) -> None:
    space = build_search_space(exp, family, SYMBOL)
    drawn = sample_common_candidates(space, n_candidates=20, seed=2026)
    assert len(drawn) == 20
    assert all(space.is_valid(values)[0] for values in drawn)
    assert len({space.candidate_hash(values) for values in drawn}) == 20


def test_a_set_too_small_to_rank_is_refused(exp) -> None:
    space = build_search_space(exp, S2_FAMILIES[0], SYMBOL)
    with pytest.raises(CommonCandidateError, match="at least two"):
        sample_common_candidates(space, n_candidates=1)


def test_asking_for_more_candidates_than_the_space_holds_fails_loudly(exp) -> None:
    space = build_search_space(exp, S2_FAMILIES[0], SYMBOL)
    cardinality = space.finite_cardinality()
    assert cardinality is not None, "the S2 spaces are finite by construction"
    with pytest.raises(CommonCandidateError, match="unique valid candidates"):
        sample_common_candidates(space, n_candidates=cardinality + 1)


# --------------------------------------------------------------------------- #
# Block Sharpe ratios
# --------------------------------------------------------------------------- #


def test_block_sharpes_returns_one_number_per_block() -> None:
    returns = np.linspace(-0.01, 0.01, 400)
    blocks = _block_sharpes(returns, n_blocks=8, timeframe=TIMEFRAME, days_per_year=365)
    assert blocks is not None
    assert blocks.shape == (8,)
    assert np.isfinite(blocks).all()


def test_a_block_that_never_moved_earned_nothing_rather_than_undefined() -> None:
    blocks = _block_sharpes(np.zeros(64), n_blocks=4, timeframe=TIMEFRAME, days_per_year=365)
    assert blocks is not None
    assert np.allclose(blocks, 0.0)


def test_too_few_observations_to_fill_the_blocks_returns_nothing() -> None:
    assert _block_sharpes(np.zeros(4), n_blocks=8, timeframe=TIMEFRAME, days_per_year=365) is None


# --------------------------------------------------------------------------- #
# Causal regime labelling and the scored window
# --------------------------------------------------------------------------- #


def test_the_scored_window_starts_where_the_regime_fitting_window_ends(exp, dev_bars) -> None:
    prepared = build_pbo_frame(
        dev_bars,
        exp=exp,
        family=S2_FAMILIES[0],
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        funding=None,
        holdout_start=exp.periods.holdout_start,
    )
    first_fold = generate_walk_forward(exp, strict=True)[0]
    assert prepared.regime_fit_start == first_fold.train_start
    assert prepared.regime_fit_end == first_fold.train_end
    assert prepared.scored_from == first_fold.train_end
    assert DEFAULT_REGIME_COL in prepared.frame.columns
    scored = prepared.scored_mask()
    assert scored.sum() > 0
    assert not scored[0], "bars inside the fitting window must not be scored"


def test_the_regime_labels_do_not_depend_on_later_data(exp, dev_bars) -> None:
    """Truncating the future must not change any label the PBO actually scores."""
    kwargs = {
        "exp": exp,
        "family": S2_FAMILIES[0],
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "funding": None,
        "holdout_start": exp.periods.holdout_start,
    }
    full = build_pbo_frame(dev_bars, **kwargs)
    cut = dev_bars.height * 4 // 5
    truncated = build_pbo_frame(dev_bars.head(cut), **kwargs)

    common = truncated.frame.select("open_time", DEFAULT_REGIME_COL).join(
        full.frame.select("open_time", DEFAULT_REGIME_COL),
        on="open_time",
        how="inner",
        suffix="_full",
    )
    assert common.height == cut
    assert common[DEFAULT_REGIME_COL].equals(
        common[f"{DEFAULT_REGIME_COL}_full"].rename(DEFAULT_REGIME_COL)
    )


def test_a_span_that_ends_inside_the_fitting_window_leaves_nothing_to_score(exp) -> None:
    short = synthetic_klines(
        24 * 400, seed=3, start=exp.periods.development_start, timeframe=TIMEFRAME
    )
    with pytest.raises(CommonCandidateError, match="after the regime fitting window"):
        build_pbo_frame(
            short,
            exp=exp,
            family=S2_FAMILIES[0],
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            funding=None,
            holdout_start=exp.periods.holdout_start,
        )


# --------------------------------------------------------------------------- #
# End-to-end PBO
# --------------------------------------------------------------------------- #


def test_pbo_is_a_probability_measured_on_the_causal_window(exp, dev_bars) -> None:
    result = common_candidate_pbo(
        exp,
        family=S2_FAMILIES[0],
        symbol=SYMBOL,
        bars=dev_bars,
        funding=None,
        timeframe=TIMEFRAME,
        holdout_start=exp.periods.holdout_start,
        n_candidates=6,
        n_blocks=4,
    )
    assert 0.0 <= result.pbo <= 1.0
    assert result.n_candidates_evaluated <= 6
    assert result.n_blocks == 4
    assert 0 < result.scored_bars < result.development_bars
    payload = result.to_dict()
    assert payload["regime"]["regime_model"] == "threshold"
    assert payload["regime"]["scored_from"] == result.regime["scored_from"]
