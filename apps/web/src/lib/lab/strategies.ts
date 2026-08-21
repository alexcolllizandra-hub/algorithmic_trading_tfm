// Browser re-implementations of four study strategy families.
//
// Each signal function is a line-by-line port of its Python counterpart in
// src/perp_lab/strategies/ (momentum.py, mean_reversion.py, breakout.py,
// volatility_breakout.py): same thresholds, same shift(1) exclusions of the
// decision bar, same position state machine. The parameter grids offered in
// the UI are the study's own search-space values plus free numeric entry.

import { atr, rollingMax, rollingMin, rollingQuantile, shift1, sma, zscore } from "./indicators";
import type { FundingSeries } from "./engine";

export type Direction = "both" | "long" | "short";

export interface Bars {
  t: Float64Array; // bar open time, unix seconds
  o: Float64Array;
  h: Float64Array;
  l: Float64Array;
  c: Float64Array;
}

/** Port of strategies/base.py evolve_positions: flat→entry, reverse, exit. */
export function evolvePositions(
  longEntry: Uint8Array,
  shortEntry: Uint8Array,
  exitFlat: Uint8Array
): Int8Array {
  const n = longEntry.length;
  const pos = new Int8Array(n);
  let current = 0;
  for (let t = 0; t < n; t++) {
    const le = longEntry[t] === 1;
    const se = shortEntry[t] === 1;
    const ex = exitFlat[t] === 1;
    if (current === 0) {
      if (le) current = 1;
      else if (se) current = -1;
    } else if (current === 1) {
      if (se) current = -1;
      else if (ex) current = 0;
    } else {
      if (le) current = 1;
      else if (ex) current = 0;
    }
    pos[t] = current;
  }
  return pos;
}

function consecutive(flags: Uint8Array, k: number): Uint8Array {
  if (k <= 1) return flags;
  const out = new Uint8Array(flags.length);
  let count = 0;
  for (let t = 0; t < flags.length; t++) {
    count = flags[t] ? count + 1 : 0;
    out[t] = count >= k ? 1 : 0;
  }
  return out;
}

function applyDirection(side: Int8Array, direction: Direction): Int8Array {
  if (direction === "both") return side;
  const out = new Int8Array(side.length);
  for (let i = 0; i < side.length; i++) {
    if (direction === "long") out[i] = side[i] > 0 ? 1 : 0;
    else out[i] = side[i] < 0 ? -1 : 0;
  }
  return out;
}

// ---------------------------------------------------------------------------
// Families
// ---------------------------------------------------------------------------

export interface MomentumParams {
  fast: number;
  slow: number;
  direction: Direction;
}

export function momentumSignals(bars: Bars, p: MomentumParams): Int8Array {
  const fast = sma(bars.c, p.fast);
  const slow = sma(bars.c, p.slow);
  const n = bars.c.length;
  const side = new Int8Array(n);
  for (let i = 0; i < n; i++) {
    if (!Number.isFinite(fast[i]) || !Number.isFinite(slow[i])) side[i] = 0;
    else if (fast[i] > slow[i]) side[i] = 1;
    else if (fast[i] < slow[i]) side[i] = -1;
  }
  return applyDirection(side, p.direction);
}

export interface MeanReversionParams {
  zscoreWindow: number;
  entryZ: number;
  exitZ: number;
  direction: Direction;
}

export function meanReversionSignals(bars: Bars, p: MeanReversionParams): Int8Array {
  const z = zscore(bars.c, p.zscoreWindow);
  const n = z.length;
  const longEntry = new Uint8Array(n);
  const shortEntry = new Uint8Array(n);
  const exitFlat = new Uint8Array(n);
  for (let i = 0; i < n; i++) {
    if (!Number.isFinite(z[i])) continue;
    if (z[i] <= -p.entryZ && p.direction !== "short") longEntry[i] = 1;
    if (z[i] >= p.entryZ && p.direction !== "long") shortEntry[i] = 1;
    if (Math.abs(z[i]) <= p.exitZ) exitFlat[i] = 1;
  }
  return evolvePositions(longEntry, shortEntry, exitFlat);
}

