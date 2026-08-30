"""Build the chapters 9-11 writing package (tables + figures + canonical facts).

Run with: ``uv run python scripts/build_ch9_11_package.py``

Reads only already-closed artifacts and repository documents. Runs no
experiment, no simulation and no search; never opens the reserved partition
[2026-01-01, 2026-07-01). Deterministic: no timestamps, no RNG,
SOURCE_DATE_EPOCH pinned for the PDF twins.

Outputs under docs/thesis/ch9_11_package/{tables,figures,data}/.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

os.environ.setdefault("SOURCE_DATE_EPOCH", "946684800")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import polars as pl
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from perp_lab.reporting import apply_house_style

apply_house_style()

PKG = Path("docs/thesis/ch9_11_package")
for sub in ("tables", "figures", "data", "captions"):
    (PKG / sub).mkdir(parents=True, exist_ok=True)


def save_fig(fig, name: str) -> None:
    fig.savefig(PKG / "figures" / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(PKG / "figures" / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"figure {name}")


def write_csv(df: pl.DataFrame, name: str) -> None:
    df.write_csv(PKG / "tables" / name)
    print(f"table {name} ({df.height} rows)")


# --------------------------------------------------------------------------- #
# data/: canonical facts every chapter must quote identically
# --------------------------------------------------------------------------- #
FACTS = pl.DataFrame(
    [
        # (key, value, unit, evidence_path, kind)
        (
            "closure_families",
            "13",
            "families",
            "reports/study_closure/study_dashboard.json",
            "executed",
        ),
        (
            "closure_units",
            "284",
            "family x asset x seed x engine",
            "reports/study_closure/study_dashboard.json",
            "executed",
        ),
        (
            "closure_evaluations",
            "496500",
            "unique configurations",
            "reports/thesis/chapter_06/INVENTARIO_MAESTRO.md",
            "executed",
        ),
        (
            "crt_evaluations_valid",
            "540000",
            "unique configurations",
            "reports/thesis/chapter_06/INVENTARIO_MAESTRO.md",
            "executed",
        ),
        (
            "s3_evaluations_study",
            "60000",
            "unique configurations",
            "reports/thesis/chapter_06/INVENTARIO_MAESTRO.md",
            "executed",
        ),
        (
            "s3_pilot_evaluations",
            "750",
            "unique configurations",
            "reports/thesis/chapter_06/INVENTARIO_MAESTRO.csv",
            "executed",
        ),
        (
            "confirmatory_total_excl_s3_pilot",
            "1096500",
            "unique configurations",
            "reports/thesis/chapter_07/MANIFEST.md",
            "executed",
        ),
        (
            "confirmatory_total_incl_s3_pilot",
            "1097250",
            "unique configurations",
            "reports/thesis/chapter_07/MANIFEST.md",
            "executed",
        ),
        (
            "discarded_crt_evaluations",
            "93000",
            "unique configurations",
            "reports/thesis/chapter_06/INVENTARIO_MAESTRO.md",
            "executed",
        ),
        (
            "full_study_families",
            "16",
            "families",
            "reports/thesis/chapter_07/ch7_results_units.csv",
            "executed",
        ),
        (
            "full_study_units",
            "640",
            "family x asset x engine x seed",
            "reports/thesis/chapter_07/ch7_results_units.csv",
            "executed",
        ),
        ("promotions", "0", "strategies", "reports/study_closure/study_dashboard.json", "executed"),
        (
            "smallest_raw_p",
            "0.3455",
            "p-value",
            "reports/study_closure/study_level_multiple_testing.json",
            "executed",
        ),
        (
            "holm_rejections",
            "0",
            "families",
            "reports/study_closure/study_level_multiple_testing.json",
            "executed",
        ),
        (
            "bh_rejections",
            "0",
            "families",
            "reports/study_closure/study_level_multiple_testing.json",
            "executed",
        ),
        (
            "dsr_n13",
            "0.139",
            "deflated Sharpe",
            "reports/study_closure/study_level_multiple_testing.json",
            "executed",
        ),
        (
            "dsr_n496500",
            "0.00012",
            "deflated Sharpe",
            "reports/study_closure/study_level_multiple_testing.json",
            "executed",
        ),
        (
            "pbo_cscv",
            "0.4857",
            "probability",
            "reports/study_closure/study_level_multiple_testing.json",
            "executed",
        ),
        (
            "white_rc_p_s1b",
            "0.9955",
            "p-value",
            "reports/gate_s1b/s1b_pilot_report.json",
            "executed",
        ),
        (
            "hansen_spa_p_s1b",
            "1.0",
            "p-value",
            "reports/gate_s1b/s1b_pilot_report.json",
            "executed",
        ),
        (
            "regime_cells_tested",
            "65",
            "family x regime cells",
            "reports/study_closure/regime_conditioned.json",
            "executed",
        ),
        (
            "regime_survivors",
            "0",
            "cells",
            "reports/study_closure/regime_conditioned.json",
            "executed",
        ),
        (
            "oos_bars",
            "32385",
            "hourly bars",
            "reports/thesis/chapter_07/ch7_results_units.csv",
            "executed",
        ),
        (
            "oos_window",
            "2022-03-31..2025-12-09",
            "date range",
            "reports/thesis/chapter_07/ch7_results_units.csv",
            "executed",
        ),
        (
            "dev_window",
            "2020-01-01..2025-12-31",
            "date range",
            "configs/data_contract.yaml",
            "executed",
        ),
        (
            "bh_btc_funded",
            "0.522748",
            "total return",
            "reports/thesis/chapter_07/ch7_results_units.csv",
            "executed",
        ),
        (
            "pdl_btc_seeds_positive",
            "10/10",
            "seeds",
            "reports/thesis/chapter_07/ch7_criteria.csv",
            "executed",
        ),
        (
            "pdl_btc_bootstrap_ci_gt0",
            "0/10",
            "seeds",
            "reports/thesis/chapter_07/ch7_criteria.csv",
            "executed",
        ),
        (
            "pdl_btc_drop_top5_survivors",
            "2/10",
            "seeds",
            "reports/thesis/chapter_07/ch7_criteria.csv",
            "executed",
        ),
        (
            "volb_btc_seeds_positive",
            "6/10",
            "seeds",
            "reports/thesis/chapter_07/ch7_criteria.csv",
            "executed",
        ),
        (
            "volb_btc_drop_top5_survivors",
            "0/10",
            "seeds",
            "reports/thesis/chapter_07/ch7_criteria.csv",
            "executed",
        ),
        (
            "ch8_pdl_terminal_p50",
            "1.142",
            "equity multiple",
            "reports/thesis/chapter_08/ch8_simulation_summary.csv",
            "conditional_simulation",
        ),
        (
            "ch8_pdl_prob_below_1",
            "0.204",
            "probability (MC SE 0.006)",
            "reports/thesis/chapter_08/ch8_simulation_summary.csv",
            "conditional_simulation",
        ),
        (
            "ch8_pdl_mdd_p95",
            "0.221",
            "drawdown magnitude",
            "reports/thesis/chapter_08/ch8_drawdown_summary.csv",
            "conditional_simulation",
        ),
        (
            "ch8_volb_terminal_p50",
            "0.962",
            "equity multiple",
            "reports/thesis/chapter_08/ch8_simulation_summary.csv",
            "conditional_simulation",
        ),
        (
            "ch8_volb_prob_below_1",
            "0.519",
            "probability (MC SE 0.008)",
            "reports/thesis/chapter_08/ch8_simulation_summary.csv",
            "conditional_simulation",
        ),
        (
            "ch8_volb_mdd_p95",
            "0.798",
            "drawdown magnitude",
            "reports/thesis/chapter_08/ch8_drawdown_summary.csv",
            "conditional_simulation",
        ),
        (
            "ch8_volb_prob_mdd_gt50",
            "0.480",
            "probability",
            "reports/thesis/chapter_08/ch8_drawdown_summary.csv",
            "conditional_simulation",
        ),
        (
            "metalabel_real_primary",
            "crt_htf_range_reversal BTCUSDT 1h",
            "family",
            "reports/meta_labeling_real/meta_labeling_real.md",
            "descriptive_exploratory",
        ),
        (
            "metalabel_real_auc",
            "0.548",
            "ROC-AUC median",
            "reports/meta_labeling_real/meta_labeling_real.md",
            "descriptive_exploratory",
        ),
        (
            "metalabel_real_folds_improved",
            "4/4",
            "folds",
            "reports/meta_labeling_real/meta_labeling_real.md",
            "descriptive_exploratory",
        ),
        (
            "metalabel_real_abstention",
            "0.50",
            "rate",
            "reports/meta_labeling_real/meta_labeling_real.md",
            "descriptive_exploratory",
        ),
        (
            "volforecast_dm_p_btc",
            "0.091",
            "p-value",
            "artifacts/volforecast/results.json",
            "descriptive_exploratory",
        ),
        (
            "volforecast_dm_p_eth",
            "0.647",
            "p-value",
            "artifacts/volforecast/results.json",
            "descriptive_exploratory",
        ),
        (
            "altdata_event_vol_multiplier",
            "2.5-3.2",
            "x baseline hour",
            "docs/thesis/anexo_altdata.md",
            "descriptive",
        ),
        (
            "holdout_window",
            "2026-01-01..2026-07-01",
            "date range",
            "docs/methodology/holdout_audit_status.md",
            "consumed",
        ),
        (
            "holdout_opened_at",
            "2026-08-13T11:13:37Z",
            "timestamp",
            "docs/methodology/holdout_audit_status.md",
            "consumed",
        ),
        (
            "holdout_state",
            "HOLDOUT_LOCKED",
            "status",
            "docs/methodology/holdout_audit_status.md",
            "consumed",
        ),
        (
            "holdout_audit_req1",
            "NOT MET (verified)",
            "audit requirement",
            "docs/methodology/holdout_audit_status.md",
            "consumed",
        ),
        ("pytest_tests", "1579", "tests", "uv run pytest", "verified_2026-08-29"),
        ("vitest_tests", "112", "tests", "npm test (apps/web)", "verified_2026-08-29"),
        ("e2e_tests", "22", "tests", "npx playwright test (apps/web)", "verified_2026-08-29"),
        ("test_files_python", "121", "files", "tests/**/test_*.py", "verified_2026-08-29"),
        ("assets", "BTCUSDT, ETHUSDT", "symbols", "configs/data_contract.yaml", "executed"),
        (
            "exchange",
            "Binance USDT-M (linear perpetuals)",
            "venue",
            "configs/data_contract.yaml",
            "executed",
        ),
        (
            "timeframe",
            "1h primary (15m/5m ancillary)",
            "bar size",
            "configs/data_contract.yaml",
            "executed",
        ),
        (
            "costs",
            "4 bps fee + 1 bps slippage per side + realized funding",
            "cost model",
            "configs/experiment.yaml",
            "executed",
        ),
    ],
    schema=["key", "value", "unit", "evidence_path", "kind"],
    orient="row",
)
FACTS.write_csv(PKG / "data" / "canonical_facts.csv")
print(f"data canonical_facts.csv ({FACTS.height} rows)")


# --------------------------------------------------------------------------- #
# Chapter 9 tables
# --------------------------------------------------------------------------- #
T91 = pl.DataFrame(
    [
        (
            "Executed external validation (new market/venue/period)",
            "NONE",
            "No dataset outside Binance USDT-M BTCUSDT/ETHUSDT exists in the repository (data/manifests/ lists only binance_um_* plus alt-data streams)",
            "data/manifests/, configs/data_contract.yaml",
            "May not be claimed in any form",
        ),
        (
            "Reserved partition [2026-01-01, 2026-07-01)",
            "CONSUMED, reading withheld",
            "Opened once 2026-08-13T11:13:37Z on volatility_breakout BTC, a family already rejected by the study-level correction; state HOLDOUT_LOCKED; audit requirement 1 verified NOT MET",
            "docs/methodology/holdout_audit_status.md, reports/study_closure/final_holdout.json",
            "Cannot serve as external validation; must never be described as untouched",
        ),
        (
            "Walk-forward OOS test slices (development)",
            "EXECUTED, internal",
            "15 expanding folds, purge 96 / embargo 118 bars, 32,385 OOS bars per unit",
            "reports/thesis/chapter_07/ch7_results_units.csv",
            "Internal out-of-sample only; not external validation",
        ),
        (
            "Regime-conditioned re-evaluation",
            "EXECUTED, exploratory",
            "65 family x regime cells (volatility terciles and trend direction), 0 survivors after Holm/BH",
            "reports/study_closure/regime_conditioned.json",
            "Exploratory hypothesis generation; not validation",
        ),
        (
            "Conditional risk simulation (chapter 8)",
            "EXECUTED, conditional",
            "Bootstrap resampling of the SAME observed development record",
            "reports/thesis/chapter_08/",
            "Diagnostic conditional on the observed record; not new evidence",
        ),
        (
            "Paper trading / forward test",
            "NONE",
            "No paper-trading module, log, broker adapter or forward-test artifact exists",
            "repository search: no paper_trading/live modules",
            "May not be claimed",
        ),
        (
            "Other exchange (Bybit, OKX, ...)",
            "NONE",
            "No ingestion path, contract or manifest for any other venue",
            "configs/data_contract.yaml (exchange: binance)",
            "May not be claimed",
        ),
        (
            "Other market (index futures, equities, FX)",
            "NONE",
            "No dataset, cost model or session calendar for any non-crypto market",
            "configs/",
            "May not be claimed",
        ),
        (
            "Auxiliary annexes (meta-labeling, HAR/LSTM, alt-data)",
            "EXECUTED, auxiliary",
            "Run on the same development history under exploratory contracts",
            "reports/meta_labeling_real/, artifacts/volforecast/, docs/thesis/anexo_altdata.md",
            "Auxiliary analyses on the same data; explicitly NOT external validation",
        ),
    ],
    schema=["evidence_item", "status", "what_exists", "evidence_path", "admissible_interpretation"],
    orient="row",
)
write_csv(T91, "table_9_1_external_validation_status.csv")

T92 = pl.DataFrame(
    [
        (
            "Instrument",
            "Perpetual swap, no expiry",
            "Index/commodity future with quarterly expiry",
            "Roll logic and continuous-series construction absent from the pipeline",
            "Add roll calendar and back-adjustment; redefine the return series",
            "Silent look-ahead or phantom gaps at each roll",
        ),
        (
            "Funding / carry",
            "8-hourly funding, charged as-of-past (mean 1.2-1.4 bps, 87-88% positive)",
            "No funding; carry via basis and financing rate",
            "backtesting/engine.py charges a funding column that would not exist",
            "Replace the funding term with a financing/basis model or set it to zero explicitly",
            "Costs mis-stated in both directions; the funded benchmark loses meaning",
        ),
        (
            "Trading calendar",
            "24/7, no sessions or gaps",
            "Exchange sessions, holidays, overnight gaps, auctions",
            "Bar indexing, 8760 bars/year annualisation, purge/embargo in bars, CRT session windows",
            "Session-aware calendar, gap handling, recomputed annualisation and embargo",
            "Annualisation and drawdown durations inflated; session families meaningless",
        ),
        (
            "Microstructure",
            "Deep crypto CLOB, taker fee 4 bps, slippage 1 bps assumed",
            "Different tick size, fee schedule, liquidity profile",
            "Cost model is a constant per side (ADR 0005, provisional)",
            "Re-estimate fees/slippage per venue; re-run the 2x cost stress",
            "Results not comparable; cost-sensitivity conclusions do not transfer",
        ),
        (
            "Data provenance",
            "Binance Vision bulk archive, SHA-256 manifests, QC vs native klines",
            "Vendor feeds with different adjustment and revision policies",
            "ingestion/ and the data contract assume the Binance schema",
            "New contract, manifest and QC suite per source",
            "Unverifiable inputs break the reproducibility chain",
        ),
        (
            "Volatility regime",
            "Crypto-scale volatility; heavy tails (F2/F3), clustering (F4)",
            "Lower unconditional volatility, different tail behaviour",
            "ATR-scaled thresholds, regime terciles, block lengths chosen from this ACF",
            "Recalibrate regime cuts and bootstrap block lengths on the new series",
            "Thresholds tuned to crypto volatility silently mis-scale",
        ),
        (
            "Cross-asset structure",
            "BTC-ETH Pearson 0.839, peak lead-lag at lag 0",
            "Different correlation and lead-lag structure",
            "BTC_ETH_confirmation and xasset families are asset-pair specific",
            "Re-measure dependence before reusing the cross-asset families",
            "Family motivation evaporates; results uninterpretable",
        ),
        (
            "Execution model",
            "Next-bar-open fill, fixed fraction 1.0, no queue position",
            "Same simplification, but different fill realism per venue",
            "backtesting/engine.py has no order book, queue or partial fills",
            "Order-book-aware execution or explicit declaration of the same limitation",
            "Optimistic fills; unmodelled impact at larger size",
        ),
        (
            "Regulatory / access",
            "Retail-accessible perpetuals, high leverage available",
            "Margin rules, exchange membership, contract size",
            "Exposure multipliers of chapter 8 assume frictionless scaling",
            "Constrain the multiplier grid to feasible margin",
            "Scenarios not attainable in practice",
        ),
    ],
    schema=[
        "dimension",
        "binance_perpetuals",
        "alternative_market",
        "pipeline_impact",
        "required_adaptation",
        "threat_if_ignored",
    ],
    orient="row",
)
write_csv(T92, "table_9_2_transferability_matrix.csv")


# --------------------------------------------------------------------------- #
# Chapter 10 tables
# --------------------------------------------------------------------------- #
T101 = pl.DataFrame(
    [
        (
            "Two assets only (BTCUSDT, ETHUSDT)",
            "Every family-level conclusion",
            "No claim about other underlyings; the two assets correlate 0.839, so they are not two independent bets",
            "configs/data_contract.yaml; scientific_questions.md F8",
        ),
        (
            "Single exchange (Binance USDT-M)",
            "Cost model, funding, microstructure conclusions",
            "Venue-specific fee/funding structure; results may not transfer",
            "configs/data_contract.yaml",
        ),
        (
            "Development window 2020-2025, OOS 2022-03-31..2025-12-09",
            "All performance evidence",
            "One market history; regime coverage is what those years happened to contain",
            "reports/thesis/chapter_07/ch7_results_units.csv",
        ),
        (
            "OHLCV + funding only, no order book",
            "Microstructure families (S2), execution realism",
            "Taker imbalance is a proxy, never true order flow; explicitly named as such",
            "docs/roadmap/gate_s2_batch_01.md",
        ),
        (
            "No queue position, partial fills or market impact",
            "All net-return figures",
            "Fills assumed at next-bar open at any size; optimistic at scale",
            "src/perp_lab/backtesting/engine.py",
        ),
        (
            "Constant slippage model (1 bps/side, provisional)",
            "Cost-sensitivity conclusions",
            "2x cost stress included as a criterion, but does not exhaust real microstructure",
            "ADR 0005; ch7_criteria.csv",
        ),
        (
            "Next-bar-open execution",
            "Timing of every signal",
            "Conservative and causal, but coarse relative to intrabar reality",
            "src/perp_lab/backtesting/engine.py",
        ),
        (
            "Finite search budgets (25-300 per fold per engine)",
            "Any 'the space was explored' claim",
            "Budgets bounded by space cardinality (ADR 0014); a larger budget could find different winners",
            "reports/thesis/chapter_07/ch7_results_units.csv",
        ),
        (
            "Pilots run with 1 or 3 seeds (S1-B, S2-B)",
            "The 13-family closure's homogeneity",
            "Six of the thirteen closure families carry pilot-level evidence only; not equally powered",
            "reports/thesis/chapter_06/INVENTARIO_MAESTRO.md",
        ),
        (
            "Configurations are dependent, not independent trials",
            "Multiple-testing counts",
            "Bonferroni-style counts over 496,500 configurations are conservative bounds, not exact N",
            "reports/study_closure/study_level_multiple_testing.json",
        ),
        (
            "All seeds share one market history",
            "Seed dispersion readings",
            "Ten seeds are ten searches over the same bars; dispersion is search noise, never a confidence interval",
            "reports/thesis/chapter_07/ch7_seed_dispersion.md",
        ),
        (
            "Reserved partition consumed (opened 2026-08-13)",
            "Any confirmatory claim",
            "No clean final test remains on this history; new data required",
            "docs/methodology/holdout_audit_status.md",
        ),
        (
            "No study-level correction for CRT and S3",
            "Cross-round statements",
            "Holm/BH/DSR/PBO computed for the 13-family universe only; CRT/S3 carry per-cell verdicts only",
            "reports/thesis/chapter_06/MANIFEST.md",
        ),
        (
            "Chapter 8 simulations are conditional",
            "Risk statements",
            "Bootstrap of the observed record; not validation, not a forecast",
            "reports/thesis/chapter_08/ch8_method_contract.md",
        ),
        (
            "Risk engine implemented but inactive",
            "Any risk-management claim",
            "CRT risk module, position sizing and daily limits exist in code but were NOT active in any executed round",
            "reports/thesis/chapter_07/ch7_hypotheses_rules.md",
        ),
        (
            "No live or paper trading",
            "Operational claims",
            "Nothing was ever executed against a live or simulated broker",
            "repository: no execution/OMS module",
        ),
        (
            "Interpretable rule families only (plus auxiliary ML annexes)",
            "Scope of the negative result",
            "The negative covers this hypothesis space, not machine learning strategies in general",
            "docs/methodology/experimental_design.md",
        ),
    ],
    schema=["limitation", "affected_conclusion", "practical_consequence", "evidence_path"],
    orient="row",
)
write_csv(T101, "table_10_1_limitations.csv")

T102 = pl.DataFrame(
    [
        (
            "construct",
            "Sharpe ratio as the selection statistic under heavy tails",
            "Kurtosis makes a point Sharpe a weak summary; the search optimises a fragile statistic",
            "Winners selected on a noisy criterion",
            "Promotion requires a bootstrap CI excluding zero, not a point estimate; tail metrics reported",
            "Selection still runs on validation Sharpe",
            "reports/thesis/chapter_06/METRICAS_DEFINICIONES.md",
        ),
        (
            "construct",
            "Two different Sharpe aggregations coexist",
            "Bar-weighted concatenated vs fold-weighted mean differ numerically",
            "Cross-reading them would misstate results",
            "Both reported in separate columns with an explicit warning",
            "Reader may still conflate them",
            "reports/thesis/chapter_07/ch7_results_units.csv",
        ),
        (
            "construct",
            "Taker imbalance used as an order-flow proxy",
            "No limit-order data; the construct is not OFI",
            "S2 families may not measure what their name suggests",
            "Named 'taker imbalance' throughout; overlap with mean_reversion measured by test",
            "Proxy remains a proxy",
            "docs/roadmap/gate_s2_batch_01.md",
        ),
        (
            "internal",
            "Outer-fold contamination in candidate search (R1)",
            "Fitness pooled across all folds leaked later windows into earlier selections",
            "Invalidated R1 evidence; biased in the GA's favour",
            "Detected, documented (ADR 0012), search isolated per fold, R2 re-baseline executed",
            "R1 numbers remain in history and must never be cited",
            "docs/decisions/0012-outer-fold-contamination-in-candidate-search.md",
        ),
        (
            "internal",
            "Look-ahead through features or regimes",
            "Indicators or regime cuts fitted on full sample would leak",
            "Inflated OOS performance",
            "Causal feature engine, per-fold regime refit, planted-leak counterexample detected by the guards (notebook 02)",
            "Guards cover the tested surface only",
            "notebooks/02_causal_features_and_leakage.ipynb",
        ),
        (
            "internal",
            "Fold boundary effects",
            "Adjacent train/test windows share information",
            "Optimistic OOS",
            "Purge 96 / embargo 118 bars derived from max label horizon, enforced in code",
            "Residual dependence across the concatenated series",
            "src/perp_lab/validation/walk_forward.py",
        ),
        (
            "internal",
            "Dirty worktrees during R2/R3 execution",
            "Code state not reconstructible from commit alone",
            "Exact re-execution not guaranteed",
            "Run identity records diff and untracked hashes; numbers cross-verified across persisted JSON",
            "reproducible_from_commit_alone = false for those rounds",
            "reports/thesis/chapter_07/NOTA_ACLARACIONES.md",
        ),
        (
            "external",
            "Single venue and two assets",
            "Market structure is venue- and asset-specific",
            "Findings may not generalise",
            "Scope stated in every table; transferability matrix prepared",
            "Unresolved without new data",
            "docs/thesis/ch9_11_package/tables/table_9_2_transferability_matrix.csv",
        ),
        (
            "external",
            "Reserved partition consumed",
            "No untouched confirmatory sample remains",
            "No clean confirmation possible on this history",
            "Opening documented in full, publication locked, conclusion made independent of it",
            "Permanent for this dataset",
            "docs/methodology/holdout_audit_status.md",
        ),
        (
            "external",
            "One historical period",
            "Regimes observed are those of 2020-2025",
            "Conclusions conditional on that history",
            "Walk-forward across 15 folds; regime-conditioned exploration",
            "Cannot be removed without new periods",
            "reports/thesis/chapter_07/ch7_results_units.csv",
        ),
        (
            "conclusion",
            "Multiple comparisons across families, seeds and configurations",
            "Best-of-N inflates the maximum observed statistic",
            "False promotion risk",
            "Holm, BH, DSR under two trial counts, CSCV PBO, trial-count sensitivity (13 to 496,500)",
            "Corrections cover the 13-family universe only; CRT/S3 not covered",
            "reports/study_closure/study_level_multiple_testing.json",
        ),
        (
            "conclusion",
            "Low power against small effects",
            "Costs and finite samples make small edges undetectable",
            "Absence of evidence read as evidence of absence",
            "Negative framed as 'not demonstrated under this protocol'; power limits stated",
            "Small true edges could remain undetected",
            "reports/thesis/chapter_07/ch7_ready_to_write.md",
        ),
        (
            "conclusion",
            "Regime conditioning splits the sample",
            "Fewer observations per cell reduces power",
            "Weak conditional effects could escape",
            "65 cells tested with a 500-bar floor and corrected p-values; labelled exploratory",
            "Only strong conditional edges are excluded",
            "reports/study_closure/regime_conditioned.json",
        ),
        (
            "conclusion",
            "Conditional simulations mistaken for validation",
            "Bootstrap ranges look like inference",
            "Over-claiming risk-based conclusions",
            "Chapter 8 labels every range a conditional simulation interval and states it validates no edge",
            "Reader may still over-read",
            "reports/thesis/chapter_08/ch8_method_contract.md",
        ),
    ],
    schema=[
        "validity_type",
        "threat",
        "mechanism",
        "possible_impact",
        "mitigation_implemented",
        "residual_risk",
        "evidence_path",
    ],
    orient="row",
)
write_csv(T102, "table_10_2_threats_to_validity.csv")


# --------------------------------------------------------------------------- #
# Chapter 11 tables
# --------------------------------------------------------------------------- #
# NOTE: O1-O8 are NOT defined anywhere in the repository (verified by search).
# The rows below are RECONSTRUCTED from the executed contract (RQ1-RQ5 in
# docs/methodology/experimental_design.md plus the operational objective of the
# methodology chapter) and are labelled as such. The writer must map them onto
# the DOCX's own O1-O8 wording before use.
T111 = pl.DataFrame(
    [
        (
            "O1 (reconstructed)",
            "Build a reproducible, causally sound research pipeline for crypto perpetuals",
            "ACHIEVED",
            "Versioned pipeline: data contract with SHA-256 manifests, causal feature engine, cost-aware backtester, walk-forward with purge/embargo, run identity fingerprints; 1,579 Python tests, deterministic notebooks",
            "Local single-machine execution; no orchestration or production deployment",
            "Chapters 4, 5",
        ),
        (
            "O2 (reconstructed)",
            "Characterise the statistical properties of the instruments (EDA)",
            "ACHIEVED",
            "10 recorded findings (F2-F10) with measured values; 27+ frozen EDA figures; findings drive family design and are re-derived causally per fold",
            "Full-sample descriptive thresholds are illustrative, never decision thresholds",
            "Chapter 5",
        ),
        (
            "O3 (reconstructed)",
            "Design and implement interpretable strategy families with pre-registered hypotheses",
            "ACHIEVED",
            "23 registered families across R2/R3/S1/S2/CRT/S3; each with entry/exit rules, searched grids and frozen pre-registration documents",
            "Five R3 families have no standalone catalogue sheet (hypotheses live in module docstrings at the frozen commit)",
            "Chapters 5, 7",
        ),
        (
            "O4 (reconstructed) = RQ1",
            "Determine whether any interpretable family is profitable net of costs OOS",
            "ACHIEVED (answer: no)",
            "0 promotions over 16 full-study families and 6 pilot families; smallest raw p = 0.3455; 0/13 survive Holm and BH",
            "Answer is 'not demonstrated under this protocol', not 'impossible'",
            "Chapters 6, 7",
        ),
        (
            "O5 (reconstructed) = RQ5 statistical control",
            "Apply selection-bias and multiple-testing control",
            "PARTIALLY_ACHIEVED",
            "Holm, BH, DSR (N=13 and N=496,500), CSCV PBO = 0.4857, trial-count sensitivity, White RC and Hansen SPA in the S1-B/S2-B pilots",
            "Computed for the 13-family closure universe ONLY; CRT (9 families) and S3 carry per-cell C1-C6 verdicts but no study-level correction: the extended 23-family universe was never corrected",
            "Chapter 6",
        ),
        (
            "O6 (reconstructed) = RQ2",
            "Compare Random Search and a Genetic Algorithm at equal budget",
            "ACHIEVED (answer: no advantage)",
            "Budget parity verified at artifact level: all 320 full-study runs consume exactly budget unique candidates per fold (9,600 cells, zero violations); paired GA-RS estimate -0.061, CI [-0.399, +0.277] under the clean protocol",
            "Compared on spaces of this cardinality only; says nothing about much larger spaces",
            "Chapters 6, 7",
        ),
        (
            "O7 (reconstructed) = risk analysis",
            "Quantify risk and uncertainty of the observed results",
            "ACHIEVED (as conditional diagnostics)",
            "Chapter 8: hierarchical stationary-block bootstrap (4,000 paths/candidate), per-seed path layer, exposure grid 0.25-2.00 with capital-breach probabilities, drawdown magnitude/duration, trade-concentration and permutation diagnostics, 92 automatic checks",
            "Conditional on the observed development record; validates no edge and changes no chapter-7 verdict; stop-based sizing NOT evaluable (ledgers persist no stop or monetary risk)",
            "Chapter 8",
        ),
        (
            "O8 (reconstructed) = architecture",
            "Deliver a maintainable, testable research architecture",
            "PARTIALLY_ACHIEVED",
            "Implemented: ingestion, catalog (SQLAlchemy + DuckDB over Parquet), features, strategies, backtesting, validation, search, evaluation, tracking, reporting, read-only API and web platform; quality gates (ruff, pyright 0 errors, 1,579 pytest, 112 vitest, 22 e2e) and CI on push/PR",
            "TARGET-ONLY components: portfolio layer, live risk engine (implemented for CRT but inactive), broker/exchange adapter, OMS, monitoring/drift, scheduler; architecture.md status markers are stale (self-declared out of date since 2026-08-08)",
            "Chapters 4, 11",
        ),
    ],
    schema=[
        "objective_id",
        "original_objective_reconstructed",
        "status",
        "actual_result_and_evidence",
        "limitation",
        "chapter_of_proof",
    ],
    orient="row",
)
write_csv(T111, "table_11_1_objectives.csv")

T112 = pl.DataFrame(
    [
        (
            "Data ingestion + contract",
            "IMPLEMENTED",
            "Binance Vision bulk archive, per-partition SHA-256 manifests, QC vs native klines, development/holdout physically separated",
            "Single venue and schema",
            "src/perp_lab/ingestion/, configs/data_contract.yaml",
        ),
        (
            "Experiment catalog",
            "IMPLEMENTED",
            "SQLAlchemy models (SQLite offline/tests, PostgreSQL variant) plus DuckDB queries over registered Parquet",
            "No server deployment; local files",
            "src/perp_lab/catalog/",
        ),
        (
            "Causal feature engine",
            "IMPLEMENTED",
            "Past-only shifted frames, availability enforced, planted-leak counterexample detected",
            "Feature set fixed to the declared families",
            "src/perp_lab/features/",
        ),
        (
            "Backtesting engine",
            "IMPLEMENTED",
            "Next-bar-open, fees, slippage, as-of-past funding, trade and equity ledgers per fold",
            "No order book, queue position, partial fills, market impact; fixed fraction 1.0",
            "src/perp_lab/backtesting/engine.py",
        ),
        (
            "Walk-forward validation",
            "IMPLEMENTED",
            "15 expanding folds, purge 96 / embargo 118 derived from label horizon, fold isolation enforced with an exception",
            "Geometry fixed by ADR 0008",
            "src/perp_lab/validation/walk_forward.py",
        ),
        (
            "Search (RS + GA)",
            "IMPLEMENTED",
            "Shared space, hash dedup, per-fold isolation, budget parity verified over 9,600 fold cells",
            "Budgets 25-300 per fold; two engines only",
            "src/perp_lab/search/",
        ),
        (
            "Evaluation and robustness",
            "IMPLEMENTED",
            "Metrics battery, block bootstrap, cost stress, concentration, baselines, multiple-testing module, Monte Carlo module",
            "Study-level corrections applied to the 13-family universe only",
            "src/perp_lab/evaluation/",
        ),
        (
            "Experiment tracking",
            "IMPLEMENTED",
            "Run identity (config + contract + dataset + git state incl. diff/untracked), seed schedules, checkpointed multi-seed studies",
            "Dirty-worktree runs are identified but not reconstructible from commit alone",
            "src/perp_lab/tracking/identity.py",
        ),
        (
            "Reporting and thesis artifacts",
            "IMPLEMENTED",
            "Deterministic figure/table builders, 8 executed notebooks, chapter packages 3-8 with manifests and verification",
            "Manual chapter assembly",
            "scripts/, reports/",
        ),
        (
            "Read-only API + web platform",
            "IMPLEMENTED",
            "FastAPI /api/v1 over artifacts, Next.js research site with browser backtester, strategy explorer, guided lab",
            "Read-only by design; no trading control surface",
            "apps/api/, apps/web/",
        ),
        (
            "Meta-labeling layer",
            "IMPLEMENTED (exploratory use only)",
            "Triple-barrier labels, three pre-registered models, calibration, synthetic validation (ADR 0017) and one real application",
            "Ran with no eligible primary; exploratory contract; not a validated component",
            "src/perp_lab/meta_labeling/, src/perp_lab/models/",
        ),
        (
            "Volatility forecasting annex",
            "IMPLEMENTED (annex)",
            "HAR vs LSTM with a frozen decision rule and Diebold-Mariano test",
            "Forecasting layer only; never wired into a strategy",
            "src/perp_lab/volforecast/",
        ),
        (
            "CRT risk engine",
            "IMPLEMENTED BUT INACTIVE",
            "Stop-distance sizing, max trades per session/level, daily-loss lockouts, all unit-tested",
            "Never connected: FamilyMechanics.risk is None in every executed round; sizing stayed at 1.0",
            "src/perp_lab/crt/risk.py",
        ),
        (
            "Position sizing / leverage limits (config)",
            "DESIGNED, NOT CONSUMED",
            "position_sizing and risk blocks exist in configs/experiment.yaml, marked provisional",
            "The backtester never reads them; the YAML comment claiming otherwise is wrong",
            "configs/experiment.yaml",
        ),
        (
            "Portfolio layer",
            "NOT IMPLEMENTED",
            "Correlation-aware allocation across families/assets",
            "Required before any multi-strategy claim (BTC-ETH correlate 0.839)",
            "docs/roadmap/future_architecture.md",
        ),
        (
            "Broker / exchange adapter, OMS",
            "NOT IMPLEMENTED",
            "No connectivity, order management or reconciliation",
            "Blocks paper trading and live deployment",
            "-",
        ),
        (
            "Monitoring / drift detection",
            "NOT IMPLEMENTED",
            "No production monitoring or data-drift alerts",
            "Blocks controlled deployment",
            "-",
        ),
        (
            "Quality gates",
            "IMPLEMENTED (partial CI)",
            "ruff, ruff format, stale-claims sweep and pytest (non-network) run in GitHub Actions on push/PR; pyright, vitest, Playwright and the production build are run locally",
            "CI does not cover type checking or the web suites",
            ".github/workflows/ci.yml",
        ),
        (
            "Determinism and reproducibility",
            "IMPLEMENTED",
            "Seed schedules, fixed builders, double-run byte-identity checks for chapters 3, 5, 7 and 8; notebook re-execution verified",
            "Not enforced per-commit in CI",
            "scripts/verify_determinism.py, chapter MANIFESTs",
        ),
        (
            "Compute cost per round",
            "NOT RECORDED",
            "No wall-clock or cost accounting persisted per study",
            "Cannot report computational budget in the thesis",
            "-",
        ),
    ],
    schema=["component", "status", "what_exists", "limitation_or_gap", "evidence_path"],
    orient="row",
)
write_csv(T112, "table_11_2_architecture_assessment.csv")

T113 = pl.DataFrame(
    [
        (
            "Causal, reproducible research protocol",
            "Methodological",
            "Per-fold isolated search with frozen winner fingerprints, purge/embargo derived from the label horizon, guards that fail closed and detect a planted leak",
            "ADR 0012, ADR 0008, notebooks 02-03",
            "Transferable to any walk-forward study",
        ),
        (
            "Detection and correction of outer-fold contamination",
            "Methodological",
            "A real defect found, documented, corrected and re-baselined instead of silently fixed: re-scoring 60 candidates changed 44 fitness values",
            "ADR 0012, ADR 0013",
            "The clearest demonstration that the protocol catches its own errors",
        ),
        (
            "Data contracts with cryptographic provenance",
            "Engineering",
            "SHA-256 manifests per partition, physical dev/holdout separation, QC against a second source",
            "configs/data_contract.yaml, data/manifests/",
            "Market data never published; only hashes",
        ),
        (
            "Cost- and funding-aware backtesting",
            "Engineering",
            "Net returns after 4+1 bps/side and realized as-of-past funding; funded always-long perp benchmark on identical bars",
            "src/perp_lab/backtesting/, evaluation/baselines.py",
            "Benchmark convention reconciled and asserted in the builders",
        ),
        (
            "RS vs GA under verified budget parity",
            "Empirical",
            "Budget parity proven at artifact level (9,600 fold cells, zero violations); no GA advantage under the clean protocol",
            "ch7 package, NOTA_ACLARACIONES.md",
            "Answers RQ2 conservatively",
        ),
        (
            "Multi-seed walk-forward evaluation",
            "Methodological",
            "Seed dispersion treated as search noise over one market history, never as independent replications or confidence intervals",
            "ch7_seed_dispersion.md",
            "Prevents a common over-claim",
        ),
        (
            "Study-level multiple-testing control",
            "Methodological",
            "Holm, BH, DSR under two trial counts, CSCV PBO, and an explicit trial-count sensitivity from 13 to 496,500",
            "reports/study_closure/",
            "Scope limits published alongside",
        ),
        (
            "Full experiment traceability",
            "Engineering",
            "Run identity covering config, contract, dataset hashes and git state including diff and untracked files; checkpointed studies; master inventory of every round including discarded ones",
            "tracking/identity.py, INVENTARIO_MAESTRO",
            "Discarded runs documented, not hidden",
        ),
        (
            "Transparent publication of a negative result",
            "Scientific",
            "0 promotions published with the mechanism (PBO 0.4857, selection optimism +4.04 Sharpe units), plus a protocol deviation (holdout opening) recorded in the open",
            "Chapters 6-7, holdout_audit_status.md",
            "Includes the discrepancy that is costly to admit",
        ),
        (
            "Conditional risk and uncertainty analysis",
            "Methodological",
            "Separation of search, path and combined uncertainty; conditional simulation intervals; exposure-scaling breach probabilities with Monte Carlo error",
            "Chapter 8 package",
            "Explicitly not validation",
        ),
    ],
    schema=["contribution", "type", "what_was_demonstrated", "evidence_path", "note"],
    orient="row",
)
write_csv(T113, "table_11_3_contributions.csv")


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
BLUE, ORANGE, GREEN, GREY, RED = "#0072B2", "#D55E00", "#009E73", "#666666", "#C0392B"


def box(ax, x, y, w, h, text, fc, ec, fontsize=9, weight="normal", tc="black"):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            facecolor=fc,
            edgecolor=ec,
            linewidth=1.4,
        )
    )
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=weight,
        color=tc,
        wrap=True,
    )


def arrow(ax, x1, y1, x2, y2, color=GREY, style="-|>"):
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle=style,
            mutation_scale=13,
            color=color,
            linewidth=1.3,
            shrinkA=2,
            shrinkB=2,
        )
    )


# --- Figure 9.1: validation-path decision tree ------------------------------
fig, ax = plt.subplots(figsize=(11.0, 7.6))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")

box(
    ax,
    3.0,
    9.05,
    4.0,
    0.75,
    "Is an untouched sample available\non this dataset?",
    "#FDF6E3",
    GREY,
    10,
    "bold",
)
box(
    ax,
    0.15,
    8.28,
    2.3,
    0.72,
    "NO - the reserved partition\nwas opened 2026-08-13\nand is consumed",
    "#FDEDEC",
    RED,
    8.2,
)
arrow(ax, 3.6, 9.05, 1.7, 9.02)
ax.text(2.9, 9.12, "verified", fontsize=7.5, color=GREY, style="italic", ha="right")

box(
    ax,
    2.6,
    7.85,
    4.8,
    0.62,
    "External validation requires NEW evidence",
    "#EAF2FA",
    BLUE,
    9.5,
    "bold",
)
arrow(ax, 5.0, 9.05, 5.0, 8.5)

paths = [
    (
        0.15,
        5.3,
        "Path A\nNew time period\n(cutoff > 2026-07-01)",
        "Same venue, same assets;\nonly new bars",
        "PRIORITY 1",
        GREEN,
    ),
    (
        2.65,
        5.3,
        "Path D\nForward paper trading\n(no post-start edits)",
        "Needs broker adapter\nand OMS (absent)",
        "PRIORITY 2",
        BLUE,
    ),
    (
        5.15,
        5.3,
        "Path B\nAnother perpetuals\nexchange",
        "Re-estimate fees,\nfunding, liquidity",
        "PRIORITY 3",
        ORANGE,
    ),
    (
        7.65,
        5.3,
        "Path C\nAnother market\n(index futures)",
        "Roll calendar, sessions,\ncost model, no funding",
        "PRIORITY 4",
        GREY,
    ),
]
for x, y, title, req, prio, color in paths:
    box(ax, x, y, 2.2, 1.15, title, "white", color, 9, "bold")
    arrow(ax, 5.0, 7.85, x + 1.1, y + 1.15)
    box(ax, x, y - 1.05, 2.2, 0.9, req, "#F7F7F7", "#BBBBBB", 8)
    ax.text(x + 1.1, y - 1.35, prio, ha="center", fontsize=8.5, fontweight="bold", color=color)

box(
    ax,
    1.2,
    1.6,
    7.6,
    1.5,
    "Selected future route: Path A first.\n"
    "It is the only path that changes ONE factor (time) while holding venue, assets,\n"
    "contract, cost model and pipeline fixed - so a failure is attributable.\n"
    "Paths B/C confound market change with strategy validity; Path D needs components\n"
    "that do not exist yet (broker adapter, OMS, monitoring).",
    "#EAF7F0",
    GREEN,
    9,
)
arrow(ax, 1.25, 3.88, 2.3, 3.12, GREEN)

ax.text(
    5.0,
    0.75,
    "NOT EXECUTED - this is a design, not a result. No external validation exists in this thesis.",
    ha="center",
    fontsize=9,
    fontweight="bold",
    color=RED,
)
ax.set_title(
    "Decision tree for external-validation paths and the rationale for the selected future route",
    fontsize=11.5,
    pad=12,
)
save_fig(fig, "fig_9_1_validation_paths")

# --- Figure 10.1: threats and mitigations -----------------------------------
threat_rows = [
    ("Construct", "Sharpe under heavy tails", "Bootstrap CI required for promotion", 0.55),
    ("Construct", "Order-flow proxy (no book)", "Named as proxy; overlap tested", 0.70),
    ("Internal", "Outer-fold contamination", "Per-fold isolation + re-baseline (ADR 0012)", 0.15),
    ("Internal", "Look-ahead in features", "Causal engine + planted-leak detection", 0.20),
    ("Internal", "Fold boundary leakage", "Purge 96 / embargo 118 bars", 0.25),
    ("External", "Single venue, two assets", "Scope declared everywhere", 0.85),
    ("External", "Reserved partition consumed", "Documented; conclusion made independent", 0.90),
    ("Conclusion", "Multiple comparisons", "Holm/BH/DSR/PBO + trial-count sensitivity", 0.35),
    ("Conclusion", "Low power vs small effects", "Framed as 'not demonstrated'", 0.65),
    ("Conclusion", "Simulation read as validation", "Conditional-interval labelling (ch. 8)", 0.40),
]
cat_color = {"Construct": BLUE, "Internal": GREEN, "External": ORANGE, "Conclusion": "#CC79A7"}
fig, ax = plt.subplots(figsize=(11.4, 6.8))
ys = range(len(threat_rows))
for i, (cat, threat, mitig, residual) in enumerate(threat_rows):
    y = len(threat_rows) - 1 - i
    ax.barh(y, 1.0, color="#EEEEEE", edgecolor="none", height=0.62)
    ax.barh(y, 1.0 - residual, color=cat_color[cat], alpha=0.85, edgecolor="none", height=0.62)
    ax.text(-0.02, y, threat, ha="right", va="center", fontsize=9)
    ax.text(1.02, y, mitig, ha="left", va="center", fontsize=8, color="#444444")
ax.set_yticks([])
ax.set_xlim(0, 1)
ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
ax.set_xlabel(
    "share of the threat addressed by an implemented mitigation (grey = residual risk that remains)"
)
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cat_color.values()]
ax.legend(
    handles,
    cat_color.keys(),
    fontsize=8.5,
    ncol=4,
    loc="lower center",
    bbox_to_anchor=(0.5, -0.28),
    title="validity category",
)
ax.set_title(
    "Threats to validity and the protocol mechanisms that mitigate them\n"
    "Every bar keeps a grey remainder: a mitigation reduces a threat, it never "
    "removes it. Shares are qualitative assessments, not measured quantities.",
    fontsize=11,
    pad=14,
)
ax.grid(axis="y", visible=False)
fig.tight_layout()
save_fig(fig, "fig_10_1_threats_to_validity")

# --- Figure 11.1: future-work roadmap ---------------------------------------
fig, ax = plt.subplots(figsize=(11.4, 7.2))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")

lanes = [
    (8.15, "NEW EVIDENCE", BLUE),
    (5.35, "EXECUTION REALISM", ORANGE),
    (2.55, "CONTROLLED DEPLOYMENT", GREEN),
]
for y, label, color in lanes:
    ax.add_patch(
        FancyBboxPatch(
            (0.1, y - 0.95),
            9.8,
            2.35,
            boxstyle="round,pad=0.01,rounding_size=0.02",
            facecolor="#FAFAFA",
            edgecolor="#DDDDDD",
            linewidth=1.0,
        )
    )
    ax.text(0.28, y + 1.12, label, fontsize=9.5, fontweight="bold", color=color)

items = [
    (0.45, 8.15, "1. New frozen\ntime partition\n(cutoff > 2026-07)", BLUE),
    (2.75, 8.15, "2. Forward\npaper trading\n(no edits after start)", BLUE),
    (5.05, 8.15, "3. Additional venue\nor market\n(B / C)", BLUE),
    (7.35, 8.15, "4. Statistical closure\nof the 23-family\nuniverse", BLUE),
    (0.45, 5.35, "5. Order-book-aware\nexecution and\nimpact model", ORANGE),
    (2.75, 5.35, "6. Portfolio layer +\nactivated risk\nengine", ORANGE),
    (5.05, 5.35, "8. Meta-labeling only\nover a viable\nprimary signal", ORANGE),
    (0.45, 2.55, "7. Drift and\nperformance\nmonitoring", GREEN),
    (2.75, 2.55, "9. Controlled\ndeployment\n(small size, kill switch)", GREEN),
]
for x, y, text, color in items:
    box(ax, x, y - 0.55, 2.05, 1.15, text, "white", color, 8.6)

arrow(ax, 2.5, 8.15, 2.75, 8.15, BLUE)
arrow(ax, 4.8, 8.15, 5.05, 8.15, BLUE)
arrow(ax, 1.47, 7.6, 1.47, 6.05, GREY)
arrow(ax, 3.8, 4.8, 3.8, 3.7, GREY)
arrow(ax, 2.5, 2.55, 2.75, 2.55, GREEN)

ax.text(
    5.05,
    3.05,
    "Deployment is gated by everything above it:\n"
    "no new evidence and no execution realism means no deployment.",
    fontsize=8.8,
    color="#444444",
    va="center",
)
ax.text(
    5.0,
    0.85,
    "Priority runs left to right and top to bottom. Nothing in this roadmap has been "
    "executed;\nit is the pre-registered order in which new evidence would have to be "
    "produced.",
    ha="center",
    fontsize=9,
    color=RED,
    fontweight="bold",
)
ax.set_title(
    "Future-work roadmap: new evidence, execution realism and controlled deployment",
    fontsize=11.5,
    pad=10,
)
save_fig(fig, "fig_11_1_future_work_roadmap")


# --------------------------------------------------------------------------- #
# Hash index for the manifest
# --------------------------------------------------------------------------- #
rows = []
for sub in ("tables", "figures", "data"):
    for p in sorted((PKG / sub).iterdir()):
        if p.is_file():
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            rows.append({"path": f"{sub}/{p.name}", "bytes": p.stat().st_size, "sha256": digest})
HASHES = pl.DataFrame(rows)
HASHES.write_csv(PKG / "data" / "artifact_hashes.csv")
print(f"\nartifacts: {HASHES.height} files hashed -> data/artifact_hashes.csv")
print(f"written under {PKG}")
