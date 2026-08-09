"""Artifact loading and data transformations for the Research Dashboard.

This module is deliberately **Streamlit-free** and side-effect-free so it can be
unit tested in isolation. It knows the on-disk layout produced by
:func:`perp_lab.search.runner.run_search` and turns raw JSON/Parquet artifacts
into small, plain Python / Polars structures for the UI.

Every loader tolerates missing or incomplete artifacts: absent files yield
``None`` or empty frames rather than raising, so a partially written or
interrupted run can still be browsed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import polars as pl

# Run-kind classification labels shown in the UI.
KIND_SYNTHETIC = "synthetic-smoke"
KIND_DEVELOPMENT = "development"
KIND_HOLDOUT = "final-holdout"
KIND_UNKNOWN = "unknown"

METHODS: tuple[str, ...] = ("random_search", "genetic_algorithm")

# The temporal contract current artifacts are produced under (ADR 0012). Runs
# recorded under any other protocol pooled fitness across outer folds and their
# selections are contaminated; they are still browsable, but clearly labelled.
CURRENT_SEARCH_PROTOCOL = "independent_search_per_outer_fold"
LEGACY_SEARCH_PROTOCOL = "pooled_across_folds_contaminated"


def search_protocol(summary: Mapping[str, Any] | None) -> str:
    """The protocol a run was produced under, inferred when not recorded."""
    if summary and isinstance(summary.get("search_protocol"), str):
        return str(summary["search_protocol"])
    return LEGACY_SEARCH_PROTOCOL


def _read_json(path: Path) -> Any | None:
    """Read a JSON artifact, returning ``None`` when it is missing or invalid."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _read_parquet(path: Path) -> pl.DataFrame:
    """Read a Parquet artifact, returning an empty frame when missing/invalid."""
    if not path.exists():
        return pl.DataFrame()
    try:
        return pl.read_parquet(path)
    except (OSError, pl.exceptions.PolarsError):
        return pl.DataFrame()


def classify_run_kind(summary: Mapping[str, Any] | None, config: Mapping[str, Any] | None) -> str:
    """Classify a run as synthetic smoke, development, or final holdout.

    Priority:
      1. An explicit ``synthetic`` flag in the search config.
      2. Keywords in the run label / kind (``holdout`` beats ``development``).
    """
    label = ""
    if summary:
        label = f"{summary.get('label', '')} {summary.get('run_kind', '')}".lower()
    if config and "label" in config:
        label = f"{label} {str(config.get('label', '')).lower()}"

    # Strip explicit negations so "..._not_holdout" is not read as a holdout run.
    cleaned = label.replace("not_holdout", "").replace("not-holdout", "").replace("not holdout", "")

    if config is not None and bool(config.get("synthetic", False)):
        return KIND_SYNTHETIC
    if "holdout" in cleaned:
        return KIND_HOLDOUT
    if "synthetic" in label or "smoke" in label:
        return KIND_SYNTHETIC
    if "development" in label or "dev" in label:
        return KIND_DEVELOPMENT
    if summary is not None or config is not None:
        # A real summary with no synthetic flag defaults to development data.
        return KIND_DEVELOPMENT
    return KIND_UNKNOWN


@dataclass(frozen=True)
class RunSummary:
    """Lightweight metadata for the run-browser list."""

    run_id: str
    path: Path
    kind: str
    label: str
    family: str
    algorithm: str
    symbol: str
    timeframe: str
    seed: int | None
    budget: int | None
    n_folds: int | None
    best_method: str | None
    has_comparison: bool
    protocol: str = LEGACY_SEARCH_PROTOCOL


def discover_runs(runs_dir: str | Path) -> list[RunSummary]:
    """Scan ``runs_dir`` for search runs, newest first.

    A directory qualifies if it contains ``comparison_summary.json`` or
    ``metrics.json``. Non-search runs (e.g. the ``dev_*`` pipeline) are skipped.
    """
    root = Path(runs_dir)
    out: list[RunSummary] = []
    if not root.exists():
        return out
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        summary = _read_json(d / "comparison_summary.json")
        if summary is None:
            metrics = _read_json(d / "metrics.json")
            summary = metrics.get("summary") if isinstance(metrics, dict) else None
        if not isinstance(summary, dict):
            continue
        config = _read_json(d / "search_config.json")
        cfg = config if isinstance(config, dict) else None
        out.append(
            RunSummary(
                run_id=d.name,
                path=d,
                kind=classify_run_kind(summary, cfg),
                label=str(summary.get("label", "")),
                family=str(summary.get("family", "")),
                algorithm=str(summary.get("algorithm", "")),
                symbol=str(summary.get("symbol", "")),
                timeframe=str(summary.get("timeframe", "")),
                seed=summary.get("seed"),
                budget=summary.get("budget"),
                n_folds=summary.get("n_folds"),
                best_method=summary.get("best_out_of_sample_method"),
                has_comparison=(d / "comparison_summary.json").exists(),
                protocol=search_protocol(summary),
            )
        )
    out.sort(key=lambda r: r.run_id, reverse=True)
    return out


