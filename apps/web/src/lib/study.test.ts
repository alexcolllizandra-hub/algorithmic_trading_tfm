import { describe, expect, it } from "vitest";

import type { StudyFamilyDetail, StudyFamilySummary, StudyMonteCarlo } from "@/lib/api-types";
import {
  ALL,
  criterionPercent,
  crossAssetRows,
  distinctValues,
  fanDomain,
  filterFamilies,
  gaugePercent,
  monteCarloRows,
  seedEquitySeries,
  seedReturnSpread,
  sortFamilies,
  splitFamilyKey,
  statusDescriptor,
  terminalDistribution,
} from "@/lib/study";

function family(overrides: Partial<StudyFamilySummary>): StudyFamilySummary {
  return {
    key: "f|BTCUSDT",
    family: "f",
    gate: "R3",
    symbol: "BTCUSDT",
    thesis: "",
    n_seeds: 10,
    n_bars: 100,
    total_return: 0,
    sharpe: 0,
    max_drawdown: -0.1,
    p_value: 0.5,
    holm_adjusted_p: 1,
    bh_adjusted_p: 1,
    survives_correction: false,
    verdict: "REJECTED",
    gate_note: null,
    criteria: null,
    buy_and_hold_return: null,
    ...overrides,
  };
}

const rows = [
  family({ key: "a|BTCUSDT", family: "a", total_return: 0.1, sharpe: 0.5, p_value: 0.3 }),
  family({
    key: "b|ETHUSDT",
    family: "b",
    symbol: "ETHUSDT",
    gate: "S2",
    total_return: -0.4,
    sharpe: -1.2,
    p_value: null,
  }),
  family({ key: "c|BTCUSDT", family: "c", total_return: -0.1, sharpe: -0.2, p_value: 0.9 }),
];

describe("family key", () => {
  it("splits family|SYMBOL", () => {
    expect(splitFamilyKey("volatility_breakout|BTCUSDT")).toEqual({
      family: "volatility_breakout",
      symbol: "BTCUSDT",
    });
  });

  it("tolerates a key without a symbol", () => {
    expect(splitFamilyKey("momentum")).toEqual({ family: "momentum", symbol: "" });
  });
});

describe("master table filtering and sorting", () => {
  it("lists distinct categorical values alphabetically", () => {
    expect(distinctValues(rows, "gate")).toEqual(["R3", "S2"]);
    expect(distinctValues(rows, "symbol")).toEqual(["BTCUSDT", "ETHUSDT"]);
  });

  it("applies every filter, with a sentinel meaning 'all'", () => {
    expect(filterFamilies(rows, { gate: ALL, symbol: ALL, verdict: ALL })).toHaveLength(3);
    expect(filterFamilies(rows, { gate: "R3", symbol: ALL, verdict: ALL })).toHaveLength(2);
    expect(
      filterFamilies(rows, { gate: ALL, symbol: "ETHUSDT", verdict: "REJECTED" }).map((r) => r.key)
    ).toEqual(["b|ETHUSDT"]);
  });

  it("sorts descending and ascending", () => {
    expect(sortFamilies(rows, "total_return", "desc").map((r) => r.key)).toEqual([
      "a|BTCUSDT",
      "c|BTCUSDT",
      "b|ETHUSDT",
    ]);
    expect(sortFamilies(rows, "sharpe", "asc").map((r) => r.key)).toEqual([
      "b|ETHUSDT",
      "c|BTCUSDT",
      "a|BTCUSDT",
    ]);
  });

  it("keeps missing values last in both directions", () => {
    expect(sortFamilies(rows, "p_value", "asc").map((r) => r.key)).toEqual([
      "a|BTCUSDT",
      "c|BTCUSDT",
      "b|ETHUSDT",
    ]);
    expect(sortFamilies(rows, "p_value", "desc").map((r) => r.key)).toEqual([
      "c|BTCUSDT",
      "a|BTCUSDT",
      "b|ETHUSDT",
    ]);
  });

  it("does not mutate the input array", () => {
    const before = rows.map((r) => r.key);
    sortFamilies(rows, "total_return", "asc");
    expect(rows.map((r) => r.key)).toEqual(before);
  });
});

describe("cross-asset rows", () => {
  it("returns every asset a family was tested on, ordered by symbol", () => {
    const both = [
      family({ key: "x|ETHUSDT", family: "x", symbol: "ETHUSDT" }),
      family({ key: "x|BTCUSDT", family: "x", symbol: "BTCUSDT" }),
      family({ key: "y|BTCUSDT", family: "y" }),
    ];
    expect(crossAssetRows(both, "x").map((r) => r.symbol)).toEqual(["BTCUSDT", "ETHUSDT"]);
    expect(crossAssetRows(both, "y")).toHaveLength(1);
  });
});

const detail: StudyFamilyDetail = {
  ...family({ key: "vb|BTCUSDT", family: "vb" }),
  equity: [
    { t: "2024-01-01T00:00:00+00:00", equity: 1 },
    { t: "2024-01-03T00:00:00+00:00", equity: 1.1 },
  ],
  seeds: [
    {
      seed: 2,
      total_return: -0.2,
      sharpe: -0.5,
      max_drawdown: -0.3,
      n_bars: 2,
      equity: [{ t: "2024-01-02T00:00:00+00:00", equity: 0.8 }],
    },
    {
      seed: 1,
      total_return: 0.3,
      sharpe: 0.4,
      max_drawdown: -0.1,
      n_bars: 2,
      equity: [{ t: "2024-01-01T00:00:00+00:00", equity: 1 }],
    },
  ],
  monte_carlo: {} as StudyMonteCarlo,
  min_trades_veto: null,
};

