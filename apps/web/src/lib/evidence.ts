"use client";

// Loader for the study's evidence file. Written by
// `scripts/export_web_evidence.py` straight from the closure artifacts and the
// R3 run directories, so the landing page cannot drift from the thesis.
//
// The frozen holdout is never part of this payload: the exporter refuses to run
// if a holdout reading is present in the dashboard artifact.

import useSWR from "swr";

export interface FamilyResult {
  family: string;
  symbol: string;
  gate: string;
  thesis: string;
  total_return: number;
  sharpe: number;
  max_drawdown: number;
  p_value: number;
  holm_p: number;
  survives: boolean;
}

export interface SensitivityRow {
  definition: string;
  n_tests: number;
  threshold: number;
  any_survive: boolean;
}

export interface StudyEvidence {
  n_families: number;
  n_units: number;
  n_configurations: number;
  alpha: number;
  best_family: string;
  holm_rejected: number;
  bh_rejected: number;
  smallest_raw_p: number;
  pbo: number;
  pbo_splits: number;
  prob_best_spurious_families: number;
  prob_best_spurious_all: number;
  regime_cells: number;
  regime_survivors: number;
  source_commit: string;
  sensitivity: SensitivityRow[];
  families: FamilyResult[];
}

export interface OptimismEvidence {
  n: number;
  mean_val: number;
  mean_test: number;
  mean_gap: number;
  share_underperforming: number;
  slope: number;
  /** [validation Sharpe, test Sharpe] for a deterministic sample of winners. */
  points: [number, number][];
}

export interface LeakageRow {
  variant: string;
  sharpe: number | null;
  final_equity: number | null;
}

export interface TurnoverPoint {
  fast: number;
  slow: number;
  turnover: number | null;
  gross: number | null;
  net: number | null;
}

export interface EvidenceFile {
  generated_at: string;
  holdout_published: boolean;
  holdout_state: string;
  study: StudyEvidence;
  optimism: OptimismEvidence;
  leakage: LeakageRow[];
  turnover: { grid: TurnoverPoint[]; buy_and_hold_sharpe: number | null };
  cost_sensitivity: { round_trip_bps: number | null; sharpe: number | null }[];
}

async function loadJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(
      `No se pudo cargar ${path} (${response.status}). ` +
        "Ejecuta: uv run python scripts/export_web_evidence.py"
    );
  }
  return (await response.json()) as T;
}

export function useEvidence() {
  return useSWR<EvidenceFile>("/data/evidence.json", loadJson, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });
}

/** Human labels for the four ways of counting how many hypotheses were tested. */
export const TEST_COUNT_LABEL: Record<string, string> = {
  families: "Una prueba por familia",
  family_x_asset: "Familia × activo",
  family_x_asset_x_seed: "Familia × activo × semilla",
  all_configurations_evaluated: "Cada configuración evaluada",
};

export function formatPct(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatSharpe(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value >= 0 ? `+${value.toFixed(2)}` : value.toFixed(2);
}
