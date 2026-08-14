// Pure helpers for the guided mode (/guia).
//
// Two kinds of data live here and must never be confused:
//
//  - the panel registry, layout maths and small selectors over the API payload;
//  - ILLUSTRATIVE figure data, invented on purpose to explain a concept. It has
//    no relation to any run, it is never rendered with a numeric value on
//    screen, and it always sits behind the "ejemplo ilustrativo" label.
//
// No study metric is computed or stored here: those arrive from the API.

import type { StudyCorrections, StudyFamilySummary, StudySummaryResponse } from "@/lib/api-types";
import { es } from "@/lib/i18n/es";

// --------------------------------------------------------------------------- //
// Panel registry
// --------------------------------------------------------------------------- //

/** The thirteen panels, in reading order. */
export const GUIDE_PANEL_IDS = [
  "pregunta",
  "datos",
  "estrategia",
  "backtest",
  "particiones",
  "walkForward",
  "purgeEmbargo",
  "semillasFolds",
  "costes",
  "estrategiasProbadas",
  "resultados",
  "rechazo",
  "conclusion",
] as const;

export type GuidePanelId = (typeof GUIDE_PANEL_IDS)[number];

/** The four labelled parts every panel must carry. */
export const GUIDE_PART_KEYS = ["viendo", "importa", "interpreta", "conclusion"] as const;

export type GuidePartKey = (typeof GUIDE_PART_KEYS)[number];

export interface GuidePanelCopy {
  title: string;
  viendo: string;
  importa: string;
  interpreta: string;
  conclusion: string;
}

export function panelCopy(id: GuidePanelId): GuidePanelCopy {
  return es.guia.panels[id];
}

export function panelAnchor(id: GuidePanelId): string {
  return `panel-${id}`;
}

export function panelNumber(id: GuidePanelId): number {
  return GUIDE_PANEL_IDS.indexOf(id) + 1;
}

export interface GuidePart {
  key: GuidePartKey;
  label: string;
  text: string;
}

/** The four parts of a panel, always in the same order and never empty. */
export function panelParts(id: GuidePanelId): GuidePart[] {
  const copy = panelCopy(id);
  return GUIDE_PART_KEYS.map((key) => ({ key, label: es.guia.parts[key], text: copy[key] }));
}

export interface TocItem {
  id: GuidePanelId;
  number: number;
  title: string;
  anchor: string;
}

export function tocItems(): TocItem[] {
  return GUIDE_PANEL_IDS.map((id, i) => ({
    id,
    number: i + 1,
    title: panelCopy(id).title,
    anchor: panelAnchor(id),
  }));
}

/** Reading progress as a percentage of the thirteen panels. */
export function progressPercent(id: GuidePanelId | null): number {
  if (id == null) return 0;
  return Math.round((panelNumber(id) / GUIDE_PANEL_IDS.length) * 100);
}

/** Smooth scrolling is opt-out: a reduced-motion preference jumps instead. */
export function scrollBehaviorFor(reducedMotion: boolean): ScrollBehavior {
  return reducedMotion ? "auto" : "smooth";
}

export interface VisibilityCandidate {
  id: GuidePanelId;
  ratio: number;
}

/**
 * The panel the reader is on: the most visible one. Ties resolve towards the
 * earlier panel so the indicator never flickers backwards and forwards.
 */
export function mostVisible(candidates: readonly VisibilityCandidate[]): GuidePanelId | null {
  let best: VisibilityCandidate | null = null;
  for (const candidate of candidates) {
    if (candidate.ratio <= 0) continue;
    if (best == null || candidate.ratio > best.ratio) best = candidate;
  }
  return best?.id ?? null;
}

// --------------------------------------------------------------------------- //
// Selectors over the API payload — no metric is invented, only picked
// --------------------------------------------------------------------------- //

