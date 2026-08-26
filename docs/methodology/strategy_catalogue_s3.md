# Gate S3 — batch 01: macro-event risk gating (pre-specification)

**Status: FROZEN before any backtest of this family.** This document is the
registered hypothesis for Gate S3. It follows the S1 discipline (ADR 0016):
the family, its parameter space and its evaluation contract are fixed here,
before the first pilot bar is simulated. Executing S3 adds one family to the
study's trial count; every study-level multiple-testing correction that
includes S3 must use N := N + 1.

## Family: `macro_event_brake`

### Economic hypothesis

Scheduled US macro releases (CPI prints, FOMC decisions) are the most
predictable volatility events in the development window: the descriptive
annex (`docs/thesis/anexo_altdata.md`, figures A3-A4) measured 2.5-3.2 times
the absolute hourly return of seasonality-matched non-event hours
(permutation p < 0.001), with elevated volatility persisting two to three
hours — while showing **no** exploitable directional drift. If macro event
windows contain outsized, directionless variance, then a simple directional
carrier should have a better net risk-adjusted profile when it is **flat**
inside those windows: same directional exposure elsewhere, less exposure to
unpriceable event risk.

The hypothesis is therefore about **risk gating, not signal generation**: the
carrier is the study's best-understood failed family (momentum crossover,
Gates R2-R3), and the only new ingredient is the calendar gate. If the gated
variant does not improve on the carrier, calendar awareness at this frequency
adds nothing that survives costs.

### Why this is a distinct hypothesis

No family evaluated at R3/S1/S2 conditions on the macro calendar. The event
times are exogenous, scheduled, and known days in advance (BLS and Federal
Reserve publish them), so the gate is trivially causal: membership of bar *t*
in an event window is known before the window opens. The gate uses the frozen
committed calendar `configs/altdata/us_macro_events.csv` (71 CPI releases,
49 FOMC decisions, 2020-2025, per-row source URLs); the calendar was curated
from official schedules and is versioned with the repository.

### Strategy definition

Base carrier: the R2/R3 momentum crossover (fast/slow SMA, next-open
execution, optional trend and regime gates — unchanged semantics). New
behaviour: the target position is forced to 0 for every bar whose interval
intersects `[event - pre_bars hours, event + post_bars hours]` for the
selected event set. Re-entry after the window follows the carrier's signal.

### Parameter space (frozen)

| Parameter | Values | Notes |
|---|---|---|
| `fast` | 12, 24 | carrier fast SMA (subset of the R2 grid) |
| `slow` | 96, 168 | carrier slow SMA |
| `event_set` | `cpi`, `fomc`, `both` | which calendar rows gate |
| `pre_bars` | 1, 2, 4 | hours flat before the event |
| `post_bars` | 2, 4, 8 | hours flat after the event |
| `direction` | long, short, both | shared study parameter |
| `use_regime_gate` | on/off + shared gate options | shared study parameter |

Cardinality: 2·2·3·3·3·3·(1+3) = 2,592 raw combinations; the standard
effective budget (100 unique candidates per fold and engine) samples it
exactly as every other family.

### Evaluation contract (identical to R3/S1-C, no deviations)

BTCUSDT + ETHUSDT · 10 seeds from base seed 42 · 15 expanding folds ·
purge/embargo derived (96/118 bars) · costs 4+1 bps per side + realized
funding · Random Search confirmatory, GA diagnostic, budget parity on unique
candidates · promotion requires all six frozen criteria (C1-C6) per
family×asset cell · the final holdout is never loaded.

### Falsifiable predictions (written before execution)

1. The gate reduces realized OOS volatility of the carrier (mechanical).
2. Promotion still requires C1-C6; given that the ungated carrier failed
   R2/R3 decisively, the honest prior is **no promotion** — the informative
   outcome is whether the gated variant's seed distribution shifts relative
   to the R2 momentum baseline, which the closure report must state either way.

### What would count as a partial signal

A majority of seeds with higher OOS Sharpe than the corresponding ungated
momentum cell, recorded and reported without unlocking anything — exactly the
S1 partial-signal semantics.
