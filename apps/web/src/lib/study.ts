// Pure helpers for the study-closure views. Everything here derives from the
// API payload: no thresholds, verdicts or metrics are invented locally.

import type {
  StudyFamilyDetail,
  StudyFamilySummary,
  StudyMonteCarlo,
  StudyMonteCarloTerminal,
} from "@/lib/api-types";

/** Sentinel for "no filter applied" in the master table selects. */
export const ALL = "__all__";

export interface FamilyKeyParts {
  family: string;
  symbol: string;
}

/** Split the `family|SYMBOL` key the API uses as its family identifier. */
export function splitFamilyKey(key: string): FamilyKeyParts {
  const i = key.indexOf("|");
  if (i < 0) return { family: key, symbol: "" };
  return { family: key.slice(0, i), symbol: key.slice(i + 1) };
}

export type StudySortKey = "total_return" | "sharpe" | "p_value";
export type SortDirection = "asc" | "desc";

export interface StudyFilters {
  gate: string;
  symbol: string;
  verdict: string;
}

export const NO_FILTERS: StudyFilters = { gate: ALL, symbol: ALL, verdict: ALL };

/** Distinct values of a categorical field, in stable alphabetical order. */
export function distinctValues(rows: StudyFamilySummary[], field: keyof StudyFamilySummary) {
  const seen = new Set<string>();
  for (const row of rows) {
    const value = row[field];
    if (typeof value === "string" && value.length > 0) seen.add(value);
  }
  return [...seen].sort((a, b) => a.localeCompare(b));
}

export function filterFamilies(
  rows: StudyFamilySummary[],
  filters: StudyFilters
): StudyFamilySummary[] {
  return rows.filter(
    (row) =>
      (filters.gate === ALL || row.gate === filters.gate) &&
      (filters.symbol === ALL || row.symbol === filters.symbol) &&
      (filters.verdict === ALL || row.verdict === filters.verdict)
  );
}

/**
 * Sort by one numeric column. Rows whose value is null or non-finite always go
 * last, in both directions, so a missing p-value never reads as a small one.
 */
export function sortFamilies<T extends StudyFamilySummary>(
  rows: T[],
  key: StudySortKey,
  direction: SortDirection
): T[] {
  const sign = direction === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const av = a[key];
    const bv = b[key];
    const aOk = av != null && Number.isFinite(av);
    const bOk = bv != null && Number.isFinite(bv);
    if (!aOk && !bOk) return 0;
    if (!aOk) return 1;
    if (!bOk) return -1;
    return sign * ((av as number) - (bv as number));
  });
}

export interface SeedEquityRow {
  /** Epoch milliseconds — a numeric axis, because the series share no timestamps. */
  x: number;
  [series: string]: number | null;
}

export interface SeedEquitySeries {
  rows: SeedEquityRow[];
  /** Data keys of the per-seed lines, ordered by seed. */
  seedKeys: string[];
  /** Data key of the seed-averaged line. */
  averageKey: string;
}

export function seedSeriesKey(seed: number): string {
  return `seed_${seed}`;
}

/**
 * Merge the seed-averaged curve and every per-seed curve into one dataset.
 *
 * The curves are decimated independently upstream, so they share almost no
 * timestamps; the merge is a union over time with nulls elsewhere, which the
 * chart bridges with `connectNulls`.
 */
export function seedEquitySeries(detail: StudyFamilyDetail): SeedEquitySeries {
  const averageKey = "average";
  const seedKeys = [...detail.seeds]
    .sort((a, b) => a.seed - b.seed)
    .map((s) => seedSeriesKey(s.seed));
  const allKeys = [averageKey, ...seedKeys];
  const byX = new Map<number, SeedEquityRow>();

  const rowAt = (t: string): SeedEquityRow | null => {
    const x = new Date(t).getTime();
    if (!Number.isFinite(x)) return null;
    let row = byX.get(x);
    if (!row) {
      row = { x };
      for (const key of allKeys) row[key] = null;
      byX.set(x, row);
    }
    return row;
  };

  for (const point of detail.equity) {
    const row = rowAt(point.t);
    if (row) row[averageKey] = point.equity;
  }
  for (const seed of detail.seeds) {
    const key = seedSeriesKey(seed.seed);
    for (const point of seed.equity) {
      const row = rowAt(point.t);
      if (row) row[key] = point.equity;
    }
  }

  return {
    rows: [...byX.values()].sort((a, b) => a.x - b.x),
    seedKeys,
    averageKey,
  };
}

/** Spread of the per-seed terminal returns — the dispersion, not the average. */
export function seedReturnSpread(detail: StudyFamilyDetail): { min: number; max: number } | null {
  const values = detail.seeds.map((s) => s.total_return).filter((v) => Number.isFinite(v));
  if (values.length === 0) return null;
  return { min: Math.min(...values), max: Math.max(...values) };
}

export interface FanRow {
  /** Bar index of the checkpoint inside the out-of-sample series. */
  x: number;
  p05: number | null;
  p25: number | null;
  p50: number | null;
  p75: number | null;
  p95: number | null;
  /** Height of the p05–p95 band, stacked on top of `p05`. */
  span0595: number | null;
  /** Height of the p25–p75 band, stacked on top of `p25`. */
  span2575: number | null;
  observed: number | null;
}