@dataclass
class RunArtifacts:
    """Parsed artifacts for a single run directory (missing pieces are ``None``)."""

    run_dir: Path
    summary: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    objective: dict[str, Any] | None = None
    environment: dict[str, Any] | None = None
    dataset_manifests: dict[str, Any] | None = None
    feature_manifest: dict[str, Any] | None = None
    folds: dict[str, Any] | None = None
    warnings: dict[str, Any] | None = None
    algorithms: dict[str, Any] | None = None
    search_space: dict[str, Any] | None = None
    ga_diversity: dict[str, Any] | None = None
    ga_lineage: list[dict[str, Any]] = field(default_factory=list)
    report_md: str | None = None

    @property
    def kind(self) -> str:
        return classify_run_kind(self.summary, self.config)

    @property
    def protocol(self) -> str:
        return search_protocol(self.summary)

    @property
    def contaminated(self) -> bool:
        """True when this run's candidate selection saw other folds (pre-ADR-0012)."""
        return self.protocol != CURRENT_SEARCH_PROTOCOL

    @property
    def available_methods(self) -> list[str]:
        """Methods for which a candidate ledger exists on disk."""
        found: list[str] = []
        for m in METHODS:
            if (self.run_dir / f"{m}_candidates.parquet").exists():
                found.append(m)
        return found


def load_run(run_dir: str | Path) -> RunArtifacts:
    """Load all JSON/text artifacts for a run (frames are loaded on demand)."""
    d = Path(run_dir)
    lineage = _flatten_lineage(_read_json(d / "ga_lineage.json"))
    report_path = d / "comparison_report.md"
    return RunArtifacts(
        run_dir=d,
        summary=_read_json(d / "comparison_summary.json"),
        config=_read_json(d / "search_config.json"),
        objective=_read_json(d / "objective.json"),
        environment=_read_json(d / "environment.json"),
        dataset_manifests=_read_json(d / "dataset_manifests.json"),
        feature_manifest=_read_json(d / "feature_manifest.json"),
        folds=_read_json(d / "folds.json"),
        warnings=_read_json(d / "warnings.json"),
        algorithms=_read_json(d / "algorithms.json"),
        search_space=_read_json(d / "search_space.json"),
        ga_diversity=_read_json(d / "ga_diversity.json"),
        ga_lineage=lineage,
        report_md=report_path.read_text(encoding="utf-8") if report_path.exists() else None,
    )


def _flatten_lineage(raw: Any) -> list[dict[str, Any]]:
    """GA lineage as one list, tagging each edge with the fold that produced it."""
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if not isinstance(raw, dict):
        return []
    out: list[dict[str, Any]] = []
    for fold_key, rows in sorted(raw.items(), key=lambda kv: int(kv[0])):
        if not isinstance(rows, list):
            continue
        out.extend({**r, "fold": int(fold_key)} for r in rows if isinstance(r, dict))
    return out


