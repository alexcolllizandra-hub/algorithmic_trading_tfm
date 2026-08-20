// Parity tests for the lab engine against hand-computed values that mirror
// the Python engine's documented semantics (backtesting/engine.py).

import { describe, expect, it } from "vitest";

import {
  buyAndHold,
  circularShiftTest,
  computeMetrics,
  extractTrades,
  runBacktest,
} from "./engine";
import { rollingMax, rollingStd, sma, zscore } from "./indicators";
import {
  breakoutSignals,
  evolvePositions,
  meanReversionSignals,
  momentumSignals,
  type Bars,
} from "./strategies";

function makeBars(opens: number[], highs?: number[], lows?: number[], closes?: number[]): Bars {
  const n = opens.length;
  const t = Float64Array.from({ length: n }, (_, i) => 1_600_000_000 + i * 3600);
  const o = Float64Array.from(opens);
  const c = closes ? Float64Array.from(closes) : o.slice();
  const h = highs ? Float64Array.from(highs) : Float64Array.from(opens.map((x) => x * 1.01));
  const l = lows ? Float64Array.from(lows) : Float64Array.from(opens.map((x) => x * 0.99));
  return { t, o, h, l, c };
}

describe("indicators", () => {
  it("sma matches a hand computation and marks warm-up as NaN", () => {
    const out = sma(Float64Array.from([1, 2, 3, 4, 5]), 3);
    expect(Number.isNaN(out[0])).toBe(true);
    expect(Number.isNaN(out[1])).toBe(true);
    expect(out[2]).toBeCloseTo(2);
    expect(out[4]).toBeCloseTo(4);
  });

  it("rollingStd uses the sample estimator (ddof=1) like polars", () => {
    const out = rollingStd(Float64Array.from([1, 2, 3, 4]), 3);
    // std([1,2,3], ddof=1) = 1
    expect(out[2]).toBeCloseTo(1);
    expect(out[3]).toBeCloseTo(1);
  });

  it("zscore is (x - mean)/std over the trailing window", () => {
    const out = zscore(Float64Array.from([1, 2, 3, 6]), 3);
    // window [2,3,6]: mean=11/3, std=sqrt(13/3)... check numerically
    const mean = 11 / 3;
    const std = Math.sqrt(((2 - mean) ** 2 + (3 - mean) ** 2 + (6 - mean) ** 2) / 2);
    expect(out[3]).toBeCloseTo((6 - mean) / std);
  });

  it("rollingMax honours the window", () => {
    const out = rollingMax(Float64Array.from([5, 1, 4, 2, 3]), 2);
    expect(out[1]).toBe(5);
    expect(out[2]).toBe(4);
    expect(out[4]).toBe(3);
  });
});

describe("evolvePositions", () => {
  it("opens, reverses on opposite entry, and exits to flat", () => {
    const le = Uint8Array.from([1, 0, 0, 0, 0]);
    const se = Uint8Array.from([0, 0, 1, 0, 0]);
    const ex = Uint8Array.from([0, 0, 0, 0, 1]);
    expect(Array.from(evolvePositions(le, se, ex))).toEqual([1, 1, -1, -1, 0]);
  });
});

describe("runBacktest", () => {
  it("executes next-open, charges turnover, drops the final bar", () => {
    const bars = makeBars([100, 100, 110, 121]);
    // side decided at close of each bar; long from bar0.
    const side = Int8Array.from([1, 1, 1, 1]);
    const ledger = runBacktest(bars, side, { feeBpsPerSide: 0, slippageBpsPerSide: 0 }, null);
    // n = 3 (last bar dropped). position = [0, 1, 1].
    expect(Array.from(ledger.position)).toEqual([0, 1, 1]);
    expect(ledger.net[0]).toBeCloseTo(0); // flat bar earns nothing
    expect(ledger.net[1]).toBeCloseTo(0.1); // 110 -> 121? no: bar1 open 100 -> bar2 open 110
    expect(ledger.net[2]).toBeCloseTo(0.1); // 110 -> 121
    expect(ledger.equity[2]).toBeCloseTo(1.21);
  });

  it("a long->short flip pays two units of turnover", () => {
    const bars = makeBars([100, 100, 100, 100, 100]);
    const side = Int8Array.from([1, -1, -1, 0, 0]);
    const ledger = runBacktest(bars, side, { feeBpsPerSide: 10, slippageBpsPerSide: 0 }, null);
    // positions: [0, 1, -1, -1]; turnover: [0, 1, 2, 0]
    expect(Array.from(ledger.turnover)).toEqual([0, 1, 2, 0]);
    expect(ledger.fee[2]).toBeCloseTo(2 * 0.001);
  });

  it("funding settles into the bar whose interval contains the event", () => {
    const bars = makeBars([100, 100, 100, 100]);
    const funding = {
      t: Float64Array.from([bars.t[1] + 1800]), // settles inside bar 1
      rate: Float64Array.from([0.01]),
    };
    const side = Int8Array.from([1, 1, 1, 1]);
    const ledger = runBacktest(bars, side, { feeBpsPerSide: 0, slippageBpsPerSide: 0 }, funding);
    expect(ledger.funding[1]).toBeCloseTo(0.01); // long pays positive funding
    expect(ledger.net[1]).toBeCloseTo(-0.01);
    expect(ledger.funding[0]).toBeCloseTo(0);
  });
});

