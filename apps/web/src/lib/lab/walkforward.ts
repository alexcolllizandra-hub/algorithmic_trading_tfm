// Walk-forward mini-search for the browser lab (phase 8a of the panel
// restructure): the study's own protocol, miniaturised. Candidates are
// sampled from the family's parameter space with a per-seed deterministic
// PRNG; in every fold the winner is chosen on the validation window (highest
// validation Sharpe — a declared simplification of the study's penalised
// fitness) and evaluated once on the test window it has never seen. Fold
// dates, purge and embargo come verbatim from a committed study run via
// /data/lab/folds.json; signals are computed causally on the full series, so
// evaluation windows only slice the ledger.

import { runBacktest, type CostModel, type FundingSeries, type Ledger } from "./engine";
import type { Bars, ParamSpec, StrategyDef } from "./strategies";

export interface FoldSpec {
  index: number;
  train_start: string;
  train_end: string;
  val_start: string;
  val_end: string;
  test_start: string;
  test_end: string;
  purge_bars: number;
  embargo_bars: number;
}

export interface FoldsFile {
  source_run: string;
  n_folds: number;
  folds: FoldSpec[];
  generated_at: string;
}

export interface FoldResult {
  fold: number;
  testStart: string;
  winner: Record<string, number | string>;
  valSharpe: number;
  testReturn: number;
  testSharpe: number;
}

export interface WalkForwardResult {
  seed: number;
  nCandidates: number;
  nEvaluations: number;
  folds: FoldResult[];
  /** Concatenated test-window equity curve (starts at 1). */
  oosCurve: number[];
  oosTotalReturn: number;
  oosSharpe: number;
}

/** Mulberry32: the lab's deterministic PRNG (same as the circular-shift test). */
export function mulberry32(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let z = s;
    z = Math.imul(z ^ (z >>> 15), z | 1);
    z ^= z + Math.imul(z ^ (z >>> 7), z | 61);
    return ((z ^ (z >>> 14)) >>> 0) / 4294967296;
  };
}

/** Sample one candidate from the family's study grid with the given PRNG. */
export function sampleCandidate(
  params: ParamSpec[],
  rand: () => number
): Record<string, number | string> {
  const values: Record<string, number | string> = {};
  for (const spec of params) {
    const pick = spec.studyValues[Math.floor(rand() * spec.studyValues.length)];
    values[spec.key] = pick;
  }
  // Family-level repair mirroring the Python space: momentum needs fast < slow.
  if (typeof values.fast === "number" && typeof values.slow === "number") {
    if (Number(values.fast) >= Number(values.slow)) {
      const fasts = (params.find((p) => p.key === "fast")?.studyValues ?? []) as number[];
      const smaller = fasts.filter((f) => f < Number(values.slow));
      values.fast = smaller.length ? smaller[smaller.length - 1] : fasts[0];
    }
  }
  // mean_reversion needs exit_z < entry_z.
  if (typeof values.entryZ === "number" && typeof values.exitZ === "number") {
    if (Number(values.exitZ) >= Number(values.entryZ)) {
      const exits = (params.find((p) => p.key === "exitZ")?.studyValues ?? []) as number[];
      const smaller = exits.filter((e) => e < Number(values.entryZ));
      values.exitZ = smaller.length ? smaller[smaller.length - 1] : exits[0];
    }
  }
  // volatility_breakout stop mode needs exitAtr < entryAtr.
  if (
    values.exitMode === "volatility_stop" &&
    typeof values.entryAtr === "number" &&
    typeof values.exitAtr === "number" &&
    Number(values.exitAtr) >= Number(values.entryAtr)
  ) {
    const exits = (params.find((p) => p.key === "exitAtr")?.studyValues ?? []) as number[];
    const smaller = exits.filter((e) => e < Number(values.entryAtr));
    values.exitAtr = smaller.length ? smaller[smaller.length - 1] : exits[0];
  }
  return values;
}

function paramHash(values: Record<string, number | string>): string {
  return Object.keys(values)
    .sort()
    .map((k) => `${k}=${values[k]}`)
    .join("|");
}

