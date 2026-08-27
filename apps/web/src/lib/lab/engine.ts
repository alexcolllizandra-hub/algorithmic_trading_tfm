// In-browser backtest engine: a faithful port of
// src/perp_lab/backtesting/engine.py and metrics.py.
//
// Execution model (identical to the study's):
//   * side_t is decided at the close of bar t;
//   * position_b = side_{b-1}, entered at open_b, earning the open-to-open
//     return open_{b+1}/open_b - 1;
//   * turnover_b = |position_b - position_{b-1}| (a flip costs two units);
//   * fee/slippage = turnover * bps / 1e4 per side;
//   * funding_b = position_b * (funding rates settling in [open_b, open_{b+1}));
//   * net = gross - fee - slippage - funding; the final bar (undefined
//     open-to-open return) is dropped before compounding.
//
// Annualisation uses the 24/7, 365-day convention (8,760 hourly bars/year).

import type { Bars } from "./strategies";

export interface CostModel {
  feeBpsPerSide: number;
  slippageBpsPerSide: number;
}

export interface FundingSeries {
  t: Float64Array; // settlement time, unix seconds
  rate: Float64Array;
}

export interface Ledger {
  /** Bar open times (unix seconds); final input bar already dropped. */
  t: Float64Array;
  position: Float64Array;
  ooReturn: Float64Array;
  gross: Float64Array;
  fee: Float64Array;
  slippage: Float64Array;
  funding: Float64Array;
  net: Float64Array;
  turnover: Float64Array;
  equity: Float64Array;
  drawdown: Float64Array;
  executionPrice: Float64Array;
}

export interface Trade {
  entryIndex: number; // index into the ledger arrays
  exitIndex: number;
  position: 1 | -1;
  entryPrice: number;
  exitPrice: number;
  nBars: number;
  netReturn: number;
  /** Maximum favorable excursion vs entry price, as a fraction (>= 0). */
  mfe: number;
  /** Maximum adverse excursion vs entry price, as a fraction (>= 0). */
  mae: number;
  exitReason: "signal_close" | "signal_reverse" | "open";
}

export interface Metrics {
  n_bars: number;
  total_return: number;
  ann_return: number;
  ann_volatility: number;
  sharpe: number;
  sortino: number;
  max_drawdown: number;
  calmar: number;
  exposure: number;
  hit_rate: number;
  turnover: number;
  n_trades: number;
  time_in_drawdown: number;
  ulcer_index: number;
  var_95: number;
  expected_shortfall_95: number;
  longest_win_streak: number;
  longest_loss_streak: number;
  profit_factor: number;
  expectancy: number;
  trade_hit_rate: number;
  n_trades_closed: number;
  mean_duration_bars: number;
  median_mae: number;
  median_mfe: number;
  e_ratio: number;
}

export const BARS_PER_YEAR_1H = 8760;

/** Sum funding rates settling inside each bar's holding interval (causal). */
function fundingPerBar(barT: Float64Array, funding: FundingSeries | null): Float64Array {
  const n = barT.length;
  const out = new Float64Array(n);
  if (!funding || funding.t.length === 0) return out;
  let j = 0;
  for (let i = 0; i < n; i++) {
    const next = i + 1 < n ? barT[i + 1] : Infinity;
    while (j < funding.t.length && funding.t[j] < barT[i]) j++;
    let k = j;
    while (k < funding.t.length && funding.t[k] < next) {
      out[i] += funding.rate[k];
      k++;
    }
    j = k;
  }
  // Events after the last bar's open would need open_{n+1}; the Python engine
  // charges them to the last bar, which is then dropped — net effect identical.
  return out;
}

