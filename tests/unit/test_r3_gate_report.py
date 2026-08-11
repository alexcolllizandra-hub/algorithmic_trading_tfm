"""Tests for read-only Gate R3 thesis reporting."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from perp_lab.evaluation.study_robustness import PROMOTION_TESTS, R3_PRIMARY_ENGINE
from perp_lab.reporting.r3_gate import (
    R3_GATE_FAMILIES,
    ArtifactReader,
    R3ReportConsistencyError,
    R3ReportError,
    build_r3_thesis_report,
    build_read_allowlist,
    render_r3_thesis_markdown,
    write_r3_thesis_report,
)

REAL_ROOT = Path("artifacts/runs/r3_full_budget100_ga21")
OOS_END_OK = "2025-12-09 22:00:00+00:00"
OOS_END_HOLDOUT = "2026-01-15 00:00:00+00:00"
DIFF_A = "4073dba60103de8d7a4ea99a901296fab9f1a4b7d6c4228d65037e6a984f2e9b"
DIFF_B = "0378645e31c35f0b988d1a57eefb6dcbed9517e513d6d50cf739c1e8d89534de"
REAL_SEEDS = [
    891022,
    341110,
    693857,
    683778,
    765570,
    692467,
    605142,
    671194,
    707014,
    278037,
]
DEFAULT_DIFF_BY_FAMILY = {
    family: DIFF_A for family in R3_GATE_FAMILIES if family != "BTC_ETH_confirmation"
} | {"BTC_ETH_confirmation": DIFF_B}


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


def _per_run_entries(
    *, family: str, oos_end: str = OOS_END_OK, seeds: list[int] | None = None
) -> dict:
    seed_list = seeds or REAL_SEEDS
    per_run: dict = {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        for seed in seed_list:
            for method in ("random_search", "genetic_algorithm"):
                key = f"{symbol}|seed={seed}|{method}"
                per_run[key] = {
                    "symbol": symbol,
                    "seed": seed,
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


def _checkpoint_units(*, seeds: list[int] | None = None) -> dict:
    seed_list = seeds or REAL_SEEDS
    units: dict = {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        for seed in seed_list:
            key = f"{symbol}|seed={seed}"
            units[key] = {"symbol": symbol, "seed": seed}
    return units


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
    diff_by_family = diff_by_family or dict(DEFAULT_DIFF_BY_FAMILY)
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
                "summary": {"n_promoted": 0, "n_rejected": 5},
            }
        ),
        encoding="utf-8",
    )

    if include_closure:
        (root / "r3_scientific_closure_report.json").write_text(
            json.dumps(
                {
                    "isolation_audit": {
                        "per_family_runs": 20,
                        "families": 5,
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
            "triggered_rejections": ["BTCUSDT: zero_seeds_positive"],
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
                        "seeds": REAL_SEEDS,
                    },
                    "units": _checkpoint_units(seeds=REAL_SEEDS),
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
    root = _write_full_r3_root(tmp_path, include_closure=True)
    report = build_r3_thesis_report(root)
    units = report["closure_summary"]["units_completed"]
    audit = report["documentary_claims"]["isolation_audit_at_closure"]
    assert units["verification_level"] == "reporter_verified"
    assert audit["verification_level"] == "documentary"
    assert "does not substitute" in units.get("note", "").lower() or units["note"]


def test_r4_evidence_is_split_between_reporter_and_documentary(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    report = build_r3_thesis_report(root)
    assert report["documentary_claims"]["r4_required_at_closure"]["verification_level"] == (
        "reporter_verified"
    )
    assert report["documentary_claims"]["r4_application_status"]["verification_level"] == (
        "documentary"
    )
    assert report["documentary_claims"]["r4_promoted_only_scope"]["verification_level"] == (
        "documentary"
    )
    assert "r4_required" not in report["closure_summary"]
    assert "SKIPPED" in report["documentary_claims"]["r4_application_status"]["value"]


def test_rejects_missing_closure_report(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path, include_closure=False)
    with pytest.raises(R3ReportError, match="missing"):
        build_r3_thesis_report(root)


def test_rejects_isolation_audit_failures(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    (root / "r3_scientific_closure_report.json").write_text(
        json.dumps(
            {
                "isolation_audit": {
                    "total_runs_audited": 100,
                    "failures": 1,
                    "families": 5,
                    "per_family_runs": 20,
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(R3ReportConsistencyError, match="failures"):
        build_r3_thesis_report(root)


def test_rejects_incomplete_checkpoint_units(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    checkpoint = json.loads((root / "breakout/checkpoint.json").read_text(encoding="utf-8"))
    units = dict(list(checkpoint["units"].items())[:19])
    checkpoint["units"] = units
    (root / "breakout/checkpoint.json").write_text(json.dumps(checkpoint), encoding="utf-8")
    with pytest.raises(R3ReportConsistencyError, match=r"checkpoint\.units count"):
        build_r3_thesis_report(root)


def test_allowlist_rejects_unlisted_json(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    (root / "unexpected.json").write_text("{}", encoding="utf-8")
    reader = ArtifactReader(root, allowlist=build_read_allowlist(list(R3_GATE_FAMILIES)))
    with pytest.raises(R3ReportError, match="allowlist"):
        reader.read_json("unexpected.json")


def test_provenance_note_is_derived_not_hardcoded(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    report = build_r3_thesis_report(root)
    prov = report["closure_summary"]["provenance_limitation"]
    assert prov["distinct_tracked_states"] == 2
    assert prov["distinct_commits"][0] in prov["note"]
    assert prov["patch_bytes_available"] is False
    assert prov["exact_reconstruction_from_commit_alone"] is False
    md = render_r3_thesis_markdown(report)
    assert "multiple tracked states" not in md.lower()


def test_determinism_across_two_absolute_roots(tmp_path: Path) -> None:
    import shutil

    source = _write_full_r3_root(tmp_path)
    study_name = "r3_full_budget100_ga21"
    root_a = tmp_path / "abs_a" / study_name
    root_b = tmp_path / "abs_b" / study_name
    shutil.copytree(source, root_a)
    shutil.copytree(source, root_b)
    report_a = build_r3_thesis_report(root_a)
    report_b = build_r3_thesis_report(root_b)
    assert json.dumps(report_a, sort_keys=True) == json.dumps(report_b, sort_keys=True)


def test_documentary_isolation_when_closure_present(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path, include_closure=True)
    report = build_r3_thesis_report(root)
    assert report["documentary_claims"]["isolation_audit_at_closure"]["value"] == (
        "100/100 audited; failures=0"
    )


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
    reader = ArtifactReader(root, allowlist=build_read_allowlist(list(R3_GATE_FAMILIES)))
    original_read_bytes = Path.read_bytes
    original_open = Path.open
    allowed = {root.resolve()}

    def tracked_read_bytes(self: Path) -> bytes:
        resolved = self.resolve()
        if not any(resolved == base or base in resolved.parents for base in allowed):
            raise AssertionError(f"unexpected read outside root: {self}")
        return original_read_bytes(self)

    def tracked_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        resolved = self.resolve()
        if not any(resolved == base or base in resolved.parents for base in allowed):
            raise AssertionError(f"unexpected open outside root: {self}")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", tracked_read_bytes)
    monkeypatch.setattr(Path, "open", tracked_open)
    build_r3_thesis_report(root, reader=reader)
    assert reader.reads
    allowlist = build_read_allowlist(list(R3_GATE_FAMILIES))
    assert all(item.relative_path.endswith(".json") for item in reader.reads)
    assert all(item.relative_path in allowlist for item in reader.reads)


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
    reader = ArtifactReader(root, allowlist=build_read_allowlist(list(R3_GATE_FAMILIES)))
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
    assert report["reporter_holdout_accessed"] is False


def test_rejects_status_total_incorrect(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    (root / "breakout/status.json").write_text(
        json.dumps({"completed": 20, "total": 19}), encoding="utf-8"
    )
    with pytest.raises(R3ReportConsistencyError, match=r"status\.total"):
        build_r3_thesis_report(root)


def test_rejects_duplicate_checkpoint_seed(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    checkpoint = json.loads((root / "breakout/checkpoint.json").read_text(encoding="utf-8"))
    dup_seeds = [*REAL_SEEDS[:9], REAL_SEEDS[0]]
    checkpoint["meta"]["seeds"] = dup_seeds
    checkpoint["units"] = _checkpoint_units(seeds=dup_seeds)
    (root / "breakout/checkpoint.json").write_text(json.dumps(checkpoint), encoding="utf-8")
    with pytest.raises(R3ReportConsistencyError, match="duplicates"):
        build_r3_thesis_report(root)


def test_rejects_cross_family_seed_mismatch(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    checkpoint = json.loads((root / "funding/checkpoint.json").read_text(encoding="utf-8"))
    alt_seeds = [*REAL_SEEDS[1:], 999999]
    checkpoint["meta"]["seeds"] = alt_seeds
    checkpoint["units"] = _checkpoint_units(seeds=alt_seeds)
    (root / "funding/checkpoint.json").write_text(json.dumps(checkpoint), encoding="utf-8")
    with pytest.raises(R3ReportConsistencyError, match="seeds differ"):
        build_r3_thesis_report(root)


def test_rejects_invalid_n_pass_range(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    study = json.loads((root / "breakout/study_robustness.json").read_text(encoding="utf-8"))
    study["r3_promotion"]["by_symbol"]["BTCUSDT"]["promotion"]["positive_total_return"][
        "n_pass"
    ] = 11
    (root / "breakout/study_robustness.json").write_text(json.dumps(study), encoding="utf-8")
    with pytest.raises(R3ReportConsistencyError, match="not in"):
        build_r3_thesis_report(root)


def test_rejects_contradictory_veto_triggered(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    study = json.loads((root / "breakout/study_robustness.json").read_text(encoding="utf-8"))
    veto = study["r3_promotion"]["by_symbol"]["BTCUSDT"]["rejections"]["depends_on_few_trades"]
    veto["triggered"] = True
    veto["n_seeds_below_min_trades"] = 0
    (root / "breakout/study_robustness.json").write_text(json.dumps(study), encoding="utf-8")
    with pytest.raises(R3ReportConsistencyError, match="triggered"):
        build_r3_thesis_report(root)


def test_rejects_verdict_when_all_criteria_and_veto_pass(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path, n_pass=10)
    study = json.loads((root / "breakout/study_robustness.json").read_text(encoding="utf-8"))
    for symbol in ("BTCUSDT", "ETHUSDT"):
        block = study["r3_promotion"]["by_symbol"][symbol]
        for name in PROMOTION_TESTS:
            block["promotion"][name]["n_pass"] = 10
            block["promotion"][name]["pass"] = True
        block["rejections"]["depends_on_few_trades"]["triggered"] = False
        block["rejections"]["depends_on_few_trades"]["n_seeds_below_min_trades"] = 0
    study["by_symbol_and_engine"] = _by_symbol_and_engine(n_pass=10)
    for key in study["by_symbol_and_engine"]:
        study["by_symbol_and_engine"][key]["n_min_oos_trades_met"] = 10
    study["r3_promotion"]["triggered_rejections"] = []
    (root / "breakout/study_robustness.json").write_text(json.dumps(study), encoding="utf-8")
    with pytest.raises(R3ReportConsistencyError, match="veto cleared"):
        build_r3_thesis_report(root)


def test_rejects_audit_total_not_100(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    (root / "r3_scientific_closure_report.json").write_text(
        json.dumps(
            {
                "isolation_audit": {
                    "per_family_runs": 20,
                    "families": 5,
                    "total_runs_audited": 99,
                    "failures": 0,
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(R3ReportConsistencyError, match="total_runs_audited"):
        build_r3_thesis_report(root)


def test_rejects_missing_isolation_audit_families_field(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    (root / "r3_scientific_closure_report.json").write_text(
        json.dumps(
            {"isolation_audit": {"per_family_runs": 20, "total_runs_audited": 100, "failures": 0}}
        ),
        encoding="utf-8",
    )
    with pytest.raises(R3ReportError, match="families"):
        build_r3_thesis_report(root)


def test_rejects_incorrect_primary_engine(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    rollup = json.loads((root / "r3_family_rollup.json").read_text(encoding="utf-8"))
    rollup["primary_engine"] = "genetic_algorithm"
    (root / "r3_family_rollup.json").write_text(json.dumps(rollup), encoding="utf-8")
    with pytest.raises(R3ReportConsistencyError, match="primary_engine"):
        build_r3_thesis_report(root)


def test_rejects_incorrect_summary_n_rejected(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    rollup = json.loads((root / "r3_family_rollup.json").read_text(encoding="utf-8"))
    rollup["summary"]["n_rejected"] = 4
    (root / "r3_family_rollup.json").write_text(json.dumps(rollup), encoding="utf-8")
    with pytest.raises(R3ReportConsistencyError, match="n_rejected"):
        build_r3_thesis_report(root)


def test_rejects_missing_ga_rs_statistics(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    rollup = json.loads((root / "r3_family_rollup.json").read_text(encoding="utf-8"))
    del rollup["families"]["breakout"]["analysis"]["paired_ga_minus_rs"]["mean_difference"]
    (root / "r3_family_rollup.json").write_text(json.dumps(rollup), encoding="utf-8")
    with pytest.raises(R3ReportConsistencyError, match="mean_difference"):
        build_r3_thesis_report(root)


def test_rejects_invalid_ga_rs_ci_order(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    rollup = json.loads((root / "r3_family_rollup.json").read_text(encoding="utf-8"))
    paired = rollup["families"]["breakout"]["analysis"]["paired_ga_minus_rs"]
    paired["ci_low"], paired["ci_high"] = 0.5, -0.5
    (root / "r3_family_rollup.json").write_text(json.dumps(rollup), encoding="utf-8")
    with pytest.raises(R3ReportConsistencyError, match="CI low > high"):
        build_r3_thesis_report(root)


def test_rejects_missing_provenance_field(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    identity = json.loads((root / "breakout/run_identity.json").read_text(encoding="utf-8"))
    del identity["worktree"]["reproducible_from_commit_alone"]
    (root / "breakout/run_identity.json").write_text(json.dumps(identity), encoding="utf-8")
    with pytest.raises(R3ReportError, match="reproducible_from_commit_alone"):
        build_r3_thesis_report(root)


def test_rejects_reader_root_mismatch(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    other_root = tmp_path / "other"
    other_root.mkdir()
    reader = ArtifactReader(other_root, allowlist=build_read_allowlist(list(R3_GATE_FAMILIES)))
    with pytest.raises(R3ReportError, match="ArtifactReader root"):
        build_r3_thesis_report(root, reader=reader)


def test_rejects_study_root_under_forbidden_data_path(tmp_path: Path) -> None:
    root = tmp_path / "data" / "processed" / "r3_full"
    root.mkdir(parents=True)
    with pytest.raises(R3ReportError, match="forbidden"):
        build_r3_thesis_report(root)


def test_rejects_non_json_read(tmp_path: Path) -> None:
    root = _write_full_r3_root(tmp_path)
    reader = ArtifactReader(root, allowlist=build_read_allowlist(list(R3_GATE_FAMILIES)))
    with pytest.raises(R3ReportError, match="only JSON"):
        reader.read_json("breakout/status.txt")


def test_source_artifacts_unchanged_after_report_generation(tmp_path: Path) -> None:
    import hashlib

    root = _write_full_r3_root(tmp_path)
    allowlist = build_read_allowlist(list(R3_GATE_FAMILIES))
    paths = sorted(root / rel for rel in allowlist if (root / rel).exists())

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    before = {path.relative_to(root).as_posix(): digest(path) for path in paths}
    out_dir = tmp_path / "reports_out"
    write_r3_thesis_report(root, out_dir)
    after = {path.relative_to(root).as_posix(): digest(path) for path in paths}
    assert before == after


def test_portability_byte_identical_outputs(tmp_path: Path) -> None:
    import hashlib
    import shutil

    source = _write_full_r3_root(tmp_path)
    study_name = "r3_full_budget100_ga21"
    root_a = tmp_path / "abs_a" / study_name
    root_b = tmp_path / "abs_b" / study_name
    shutil.copytree(source, root_a)
    shutil.copytree(source, root_b)
    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"
    write_r3_thesis_report(root_a, out_a)
    write_r3_thesis_report(root_b, out_b)
    json_a = (out_a / "thesis_report.json").read_bytes()
    json_b = (out_b / "thesis_report.json").read_bytes()
    md_a = (out_a / "thesis_report.md").read_bytes()
    md_b = (out_b / "thesis_report.md").read_bytes()
    assert json_a == json_b
    assert md_a == md_b
    assert hashlib.sha256(json_a).hexdigest() == hashlib.sha256(json_b).hexdigest()
