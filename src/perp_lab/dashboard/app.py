"""Streamlit Research Dashboard (v0) for perp-lab search runs.

Read-only viewer over artifacts written by ``perp_lab.search``. It never runs a
backtest or a search; all logic lives in :mod:`perp_lab.dashboard.loader`.

Launch with the project CLI (binds port 8501)::

    uv run perp-lab dashboard

or directly::

    uv run streamlit run src/perp_lab/dashboard/app.py --server.port 8501
"""

from __future__ import annotations

import os
from pathlib import Path

import polars as pl
import streamlit as st

from perp_lab.dashboard import loader

KIND_BADGE = {
    loader.KIND_SYNTHETIC: (":orange[SYNTHETIC SMOKE]", "orange"),
    loader.KIND_DEVELOPMENT: (":blue[DEVELOPMENT DATA]", "blue"),
    loader.KIND_HOLDOUT: (":red[FINAL HOLDOUT]", "red"),
    loader.KIND_UNKNOWN: (":gray[UNKNOWN]", "gray"),
}


def _runs_dir() -> Path:
    return Path(os.environ.get("PERP_LAB_RUNS_DIR", "artifacts/runs"))


def _show_frame(df: pl.DataFrame, *, empty_msg: str = "No data available.") -> None:
    if df.is_empty():
        st.info(empty_msg)
        return
    st.dataframe(df.to_pandas(), use_container_width=True, hide_index=True)


def _sidebar(runs: list[loader.RunSummary]) -> loader.RunSummary | None:
    st.sidebar.title("perp-lab research")
    st.sidebar.caption("Read-only viewer of search run artifacts.")

    if not runs:
        st.sidebar.error("No search runs found.")
        return None

    kinds = sorted({r.kind for r in runs})
    kind_filter = st.sidebar.multiselect("Run kind", kinds, default=kinds)
    families = sorted({r.family for r in runs if r.family})
    family_filter = st.sidebar.multiselect("Strategy family", families, default=families)

    filtered = [
        r for r in runs if r.kind in kind_filter and (not families or r.family in family_filter)
    ]
    if not filtered:
        st.sidebar.warning("No runs match the current filters.")
        return None

    labels = {f"{r.run_id}  ({r.kind})": r for r in filtered}
    choice = st.sidebar.selectbox("Run", list(labels.keys()))
    return labels[choice]


def _header(run: loader.RunSummary, art: loader.RunArtifacts) -> None:
    badge, _ = KIND_BADGE.get(run.kind, KIND_BADGE[loader.KIND_UNKNOWN])
    st.title("Research Dashboard v0")
    st.markdown(f"**Run:** `{run.run_id}` — {badge}")

    if run.kind != loader.KIND_HOLDOUT:
        st.warning(
            "EXPLORATORY: these are development walk-forward validation/test metrics, "
            "**not** final holdout performance. Do not report them as the thesis's "
            "out-of-sample result."
        )
    for msg in loader.warning_messages(art):
        st.caption(f":warning: {msg}")


def _method_filter(art: loader.RunArtifacts) -> list[str]:
    methods = art.available_methods or list(loader.METHODS)
    return st.multiselect("Algorithm", methods, default=methods, key="algo_filter")


def _tab_overview(run: loader.RunSummary, art: loader.RunArtifacts) -> None:
    s = art.summary or {}
    cols = st.columns(4)
    cols[0].metric("Family", run.family or "-")
    cols[1].metric("Symbol / TF", f"{run.symbol} {run.timeframe}")
    cols[2].metric("Folds", run.n_folds if run.n_folds is not None else "-")
    cols[3].metric("Budget", run.budget if run.budget is not None else "-")

    cols = st.columns(3)
    cols[0].metric("Seed", run.seed if run.seed is not None else "-")
    cols[1].metric("Space version", s.get("space_version", "-"))
    cols[2].metric("Best OOS method", s.get("best_out_of_sample_method", "-"))

    st.subheader("Random Search vs Genetic Algorithm")
    _show_frame(loader.comparison_table(art.summary))
    st.caption(f"Comparison metric: {s.get('comparison_metric', 'n/a')}")

    st.subheader("Fair-budget verification")
    fb = loader.fair_budget_report(art.summary)
    if fb["ok"]:
        st.success("Fair budget respected: every method stayed within the shared budget.")
    else:
        st.error("Fair-budget check FAILED or incomplete — inspect the counters below.")
    st.caption(str(fb.get("definition")))
    _show_frame(fb["rows"])

    if art.report_md:
        with st.expander("Human-readable comparison report"):
            st.markdown(art.report_md)


def _tab_config(art: loader.RunArtifacts) -> None:
    st.subheader("Resolved search configuration")
    st.json(art.config or {})
    st.subheader("Objective definition and constraints")
    st.json(art.objective or {})
    st.subheader("Search space")
    st.json(art.search_space or {})
    st.subheader("Environment")
    st.json(art.environment or {})