/** Longest out-of-sample row, so a bar count can be quoted without summing. */
export function maxOutOfSampleBars(families: readonly StudyFamilySummary[]): number | null {
  const values = families.map((f) => f.n_bars).filter((v) => v != null && Number.isFinite(v));
  return values.length > 0 ? Math.max(...values) : null;
}

/** The family the artifact itself calls best, preferring the primary asset. */
export function bestFamilyRow(summary: StudySummaryResponse): StudyFamilySummary | null {
  const name = summary.study?.best_family;
  if (!name) return null;
  const rows = summary.families.filter((f) => f.family === name);
  if (rows.length === 0) return null;
  return rows.find((f) => f.symbol === summary.primary_symbol) ?? rows[0];
}

/** The promotion criterion that doubles transaction costs. */
export const COST_CRITERION_KEY = "survives_double_costs";

export interface CostCriterionRow {
  key: string;
  family: string;
  symbol: string;
  passed: number;
  of: number;
  required: number;
  met: boolean;
}

/**
 * Rows for the double-cost criterion, for the units that actually scored it.
 * A family without the criterion is absent rather than shown as a zero.
 */
export function costCriterionRows(families: readonly StudyFamilySummary[]): CostCriterionRow[] {
  const rows: CostCriterionRow[] = [];
  for (const family of families) {
    const criterion = family.criteria?.find((c) => c.key === COST_CRITERION_KEY);
    if (!criterion) continue;
    rows.push({
      key: family.key,
      family: family.family,
      symbol: family.symbol,
      passed: criterion.passed,
      of: criterion.of,
      required: criterion.required,
      met: criterion.met,
    });
  }
  return rows;
}

export interface SpuriousRow {
  rule: string;
  nTrials: number | null;
  deflated: number | null;
  probability: number | null;
}

/** Deflated-Sharpe entries keyed by their trial-counting rule. */
export function spuriousRows(study: StudyCorrections): SpuriousRow[] {
  return Object.entries(study.deflated_sharpe ?? {}).map(([rule, entry]) => ({
    rule,
    nTrials: entry.n_trials ?? null,
    deflated: entry.deflated_sharpe ?? null,
    probability: entry.probability_best_is_spurious ?? null,
  }));
}

// --------------------------------------------------------------------------- //
// Illustrative figures — invented values, never shown as numbers
// --------------------------------------------------------------------------- //

export type SegmentTone =
  | "train"
  | "val"
  | "test"
  | "holdout"
  | "development"
  | "purge"
  | "embargo"
  | "signal"
  | "exec"
  | "future"
  | "neutral";

export interface GuideSegment {
  key: string;
  tone: SegmentTone;
  /** Relative width; only the proportion between segments is meaningful. */
  span: number;
  /** Legend key when the tone's default label would not describe it. */
  labelKey?: string;
}

export interface GuideTimelineRow {
  key: string;
  segments: GuideSegment[];
}

export interface SegmentWidth {
  key: string;
  pct: number;
}

/** Segment spans as percentages of the row. An empty row yields no widths. */
export function segmentWidths(segments: readonly GuideSegment[]): SegmentWidth[] {
  const total = segments.reduce((acc, s) => acc + Math.max(0, s.span), 0);
  if (total <= 0) return segments.map((s) => ({ key: s.key, pct: 0 }));
  return segments.map((s) => ({
    key: s.key,
    pct: Number(((Math.max(0, s.span) / total) * 100).toFixed(4)),
  }));
}

export interface LegendEntry {
  key: string;
  tone: SegmentTone;
}

/** Distinct legend entries across the rows, in order of first appearance. */
export function timelineLegend(rows: readonly GuideTimelineRow[]): LegendEntry[] {
  const seen = new Set<string>();
  const entries: LegendEntry[] = [];
  for (const row of rows) {
    for (const segment of row.segments) {
      const key = segment.labelKey ?? segment.tone;
      if (seen.has(key)) continue;
      seen.add(key);
      entries.push({ key, tone: segment.tone });
    }
  }
  return entries;
}

