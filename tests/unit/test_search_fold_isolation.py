"""Fold-isolation tests for the per-outer-fold search protocol (ADR 0012).

These are the tests that would have caught the original contamination. Each one
fails if a specific channel between a fold and data it may not see is reopened:

* another fold's validation reaching a candidate's fitness;
* another fold's test being reachable at all from a fold's evaluator;
* the test slice influencing fitness;
* a fold's winner changing after its test slice was scored;
* the two engines searching at different effective budgets inside one fold.

They are deliberately written against observable behaviour rather than
implementation details, so a future refactor that reintroduces the leak still
fails them.
"""

from __future__ import annotations

import hashlib
import json

import polars as pl
import pytest
from search_helpers import build_env

from perp_lab.search.candidate import Candidate
from perp_lab.search.evaluator import (
    CandidateEvaluator,
    FoldData,
    FoldIsolationError,
    single_fold_bundle,
)
from perp_lab.search.outcome import Counters, SearchOutcome
from perp_lab.search.runner import (
    SEARCH_PROTOCOL,
    BudgetParityError,
    _assert_budget_parity,
    _freeze_winner,
    _select_fold_winner,
)


def _evaluator_for(env, bundle) -> CandidateEvaluator:
    return CandidateEvaluator(
        bundle,
        env.space,
        timeframe="1h",
        fee_bps_per_side=env.exp.costs.fee_bps_per_side,
        slippage_bps_per_side=env.exp.costs.slippage.baseline_bps,
        days_per_year=env.exp.annualization_days,
        require_funding=False,
        objective_cfg=env.objective_cfg,
    )


def _a_candidate(env, seed: int = 3) -> Candidate:
    import numpy as np

    rng = np.random.default_rng(seed)
    for _ in range(200):
        values = env.space.sample(rng)
        ok, _reason = env.space.is_valid(values)
        if ok:
            return Candidate.create(env.space, values, seed=seed, step=0)
    raise AssertionError("the search space produced no valid candidate")


# --------------------------------------------------------------------------- #
# A fold's search environment physically cannot reach another fold
# --------------------------------------------------------------------------- #


def test_single_fold_bundle_holds_exactly_one_fold() -> None:
    env = build_env(seed=5)
    assert len(env.bundle.folds) >= 2
    isolated = single_fold_bundle(env.bundle, 1)
    assert [fd.index for fd in isolated.folds] == [1]


def test_an_isolated_evaluator_refuses_another_folds_test_slice() -> None:
    """Reaching a neighbour's test data must raise, not silently resolve."""
    env = build_env(seed=5)
    ev = _evaluator_for(env, single_fold_bundle(env.bundle, 1))
    candidate = _a_candidate(env)
    ev.evaluate(candidate)

    assert ev.fold_indices == [1]
    ev.evaluate_on_test(candidate, 1)  # its own fold is allowed
    for other in (0, 2):
        with pytest.raises(FoldIsolationError):
            ev.evaluate_on_test(candidate, other)


def test_an_isolated_evaluator_carries_no_bar_beyond_its_own_fold() -> None:
    """Isolation must be structural: later data simply is not present."""
    env = build_env(seed=5)
    isolated = single_fold_bundle(env.bundle, 0)
    fold = isolated.folds[0]

    reachable: set = set()
    for frame in (fold.train, fold.val, fold.test):
        reachable.update(frame["open_time"].to_list())

    boundary = fold.fold.test_end
    assert not [t for t in reachable if t >= boundary], (
        "the fold-0 search environment can read bars from beyond its own test window"
    )
    # And the fixture really does have later data that was excluded.
    later = env.bundle.folds[-1]
    assert [t for t in later.test["open_time"].to_list() if t >= boundary]


# --------------------------------------------------------------------------- #
# Fitness must not depend on folds other than its own
# --------------------------------------------------------------------------- #


