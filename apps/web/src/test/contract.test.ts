import { describe, expect, it } from "vitest";

import { FIXTURES, resolveFixture } from "@/mock/fixtures";
import type {
  ComparisonResponse,
  RunListResponse,
  SearchAnalyticsResponse,
  StudyFamilyDetail,
  StudyHoldoutResponse,
  StudyRegimesResponse,
  StudySummaryResponse,
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

  it("study summary matches StudySummaryResponse and carries no curves", () => {
    const summary = FIXTURES["/study/summary"] as StudySummaryResponse;
    for (const key of [
      "generated_at",
      "schema_version",
      "primary_symbol",
      "secondary_symbol",
      "primary_engine",
      "timeframe",
      "study",
      "families",
      "holdout_opened",
    ]) {
      expect(summary).toHaveProperty(key);
    }
    for (const key of [
      "n_families",
      "n_units",
      "n_configurations_evaluated",
      "alpha",
      "best_family",
      "holm",
      "benjamini_hochberg",
      "pbo",
      "deflated_sharpe",
      "sensitivity",
      "criteria_by_gate",
      "conclusion",
      "source_commit",
    ]) {
      expect(summary.study).toHaveProperty(key);
    }

    expect(summary.families.length).toBeGreaterThan(1);
    for (const row of summary.families) {
      for (const key of [
        "key",
        "family",
        "gate",
        "symbol",
        "thesis",
        "n_seeds",
        "n_bars",
        "total_return",
        "sharpe",
        "max_drawdown",
        "p_value",
        "holm_adjusted_p",
        "bh_adjusted_p",
        "survives_correction",
        "verdict",
        "gate_note",
        "criteria",
        "buy_and_hold_return",
      ]) {
        expect(row).toHaveProperty(key);
      }
      // The summary endpoint strips the heavy fields; only the detail has them.
      expect(row).not.toHaveProperty("equity");
      expect(row).not.toHaveProperty("seeds");
      expect(row).not.toHaveProperty("monte_carlo");
      expect(row.key).toBe(`${row.family}|${row.symbol}`);
    }

    // Sorted by total return descending, as the API does.
    const returns = summary.families.map((r) => r.total_return);
    expect([...returns].sort((a, b) => b - a)).toEqual(returns);
  });

  it("study family detail resolves by its piped key and matches StudyFamilyDetail", () => {
    const summary = FIXTURES["/study/summary"] as StudySummaryResponse;
    for (const row of summary.families) {
      const detail = resolveFixture(`/study/families/${row.key}`) as StudyFamilyDetail;
      expect(detail).toBeTruthy();
      expect(detail.key).toBe(row.key);
      expect(detail.equity.length).toBeGreaterThan(0);
      expect(detail.seeds.length).toBeGreaterThan(0);
      expect(detail.seeds.every((s) => s.equity.length > 0)).toBe(true);
      expect(detail.monte_carlo.measures).toBe("path_risk_not_significance");

      const mc = detail.monte_carlo;
      const n = mc.checkpoint_index.length;
      expect(mc.observed).toHaveLength(n);
      for (const band of ["p05", "p25", "p50", "p75", "p95"]) {
        expect(mc.bands[band]).toHaveLength(n);
      }
      for (const key of [
        "observed_total_return",
        "p05",
        "p25",
        "p50",
        "p75",
        "p95",
        "probability_positive",
      ]) {
        expect(mc.terminal).toHaveProperty(key);
      }
      if (detail.criteria) {
        for (const criterion of detail.criteria) {
          expect(criterion.passed).toBeLessThanOrEqual(criterion.of);
          expect(criterion.met).toBe(criterion.passed >= criterion.required);
        }
      }
    }
    expect(resolveFixture("/study/families/does_not_exist|BTCUSDT")).toBeNull();
  });

  it("study regimes travel with the exploratory flag", () => {
    const regimes = FIXTURES["/study/regimes"] as StudyRegimesResponse;
    expect(regimes.exploratory).toBe(true);
    expect(regimes.cells.length).toBeGreaterThan(0);
    for (const cell of regimes.cells) {
      for (const key of ["family", "gate", "dimension", "regime", "n_bars", "p_value"]) {
        expect(cell).toHaveProperty(key);
      }
    }
    expect(regimes.correction).toHaveProperty("n_cells");
    expect(regimes).toHaveProperty("candidate");
    expect(regimes).toHaveProperty("conclusion");
  });

  it("study holdout is locked and carries no result to render", () => {
    const holdout = FIXTURES["/study/holdout"] as StudyHoldoutResponse;
    expect(holdout.status).toBe("HOLDOUT_LOCKED");
    expect(holdout.opened).toBe(false);
    expect(holdout.provenance).toBeNull();
    expect(holdout.result).toBeNull();
    expect(holdout.buy_and_hold).toBeNull();
    expect(typeof holdout.period).toBe("string");
    expect(typeof holdout.reason).toBe("string");
    expect(holdout.requirements.length).toBeGreaterThan(0);
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
