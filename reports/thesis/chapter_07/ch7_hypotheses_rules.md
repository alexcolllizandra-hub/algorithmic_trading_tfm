# Chapter 7 — hypotheses and rules of every executed family (code-verified)

Every statement below was checked against the code, configs and pre-registration
documents cited; nothing is taken from memory. Canonical family names are the
exact strings in `src/perp_lab/search/registry.py` (`FAMILIES`, lines 60–118).
Parameter spaces are NOT in the search YAMLs: defaults live in
`src/perp_lab/config/experiment.py` (Pydantic family classes), a partial
override sits in `configs/experiment.yaml` (`strategies.families` redeclares
only momentum, breakout, mean_reversion and macro_event_brake, with values
identical to the defaults), and the space structure plus cross-parameter
constraints (`repair()`/`validate()`) live only in `registry.py`
(`SPACE_VERSION = "1.1.0"`). The search YAMLs (`configs/search_*.yaml`) carry
the execution contract: family, symbol, seed, budget, GA hyper-parameters.

## Execution controls actually active (all rounds)

`src/perp_lab/backtesting/engine.py`, `run_backtest` (lines ~149–286):
next-bar-open execution, 4 bps taker fee + 1 bps slippage per side on position
changes, realized funding as-of-past. **There is no engine-level position
sizing** (positions are the strategy's ±1, i.e. fixed fraction 1.0, no
leverage, no vol scaling), **no engine-level stop-loss or take-profit, and no
daily-trade limit**. Fields that exist in configuration but are NOT consumed
by the engine — do not attribute them to any experiment: `strategies.stop_loss_atr`,
`take_profit_atr`, `position_sizing` (marked provisional) and the `risk:` block
in `configs/experiment.yaml` (its comment claims the backtester applies it;
the code does not). The CRT risk engine (`src/perp_lab/crt/risk.py`: sizing by
stop distance, max trades per session/level, daily-loss lockouts) is
implemented and tested but **inactive in every executed round**:
`_crt_mechanics()` in `registry.py` never passes `risk=`, so CRT sizing is 1.0
scaled only by partial exits. The only stops that exist anywhere are
signal-level: the `volatility_stop` exit mode of volatility_breakout, and the
CRT trade-management engine described below.

## R1 → R2 (why R1's numbers are not evidence)

ADRs 0011/0012/0013 (`docs/decisions/`). The original evaluator computed each
candidate's fitness on the validation windows of ALL folds at once, so the
search inside fold 0 could see years that fold 0's test had not reached —
outer-fold contamination that favoured the GA (it evolves on fitness; RS
samples blindly). The fix (ADR 0012) isolates the search per outer fold
structurally (`single_fold_bundle`, `FoldIsolationError`), redefines the
dispersion penalty within-fold, and freezes each fold winner by fingerprint
before its single test evaluation. Re-scoring the same 60 candidates changed
44 of 60 fitness values. R1's runs are marked SUPERSEDED, never deleted, and
never cited as results; R2 is the pre-registered clean re-baseline.

## R2 — `momentum` (full study: 2 assets × 10 seeds × 15 folds, budget 300)

Hypothesis: persistent directional drift capturable by an SMA crossover — the
interpretable baseline, not a novel claim. Entry: state (not event): +1 if
`sma_fast > sma_slow`, −1 if below; optional trend gate (`close > sma_{168|336}`)
and regime gate (both only flatten to 0). Exit: opposite crossover inverts the
position; no stop, no target, no time exit. Space (540 exact identities):
`fast ∈ {6,12,24,48}`, `slow ∈ {48,96,168,336}` with `fast < slow`,
`direction ∈ {long,short,both}`, trend filter on/off × {168,336}, regime gate
on/off × 3 sets. Indicators: SMAs on 1h; no HTF aggregation.
Files: `src/perp_lab/strategies/momentum.py` · `configs/search_r2_momentum.yaml`
· `docs/methodology/strategy_specification.md` §1, ADR 0013.

## R3 — five families (full studies, budget 100)

**`breakout`** — Donchian channel: close beyond the previous `channel_window`-bar
range (channel excludes the decision bar), `confirmation_bars` consecutive
closes required; exit on re-entering the channel; opposite entry inverts. No
stop/target/time exit. Space (108): `channel_window ∈ {24,48,96}`,
`confirmation_bars ∈ {1,2,3}`, direction, regime gate. Raw OHLC 1h.
`strategies/breakout.py` · `configs/search_r3_breakout.yaml` · spec §2.

