// Exit overlays and composable gates (phase 8d, blocks B1/B2). All of them
// post-process the family's side series — the decision stream, one value per
// closed bar — using only information available at each bar's close: closes,
// a shift(1) ATR, a shift(1) SMA trend line, and a trailing rolling-tercile
// volatility regime. Overlays can only remove or shorten exposure; re-entry
// requires a fresh signal from the family (a value change in the original
// series), mirroring how the study's volatility_stop treats episodes.

import { atr, rollingStd, shift1, sma } from "./indicators";
import type { Bars } from "./strategies";

export interface ExitOverlay {
  /** Hard stop at k ATRs against the episode's entry reference close. */
  stopAtr: number | null;
  /** Take profit at k ATRs in favour of the entry reference close. */
  takeProfitAtr: number | null;
  /** Trailing stop at k ATRs from the episode's best close. */
  trailingAtr: number | null;
  /** Maximum bars an episode may stay open. */
  maxBars: number | null;
  /** ATR window used by the three ATR-based exits. */
  atrWindow: number;
}

export const NO_EXITS: ExitOverlay = {
  stopAtr: null,
  takeProfitAtr: null,
  trailingAtr: null,
  maxBars: null,
  atrWindow: 24,
};

/**
 * Apply the exit overlay to a side series. Episodes are maximal runs of a
 * constant non-zero side; once an exit fires, the rest of the episode is
 * flattened. The entry reference is the close of the bar that opened the
 * episode (a causal proxy for the next-open execution price).
 */
export function applyExitOverlay(side: Int8Array, bars: Bars, overlay: ExitOverlay): Int8Array {
  const { stopAtr, takeProfitAtr, trailingAtr, maxBars } = overlay;
  if (stopAtr == null && takeProfitAtr == null && trailingAtr == null && maxBars == null) {
    return side;
  }
  const atrArr = shift1(atr(bars.h, bars.l, bars.c, overlay.atrWindow));
  const out = Int8Array.from(side);
  const n = side.length;

  let i = 0;
  while (i < n) {
    const p = side[i];
    const isEntry = p !== 0 && (i === 0 || side[i - 1] !== p);
    if (!isEntry) {
      i++;
      continue;
    }
    const entryRef = bars.c[i];
    let extreme = bars.c[i];
    let exited = false;
    let j = i;
    while (j < n && side[j] === p) {
      if (exited) {
        out[j] = 0;
        j++;
        continue;
      }
      const close = bars.c[j];
      extreme = p === 1 ? Math.max(extreme, close) : Math.min(extreme, close);
      const unit = atrArr[j];
      const held = j - i + 1;
      let exitNow = false;
      if (maxBars != null && held >= maxBars) exitNow = true;
      if (!exitNow && Number.isFinite(unit) && unit > 0) {
        if (stopAtr != null) {
          exitNow =
            p === 1 ? close <= entryRef - stopAtr * unit : close >= entryRef + stopAtr * unit;
        }
        if (!exitNow && takeProfitAtr != null) {
          exitNow =
            p === 1
              ? close >= entryRef + takeProfitAtr * unit
              : close <= entryRef - takeProfitAtr * unit;
        }
        if (!exitNow && trailingAtr != null) {
          exitNow =
            p === 1 ? close <= extreme - trailingAtr * unit : close >= extreme + trailingAtr * unit;
        }
      }
      if (exitNow) {
        // The exit decision is taken at this bar's close, so this bar keeps
        // the position (it flattens from the next bar's open onwards).
        exited = true;
      }
      j++;
    }
    i = j;
  }
  return out;
}

/** Longs only above the shift(1) SMA(n); shorts only below it. */
export function applyTrendGate(side: Int8Array, bars: Bars, window: number): Int8Array {
  const trend = shift1(sma(bars.c, window));
  const out = Int8Array.from(side);
  for (let i = 0; i < side.length; i++) {
    if (!Number.isFinite(trend[i])) {
      out[i] = 0;
      continue;
    }
    if (side[i] === 1 && bars.c[i] <= trend[i]) out[i] = 0;
    if (side[i] === -1 && bars.c[i] >= trend[i]) out[i] = 0;
  }
  return out;
}

export type Regime = "low" | "mid" | "high";

/**
 * Trailing volatility-regime label per bar: rvol(168h of log returns), with
 * tercile boundaries taken from a trailing 2,160-bar (90-day) window shifted
 * by one bar — fully causal, declared as the lab's simplification of the
 * study's train-fitted regime model.
 */
export function regimeLabels(bars: Bars): (Regime | null)[] {
  const n = bars.c.length;
  const logRet = new Float64Array(n);
  for (let i = 1; i < n; i++) logRet[i] = Math.log(bars.c[i] / bars.c[i - 1]);
  const rvol = rollingStd(logRet, 168);

  const window = 2160;
  const labels: (Regime | null)[] = new Array(n).fill(null);
  const buffer: number[] = [];
  for (let i = 0; i < n; i++) {
    // Boundaries from the trailing window as of the PREVIOUS bar.
    if (buffer.length >= 200 && Number.isFinite(rvol[i])) {
      const sorted = [...buffer].sort((a, b) => a - b);
      const q1 = sorted[Math.floor(sorted.length / 3)];
      const q2 = sorted[Math.floor((2 * sorted.length) / 3)];
      labels[i] = rvol[i] <= q1 ? "low" : rvol[i] <= q2 ? "mid" : "high";
    }
    if (Number.isFinite(rvol[i])) {
      buffer.push(rvol[i]);
      if (buffer.length > window) buffer.shift();
    }
  }
  return labels;
}

/** Flatten every bar whose regime is not in the allowed set. */
export function applyRegimeGate(
  side: Int8Array,
  labels: (Regime | null)[],
  allowed: Regime[]
): Int8Array {
  const set = new Set(allowed);
  const out = Int8Array.from(side);
  for (let i = 0; i < side.length; i++) {
    const label = labels[i];
    if (label == null || !set.has(label)) out[i] = 0;
  }
  return out;
}
