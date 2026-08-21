// Tests for the mini walk-forward: determinism, correct winner selection,
// window slicing without overlap, and the chance-Sharpe yardstick.

import { describe, expect, it } from "vitest";

import { STRATEGIES, type Bars } from "./strategies";
import {
  barIndexAt,
  expectedMaxSharpe,
  mulberry32,
  runWalkForward,
  sampleCandidate,
  type FoldSpec,
} from "./walkforward";

function syntheticBars(n: number): Bars {
  const t = Float64Array.from(
    { length: n },
    (_, i) => Date.parse("2020-01-01T00:00:00Z") / 1000 + i * 3600
  );
  const o = new Float64Array(n);
  const h = new Float64Array(n);
  const l = new Float64Array(n);
  const c = new Float64Array(n);
  let price = 100;
  const rand = mulberry32(7);
  for (let i = 0; i < n; i++) {
    price *= 1 + (rand() - 0.495) * 0.01;
    o[i] = price;
    c[i] = price * (1 + (rand() - 0.5) * 0.002);
    h[i] = Math.max(o[i], c[i]) * 1.001;
    l[i] = Math.min(o[i], c[i]) * 0.999;
  }
  return { t, o, h, l, c };
}

function isoAt(bars: Bars, index: number): string {
  return new Date(bars.t[index] * 1000).toISOString();
}

function makeFolds(bars: Bars): FoldSpec[] {
  return [0, 1].map((k) => {
    const valFrom = 400 + k * 400;
    return {
      index: k,
      train_start: isoAt(bars, 0),
      train_end: isoAt(bars, valFrom - 20),
      val_start: isoAt(bars, valFrom),
      val_end: isoAt(bars, valFrom + 180),
      test_start: isoAt(bars, valFrom + 200),
      test_end: isoAt(bars, valFrom + 380),
      purge_bars: 20,
      embargo_bars: 20,
    };
  });
}

const momentum = STRATEGIES.find((s) => s.id === "momentum")!;

describe("walk-forward", () => {
  it("barIndexAt finds the first bar at or after the timestamp", () => {
    const bars = syntheticBars(10);
    expect(barIndexAt(bars.t, isoAt(bars, 3))).toBe(3);
    const between = new Date((bars.t[3] + 1800) * 1000).toISOString();
    expect(barIndexAt(bars.t, between)).toBe(4);
  });

  it("sampleCandidate repairs momentum fast >= slow", () => {
    const rand = mulberry32(1);
    for (let i = 0; i < 200; i++) {
      const values = sampleCandidate(momentum.params, rand);
      expect(Number(values.fast)).toBeLessThan(Number(values.slow));
    }
  });

  it("is deterministic for a fixed seed and differs across seeds", () => {
    const bars = syntheticBars(1200);
    const folds = makeFolds(bars);
    const base = {
      bars,
      funding: null,
      def: momentum,
      folds,
      costs: { feeBpsPerSide: 4, slippageBpsPerSide: 1 },
      budgetPerFold: 8,
    };
    const a = runWalkForward({ ...base, seed: 42 });
    const b = runWalkForward({ ...base, seed: 42 });
    const c = runWalkForward({ ...base, seed: 137 });
    expect(a.oosTotalReturn).toBe(b.oosTotalReturn);
    expect(a.folds.map((f) => f.winner)).toEqual(b.folds.map((f) => f.winner));
    // A different seed samples different candidates (overwhelmingly likely).
    expect(JSON.stringify(a.folds)).not.toEqual(JSON.stringify(c.folds));
  });

  it("concatenates exactly the test windows", () => {
    const bars = syntheticBars(1200);
    const folds = makeFolds(bars);
    const result = runWalkForward({
      bars,
      funding: null,
      def: momentum,
      folds,
      costs: { feeBpsPerSide: 0, slippageBpsPerSide: 0 },
      seed: 42,
      budgetPerFold: 4,
    });
    const expected = folds.reduce(
      (total, f) => total + (barIndexAt(bars.t, f.test_end) - barIndexAt(bars.t, f.test_start)),
      0
    );
    expect(result.oosCurve.length).toBe(expected);
    expect(result.folds).toHaveLength(2);
    expect(result.nEvaluations).toBe(8);
  });

  it("expectedMaxSharpe grows with tries and shrinks with sample size", () => {
    expect(expectedMaxSharpe(100, 30000)).toBeGreaterThan(expectedMaxSharpe(10, 30000));
    expect(expectedMaxSharpe(100, 60000)).toBeLessThan(expectedMaxSharpe(100, 30000));
    expect(expectedMaxSharpe(0, 100)).toBe(0);
  });
});
