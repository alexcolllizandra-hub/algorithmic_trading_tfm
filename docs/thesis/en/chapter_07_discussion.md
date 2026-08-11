# Chapter 7 — Discussion

## 7.1 Interpreting the negative outcome

Under a corrected temporal protocol, a rejected momentum baseline, homogeneous search budgets and six promotion criteria plus a trade-count veto, **no interpretable family qualified for promotion**. This is a **valid scientific outcome**: a rigorous null result is preferable to a positive result obtained through leakage or undisclosed search.

The negative result **does not prove** alpha is impossible in these markets; it **bounds** what was **not supported** under this contract, period, frequency and asset pair.

## 7.2 Internal validity

Strengths include chronological splits, holdout isolation by design, documented correction of outer-fold contamination (R1), budget parity, multi-seed replication and read-only R3 reporting with zero numerical contradictions across artifacts.

Residual threats include multiple comparisons across five families and ten seeds, provisional cost assumptions, and development-only inference without a final holdout opening (no promoted candidate).

Dirty-worktree provenance limits exact reconstruction from commit alone; it is **separate** from the verified numerical coherence of persisted JSON artifacts.

## 7.3 External and construct validity

Results apply to BTC/ETH USDT-M 1h perpetuals over 2020–2025 development geometry. Rejected families indicate the **implemented operationalisations** did not achieve stable net OOS performance, not necessarily that broader economic narratives are false.

## 7.4 Random Search versus Genetic Algorithm

R2 under the clean protocol: GA−RS = −0.061, CI includes zero (ADR 0013). R3 paired comparisons are diagnostic only; GA does **not** decide promotion. **No sufficient evidence** supports systematic GA superiority.

## 7.5 BTC versus ETH

Reference buy-and-hold medians differ (+52.3% BTC vs −21.9% ETH on aggregated development OOS; thesis report). Strategy medians are predominantly negative on both assets; ETH shows more negative extremes (e.g. mean reversion −79.9%).

*Interpretive hypothesis (not isolated causal test):* divergent underlying drift between assets might penalise directional strategies with limited sign adaptation; this was **not** subjected to a dedicated causal experiment.

No family satisfied promotion on **both** assets simultaneously.

## 7.6 Costs, trade-count veto and partial robustness

Criteria C3 and C5 target cost fragility and trade concentration. The **min_oos_trades_met veto was not the primary rejection driver** (10/10 on most rows); failures concentrated in C1, C2, C4 and negative median returns.

Partial robustness checks in R3 (bootstrap CI, doubled costs, drop-top-5) **do not confirm H5**, which requires a **promoted** strategy under the extended battery (R4).

## 7.7 Why R4 was not executed

R4 is confirmatory on **promoted** families only. Applying it after universal R3 rejection would risk retrospective “rescue” of rejected families, forbidden by the protocol (phase_gates § R4; ADR 0015).

## 7.8 Future work

New hypotheses must enter as **Gate S1** — pre-specified, independent, without retuning rejected R3 families. Meta-labeling only under M1/M2 contracts. Holdout opens **once**, only with a strategy frozen beforehand — condition not met here.