def test_fitness_is_unchanged_by_the_existence_of_later_folds() -> None:
    """The regression test for the original bug.

    Under the contaminated protocol a candidate's fitness was an aggregate over
    every fold, so adding a later fold changed the score used to pick fold 0's
    winner. Here fold 0's fitness must be identical whether the run has one fold
    or three.
    """
    one_fold = build_env(seed=5, max_folds=1)
    three_folds = build_env(seed=5, max_folds=3)
    assert len(three_folds.bundle.folds) > len(one_fold.bundle.folds)

    short = _evaluator_for(one_fold, single_fold_bundle(one_fold.bundle, 0))
    long = _evaluator_for(three_folds, single_fold_bundle(three_folds.bundle, 0))

    compared = 0
    for seed in range(60):
        a, b = _a_candidate(one_fold, seed=seed), _a_candidate(three_folds, seed=seed)
        assert a.candidate_id == b.candidate_id
        short.evaluate(a)
        long.evaluate(b)
        assert a.fitness == b.fitness
        assert a.objective_components == b.objective_components
        assert len(b.fold_metrics) == 1, "a fold's fitness saw more than one fold"
        if a.status == a.status.EVALUATED:
            compared += 1
    # A run where every candidate was rejected would satisfy the equalities above
    # without ever exercising the objective.
    assert compared > 0, "no candidate was admissible, so no fitness was actually compared"


def test_the_same_candidate_scores_differently_in_different_folds() -> None:
    """Each fold is its own environment, so fitness must be fold-specific.

    If one cache or one aggregate were shared, the two scores would coincide and
    a single ranking would be driving every fold's selection.
    """
    env = build_env(seed=5)
    first = _evaluator_for(env, single_fold_bundle(env.bundle, 0))
    last = _evaluator_for(env, single_fold_bundle(env.bundle, len(env.bundle.folds) - 1))

    for seed in range(60):
        a, b = _a_candidate(env, seed=seed), _a_candidate(env, seed=seed)
        first.evaluate(a)
        last.evaluate(b)
        if a.status == a.status.EVALUATED and b.status == b.status.EVALUATED:
            assert a.candidate_id == b.candidate_id
            assert a.fitness != b.fitness
            return
    pytest.fail("no candidate was admissible in both folds; the fixture proves nothing")


# --------------------------------------------------------------------------- #
# The test slice never enters fitness
# --------------------------------------------------------------------------- #


def test_corrupting_the_test_slice_does_not_move_fitness() -> None:
    """Fitness must be blind to out-of-sample data, by construction."""
    env = build_env(seed=5)
    clean = single_fold_bundle(env.bundle, 0)

    fold = clean.folds[0]
    scrambled = fold.test.with_columns(
        [(pl.col(c) * 1000.0).alias(c) for c in ("open", "high", "low", "close")]
    )
    corrupted = single_fold_bundle(env.bundle, 0)
    corrupted.folds[0] = FoldData(
        index=fold.index,
        train=fold.train,
        val=fold.val,
        test=scrambled,
        regime_params=fold.regime_params,
        fold=fold.fold,
    )

    clean_ev = _evaluator_for(env, clean)
    corrupt_ev = _evaluator_for(env, corrupted)

    compared = 0
    for seed in range(60):
        a, b = _a_candidate(env, seed=seed), _a_candidate(env, seed=seed)
        clean_ev.evaluate(a)
        corrupt_ev.evaluate(b)
        assert a.fitness == b.fitness
        assert a.objective_components == b.objective_components
        if a.status == a.status.EVALUATED:
            compared += 1
    assert compared > 0, "no candidate was admissible, so no fitness was actually compared"


def test_winner_selection_reads_validation_only() -> None:
    """Ranking uses the fold's validation record, never a test metric."""
    env = build_env(seed=5)
    candidates = []
    for i, val_sharpe in enumerate((0.1, 2.0, -3.0)):
        c = _a_candidate(env, seed=10 + i)
        c.status = c.status.EVALUATED
        c.fitness = float(i)
        c.fold_metrics = [{"sharpe": val_sharpe, "n_trades": 25.0}]
        candidates.append(c)
    outcome = SearchOutcome(
        algorithm="random_search",
        version="1.0.0",
        seed=1,
        budget=3,
        candidates=candidates,
        counters=Counters(evaluated=3),
        convergence=[],
        best=None,
    )
    winner, val_sharpe = _select_fold_winner(outcome, min_trades_per_fold=1)
    assert winner is candidates[1]
    assert val_sharpe == 2.0


