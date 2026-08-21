// Extended test battery for the lab (phase 8c): stationary-bootstrap Sharpe
// CI, parameter-perturbation tornado, and volatility-regime split. All
// deterministic (Mulberry32, fixed seeds) and computed on the real ledgers.

import { runBacktest, type CostModel, type FundingSeries, type Ledger } from "./engine";
import { rollingStd } from "./indicators";
import type { Bars, StrategyDef } from "./strategies";
import { mulberry32 } from "./walkforward";

const BARS_PER_YEAR = 8760;

function sharpeOf(values: number[]): number {
  const n = values.length;
  if (n < 2) return 0;
  const mean = values.reduce((a, b) => a + b, 0) / n;
  const sq = values.reduce((a, b) => a + (b - mean) ** 2, 0);
  const std = Math.sqrt(sq / (n - 1));
  return std > 0 ? (mean / std) * Math.sqrt(BARS_PER_YEAR) : 0;
}

/**
 * Stationary bootstrap (Politis–Romano) of the annualised Sharpe over a
 * ledger slice: geometric block lengths with mean ≈ sqrt(n), wrap-around
 * indexing, deterministic seed. Returns the 95% percentile interval.
 */
export function bootstrapSharpeCI(
  net: Float64Array,
  from: number,
  to: number,
  nBoot = 200,
  seed = 42
): { lo: number; hi: number; median: number } {
  const n = to - from;
  if (n < 20) return { lo: 0, hi: 0, median: 0 };
  const slice = Array.from(net.slice(from, to));
  const meanBlock = Math.max(6, Math.round(Math.sqrt(n)));
  const pRestart = 1 / meanBlock;
  const rand = mulberry32(seed);

  const sharpes: number[] = [];
  for (let b = 0; b < nBoot; b++) {
    const sample = new Array<number>(n);
    let idx = Math.floor(rand() * n);
    for (let i = 0; i < n; i++) {
      sample[i] = slice[idx];
      idx = rand() < pRestart ? Math.floor(rand() * n) : (idx + 1) % n;
    }
    sharpes.push(sharpeOf(sample));
  }
  sharpes.sort((a, b) => a - b);
  const at = (q: number) => sharpes[Math.min(nBoot - 1, Math.floor(q * (nBoot - 1)))];
  return { lo: at(0.025), hi: at(0.975), median: at(0.5) };
}

function sliceReturn(net: Float64Array, from: number, to: number): number {
  let eq = 1;
  for (let i = from; i < to; i++) eq *= 1 + net[i];
  return eq - 1;
}

export interface TornadoRow {
  key: string;
  base: number | string;
  /** OOS return delta when the parameter moves one grid step down / up. */
  down: number | null;
  up: number | null;
}

/**
 * ±1 grid-step perturbation per numeric parameter: how much the OOS return
 * moves when each knob turns one study-grid notch. Fragile configurations
 * show large bars — the study's parameter-perturbation check, interactive.
 */
export function perturbationTornado(
  def: StrategyDef,
  values: Record<string, number | string>,
  bars: Bars,
  funding: FundingSeries | null,
  costs: CostModel,
  from: number,
  to: number,
  baseReturn: number
): TornadoRow[] {
  const rows: TornadoRow[] = [];
  for (const spec of def.params) {
    if (spec.kind === "choice") continue;
    const grid = spec.studyValues as number[];
    const current = Number(values[spec.key]);
    // Position in the grid; fall back to nearest value for free-typed inputs.
    let pos = grid.indexOf(current);
    if (pos < 0) {
      pos = grid.reduce(
        (bestIdx, v, i) =>
          Math.abs(v - current) < Math.abs(grid[bestIdx] - current) ? i : bestIdx,
        0
      );
    }
    const evalAt = (idx: number): number | null => {
      if (idx < 0 || idx >= grid.length) return null;
      const perturbed = { ...values, [spec.key]: grid[idx] };
      const side = def.run(bars, perturbed);
      const ledger = runBacktest(bars, side, costs, funding);
      return sliceReturn(ledger.net, from, Math.min(to, ledger.net.length)) - baseReturn;
    };
    rows.push({
      key: spec.key,
      base: values[spec.key],
      down: evalAt(pos - 1),
      up: evalAt(pos + 1),
    });
  }
  return rows;
}

export interface RegimeRow {
  regime: "low" | "mid" | "high";
  nBars: number;
  totalReturn: number;
  sharpe: number;
}

/**
 * OOS metrics split by volatility regime. The regime label is causal twice
 * over: rvol is a trailing 168h std of log returns, and the tercile
 * boundaries are computed on the in-sample phase only, then applied forward.
 */
export function regimeSplit(bars: Bars, ledger: Ledger, splitIdx: number, to: number): RegimeRow[] {
  const n = ledger.net.length;
  const logRet = new Float64Array(n);
  for (let i = 1; i < n; i++) logRet[i] = Math.log(bars.c[i] / bars.c[i - 1]);
  const rvol = rollingStd(logRet, 168);

  const inSample: number[] = [];
  for (let i = 0; i < splitIdx; i++) if (Number.isFinite(rvol[i])) inSample.push(rvol[i]);
  inSample.sort((a, b) => a - b);
  if (inSample.length < 10) return [];
  const q1 = inSample[Math.floor(inSample.length / 3)];
  const q2 = inSample[Math.floor((2 * inSample.length) / 3)];

  const buckets: Record<"low" | "mid" | "high", number[]> = { low: [], mid: [], high: [] };
  for (let i = splitIdx; i < Math.min(to, n); i++) {
    if (!Number.isFinite(rvol[i])) continue;
    const label = rvol[i] <= q1 ? "low" : rvol[i] <= q2 ? "mid" : "high";
    buckets[label].push(ledger.net[i]);
  }
  return (Object.keys(buckets) as ("low" | "mid" | "high")[]).map((regime) => {
    const values = buckets[regime];
    let eq = 1;
    for (const r of values) eq *= 1 + r;
    return {
      regime,
      nBars: values.length,
      totalReturn: eq - 1,
      sharpe: sharpeOf(values),
    };
  });
}