export function runBacktest(
  bars: Bars,
  side: Int8Array,
  costs: CostModel,
  funding: FundingSeries | null
): Ledger {
  const nAll = bars.o.length;
  const n = nAll - 1; // final bar dropped: open-to-open return undefined
  const feeRate = costs.feeBpsPerSide / 1e4;
  const slipRate = costs.slippageBpsPerSide / 1e4;

  const t = bars.t.slice(0, n);
  const position = new Float64Array(n);
  for (let i = 1; i < n; i++) position[i] = side[i - 1];

  const rateInBar = fundingPerBar(bars.t, funding).slice(0, n);

  const ooReturn = new Float64Array(n);
  const gross = new Float64Array(n);
  const fee = new Float64Array(n);
  const slippage = new Float64Array(n);
  const fundingCost = new Float64Array(n);
  const net = new Float64Array(n);
  const turnover = new Float64Array(n);
  const equity = new Float64Array(n);
  const drawdown = new Float64Array(n);
  const executionPrice = bars.o.slice(0, n);

  let eq = 1;
  let peak = 1;
  for (let i = 0; i < n; i++) {
    ooReturn[i] = bars.o[i + 1] / bars.o[i] - 1;
    turnover[i] = Math.abs(position[i] - (i > 0 ? position[i - 1] : 0));
    gross[i] = position[i] * ooReturn[i];
    fee[i] = turnover[i] * feeRate;
    slippage[i] = turnover[i] * slipRate;
    fundingCost[i] = position[i] * rateInBar[i];
    net[i] = gross[i] - fee[i] - slippage[i] - fundingCost[i];
    eq *= 1 + net[i];
    peak = Math.max(peak, eq);
    equity[i] = eq;
    drawdown[i] = eq / peak - 1;
  }

  return {
    t,
    position,
    ooReturn,
    gross,
    fee,
    slippage,
    funding: fundingCost,
    net,
    turnover,
    equity,
    drawdown,
    executionPrice,
  };
}

/** Extract round-trip trades with MAE/MFE from bar highs/lows (real data). */
export function extractTrades(ledger: Ledger, bars: Bars): Trade[] {
  const n = ledger.position.length;
  const trades: Trade[] = [];
  let start = -1;
  for (let i = 0; i <= n; i++) {
    const p = i < n ? ledger.position[i] : 0;
    const prev = i > 0 ? ledger.position[i - 1] : 0;
    if (p !== prev) {
      if (prev !== 0 && start >= 0) {
        const last = i - 1;
        const dir = prev as 1 | -1;
        const entryPrice = ledger.executionPrice[start];
        // The position over bar b spans [open_b, open_{b+1}); highs/lows of
        // bars start..last all fall inside the held interval.
        let hi = -Infinity;
        let lo = Infinity;
        let net = 0;
        for (let b = start; b <= last; b++) {
          hi = Math.max(hi, bars.h[b]);
          lo = Math.min(lo, bars.l[b]);
          net += ledger.net[b];
        }
        const exitPrice = last + 1 < bars.o.length ? bars.o[last + 1] : bars.c[last];
        const mfe = dir === 1 ? hi / entryPrice - 1 : 1 - lo / entryPrice;
        const mae = dir === 1 ? 1 - lo / entryPrice : hi / entryPrice - 1;
        trades.push({
          entryIndex: start,
          exitIndex: last,
          position: dir,
          entryPrice,
          exitPrice,
          nBars: last - start + 1,
          netReturn: net,
          mfe: Math.max(0, mfe),
          mae: Math.max(0, mae),
          exitReason: i === n ? "open" : p === 0 ? "signal_close" : ("signal_reverse" as const),
        });
      }
      start = p !== 0 ? i : -1;
    }
  }
  return trades;
}

function quantile(sorted: number[], q: number): number {
  if (!sorted.length) return NaN;
  const pos = q * (sorted.length - 1);
  const base = Math.floor(pos);
  const frac = pos - base;
  return (
    sorted[base] + frac * ((sorted[Math.min(base + 1, sorted.length - 1)] ?? 0) - sorted[base])
  );
}

function median(values: number[]): number {
  const s = [...values].sort((a, b) => a - b);
  return quantile(s, 0.5);
}