export interface BreakoutParams {
  channelWindow: number;
  confirmationBars: number;
  direction: Direction;
}

export function breakoutSignals(bars: Bars, p: BreakoutParams): Int8Array {
  const upper = shift1(rollingMax(bars.h, p.channelWindow));
  const lower = shift1(rollingMin(bars.l, p.channelWindow));
  const n = bars.c.length;
  const breakUp = new Uint8Array(n);
  const breakDn = new Uint8Array(n);
  const exitFlat = new Uint8Array(n);
  for (let i = 0; i < n; i++) {
    const valid = Number.isFinite(upper[i]) && Number.isFinite(lower[i]);
    if (!valid) continue;
    if (bars.c[i] > upper[i]) breakUp[i] = 1;
    if (bars.c[i] < lower[i]) breakDn[i] = 1;
    if (bars.c[i] <= upper[i] && bars.c[i] >= lower[i]) exitFlat[i] = 1;
  }
  let longEntry = consecutive(breakUp, p.confirmationBars);
  let shortEntry = consecutive(breakDn, p.confirmationBars);
  if (p.direction === "long") shortEntry = new Uint8Array(n);
  if (p.direction === "short") longEntry = new Uint8Array(n);
  return evolvePositions(longEntry, shortEntry, exitFlat);
}

export type VbExitMode = "reenter_level" | "opposite_break" | "volatility_stop";

export interface VolatilityBreakoutParams {
  levelWindow: number;
  atrWindow: number;
  entryAtr: number;
  exitAtr: number;
  exitMode: VbExitMode;
  minAtrPct: number | null;
  direction: Direction;
}

export function volatilityBreakoutSignals(bars: Bars, p: VolatilityBreakoutParams): Int8Array {
  const n = bars.c.length;
  const upper = shift1(rollingMax(bars.h, p.levelWindow));
  const lower = shift1(rollingMin(bars.l, p.levelWindow));
  const atrArr = shift1(atr(bars.h, bars.l, bars.c, p.atrWindow));

  let floor: Float64Array | null = null;
  if (p.minAtrPct != null) {
    const floorWindow = Math.max(p.atrWindow * 10, 100);
    floor = rollingQuantile(atrArr, floorWindow, p.minAtrPct);
  }

  const valid = new Uint8Array(n);
  let longEntry = new Uint8Array(n);
  let shortEntry = new Uint8Array(n);
  for (let i = 0; i < n; i++) {
    let ok =
      Number.isFinite(upper[i]) &&
      Number.isFinite(lower[i]) &&
      Number.isFinite(atrArr[i]) &&
      atrArr[i] > 0;
    if (ok && floor) ok = Number.isFinite(floor[i]) && atrArr[i] >= floor[i];
    valid[i] = ok ? 1 : 0;
    if (!ok) continue;
    if (bars.c[i] > upper[i] + p.entryAtr * atrArr[i]) longEntry[i] = 1;
    if (bars.c[i] < lower[i] - p.entryAtr * atrArr[i]) shortEntry[i] = 1;
  }
  if (p.direction === "long") shortEntry = new Uint8Array(n);
  if (p.direction === "short") longEntry = new Uint8Array(n);

  const exitFlat = new Uint8Array(n);
  if (p.exitMode === "reenter_level") {
    for (let i = 0; i < n; i++) {
      if (valid[i] && bars.c[i] <= upper[i] && bars.c[i] >= lower[i]) exitFlat[i] = 1;
    }
  } else if (p.exitMode === "volatility_stop") {
    // Trailing stop from the trade's best close, exit_atr volatility units away.
    let position = 0;
    let extreme = NaN;
    for (let t = 0; t < n; t++) {
      if (position === 0) {
        if (valid[t] && longEntry[t]) {
          position = 1;
          extreme = bars.c[t];
        } else if (valid[t] && shortEntry[t]) {
          position = -1;
          extreme = bars.c[t];
        }
        continue;
      }
      if (position === 1) {
        extreme = Math.max(extreme, bars.c[t]);
        if (valid[t] && bars.c[t] <= extreme - p.exitAtr * atrArr[t]) {
          exitFlat[t] = 1;
          position = 0;
          extreme = NaN;
        } else if (shortEntry[t]) {
          position = -1;
          extreme = bars.c[t];
        }
      } else {
        extreme = Math.min(extreme, bars.c[t]);
        if (valid[t] && bars.c[t] >= extreme + p.exitAtr * atrArr[t]) {
          exitFlat[t] = 1;
          position = 0;
          extreme = NaN;
        } else if (longEntry[t]) {
          position = 1;
          extreme = bars.c[t];
        }
      }
    }
  }
  // opposite_break: no separate exit — evolvePositions reverses on opposite entry.

  return evolvePositions(longEntry, shortEntry, exitFlat);
}