**`mean_reversion`** — z-score of price vs its rolling mean: long at
`z ≤ −entry_z`, short at `z ≥ +entry_z`, exit at `|z| ≤ exit_z < entry_z`. No
stop/target/time exit. Space (432): `zscore_window ∈ {24,48,96}`,
`entry_z ∈ {1.5,2,2.5,3}`, `exit_z ∈ {0,0.5,1}`, direction, gate.
`strategies/mean_reversion.py` · `configs/search_r3_mean_reversion.yaml` · spec §3.

**`volatility_breakout`** — breakout threshold scaled by ATR so "a large move"
means the same in every regime. Entry: close beyond previous `level_window`
extreme ± `entry_atr`·ATR₁₄₋₄₈; optional ATR floor (rolling quantile, never
expanding). Exit: one of three searched modes — re-enter level, opposite break,
or `volatility_stop` = trailing stop at `exit_atr`·ATR from the trade's best
close (**the only price stop among non-CRT families**; a signal-level stop, not
an intrabar fill). Space (7,776): `level_window {24,48,96}`, `atr_window
{14,24,48}`, `entry_atr {0.25,0.5,1.0}`, `exit_atr {0.1,0.25,0.5}` (constraint
`exit_atr < entry_atr` only under volatility_stop), `exit_mode` ×3,
`use_atr_floor` × `min_atr_pct {0.25,0.5}`, direction, gate. Hypothesis lives
in the module docstring (no dedicated catalogue sheet — stated as a gap below).
`strategies/volatility_breakout.py` · `configs/search_r3_volatility_breakout.yaml`.

**`funding`** — the published funding rate as a positioning feature. Entry on
the rolling z-score of funding with searched stance: `fade` (take the side
being paid) or `follow` (take the side that pays); optional `|rate|` floor.
Exit at `|z| ≤ exit_z`. The funding *cashflow* is charged by the engine, never
by the strategy (no double counting). Space (1,296): `signal_window
{24,48,168}`, `entry_z {1,1.5,2}`, `exit_z {0,0.25,0.5}`, `stance ×2`,
`min_abs_rate {0, 5e-5}`, direction, gate. As-of backward join on publication
time. `strategies/funding.py` · `configs/search_r3_funding.yaml`.

**`BTC_ETH_confirmation`** (exact casing) — trade one asset only when the other
confirms. Modes: `agree` (both move ≥ thresholds), `lead_lag` (reference moves,
target ignored), `divergence` (opposite moves). Reference series lagged
`reference_lag ≥ 1` bars *before* an as-of backward join (bars are labelled by
open time — the 12:00 bar is not complete until 13:00 and must never confirm a
12:00 decision). Exit at `|move| ≤ exit_threshold`. Space (7,776): `lookback
{6,12,24,48}`, `entry_threshold {0.003,0.005,0.01}`, `reference_threshold
{0,0.002,0.005}`, `exit_threshold {0,0.001}`, `reference_lag {1,2,4}`, mode ×3,
direction, gate. The only family consuming raw reference bars.
`strategies/cross_asset.py` · `configs/search_r3_BTC_ETH_confirmation.yaml`.

## S1-B — four pilots (BTC only, 1 seed, budget 25; catalogue frozen 2026-08-11)

Catalogue: `docs/methodology/strategy_catalogue_s1.md`, ADR 0016. Executed as
pilots ONLY; the full-study configs (`configs/search_s1c_*.yaml`) were written
but never run.

**`mtf_trend_consensus`** — drift visible in several horizons at once: momentum
per horizon normalized by `roll_std·√h`, k-of-n agreement to enter, drop below
`exit_agreement` to flatten. Horizons are 1h lookbacks (up to 336 bars), not
HTF resamples. Space: 4 horizon sets, `min_agreement {2,3}`, `exit_agreement
{1,2}`, `min_strength {0,0.25,0.5}`, `strength_window {48,168}`, direction, gate.

**`funding_reversal`** — extreme funding = crowded positioning that resolves
against the paying side within a bounded horizon. Entry at rolling-quantile
extremes of the rate; **pure time exit** after `holding_bars` (the clock
closes, never the signal). Space: `rank_window {168,336,720}`, `extreme_pct
{0.90,0.95,0.99}`, `holding_bars {4,8,24,48}`, `min_abs_rate {0,5e-5}`,
direction, gate.

**`intraday_seasonality`** — session opens, daily settlement and 8h funding
timestamps concentrate flows at recurring UTC hours; contains NO price
predictor. Enter at `entry_hour` with `side_mode` long or short; pure time
exit. The shared `direction` parameter is deliberately not exposed (`side_mode`
already fixes the side); selection load: 192 configurations. Space:
`entry_hour {0..23}`, `holding_bars {1,2,4,8}`, `side_mode ×2`, optional trend
filter {168,336}, gate.