def _tab_data(art: loader.RunArtifacts) -> None:
    st.subheader("Dataset manifests")
    _show_frame(loader.dataset_manifest_frame(art), empty_msg="No dataset manifest recorded.")
    st.subheader("Feature manifest")
    fm = art.feature_manifest or {}
    if fm:
        cols = st.columns(3)
        cols[0].metric("Symbol", fm.get("symbol", "-"))
        cols[1].metric("Timeframe", fm.get("timeframe", "-"))
        cols[2].metric("# Features", fm.get("n_features", "-"))
    st.json(fm)
    st.subheader("Temporal partitions (walk-forward folds)")
    _show_frame(loader.folds_frame(art), empty_msg="No folds recorded.")


def _tab_convergence(art: loader.RunArtifacts, methods: list[str]) -> None:
    st.subheader("Convergence (best fitness after each evaluation)")
    st.caption(
        "Search runs independently inside each outer fold, so every fold has its own "
        "trace. Fitness is measured on that fold's validation window and is not "
        "comparable across folds."
    )
    available = sorted({f for m in methods for f in loader.convergence_folds(art.run_dir, m)})
    if not available:
        st.info("No convergence history available.")
    else:
        fold = st.selectbox("Outer fold", available, key="convergence_fold")
        frames = []
        for m in methods:
            cf = loader.convergence_frame(art.run_dir, m, fold=fold)
            if not cf.is_empty():
                frames.append(cf.with_columns(pl.lit(m).alias("method")))
        if frames:
            combined = pl.concat(frames)
            chart = combined.pivot(values="best_fitness", index="evaluation", on="method")
            st.line_chart(chart.to_pandas(), x="evaluation")

    st.subheader("Genetic Algorithm diversity")
    div = loader.diversity_frame(art)
    if div.is_empty():
        st.info("No GA diversity recorded (run had no genetic algorithm).")
    else:
        if "fold" in div.columns:
            div = div.filter(pl.col("fold") == div["fold"].min())
        st.line_chart(div.to_pandas(), x="generation")
        _show_frame(loader.generation_best_frame(art))
        if art.ga_lineage:
            with st.expander("GA lineage (parent/offspring)"):
                _show_frame(pl.DataFrame(art.ga_lineage))


def _tab_candidates(art: loader.RunArtifacts, methods: list[str]) -> None:
    for m in methods:
        st.subheader(f"Candidate ranking — {m}")
        ranked = loader.candidate_ranking(art.run_dir, m, top=50)
        _show_frame(ranked, empty_msg=f"No candidate ledger for {m}.")
        failed = loader.failed_candidates_frame(art.run_dir, m)
        if not failed.is_empty():
            with st.expander(f"Failed / rejected candidates — {m}"):
                _show_frame(failed)


def _tab_folds(art: loader.RunArtifacts, methods: list[str]) -> None:
    fold_options = []
    folds = loader.folds_frame(art)
    if not folds.is_empty():
        fold_options = folds["fold"].to_list()

    for m in methods:
        st.subheader(f"Fold winners — {m}")
        _show_frame(
            loader.fold_winners_frame(art.run_dir, m),
            empty_msg=f"No fold winners for {m}.",
        )

    if not fold_options:
        return

    st.subheader("Test equity & drawdown by fold")
    method = st.selectbox("Method", methods, key="equity_method")
    fold = st.selectbox("Fold", fold_options, key="equity_fold")
    if method is None or fold is None:
        return
    fold_idx = int(fold)
    eq = loader.equity_frame(art.run_dir, str(method), fold_idx)
    if eq.is_empty():
        st.info("No test equity available for this selection.")
        return
    if "open_time" in eq.columns and "equity" in eq.columns:
        st.line_chart(eq.select(["open_time", "equity"]).to_pandas(), x="open_time")
    if "open_time" in eq.columns and "drawdown" in eq.columns:
        st.area_chart(eq.select(["open_time", "drawdown"]).to_pandas(), x="open_time")

    st.subheader("Trades")
    _show_frame(
        loader.trades_frame(art.run_dir, str(method), fold_idx),
        empty_msg="No trades recorded for this selection.",
    )


def main() -> None:
    st.set_page_config(page_title="perp-lab Research Dashboard", layout="wide")
    runs = loader.discover_runs(_runs_dir())
    run = _sidebar(runs)
    if run is None:
        st.title("Research Dashboard v0")
        st.info(
            f"No search runs found under `{_runs_dir()}`. "
            "Run `uv run perp-lab search --config configs/search_pilot.yaml` first."
        )
        return

    art = loader.load_run(run.path)
    _header(run, art)
    methods = _method_filter(art)

    tabs = st.tabs(
        [
            "Overview",
            "Configuration",
            "Data & Features",
            "Convergence & Diversity",
            "Candidates",
            "Folds & Test",
        ]
    )
    with tabs[0]:
        _tab_overview(run, art)
    with tabs[1]:
        _tab_config(art)
    with tabs[2]:
        _tab_data(art)
    with tabs[3]:
        _tab_convergence(art, methods)
    with tabs[4]:
        _tab_candidates(art, methods)
    with tabs[5]:
        _tab_folds(art, methods)


if __name__ == "__main__":
    main()
