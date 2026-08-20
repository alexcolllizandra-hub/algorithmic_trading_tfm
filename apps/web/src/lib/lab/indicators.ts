// Causal indicators for the in-browser lab engine.
//
// Each function mirrors its counterpart in src/perp_lab/features/causal.py or
// the strategy modules: trailing windows only, warm-up rows are NaN, and the
// rolling std uses the sample estimator (ddof=1) like polars' rolling_std.

export function sma(values: Float64Array, window: number): Float64Array {
  const n = values.length;
  const out = new Float64Array(n).fill(NaN);
  let sum = 0;
  for (let i = 0; i < n; i++) {
    sum += values[i];
    if (i >= window) sum -= values[i - window];
    if (i >= window - 1) out[i] = sum / window;
  }
  return out;
}

/** Rolling sample standard deviation (ddof=1), matching polars rolling_std. */
export function rollingStd(values: Float64Array, window: number): Float64Array {
  const n = values.length;
  const out = new Float64Array(n).fill(NaN);
  if (window < 2) return out;
  let sum = 0;
  let sumSq = 0;
  for (let i = 0; i < n; i++) {
    sum += values[i];
    sumSq += values[i] * values[i];
    if (i >= window) {
      sum -= values[i - window];
      sumSq -= values[i - window] * values[i - window];
    }
    if (i >= window - 1) {
      const mean = sum / window;
      const variance = (sumSq - window * mean * mean) / (window - 1);
      out[i] = variance > 0 ? Math.sqrt(variance) : 0;
    }
  }
  return out;
}

/** Trailing z-score (P_t - mean_w)/std_w; zero-std windows map to NaN. */
export function zscore(values: Float64Array, window: number): Float64Array {
  const mean = sma(values, window);
  const std = rollingStd(values, window);
  const n = values.length;
  const out = new Float64Array(n).fill(NaN);
  for (let i = 0; i < n; i++) {
    if (Number.isFinite(mean[i]) && Number.isFinite(std[i]) && std[i] > 0) {
      out[i] = (values[i] - mean[i]) / std[i];
    }
  }
  return out;
}

/** Rolling max over the window ending at each bar (monotonic deque, O(n)). */
export function rollingMax(values: Float64Array, window: number): Float64Array {
  const n = values.length;
  const out = new Float64Array(n).fill(NaN);
  const deque: number[] = [];
  for (let i = 0; i < n; i++) {
    while (deque.length && values[deque[deque.length - 1]] <= values[i]) deque.pop();
    deque.push(i);
    if (deque[0] <= i - window) deque.shift();
    if (i >= window - 1) out[i] = values[deque[0]];
  }
  return out;
}

export function rollingMin(values: Float64Array, window: number): Float64Array {
  const n = values.length;
  const out = new Float64Array(n).fill(NaN);
  const deque: number[] = [];
  for (let i = 0; i < n; i++) {
    while (deque.length && values[deque[deque.length - 1]] >= values[i]) deque.pop();
    deque.push(i);
    if (deque[0] <= i - window) deque.shift();
    if (i >= window - 1) out[i] = values[deque[0]];
  }
  return out;
}

/** Shift forward by one: out[i] = values[i-1], out[0] = NaN. */
export function shift1(values: Float64Array): Float64Array {
  const n = values.length;
  const out = new Float64Array(n).fill(NaN);
  for (let i = 1; i < n; i++) out[i] = values[i - 1];
  return out;
}

/** True range from the current bar's high/low and the previous close. */
export function trueRange(
  high: Float64Array,
  low: Float64Array,
  close: Float64Array
): Float64Array {
  const n = high.length;
  const out = new Float64Array(n).fill(NaN);
  for (let i = 0; i < n; i++) {
    const hl = high[i] - low[i];
    if (i === 0) {
      out[i] = hl;
      continue;
    }
    const hc = Math.abs(high[i] - close[i - 1]);
    const lc = Math.abs(low[i] - close[i - 1]);
    out[i] = Math.max(hl, hc, lc);
  }
  return out;
}

/** ATR as the trailing simple mean of true range (mirrors add_atr). */
export function atr(
  high: Float64Array,
  low: Float64Array,
  close: Float64Array,
  window: number
): Float64Array {
  return sma(trueRange(high, low, close), window);
}

/**
 * Trailing rolling quantile (linear interpolation, numpy default), used by the
 * volatility-breakout ATR floor. Insertion-sorted window buffer: O(n·w) moves,
 * fine at the lab's sizes (n ≈ 5·10^4, w ≤ 480).
 */
export function rollingQuantile(
  values: Float64Array,
  window: number,
  quantile: number
): Float64Array {
  const n = values.length;
  const out = new Float64Array(n).fill(NaN);
  const buffer: number[] = [];

  const insertSorted = (x: number) => {
    let lo = 0;
    let hi = buffer.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (buffer[mid] < x) lo = mid + 1;
      else hi = mid;
    }
    buffer.splice(lo, 0, x);
  };
  const removeSorted = (x: number) => {
    let lo = 0;
    let hi = buffer.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (buffer[mid] < x) lo = mid + 1;
      else hi = mid;
    }
    buffer.splice(lo, 1);
  };

  for (let i = 0; i < n; i++) {
    const v = values[i];
    insertSorted(Number.isFinite(v) ? v : Infinity);
    if (i >= window)
      removeSorted(Number.isFinite(values[i - window]) ? values[i - window] : Infinity);
    if (i >= window - 1) {
      const pos = quantile * (window - 1);
      const base = Math.floor(pos);
      const frac = pos - base;
      const a = buffer[base];
      const b = buffer[Math.min(base + 1, window - 1)];
      out[i] = Number.isFinite(a) && Number.isFinite(b) ? a + frac * (b - a) : NaN;
    }
  }
  return out;
}