/** Port of performance_metrics + trade_metrics over one ledger slice. */
export function computeMetrics(ledger: Ledger, trades: Trade[], from = 0, to?: number): Metrics {
  const end = to ?? ledger.net.length;
  const r = Array.from(ledger.net.slice(from, end));
  const pos = ledger.position.slice(from, end);
  const tvr = ledger.turnover.slice(from, end);
  const n = r.length;

  const bpy = BARS_PER_YEAR_1H;
  let totalReturn = 1;
  for (const x of r) totalReturn *= 1 + x;
  totalReturn -= 1;

  const mean = r.reduce((a, b) => a + b, 0) / Math.max(1, n);
  const std = n > 1 ? Math.sqrt(r.reduce((a, b) => a + (b - mean) ** 2, 0) / (n - 1)) : 0;

  // Equity/drawdown recomputed inside the slice, so phase metrics are
  // self-contained (the in-sample peak does not leak into out-of-sample).
  let eq = 1;
  let peak = 1;
  let maxDd = 0;
  let underBars = 0;
  let ddSq = 0;
  for (const x of r) {
    eq *= 1 + x;
    peak = Math.max(peak, eq);
    const dd = eq / peak - 1;
    maxDd = Math.min(maxDd, dd);
    if (dd < 0) underBars++;
    ddSq += dd * dd;
  }

  const annVol = std * Math.sqrt(bpy);
  const annReturn = totalReturn > -1 ? Math.pow(1 + totalReturn, bpy / Math.max(1, n)) - 1 : -1;
  const sharpe = std > 0 ? (mean / std) * Math.sqrt(bpy) : 0;

  const downside = r.filter((x) => x < 0);
  const dmean = downside.reduce((a, b) => a + b, 0) / Math.max(1, downside.length);
  const dstd =
    downside.length > 1
      ? Math.sqrt(downside.reduce((a, b) => a + (b - dmean) ** 2, 0) / (downside.length - 1))
      : 0;
  const sortino = dstd > 0 ? (mean / dstd) * Math.sqrt(bpy) : 0;

  const sorted = [...r].sort((a, b) => a - b);
  const var95 = quantile(sorted, 0.05);
  const tail = sorted.filter((x) => x <= var95);
  const es95 = tail.length ? tail.reduce((a, b) => a + b, 0) / tail.length : var95;

  let bestWin = 0;
  let bestLoss = 0;
  let curWin = 0;
  let curLoss = 0;
  for (const x of r) {
    if (x > 0) {
      curWin++;
      curLoss = 0;
    } else if (x < 0) {
      curLoss++;
      curWin = 0;
    } else {
      curWin = 0;
      curLoss = 0;
    }
    bestWin = Math.max(bestWin, curWin);
    bestLoss = Math.max(bestLoss, curLoss);
  }

  let activeBars = 0;
  let activeWins = 0;
  for (let i = 0; i < n; i++) {
    if (pos[i] !== 0) {
      activeBars++;
      if (r[i] > 0) activeWins++;
    }
  }
  let turnoverSum = 0;
  let nTrades = 0;
  for (let i = 0; i < n; i++) {
    turnoverSum += tvr[i];
    if (tvr[i] > 0) nTrades++;
  }

  const phaseTrades = trades.filter((tr) => tr.entryIndex >= from && tr.entryIndex < end);
  const tReturns = phaseTrades.map((tr) => tr.netReturn);
  const wins = tReturns.filter((x) => x > 0);
  const losses = tReturns.filter((x) => x < 0);
  const grossProfit = wins.reduce((a, b) => a + b, 0);
  const grossLoss = -losses.reduce((a, b) => a + b, 0);
  const maes = phaseTrades.map((tr) => tr.mae);
  const mfes = phaseTrades.map((tr) => tr.mfe);
  const meanMae = maes.reduce((a, b) => a + b, 0) / Math.max(1, maes.length);
  const meanMfe = mfes.reduce((a, b) => a + b, 0) / Math.max(1, mfes.length);

  return {
    n_bars: n,
    total_return: totalReturn,
    ann_return: annReturn,
    ann_volatility: annVol,
    sharpe,
    sortino,
    max_drawdown: maxDd,
    calmar: maxDd < 0 ? annReturn / Math.abs(maxDd) : 0,
    exposure: n ? activeBars / n : 0,
    hit_rate: activeBars ? activeWins / activeBars : 0,
    turnover: turnoverSum,
    n_trades: nTrades,
    time_in_drawdown: n ? underBars / n : 0,
    ulcer_index: n ? Math.sqrt(ddSq / n) : 0,
    var_95: var95,
    expected_shortfall_95: es95,
    longest_win_streak: bestWin,
    longest_loss_streak: bestLoss,
    profit_factor: grossLoss > 0 ? grossProfit / grossLoss : wins.length ? Infinity : 0,
    expectancy: tReturns.length ? tReturns.reduce((a, b) => a + b, 0) / tReturns.length : 0,
    trade_hit_rate: tReturns.length ? wins.length / tReturns.length : 0,
    n_trades_closed: tReturns.length,
    mean_duration_bars: phaseTrades.length
      ? phaseTrades.reduce((a, b) => a + b.nBars, 0) / phaseTrades.length
      : 0,
    median_mae: maes.length ? median(maes) : 0,
    median_mfe: mfes.length ? median(mfes) : 0,
    e_ratio: meanMae > 0 ? meanMfe / meanMae : 0,
  };
}