const bandValue = (bands: Record<string, number[]>, name: string, i: number): number | null => {
  const series = bands[name];
  const value = series?.[i];
  return value != null && Number.isFinite(value) ? value : null;
};

const span = (lower: number | null, upper: number | null): number | null =>
  lower == null || upper == null ? null : Math.max(0, upper - lower);

/** Build the fan dataset: two stacked bands plus the median and observed paths. */
export function monteCarloRows(mc: StudyMonteCarlo): FanRow[] {
  return mc.checkpoint_index.map((index, i) => {
    const p05 = bandValue(mc.bands, "p05", i);
    const p25 = bandValue(mc.bands, "p25", i);
    const p75 = bandValue(mc.bands, "p75", i);
    const p95 = bandValue(mc.bands, "p95", i);
    const observed = mc.observed[i];
    return {
      x: index,
      p05,
      p25,
      p50: bandValue(mc.bands, "p50", i),
      p75,
      p95,
      span0595: span(p05, p95),
      span2575: span(p25, p75),
      observed: observed != null && Number.isFinite(observed) ? observed : null,
    };
  });
}

/**
 * Explicit y-domain for the fan. Stacked areas would otherwise pull the axis
 * down to zero and flatten a fan that lives around equity 1.
 */
export function fanDomain(rows: FanRow[], pad = 0.04): [number, number] {
  const values: number[] = [];
  for (const row of rows) {
    if (row.p05 != null) values.push(row.p05);
    if (row.p05 != null && row.span0595 != null) values.push(row.p05 + row.span0595);
    if (row.observed != null) values.push(row.observed);
    if (row.p50 != null) values.push(row.p50);
  }
  if (values.length === 0) return [0, 1];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const margin = (max - min) * pad || Math.abs(max) * pad || pad;
  return [min - margin, max + margin];
}

export interface TerminalRow {
  key: string;
  label: string;
  value: number;
}

/** Terminal distribution as ordered rows, observed value kept separate. */
export function terminalDistribution(terminal: StudyMonteCarloTerminal): TerminalRow[] {
  return [
    { key: "p05", label: "p05", value: terminal.p05 },
    { key: "p25", label: "p25", value: terminal.p25 },
    { key: "p50", label: "p50 (mediana)", value: terminal.p50 },
    { key: "p75", label: "p75", value: terminal.p75 },
    { key: "p95", label: "p95", value: terminal.p95 },
  ];
}

/** Share of seeds that met a criterion, as a percentage for the bar width. */
export function criterionPercent(passed: number, of: number): number {
  if (!Number.isFinite(passed) || !Number.isFinite(of) || of <= 0) return 0;
  return Math.min(100, Math.max(0, (passed / of) * 100));
}

/** Position of the PBO reading on a 0..1 gauge, clamped. */
export function gaugePercent(value: number | null | undefined, max = 1): number {
  if (value == null || !Number.isFinite(value) || max <= 0) return 0;
  return Math.min(100, Math.max(0, (value / max) * 100));
}

// --------------------------------------------------------------------------- //
// Shared status vocabulary
// --------------------------------------------------------------------------- //

export type StatusTone = "neutral" | "accent" | "positive" | "negative" | "warn";

export interface StatusDescriptor {
  /** Machine code as emitted by the backend. */
  code: string;
  label: string;
  tone: StatusTone;
}

/**
 * The states the backend emits, with their Spanish label and badge tone.
 *
 * A status is never a number: an absent measurement is reported as one of these
 * states, never as a zero.
 */
export const STATUS_VOCABULARY: Record<string, { label: string; tone: StatusTone }> = {
  EXECUTED: { label: "Ejecutado", tone: "accent" },
  AUDITED: { label: "Auditado", tone: "positive" },
  REJECTED: { label: "Rechazado", tone: "negative" },
  INVALIDATED: { label: "Invalidado", tone: "negative" },
  SKIPPED: { label: "Omitido", tone: "warn" },
  NOT_EXECUTED: { label: "No ejecutado", tone: "neutral" },
  NOT_AVAILABLE: { label: "No disponible", tone: "neutral" },
  HOLDOUT_LOCKED: { label: "Holdout retenido", tone: "warn" },
};

export const NOT_AVAILABLE = "NOT_AVAILABLE";

/**
 * Resolve a status code. An unknown code is shown verbatim rather than mapped
 * to something friendlier, so a new backend state is visible instead of hidden.
 */
export function statusDescriptor(status: string | null | undefined): StatusDescriptor {
  const code = status == null || status === "" ? NOT_AVAILABLE : status;
  const known = STATUS_VOCABULARY[code];
  return known ? { code, ...known } : { code, label: code, tone: "neutral" };
}

/** Both sides of a family whose hypothesis was tested on two assets. */
export function crossAssetRows(rows: StudyFamilySummary[], family: string): StudyFamilySummary[] {
  return rows.filter((r) => r.family === family).sort((a, b) => a.symbol.localeCompare(b.symbol));
}
