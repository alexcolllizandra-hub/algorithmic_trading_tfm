import { describe, expect, it } from "vitest";

import { FIXTURES } from "@/mock/fixtures";
import type { ComparisonResponse, RunListResponse } from "@/lib/api-types";

// Lightweight contract check: the mock fixtures (which mirror the API schema)
// must satisfy the TypeScript response contracts. A shape drift here signals the
// api-types.ts mirror has fallen out of sync with the fixtures/API.
describe("API contract (fixtures vs types)", () => {
  it("run list matches RunListResponse", () => {
    const runs = FIXTURES["/runs"] as RunListResponse;
    expect(runs.items.length).toBeGreaterThan(0);
    const r = runs.items[0];
    for (const key of [
      "run_id",
      "kind",
      "label",
      "family",
      "algorithm",
      "symbol",
      "timeframe",
      "has_comparison",
    ]) {
      expect(r).toHaveProperty(key);
    }
  });

  it("comparison matches ComparisonResponse and fair-budget invariant", () => {
    const key = Object.keys(FIXTURES).find((k) => k.endsWith("/comparison"))!;
    const cmp = FIXTURES[key] as ComparisonResponse;
    expect(cmp.methods.length).toBe(2);
    expect(cmp.fair_budget).toHaveProperty("ok");
    for (const row of cmp.fair_budget.rows) {
      // evaluated must never exceed budget in a fair comparison.
      if (row.budget != null && row.evaluated != null) {
        expect(row.evaluated).toBeLessThanOrEqual(row.budget);
      }
    }
  });
});
