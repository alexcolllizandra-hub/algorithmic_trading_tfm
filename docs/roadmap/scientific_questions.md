# Scientific question map

**Version:** 1.0 · **Date:** 2026-08-08

This document answers one question: **why does each strategy family exist?**

Every family must trace back to a measured property of the data. A family with no
traceable motivation is indicator mining, and this document is where that becomes
visible.

Related: [current state](current_state.md) · [master roadmap](master_roadmap.md) ·
[phase gates](phase_gates.md) · [future architecture](future_architecture.md)

---

## The chain

```
EDA finding → hypothesis → features → strategy family → experiment → result
```

Each link must be documented **before** the next is built. Inventing the
motivation after seeing a result is the failure mode this chain prevents.

**Source of the EDA figures below:** `reports/tables/eda/` on the development
period 2020-01-01 … 2025-12-31, 1h bars, holdout excluded. These are
**full-sample descriptive statistics** and are used only to motivate hypotheses —
never as model inputs or decision thresholds. Causal, rolling versions are
recomputed inside each training window.

---

## Measured EDA findings

Ten findings were recorded in `reports/tables/eda/s6_main_findings.md`. The ones
that drive strategy design:

| ID | Finding | Key measured values |
|---|---|---|
| **F2** | Returns are heavy-tailed and leptokurtic with near-zero mean | Kurtosis falls with aggregation |
| **F3** | Large historical VaR/ES; deep multi-week drawdowns; lower tail ≥ upper | — |
| **F4** | Strong volatility clustering; ARCH-LM rejects homoscedasticity | — |
| **F5** | **Raw-return autocorrelation is negligible; \|r\| and r² are persistent** | BTC lag-1 ACF: raw **−0.0174**, \|r\| **0.296**, r² **0.169**; ETH: raw **−0.0075**, \|r\| **0.283**, r² **0.183** |
| **F6** | Activity is coincident with \|return\|, weaker as a predictor | Spearman(volume, \|r\|) 1h: BTC **0.528**, ETH **0.463**; one-lag predictive: BTC **0.314**, ETH **0.242** |
| **F7** | Funding is small, mostly positive, heavy-tailed and **persistent** | Share positive: BTC **87.5 %**, ETH **88.3 %**; mean **1.17 / 1.40 bps**; ACF lag-1 **0.796 / 0.786**; mean run length **≈ 8** settlements |
| **F8** | BTC-ETH are strongly dependent, more so in the tails, with **no lead-lag** | 1h Pearson **0.839**, Spearman **0.820**; lower-tail co-exceedance **13.15×**, upper **11.26×**; **peak lead-lag at lag 0** |
| **F10** | Volatility regimes are persistent and transition gradually | Full-sample thresholds; provisional |

---

## Map: finding → hypothesis → family

### F5 → the constraint that shapes everything

> **Raw returns carry almost no linear autocorrelation, but their magnitude is
> strongly persistent.**

Lag-1 ACF of raw 1h returns is **−0.017 (BTC)** and **−0.008 (ETH)** — economically
zero. Meanwhile \|r\| has ACF **0.296 / 0.283**.

**Hypothesis H-F5.** Simple linear trend-following on raw returns should **not**
work. What is predictable is *volatility*, not *direction*.

**Consequences.**

* Momentum is included as a **falsifiable baseline**, not a favourite. F5 predicts
  it fails.
* Families that condition on *magnitude* (volatility breakout, squeeze) are
  better motivated than families that extrapolate *direction*.
* Any family claiming linear return predictability carries a higher burden of
  proof.