/** Port of strategies/timed_exit.py evolve_timed_positions: open on an event,
 * hold exactly `holdingBars` bars, ignore events while open, cancel when a
 * long and a short event fire on the same bar. */
export function evolveTimedPositions(
  longEvent: Uint8Array,
  shortEvent: Uint8Array,
  holdingBars: number
): Int8Array {
  const n = longEvent.length;
  const side = new Int8Array(n);
  let remaining = 0;
  let current = 0;
  for (let t = 0; t < n; t++) {
    if (remaining > 0) {
      side[t] = current;
      remaining--;
      continue;
    }
    const le = longEvent[t] === 1;
    const se = shortEvent[t] === 1;
    if (le === se) continue;
    current = le ? 1 : -1;
    side[t] = current;
    remaining = holdingBars - 1;
  }
  return side;
}

/** Backward as-of join: the last funding rate published at or before each
 * bar's open (mirrors the Python pipeline's causal attach). */
export function fundingAsOf(barT: Float64Array, funding: FundingSeries): Float64Array {
  const n = barT.length;
  const out = new Float64Array(n).fill(NaN);
  let j = -1;
  for (let i = 0; i < n; i++) {
    while (j + 1 < funding.t.length && funding.t[j + 1] <= barT[i]) j++;
    if (j >= 0) out[i] = funding.rate[j];
  }
  return out;
}

export interface FundingReversalParams {
  rankWindow: number;
  extremePct: number;
  holdingBars: number;
  minAbsRate: number;
  direction: Direction;
}

export function fundingReversalSignals(
  bars: Bars,
  funding: FundingSeries,
  p: FundingReversalParams
): Int8Array {
  const rate = fundingAsOf(bars.t, funding);
  const upper = rollingQuantile(rate, p.rankWindow, p.extremePct);
  const lower = rollingQuantile(rate, p.rankWindow, 1 - p.extremePct);
  const n = rate.length;
  let longEvent = new Uint8Array(n);
  let shortEvent = new Uint8Array(n);
  for (let i = 0; i < n; i++) {
    const valid =
      Number.isFinite(rate[i]) &&
      Number.isFinite(upper[i]) &&
      Number.isFinite(lower[i]) &&
      Math.abs(rate[i]) >= p.minAbsRate;
    if (!valid) continue;
    // Funding at the top of its trailing distribution: longs are paying, so
    // the reversal trade is short; symmetric for the lower tail.
    if (rate[i] >= upper[i]) shortEvent[i] = 1;
    if (rate[i] <= lower[i]) longEvent[i] = 1;
  }
  if (p.direction === "long") shortEvent = new Uint8Array(n);
  if (p.direction === "short") longEvent = new Uint8Array(n);
  return evolveTimedPositions(longEvent, shortEvent, p.holdingBars);
}

export interface IntradaySeasonalityParams {
  entryHour: number;
  holdingBars: number;
  sideMode: "long" | "short";
  trendFilterMa: number; // 0 disables the gate
}