**`xasset_spread_reversion`** — BTC/ETH share a dominant common factor; a
short-window one-leg dislocation is relative mispricing and reverts. Trades
the target leg only. Entry at `|xasset_rel_momentum| ≥ entry_spread` with
optional correlation floor (`xasset_corr ≥ min_corr`); exit at
`|spread| ≤ exit_spread`. Space: `lookback {6,12,24,48}`, `entry_spread
{0.005,0.01,0.02}`, `exit_spread {0,0.002,0.005}`, corr floor on/off ×
`{0.3,0.5,0.7}` × window `{48,168}`, direction, gate.

## S2-B — three pilots (2 assets × 3 seeds {42,43,44}, budget 25)

Prereg: `docs/roadmap/gate_s2_batch_01.md` (frozen 2026-08-11). Data axis:
taker buy volumes and trade counts — deliberately called *taker imbalance*,
never "OFI" (no limit-order additions/cancellations available). All flow
inputs lagged ≥ 1 bar (frozen batch invariant).

**`taker_flow_extreme`** — extreme one-sided aggressive volume; continuation
vs reversal is genuinely contested in the literature, so `response` is a
searched parameter and both arms are charged to the multiple-testing book.
Entry when `|imbalance|` exceeds its own trailing quantile; pure time exit
(`holding_bars {4,6,8,12}`). Space 6,912.

**`illiquidity_reversion`** — Amihud-style price impact per unit of traded
value; moves on thin value are transitory. Entry when impact exceeds its
trailing `entry_pct` quantile with a minimum move; **fade is fixed** (no
response parameter). Exit when impact normalizes below the `exit_pct`
quantile, plus a hard `max_holding_bars {12,24,48}` cap that can only remove
exposure. Space 5,184. Material difference from mean_reversion is *measured*
(a unit test fails if trigger overlap exceeds Jaccard 0.25).

**`flow_price_divergence`** — windows where aggressors bought hard and price
FELL (or sold and it rose): the passive side absorbed. `response ∈
{follow_absorber, follow_flow}` searched. Entry when both `|imbalance|` and
`|move|` are material (their own quantiles) with opposite signs; pure time
exit. Quantile grid deliberately lower than the other S2 families — calibrated
on trigger frequency only (0.2–3.6% of bars), never on returns, and frozen.
Space 10,368.

## CRT_INTRADAY_V1 — nine families, one engine (full studies, budget 100)

Prereg: `docs/methodology/crt_intraday.md` — registered as a separate round;
§6bis declares in advance that **no CRT family can be promoted** (the final
partition is consumed): the round produces evidence, not candidates. All nine
are assembled by `_assemble()` in `src/perp_lab/crt/strategies.py`; long and
short share code (a `Side` carries the sign). Common machinery: causal
`available_from` on every reference range; sessions in IANA zones (Asia/Tokyo
09:00+9h, London 08:00+8h30, New York 09:30+6h30, crypto day UTC); state
machine AVAILABLE → … → SWEPT → {REJECTED, RECLAIMED} → …; a rejection
without a prior sweep is not a setup. Shared searched grid: `sweep_bps
{5,20}`, `stop_kind {wick_extreme, atr_distance}`, `target_plan {mid,
mid_then_opposite, r_multiple_2}`, `time_stop_bars {12,48}`,
`min_net_reward_risk {1.0,1.5}`, `direction {long,short,both}` (with
family-specific omissions below). Fixed mechanics (NOT searched — each extra
configuration is paid in the multiple-testing correction): stop buffer 5 bps,
ATR₁₄ stop multiple 1.0, max wait 6 bars, reclaim within 3 bars / 1
confirmation close, acceptance 3 closes / 10 bps, max 96 bars active,
displacement 0.5·ATR, breakeven after first target, cost 5 bps/side. Trade
management (`crt/exits.py`): pre-entry rejection unless net R:R (after a full
round trip on both legs) ≥ `min_net_reward_risk`; stop live from the first
bar; partial targets with breakeven; time stop; session-end close where a
session is declared; pessimistic intrabar policy STOP_FIRST with ambiguity
rate reported. CRT is the only family emitting fractional positions (partial
exits); one position at a time. Risk engine: implemented, inactive (above).

Per family (entry-rule options searched unless stated):

1. **`pdl_reclaim_long` / `pdh_reclaim_short`** — one family, two fixed sides:
   previous-day low (high) is resting liquidity; sweep beyond it by
   `min_sweep_bps {5,25}` then reclaim. Direction fixed (not searched);
   entry `{reclaim_close, first_retest}`; 192 identities each. HTF reference:
   the natural day.