export function developmentHoldoutRows(): GuideTimelineRow[] {
  return [
    {
      key: "serie",
      segments: [
        { key: "dev", tone: "development", span: 80 },
        { key: "holdout", tone: "holdout", span: 20 },
      ],
    },
  ];
}

export function nextBarRows(): GuideTimelineRow[] {
  return [
    {
      key: "barras",
      segments: [
        { key: "t-2", tone: "neutral", span: 1 },
        { key: "t-1", tone: "neutral", span: 1 },
        { key: "t", tone: "signal", span: 1 },
        { key: "t+1", tone: "exec", span: 1 },
        { key: "t+2", tone: "neutral", span: 1 },
        { key: "t+3", tone: "neutral", span: 1 },
      ],
    },
  ];
}

export function splitTimelineRows(): GuideTimelineRow[] {
  return [
    {
      key: "reparto",
      segments: [
        { key: "train", tone: "train", span: 46 },
        { key: "purge", tone: "purge", span: 3 },
        { key: "val", tone: "val", span: 15 },
        { key: "embargo", tone: "embargo", span: 3 },
        { key: "test", tone: "test", span: 13 },
        { key: "holdout", tone: "holdout", span: 20 },
      ],
    },
  ];
}

/** One row per fold, each shifted forward in time, with the holdout at the end. */
export function walkForwardRows(nFolds = 4): GuideTimelineRow[] {
  const rows: GuideTimelineRow[] = [];
  for (let i = 0; i < nFolds; i += 1) {
    const offset = i * 8;
    const used = offset + 58;
    const tail = Math.max(0, 84 - used);
    const segments: GuideSegment[] = [];
    if (offset > 0) segments.push({ key: "before", tone: "neutral", span: offset });
    segments.push({ key: "train", tone: "train", span: 34 });
    segments.push({ key: "val", tone: "val", span: 12 });
    segments.push({ key: "test", tone: "test", span: 12 });
    if (tail > 0) segments.push({ key: "after", tone: "neutral", span: tail });
    segments.push({ key: "holdout", tone: "holdout", span: 16 });
    rows.push({ key: `fold_${i}`, segments });
  }
  return rows;
}

/** Row labels for the walk-forward figure, from a `{n}` template. */
export function foldRowLabels(nFolds: number, template: string): Record<string, string> {
  const labels: Record<string, string> = {};
  for (let i = 0; i < nFolds; i += 1) {
    labels[`fold_${i}`] = template.replace("{n}", String(i + 1));
  }
  return labels;
}

export function purgeEmbargoRows(): GuideTimelineRow[] {
  return [
    {
      key: "sin",
      segments: [
        { key: "train", tone: "train", span: 60 },
        { key: "test", tone: "test", span: 40 },
      ],
    },
    {
      key: "con",
      segments: [
        { key: "train", tone: "train", span: 55 },
        { key: "purge", tone: "purge", span: 5 },
        { key: "embargo", tone: "embargo", span: 5 },
        { key: "test", tone: "test", span: 35 },
      ],
    },
  ];
}

export function leakageRows(): GuideTimelineRow[] {
  return [
    {
      key: "leak",
      segments: [
        { key: "past", tone: "neutral", span: 25 },
        { key: "window", tone: "signal", span: 20, labelKey: "window" },
        { key: "future", tone: "future", span: 15 },
        { key: "rest", tone: "neutral", span: 40 },
      ],
    },
    {
      key: "ok",
      segments: [
        { key: "past", tone: "neutral", span: 25 },
        { key: "window", tone: "signal", span: 35, labelKey: "window" },
        { key: "rest", tone: "neutral", span: 40 },
      ],
    },
  ];
}

