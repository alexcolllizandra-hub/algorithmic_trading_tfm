import { describe, expect, it } from "vitest";

import { baseAsset, holdoutBoundary, type Partition } from "@/lib/site-data";

const point = (t: string, p: Partition) => ({ t, p });

describe("baseAsset", () => {
  it("strips the quote currency", () => {
    expect(baseAsset("BTCUSDT")).toBe("BTC");
    expect(baseAsset("ETHUSDT")).toBe("ETH");
  });

  it("leaves anything else alone", () => {
    expect(baseAsset("BTC")).toBe("BTC");
    expect(baseAsset("USDTBTC")).toBe("USDTBTC");
  });
});

describe("holdoutBoundary", () => {
  it("finds the first frozen day so the chart can shade from there", () => {
    const points = [
      point("2025-12-30", "development"),
      point("2025-12-31", "development"),
      point("2026-01-01", "holdout"),
      point("2026-01-02", "holdout"),
    ];
    expect(holdoutBoundary(points)).toBe("2026-01-01");
  });

  it("returns null when the export stopped at the holdout", () => {
    const points = [point("2025-12-30", "development"), point("2025-12-31", "development")];
    expect(holdoutBoundary(points)).toBeNull();
  });

  it("returns null for an empty series", () => {
    expect(holdoutBoundary([])).toBeNull();
  });
});