2. **`crt_htf_range_reversal`** — the range of a CLOSED HTF candle
   (`candle_timeframe {1h,4h,1d}` searched), sweep + reclaim, both directions.
3. **`session_liquidity_sweep`** — one session sweeps another session's closed
   extreme (`session_pairs {(asia,london),(asia,new_york),(london,new_york)}`);
   trade only inside the operating session; session-end close active.
4. **`session_range_rotation`** — rejection at a closed session-range edge
   (trigger REJECTED, `require_sweep=False`), rotate to the other edge; entry
   `{reclaim_close, retest_with_rejection}`; session-end close.
5. **`opening_range_breakout_retest`** — the only CONTINUATION setup: close
   beyond the 60/120-minute opening range (London or New York), trigger
   ACCEPTED_OUTSIDE (a wick pierce never qualifies); `sweep_bps` excluded from
   its grid; target plans restricted to `{r_multiple_2, atr_multiple_2,
   r1_then_r3}` (a continuation cannot target the range it just left); entry
   `{first_retest, displacement_confirmation}`.
6. **`failed_breakout_reversal`** — a breakout that closed outside
   (`min_closes_outside=1`, fixed) and then failed; reference previous day or
   4h candle.
7. **`double_sweep_reversal`** — both range extremes taken, traded from the
   second; first-swept side recorded; entry `{reclaim_close,
   displacement_confirmation}`.
8. **`crt_three_candle_model`** — canonical 3-candle CRT: candle 1 range,
   candle 2 sweep, candle 3 displacement whose BODY covers `displacement_atr
   {0.3,0.75}`·ATR (the only grid parameter that overrides mechanics); entry
   rule fixed in code to `displacement_confirmation` (the rule IS the model);
   `candle_timeframe {1h,4h,1d}`; the only family triggering on both RECLAIMED
   and REJECTED.

Configs `configs/search_crt_v1_*.yaml`. RS is the sole confirmatory evidence;
the GA runs at identical budget as a cross-check only.

## S3 — `macro_event_brake` (full study, budget 100)

Hypothesis (ADR 0019, `docs/methodology/strategy_catalogue_s3.md`): scheduled
US macro releases (CPI, FOMC) carry 2.5–3.2× hourly volatility with no
directional drift (development-window event study, permutation p < 0.001), so
a directional carrier should have a better net risk profile FLAT inside those
windows. Risk gating, not signal generation: the carrier is the R2/R3 momentum
crossover, so any improvement is attributable to the calendar gate alone.
Entry/exit: identical to momentum; afterwards the gate forces `side = 0` in
`[event − pre_bars·1h, event + post_bars·1h)`. No stop/target/time exit.
Space (2,592 raw): `fast {12,24}`, `slow {96,168}`, `event_set {cpi, fomc,
both}`, `pre_bars {1,2,4}`, `post_bars {2,4,8}`, direction, regime gate.
Calendar frozen and committed: `configs/altdata/us_macro_events.csv` (71 CPI,
49 FOMC, 2020–2025, source URL per row); the two March-2020 emergency FOMC
actions are explicitly excluded (not scheduled → gating on them would be
look-ahead). `src/perp_lab/strategies/macro_event_brake.py` ·
`configs/search_s3_macro_event_brake.yaml`.

## Where the annex layers fit (and what they are not)

Meta-labeling (chapter 9): a secondary layer over a momentum primary on BTC,
run under an exploratory infrastructure contract (ADR 0017) after the closure
left no eligible primary — not a strategy round, not external validation.
HAR/LSTM volatility forecasting and the alt-data event study (annex/chapter 11
and 5): descriptive and forecasting layers on the same development data; the
event study *motivated* S3, whose confirmatory test then failed. None of these
belongs in the round tables above.

## Known documentation gaps (stated, not papered over)

- No dedicated catalogue sheet exists for the five R3 families;
  `strategy_specification.md` covers momentum/breakout/mean_reversion only,
  and for volatility_breakout, funding and BTC_ETH_confirmation the economic
  hypothesis lives in the module docstrings.
- `crt_intraday.md` documents the engine and the round but has no per-family
  hypothesis table; the nine hypotheses live in the docstrings of
  `crt/strategies.py`.
- The headers of `configs/search_crt_v1_*.yaml` still say "NOT YET EXECUTED";
  the artifacts under `artifacts/runs/crt_v1_budget100/` show the round was
  executed — the header is stale.
- Two CRT mechanics fields (`pierce_bps`, `pivot_span`) exist in the config
  model but are not forwarded to the engine; they run at their code defaults
  and are not effectively configurable.
