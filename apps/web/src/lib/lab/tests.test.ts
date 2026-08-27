// Unit tests for the extended battery: bootstrap determinism, tornado
// structure, and causal regime split.

import { describe, expect, it } from "vitest";

import { runBacktest } from "./engine";
import { STRATEGIES, type Bars } from "./strategies";
import { bootstrapSharpeCI, perturbationTornado, regimeSplit } from "./tests";
import { mulberry32 } from "./walkforward";

function syntheticBars(n: number, drift = 0.0002): Bars {
  const t = Float64Array.from({ length: n }, (_, i) => 1_600_000_000 + i * 3600);
  const o = new Float64Array(n);
  const h = new Float64Array(n);
  const l = new Float64Array(n);
  const c = new Float64Array(n);
  let price = 100;
  const rand = mulberry32(3);
  for (let i = 0; i < n; i++) {
    price *= 1 + drift + (rand() - 0.5) * 0.008;
    o[i] = price;
    c[i] = price;
    h[i] = price * 1.002;
    l[i] = price * 0.998;
  }
  return { t, o, h, l, c };
}

describe("extended battery", () => {
  it("bootstrapSharpeCI is deterministic and brackets the median", () => {
    const bars = syntheticBars(800);
    const side = Int8Array.from({ length: 800 }, () => 1);
    const ledger = runBacktest(bars, side, { feeBpsPerSide: 0, slippageBpsPerSide: 0 }, null);
    const a = bootstrapSharpeCI(ledger.net, 0, ledger.net.length, 100, 42);
    const b = bootstrapSharpeCI(ledger.net, 0, ledger.net.length, 100, 42);
    expect(a).toEqual(b);
    expect(a.lo).toBeLessThanOrEqual(a.median);
    expect(a.median).toBeLessThanOrEqual(a.hi);
  });

  it("perturbationTornado covers each numeric parameter with grid-edge nulls", () => {
    const bars = syntheticBars(600);
    const momentum = STRATEGIES.find((s) => s.id === "momentum")!;
    const values = { fast: 6, slow: 168, direction: "both" };
    const rows = perturbationTornado(
      momentum,
      values,
      bars,
      null,
      { feeBpsPerSide: 4, slippageBpsPerSide: 1 },
      300,
      599,
      0
    );
    expect(rows.map((r) => r.key)).toEqual(["fast", "slow"]);
    // fast=6 is the grid's lower edge: no downward neighbour.
    expect(rows[0].down).toBeNull();
    expect(rows[0].up).not.toBeNull();
  });

  it("regimeSplit uses in-sample tercile boundaries and covers the OOS bars", () => {
    const bars = syntheticBars(1500);
    const side = Int8Array.from({ length: 1500 }, () => 1);
    const ledger = runBacktest(bars, side, { feeBpsPerSide: 0, slippageBpsPerSide: 0 }, null);
    const split = 1000;
    const rows = regimeSplit(bars, ledger, split, ledger.net.length);
    expect(rows).toHaveLength(3);
    const total = rows.reduce((a, r) => a + r.nBars, 0);
    // Every OOS bar with a defined rvol lands in exactly one bucket.
    expect(total).toBe(ledger.net.length - split);
  });
});