export function intradaySeasonalitySignals(bars: Bars, p: IntradaySeasonalityParams): Int8Array {
  const n = bars.t.length;
  const fires = new Uint8Array(n);
  for (let i = 0; i < n; i++) {
    const hour = Math.floor(bars.t[i] / 3600) % 24;
    if (hour === p.entryHour) fires[i] = 1;
  }
  let longEvent = p.sideMode === "long" ? fires : new Uint8Array(n);
  let shortEvent = p.sideMode === "short" ? fires : new Uint8Array(n);
  if (p.trendFilterMa > 0) {
    const trend = sma(bars.c, p.trendFilterMa);
    const gatedLong = new Uint8Array(n);
    const gatedShort = new Uint8Array(n);
    for (let i = 0; i < n; i++) {
      if (!Number.isFinite(trend[i])) continue;
      if (longEvent[i] === 1 && bars.c[i] > trend[i]) gatedLong[i] = 1;
      if (shortEvent[i] === 1 && bars.c[i] < trend[i]) gatedShort[i] = 1;
    }
    longEvent = gatedLong;
    shortEvent = gatedShort;
  }
  return evolveTimedPositions(longEvent, shortEvent, p.holdingBars);
}

// ---------------------------------------------------------------------------
// Registry for the UI
// ---------------------------------------------------------------------------

export type StrategyId =
  | "momentum"
  | "mean_reversion"
  | "breakout"
  | "volatility_breakout"
  | "funding_reversal"
  | "intraday_seasonality";

export interface ParamSpec {
  key: string;
  /** Values the study's own search space enumerated (shown as presets). */
  studyValues: (number | string)[];
  default: number | string;
  kind: "int" | "float" | "choice";
  min?: number;
  max?: number;
  step?: number;
}

export interface StrategyExtras {
  funding: FundingSeries | null;
}

export interface StrategyDef {
  id: StrategyId;
  params: ParamSpec[];
  run: (bars: Bars, values: Record<string, number | string>, extras?: StrategyExtras) => Int8Array;
}

const DIRECTION_SPEC: ParamSpec = {
  key: "direction",
  studyValues: ["both", "long", "short"],
  default: "both",
  kind: "choice",
};

