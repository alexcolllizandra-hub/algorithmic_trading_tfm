# Chapter 8 — Conclusions

Research questions **RQ1–RQ5** and hypotheses **H1–H5** are defined in `docs/methodology/experimental_design.md` and traced in `hypothesis_matrix.md`.

## 8.1 General objective

**Objective:** discover and validate interpretable strategies on BTC/ETH USDT-M perpetuals under strict temporal discipline, explicit costs and reproducible tracking.

**Conclusion:** No interpretable strategy was **promotion-eligible** under the executed contract (R1 corrected protocol; R2 rejected momentum; R3 **0/5**; R4 **SKIPPED**; holdout closed). The thesis delivers methodological, empirical and engineering contributions: leakage correction, documented promotion gates, auditable negative evidence and a versioned pipeline.

## 8.2 Specific objectives and traceability

### Table 8.1 — Objectives / questions → evidence → conclusion

| Objective or question | Evidence | Conclusion |
|-----------------------|----------|------------|
| **General** — validate interpretable strategies net of costs | R1–R3; ADR 0012, 0013, 0015; thesis_report | Not promotion-eligible; positive methodological contribution |
| **RQ1** — profitability after costs | ADR 0013 (0/40 momentum); R3 0/5 | **No** |
| **RQ2** — GA vs RS | ADR 0013: GA−RS −0.061, CI includes 0 | **No systematic GA superiority** |
| **RQ3** — meta-labeling | M1/M2 not started | **Not evaluated** |
| **RQ4** — regime dependence | Descriptive EDA regimes (Ch. 3); R4 SKIPPED | **Not confirmatorily tested** |
| **RQ5** — robustness under stress | Partial R3 criteria (C2–C5); R4 SKIPPED | **Partially addressed**; does **not** confirm H5 |
| **H1** | ADR 0013, 0015 | **Rejected** |
| **H2** | ADR 0013 | **No GA advantage evidence** |
| **H3** | M1/M2 not started | **Not evaluated** |
| **H4** | EDA descriptive; no confirmatory gate | **Not confirmatorily tested** |
| **H5** | Zero promotions; R4 SKIPPED | **Not evaluable** |
| **R1** | ADR 0012 | Contamination **corrected** |
| **R2** | ADR 0013 | Momentum **rejected** |
| **R3** | ADR 0015 | **CLOSED_NEGATIVE**, 0/5 |
| **volatility_breakout/BTC** | thesis_report | Partial non-robust signal; **not approved** |
| **R4** | ADR 0015 | **SKIPPED** |
| **Holdout** | ADR 0003 | **Remains closed** |

## 8.3 Contributions

**Methodological:** per-fold search correction (R1); six-criterion promotion plus separate veto; explicit R1–R4 gates.

**Empirical:** clean momentum rejection (0/40); five-family homogeneous evaluation (100/100 units, 0/5 promotions); honest recording of partial VB/BTC signal.

**Engineering/reproducibility:** typed pipeline, offline tests, read-only R3 reporter with full read manifest and reporter_verified vs documentary claims.

## 8.4 Limitations

BTC/ETH USDT-M 1h only; development through 2025-12-31; provisional costs; multiple-comparison risk in development; dirty R3 provenance limiting exact code replay; holdout unused (no candidate); RQ3, confirmatory RQ4/RQ5 extended scope not executed.

## 8.5 Future work

Gate **S1** for new pre-specified families; **M1/M2** for meta-labeling; asset/period/frequency extensions; single holdout opening only with frozen candidate.

## 8.6 Final conclusion

R1 restored temporal validity; R2 rejected momentum; R3 closed with zero promotions; R4 was **not executed**; holdout stays closed; GA superiority was **not demonstrated**. **volatility_breakout/BTC** showed a partial non-robust signal, not an approved strategy. The thesis contributes a reproducible, auditable framework and a rigorous **negative** empirical arc — a valid Data Science Master's outcome.
