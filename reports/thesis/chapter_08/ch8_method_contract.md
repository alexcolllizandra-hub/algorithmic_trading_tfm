# CH8 method contract

## Status of each methodological element

| Element | Status |
|---|---|
| Stationary block bootstrap (Politis–Romano) as resampling core | FROZEN precedent (notebook 07, executed before this package) |
| Block length from `suggest_block_length` (last ACF lag above the 2/√n band, clipped to [6, 168]) | FROZEN heuristic (notebook 07; documented as heuristic, ACF inspectable) |
| Block trio 24/168/720 for sensitivity | FROZEN (C2 gate, `study_robustness.BLOCK_SIZES`) |
| Median-by-return seed rule wherever ONE seed is needed | FROZEN (notebook 07, fixed before reading results) |
| IID-trade bootstrap / order permutation secondaries | FROZEN precedent (notebook 07) |
| Prop-firm account configs (Table 8.7) | FROZEN (notebook 07, published rules); ONLY the already-executed results are cited |
| Per-seed path-uncertainty layer (all 10 seeds) | RETROSPECTIVE (post-hoc diagnostic) |
| Hierarchical seed-then-path scheme | RETROSPECTIVE |
| Exposure multiplier grid 0.25–2.00 and absorption rule | RETROSPECTIVE |
| Capital barriers 90/80/70/50% and loss/MDD ladders | RETROSPECTIVE |
| Drawdown-duration, time-under-water, recovery metrics | RETROSPECTIVE (not defined anywhere in the code base before this package) |
| Circular moving-block bootstrap as method sensitivity | RETROSPECTIVE |
| Block-of-consecutive-trades bootstrap (block = round(√n_trades)) | RETROSPECTIVE |
| Budgets (1,000 / 4,000 / 2,000) and master seed 20260829 | RETROSPECTIVE, declared before running |

## Formal definitions

- **Wealth**: W_t = ∏_{i≤t} (1 + r_i), W_0 = 1. Every simulated path has
  exactly 32,385 observations (the OOS horizon).
- **Exposure scaling**: r_t^{(m)} = m · r_t. This is a RETURN MULTIPLIER, not
  "risk per trade" and not stop-based sizing (both are NOT EVALUATED: the
  ledgers persist no initial stop or monetary risk). **Absorption rule**: if
  1 + m·r_t ≤ 0 at any bar, the account is absorbed at zero at that bar —
  terminal 0, drawdown 1, every barrier crossed, no recovery.
- **Maximum drawdown**: max_t (1 − W_t / max_{s≤t} W_s), reported as a
  positive magnitude (the code's `path_metrics` uses the negative convention;
  chapter 7's `max_drawdown` column is negative).
- **Drawdown duration**: the longest contiguous run of bars with W_t strictly
  below the running peak (bars; days = bars/24). **Time under water**: share
  of such bars. **Recovery**: whether W regains the pre-trough peak before the
  horizon ends.
- **Capital breach**: min_t W_t < barrier. **Ruin/absorption**: W reaches 0
  under the absorption rule (distinct from the prop-firm loss-limit "ruin" of
  notebook 07).
- **Trade concentration shares**: top-k share = Σ of the k largest positive
  trade returns / Σ of all positive trade returns. Concentration index =
  Herfindahl over positive-trade shares. Removal columns recompute the
  compounded product over the remaining trades (`drop_best_trades`, the same
  convention as the chapter-7 criterion) — causal, no double costs.
- **Hierarchical scheme**: draw seed s uniformly from the 10, then resample
  that seed's OOS series with the primary method. It mixes search and path
  sensitivity in ONE diagnostic; it does NOT represent ten independent market
  replications, because all seeds share the same market history.

## Determinism

Master seed 20260829. Each scenario uses
`SeedSequence([master, blake2b(key)])` with
key = candidate|scenario|method|block|seed-mode|chunk-index, so results are
independent of execution order and chunking is part of the key. Notebook-07
results cited in Table 8.7 keep their own frozen seed (42).

## Interpretation contract

All simulated ranges are **conditional simulation intervals** on the observed
development record. They quantify path and search sensitivity GIVEN that
record; they are not confidence intervals on a true edge, they do not correct
selection/data-snooping, they cannot promote any rejected strategy, and they
leave every chapter-7 verdict untouched.