export const STRATEGIES: StrategyDef[] = [
  {
    id: "momentum",
    params: [
      { key: "fast", studyValues: [6, 12, 24, 48], default: 24, kind: "int", min: 2, max: 200 },
      {
        key: "slow",
        studyValues: [48, 96, 168, 336],
        default: 168,
        kind: "int",
        min: 4,
        max: 1000,
      },
      DIRECTION_SPEC,
    ],
    run: (bars, v) =>
      momentumSignals(bars, {
        fast: Number(v.fast),
        slow: Number(v.slow),
        direction: v.direction as Direction,
      }),
  },
  {
    id: "mean_reversion",
    params: [
      {
        key: "zscoreWindow",
        studyValues: [24, 48, 96],
        default: 48,
        kind: "int",
        min: 5,
        max: 500,
      },
      {
        key: "entryZ",
        studyValues: [1.5, 2.0, 2.5, 3.0],
        default: 2.0,
        kind: "float",
        min: 0.5,
        max: 6,
        step: 0.1,
      },
      {
        key: "exitZ",
        studyValues: [0.0, 0.5, 1.0],
        default: 0.5,
        kind: "float",
        min: 0,
        max: 3,
        step: 0.1,
      },
      DIRECTION_SPEC,
    ],
    run: (bars, v) =>
      meanReversionSignals(bars, {
        zscoreWindow: Number(v.zscoreWindow),
        entryZ: Number(v.entryZ),
        exitZ: Number(v.exitZ),
        direction: v.direction as Direction,
      }),
  },
  {
    id: "breakout",
    params: [
      {
        key: "channelWindow",
        studyValues: [24, 48, 96],
        default: 48,
        kind: "int",
        min: 5,
        max: 500,
      },
      {
        key: "confirmationBars",
        studyValues: [1, 2, 3],
        default: 1,
        kind: "int",
        min: 1,
        max: 10,
      },
      DIRECTION_SPEC,
    ],
    run: (bars, v) =>
      breakoutSignals(bars, {
        channelWindow: Number(v.channelWindow),
        confirmationBars: Number(v.confirmationBars),
        direction: v.direction as Direction,
      }),
  },
  {
    id: "volatility_breakout",
    params: [
      {
        key: "levelWindow",
        studyValues: [24, 48, 96],
        default: 48,
        kind: "int",
        min: 5,
        max: 500,
      },
      { key: "atrWindow", studyValues: [14, 24, 48], default: 24, kind: "int", min: 2, max: 200 },
      {
        key: "entryAtr",
        studyValues: [0.25, 0.5, 1.0],
        default: 0.5,
        kind: "float",
        min: 0.05,
        max: 4,
        step: 0.05,
      },
      {
        key: "exitAtr",
        studyValues: [0.1, 0.25, 0.5],
        default: 0.25,
        kind: "float",
        min: 0.05,
        max: 3,
        step: 0.05,
      },
      {
        key: "exitMode",
        studyValues: ["reenter_level", "opposite_break", "volatility_stop"],
        default: "reenter_level",
        kind: "choice",
      },
      DIRECTION_SPEC,
    ],
    run: (bars, v) =>
      volatilityBreakoutSignals(bars, {
        levelWindow: Number(v.levelWindow),
        atrWindow: Number(v.atrWindow),
        entryAtr: Number(v.entryAtr),
        exitAtr: Number(v.exitAtr),
        exitMode: v.exitMode as VbExitMode,
        minAtrPct: null,
        direction: v.direction as Direction,
      }),
  },
  {
    id: "funding_reversal",
    params: [
      {
        key: "rankWindow",
        studyValues: [168, 336, 720],
        default: 336,
        kind: "int",
        min: 24,
        max: 2000,
      },
      {
        key: "extremePct",
        studyValues: [0.9, 0.95, 0.99],
        default: 0.95,
        kind: "float",
        min: 0.51,
        max: 0.99,
        step: 0.01,
      },
      {
        key: "holdingBars",
        studyValues: [4, 8, 24, 48],
        default: 24,
        kind: "int",
        min: 1,
        max: 200,
      },
      {
        key: "minAbsRate",
        studyValues: [0, 0.00005],
        default: 0,
        kind: "float",
        min: 0,
        max: 0.001,
        step: 0.00005,
      },
      DIRECTION_SPEC,
    ],
    run: (bars, v, extras) => {
      if (!extras?.funding) return new Int8Array(bars.t.length);
      return fundingReversalSignals(bars, extras.funding, {
        rankWindow: Number(v.rankWindow),
        extremePct: Number(v.extremePct),
        holdingBars: Number(v.holdingBars),
        minAbsRate: Number(v.minAbsRate),
        direction: v.direction as Direction,
      });
    },
  },
  {
    id: "intraday_seasonality",
    params: [
      {
        key: "entryHour",
        studyValues: Array.from({ length: 24 }, (_, h) => h),
        default: 14,
        kind: "int",
        min: 0,
        max: 23,
      },
      {
        key: "holdingBars",
        studyValues: [1, 2, 4, 8],
        default: 4,
        kind: "int",
        min: 1,
        max: 48,
      },
      { key: "sideMode", studyValues: ["long", "short"], default: "long", kind: "choice" },
      {
        key: "trendFilterMa",
        studyValues: [0, 168, 336],
        default: 0,
        kind: "int",
        min: 0,
        max: 1000,
      },
    ],
    run: (bars, v) =>
      intradaySeasonalitySignals(bars, {
        entryHour: Number(v.entryHour),
        holdingBars: Number(v.holdingBars),
        sideMode: v.sideMode as "long" | "short",
        trendFilterMa: Number(v.trendFilterMa),
      }),
  },
];