describe("seed equity series", () => {
  it("merges the average and every seed onto one time axis", () => {
    const { rows: merged, seedKeys, averageKey } = seedEquitySeries(detail);
    expect(seedKeys).toEqual(["seed_1", "seed_2"]);
    expect(merged.map((r) => r.x)).toEqual([
      Date.parse("2024-01-01T00:00:00+00:00"),
      Date.parse("2024-01-02T00:00:00+00:00"),
      Date.parse("2024-01-03T00:00:00+00:00"),
    ]);
    expect(merged[0][averageKey]).toBe(1);
    expect(merged[0].seed_1).toBe(1);
    expect(merged[0].seed_2).toBeNull();
    expect(merged[1][averageKey]).toBeNull();
    expect(merged[1].seed_2).toBe(0.8);
  });

  it("reports the spread of per-seed terminal returns", () => {
    expect(seedReturnSpread(detail)).toEqual({ min: -0.2, max: 0.3 });
    expect(seedReturnSpread({ ...detail, seeds: [] })).toBeNull();
  });
});

const mc: StudyMonteCarlo = {
  method: "stationary_bootstrap",
  n_paths: 10,
  expected_block_bars: 24,
  seed: 1,
  measures: "path_risk_not_significance",
  checkpoint_index: [0, 10],
  bands: {
    p05: [0.9, 0.7],
    p25: [0.95, 0.85],
    p50: [1, 1],
    p75: [1.05, 1.15],
    p95: [1.1, 1.3],
  },
  observed: [1, 1.05],
  terminal: {
    observed_total_return: 0.05,
    p05: -0.3,
    p25: -0.15,
    p50: 0,
    p75: 0.15,
    p95: 0.3,
    probability_positive: 0.5,
  },
};

describe("monte carlo fan", () => {
  it("builds stacked band heights from the quantiles", () => {
    const fan = monteCarloRows(mc);
    expect(fan).toHaveLength(2);
    expect(fan[1]).toMatchObject({ x: 10, p05: 0.7, p95: 1.3, observed: 1.05 });
    expect(fan[1].span0595).toBeCloseTo(0.6, 10);
    expect(fan[1].span2575).toBeCloseTo(0.3, 10);
  });

  it("tolerates a missing band without inventing a value", () => {
    const fan = monteCarloRows({ ...mc, bands: { p50: [1, 1] } });
    expect(fan[0].p05).toBeNull();
    expect(fan[0].span0595).toBeNull();
  });

  it("keeps the y-domain around the data instead of anchoring it at zero", () => {
    const [low, high] = fanDomain(monteCarloRows(mc));
    expect(low).toBeGreaterThan(0.5);
    expect(low).toBeLessThan(0.7);
    expect(high).toBeGreaterThan(1.3);
  });

  it("orders the terminal distribution from p05 to p95", () => {
    expect(terminalDistribution(mc.terminal).map((r) => r.key)).toEqual([
      "p05",
      "p25",
      "p50",
      "p75",
      "p95",
    ]);
  });
});

describe("gauges", () => {
  it("scales criterion bars and clamps out-of-range input", () => {
    expect(criterionPercent(6, 10)).toBe(60);
    expect(criterionPercent(11, 10)).toBe(100);
    expect(criterionPercent(1, 0)).toBe(0);
  });

  it("places a value on a 0..1 gauge", () => {
    expect(gaugePercent(0.5)).toBe(50);
    expect(gaugePercent(null)).toBe(0);
    expect(gaugePercent(2)).toBe(100);
  });
});

describe("status vocabulary", () => {
  it("maps every backend state to a Spanish label and a tone", () => {
    expect(statusDescriptor("HOLDOUT_LOCKED")).toEqual({
      code: "HOLDOUT_LOCKED",
      label: "Holdout bloqueado",
      tone: "warn",
    });
    expect(statusDescriptor("REJECTED").tone).toBe("negative");
    expect(statusDescriptor("AUDITED").tone).toBe("positive");
    expect(statusDescriptor("EXECUTED").label).toBe("Ejecutado");
    expect(statusDescriptor("NOT_EXECUTED").label).toBe("No ejecutado");
    expect(statusDescriptor("SKIPPED").label).toBe("Omitido");
    expect(statusDescriptor("INVALIDATED").label).toBe("Invalidado");
  });

  it("falls back to NOT_AVAILABLE instead of a zero or an empty badge", () => {
    expect(statusDescriptor(null).code).toBe("NOT_AVAILABLE");
    expect(statusDescriptor("").label).toBe("No disponible");
  });

  it("shows an unknown code verbatim rather than hiding it", () => {
    expect(statusDescriptor("BRAND_NEW_STATE")).toEqual({
      code: "BRAND_NEW_STATE",
      label: "BRAND_NEW_STATE",
      tone: "neutral",
    });
  });
});