def test_a_candidate_below_the_fold_trade_floor_cannot_win() -> None:
    env = build_env(seed=5)
    thin = _a_candidate(env, seed=21)
    thin.status = thin.status.EVALUATED
    thin.fold_metrics = [{"sharpe": 99.0, "n_trades": 1.0}]
    outcome = SearchOutcome(
        algorithm="random_search",
        version="1.0.0",
        seed=1,
        budget=1,
        candidates=[thin],
        counters=Counters(evaluated=1),
        convergence=[],
        best=None,
    )
    winner, _ = _select_fold_winner(outcome, min_trades_per_fold=10)
    assert winner is None


# --------------------------------------------------------------------------- #
# The winner is frozen before its test slice is scored
# --------------------------------------------------------------------------- #


def test_freezing_records_a_fingerprint_of_the_selection() -> None:
    env = build_env(seed=5)
    candidate = _a_candidate(env)
    frozen = _freeze_winner(candidate, fold_index=2, val_sharpe=0.4)

    assert frozen["frozen_before_test"] is True
    assert frozen["selection_basis"] == "validation_only"
    assert "test_metrics" not in frozen, "the freeze record already contains test data"

    expected = hashlib.sha256(
        json.dumps(
            {
                "fold": 2,
                "candidate_id": candidate.candidate_id,
                "params": frozen["params"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]
    assert frozen["selection_fingerprint"] == expected


def test_a_swapped_winner_breaks_the_fingerprint() -> None:
    """The fingerprint is what makes 'frozen before test' checkable after the fact."""
    env = build_env(seed=5)
    first = _freeze_winner(_a_candidate(env, seed=1), fold_index=0, val_sharpe=0.4)
    second = _freeze_winner(_a_candidate(env, seed=99), fold_index=0, val_sharpe=0.4)
    if first["winner"] == second["winner"]:
        pytest.skip("the sampler drew the same candidate twice")
    assert first["selection_fingerprint"] != second["selection_fingerprint"]


def test_a_fold_with_no_admissible_candidate_is_recorded_not_hidden() -> None:
    frozen = _freeze_winner(None, fold_index=4, val_sharpe=float("-inf"))
    assert frozen["winner"] is None
    assert frozen["fold"] == 4
    assert frozen["reason"]


# --------------------------------------------------------------------------- #
# Budget parity holds inside every fold, not only on average
# --------------------------------------------------------------------------- #


def _outcome(name: str, evaluated: int) -> SearchOutcome:
    return SearchOutcome(
        algorithm=name,
        version="1.0.0",
        seed=1,
        budget=10,
        candidates=[],
        counters=Counters(evaluated=evaluated),
        convergence=[],
        best=None,
        extra={"termination_reason": "budget_reached"},
    )


def test_equal_budget_inside_a_fold_passes() -> None:
    _assert_budget_parity(
        {"random_search": _outcome("random_search", 10), "genetic_algorithm": _outcome("ga", 10)},
        target=10,
        fold_index=3,
    )


def test_unequal_budget_inside_a_fold_fails_and_names_the_fold() -> None:
    """A run-level total can match while one fold was searched unevenly."""
    with pytest.raises(BudgetParityError, match="fold 3"):
        _assert_budget_parity(
            {
                "random_search": _outcome("random_search", 10),
                "genetic_algorithm": _outcome("ga", 7),
            },
            target=10,
            fold_index=3,
        )


def test_an_engine_short_of_the_target_fails_even_if_both_are_short() -> None:
    """Two engines agreeing on the wrong number is not parity with the contract."""
    with pytest.raises(BudgetParityError):
        _assert_budget_parity(
            {
                "random_search": _outcome("random_search", 8),
                "genetic_algorithm": _outcome("ga", 8),
            },
            target=10,
            fold_index=0,
        )


def test_the_protocol_identifier_is_stable() -> None:
    """Artifacts are matched on this string; changing it silently would re-pool runs."""
    assert SEARCH_PROTOCOL == "independent_search_per_outer_fold"