export function fineTuningRows(): GuideTimelineRow[] {
  return [
    {
      key: "ft",
      segments: [
        { key: "learned", tone: "train", span: 60, labelKey: "learned" },
        { key: "refit", tone: "exec", span: 40, labelKey: "refit" },
      ],
    },
    {
      key: "hp",
      segments: [
        { key: "rule", tone: "neutral", span: 60, labelKey: "rule" },
        { key: "config", tone: "val", span: 40, labelKey: "config" },
      ],
    },
  ];
}

export function snoopingRows(): GuideTimelineRow[] {
  return [
    {
      key: "mirado",
      segments: [
        { key: "train", tone: "train", span: 50 },
        { key: "test", tone: "test", span: 25 },
        { key: "decision", tone: "future", span: 25, labelKey: "decision" },
      ],
    },
    {
      key: "limpio",
      segments: [
        { key: "train", tone: "train", span: 50 },
        { key: "val", tone: "val", span: 25 },
        { key: "test", tone: "test", span: 25 },
      ],
    },
  ];
}

// --------------------------------------------------------------------------- //
// Illustrative line figures
// --------------------------------------------------------------------------- //

export type SeriesTone = "accent" | "muted" | "positive" | "negative";

export interface SparkPoint {
  x: number;
  y: number;
}

export interface SparkSeries {
  key: string;
  kind: "line" | "dots";
  tone: SeriesTone;
  dashed?: boolean;
  points: SparkPoint[];
}

export interface SparkBox {
  width: number;
  height: number;
  pad: number;
}

export interface SparkDomain {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

/** Deterministic pseudo-noise in [-0.5, 0.5) — no Math.random anywhere. */
function wobble(i: number, seed = 1): number {
  const raw = Math.sin((i + 1) * 12.9898 * seed) * 43758.5453;
  return raw - Math.floor(raw) - 0.5;
}

export function sparkDomain(series: readonly SparkSeries[]): SparkDomain {
  const xs: number[] = [];
  const ys: number[] = [];
  for (const s of series) {
    for (const p of s.points) {
      if (Number.isFinite(p.x)) xs.push(p.x);
      if (Number.isFinite(p.y)) ys.push(p.y);
    }
  }
  if (xs.length === 0 || ys.length === 0) return { minX: 0, maxX: 1, minY: 0, maxY: 1 };
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  };
}

/** Project a point into SVG user space, with y growing upwards. */
export function sparkProject(p: SparkPoint, box: SparkBox, d: SparkDomain): SparkPoint {
  const spanX = d.maxX - d.minX || 1;
  const spanY = d.maxY - d.minY || 1;
  const inner = { w: box.width - 2 * box.pad, h: box.height - 2 * box.pad };
  return {
    x: Number((box.pad + ((p.x - d.minX) / spanX) * inner.w).toFixed(2)),
    y: Number((box.height - box.pad - ((p.y - d.minY) / spanY) * inner.h).toFixed(2)),
  };
}

export function sparkPath(points: readonly SparkPoint[], box: SparkBox, d: SparkDomain): string {
  if (points.length === 0) return "";
  return points
    .map((p, i) => {
      const { x, y } = sparkProject(p, box, d);
      return `${i === 0 ? "M" : "L"}${x} ${y}`;
    })
    .join(" ");
}

/** Price against its own trailing average: the rule, drawn. */
export function strategyRuleSeries(n = 26, window = 5): SparkSeries[] {
  const price: SparkPoint[] = [];
  for (let i = 0; i < n; i += 1) {
    price.push({ x: i, y: 100 + 8 * Math.sin(i / 3) + 4 * wobble(i, 2) });
  }
  const average: SparkPoint[] = [];
  for (let i = window - 1; i < n; i += 1) {
    let sum = 0;
    for (let k = i - window + 1; k <= i; k += 1) sum += price[k].y;
    average.push({ x: i, y: sum / window });
  }
  return [
    { key: "price", kind: "line", tone: "accent", points: price },
    { key: "average", kind: "line", tone: "muted", dashed: true, points: average },
  ];
}

