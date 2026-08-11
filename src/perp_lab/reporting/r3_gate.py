"""Read-only Gate R3 thesis reporting from persisted run artifacts.

Derives Markdown and JSON tables for the TFM without recomputing backtests,
reading holdout or development market data, or modifying original R3 artifacts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any, Literal

import numpy as np

from perp_lab.evaluation.study_robustness import (
    PROMOTION_TESTS,
    R3_MIN_OOS_TRADES,
    R3_PRIMARY_ENGINE,
)

SECONDARY_ENGINE = "genetic_algorithm"

R3_GATE_FAMILIES: tuple[str, ...] = (
    "breakout",
    "mean_reversion",
    "volatility_breakout",
    "funding",
    "BTC_ETH_confirmation",
)
R3_EXPECTED_SYMBOLS: tuple[str, ...] = ("BTCUSDT", "ETHUSDT")
R3_EXPECTED_SEEDS = 10
R3_EXPECTED_UNITS_PER_FAMILY = 20
R3_EXPECTED_TOTAL_UNITS = 100
R3_MAJORITY_REQUIRED = 6
HOLDOUT_START = datetime(2026, 1, 1, tzinfo=UTC)

FORBIDDEN_READ_SEGMENTS = (
    "data/raw",
    "data/validated",
    "data/processed",
    "/holdout/",
    "\\holdout\\",
)

REQUIRED_ROOT_ARTIFACTS = (
    "r3_execution.json",
    "r3_gate_verdict.json",
    "r3_family_rollup.json",
    "r3_scientific_closure_report.json",
)

PER_FAMILY_ARTIFACTS = (
    "study_robustness.json",
    "status.json",
    "checkpoint.json",
    "run_identity.json",
)


def build_read_allowlist(families: list[str]) -> frozenset[str]:
    """Explicit JSON allowlist for a complete Gate R3 study root."""
    allowed: set[str] = set(REQUIRED_ROOT_ARTIFACTS)
    allowed.add("r3_gate_report.json")
    for family in families:
        for name in PER_FAMILY_ARTIFACTS:
            allowed.add(f"{family}/{name}")
    return frozenset(allowed)


CRITERION_LABELS: dict[str, str] = {
    "positive_total_return": "C1 positive return",
    "bootstrap_sharpe_ci_excludes_zero": "C2 bootstrap Sharpe CI",
    "survives_double_costs": "C3 survives 2x costs",
    "beats_buy_and_hold": "C4 beats buy-and-hold",
    "survives_drop_top_trades": "C5 drop top 5 trades",
    "not_confined_to_one_fold": "C6 fold locality",
}

TALLY_FIELDS: dict[str, str] = {
    "positive_total_return": "n_positive",
    "bootstrap_sharpe_ci_excludes_zero": "n_bootstrap_ci_excludes_zero",
    "survives_double_costs": "n_survive_double_costs",
    "beats_buy_and_hold": "n_beat_buy_and_hold",
    "survives_drop_top_trades": "n_survives_drop_top_trades",
    "not_confined_to_one_fold": "n_not_confined_to_one_fold",
}

Classification = Literal["primary_result", "secondary_diagnostic", "limitation"]
VerificationLevel = Literal["reporter_verified", "documentary", "limitation"]


class R3ReportError(Exception):
    """Raised when required artifacts are missing or inputs are invalid."""


class R3ReportConsistencyError(R3ReportError):
    """Raised when persisted numeric fields contradict each other."""


@dataclass(frozen=True)
class R3GatePaths:
    root: Path
    execution: Path
    gate_verdict: Path
    rollup: Path
    gate_report: Path | None = None
    scientific_closure: Path | None = None


@dataclass
class ArtifactRead:
    relative_path: str
    sha256: str


@dataclass
class ArtifactReader:
    """Read-only JSON loader confined to an R3 study root."""

    root: Path
    allowlist: frozenset[str] | None = None
    reads: list[ArtifactRead] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.root = self.root.resolve()

    def read_json(self, relative_path: str | Path) -> dict[str, Any]:
        path = self._resolve_allowed(relative_path)
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        rel = path.relative_to(self.root).as_posix()
        self.reads.append(ArtifactRead(relative_path=rel, sha256=digest))
        loaded = json.loads(payload.decode("utf-8"))
        if not isinstance(loaded, dict):
            raise R3ReportError(f"expected JSON object in {rel}")
        return loaded

    def manifest(self) -> list[dict[str, str]]:
        by_path: dict[str, str] = {}
        for item in self.reads:
            by_path[item.relative_path] = item.sha256
        return [
            {"relative_path": path, "sha256": digest}
            for path, digest in sorted(by_path.items())
        ]

    def _resolve_allowed(self, relative_path: str | Path) -> Path:
        candidate = Path(relative_path)
        if candidate.is_absolute():
            raise R3ReportError(f"absolute read paths are forbidden: {relative_path}")
        path = (self.root / candidate).resolve()
        if not path.is_relative_to(self.root):
            raise R3ReportError(f"read outside R3 root forbidden: {relative_path}")
        rel_posix = path.relative_to(self.root).as_posix()
        lowered = rel_posix.lower()
        if not lowered.endswith(".json"):
            raise R3ReportError(f"only JSON artifacts may be read: {rel_posix}")
        if any(segment in lowered for segment in FORBIDDEN_READ_SEGMENTS):
            raise R3ReportError(f"forbidden artifact path: {rel_posix}")
        if self.allowlist is not None and rel_posix not in self.allowlist:
            raise R3ReportError(f"artifact not on read allowlist: {rel_posix}")
        if not path.exists():
            raise R3ReportError(f"required artifact missing: {rel_posix}")
        return path


def default_r3_root() -> Path:
    return Path("artifacts/runs/r3_full_budget100_ga21")


def resolve_r3_paths(root: Path) -> R3GatePaths:
    root = root.resolve()
    gate_report = root / "r3_gate_report.json"
    scientific = root / "r3_scientific_closure_report.json"
    return R3GatePaths(
        root=root,
        execution=root / "r3_execution.json",
        gate_verdict=root / "r3_gate_verdict.json",
        rollup=root / "r3_family_rollup.json",
        gate_report=gate_report if gate_report.exists() else None,
        scientific_closure=scientific if scientific.exists() else None,
    )


def _require_key(payload: dict[str, Any], key: str, *, context: str) -> Any:
    if key not in payload:
        raise R3ReportError(f"missing required field {key!r} in {context}")
    return payload[key]


def _stable_root_label(root: Path) -> str:
    return f"artifacts/runs/{root.name}"


def _fmt_pct(value: float | None) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"{value:+.1%}"


def _fmt_sharpe(value: float | None) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"{value:.2f}"


def _tally_cell(n_pass: int, n_seeds: int, *, required: int) -> str:
    status = "OK" if n_pass >= required else "FAIL"
    return f"{n_pass}/{n_seeds} {status}"


def _parse_oos_end(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace(" ", "T") if "T" not in value else value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _median_strategy_sharpe(study: dict[str, Any], symbol: str, engine: str) -> float | None:
    values: list[float] = []
    for entry in study.get("per_run", {}).values():
        if entry.get("symbol") != symbol or entry.get("method") != engine:
            continue
        sharpe = entry.get("strategy", {}).get("sharpe")
        if sharpe is not None and np.isfinite(float(sharpe)):
            values.append(float(sharpe))
    if not values:
        return None
    return float(median(values))


def _trace_entry(
    *,
    claim: str,
    value: Any,
    source_file: str,
    source_field: str,
    classification: Classification,
    verification_level: VerificationLevel,
    derivation: str | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "claim": claim,
        "value": value,
        "source_file": source_file,
        "source_field": source_field,
        "classification": classification,
        "verification_level": verification_level,
    }
    if derivation:
        entry["derivation"] = derivation
    return entry


def _validate_output_dir(root: Path, output_dir: Path) -> Path:
    root = root.resolve()
    output_dir = output_dir.resolve()
    if output_dir == root or root in output_dir.parents:
        raise R3ReportError("output_dir must not coincide with or lie inside the R3 study root")
    return output_dir


def _family_order(execution: dict[str, Any]) -> list[str]:
    order = _require_key(execution, "frozen_order", context="r3_execution.json")
    if not isinstance(order, list):
        raise R3ReportError("r3_execution.json frozen_order must be a list")
    return [str(item) for item in order]


def _validate_checkpoint_units(reader: ArtifactReader, family: str) -> list[str]:
    """Validate the 20 planned units recorded in checkpoint.units for one family."""
    discrepancies: list[str] = []
    checkpoint = reader.read_json(f"{family}/checkpoint.json")
    meta = _require_key(checkpoint, "meta", context=f"{family}/checkpoint.json")
    symbols = list(_require_key(meta, "symbols", context=f"{family}/checkpoint.json meta"))
    seeds = list(_require_key(meta, "seeds", context=f"{family}/checkpoint.json meta"))
    units = _require_key(checkpoint, "units", context=f"{family}/checkpoint.json")

    if list(symbols) != list(R3_EXPECTED_SYMBOLS):
        discrepancies.append(f"{family}: checkpoint symbols {symbols!r} != expected")
    if len(seeds) != R3_EXPECTED_SEEDS:
        discrepancies.append(
            f"{family}: checkpoint seeds count {len(seeds)} != {R3_EXPECTED_SEEDS}"
        )

    expected_keys = {f"{symbol}|seed={seed}" for symbol in symbols for seed in seeds}
    if len(units) != R3_EXPECTED_UNITS_PER_FAMILY:
        discrepancies.append(
            f"{family}: checkpoint.units count {len(units)} != {R3_EXPECTED_UNITS_PER_FAMILY}"
        )
    if set(units) != expected_keys:
        discrepancies.append(f"{family}: checkpoint.units keys != expected symbol|seed grid")

    for key, unit in units.items():
        symbol = unit.get("symbol")
        seed = unit.get("seed")
        if symbol not in R3_EXPECTED_SYMBOLS:
            discrepancies.append(f"{family}/{key}: unit symbol {symbol!r} invalid")
        if seed not in seeds:
            discrepancies.append(f"{family}/{key}: unit seed {seed!r} not in checkpoint.meta.seeds")
        if key != f"{symbol}|seed={seed}":
            discrepancies.append(f"{family}/{key}: unit key inconsistent with symbol/seed fields")

    status = reader.read_json(f"{family}/status.json")
    completed = int(_require_key(status, "completed", context=f"{family}/status.json"))
    total = int(_require_key(status, "total", context=f"{family}/status.json"))
    if total != R3_EXPECTED_UNITS_PER_FAMILY:
        discrepancies.append(f"{family}: status.total {total} != {R3_EXPECTED_UNITS_PER_FAMILY}")
    if completed != len(units):
        discrepancies.append(
            f"{family}: status.completed {completed} != checkpoint.units count {len(units)}"
        )
    return discrepancies


def _validate_units_aggregate(reader: ArtifactReader, families: list[str]) -> tuple[int, int]:
    discrepancies: list[str] = []
    total_units = 0
    total_completed = 0
    for family in families:
        discrepancies.extend(_validate_checkpoint_units(reader, family))
        checkpoint = reader.read_json(f"{family}/checkpoint.json")
        status = reader.read_json(f"{family}/status.json")
        total_units += len(checkpoint["units"])
        total_completed += int(status["completed"])
    if total_units != R3_EXPECTED_TOTAL_UNITS:
        discrepancies.append(
            f"aggregate checkpoint.units count {total_units} != {R3_EXPECTED_TOTAL_UNITS}"
        )
    if total_completed != R3_EXPECTED_TOTAL_UNITS:
        discrepancies.append(
            f"aggregate status.completed {total_completed} != {R3_EXPECTED_TOTAL_UNITS}"
        )
    if discrepancies:
        raise R3ReportConsistencyError("; ".join(discrepancies))
    return total_completed, total_units


def _load_provenance_by_family(reader: ArtifactReader, families: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in families:
        identity = reader.read_json(f"{family}/run_identity.json")
        worktree = _require_key(identity, "worktree", context=f"{family}/run_identity.json")
        components = identity.get("components", {})
        rows.append(
            {
                "family": family,
                "commit": worktree.get("commit") or components.get("commit"),
                "diff_sha256": worktree.get("diff_sha256") or components.get("diff_sha256"),
                "diff_bytes": worktree.get("diff_bytes"),
                "untracked_sha256": worktree.get("untracked_sha256")
                or components.get("untracked_sha256"),
                "dirty": bool(worktree.get("dirty")),
                "provisional": bool(identity.get("provisional")),
                "reproducible_from_commit_alone": bool(
                    worktree.get("reproducible_from_commit_alone", False)
                ),
                "patch_bytes_stored": any(
                    key in worktree
                    for key in ("patch_bytes", "diff_content", "diff_patch", "patch")
                ),
                "source_file": f"{family}/run_identity.json",
            }
        )
    return rows


def _group_provenance_states(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[str]] = {}
    for row in rows:
        key = (
            row.get("commit"),
            row.get("diff_sha256"),
            row.get("diff_bytes"),
            row.get("untracked_sha256"),
            row.get("dirty"),
            row.get("provisional"),
            row.get("reproducible_from_commit_alone"),
        )
        grouped.setdefault(key, []).append(str(row["family"]))
    states: list[dict[str, Any]] = []
    for index, (key, families) in enumerate(
        sorted(grouped.items(), key=lambda item: item[1]), start=1
    ):
        commit, diff_sha256, diff_bytes, untracked_sha256, dirty, provisional, reproducible = key
        states.append(
            {
                "state_id": f"tracked_state_{index}",
                "families": sorted(families),
                "commit": commit,
                "diff_sha256": diff_sha256,
                "diff_bytes": diff_bytes,
                "untracked_sha256": untracked_sha256,
                "dirty": dirty,
                "provisional": provisional,
                "reproducible_from_commit_alone": reproducible,
            }
        )
    return states


def _validate_execution_contract(execution: dict[str, Any], families: list[str]) -> list[str]:
    discrepancies: list[str] = []
    if list(families) != list(R3_GATE_FAMILIES):
        discrepancies.append(
            f"execution frozen_order {families!r} != expected {list(R3_GATE_FAMILIES)!r}"
        )
    symbols = _require_key(execution, "symbols", context="r3_execution.json")
    if list(symbols) != list(R3_EXPECTED_SYMBOLS):
        discrepancies.append(f"execution symbols {symbols!r} != expected")
    n_seeds = _require_key(execution, "n_seeds", context="r3_execution.json")
    if int(n_seeds) != R3_EXPECTED_SEEDS:
        discrepancies.append(f"execution n_seeds {n_seeds!r} != {R3_EXPECTED_SEEDS}")
    exec_families = _require_key(execution, "families", context="r3_execution.json")
    if set(exec_families) != set(R3_GATE_FAMILIES):
        discrepancies.append("execution families keys mismatch expected five families")
    for family in R3_GATE_FAMILIES:
        meta = exec_families.get(family)
        if meta is None:
            discrepancies.append(f"execution missing family {family!r}")
            continue
        if meta.get("status") != "completed":
            discrepancies.append(f"execution family {family!r} status != completed")
    return discrepancies


def _validate_verdict_contract(verdict: dict[str, Any]) -> list[str]:
    discrepancies: list[str] = []
    checks = {
        "gate_status": "CLOSED_NEGATIVE",
        "n_promoted": 0,
        "n_rejected": 5,
        "r4_required": False,
    }
    for key, expected in checks.items():
        actual = _require_key(verdict, key, context="r3_gate_verdict.json")
        if actual != expected:
            discrepancies.append(f"gate_verdict {key}={actual!r}, expected {expected!r}")
    promoted = verdict.get("promoted_families", [])
    if promoted:
        discrepancies.append(f"gate_verdict promoted_families must be empty, got {promoted!r}")
    rejected = verdict.get("rejected_families", [])
    if sorted(rejected) != sorted(R3_GATE_FAMILIES):
        discrepancies.append("gate_verdict rejected_families mismatch expected five families")
    return discrepancies


def _validate_oos_temporal(study: dict[str, Any], *, family: str) -> list[str]:
    discrepancies: list[str] = []
    per_run = study.get("per_run", {})
    if not per_run:
        discrepancies.append(f"{family}: study_robustness.json has no per_run entries")
        return discrepancies
    for key, entry in per_run.items():
        oos_end_raw = entry.get("oos_end")
        if oos_end_raw is None:
            discrepancies.append(f"{family}/{key}: missing oos_end")
            continue
        oos_end = _parse_oos_end(str(oos_end_raw))
        if oos_end >= HOLDOUT_START:
            discrepancies.append(
                f"{family}/{key}: oos_end {oos_end.isoformat()} reaches holdout start"
            )
    return discrepancies


def _validate_engine_coverage(study: dict[str, Any], *, family: str, n_seeds: int) -> list[str]:
    discrepancies: list[str] = []
    by_engine = study.get("by_symbol_and_engine", {})
    for symbol in R3_EXPECTED_SYMBOLS:
        for engine in (R3_PRIMARY_ENGINE, SECONDARY_ENGINE):
            key = f"{symbol}|{engine}"
            block = by_engine.get(key)
            if block is None:
                discrepancies.append(f"{family}: missing by_symbol_and_engine[{key!r}]")
                continue
            if int(block.get("n_seeds", -1)) != n_seeds:
                discrepancies.append(
                    f"{family}/{key}: n_seeds {block.get('n_seeds')!r} != {n_seeds}"
                )
    per_run = study.get("per_run", {})
    for symbol in R3_EXPECTED_SYMBOLS:
        for engine in (R3_PRIMARY_ENGINE, SECONDARY_ENGINE):
            count = sum(
                1
                for entry in per_run.values()
                if entry.get("symbol") == symbol and entry.get("method") == engine
            )
            if count != n_seeds:
                discrepancies.append(
                    f"{family}/{symbol}/{engine}: per_run coverage {count}/{n_seeds}"
                )
    return discrepancies


def _validate_promotion_row(
    *,
    family: str,
    symbol: str,
    promo_row: dict[str, Any],
    tally: dict[str, Any],
    n_seeds: int,
    majority: int,
) -> list[str]:
    discrepancies: list[str] = []
    if set(promo_row.keys()) != set(PROMOTION_TESTS):
        discrepancies.append(
            f"{family}/{symbol}: expected exactly six promotion criteria, got {sorted(promo_row)}"
        )
    for name in PROMOTION_TESTS:
        row = promo_row[name]
        required = int(_require_key(row, "required", context=f"{family}/{symbol}/{name}"))
        if required != majority:
            discrepancies.append(f"{family}/{symbol}/{name}: required {required} != {majority}")
        n_pass = int(_require_key(row, "n_pass", context=f"{family}/{symbol}/{name}"))
        passed = bool(_require_key(row, "pass", context=f"{family}/{symbol}/{name}"))
        if passed != (n_pass >= required):
            discrepancies.append(
                f"{family}/{symbol}/{name}: pass={passed} inconsistent with n_pass={n_pass}"
            )
        tally_val = tally.get(TALLY_FIELDS[name])
        if tally_val != n_pass:
            discrepancies.append(
                f"{family}/{symbol}/{name}: tally {tally_val} != promotion n_pass {n_pass}"
            )
    return discrepancies


def _validate_rollup_medians(
    *,
    family: str,
    symbol: str,
    rollup_sym: dict[str, Any],
    tally: dict[str, Any],
    med_sharpe: float | None,
) -> list[str]:
    discrepancies: list[str] = []
    for field_name, tally_key in (
        ("median_total_return", "median_total_return"),
        ("median_buy_and_hold_return", "median_buy_and_hold_return"),
    ):
        rollup_val = rollup_sym.get(field_name)
        tally_val = tally.get(tally_key)
        if rollup_val is None or tally_val is None:
            discrepancies.append(
                f"{family}/{symbol}: missing {field_name} in rollup or study tally"
            )
            continue
        if abs(float(rollup_val) - float(tally_val)) > 1e-9:
            discrepancies.append(
                f"{family}/{symbol}: {field_name} rollup={rollup_val} != study={tally_val}"
            )
    rollup_positive = rollup_sym.get("n_positive")
    tally_positive = tally.get("n_positive")
    if rollup_positive != tally_positive:
        discrepancies.append(
            f"{family}/{symbol}: rollup n_positive {rollup_positive} != study {tally_positive}"
        )
    if (
        med_sharpe is not None
        and rollup_sym.get("median_sharpe") is not None
        and abs(float(rollup_sym["median_sharpe"]) - float(med_sharpe)) > 1e-9
    ):
        discrepancies.append(f"{family}/{symbol}: median_sharpe mismatch rollup vs study")
    return discrepancies


def _validate_veto_and_verdict(
    *,
    family: str,
    symbol: str,
    symbol_promo: dict[str, Any],
    family_verdict: str,
) -> list[str]:
    discrepancies: list[str] = []
    promo_block = symbol_promo["promotion"]
    rejections = symbol_promo["rejections"]
    min_trades = rejections["depends_on_few_trades"]

    if "min_oos_trades_met" in promo_block:
        discrepancies.append(
            f"{family}/{symbol}: min_oos_trades_met must not be a promotion criterion"
        )

    if min_trades.get("triggered") and family_verdict == "PROMOTED":
        discrepancies.append(
            f"{family}/{symbol}: min_oos_trades veto triggered but family verdict is PROMOTED"
        )
    return discrepancies


def _validate_family_promotion_semantics(
    *,
    family: str,
    promo: dict[str, Any],
    family_verdict: str,
) -> list[str]:
    discrepancies: list[str] = []
    if promo.get("engine") != R3_PRIMARY_ENGINE:
        discrepancies.append(f"{family}: promotion engine must be random_search")
    if promo.get("verdict") != family_verdict:
        discrepancies.append(
            f"{family}: study verdict {promo.get('verdict')!r} != rollup {family_verdict!r}"
        )
    if family_verdict == "PROMOTED":
        discrepancies.append(f"{family}: CLOSED_NEGATIVE gate cannot contain PROMOTED family")
    elif family_verdict != "REJECTED":
        discrepancies.append(f"{family}: expected family verdict REJECTED, got {family_verdict!r}")

    both_symbols_pass_all_six = True
    for symbol in R3_EXPECTED_SYMBOLS:
        if symbol not in promo.get("by_symbol", {}):
            discrepancies.append(f"{family}: missing r3_promotion.by_symbol[{symbol!r}]")
            continue
        symbol_promo = promo["by_symbol"][symbol]
        discrepancies.extend(
            _validate_veto_and_verdict(
                family=family,
                symbol=symbol,
                symbol_promo=symbol_promo,
                family_verdict=family_verdict,
            )
        )
        if not all(symbol_promo["promotion"][name]["pass"] for name in PROMOTION_TESTS):
            both_symbols_pass_all_six = False

    if both_symbols_pass_all_six and family_verdict == "REJECTED":
        any_veto = any(
            promo["by_symbol"][symbol]["rejections"]["depends_on_few_trades"].get("triggered")
            for symbol in R3_EXPECTED_SYMBOLS
        )
        any_rejection = bool(promo.get("triggered_rejections"))
        if not any_veto and not any_rejection:
            discrepancies.append(
                f"{family}: all six criteria pass on both assets but family verdict is REJECTED"
            )
    return discrepancies


def _require_documentary_isolation_audit(reader: ArtifactReader) -> dict[str, Any]:
    payload = reader.read_json("r3_scientific_closure_report.json")
    audit = _require_key(payload, "isolation_audit", context="r3_scientific_closure_report.json")
    total = int(_require_key(audit, "total_runs_audited", context="isolation_audit"))
    failures = int(_require_key(audit, "failures", context="isolation_audit"))
    if total != R3_EXPECTED_TOTAL_UNITS:
        raise R3ReportConsistencyError(
            f"documentary isolation_audit.total_runs_audited={total}, expected 100"
        )
    if failures != 0:
        raise R3ReportConsistencyError(
            f"documentary isolation_audit.failures={failures}, expected 0"
        )
    per_family = audit.get("per_family_runs")
    if per_family is not None and int(per_family) != R3_EXPECTED_UNITS_PER_FAMILY:
        raise R3ReportConsistencyError(
            f"documentary isolation_audit.per_family_runs={per_family}, expected 20"
        )
    return {
        "value": f"{total}/{total} audited; failures={failures}",
        "source_file": "r3_scientific_closure_report.json",
        "source_field": "isolation_audit",
        "verification_level": "documentary",
        "note": "Recorded at R3 closure; not re-executed by this reporter",
    }


def _derive_provenance_limitation(
    rows: list[dict[str, Any]], states: list[dict[str, Any]]
) -> dict[str, Any]:
    commits = sorted({str(row["commit"]) for row in rows if row.get("commit")})
    all_dirty = all(bool(row.get("dirty")) for row in rows)
    all_not_reproducible = all(not bool(row.get("reproducible_from_commit_alone")) for row in rows)
    patch_bytes_available = any(
        row.get("diff_bytes") is not None and row.get("patch_bytes_stored") for row in rows
    )
    notes: list[str] = []
    if all_dirty:
        notes.append("every family run_identity.json records worktree.dirty=true")
    if all_not_reproducible:
        notes.append("every family records reproducible_from_commit_alone=false")
    if len(states) > 1:
        notes.append(f"{len(states)} distinct tracked diff states observed across families")
    if not patch_bytes_available:
        notes.append("patch bytes were not retained in persisted run_identity.json artifacts")
    return {
        "provenance_by_family": rows,
        "provenance_states": states,
        "distinct_commits": commits,
        "distinct_tracked_states": len(states),
        "patch_bytes_available": patch_bytes_available,
        "exact_reconstruction_from_commit_alone": False if all_not_reproducible else None,
        "note": "; ".join(notes),
        "verification_level": "limitation",
    }


def _partial_signal_note(family: str, symbol: str, row: dict[str, Any]) -> str | None:
    if family != "volatility_breakout" or symbol != "BTCUSDT":
        return None
    c1 = row["criteria"]["positive_total_return"]["n_pass"]
    if c1 >= row["majority_required"] and row["verdict"] == "REJECTED":
        return "partial non-robust signal (not promotion-eligible)"
    return None


def build_r3_thesis_report(root: Path, *, reader: ArtifactReader | None = None) -> dict[str, Any]:
    """Build a deterministic thesis report payload from persisted Gate R3 artifacts."""
    paths = resolve_r3_paths(root)
    artifact_reader = reader or ArtifactReader(
        paths.root, allowlist=build_read_allowlist(list(R3_GATE_FAMILIES))
    )
    if artifact_reader.allowlist is None:
        artifact_reader.allowlist = build_read_allowlist(list(R3_GATE_FAMILIES))

    execution = artifact_reader.read_json("r3_execution.json")
    verdict = artifact_reader.read_json("r3_gate_verdict.json")
    rollup = artifact_reader.read_json("r3_family_rollup.json")

    families = _family_order(execution)
    artifact_reader.allowlist = build_read_allowlist(families)
    n_seeds = int(_require_key(execution, "n_seeds", context="r3_execution.json"))
    if n_seeds != R3_EXPECTED_SEEDS:
        raise R3ReportConsistencyError(f"expected n_seeds={R3_EXPECTED_SEEDS}, got {n_seeds}")
    majority = R3_MAJORITY_REQUIRED if n_seeds == 10 else max(1, (n_seeds // 2) + 1)
    if majority != R3_MAJORITY_REQUIRED:
        raise R3ReportConsistencyError(
            f"expected majority threshold {R3_MAJORITY_REQUIRED}, got {majority}"
        )

    discrepancies: list[str] = []
    discrepancies.extend(_validate_execution_contract(execution, families))
    discrepancies.extend(_validate_verdict_contract(verdict))
    if set(rollup.get("families", {})) != set(R3_GATE_FAMILIES):
        discrepancies.append("rollup families mismatch expected five families")
    if rollup.get("summary", {}).get("n_promoted", -1) != 0:
        discrepancies.append("rollup summary n_promoted must be 0")
    if any(
        row.get("analysis", {}).get("verdict") == "PROMOTED" for row in rollup["families"].values()
    ):
        discrepancies.append("no family may be PROMOTED in rollup")

    units_completed, units_expected = _validate_units_aggregate(artifact_reader, families)

    provenance_rows = _load_provenance_by_family(artifact_reader, families)
    provenance_states = _group_provenance_states(provenance_rows)
    documentary_isolation = _require_documentary_isolation_audit(artifact_reader)

    primary_rows: list[dict[str, Any]] = []
    rs_ga_rows: list[dict[str, Any]] = []
    traceability: list[dict[str, Any]] = []

    for family in families:
        if family not in rollup["families"]:
            discrepancies.append(f"rollup missing family {family!r}")
            continue
        family_meta = rollup["families"][family]
        analysis = family_meta.get("analysis")
        if analysis is None:
            discrepancies.append(f"family {family!r} has no rollup analysis")
            continue

        study = artifact_reader.read_json(f"{family}/study_robustness.json")
        promo = _require_key(study, "r3_promotion", context=f"{family}/study_robustness.json")
        discrepancies.extend(
            _validate_family_promotion_semantics(
                family=family,
                promo=promo,
                family_verdict=str(analysis["verdict"]),
            )
        )
        if analysis["verdict"] == "PROMOTED":
            discrepancies.append(f"{family}: rejected families cannot be PROMOTED")

        discrepancies.extend(_validate_oos_temporal(study, family=family))
        discrepancies.extend(_validate_engine_coverage(study, family=family, n_seeds=n_seeds))

        paired = analysis["paired_ga_minus_rs"]
        rs_ga_rows.append(
            {
                "family": family,
                "mean_difference_ga_minus_rs": paired.get("mean_difference"),
                "ci_low": paired.get("ci_low"),
                "ci_high": paired.get("ci_high"),
                "interpretation": paired.get("verdict"),
                "ga_does_not_decide_promotion": True,
                "source_file": "r3_family_rollup.json",
                "source_field": f"families.{family}.analysis.paired_ga_minus_rs",
            }
        )

        by_symbol_rs = analysis.get("by_symbol_rs", {})
        if sorted(by_symbol_rs) != sorted(R3_EXPECTED_SYMBOLS):
            discrepancies.append(f"{family}: rollup by_symbol_rs symbols mismatch")

        for symbol in R3_EXPECTED_SYMBOLS:
            if symbol not in promo.get("by_symbol", {}):
                discrepancies.append(f"{family}: missing r3_promotion.by_symbol[{symbol!r}]")
                continue
            if symbol not in by_symbol_rs:
                discrepancies.append(f"{family}: missing rollup by_symbol_rs[{symbol!r}]")
                continue
            rs_key = f"{symbol}|{R3_PRIMARY_ENGINE}"
            rs_tally = study["by_symbol_and_engine"][rs_key]
            symbol_promo = promo["by_symbol"][symbol]
            if int(symbol_promo["n_seeds"]) != n_seeds:
                discrepancies.append(f"{family}/{symbol}: symbol n_seeds mismatch")
            if int(symbol_promo["majority_required"]) != majority:
                discrepancies.append(f"{family}/{symbol}: unexpected majority threshold")

            promo_block = symbol_promo["promotion"]
            discrepancies.extend(
                _validate_promotion_row(
                    family=family,
                    symbol=symbol,
                    promo_row=promo_block,
                    tally=rs_tally,
                    n_seeds=n_seeds,
                    majority=majority,
                )
            )

            min_trades = symbol_promo["rejections"]["depends_on_few_trades"]
            n_min_ok = int(rs_tally.get("n_min_oos_trades_met", 0))
            n_below = int(min_trades.get("n_seeds_below_min_trades", 0))
            if n_min_ok + n_below != int(symbol_promo["n_seeds"]):
                discrepancies.append(f"{family}/{symbol}: min-trade seed counts inconsistent")

            med_sharpe = _median_strategy_sharpe(study, symbol, R3_PRIMARY_ENGINE)
            rollup_sym = by_symbol_rs[symbol]
            discrepancies.extend(
                _validate_rollup_medians(
                    family=family,
                    symbol=symbol,
                    rollup_sym=rollup_sym,
                    tally=rs_tally,
                    med_sharpe=med_sharpe,
                )
            )

            criteria: dict[str, Any] = {}
            for name in PROMOTION_TESTS:
                promo_row = promo_block[name]
                criteria[name] = {
                    "label": CRITERION_LABELS[name],
                    "n_pass": int(promo_row["n_pass"]),
                    "n_seeds": int(symbol_promo["n_seeds"]),
                    "majority_required": int(promo_row["required"]),
                    "pass": bool(promo_row["pass"]),
                    "display": _tally_cell(
                        int(promo_row["n_pass"]),
                        int(symbol_promo["n_seeds"]),
                        required=int(promo_row["required"]),
                    ),
                    "source_file": f"{family}/study_robustness.json",
                    "source_field": f"r3_promotion.by_symbol.{symbol}.promotion.{name}",
                }

            row = {
                "family": family,
                "symbol": symbol,
                "engine": R3_PRIMARY_ENGINE,
                "criteria": criteria,
                "min_oos_trades_met": {
                    "n_pass": n_min_ok,
                    "n_seeds": int(symbol_promo["n_seeds"]),
                    "min_trades_required": R3_MIN_OOS_TRADES,
                    "veto_triggered": bool(min_trades.get("triggered")),
                    "display": _tally_cell(
                        n_min_ok, int(symbol_promo["n_seeds"]), required=n_seeds
                    ),
                    "role": "separate veto (not a seventh promotion criterion)",
                    "source_file": f"{family}/study_robustness.json",
                    "source_field": (
                        f"r3_promotion.by_symbol.{symbol}.rejections.depends_on_few_trades"
                    ),
                },
                "median_oos_return": rs_tally.get("median_total_return"),
                "median_oos_sharpe": med_sharpe,
                "median_buy_and_hold_return": rs_tally.get("median_buy_and_hold_return"),
                "verdict": analysis["verdict"],
                "majority_required": majority,
            }
            note = _partial_signal_note(family, symbol, row)
            if note:
                row["diagnostic_note"] = note
            primary_rows.append(row)

            for name in PROMOTION_TESTS:
                traceability.append(
                    _trace_entry(
                        claim=f"{family}/{symbol} {CRITERION_LABELS[name]}",
                        value=criteria[name]["display"],
                        source_file=criteria[name]["source_file"],
                        source_field=criteria[name]["source_field"],
                        classification=(
                            "secondary_diagnostic"
                            if note and name == "positive_total_return"
                            else "primary_result"
                        ),
                        verification_level="reporter_verified",
                    )
                )
            traceability.append(
                _trace_entry(
                    claim=f"{family}/{symbol} min_oos_trades_met veto",
                    value=row["min_oos_trades_met"]["display"],
                    source_file=row["min_oos_trades_met"]["source_file"],
                    source_field=row["min_oos_trades_met"]["source_field"],
                    classification="primary_result",
                    verification_level="reporter_verified",
                )
            )
            traceability.append(
                _trace_entry(
                    claim=f"{family}/{symbol} median OOS return",
                    value=row["median_oos_return"],
                    source_file=f"{family}/study_robustness.json",
                    source_field=f"by_symbol_and_engine.{symbol}|random_search.median_total_return",
                    classification="primary_result",
                    verification_level="reporter_verified",
                )
            )
            traceability.append(
                _trace_entry(
                    claim=f"{family}/{symbol} median OOS Sharpe",
                    value=row["median_oos_sharpe"],
                    source_file=f"{family}/study_robustness.json",
                    source_field="per_run[].strategy.sharpe",
                    derivation="median of per_run strategy.sharpe for symbol and random_search",
                    classification="primary_result",
                    verification_level="reporter_verified",
                )
            )
            traceability.append(
                _trace_entry(
                    claim=f"{family}/{symbol} median buy-and-hold return",
                    value=row["median_buy_and_hold_return"],
                    source_file=f"{family}/study_robustness.json",
                    source_field=(
                        f"by_symbol_and_engine.{symbol}|random_search.median_buy_and_hold_return"
                    ),
                    classification="primary_result",
                    verification_level="reporter_verified",
                )
            )
            traceability.append(
                _trace_entry(
                    claim=f"{family}/{symbol} family verdict",
                    value=row["verdict"],
                    source_file="r3_family_rollup.json",
                    source_field=f"families.{family}.analysis.verdict",
                    classification="primary_result",
                    verification_level="reporter_verified",
                )
            )

        traceability.append(
            _trace_entry(
                claim=f"{family} GA-RS paired mean difference",
                value=paired.get("mean_difference"),
                source_file="r3_family_rollup.json",
                source_field=f"families.{family}.analysis.paired_ga_minus_rs.mean_difference",
                classification="secondary_diagnostic",
                verification_level="reporter_verified",
            )
        )
        traceability.append(
            _trace_entry(
                claim=f"{family} GA-RS 95% CI",
                value=[paired.get("ci_low"), paired.get("ci_high")],
                source_file="r3_family_rollup.json",
                source_field=f"families.{family}.analysis.paired_ga_minus_rs",
                classification="secondary_diagnostic",
                verification_level="reporter_verified",
            )
        )

    if discrepancies:
        raise R3ReportConsistencyError("; ".join(discrepancies))

    documentary_claims: dict[str, Any] = {
        "historical_holdout_status": {
            "value": "Frozen holdout not opened during Gate R3 (documented at closure)",
            "source_file": "docs/decisions/0015-r3-family-evaluation-negative.md",
            "source_field": "Decision item 4",
            "verification_level": "documentary",
            "note": "Reporter reads only allowlisted JSON under the R3 study root",
        },
        "r4_required_at_closure": {
            "value": verdict["r4_required"],
            "source_file": "r3_gate_verdict.json",
            "source_field": "r4_required",
            "verification_level": "reporter_verified",
        },
        "r4_application_status": {
            "value": "SKIPPED (zero R3 promotions at closure)",
            "source_file": "docs/decisions/0015-r3-family-evaluation-negative.md",
            "source_field": "Decision item 3",
            "verification_level": "documentary",
            "note": (
                "Promoted-only R4 confirmatory scope was harmonized in documentation after "
                "R3 closed; it was not part of the executed R3 contract"
            ),
        },
        "isolation_audit_at_closure": documentary_isolation,
    }

    provenance_limitation = _derive_provenance_limitation(provenance_rows, provenance_states)

    closure = {
        "gate_status": {
            "value": verdict["gate_status"],
            "verification_level": "reporter_verified",
            "source_file": "r3_gate_verdict.json",
            "source_field": "gate_status",
        },
        "n_promoted": {
            "value": verdict["n_promoted"],
            "verification_level": "reporter_verified",
            "source_file": "r3_gate_verdict.json",
            "source_field": "n_promoted",
        },
        "n_rejected": {
            "value": verdict["n_rejected"],
            "verification_level": "reporter_verified",
            "source_file": "r3_gate_verdict.json",
            "source_field": "n_rejected",
        },
        "units_completed": {
            "value": f"{units_completed}/{units_expected}",
            "verification_level": "reporter_verified",
            "source_file": "*/status.json + */checkpoint.json",
            "source_field": "status.completed vs checkpoint.meta symbols*seeds",
            "note": "Unit completion counts only; does not substitute for fold-isolation audit",
        },
        "numerical_discrepancies": {
            "value": 0,
            "verification_level": "reporter_verified",
            "source_file": "reporter consistency battery",
            "source_field": "n/a",
            "note": "Zero contradictions across execution, rollup, study_robustness and gate verdict",
        },
        "r4_required": {
            "value": verdict["r4_required"],
            "verification_level": "reporter_verified",
            "source_file": "r3_gate_verdict.json",
            "source_field": "r4_required",
        },
        "provenance_limitation": provenance_limitation,
    }

    traceability.extend(
        [
            _trace_entry(
                claim="Units completed",
                value=f"{units_completed}/{units_expected}",
                source_file="*/status.json",
                source_field="completed",
                classification="primary_result",
                verification_level="reporter_verified",
            ),
            _trace_entry(
                claim="Numerical discrepancies",
                value=0,
                source_file="reporter consistency battery",
                source_field="n/a",
                derivation="cross-check execution, rollup, study_robustness, gate_verdict",
                classification="primary_result",
                verification_level="reporter_verified",
            ),
            _trace_entry(
                claim="Gate R3 status",
                value=verdict["gate_status"],
                source_file="r3_gate_verdict.json",
                source_field="gate_status",
                classification="primary_result",
                verification_level="reporter_verified",
            ),
            _trace_entry(
                claim="Families promoted",
                value=str(verdict["n_promoted"]),
                source_file="r3_gate_verdict.json",
                source_field="n_promoted",
                classification="primary_result",
                verification_level="reporter_verified",
            ),
        ]
    )
    traceability.append(
        _trace_entry(
            claim="Isolation audit at R3 closure",
            value=documentary_isolation["value"],
            source_file=documentary_isolation["source_file"],
            source_field=documentary_isolation["source_field"],
            classification="secondary_diagnostic",
            verification_level="documentary",
        )
    )
    traceability.append(
        _trace_entry(
            claim="R4 required at closure",
            value=str(verdict["r4_required"]),
            source_file="r3_gate_verdict.json",
            source_field="r4_required",
            classification="primary_result",
            verification_level="reporter_verified",
        )
    )
    traceability.append(
        _trace_entry(
            claim="R4 application status",
            value=documentary_claims["r4_application_status"]["value"],
            source_file=documentary_claims["r4_application_status"]["source_file"],
            source_field=documentary_claims["r4_application_status"]["source_field"],
            classification="secondary_diagnostic",
            verification_level="documentary",
        )
    )
    traceability.append(
        _trace_entry(
            claim="Historical holdout status",
            value=documentary_claims["historical_holdout_status"]["value"],
            source_file=documentary_claims["historical_holdout_status"]["source_file"],
            source_field=documentary_claims["historical_holdout_status"]["source_field"],
            classification="limitation",
            verification_level="documentary",
        )
    )
    for state in provenance_states:
        traceability.append(
            _trace_entry(
                claim=f"Provenance state {state['state_id']}",
                value=state,
                source_file="*/run_identity.json",
                source_field="worktree.diff_sha256",
                classification="limitation",
                verification_level="limitation",
            )
        )

    source_timestamp = (
        verdict.get("closed_at") or rollup.get("generated_at") or execution.get("completed_at")
    )

    return {
        "schema_version": 2,
        "gate": "R3",
        "source_root": _stable_root_label(paths.root),
        "source_timestamp": source_timestamp,
        "source_files_read": artifact_reader.manifest(),
        "reporter_holdout_accessed": False,
        "primary_engine": R3_PRIMARY_ENGINE,
        "secondary_engine": SECONDARY_ENGINE,
        "majority_rule": f">={majority}/{n_seeds} seeds per asset on both assets",
        "closure_summary": closure,
        "documentary_claims": documentary_claims,
        "primary_table_rs": primary_rows,
        "rs_ga_comparison": rs_ga_rows,
        "traceability": traceability,
    }


def render_r3_thesis_markdown(report: dict[str, Any]) -> str:
    """Render a thesis-ready Markdown report from a build_r3_thesis_report payload."""
    lines = [
        "# Gate R3 — Thesis reporting extract",
        "",
        f"*Derived from persisted artifacts · source timestamp `{report['source_timestamp']}`*",
        "",
        "Random Search is the **confirmatory** promotion engine. Genetic Algorithm results are "
        "**secondary** and do not decide family promotion.",
        "",
        "## Closure summary",
        "",
    ]
    closure = report["closure_summary"]
    for key in (
        "gate_status",
        "n_promoted",
        "n_rejected",
        "units_completed",
        "numerical_discrepancies",
        "r4_required",
    ):
        block = closure[key]
        lines.append(
            f"- **{key}:** {block['value']} "
            f"(*{block['verification_level']}* · `{block['source_file']}` · `{block['source_field']}`)"
        )
    if "isolation_audit_at_closure" in report.get("documentary_claims", {}):
        audit = report["documentary_claims"]["isolation_audit_at_closure"]
        lines.append(
            f"- **isolation_audit_at_closure:** {audit['value']} "
            f"(*documentary* · `{audit['source_file']}` · `{audit['source_field']}`)"
        )
    lines.append(
        f"- **reporter_holdout_accessed:** {report['reporter_holdout_accessed']} "
        "(*reporter_verified* · read manifest under R3 root only)"
    )
    holdout_doc = report["documentary_claims"]["historical_holdout_status"]
    lines.append(
        f"- **historical_holdout_status:** {holdout_doc['value']} "
        f"(*documentary* · `{holdout_doc['source_file']}`)"
    )
    r4_required = report["documentary_claims"]["r4_required_at_closure"]
    lines.append(
        f"- **r4_required_at_closure:** {r4_required['value']} "
        f"(*{r4_required['verification_level']}* · `{r4_required['source_file']}`)"
    )
    r4_doc = report["documentary_claims"]["r4_application_status"]
    lines.append(
        f"- **r4_application_status:** {r4_doc['value']} (*{r4_doc['verification_level']}*)"
    )

    lines.extend(
        [
            "",
            "## Primary results — Random Search",
            "",
            "| Family | Asset | C1 | C2 | C3 | C4 | C5 | C6 | Min trades veto | Med OOS ret | "
            "Med OOS Sharpe | Med B&H | Verdict |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )

    for row in report["primary_table_rs"]:
        crit = row["criteria"]
        note = f" ({row['diagnostic_note']})" if row.get("diagnostic_note") else ""
        lines.append(
            f"| {row['family']} | {row['symbol']} "
            f"| {crit['positive_total_return']['display']} "
            f"| {crit['bootstrap_sharpe_ci_excludes_zero']['display']} "
            f"| {crit['survives_double_costs']['display']} "
            f"| {crit['beats_buy_and_hold']['display']} "
            f"| {crit['survives_drop_top_trades']['display']} "
            f"| {crit['not_confined_to_one_fold']['display']} "
            f"| {row['min_oos_trades_met']['display']} "
            f"| {_fmt_pct(row['median_oos_return'])} "
            f"| {_fmt_sharpe(row['median_oos_sharpe'])} "
            f"| {_fmt_pct(row['median_buy_and_hold_return'])} "
            f"| **{row['verdict']}**{note} |"
        )

    lines.extend(
        [
            "",
            "`min_oos_trades_met` is a **separate veto**, not a seventh promotion criterion.",
            "",
            "## Random Search vs Genetic Algorithm (secondary)",
            "",
            "| Family | GA - RS mean | 95% CI | Interpretation | GA decides promotion? |",
            "|---|---:|---|---|:---:|",
        ]
    )
    for row in report["rs_ga_comparison"]:
        ci = f"[{row['ci_low']:+.3f}, {row['ci_high']:+.3f}]"
        lines.append(
            f"| {row['family']} | {row['mean_difference_ga_minus_rs']:+.3f} | {ci} | "
            f"{row['interpretation']} | **No** |"
        )

    lines.extend(["", "## Traceability", ""])
    lines.append("| Claim | Value | Source file | Source field | Verification | Classification |")
    lines.append("|---|---|---|---|---|---|")
    for entry in report["traceability"]:
        value = entry["value"]
        if isinstance(value, (dict, list)):
            value_repr = json.dumps(value, sort_keys=True)
        else:
            value_repr = str(value)
        lines.append(
            f"| {entry['claim']} | {value_repr} | `{entry['source_file']}` | "
            f"`{entry['source_field']}` | {entry['verification_level']} | "
            f"{entry['classification']} |"
        )

    prov = closure["provenance_limitation"]
    commits = ", ".join(f"`{c}`" for c in prov.get("distinct_commits", []))
    lines.extend(
        [
            "",
            "## Provenance limitation",
            "",
            f"Executed code cannot be reconstructed exactly from commit(s) {commits} alone: "
            f"{prov.get('note', '')}",
            "",
            "| State | Families | Commit | diff_sha256 | diff_bytes | untracked_sha256 | dirty |",
            "|---|---|---|---|---|---|:---:|",
        ]
    )
    for state in prov["provenance_states"]:
        lines.append(
            f"| {state['state_id']} | {', '.join(state['families'])} | `{state['commit']}` | "
            f"`{state['diff_sha256']}` | {state['diff_bytes']} | `{state['untracked_sha256']}` | "
            f"{state['dirty']} |"
        )
    lines.append("")
    lines.append(
        "Dirty-worktree provenance limits exact code reconstruction; it is distinct from the "
        "numerical consistency checks performed by this reporter and from the persisted gate verdict."
    )
    return "\n".join(lines) + "\n"


def write_r3_thesis_report(root: Path, output_dir: Path) -> dict[str, Path]:
    """Build and write deterministic thesis report artifacts."""
    root = root.resolve()
    output_dir = _validate_output_dir(root, output_dir)
    report = build_r3_thesis_report(root)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "thesis_report.json"
    md_path = output_dir / "thesis_report.md"

    json_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    md_text = render_r3_thesis_markdown(report)

    json_path.write_text(json_text, encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")

    return {"json": json_path, "markdown": md_path}
