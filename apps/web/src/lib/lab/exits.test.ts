// Parity tests for the timed families and the exit/gate overlays (phase 8d).

import { describe, expect, it } from "vitest";

import { applyExitOverlay, applyRegimeGate, applyTrendGate, NO_EXITS } from "./exits";
import {
  evolveTimedPositions,
  fundingAsOf,
  fundingReversalSignals,
  intradaySeasonalitySignals,
  type Bars,
} from "./strategies";

function flatBars(n: number, price = 100): Bars {
  const t = Float64Array.from({ length: n }, (_, i) => 1_600_000_000 + i * 3600);
  return {
    t,
    o: new Float64Array(n).fill(price),
    h: new Float64Array(n).fill(price * 1.001),
    l: new Float64Array(n).fill(price * 0.999),
    c: new Float64Array(n).fill(price),
  };
}

describe("evolveTimedPositions", () => {
  it("holds exactly holding_bars, ignores events while open, cancels ties", () => {
    const le = Uint8Array.from([1, 0, 0, 1, 0, 0, 0, 1, 0]);
    const se = Uint8Array.from([0, 0, 0, 0, 0, 0, 0, 1, 0]);
    const side = evolveTimedPositions(le, se, 3);
    // Opens at 0 for 3 bars; the event at 3 is IGNORED (the Python semantics
    // count the opening bar, so the position covers bars 0-2 and bar 3 is
    // the first free bar => a fresh event at 3 opens again for bars 3-5).
    // Simultaneous long+short at 7 cancels.
    expect(Array.from(side)).toEqual([1, 1, 1, 1, 1, 1, 0, 0, 0]);
  });
});

describe("fundingAsOf", () => {
  it("joins the last rate published at or before each bar open", () => {
    const barT = Float64Array.from([100, 200, 300, 400]);
    const funding = { t: Float64Array.from([150, 300]), rate: Float64Array.from([0.01, -0.02]) };
    const out = fundingAsOf(barT, funding);
    expect(Number.isNaN(out[0])).toBe(true);
    expect(out[1]).toBeCloseTo(0.01);
    expect(out[2]).toBeCloseTo(-0.02); // published exactly at the open counts
    expect(out[3]).toBeCloseTo(-0.02);
  });
});

describe("timed families", () => {
  it("funding_reversal fades the paying side after an extreme", () => {
    const n = 60;
    const bars = flatBars(n);
    // One funding event per bar: mostly ~0, a big positive spike at bar 40.
    const rates = new Float64Array(n).fill(0.0001);
    rates[40] = 0.01;
    const funding = { t: Float64Array.from(bars.t), rate: rates };
    const side = fundingReversalSignals(bars, funding, {
      rankWindow: 24,
      extremePct: 0.9,
      holdingBars: 4,
      minAbsRate: 0,
      direction: "both",
    });
    // The spike reaches bar 40's as-of rate at bar 40... published at open
    // counts, so the short opens at bar 40 (top of its trailing distribution).
    expect(side[40]).toBe(-1);
    expect(side[43]).toBe(-1);
  });

  it("intraday_seasonality enters at the chosen UTC hour and holds", () => {
    const bars = flatBars(72); // t=1_600_000_000 is 12:26:40 UTC... use computed hours
    const hourOf = (i: number) => Math.floor(bars.t[i] / 3600) % 24;
    const target = hourOf(5);
    const side = intradaySeasonalitySignals(bars, {
      entryHour: target,
      holdingBars: 2,
      sideMode: "long",
      trendFilterMa: 0,
    });
    expect(side[5]).toBe(1);
    expect(side[6]).toBe(1);
    expect(side[7]).toBe(0);
  });
});

describe("exit overlays and gates", () => {
  it("time exit flattens the episode after maxBars", () => {
    const bars = flatBars(10);
    const side = Int8Array.from([0, 1, 1, 1, 1, 1, 0, 0, 0, 0]);
    const out = applyExitOverlay(side, bars, { ...NO_EXITS, maxBars: 2 });
    expect(Array.from(out)).toEqual([0, 1, 1, 0, 0, 0, 0, 0, 0, 0]);
  });

  it("stop exit fires when close falls k ATRs below the entry reference", () => {
    const n = 12;
    const bars = flatBars(n);
    // Price collapses from bar 6 onward.
    for (let i = 6; i < n; i++) {
      bars.c[i] = 80;
      bars.o[i] = 80;
      bars.h[i] = 80.5;
      bars.l[i] = 79.5;
    }
    const side = Int8Array.from({ length: n }, (_, i) => (i >= 2 ? 1 : 0));
    const out = applyExitOverlay(side, bars, { ...NO_EXITS, stopAtr: 2, atrWindow: 3 });
    expect(out[5]).toBe(1); // still above the stop
    expect(out[7]).toBe(0); // flattened after the collapse triggers the stop
  });

  it("trend gate zeroes longs below the SMA and regime gate respects labels", () => {
    const n = 300;
    const bars = flatBars(n);
    for (let i = 200; i < n; i++) bars.c[i] = 50; // deep below the SMA(100)
    const side = Int8Array.from({ length: n }, () => 1);
    const gated = applyTrendGate(side, bars, 100);
    expect(gated[250]).toBe(0);

    const labels = Array.from({ length: n }, (_, i) => (i < 150 ? "low" : "high") as const);
    const regimed = applyRegimeGate(side, labels, ["low"]);
    expect(regimed[100]).toBe(1);
    expect(regimed[200]).toBe(0);
  });
});