**Status: H-F5 is supported so far.** The momentum multi-seed study
([FR-1](current_state.md#fr-1--momentum-has-no-demonstrated-edge)) found no edge —
0/10 seeds positive on BTC, median OOS return −0.47 against buy-and-hold +0.78.
**This is EDA correctly predicting an experimental outcome**, which is the
strongest form of evidence this project has produced so far.

| Family | Relationship to F5 |
|---|---|
| Momentum | Falsifiable baseline; predicted to fail; **it did** |
| Volatility breakout | Motivated: trades magnitude persistence |
| Squeeze (future) | Motivated: contraction → expansion |
| Classical trend indicators (MACD, ROC, ADX) | **Weakly motivated** — they restate directional extrapolation that F5 argues against |

### F4 + F10 → volatility clustering and regimes

> Volatility clusters strongly and regimes persist with gradual transitions.

**Hypothesis H-F4.** Because volatility is persistent, periods of compression
predict periods of expansion, and the *size* of a move is forecastable even when
its *sign* is not.

| Element | Status |
|---|---|
| Features | `rvol_*`, `roll_std_*`, `atr_*` — implemented |
| Family | **Volatility Breakout** (`VolatilityBreakout`) — implemented, piloted |
| Future family | Volatility contraction → expansion (squeeze) — specified |
| Future use | Regime conditioning and regime switching — specified |

**Mechanism.** Enter when price clears the prior range by an ATR-scaled margin,
so the trigger adapts to the current volatility state instead of a fixed
threshold.

**Caveat.** The regime thresholds in the EDA are full-sample and explicitly
descriptive. Causal regime models are refitted on each fold's training window —
this is enforced in `build_folds_data`.

### F7 → funding persistence

> Funding is positive ~88 % of the time, averages ~1.2–1.4 bps, and is highly
> persistent (ACF lag-1 ≈ 0.79, mean run length ≈ 8 settlements).

**Hypothesis H-F7.** Persistent funding reflects persistent positioning. Two
readings, and they conflict:

* **Fade:** extreme funding marks crowding that resolves against the crowd.
* **Follow:** persistent funding marks a genuine directional regime.

The `FundingTilt` family exposes `stance ∈ {fade, follow}` precisely so the data
decides rather than the researcher.

| Element | Status |
|---|---|
| Feature | `funding_rate` — implemented |
| Family | **Funding** (`FundingTilt`) — implemented, piloted |
| Future | Funding + momentum; funding + basis proxy — specified |

**Important caveat from F7.** The EDA found only a **weak leak-free link between
funding and future returns**. Funding is unambiguously a **cost**; whether it is a
*signal* is exactly what the experiment must decide. The pilot's Sharpe of −1.09
(RS) / −0.91 (GA) is not evidence either way — it is one contaminated seed.

### F8 → BTC-ETH dependence

> 1h Pearson **0.839**, tail co-exceedance **13×**, and **peak lead-lag at lag 0**.

**Hypothesis H-F8.** The assets are strongly contemporaneously dependent but
**neither reliably leads the other**.

**This finding constrains the family more than it motivates it.** Lead-lag at lag
zero means a naive "BTC moves, then ETH follows" strategy has no measured basis.
`CrossAssetConfirmation` therefore enforces `MIN_REFERENCE_LAG = 1` — it can only
use information genuinely available beforehand — and offers three modes:

| Mode | Hypothesis |
|---|---|
| `agree` | Confirmation reduces false signals even without lead-lag |
| `lead_lag` | Residual predictability exists at ≥1 bar despite peak at lag 0 |
| `divergence` | Temporary decoupling mean-reverts |

**Honest assessment.** F8 offers *weak* support for `lead_lag`, *moderate* support
for `agree`, and the most support for `divergence`. This should be stated when
the family is evaluated.

**Second consequence.** Correlation ≈ 0.84 means **BTC and ETH are not two
independent bets.** This is why the multi-seed analysis uses symbol × fold units
and why a future portfolio layer must be correlation-aware.

### F6 → activity and order flow

> Volume correlates with contemporaneous \|return\| (Spearman ≈ 0.53 BTC / 0.46
> ETH) but predicts next-bar \|return\| more weakly (0.31 / 0.24).

**Hypothesis H-F6.** Aggressive participation distinguishes a genuine breakout
from noise — a **confirmation filter**, not a standalone signal.

| Element | Status |
|---|---|
| Features | `rel_volume`, `volume_zscore` (extended); `taker_buy_ratio`, `taker_buy_imbalance` (**experimental, flagged proxies**) |
| Future family | Breakout + taker-flow confirmation — specified |

**Caveat.** The measured *predictive* correlation is materially weaker than the
contemporaneous one. Order-flow features are declared proxies, not true order
book data. Claims must stay modest.

### F2 + F3 → tails and risk

> Heavy tails, large VaR/ES, deep drawdowns, lower tail ≥ upper.

These do **not** motivate a strategy family. They constrain **evaluation**:

| Consequence | Where it applies |
|---|---|
| Avoid Gaussian assumptions | Bootstrap CIs rather than parametric intervals |
| Report tail metrics | VaR/ES at 95 % and 99 %, skewness, excess kurtosis — implemented |
| Concentration matters | `drop_best_trades`, `concentration_analysis` — implemented |
| Distribution-free tests | **Not yet implemented** — Gate R4 |
| Tail-aware sizing | Future risk layer |

Under heavy tails a Sharpe ratio is a weak summary. This is why promotion
requires a bootstrap CI excluding zero rather than a point estimate.

---

## Coverage: which findings drive which family

| EDA finding | Family motivated | Family status |
|---|---|---|
| F5 (no linear predictability) | Momentum — as falsification | `MULTI-SEED`, **negative — as predicted** |
| F4/F10 (vol clustering, regimes) | Volatility Breakout | `PILOTED` |
| F4/F10 | Squeeze | Specified |
| F7 (funding persistence) | Funding | `PILOTED` |
| F8 (cross-asset dependence) | BTC-ETH Confirmation | `PILOTED` |
| F6 (activity ↔ \|return\|) | Breakout + flow confirmation | Specified |
| F2/F3 (tails) | *none — constrains evaluation* | Battery implemented |

### Families with weaker EDA motivation

Honesty requires naming these.

| Family | Motivation | Assessment |
|---|---|---|
| **Breakout** (Donchian) | Related to F4 via range dynamics, but not directly derived from a measured finding | Standard baseline. Its inclusion is **conventional, not evidence-driven** — state this when reporting. |
| **Mean Reversion** (z-score) | F5's slightly negative raw ACF (−0.017) is economically negligible | **Weakly motivated.** Included for coverage of the classical trichotomy. |
| Classical indicators (RSI, MACD, Stochastic, Bollinger, ROC, ADX) | None specific to this dataset | **Not motivated by this project's EDA.** Gated in [Phase S1](master_roadmap.md#phase-s1--controlled-strategy-expansion). If added, the honest motivation is "standard practice", and results must be read against the multiple-comparison burden. |

---

## Research questions and their status

Mapped from `docs/methodology/hypothesis_matrix.md`, updated with actual evidence.

| ID | Question | Status | Evidence |
|---|---|---|---|
| **H1** | Does an interpretable family beat benchmarks net of costs? | **Open — negative so far** | Only momentum tested; 0/40 bootstrap CIs excluded zero |
| **H2** | Does the GA beat Random Search at equal budget? | **Answered: no evidence** | Paired mean +0.183, 95 % CI [−0.053, +0.419]. **Confounded** — see below |
| **H3** | Does meta-labeling improve base signals? | **Unanswerable so far — machinery ready** | No base signal has qualified, so the question has no subject yet. The layer itself is built and validated on synthetic markets ([M1/M2 synthetic validation](m1m2_synthetic_validation.md)); that says nothing about real signals |
| **H4** | Does performance differ across volatility regimes? | **Not started** | Regime models exist; regime-conditional evaluation does not |
| **H5** | Is performance robust to perturbation? | **Partially answered** | Battery covers bootstrap, costs, delay, concentration; parameter perturbation and regime conditioning missing |

### A necessary caveat on H2

The RS-vs-GA comparison is **confounded**. Under the current protocol the GA's
population evolved on a fitness pooled across *all* folds — including folds later
than the one being scored — while Random Search samples independently of fitness
and never received that advantage
([Inconsistency 1](current_state.md#inconsistency-1-outer-fold-contamination-in-candidate-search)).

The bias runs **in the GA's favour**. That the GA still shows no significant
advantage makes "no evidence of a difference" a *conservative* conclusion — but
the point estimate of +0.183 must not be read as a real, merely-underpowered
effect. H2 must be re-answered under the corrected protocol
([Phase R2](master_roadmap.md#phase-r2--re-baseline-momentum-and-the-engine-comparison)).

---

## What EDA does not license

Recorded so future work does not over-claim.

1. **EDA cannot establish an edge.** It is descriptive and full-sample. Only
   walk-forward OOS experiments produce evidence.
2. **Full-sample thresholds are not decision thresholds.** Regime cuts in the EDA
   are illustrative; production regimes are refitted per training window.
3. **Correlation is not a mechanism.** F6's activity–\|return\| relationship is
   coincident; using it predictively requires the weaker one-lag figure.
4. **Absence of lead-lag is a real constraint.** F8 measured peak lead-lag at lag
   0. A cross-asset strategy must justify itself despite this, not pretend
   otherwise.
5. **A finding motivating a family does not predict success.** F7 motivates a
   funding family; whether funding is a *signal* rather than only a *cost* is
   undecided.

---

## Obsidian navigation

The knowledge graph these documents form:

```
EDA finding
  ├── F5 no linear predictability ──→ Momentum (falsified) ──→ FR-1
  ├── F4 volatility clustering ─────→ Volatility Breakout ──→ pilot
  │                              └──→ Squeeze (specified)
  ├── F7 funding persistence ───────→ Funding ─────────────→ pilot
  ├── F8 cross-asset dependence ────→ BTC-ETH Confirmation → pilot
  │                              └──→ correlation-aware Portfolio (specified)
  ├── F6 activity ↔ |return| ───────→ Flow confirmation (specified)
  └── F2/F3 heavy tails ────────────→ Robustness battery + Risk (specified)
```

Each node has a home: findings in `reports/tables/eda/`, families in
`src/perp_lab/strategies/`, results in
[current_state.md](current_state.md#frozen-scientific-results), and gates in
[phase_gates.md](phase_gates.md).