/** Observations, a line that chases their noise, and one that ignores it. */
export function curveFittingSeries(n = 12): SparkSeries[] {
  const dots: SparkPoint[] = [];
  const trend: SparkPoint[] = [];
  for (let i = 0; i < n; i += 1) {
    dots.push({ x: i, y: 50 + 3 * i + 9 * wobble(i, 3) });
    trend.push({ x: i, y: 50 + 3 * i });
  }
  return [
    { key: "overfit", kind: "line", tone: "negative", points: dots },
    { key: "trend", kind: "line", tone: "accent", points: trend },
    { key: "observations", kind: "dots", tone: "muted", points: dots },
  ];
}

/** The scissors: in-sample error falling while out-of-sample error turns up. */
export function overfittingSeries(n = 10): SparkSeries[] {
  const inSample: SparkPoint[] = [];
  const outSample: SparkPoint[] = [];
  for (let i = 1; i <= n; i += 1) {
    inSample.push({ x: i, y: 0.05 + 0.9 * Math.exp(-0.35 * i) });
    outSample.push({ x: i, y: 0.12 + 0.55 * Math.exp(-0.6 * i) + (0.035 * i * i) / 10 });
  }
  return [
    { key: "inSample", kind: "line", tone: "accent", points: inSample },
    { key: "outSample", kind: "line", tone: "negative", points: outSample },
  ];
}

// --------------------------------------------------------------------------- //
// Illustrative p-value figures
// --------------------------------------------------------------------------- //

export interface PDot {
  key: string;
  p: number;
  rejected: boolean;
  highlighted: boolean;
}

export interface PDotFigure {
  alpha: number;
  dots: PDot[];
}

export const ILLUSTRATIVE_ALPHA = 0.05;

/** Thirteen invented p-values: one below the threshold, twelve above. */
export const ILLUSTRATIVE_P_VALUES: readonly number[] = [
  0.03, 0.12, 0.21, 0.34, 0.41, 0.47, 0.55, 0.63, 0.71, 0.8, 0.88, 0.94, 0.99,
];

/** Twenty invented p-values, as a wide scan of a pattern space would produce. */
export const ILLUSTRATIVE_MINING_P_VALUES: readonly number[] = [
  0.01, 0.07, 0.13, 0.18, 0.24, 0.29, 0.33, 0.38, 0.44, 0.5, 0.55, 0.6, 0.66, 0.7, 0.76, 0.81, 0.86,
  0.9, 0.95, 0.99,
];

/** A p-hacked sequence: the same data retried until the threshold gives way. */
export const ILLUSTRATIVE_PHACK_P_VALUES: readonly number[] = [0.42, 0.31, 0.27, 0.19, 0.11, 0.043];

const clampP = (value: number): number => Math.min(1, Math.max(0, value));

/**
 * Holm step-down adjusted p-values, in the input order.
 *
 * Sort ascending, scale each by the number of remaining hypotheses, then
 * enforce monotonicity so an adjusted value never falls below an earlier one.
 */
export function holmAdjusted(ps: readonly number[]): number[] {
  const m = ps.length;
  if (m === 0) return [];
  const order = ps.map((p, i) => ({ p, i })).sort((a, b) => a.p - b.p);
  const adjusted = new Array<number>(m);
  let running = 0;
  order.forEach((entry, rank) => {
    running = Math.max(running, (m - rank) * entry.p);
    adjusted[entry.i] = clampP(running);
  });
  return adjusted;
}

/**
 * Benjamini-Hochberg adjusted p-values, in the input order. Walks the sorted
 * list backwards taking a running minimum, which is what keeps BH monotone.
 */
export function benjaminiHochbergAdjusted(ps: readonly number[]): number[] {
  const m = ps.length;
  if (m === 0) return [];
  const order = ps.map((p, i) => ({ p, i })).sort((a, b) => a.p - b.p);
  const adjusted = new Array<number>(m);
  let running = 1;
  for (let rank = m - 1; rank >= 0; rank -= 1) {
    const entry = order[rank];
    running = Math.min(running, (m / (rank + 1)) * entry.p);
    adjusted[entry.i] = clampP(running);
  }
  return adjusted;
}

