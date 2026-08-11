# Gate R3 — Thesis reporting extract

*Derived from persisted artifacts · source timestamp `2026-08-10T17:41:53.213509+00:00`*

Random Search is the **confirmatory** promotion engine. Genetic Algorithm results are **secondary** and do not decide family promotion.

## Closure summary

- **gate_status:** CLOSED_NEGATIVE (*reporter_verified* · `r3_gate_verdict.json` · `gate_status`)
- **n_promoted:** 0 (*reporter_verified* · `r3_gate_verdict.json` · `n_promoted`)
- **n_rejected:** 5 (*reporter_verified* · `r3_gate_verdict.json` · `n_rejected`)
- **units_completed:** 100/100 (*reporter_verified* · `*/status.json + */checkpoint.json` · `status.completed vs checkpoint.meta symbols*seeds`)
- **numerical_discrepancies:** 0 (*reporter_verified* · `reporter consistency battery` · `n/a`)
- **r4_required:** False (*reporter_verified* · `r3_gate_verdict.json` · `r4_required`)
- **isolation_audit_at_closure:** 100/100 audited; failures=0 (*documentary* · `r3_scientific_closure_report.json` · `isolation_audit`)
- **reporter_holdout_accessed:** False (*reporter_verified* · read manifest under R3 root only)
- **historical_holdout_status:** Frozen holdout not opened during Gate R3 (documented at closure) (*documentary* · `docs/decisions/0015-r3-family-evaluation-negative.md`)
- **r4_required_at_closure:** False (*reporter_verified* · `r3_gate_verdict.json`)
- **r4_application_status:** SKIPPED (zero R3 promotions at closure) (*documentary*)

## Primary results — Random Search

| Family | Asset | C1 | C2 | C3 | C4 | C5 | C6 | Min trades veto | Med OOS ret | Med OOS Sharpe | Med B&H | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| breakout | BTCUSDT | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 10/10 OK | 10/10 OK | -15.8% | -0.73 | +52.3% | **REJECTED** |
| breakout | ETHUSDT | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 10/10 OK | 10/10 OK | -25.5% | -1.05 | -21.9% | **REJECTED** |
| mean_reversion | BTCUSDT | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 10/10 OK | 10/10 OK | -60.0% | -0.50 | +52.3% | **REJECTED** |
| mean_reversion | ETHUSDT | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 10/10 OK | 10/10 OK | -79.9% | -0.89 | -21.9% | **REJECTED** |
| volatility_breakout | BTCUSDT | 6/10 OK | 0/10 FAIL | 3/10 FAIL | 2/10 FAIL | 0/10 FAIL | 6/10 OK | 10/10 OK | +6.5% | 0.22 | +52.3% | **REJECTED** (partial non-robust signal (not promotion-eligible)) |
| volatility_breakout | ETHUSDT | 1/10 FAIL | 0/10 FAIL | 1/10 FAIL | 1/10 FAIL | 0/10 FAIL | 9/10 OK | 10/10 OK | -73.5% | -0.66 | -21.9% | **REJECTED** |
| funding | BTCUSDT | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 10/10 OK | 10/10 OK | -40.9% | -0.27 | +52.3% | **REJECTED** |
| funding | ETHUSDT | 1/10 FAIL | 0/10 FAIL | 1/10 FAIL | 1/10 FAIL | 0/10 FAIL | 10/10 OK | 10/10 OK | -59.9% | -0.32 | -21.9% | **REJECTED** |
| BTC_ETH_confirmation | BTCUSDT | 1/10 FAIL | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 9/10 OK | 10/10 OK | -65.8% | -0.55 | +52.3% | **REJECTED** |
| BTC_ETH_confirmation | ETHUSDT | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 0/10 FAIL | 10/10 OK | 10/10 OK | -68.3% | -0.30 | -21.9% | **REJECTED** |

`min_oos_trades_met` is a **separate veto**, not a seventh promotion criterion.

## Random Search vs Genetic Algorithm (secondary)

