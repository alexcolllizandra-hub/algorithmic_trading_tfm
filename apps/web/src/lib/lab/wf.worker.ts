// Web Worker running the multi-seed walk-forward mini-search off the main
// thread. Receives typed-array buffers (transferred, not copied), runs the
// seeds sequentially, and streams progress messages back to the page.

import type { CostModel, FundingSeries } from "./engine";
import { STRATEGIES, type Bars, type StrategyId } from "./strategies";
import { runWalkForward, type FoldSpec, type WalkForwardResult } from "./walkforward";

export interface WfRequest {
  type: "run";
  strategyId: StrategyId;
  bars: { t: ArrayBuffer; o: ArrayBuffer; h: ArrayBuffer; l: ArrayBuffer; c: ArrayBuffer };
  funding: { t: ArrayBuffer; rate: ArrayBuffer } | null;
  folds: FoldSpec[];
  costs: CostModel;
  seeds: number[];
  budgetPerFold: number;
}

export type WfResponse =
  | {
      type: "progress";
      seed: number;
      seedIndex: number;
      nSeeds: number;
      done: number;
      total: number;
    }
  | { type: "done"; results: WalkForwardResult[] }
  | { type: "error"; message: string };

self.onmessage = (event: MessageEvent<WfRequest>) => {
  const msg = event.data;
  if (msg.type !== "run") return;
  try {
    const bars: Bars = {
      t: new Float64Array(msg.bars.t),
      o: new Float64Array(msg.bars.o),
      h: new Float64Array(msg.bars.h),
      l: new Float64Array(msg.bars.l),
      c: new Float64Array(msg.bars.c),
    };
    const funding: FundingSeries | null = msg.funding
      ? { t: new Float64Array(msg.funding.t), rate: new Float64Array(msg.funding.rate) }
      : null;
    const def = STRATEGIES.find((s) => s.id === msg.strategyId);
    if (!def) throw new Error(`unknown strategy ${msg.strategyId}`);

    const results: WalkForwardResult[] = [];
    msg.seeds.forEach((seed, seedIndex) => {
      const result = runWalkForward({
        bars,
        funding,
        def,
        folds: msg.folds,
        costs: msg.costs,
        seed,
        budgetPerFold: msg.budgetPerFold,
        onProgress: (done, total) => {
          const progress: WfResponse = {
            type: "progress",
            seed,
            seedIndex,
            nSeeds: msg.seeds.length,
            done,
            total,
          };
          (self as unknown as Worker).postMessage(progress);
        },
      });
      results.push(result);
    });
    const done: WfResponse = { type: "done", results };
    (self as unknown as Worker).postMessage(done);
  } catch (error) {
    const fail: WfResponse = { type: "error", message: String(error) };
    (self as unknown as Worker).postMessage(fail);
  }
};
