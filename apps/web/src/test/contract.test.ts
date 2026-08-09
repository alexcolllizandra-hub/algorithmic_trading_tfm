import { describe, expect, it } from "vitest";

import { FIXTURES } from "@/mock/fixtures";
import type {
  ComparisonResponse,
  RunListResponse,
  SearchAnalyticsResponse,
} from "@/lib/api-types";

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
      "protocol",
      "contaminated",
    ]) {
      expect(r).toHaveProperty(key);
    }
  });

  it("comparison matches ComparisonResponse and the per-fold fair-budget invariant", () => {
    const key = Object.keys(FIXTURES).find((k) => k.endsWith("/comparison"))!;
    const cmp = FIXTURES[key] as ComparisonResponse;
    expect(cmp.methods.length).toBe(2);
    expect(cmp.fair_budget).toHaveProperty("ok");
    expect(cmp.fair_budget.parity_level).toBe("per outer fold");

    // The budget is a PER-FOLD quantity spent in full inside every outer fold, so
    // the reported total is budget x folds. Every engine must land on the same
    // total, otherwise they were not compared at equal effort.
    const totals = new Set<number>();
    for (const row of cmp.fair_budget.rows) {
      if (row.budget != null && row.evaluated != null && row.n_folds_searched != null) {
        expect(row.evaluated).toBe(row.budget * row.n_folds_searched);
        totals.add(row.evaluated);
      }
    }
    expect(totals.size).toBe(1);
  });

  it("convergence points carry the outer fold that produced them", () => {
    const key = Object.keys(FIXTURES).find((k) => k.endsWith("/analytics"))!;
    const analytics = FIXTURES[key] as SearchAnalyticsResponse;
    expect(analytics.convergence_folds.length).toBeGreaterThan(0);
    for (const points of Object.values(analytics.convergence)) {
      for (const p of points) {
        expect(typeof p.fold).toBe("number");
        expect(analytics.convergence_folds).toContain(p.fold);
      }
    }
  });
});
