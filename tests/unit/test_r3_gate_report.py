"""Tests for read-only Gate R3 thesis reporting."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from perp_lab.evaluation.study_robustness import PROMOTION_TESTS, R3_PRIMARY_ENGINE
from perp_lab.reporting.r3_gate import (
    R3_GATE_FAMILIES,
    ArtifactReader,
    R3ReportConsistencyError,
    R3ReportError,
    build_r3_thesis_report,
    render_r3_thesis_markdown,
    write_r3_thesis_report,
)

REAL_ROOT = Path("artifacts/runs/r3_full_budget100_ga21")
OOS_END_OK = "2025-12-09 22:00:00+00:00"
OOS_END_HOLDOUT = "2026-01-15 00:00:00+00:00"
DIFF_A = "4073dba60103de8d7a4ea99a901296fab9f1a4b7d6c4228d65037e6a984f2e9b"
DIFF_B = "0378645e31c35f0b988d1a57eefb6dcbed9517e513d6d50cf739c1e8d89534de"


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


def _tally_block(*, n_pass: int, n_seeds: int = 10, symbol: str = "BTCUSDT") -> dict:
    med = -0.1 if symbol == "BTCUSDT" else -0.2
    bh = 0.5 if symbol == "BTCUSDT" else -0.22
    return {
        "n_seeds": n_seeds,
        "n_positive": n_pass,
        "n_bootstrap_ci_excludes_zero": 0,
        "n_survive_double_costs": 0,
        "n_beat_buy_and_hold": 0,
        "n_survives_drop_top_trades": 0,
        "n_not_confined_to_one_fold": n_seeds,
        "n_min_oos_trades_met": n_seeds,
        "median_total_return": med,
        "median_buy_and_hold_return": bh,
    }


def _per_run_entries(*, family: str, oos_end: str = OOS_END_OK) -> dict:
    per_run: dict = {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        for seed in range(10):
            for method in ("random_search", "genetic_algorithm"):
                key = f"{symbol}|seed={seed}|{method}"
                per_run[key] = {
                    "symbol": symbol,
                    "method": method,
                    "oos_end": oos_end,
                    "strategy": {"sharpe": -0.5, "total_return": -0.1},
                }
    return per_run


def _by_symbol_and_engine(*, n_pass: int = 0) -> dict:
    out: dict = {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        for engine in ("random_search", "genetic_algorithm"):
            out[f"{symbol}|{engine}"] = _tally_block(n_pass=n_pass, symbol=symbol)
    return out


def _rollup_family(*, family: str, n_pass: int = 0) -> dict:
    by_symbol_rs = {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        med = -0.1 if symbol == "BTCUSDT" else -0.2
        by_symbol_rs[symbol] = {
            "n_positive": n_pass,
            "median_total_return": med,
            "median_buy_and_hold_return": 0.5 if symbol == "BTCUSDT" else -0.22,
            "promotion": _promotion_block(n_pass=n_pass)["promotion"],
        }
    return {
        "status": "completed",
        "analysis": {
            "verdict": "REJECTED",
            "by_symbol_rs": by_symbol_rs,
            "paired_ga_minus_rs": {
                "mean_difference": 0.0,
                "ci_low": -0.1,
                "ci_high": 0.1,
                "verdict": "no difference",
            },
        },
    }


def _run_identity(*, family: str, diff_sha256: str, diff_bytes: int) -> dict:
    return {
        "provisional": True,
        "components": {
            "commit": "aac33577c14cba08f349381ce3566eca0c587299",
            "diff_sha256": diff_sha256,
            "untracked_sha256": "97ca909987a70b14c7e7f71095e4b5c068ae8348d70df39f385c3990ae265d50",
        },
        "worktree": {
            "commit": "aac33577c14cba08f349381ce3566eca0c587299",
            "dirty": True,
            "diff_sha256": diff_sha256,
            "diff_bytes": diff_bytes,
            "untracked_sha256": "97ca909987a70b14c7e7f71095e4b5c068ae8348d70df39f385c3990ae265d50",
            "reproducible_from_commit_alone": False,
        },
    }


def _write_full_r3_root(
    tmp_path: Path,
    *,
    families: list[str] | None = None,
    diff_by_family: dict[str, str] | None = None,
    diff_bytes_by_family: dict[str, int] | None = None,
    n_pass: int = 0,
    oos_end: str = OOS_END_OK,
    include_closure: bool = True,
) -> Path:
    root = tmp_path / "r3_full"
    root.mkdir(parents=True)
    families = list(families or R3_GATE_FAMILIES)
    diff_by_family = diff_by_family or dict.fromkeys(families, DIFF_A)
    diff_bytes_by_family = diff_bytes_by_family or {
        family: 45647 if diff_by_family[family] == DIFF_A else 66986 for family in families
    }

    execution = {
        "frozen_order": families,
        "n_seeds": 10,
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "families": {family: {"status": "completed"} for family in families},
        "completed_at": "2026-08-10T17:25:40+00:00",
    }
    (root / "r3_execution.json").write_text(json.dumps(execution), encoding="utf-8")
    (root / "r3_gate_verdict.json").write_text(
        json.dumps(
            {
                "gate_status": "CLOSED_NEGATIVE",
                "n_promoted": 0,
                "n_rejected": len(families) if len(families) == 5 else 5,
                "r4_required": False,
                "promoted_families": [],
                "rejected_families": list(R3_GATE_FAMILIES),
                "closed_at": "2026-08-10T17:41:53+00:00",
            }
        ),
        encoding="utf-8",
    )

    rollup_families = {family: _rollup_family(family=family, n_pass=n_pass) for family in families}
    (root / "r3_family_rollup.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-08-10T17:41:53+00:00",
                "primary_engine": R3_PRIMARY_ENGINE,
                "families": rollup_families,
                "summary": {"n_promoted": 0, "n_rejected": len(families)},
            }
        ),
        encoding="utf-8",
    )

    if include_closure:
        (root / "r3_scientific_closure_report.json").write_text(
            json.dumps(
                {
                    "isolation_audit": {
                        "total_runs_audited": 100,
                        "failures": 0,
                    }
                }
            ),
            encoding="utf-8",
        )

    for family in families:
        study_dir = root / family
        study_dir.mkdir(parents=True)
        promo = {
            "engine": R3_PRIMARY_ENGINE,
            "verdict": "REJECTED",
            "by_symbol": {
                "BTCUSDT": _promotion_block(n_pass=n_pass),
                "ETHUSDT": _promotion_block(n_pass=n_pass),
            },
        }
        study = {
            "r3_promotion": promo,
            "by_symbol_and_engine": _by_symbol_and_engine(n_pass=n_pass),
            "per_run": _per_run_entries(family=family, oos_end=oos_end),
        }
        (study_dir / "study_robustness.json").write_text(json.dumps(study), encoding="utf-8")
        (study_dir / "status.json").write_text(
            json.dumps({"completed": 20, "total": 20}), encoding="utf-8"
        )
        (study_dir / "checkpoint.json").write_text(
            json.dumps(
                {
                    "meta": {
                        "symbols": ["BTCUSDT", "ETHUSDT"],
                        "seeds": list(range(10)),
                    },
                    "units": {f"u{i}": {} for i in range(20)},
                }
            ),
            encoding="utf-8",
        )
        (study_dir / "run_identity.json").write_text(
            json.dumps(
                _run_identity(
                    family=family,
                    diff_sha256=diff_by_family[family],
                    diff_bytes=diff_bytes_by_family[family],
                )
            ),
            encoding="utf-8",
        )
    return root


def test_full_fixture_has_six_criteria_and_separate_veto(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    report = build_r3_thesis_report(root)
    assert len(report["primary_table_rs"]) == 10
    row = report["primary_table_rs"][0]
    assert set(row["criteria"]) == set(PROMOTION_TESTS)
    assert row["min_oos_trades_met"]["role"].startswith("separate veto")
    assert report["primary_engine"] == "random_search"
    assert report["reporter_holdout_accessed"] is False
    assert "pre-specified" not in json.dumps(report).lower()
    assert "pre-registered" not in json.dumps(report).lower()


def test_rejects_incomplete_study(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path, families=["breakout", "funding"])
    with pytest.raises(R3ReportConsistencyError):
        build_r3_thesis_report(root)


def test_rejects_missing_symbol(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    study = json.loads((root / "breakout/study_robustness.json").read_text(encoding="utf-8"))
    del study["r3_promotion"]["by_symbol"]["ETHUSDT"]
    (root / "breakout/study_robustness.json").write_text(json.dumps(study), encoding="utf-8")
    with pytest.raises((R3ReportConsistencyError, R3ReportError)):
        build_r3_thesis_report(root)


def test_rejects_execution_rollup_mismatch(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    rollup = json.loads((root / "r3_family_rollup.json").read_text(encoding="utf-8"))
    rollup["families"]["breakout"]["analysis"]["verdict"] = "PROMOTED"
    (root / "r3_family_rollup.json").write_text(json.dumps(rollup), encoding="utf-8")
    with pytest.raises(R3ReportConsistencyError, match="PROMOTED"):
        build_r3_thesis_report(root)


def test_rejects_pass_boolean_contradiction(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    study = json.loads((root / "breakout/study_robustness.json").read_text(encoding="utf-8"))
    study["r3_promotion"]["by_symbol"]["BTCUSDT"]["promotion"]["positive_total_return"]["pass"] = (
        True
    )
    (root / "breakout/study_robustness.json").write_text(json.dumps(study), encoding="utf-8")
    with pytest.raises(R3ReportConsistencyError, match="pass="):
        build_r3_thesis_report(root)


def test_rejects_oos_end_in_holdout(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path, oos_end=OOS_END_HOLDOUT)
    with pytest.raises(R3ReportConsistencyError, match="oos_end"):
        build_r3_thesis_report(root)


def test_units_completed_does_not_imply_isolation_audit(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path, include_closure=False)
    report = build_r3_thesis_report(root)
    assert report["closure_summary"]["units_completed"]["verification_level"] == "reporter_verified"
    assert "isolation_audit_at_closure" not in report["documentary_claims"]


def test_documentary_isolation_when_closure_present(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path, include_closure=True)
    report = build_r3_thesis_report(root)
    audit = report["documentary_claims"]["isolation_audit_at_closure"]
    assert audit["verification_level"] == "documentary"
    assert audit["source_file"] == "r3_scientific_closure_report.json"


def test_preserves_two_provenance_states(tmp_path: Path) -> None:
    diff_map = dict.fromkeys(R3_GATE_FAMILIES, DIFF_A)
    diff_map["BTC_ETH_confirmation"] = DIFF_B
    root = _write_full_r3_root(tmp_path, diff_by_family=diff_map)
    report = build_r3_thesis_report(root)
    states = report["closure_summary"]["provenance_limitation"]["provenance_states"]
    assert len(states) == 2
    state_a = next(s for s in states if "BTC_ETH_confirmation" not in s["families"])
    state_b = next(s for s in states if "BTC_ETH_confirmation" in s["families"])
    assert len(state_a["families"]) == 4
    assert state_a["diff_sha256"] == DIFF_A
    assert state_b["diff_sha256"] == DIFF_B


def test_output_has_no_absolute_paths(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    report = build_r3_thesis_report(root)
    md = render_r3_thesis_markdown(report)
    blob = json.dumps(report) + md
    assert re.search(r"[A-Za-z]:\\\\", blob) is None
    assert "Users" not in blob


def test_rejects_output_inside_root(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    with pytest.raises(R3ReportError, match="output_dir"):
        write_r3_thesis_report(root, root / "nested")


def test_traceability_in_markdown_and_json(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    report = build_r3_thesis_report(root)
    md = render_r3_thesis_markdown(report)
    assert "## Traceability" in md
    assert len(report["traceability"]) >= 50
    assert any(entry["claim"].endswith("median OOS Sharpe") for entry in report["traceability"])


def test_reader_only_opens_json_under_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _write_full_r3_root(tmp_path)
    reader = ArtifactReader(root)
    original_read_bytes = Path.read_bytes

    def tracked_read_bytes(self: Path) -> bytes:
        if (
            self.suffix == ".json"
            and root.resolve() not in self.resolve().parents
            and self.resolve() != root.resolve()
            and not str(self.resolve()).startswith(str(root.resolve()))
        ):
            raise AssertionError(f"unexpected read outside root: {self}")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", tracked_read_bytes)
    build_r3_thesis_report(root, reader=reader)
    assert reader.reads
    assert all(item.relative_path.endswith(".json") for item in reader.reads)


def test_determinism_across_output_directories(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"
    write_r3_thesis_report(root, out_a)
    write_r3_thesis_report(root, out_b)
    assert (out_a / "thesis_report.json").read_bytes() == (
        out_b / "thesis_report.json"
    ).read_bytes()
    assert (out_a / "thesis_report.md").read_bytes() == (out_b / "thesis_report.md").read_bytes()


def test_rejects_forbidden_json_path(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    reader = ArtifactReader(root)
    with pytest.raises(R3ReportError, match="forbidden"):
        reader.read_json("data/raw/forbidden.json")


@pytest.mark.skipif(not REAL_ROOT.exists(), reason="R3 artifacts not present locally")
def test_real_r3_artifacts_report_consistency() -> None:
    report = build_r3_thesis_report(REAL_ROOT)
    assert report["closure_summary"]["gate_status"]["value"] == "CLOSED_NEGATIVE"
    assert report["closure_summary"]["n_promoted"]["value"] == 0
    assert len(report["primary_table_rs"]) == 10
    vb_btc = next(
        r
        for r in report["primary_table_rs"]
        if r["family"] == "volatility_breakout" and r["symbol"] == "BTCUSDT"
    )
    assert vb_btc.get("diagnostic_note") == "partial non-robust signal (not promotion-eligible)"
    assert all(r["verdict"] == "REJECTED" for r in report["primary_table_rs"])
    states = report["closure_summary"]["provenance_limitation"]["provenance_states"]
    assert len(states) == 2