/** First bar index with open time >= the ISO timestamp. */
export function barIndexAt(barT: Float64Array, iso: string): number {
  const target = Date.parse(iso) / 1000;
  let lo = 0;
  let hi = barT.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (barT[mid] < target) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

function sliceSharpe(net: Float64Array, from: number, to: number): number {
  const n = to - from;
  if (n < 2) return 0;
  let sum = 0;
  for (let i = from; i < to; i++) sum += net[i];
  const mean = sum / n;
  let sq = 0;
  for (let i = from; i < to; i++) sq += (net[i] - mean) ** 2;
  const std = Math.sqrt(sq / (n - 1));
  return std > 0 ? (mean / std) * Math.sqrt(8760) : 0;
}

function sliceReturn(net: Float64Array, from: number, to: number): number {
  let eq = 1;
  for (let i = from; i < to; i++) eq *= 1 + net[i];
  return eq - 1;
}

export interface WalkForwardInput {
  bars: Bars;
  funding: FundingSeries | null;
  def: StrategyDef;
  folds: FoldSpec[];
  costs: CostModel;
  seed: number;
  /** Candidates sampled per fold (the study's per-fold budget was 100). */
  budgetPerFold: number;
  onProgress?: (done: number, total: number) => void;
}

/**
 * Run the mini walk-forward: per fold, sample `budgetPerFold` candidates,
 * pick the best validation Sharpe, score it once on the fold's test window.
 * Ledgers are cached per parameter set, so repeated candidates are free.
 */
export function runWalkForward(input: WalkForwardInput): WalkForwardResult {
  const { bars, funding, def, folds, costs, seed, budgetPerFold, onProgress } = input;
  const rand = mulberry32(seed);
  const cache = new Map<string, Ledger>();
  let evaluations = 0;
  const total = folds.length * budgetPerFold;

  const ledgerFor = (values: Record<string, number | string>): Ledger => {
    const key = paramHash(values);
    const hit = cache.get(key);
    if (hit) return hit;
    const side = def.run(bars, values);
    const ledger = runBacktest(bars, side, costs, funding);
    cache.set(key, ledger);
    return ledger;
  };

  const foldResults: FoldResult[] = [];
  const oosNet: number[] = [];

  for (const fold of folds) {
    const valFrom = barIndexAt(bars.t, fold.val_start);
    const valTo = barIndexAt(bars.t, fold.val_end);
    const testFrom = barIndexAt(bars.t, fold.test_start);
    const testTo = barIndexAt(bars.t, fold.test_end);

    let best: { values: Record<string, number | string>; sharpe: number } | null = null;
    for (let c = 0; c < budgetPerFold; c++) {
      const values = sampleCandidate(def.params, rand);
      const ledger = ledgerFor(values);
      const valSharpe = sliceSharpe(ledger.net, valFrom, Math.min(valTo, ledger.net.length));
      evaluations++;
      if (onProgress && evaluations % 25 === 0) onProgress(evaluations, total);
      if (!best || valSharpe > best.sharpe) best = { values, sharpe: valSharpe };
    }

    const winnerLedger = ledgerFor(best!.values);
    const tTo = Math.min(testTo, winnerLedger.net.length);
    for (let i = testFrom; i < tTo; i++) oosNet.push(winnerLedger.net[i]);
    foldResults.push({
      fold: fold.index,
      testStart: fold.test_start.slice(0, 10),
      winner: best!.values,
      valSharpe: best!.sharpe,
      testReturn: sliceReturn(winnerLedger.net, testFrom, tTo),
      testSharpe: sliceSharpe(winnerLedger.net, testFrom, tTo),
    });
  }
  onProgress?.(total, total);

  const oosCurve: number[] = [];
  let eq = 1;
  for (const r of oosNet) {
    eq *= 1 + r;
    oosCurve.push(eq);
  }
  const oosArr = Float64Array.from(oosNet);
  return {
    seed,
    nCandidates: cache.size,
    nEvaluations: evaluations,
    folds: foldResults,
    oosCurve,
    oosTotalReturn: eq - 1,
    oosSharpe: sliceSharpe(oosArr, 0, oosArr.length),
  };
}

/**
 * Expected maximum Sharpe of N independent no-skill tries (the attempts
 * counter's honest yardstick). Simplified Bailey–López de Prado bound:
 * E[max SR] ≈ sqrt(2 ln N / T) annualised, with T the number of bars.
 */
export function expectedMaxSharpe(nTries: number, nBars: number): number {
  if (nTries < 1 || nBars < 2) return 0;
  return Math.sqrt((2 * Math.log(Math.max(2, nTries))) / nBars) * Math.sqrt(8760);
}
