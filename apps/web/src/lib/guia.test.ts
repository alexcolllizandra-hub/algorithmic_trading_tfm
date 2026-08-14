import { describe, expect, it } from "vitest";

import type { StudyFamilySummary, StudySummaryResponse } from "@/lib/api-types";
import {
  GUIDE_PANEL_IDS,
  GUIDE_PART_KEYS,
  ILLUSTRATIVE_P_VALUES,
  barWidths,
  benjaminiHochbergAdjusted,
  bestFamilyRow,
  bhFigure,
  costCriterionRows,
  costLadderBars,
  curveFittingSeries,
  developmentHoldoutRows,
  fineTuningRows,
  foldRowLabels,
  holmAdjusted,
  holmFigure,
  leakageRows,
  maxOutOfSampleBars,
  mostVisible,
  multipleTestingFigure,
  overfittingSeries,
  pDotFigure,
  panelAnchor,
  panelCopy,
  panelNumber,
  panelParts,
  progressPercent,
  purgeEmbargoRows,
  scrollBehaviorFor,
  segmentWidths,
  sparkDomain,
  sparkPath,
  sparkProject,
  spuriousRows,
  strategyRuleSeries,
  timelineLegend,
  tocItems,
  walkForwardRows,
  type SparkBox,
} from "@/lib/guia";
import { FIXTURES } from "@/mock/fixtures";

const summary = FIXTURES["/study/summary"] as StudySummaryResponse;

describe("guide panel registry", () => {
  it("declares exactly thirteen panels with unique ids and anchors", () => {
    expect(GUIDE_PANEL_IDS).toHaveLength(13);
    expect(new Set(GUIDE_PANEL_IDS).size).toBe(13);
    const anchors = GUIDE_PANEL_IDS.map(panelAnchor);
    expect(new Set(anchors).size).toBe(13);
    expect(anchors.every((a) => a.startsWith("panel-"))).toBe(true);
  });

  it("numbers the panels 1..13 in reading order", () => {
    expect(GUIDE_PANEL_IDS.map(panelNumber)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]);
  });

  // The four labelled parts are the requirement most likely to rot silently, so
  // they are checked at the copy level as well as in the rendered page.
  it("gives every panel the four labelled parts, all non-empty", () => {
    for (const id of GUIDE_PANEL_IDS) {
      const parts = panelParts(id);
      expect(parts.map((p) => p.key)).toEqual([...GUIDE_PART_KEYS]);
      for (const part of parts) {
        expect(part.label.length).toBeGreaterThan(0);
        expect(part.text.length).toBeGreaterThan(20);
      }
      expect(panelCopy(id).title.length).toBeGreaterThan(0);
    }
  });

  it("builds a table of contents with one entry per panel", () => {
    const items = tocItems();
    expect(items).toHaveLength(13);
    expect(items.map((i) => i.number)).toEqual(GUIDE_PANEL_IDS.map(panelNumber));
    expect(items.every((i) => i.title.length > 0 && i.anchor === panelAnchor(i.id))).toBe(true);
  });

  it("reports reading progress from the active panel", () => {
    expect(progressPercent(null)).toBe(0);
    expect(progressPercent(GUIDE_PANEL_IDS[0])).toBe(8);
    expect(progressPercent(GUIDE_PANEL_IDS[12])).toBe(100);
  });

  it("respects a reduced-motion preference when scrolling", () => {
    expect(scrollBehaviorFor(false)).toBe("smooth");
    expect(scrollBehaviorFor(true)).toBe("auto");
  });

  it("picks the most visible panel, resolving ties towards the earlier one", () => {
    expect(
      mostVisible([
        { id: "datos", ratio: 0.2 },
        { id: "backtest", ratio: 0.7 },
      ])
    ).toBe("backtest");
    expect(
      mostVisible([
        { id: "datos", ratio: 0.5 },
        { id: "backtest", ratio: 0.5 },
      ])
    ).toBe("datos");
    expect(mostVisible([{ id: "datos", ratio: 0 }])).toBeNull();
    expect(mostVisible([])).toBeNull();
  });
});