def _method_summaries(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    if not summary:
        return {}
    methods = summary.get("methods")
    return methods if isinstance(methods, dict) else {}


def comparison_table(summary: Mapping[str, Any] | None) -> pl.DataFrame:
    """One row per method with headline validation and out-of-sample metrics."""
    rows: list[dict[str, Any]] = []
    for name, m in _method_summaries(summary).items():
        agg = m.get("aggregate_test", {}) if isinstance(m, dict) else {}
        counters = m.get("counters", {}) if isinstance(m, dict) else {}
        rows.append(
            {
                "method": name,
                "evaluated": counters.get("evaluated"),
                "feasible": m.get("n_feasible"),
                "best_val_fitness": m.get("best_fitness"),
                "mean_test_sharpe": agg.get("mean_test_sharpe"),
                "mean_test_total_return": agg.get("mean_test_total_return"),
                "mean_test_max_drawdown": agg.get("mean_test_max_drawdown"),
                "mean_test_ann_return": agg.get("mean_test_ann_return"),
                "mean_test_n_trades": agg.get("mean_test_n_trades"),
                "n_fold_winners": agg.get("n_fold_winners"),
            }
        )
    return pl.DataFrame(rows)


def fair_budget_report(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    """Verify that both methods spent the same budget inside every outer fold.

    Under the per-fold protocol the budget is a per-fold quantity, so the check
    that matters is whether each engine reached the target in *every* fold, not
    whether its run-level total happens to match. ``ok`` is True only when it did.
    """
    parity = summary.get("budget_parity", {}) if summary else {}
    if not isinstance(parity, dict):
        parity = {}
    budget = parity.get("effective_budget_per_fold", summary.get("budget") if summary else None)
    n_folds = parity.get("n_folds")
    per_engine = parity.get("per_engine", {})
    methods = _method_summaries(summary)

    rows: list[dict[str, Any]] = []
    ok = True
    for name, m in methods.items():
        counters = m.get("counters", {}) if isinstance(m, dict) else {}
        engine = per_engine.get(name, {}) if isinstance(per_engine, dict) else {}
        reached = engine.get("reached_target_in_every_fold")
        # Absent parity block: fall back to the run-level containment check so a
        # partially written or legacy run still renders instead of erroring.
        if reached is None:
            evaluated = counters.get("evaluated")
            reached = evaluated is not None and budget is not None and evaluated <= budget
        ok = ok and bool(reached)
        rows.append(
            {
                "method": name,
                "budget": budget,
                "n_folds_searched": engine.get("n_folds_searched", n_folds),
                "proposed": counters.get("proposed"),
                "invalid": counters.get("invalid"),
                "duplicate": counters.get("duplicate"),
                "cached": counters.get("cached"),
                "evaluated": counters.get("evaluated"),
                "unique_candidates": m.get("n_unique_candidates"),
                "within_budget": bool(reached),
            }
        )
    return {
        "budget": budget,
        "n_folds": n_folds,
        "parity_level": parity.get("parity_level"),
        "definition": summary.get("fair_budget") if summary else None,
        "rows": pl.DataFrame(rows),
        "ok": ok and len(rows) > 0,
    }


def convergence_frame(run_dir: str | Path, method: str, fold: int | None = None) -> pl.DataFrame:
    """Best-fitness-so-far versus evaluation index, per outer fold.

    Returns a ``fold`` / ``evaluation`` / ``best_fitness`` frame. Traces from
    different folds are separate series: they are measured on different validation
    windows, so concatenating them would not describe a single search.
    """
    data = _read_json(Path(run_dir) / f"{method}_convergence.json")
    if not isinstance(data, dict):
        return pl.DataFrame()

    per_fold = data.get("per_fold")
    if not isinstance(per_fold, dict):
        # Legacy single-trace artifact (pre-ADR-0012 protocol).
        series = data.get("best_fitness_after_each_eval")
        if not isinstance(series, list) or not series:
            return pl.DataFrame()
        per_fold = {"0": series}

    rows: list[dict[str, Any]] = []
    for key, series in sorted(per_fold.items(), key=lambda kv: int(kv[0])):
        if not isinstance(series, list) or not series:
            continue
        idx = int(key)
        if fold is not None and idx != fold:
            continue
        rows.extend(
            {"fold": idx, "evaluation": i, "best_fitness": v} for i, v in enumerate(series, start=1)
        )
    return pl.DataFrame(rows) if rows else pl.DataFrame()


def convergence_folds(run_dir: str | Path, method: str) -> list[int]:
    """Outer folds for which a convergence trace exists."""
    cf = convergence_frame(run_dir, method)
    if cf.is_empty() or "fold" not in cf.columns:
        return []
    return sorted({int(v) for v in cf["fold"].to_list()})


def _ga_per_fold(artifacts: RunArtifacts, key: str, legacy_key: str) -> pl.DataFrame:
    div = artifacts.ga_diversity
    if not isinstance(div, dict):
        return pl.DataFrame()
    per_fold = div.get(key)
    if not isinstance(per_fold, dict):
        rows = div.get(legacy_key)
        return pl.DataFrame(rows) if isinstance(rows, list) and rows else pl.DataFrame()
    frames: list[pl.DataFrame] = []
    for fold_key, rows in sorted(per_fold.items(), key=lambda kv: int(kv[0])):
        if not isinstance(rows, list) or not rows:
            continue
        frames.append(pl.DataFrame(rows).with_columns(pl.lit(int(fold_key)).alias("fold")))
    return pl.concat(frames, how="diagonal") if frames else pl.DataFrame()


def diversity_frame(artifacts: RunArtifacts) -> pl.DataFrame:
    """Per-generation GA diversity for every outer fold (empty when no GA ran)."""
    return _ga_per_fold(artifacts, "diversity_per_fold", "diversity")


def generation_best_frame(artifacts: RunArtifacts) -> pl.DataFrame:
    """Per-generation best fitness / candidate for the GA, per outer fold."""
    return _ga_per_fold(artifacts, "generation_best_per_fold", "generation_best")


def fold_winners_frame(run_dir: str | Path, method: str) -> pl.DataFrame:
    """Per-fold winner with flattened test metrics for one method."""
    data = _read_json(Path(run_dir) / f"{method}_fold_winners.json")
    if not isinstance(data, list) or not data:
        return pl.DataFrame()
    rows: list[dict[str, Any]] = []
    for w in data:
        if not isinstance(w, dict):
            continue
        tm = w.get("test_metrics", {}) if isinstance(w.get("test_metrics"), dict) else {}
        rows.append(
            {
                "fold": w.get("fold"),
                "winner": w.get("winner"),
                "val_sharpe": w.get("val_sharpe"),
                "test_sharpe": tm.get("sharpe"),
                "test_total_return": tm.get("total_return"),
                "test_max_drawdown": tm.get("max_drawdown"),
                "test_ann_return": tm.get("ann_return"),
                "test_n_trades": tm.get("n_trades"),
                "selection_fingerprint": w.get("selection_fingerprint"),
                "frozen_before_test": w.get("frozen_before_test"),
                "params": json.dumps(w.get("params", {}), sort_keys=True),
            }
        )
    return pl.DataFrame(rows)


def folds_frame(artifacts: RunArtifacts) -> pl.DataFrame:
    """Temporal partition table (train/val/test boundaries) for a run."""
    folds = artifacts.folds
    if not isinstance(folds, dict):
        return pl.DataFrame()
    rows = folds.get("folds")
    if not isinstance(rows, list) or not rows:
        return pl.DataFrame()
    flat: list[dict[str, Any]] = []
    for f in rows:
        if not isinstance(f, dict):
            continue
        flat.append(
            {
                "fold": f.get("index"),
                "train_start": f.get("train_start"),
                "train_end": f.get("train_end"),
                "val_start": f.get("val_start"),
                "val_end": f.get("val_end"),
                "test_start": f.get("test_start"),
                "test_end": f.get("test_end"),
                "purge_bars": f.get("purge_bars"),
                "embargo_bars": f.get("embargo_bars"),
            }
        )
    return pl.DataFrame(flat)


def candidates_frame(run_dir: str | Path, method: str) -> pl.DataFrame:
    """Full candidate ledger for one method (empty frame if absent)."""
    return _read_parquet(Path(run_dir) / f"{method}_candidates.parquet")


def candidate_ranking(run_dir: str | Path, method: str, top: int | None = None) -> pl.DataFrame:
    """Feasible candidates ranked by descending fitness."""
    df = candidates_frame(run_dir, method)
    if df.is_empty() or "fitness" not in df.columns:
        return df
    ranked = df.filter(pl.col("fitness").is_not_null()).sort("fitness", descending=True)
    if top is not None:
        ranked = ranked.head(top)
    return ranked


def failed_candidates_frame(run_dir: str | Path, method: str) -> pl.DataFrame:
    """Ledger of candidates that were rejected or failed evaluation."""
    data = _read_json(Path(run_dir) / f"{method}_failed_candidates.json")
    if not isinstance(data, list) or not data:
        return pl.DataFrame()
    return pl.DataFrame(data)


def equity_frame(run_dir: str | Path, method: str, fold: int) -> pl.DataFrame:
    """Test equity / drawdown ledger for a method's winner on one fold."""
    return _read_parquet(Path(run_dir) / f"{method}_fold{fold}_test_equity.parquet")


def trades_frame(run_dir: str | Path, method: str, fold: int) -> pl.DataFrame:
    """Test trade table for a method's winner on one fold."""
    return _read_parquet(Path(run_dir) / f"{method}_fold{fold}_test_trades.parquet")


def dataset_manifest_frame(artifacts: RunArtifacts) -> pl.DataFrame:
    """Dataset identifiers and row counts as a table."""
    dm = artifacts.dataset_manifests
    if not isinstance(dm, dict) or not dm:
        return pl.DataFrame()
    rows = [
        {
            "dataset_id": k,
            "sha256": v.get("sha256") if isinstance(v, dict) else None,
            "row_count": v.get("row_count") if isinstance(v, dict) else None,
        }
        for k, v in dm.items()
    ]
    return pl.DataFrame(rows)


def warning_messages(artifacts: RunArtifacts) -> Sequence[str]:
    """All recorded warning strings for a run."""
    w = artifacts.warnings
    if not isinstance(w, dict):
        return []
    return [str(v) for v in w.values()]