| Family | GA - RS mean | 95% CI | Interpretation | GA decides promotion? |
|---|---:|---|---|:---:|
| breakout | +0.055 | [-0.034, +0.145] | no evidence of a difference between Random Search and the Genetic Algorithm: the 95% confidence interval for the paired difference includes zero | **No** |
| mean_reversion | +0.179 | [+0.012, +0.346] | genetic_algorithm is ahead on the paired fold-level comparison (interval excludes zero); this is development out-of-sample evidence only and does not establish holdout performance | **No** |
| volatility_breakout | -0.072 | [-0.366, +0.222] | no evidence of a difference between Random Search and the Genetic Algorithm: the 95% confidence interval for the paired difference includes zero | **No** |
| funding | +0.116 | [-0.227, +0.459] | no evidence of a difference between Random Search and the Genetic Algorithm: the 95% confidence interval for the paired difference includes zero | **No** |
| BTC_ETH_confirmation | +0.164 | [-0.084, +0.413] | no evidence of a difference between Random Search and the Genetic Algorithm: the 95% confidence interval for the paired difference includes zero | **No** |

## Traceability

| Claim | Value | Source file | Source field | Verification | Classification |
|---|---|---|---|---|---|
| breakout/BTCUSDT C1 positive return | 0/10 FAIL | `breakout/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.positive_total_return` | reporter_verified | primary_result |
| breakout/BTCUSDT C2 bootstrap Sharpe CI | 0/10 FAIL | `breakout/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.bootstrap_sharpe_ci_excludes_zero` | reporter_verified | primary_result |
| breakout/BTCUSDT C3 survives 2x costs | 0/10 FAIL | `breakout/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.survives_double_costs` | reporter_verified | primary_result |
| breakout/BTCUSDT C4 beats buy-and-hold | 0/10 FAIL | `breakout/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.beats_buy_and_hold` | reporter_verified | primary_result |
| breakout/BTCUSDT C5 drop top 5 trades | 0/10 FAIL | `breakout/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.survives_drop_top_trades` | reporter_verified | primary_result |
| breakout/BTCUSDT C6 fold locality | 10/10 OK | `breakout/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.not_confined_to_one_fold` | reporter_verified | primary_result |
| breakout/BTCUSDT min_oos_trades_met veto | 10/10 OK | `breakout/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.rejections.depends_on_few_trades` | reporter_verified | primary_result |
| breakout/BTCUSDT median OOS return | -0.15795781516548946 | `breakout/study_robustness.json` | `by_symbol_and_engine.BTCUSDT|random_search.median_total_return` | reporter_verified | primary_result |
| breakout/BTCUSDT median OOS Sharpe | -0.7308026909947924 | `breakout/study_robustness.json` | `per_run[].strategy.sharpe` | reporter_verified | primary_result |
| breakout/BTCUSDT median buy-and-hold return | 0.522747844787544 | `breakout/study_robustness.json` | `by_symbol_and_engine.BTCUSDT|random_search.median_buy_and_hold_return` | reporter_verified | primary_result |
| breakout/BTCUSDT family verdict | REJECTED | `r3_family_rollup.json` | `families.breakout.analysis.verdict` | reporter_verified | primary_result |
| breakout/ETHUSDT C1 positive return | 0/10 FAIL | `breakout/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.positive_total_return` | reporter_verified | primary_result |
| breakout/ETHUSDT C2 bootstrap Sharpe CI | 0/10 FAIL | `breakout/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.bootstrap_sharpe_ci_excludes_zero` | reporter_verified | primary_result |
| breakout/ETHUSDT C3 survives 2x costs | 0/10 FAIL | `breakout/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.survives_double_costs` | reporter_verified | primary_result |
| breakout/ETHUSDT C4 beats buy-and-hold | 0/10 FAIL | `breakout/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.beats_buy_and_hold` | reporter_verified | primary_result |
| breakout/ETHUSDT C5 drop top 5 trades | 0/10 FAIL | `breakout/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.survives_drop_top_trades` | reporter_verified | primary_result |
| breakout/ETHUSDT C6 fold locality | 10/10 OK | `breakout/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.not_confined_to_one_fold` | reporter_verified | primary_result |
| breakout/ETHUSDT min_oos_trades_met veto | 10/10 OK | `breakout/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.rejections.depends_on_few_trades` | reporter_verified | primary_result |
| breakout/ETHUSDT median OOS return | -0.25525919986792583 | `breakout/study_robustness.json` | `by_symbol_and_engine.ETHUSDT|random_search.median_total_return` | reporter_verified | primary_result |
| breakout/ETHUSDT median OOS Sharpe | -1.0545238570959898 | `breakout/study_robustness.json` | `per_run[].strategy.sharpe` | reporter_verified | primary_result |
| breakout/ETHUSDT median buy-and-hold return | -0.2190192992677874 | `breakout/study_robustness.json` | `by_symbol_and_engine.ETHUSDT|random_search.median_buy_and_hold_return` | reporter_verified | primary_result |
| breakout/ETHUSDT family verdict | REJECTED | `r3_family_rollup.json` | `families.breakout.analysis.verdict` | reporter_verified | primary_result |
| breakout GA-RS paired mean difference | 0.05546777780671216 | `r3_family_rollup.json` | `families.breakout.analysis.paired_ga_minus_rs.mean_difference` | reporter_verified | secondary_diagnostic |
| breakout GA-RS 95% CI | [-0.03406478852480028, 0.1450003441382246] | `r3_family_rollup.json` | `families.breakout.analysis.paired_ga_minus_rs` | reporter_verified | secondary_diagnostic |
| mean_reversion/BTCUSDT C1 positive return | 0/10 FAIL | `mean_reversion/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.positive_total_return` | reporter_verified | primary_result |
| mean_reversion/BTCUSDT C2 bootstrap Sharpe CI | 0/10 FAIL | `mean_reversion/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.bootstrap_sharpe_ci_excludes_zero` | reporter_verified | primary_result |
| mean_reversion/BTCUSDT C3 survives 2x costs | 0/10 FAIL | `mean_reversion/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.survives_double_costs` | reporter_verified | primary_result |
| mean_reversion/BTCUSDT C4 beats buy-and-hold | 0/10 FAIL | `mean_reversion/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.beats_buy_and_hold` | reporter_verified | primary_result |
| mean_reversion/BTCUSDT C5 drop top 5 trades | 0/10 FAIL | `mean_reversion/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.survives_drop_top_trades` | reporter_verified | primary_result |
| mean_reversion/BTCUSDT C6 fold locality | 10/10 OK | `mean_reversion/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.not_confined_to_one_fold` | reporter_verified | primary_result |
| mean_reversion/BTCUSDT min_oos_trades_met veto | 10/10 OK | `mean_reversion/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.rejections.depends_on_few_trades` | reporter_verified | primary_result |
| mean_reversion/BTCUSDT median OOS return | -0.5996847869944606 | `mean_reversion/study_robustness.json` | `by_symbol_and_engine.BTCUSDT|random_search.median_total_return` | reporter_verified | primary_result |
| mean_reversion/BTCUSDT median OOS Sharpe | -0.5005010494241832 | `mean_reversion/study_robustness.json` | `per_run[].strategy.sharpe` | reporter_verified | primary_result |
| mean_reversion/BTCUSDT median buy-and-hold return | 0.522747844787544 | `mean_reversion/study_robustness.json` | `by_symbol_and_engine.BTCUSDT|random_search.median_buy_and_hold_return` | reporter_verified | primary_result |
| mean_reversion/BTCUSDT family verdict | REJECTED | `r3_family_rollup.json` | `families.mean_reversion.analysis.verdict` | reporter_verified | primary_result |
| mean_reversion/ETHUSDT C1 positive return | 0/10 FAIL | `mean_reversion/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.positive_total_return` | reporter_verified | primary_result |
| mean_reversion/ETHUSDT C2 bootstrap Sharpe CI | 0/10 FAIL | `mean_reversion/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.bootstrap_sharpe_ci_excludes_zero` | reporter_verified | primary_result |
| mean_reversion/ETHUSDT C3 survives 2x costs | 0/10 FAIL | `mean_reversion/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.survives_double_costs` | reporter_verified | primary_result |
| mean_reversion/ETHUSDT C4 beats buy-and-hold | 0/10 FAIL | `mean_reversion/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.beats_buy_and_hold` | reporter_verified | primary_result |
| mean_reversion/ETHUSDT C5 drop top 5 trades | 0/10 FAIL | `mean_reversion/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.survives_drop_top_trades` | reporter_verified | primary_result |
| mean_reversion/ETHUSDT C6 fold locality | 10/10 OK | `mean_reversion/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.not_confined_to_one_fold` | reporter_verified | primary_result |
| mean_reversion/ETHUSDT min_oos_trades_met veto | 10/10 OK | `mean_reversion/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.rejections.depends_on_few_trades` | reporter_verified | primary_result |
| mean_reversion/ETHUSDT median OOS return | -0.7990860353922618 | `mean_reversion/study_robustness.json` | `by_symbol_and_engine.ETHUSDT|random_search.median_total_return` | reporter_verified | primary_result |
| mean_reversion/ETHUSDT median OOS Sharpe | -0.8932117142699131 | `mean_reversion/study_robustness.json` | `per_run[].strategy.sharpe` | reporter_verified | primary_result |
| mean_reversion/ETHUSDT median buy-and-hold return | -0.2190192992677874 | `mean_reversion/study_robustness.json` | `by_symbol_and_engine.ETHUSDT|random_search.median_buy_and_hold_return` | reporter_verified | primary_result |
| mean_reversion/ETHUSDT family verdict | REJECTED | `r3_family_rollup.json` | `families.mean_reversion.analysis.verdict` | reporter_verified | primary_result |
| mean_reversion GA-RS paired mean difference | 0.17868330561544477 | `r3_family_rollup.json` | `families.mean_reversion.analysis.paired_ga_minus_rs.mean_difference` | reporter_verified | secondary_diagnostic |
| mean_reversion GA-RS 95% CI | [0.011851644153656082, 0.34551496707723345] | `r3_family_rollup.json` | `families.mean_reversion.analysis.paired_ga_minus_rs` | reporter_verified | secondary_diagnostic |
| volatility_breakout/BTCUSDT C1 positive return | 6/10 OK | `volatility_breakout/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.positive_total_return` | reporter_verified | secondary_diagnostic |
| volatility_breakout/BTCUSDT C2 bootstrap Sharpe CI | 0/10 FAIL | `volatility_breakout/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.bootstrap_sharpe_ci_excludes_zero` | reporter_verified | primary_result |
| volatility_breakout/BTCUSDT C3 survives 2x costs | 3/10 FAIL | `volatility_breakout/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.survives_double_costs` | reporter_verified | primary_result |
| volatility_breakout/BTCUSDT C4 beats buy-and-hold | 2/10 FAIL | `volatility_breakout/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.beats_buy_and_hold` | reporter_verified | primary_result |
| volatility_breakout/BTCUSDT C5 drop top 5 trades | 0/10 FAIL | `volatility_breakout/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.survives_drop_top_trades` | reporter_verified | primary_result |
| volatility_breakout/BTCUSDT C6 fold locality | 6/10 OK | `volatility_breakout/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.not_confined_to_one_fold` | reporter_verified | primary_result |
| volatility_breakout/BTCUSDT min_oos_trades_met veto | 10/10 OK | `volatility_breakout/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.rejections.depends_on_few_trades` | reporter_verified | primary_result |
| volatility_breakout/BTCUSDT median OOS return | 0.06492510211407598 | `volatility_breakout/study_robustness.json` | `by_symbol_and_engine.BTCUSDT|random_search.median_total_return` | reporter_verified | primary_result |
| volatility_breakout/BTCUSDT median OOS Sharpe | 0.21537605004200375 | `volatility_breakout/study_robustness.json` | `per_run[].strategy.sharpe` | reporter_verified | primary_result |
| volatility_breakout/BTCUSDT median buy-and-hold return | 0.522747844787544 | `volatility_breakout/study_robustness.json` | `by_symbol_and_engine.BTCUSDT|random_search.median_buy_and_hold_return` | reporter_verified | primary_result |
| volatility_breakout/BTCUSDT family verdict | REJECTED | `r3_family_rollup.json` | `families.volatility_breakout.analysis.verdict` | reporter_verified | primary_result |
| volatility_breakout/ETHUSDT C1 positive return | 1/10 FAIL | `volatility_breakout/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.positive_total_return` | reporter_verified | primary_result |
| volatility_breakout/ETHUSDT C2 bootstrap Sharpe CI | 0/10 FAIL | `volatility_breakout/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.bootstrap_sharpe_ci_excludes_zero` | reporter_verified | primary_result |
| volatility_breakout/ETHUSDT C3 survives 2x costs | 1/10 FAIL | `volatility_breakout/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.survives_double_costs` | reporter_verified | primary_result |
| volatility_breakout/ETHUSDT C4 beats buy-and-hold | 1/10 FAIL | `volatility_breakout/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.beats_buy_and_hold` | reporter_verified | primary_result |
| volatility_breakout/ETHUSDT C5 drop top 5 trades | 0/10 FAIL | `volatility_breakout/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.survives_drop_top_trades` | reporter_verified | primary_result |
| volatility_breakout/ETHUSDT C6 fold locality | 9/10 OK | `volatility_breakout/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.not_confined_to_one_fold` | reporter_verified | primary_result |
| volatility_breakout/ETHUSDT min_oos_trades_met veto | 10/10 OK | `volatility_breakout/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.rejections.depends_on_few_trades` | reporter_verified | primary_result |
| volatility_breakout/ETHUSDT median OOS return | -0.7352424298675606 | `volatility_breakout/study_robustness.json` | `by_symbol_and_engine.ETHUSDT|random_search.median_total_return` | reporter_verified | primary_result |
| volatility_breakout/ETHUSDT median OOS Sharpe | -0.6623581493750325 | `volatility_breakout/study_robustness.json` | `per_run[].strategy.sharpe` | reporter_verified | primary_result |
| volatility_breakout/ETHUSDT median buy-and-hold return | -0.2190192992677874 | `volatility_breakout/study_robustness.json` | `by_symbol_and_engine.ETHUSDT|random_search.median_buy_and_hold_return` | reporter_verified | primary_result |
| volatility_breakout/ETHUSDT family verdict | REJECTED | `r3_family_rollup.json` | `families.volatility_breakout.analysis.verdict` | reporter_verified | primary_result |
| volatility_breakout GA-RS paired mean difference | -0.0719021434379294 | `r3_family_rollup.json` | `families.volatility_breakout.analysis.paired_ga_minus_rs.mean_difference` | reporter_verified | secondary_diagnostic |
| volatility_breakout GA-RS 95% CI | [-0.3657664282903287, 0.2219621414144699] | `r3_family_rollup.json` | `families.volatility_breakout.analysis.paired_ga_minus_rs` | reporter_verified | secondary_diagnostic |
| funding/BTCUSDT C1 positive return | 0/10 FAIL | `funding/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.positive_total_return` | reporter_verified | primary_result |
| funding/BTCUSDT C2 bootstrap Sharpe CI | 0/10 FAIL | `funding/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.bootstrap_sharpe_ci_excludes_zero` | reporter_verified | primary_result |
| funding/BTCUSDT C3 survives 2x costs | 0/10 FAIL | `funding/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.survives_double_costs` | reporter_verified | primary_result |
| funding/BTCUSDT C4 beats buy-and-hold | 0/10 FAIL | `funding/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.beats_buy_and_hold` | reporter_verified | primary_result |
| funding/BTCUSDT C5 drop top 5 trades | 0/10 FAIL | `funding/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.survives_drop_top_trades` | reporter_verified | primary_result |
| funding/BTCUSDT C6 fold locality | 10/10 OK | `funding/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.not_confined_to_one_fold` | reporter_verified | primary_result |
| funding/BTCUSDT min_oos_trades_met veto | 10/10 OK | `funding/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.rejections.depends_on_few_trades` | reporter_verified | primary_result |
| funding/BTCUSDT median OOS return | -0.4091438240259256 | `funding/study_robustness.json` | `by_symbol_and_engine.BTCUSDT|random_search.median_total_return` | reporter_verified | primary_result |
| funding/BTCUSDT median OOS Sharpe | -0.2688538431059223 | `funding/study_robustness.json` | `per_run[].strategy.sharpe` | reporter_verified | primary_result |
| funding/BTCUSDT median buy-and-hold return | 0.522747844787544 | `funding/study_robustness.json` | `by_symbol_and_engine.BTCUSDT|random_search.median_buy_and_hold_return` | reporter_verified | primary_result |
| funding/BTCUSDT family verdict | REJECTED | `r3_family_rollup.json` | `families.funding.analysis.verdict` | reporter_verified | primary_result |
| funding/ETHUSDT C1 positive return | 1/10 FAIL | `funding/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.positive_total_return` | reporter_verified | primary_result |
| funding/ETHUSDT C2 bootstrap Sharpe CI | 0/10 FAIL | `funding/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.bootstrap_sharpe_ci_excludes_zero` | reporter_verified | primary_result |
| funding/ETHUSDT C3 survives 2x costs | 1/10 FAIL | `funding/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.survives_double_costs` | reporter_verified | primary_result |
| funding/ETHUSDT C4 beats buy-and-hold | 1/10 FAIL | `funding/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.beats_buy_and_hold` | reporter_verified | primary_result |
| funding/ETHUSDT C5 drop top 5 trades | 0/10 FAIL | `funding/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.survives_drop_top_trades` | reporter_verified | primary_result |
| funding/ETHUSDT C6 fold locality | 10/10 OK | `funding/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.not_confined_to_one_fold` | reporter_verified | primary_result |
| funding/ETHUSDT min_oos_trades_met veto | 10/10 OK | `funding/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.rejections.depends_on_few_trades` | reporter_verified | primary_result |
| funding/ETHUSDT median OOS return | -0.5993944568161564 | `funding/study_robustness.json` | `by_symbol_and_engine.ETHUSDT|random_search.median_total_return` | reporter_verified | primary_result |
| funding/ETHUSDT median OOS Sharpe | -0.31523602254726624 | `funding/study_robustness.json` | `per_run[].strategy.sharpe` | reporter_verified | primary_result |
| funding/ETHUSDT median buy-and-hold return | -0.2190192992677874 | `funding/study_robustness.json` | `by_symbol_and_engine.ETHUSDT|random_search.median_buy_and_hold_return` | reporter_verified | primary_result |
| funding/ETHUSDT family verdict | REJECTED | `r3_family_rollup.json` | `families.funding.analysis.verdict` | reporter_verified | primary_result |
| funding GA-RS paired mean difference | 0.11589817669881798 | `r3_family_rollup.json` | `families.funding.analysis.paired_ga_minus_rs.mean_difference` | reporter_verified | secondary_diagnostic |
| funding GA-RS 95% CI | [-0.22696783230639356, 0.4587641857040295] | `r3_family_rollup.json` | `families.funding.analysis.paired_ga_minus_rs` | reporter_verified | secondary_diagnostic |
| BTC_ETH_confirmation/BTCUSDT C1 positive return | 1/10 FAIL | `BTC_ETH_confirmation/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.positive_total_return` | reporter_verified | primary_result |
| BTC_ETH_confirmation/BTCUSDT C2 bootstrap Sharpe CI | 0/10 FAIL | `BTC_ETH_confirmation/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.bootstrap_sharpe_ci_excludes_zero` | reporter_verified | primary_result |
| BTC_ETH_confirmation/BTCUSDT C3 survives 2x costs | 0/10 FAIL | `BTC_ETH_confirmation/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.survives_double_costs` | reporter_verified | primary_result |
| BTC_ETH_confirmation/BTCUSDT C4 beats buy-and-hold | 0/10 FAIL | `BTC_ETH_confirmation/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.beats_buy_and_hold` | reporter_verified | primary_result |
| BTC_ETH_confirmation/BTCUSDT C5 drop top 5 trades | 0/10 FAIL | `BTC_ETH_confirmation/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.survives_drop_top_trades` | reporter_verified | primary_result |
| BTC_ETH_confirmation/BTCUSDT C6 fold locality | 9/10 OK | `BTC_ETH_confirmation/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.promotion.not_confined_to_one_fold` | reporter_verified | primary_result |
| BTC_ETH_confirmation/BTCUSDT min_oos_trades_met veto | 10/10 OK | `BTC_ETH_confirmation/study_robustness.json` | `r3_promotion.by_symbol.BTCUSDT.rejections.depends_on_few_trades` | reporter_verified | primary_result |
| BTC_ETH_confirmation/BTCUSDT median OOS return | -0.6578855699743127 | `BTC_ETH_confirmation/study_robustness.json` | `by_symbol_and_engine.BTCUSDT|random_search.median_total_return` | reporter_verified | primary_result |
| BTC_ETH_confirmation/BTCUSDT median OOS Sharpe | -0.5486058697854144 | `BTC_ETH_confirmation/study_robustness.json` | `per_run[].strategy.sharpe` | reporter_verified | primary_result |
| BTC_ETH_confirmation/BTCUSDT median buy-and-hold return | 0.522747844787544 | `BTC_ETH_confirmation/study_robustness.json` | `by_symbol_and_engine.BTCUSDT|random_search.median_buy_and_hold_return` | reporter_verified | primary_result |
| BTC_ETH_confirmation/BTCUSDT family verdict | REJECTED | `r3_family_rollup.json` | `families.BTC_ETH_confirmation.analysis.verdict` | reporter_verified | primary_result |
| BTC_ETH_confirmation/ETHUSDT C1 positive return | 0/10 FAIL | `BTC_ETH_confirmation/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.positive_total_return` | reporter_verified | primary_result |
| BTC_ETH_confirmation/ETHUSDT C2 bootstrap Sharpe CI | 0/10 FAIL | `BTC_ETH_confirmation/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.bootstrap_sharpe_ci_excludes_zero` | reporter_verified | primary_result |
| BTC_ETH_confirmation/ETHUSDT C3 survives 2x costs | 0/10 FAIL | `BTC_ETH_confirmation/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.survives_double_costs` | reporter_verified | primary_result |
| BTC_ETH_confirmation/ETHUSDT C4 beats buy-and-hold | 0/10 FAIL | `BTC_ETH_confirmation/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.beats_buy_and_hold` | reporter_verified | primary_result |
| BTC_ETH_confirmation/ETHUSDT C5 drop top 5 trades | 0/10 FAIL | `BTC_ETH_confirmation/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.survives_drop_top_trades` | reporter_verified | primary_result |
| BTC_ETH_confirmation/ETHUSDT C6 fold locality | 10/10 OK | `BTC_ETH_confirmation/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.promotion.not_confined_to_one_fold` | reporter_verified | primary_result |
| BTC_ETH_confirmation/ETHUSDT min_oos_trades_met veto | 10/10 OK | `BTC_ETH_confirmation/study_robustness.json` | `r3_promotion.by_symbol.ETHUSDT.rejections.depends_on_few_trades` | reporter_verified | primary_result |
| BTC_ETH_confirmation/ETHUSDT median OOS return | -0.6830202449583207 | `BTC_ETH_confirmation/study_robustness.json` | `by_symbol_and_engine.ETHUSDT|random_search.median_total_return` | reporter_verified | primary_result |
| BTC_ETH_confirmation/ETHUSDT median OOS Sharpe | -0.2976629359260061 | `BTC_ETH_confirmation/study_robustness.json` | `per_run[].strategy.sharpe` | reporter_verified | primary_result |
| BTC_ETH_confirmation/ETHUSDT median buy-and-hold return | -0.2190192992677874 | `BTC_ETH_confirmation/study_robustness.json` | `by_symbol_and_engine.ETHUSDT|random_search.median_buy_and_hold_return` | reporter_verified | primary_result |
| BTC_ETH_confirmation/ETHUSDT family verdict | REJECTED | `r3_family_rollup.json` | `families.BTC_ETH_confirmation.analysis.verdict` | reporter_verified | primary_result |
| BTC_ETH_confirmation GA-RS paired mean difference | 0.1644040939020623 | `r3_family_rollup.json` | `families.BTC_ETH_confirmation.analysis.paired_ga_minus_rs.mean_difference` | reporter_verified | secondary_diagnostic |
| BTC_ETH_confirmation GA-RS 95% CI | [-0.08440529119545132, 0.4132134789995759] | `r3_family_rollup.json` | `families.BTC_ETH_confirmation.analysis.paired_ga_minus_rs` | reporter_verified | secondary_diagnostic |
| Units completed | 100/100 | `*/status.json` | `completed` | reporter_verified | primary_result |
| Numerical discrepancies | 0 | `reporter consistency battery` | `n/a` | reporter_verified | primary_result |
| Gate R3 status | CLOSED_NEGATIVE | `r3_gate_verdict.json` | `gate_status` | reporter_verified | primary_result |
| Families promoted | 0 | `r3_gate_verdict.json` | `n_promoted` | reporter_verified | primary_result |
| Isolation audit at R3 closure | 100/100 audited; failures=0 | `r3_scientific_closure_report.json` | `isolation_audit` | documentary | secondary_diagnostic |
| R4 required at closure | False | `r3_gate_verdict.json` | `r4_required` | reporter_verified | primary_result |
| R4 application status | SKIPPED (zero R3 promotions at closure) | `docs/decisions/0015-r3-family-evaluation-negative.md` | `Decision item 3` | documentary | secondary_diagnostic |
| Historical holdout status | Frozen holdout not opened during Gate R3 (documented at closure) | `docs/decisions/0015-r3-family-evaluation-negative.md` | `Decision item 4` | documentary | limitation |
| Provenance state tracked_state_1 | {"commit": "aac33577c14cba08f349381ce3566eca0c587299", "diff_bytes": 66986, "diff_sha256": "0378645e31c35f0b988d1a57eefb6dcbed9517e513d6d50cf739c1e8d89534de", "dirty": true, "families": ["BTC_ETH_confirmation"], "provisional": true, "reproducible_from_commit_alone": false, "state_id": "tracked_state_1", "untracked_sha256": "97ca909987a70b14c7e7f71095e4b5c068ae8348d70df39f385c3990ae265d50"} | `*/run_identity.json` | `worktree.diff_sha256` | limitation | limitation |
| Provenance state tracked_state_2 | {"commit": "aac33577c14cba08f349381ce3566eca0c587299", "diff_bytes": 45647, "diff_sha256": "4073dba60103de8d7a4ea99a901296fab9f1a4b7d6c4228d65037e6a984f2e9b", "dirty": true, "families": ["breakout", "funding", "mean_reversion", "volatility_breakout"], "provisional": true, "reproducible_from_commit_alone": false, "state_id": "tracked_state_2", "untracked_sha256": "97ca909987a70b14c7e7f71095e4b5c068ae8348d70df39f385c3990ae265d50"} | `*/run_identity.json` | `worktree.diff_sha256` | limitation | limitation |