describe("selectors over the study payload", () => {
  it("takes the longest out-of-sample row rather than summing rows", () => {
    expect(maxOutOfSampleBars(summary.families)).toBe(
      Math.max(...summary.families.map((f) => f.n_bars))
    );
    expect(maxOutOfSampleBars([])).toBeNull();
  });

  it("resolves the best family and prefers the primary asset", () => {
    const row = bestFamilyRow(summary);
    expect(row?.family).toBe(summary.study.best_family);
    expect(row?.symbol).toBe(summary.primary_symbol);
  });

  it("returns no best family when the artifact names none", () => {
    const blank = { ...summary, study: { ...summary.study, best_family: "" } };
    expect(bestFamilyRow(blank)).toBeNull();
  });

  it("lists only the units that actually scored the double-cost criterion", () => {
    const rows = costCriterionRows(summary.families);
    const scored = summary.families.filter((f) =>
      f.criteria?.some((c) => c.key === "survives_double_costs")
    );
    expect(rows).toHaveLength(scored.length);
    expect(rows.length).toBeGreaterThan(0);
    for (const row of rows) {
      expect(row.of).toBeGreaterThan(0);
      expect(row.met).toBe(row.passed >= row.required);
    }
  });

  it("omits families without criteria instead of inventing zeros", () => {
    const withoutCriteria: StudyFamilySummary[] = summary.families.map((f) => ({
      ...f,
      criteria: null,
    }));
    expect(costCriterionRows(withoutCriteria)).toEqual([]);
  });

  it("flattens the deflated-Sharpe entries by counting rule", () => {
    const rows = spuriousRows(summary.study);
    expect(rows.map((r) => r.rule).sort()).toEqual(
      Object.keys(summary.study.deflated_sharpe).sort()
    );
    for (const row of rows) expect(row.probability).not.toBeUndefined();
  });
});

describe("illustrative timeline figures", () => {
  it("turns spans into percentages that add up to the full row", () => {
    const [row] = purgeEmbargoRows();
    const widths = segmentWidths(row.segments);
    expect(widths).toHaveLength(row.segments.length);
    expect(widths.reduce((acc, w) => acc + w.pct, 0)).toBeCloseTo(100, 6);
  });

  it("returns zero widths for an empty or zero-span row", () => {
    expect(segmentWidths([])).toEqual([]);
    expect(segmentWidths([{ key: "a", tone: "train", span: 0 }])).toEqual([{ key: "a", pct: 0 }]);
  });

  it("collects legend entries once, in order of first appearance", () => {
    const legend = timelineLegend(purgeEmbargoRows());
    expect(legend.map((e) => e.key)).toEqual(["train", "test", "purge", "embargo"]);
    expect(new Set(legend.map((e) => e.key)).size).toBe(legend.length);
  });

  it("prefers an explicit label key over the tone", () => {
    expect(timelineLegend(fineTuningRows()).map((e) => e.key)).toEqual([
      "learned",
      "refit",
      "rule",
      "config",
    ]);
    expect(timelineLegend(leakageRows()).map((e) => e.key)).toContain("window");
  });

  it("shifts every walk-forward fold later in time and keeps the holdout last", () => {
    const rows = walkForwardRows(4);
    expect(rows).toHaveLength(4);
    const offsets = rows.map((row) => row.segments.find((s) => s.key === "before")?.span ?? 0);
    expect(offsets).toEqual([...offsets].sort((a, b) => a - b));
    expect(new Set(offsets).size).toBe(4);
    for (const row of rows) {
      expect(row.segments[row.segments.length - 1].tone).toBe("holdout");
      expect(row.segments.every((s) => s.span > 0)).toBe(true);
    }
  });

  it("labels the fold rows from a template", () => {
    expect(foldRowLabels(2, "Fold {n}")).toEqual({ fold_0: "Fold 1", fold_1: "Fold 2" });
  });

  it("keeps the frozen partition out of the development segment", () => {
    const [row] = developmentHoldoutRows();
    expect(row.segments.map((s) => s.tone)).toEqual(["development", "holdout"]);
  });
});

describe("illustrative line figures", () => {
  const box: SparkBox = { width: 100, height: 50, pad: 5 };

  it("spans the domain of every series", () => {
    const domain = sparkDomain(strategyRuleSeries(10, 3));
    expect(domain.minX).toBe(0);
    expect(domain.maxX).toBe(9);
    expect(domain.maxY).toBeGreaterThan(domain.minY);
  });

  it("falls back to a unit domain when there is nothing to draw", () => {
    expect(sparkDomain([])).toEqual({ minX: 0, maxX: 1, minY: 0, maxY: 1 });
    expect(sparkPath([], box, sparkDomain([]))).toBe("");
  });

  it("projects inside the box and inverts the y axis", () => {
    const domain = { minX: 0, maxX: 10, minY: 0, maxY: 10 };
    expect(sparkProject({ x: 0, y: 0 }, box, domain)).toEqual({ x: 5, y: 45 });
    expect(sparkProject({ x: 10, y: 10 }, box, domain)).toEqual({ x: 95, y: 5 });
  });

  it("writes one move and then only line commands", () => {
    const series = curveFittingSeries(4);
    const path = sparkPath(series[0].points, box, sparkDomain(series));
    expect(path.startsWith("M")).toBe(true);
    expect((path.match(/M/g) ?? []).length).toBe(1);
    expect((path.match(/L/g) ?? []).length).toBe(3);
  });

  it("draws the observations as dots and the two fits as lines", () => {
    const series = curveFittingSeries();
    expect(series.filter((s) => s.kind === "dots").map((s) => s.key)).toEqual(["observations"]);
    expect(series.filter((s) => s.kind === "line")).toHaveLength(2);
  });

  it("makes the in-sample error fall while the out-of-sample error turns up", () => {
    const [inSample, outSample] = overfittingSeries(10);
    const first = inSample.points[0].y;
    const last = inSample.points[inSample.points.length - 1].y;
    expect(last).toBeLessThan(first);

    const ys = outSample.points.map((p) => p.y);
    const minIndex = ys.indexOf(Math.min(...ys));
    expect(minIndex).toBeGreaterThan(0);
    expect(minIndex).toBeLessThan(ys.length - 1);
  });
});