describe("trades and MAE/MFE", () => {
  it("extracts entries at execution price with excursions from highs/lows", () => {
    const bars = makeBars(
      [100, 100, 108, 104], // opens
      [101, 112, 112, 105], // highs
      [99, 98, 103, 100] // lows
    );
    const side = Int8Array.from([1, 1, 0, 0]); // long decided at bar0 close, flat at bar2
    const ledger = runBacktest(bars, side, { feeBpsPerSide: 0, slippageBpsPerSide: 0 }, null);
    const trades = extractTrades(ledger, bars);
    expect(trades).toHaveLength(1);
    const trade = trades[0];
    expect(trade.entryPrice).toBe(100); // open of bar 1
    expect(trade.nBars).toBe(2); // held over bars 1-2
    expect(trade.mfe).toBeCloseTo(0.12); // high 112 vs entry 100
    expect(trade.mae).toBeCloseTo(0.02); // low 98 vs entry 100
  });
});

describe("strategies", () => {
  it("momentum goes long when fast SMA is above slow", () => {
    const rising = Array.from({ length: 20 }, (_, i) => 100 + i * 2);
    const bars = makeBars(rising, undefined, undefined, rising);
    const side = momentumSignals(bars, { fast: 3, slow: 6, direction: "both" });
    expect(side[19]).toBe(1);
    expect(side[3]).toBe(0); // slow SMA still warming up
  });

  it("mean reversion shorts a rich z-score and exits inside the band", () => {
    const closes = [...Array.from({ length: 10 }, () => 100), 130, 100, 100];
    const bars = makeBars(closes, undefined, undefined, closes);
    const side = meanReversionSignals(bars, {
      zscoreWindow: 5,
      entryZ: 1.5,
      exitZ: 0.5,
      direction: "both",
    });
    expect(side[10]).toBe(-1); // spike -> short
  });

  it("breakout enters above the prior channel high", () => {
    const closes = [...Array.from({ length: 8 }, () => 100), 120, 121];
    const bars = makeBars(
      closes,
      closes.map((c) => c + 1),
      closes.map((c) => c - 1),
      closes
    );
    const side = breakoutSignals(bars, {
      channelWindow: 5,
      confirmationBars: 1,
      direction: "both",
    });
    expect(side[8]).toBe(1);
  });
});

describe("phase metrics and null test", () => {
  it("computeMetrics compounds the slice and buyAndHold matches the market", () => {
    const opens = [100, 110, 121, 133.1, 146.41];
    const bars = makeBars(opens);
    const bh = buyAndHold(bars, { feeBpsPerSide: 0, slippageBpsPerSide: 0 }, null);
    const trades = extractTrades(bh, bars);
    const metrics = computeMetrics(bh, trades, 1, 4); // bars 1..3: +10% x3
    expect(metrics.total_return).toBeCloseTo(1.331 - 1, 6);
  });

  it("circularShiftTest is deterministic for a fixed seed", () => {
    const opens = Array.from(
      { length: 200 },
      (_, i) => 100 * (1 + 0.001 * Math.sin(i / 5)) + i * 0.05
    );
    const bars = makeBars(opens);
    const side = Int8Array.from(opens.map((_, i) => (i % 7 < 3 ? 1 : 0)).slice(0, opens.length));
    const costs = { feeBpsPerSide: 4, slippageBpsPerSide: 1 };
    const ledger = runBacktest(bars, side, costs, null);
    const a = circularShiftTest(ledger, costs, 0, ledger.net.length, 100, 42);
    const b = circularShiftTest(ledger, costs, 0, ledger.net.length, 100, 42);
    expect(a.pValue).toBe(b.pValue);
    expect(a.pValue).toBeGreaterThan(0);
    expect(a.pValue).toBeLessThanOrEqual(1);
  });
});
