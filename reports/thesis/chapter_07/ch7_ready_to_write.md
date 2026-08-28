# Chapter 7 — ready-to-write brief (verified figures, per-round conclusions, warnings)

Everything below is verified against the artifacts cited in the MANIFEST at
commit-time; regenerate with `uv run python scripts/build_ch7_results.py`
(deterministic; 44 automatic curve-vs-table consistency checks at tolerance
1e-6 run on every build). Nothing here touches the holdout or runs a new
search.

## Conventions to state once at the top of the chapter

- **Engine**: random_search is the confirmatory engine everywhere; the GA runs
  at identical budget as a cross-check and never decides promotion.
- **OOS window**: concatenated walk-forward test slices, 2022-03-31 to
  2025-12-09, 32,385 hourly bars, both assets. Costs 4+1 bps/side plus
  realized funding as-of-past.
- **Benchmark**: the funded always-long perp on the same bars (real per-bar
  funding + one 5 bps entry). BTC +52.3%, ETH −21.9% over the window. The
  price-only return (+100.7% BTC, +0.9% ETH) is a different quantity and is
  not used anywhere.
- **Two Sharpe aggregations, never mixed**: `sharpe_concat_ann` (annualised,
  bar-weighted, over the concatenated series — Figs 7.2/7.6, units CSV) and
  `mean_fold_test_sharpe` (fold-weighted mean of the 15 fold-test Sharpes —
  Fig 7.5, S3 comparison). They differ numerically by construction.
- **Dispersion, not inference**: spread across the 10 seeds is dispersion
  under search randomness — never a confidence interval, and seeds are not
  independent market histories (identical bars, different search draws).
- **Execution controls**: engine-level = next-bar-open, fees, slippage,
  funding, nothing else. No engine sizing, stops or daily limits; the CRT risk
  engine is implemented but was inactive in every executed round. The only
  active exits are strategy-level (volatility_breakout's trailing ATR stop,
  the CRT trade-management engine, time exits in several S1/S2 families).

## Verified per-round conclusions (cite these numbers)

**R1** — invalid as performance evidence: outer-fold contamination (ADR 0012;
re-scoring the same 60 candidates changed 44 fitness values). Narrate as the
methodological event that produced R2; never cite its metrics.

**R2 momentum** (full study, budget 300/fold/engine, 180,000 evals) — 0/10
seeds positive on either asset (RS). Rejected on the FOUR criteria its
artifact evaluates (positive return, bootstrap CI, 2x costs, beats funded
B&H); drop-top-trades and fold-locality are **not evaluated** for R2 (the
block postdates it) — absent, not failed. Closure dashboard carries
`criteria: null` for momentum.

**R3** (5 families, budget 100, 300,000 evals) — 0/10 promotions. Closest
cell: volatility_breakout BTC, 6/10 seeds positive, mean concatenated Sharpe
+0.11, fails bootstrap-CI (0/10) — Fig 7.3. Activity veto (min 5 OOS trades):
see ch7_activity_veto.csv; it is a disqualifier, never a seventh criterion.

**S1-B** (pilots: BTC, 1 seed, budget 25, 3,000 evals) — mechanical viability
screen passed by all four; no performance case: best one-sided bootstrap p on
the primary engine is **0.7455** (funding_reversal), BH zero rejections, White
RC p 0.9955, Hansen SPA p 1.0. **A p = 0.06 previously attributed to
funding_reversal has no verifiable source and must not appear in the text.**
Full-study S1-C configs exist, never executed.

**S2-B** (pilots: 2 assets × 3 seeds, budget 25, 13,500 evals) — no family
reaches the pre-registered partial-signal bar (majority of seeds positive,
≥5 trades, >1 fold). Pilot rules only; never apply the 10-seed criteria.

**CRT_INTRADAY_V1** (9 families, budget 100, 540,000 evals) — 0/18 cells
promoted; §6bis pre-declared that nothing could be promoted (partition
consumed). Narratable cell: pdl_reclaim_long BTC — 10/10 seeds end positive
(mean concatenated Sharpe ≈ +0.47), 6/10 survive doubled costs, yet 0/10
bootstrap CIs exclude zero and only 2/10 survive dropping the top trades:
profit concentrated in a handful of trades, indistinguishable from luck.
Figs 7.4 and 7.7 (illustrative mechanics; not evidence).

**S3 macro_event_brake** (budget 100, 60,000 evals; N := N+1) — 0/10 seeds
positive. On the **mean fold-test Sharpe** the seed distribution sits below
the carrier's on both assets (BTC −0.71 → −0.99, ETH −0.49 → −0.68). Say ONLY
that; other metrics were not systematically compared. The comparison is not
seed-paired and does not causally isolate the calendar filter (reduced
carrier grid; budget shared with gate parameters). The interesting reading:
a true volatility fact (2.5–3.2× around CPI/FOMC) did not convert into a
tradable return fact.

## Warnings the drafting must respect

1. Closure statistics (Holm/BH, DSR 0.139/1.2e-4, PBO 0.4857, the 496,500
   count) belong to the 13-family universe ONLY. Never extend them to CRT or
   S3; project-wide confirmatory totals are 23 hypotheses / 1,096,500 evals
   with **no** global correction computed.
2. Holdout: do **not** describe the reserved partition `[2026-01-01,
   2026-07-01)` as intact. It was opened once on 2026-08-13 on an
   already-rejected candidate; the reading exists on disk, is UNAUDITED
   (`HOLDOUT_LOCKED`), and is withheld pending the nine-requirement audit in
   `docs/methodology/holdout_audit_status.md`. The opening is a protocol
   deviation recorded in the open — it is not a valid confirmation, and the
   study's conclusion does not depend on it. The partition is consumed for
   any future confirmatory use on this history.
3. Pilots stay pilots: S1-B/S2-B rows carry their own budgets and advance
   rules; the closure counts them as tested hypotheses, not as equally
   powered experiments.
4. Fig 7.7 is illustrative mechanics on one real archived trade chosen by a
   fixed rule (first trade, fold 0, first seed) — a losing trade, on purpose
   not selected by outcome. The engine ledger labels its exit only as
   `signal_close`; CRT-internal exit reasons are not persisted, so none is
   claimed.
5. Every table/figure states engine, assets, seeds, period and aggregation;
   ch7_figure_captions.md carries the English captions with those fields.
