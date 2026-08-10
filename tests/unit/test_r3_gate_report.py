"""Tests for read-only Gate R3 thesis reporting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from perp_lab.evaluation.study_robustness import PROMOTION_TESTS, R3_PRIMARY_ENGINE
from perp_lab.reporting.r3_gate import (
    R3ReportConsistencyError,
    R3ReportError,
    build_r3_thesis_report,
    write_r3_thesis_report,
)

REAL_ROOT = Path("artifacts/runs/r3_full_budget100_ga21")


def _promotion_block(*, n_pass: int, n_seeds: int = 10, required: int = 6) -> dict:
    promotion = {
        name: {
            "n_pass": n_seeds if name == "not_confined_to_one_fold" else n_pass,
            "required": required,
            "pass": (n_seeds if name == "not_confined_to_one_fold" else n_pass) >= required,
        }
        for name in PROMOTION_TESTS
    }
    rejections = {
        "zero_seeds_positive": {"triggered": n_pass == 0, "n_pass": n_pass},
        "no_bootstrap_ci_excludes_zero": {"triggered": True, "n_pass": 0},
        "zero_seeds_survive_double_costs": {"triggered": True, "n_pass": 0},
        "depends_on_few_trades": {
            "triggered": False,
            "n_seeds_below_min_trades": 0,
            "min_trades_required": 5,
        },
        "confined_to_one_fold": {
            "triggered": False,
            "n_confined": 0,
            "required_not_confined": required,
        },
    }
    return {
        "n_seeds": n_seeds,
        "majority_required": required,
        "promotion": promotion,
        "rejections": rejections,
    }


def _tally_block(*, n_pass: int, n_seeds: int = 10) -> dict:
    return {
        "n_seeds": n_seeds,
        "n_positive": n_pass,
        "n_bootstrap_ci_excludes_zero": 0,
        "n_survive_double_costs": 0,
        "n_beat_buy_and_hold": 0,
        "n_survives_drop_top_trades": 0,
        "n_not_confined_to_one_fold": n_seeds,
        "n_min_oos_trades_met": n_seeds,
        "median_total_return": -0.1,
        "median_buy_and_hold_return": 0.5,
    }


def _write_minimal_r3_root(tmp_path: Path, *, n_promoted: int = 0) -> Path:
    root = tmp_path / "r3_mini"
    family = "breakout"
    study_dir = root / family
    study_dir.mkdir(parents=True)

    for name, payload in {
        "r3_execution.json": {
            "frozen_order": [family],
            "n_seeds": 10,
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "families": {family: {"status": "completed", "study_dir": str(study_dir)}},
            "completed_at": "2026-08-10T17:25:40+00:00",
        },
        "r3_gate_verdict.json": {
            "gate_status": "CLOSED_NEGATIVE",
            "n_promoted": n_promoted,
            "n_rejected": 1,
            "r4_required": False,
            "closed_at": "2026-08-10T17:41:53+00:00",
        },
    }.items():
        (root / name).write_text(json.dumps(payload), encoding="utf-8")

    promo = {
        "engine": R3_PRIMARY_ENGINE,
        "verdict": "REJECTED",
        "by_symbol": {
            "BTCUSDT": _promotion_block(n_pass=0),
            "ETHUSDT": _promotion_block(n_pass=0),
        },
    }
    study = {
        "r3_promotion": promo,
        "by_symbol_and_engine": {
            "BTCUSDT|random_search": _tally_block(n_pass=0),
            "ETHUSDT|random_search": _tally_block(n_pass=0),
        },
        "per_run": {
            "BTCUSDT|seed=0|random_search": {
                "symbol": "BTCUSDT",
                "method": "random_search",
                "strategy": {"sharpe": -0.5, "total_return": -0.1},
            }
        },
    }
    (study_dir / "study_robustness.json").write_text(json.dumps(study), encoding="utf-8")
    (study_dir / "status.json").write_text(
        json.dumps({"completed": 20, "total": 20}), encoding="utf-8"
    )
    (study_dir / "checkpoint.json").write_text(
        json.dumps(
            {
                "meta": {"symbols": ["BTCUSDT", "ETHUSDT"], "seeds": list(range(10))},
                "units": {f"u{i}": {} for i in range(20)},
            }
        ),
        encoding="utf-8",
    )
    (study_dir / "run_identity.json").write_text(
        json.dumps(
            {
                "worktree": {
                    "commit": "aac33577c14cba08f349381ce3566eca0c587299",
                    "dirty": True,
                    "reproducible_from_commit_alone": False,
                    "diff_sha256": "4073dba60103de8d7a4ea99a901296fab9f1a4b7d6c4228d65037e6a984f2e9b",
                }
            }
        ),
        encoding="utf-8",
    )

    rollup = {
        "generated_at": "2026-08-10T17:41:53+00:00",
        "primary_engine": R3_PRIMARY_ENGINE,
        "families": {
            family: {
                "status": "completed",
                "analysis": {
                    "verdict": "REJECTED",
                    "by_symbol_rs": {
                        "BTCUSDT": {"n_positive": 0, "median_total_return": -0.1},
                        "ETHUSDT": {"n_positive": 0, "median_total_return": -0.2},
                    },
                    "paired_ga_minus_rs": {
                        "mean_difference": 0.0,
                        "ci_low": -0.1,
                        "ci_high": 0.1,
                        "verdict": "no difference",
                    },
                },
            }
        },
        "summary": {"n_promoted": n_promoted, "n_rejected": 1},
    }
    (root / "r3_family_rollup.json").write_text(json.dumps(rollup), encoding="utf-8")
    return root


def test_build_report_has_six_criteria_and_separate_veto(tmp_path: Path) -> None:
    root = _write_minimal_r3_root(tmp_path)
    report = build_r3_thesis_report(root)
    row = report["primary_table_rs"][0]
    assert set(row["criteria"]) == set(PROMOTION_TESTS)
    assert row["min_oos_trades_met"]["role"].startswith("separate veto")
    assert report["primary_engine"] == "random_search"
    assert report["holdout_accessed"] is False


def test_rejects_promoted_family_in_rollup(tmp_path: Path) -> None:
    root = _write_minimal_r3_root(tmp_path)
    rollup = json.loads((root / "r3_family_rollup.json").read_text(encoding="utf-8"))
    rollup["families"]["breakout"]["analysis"]["verdict"] = "PROMOTED"
    (root / "r3_family_rollup.json").write_text(json.dumps(rollup), encoding="utf-8")
    with pytest.raises(R3ReportConsistencyError, match="PROMOTED"):
        build_r3_thesis_report(root)


def test_rejects_holdout_path(tmp_path: Path) -> None:
    holdout_root = tmp_path / "holdout_run"
    holdout_root.mkdir()
    with pytest.raises(R3ReportError, match="holdout"):
        build_r3_thesis_report(holdout_root)


def test_write_report_is_deterministic(tmp_path: Path) -> None:
    root = _write_minimal_r3_root(tmp_path)
    out = tmp_path / "out"
    first = write_r3_thesis_report(root, out)
    json_a = first["json"].read_bytes()
    md_a = first["markdown"].read_bytes()
    second = write_r3_thesis_report(root, out)
    assert second["json"].read_bytes() == json_a
    assert second["markdown"].read_bytes() == md_a


def test_report_matches_gate_verdict(tmp_path: Path) -> None:
    root = _write_minimal_r3_root(tmp_path)
    report = build_r3_thesis_report(root)
    assert report["closure_summary"]["gate_status"] == "CLOSED_NEGATIVE"
    assert report["closure_summary"]["n_promoted"] == 0
    assert report["closure_summary"]["r4_required"] is False


@pytest.mark.skipif(not REAL_ROOT.exists(), reason="R3 artifacts not present locally")
def test_real_r3_artifacts_report_consistency() -> None:
    report = build_r3_thesis_report(REAL_ROOT)
    assert report["closure_summary"]["gate_status"] == "CLOSED_NEGATIVE"
    assert report["closure_summary"]["n_promoted"] == 0
    assert len(report["primary_table_rs"]) == 10
    vb_btc = next(
        r
        for r in report["primary_table_rs"]
        if r["family"] == "volatility_breakout" and r["symbol"] == "BTCUSDT"
    )
    assert vb_btc.get("diagnostic_note") == "partial non-robust signal (not promotion-eligible)"
    assert all(r["verdict"] == "REJECTED" for r in report["primary_table_rs"])
    assert all(row["ga_does_not_decide_promotion"] for row in report["rs_ga_comparison"])