/** Buy-and-hold ledger over the same bars (always long, one entry). */
export function buyAndHold(bars: Bars, costs: CostModel, funding: FundingSeries | null): Ledger {
  const side = new Int8Array(bars.o.length).fill(1);
  return runBacktest(bars, side, costs, funding);
}

/**
 * Circular-shift randomisation test on one ledger slice: rotate the position
 * series to a random start, re-price at the same bar returns, re-charge
 * turnover at the same cost rates and funding at the rotated exposure.
 * Mirrors evaluation/montecarlo.null_circular_shifts. Returns the one-sided
 * p-value for total return with the +1 correction.
 */
export function circularShiftTest(
  ledger: Ledger,
  costs: CostModel,
  from: number,
  to: number,
  nShifts: number,
  seed: number
): { pValue: number; nullReturns: number[]; realReturn: number } {
  const n = to - from;
  const pos = ledger.position.slice(from, to);
  const oo = ledger.ooReturn.slice(from, to);
  const rate = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const p = ledger.position[from + i];
    rate[i] = p !== 0 ? ledger.funding[from + i] / p : 0;
  }
  const feeRate = (costs.feeBpsPerSide + costs.slippageBpsPerSide) / 1e4;

  let real = 1;
  for (let i = 0; i < n; i++) real *= 1 + ledger.net[from + i];
  real -= 1;

  // Mulberry32: tiny deterministic PRNG so the p-value is reproducible.
  let s = seed >>> 0;
  const rand = () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let z = s;
    z = Math.imul(z ^ (z >>> 15), z | 1);
    z ^= z + Math.imul(z ^ (z >>> 7), z | 61);
    return ((z ^ (z >>> 14)) >>> 0) / 4294967296;
  };

  const nullReturns: number[] = [];
  let countGE = 0;
  for (let k = 0; k < nShifts; k++) {
    const offset = 1 + Math.floor(rand() * (n - 1));
    let eq = 1;
    let prev = 0;
    for (let i = 0; i < n; i++) {
      const p = pos[(i + offset) % n];
      const turnover = Math.abs(p - prev);
      const net = p * oo[i] - turnover * feeRate - p * rate[i];
      eq *= 1 + net;
      prev = p;
    }
    const ret = eq - 1;
    nullReturns.push(ret);
    if (ret >= real) countGE++;
  }
  return {
    pValue: (1 + countGE) / (nShifts + 1),
    nullReturns,
    realReturn: real,
  };
}