## Provenance limitation

Executed code cannot be reconstructed exactly from commit(s) `aac33577c14cba08f349381ce3566eca0c587299` alone: every family run_identity.json records worktree.dirty=true; every family records reproducible_from_commit_alone=false; 2 distinct tracked diff states observed across families; patch bytes were not retained in persisted run_identity.json artifacts

| State | Families | Commit | diff_sha256 | diff_bytes | untracked_sha256 | dirty |
|---|---|---|---|---|---|:---:|
| tracked_state_1 | BTC_ETH_confirmation | `aac33577c14cba08f349381ce3566eca0c587299` | `0378645e31c35f0b988d1a57eefb6dcbed9517e513d6d50cf739c1e8d89534de` | 66986 | `97ca909987a70b14c7e7f71095e4b5c068ae8348d70df39f385c3990ae265d50` | True |
| tracked_state_2 | breakout, funding, mean_reversion, volatility_breakout | `aac33577c14cba08f349381ce3566eca0c587299` | `4073dba60103de8d7a4ea99a901296fab9f1a4b7d6c4228d65037e6a984f2e9b` | 45647 | `97ca909987a70b14c7e7f71095e4b5c068ae8348d70df39f385c3990ae265d50` | True |

Dirty-worktree provenance limits exact code reconstruction; it is distinct from the numerical consistency checks performed by this reporter and from the persisted gate verdict.