describe("multiple-testing corrections (illustrative)", () => {
  it("adjusts p-values with Holm step-down, in the input order", () => {
    const adjusted = holmAdjusted([0.01, 0.04, 0.03]);
    expect(adjusted[0]).toBeCloseTo(0.03, 10);
    expect(adjusted[1]).toBeCloseTo(0.06, 10);
    expect(adjusted[2]).toBeCloseTo(0.06, 10);
  });

  it("adjusts p-values with Benjamini-Hochberg, in the input order", () => {
    const adjusted = benjaminiHochbergAdjusted([0.01, 0.04, 0.03]);
    expect(adjusted[0]).toBeCloseTo(0.03, 10);
    expect(adjusted[1]).toBeCloseTo(0.04, 10);
    expect(adjusted[2]).toBeCloseTo(0.04, 10);
  });

  it("keeps both corrections monotone, clamped to one and defined on empty input", () => {
    const ps = [...ILLUSTRATIVE_P_VALUES];
    for (const adjust of [holmAdjusted, benjaminiHochbergAdjusted]) {
      const adjusted = adjust(ps);
      expect(adjusted).toHaveLength(ps.length);
      expect(Math.max(...adjusted)).toBeLessThanOrEqual(1);
      expect(Math.min(...adjusted)).toBeGreaterThanOrEqual(0);
      // The inputs are sorted ascending, so the adjusted values must be too.
      expect([...adjusted].sort((a, b) => a - b)).toEqual(adjusted);
      expect(adjust([])).toEqual([]);
    }
  });

  it("is never more conservative under BH than under Holm", () => {
    const holm = holmAdjusted(ILLUSTRATIVE_P_VALUES);
    const bh = benjaminiHochbergAdjusted(ILLUSTRATIVE_P_VALUES);
    for (let i = 0; i < holm.length; i += 1) expect(bh[i]).toBeLessThanOrEqual(holm[i] + 1e-12);
  });

  it("marks dots below alpha and highlights the smallest", () => {
    const figure = pDotFigure([0.2, 0.01, 0.9], 0.05);
    expect(figure.dots.map((d) => d.rejected)).toEqual([false, true, false]);
    expect(figure.dots.map((d) => d.highlighted)).toEqual([false, true, false]);
  });

  // The didactic point of the pair of figures: the smallest raw p-value looks
  // significant on its own and stops looking significant once corrected.
  it("shows one raw p-value crossing alpha and none after correction", () => {
    expect(multipleTestingFigure().dots.filter((d) => d.rejected)).toHaveLength(1);
    expect(holmFigure().dots.filter((d) => d.rejected)).toHaveLength(0);
    expect(bhFigure().dots.filter((d) => d.rejected)).toHaveLength(0);
  });
});

describe("illustrative bar figures", () => {
  it("scales bars against the largest magnitude", () => {
    const widths = barWidths([
      { key: "a", value: 50, tone: "accent" },
      { key: "b", value: -100, tone: "negative" },
    ]);
    expect(widths).toEqual([
      { key: "a", pct: 50 },
      { key: "b", pct: 100 },
    ]);
  });

  it("yields zero widths when there is nothing to scale", () => {
    expect(barWidths([])).toEqual([]);
    expect(barWidths([{ key: "a", value: 0, tone: "muted" }])).toEqual([{ key: "a", pct: 0 }]);
  });

  it("only ever shrinks the cost ladder", () => {
    const values = costLadderBars().map((b) => b.value);
    for (let i = 1; i < values.length; i += 1) expect(values[i]).toBeLessThan(values[i - 1]);
  });
});