/** Dots on the 0..1 axis: rejected below alpha, the smallest one highlighted. */
export function pDotFigure(ps: readonly number[], alpha = ILLUSTRATIVE_ALPHA): PDotFigure {
  let smallest = Number.POSITIVE_INFINITY;
  for (const p of ps) if (p < smallest) smallest = p;
  return {
    alpha,
    dots: ps.map((p, i) => ({
      key: `p_${i}`,
      p: clampP(p),
      rejected: p <= alpha,
      highlighted: p === smallest,
    })),
  };
}

export function multipleTestingFigure(alpha = ILLUSTRATIVE_ALPHA): PDotFigure {
  return pDotFigure(ILLUSTRATIVE_P_VALUES, alpha);
}

export function holmFigure(alpha = ILLUSTRATIVE_ALPHA): PDotFigure {
  return pDotFigure(holmAdjusted(ILLUSTRATIVE_P_VALUES), alpha);
}

export function bhFigure(alpha = ILLUSTRATIVE_ALPHA): PDotFigure {
  return pDotFigure(benjaminiHochbergAdjusted(ILLUSTRATIVE_P_VALUES), alpha);
}

export function dataMiningFigure(alpha = ILLUSTRATIVE_ALPHA): PDotFigure {
  return pDotFigure(ILLUSTRATIVE_MINING_P_VALUES, alpha);
}

export function pHackingFigure(alpha = ILLUSTRATIVE_ALPHA): PDotFigure {
  return pDotFigure(ILLUSTRATIVE_PHACK_P_VALUES, alpha);
}

// --------------------------------------------------------------------------- //
// Illustrative bar figures
// --------------------------------------------------------------------------- //

export interface GuideBar {
  /** Also the legend key: the Spanish label is resolved from the copy module. */
  key: string;
  value: number;
  tone: SeriesTone;
}

export interface BarWidth {
  key: string;
  pct: number;
}

/** Bar lengths relative to the largest magnitude, so no value is printed. */
export function barWidths(bars: readonly GuideBar[]): BarWidth[] {
  const max = bars.reduce((acc, b) => Math.max(acc, Math.abs(b.value)), 0);
  if (max <= 0) return bars.map((b) => ({ key: b.key, pct: 0 }));
  return bars.map((b) => ({
    key: b.key,
    pct: Number(((Math.abs(b.value) / max) * 100).toFixed(4)),
  }));
}

/** Running total after each deduction, so the bars only ever shrink. */
export function costLadderBars(): GuideBar[] {
  return [
    { key: "gross", value: 100, tone: "accent" },
    { key: "fees", value: 84, tone: "muted" },
    { key: "slippage", value: 70, tone: "muted" },
    { key: "net", value: 52, tone: "negative" },
  ];
}

export function hyperparameterBars(): GuideBar[] {
  return [
    { key: "valBest", value: 100, tone: "accent" },
    { key: "oosSame", value: 34, tone: "negative" },
  ];
}

export function selectionBiasBars(): GuideBar[] {
  return [
    { key: "attemptsMax", value: 92, tone: "positive" },
    { key: "attemptsMean", value: 4, tone: "muted" },
    { key: "attemptsMin", value: 88, tone: "negative" },
  ];
}

export function pboBars(): GuideBar[] {
  return [
    { key: "pboA", value: 100, tone: "accent" },
    { key: "pboB", value: 49, tone: "negative" },
  ];
}

export function deflatedBars(): GuideBar[] {
  return [
    { key: "dsrObserved", value: 100, tone: "accent" },
    { key: "dsrExpected", value: 88, tone: "muted" },
    { key: "dsrDeflated", value: 12, tone: "negative" },
  ];
}
