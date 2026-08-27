"use client";

// Types and loaders for the static JSON the public site plots. Every file under
// /data is written by `scripts/export_web_data.py` straight from the processed
// parquet, so nothing here is hand-maintained and nothing is invented.

import useSWR from "swr";

export type Partition = "development" | "holdout";

export interface PricePoint {
  /** UTC day, YYYY-MM-DD. */
  t: string;
  /** Closing price of the day's last bar. */
  c: number;
  p: Partition;
}

export interface VolatilityPoint {
  t: string;
  /** Annualised rolling volatility, 24/7 convention. */
  v: number;
  p: Partition;
}

export interface MarketSeries {
  symbol: string;
  timeframe: string;
  price: PricePoint[];
  volatility: VolatilityPoint[];
}

export interface MarketSeriesFile {
  timeframe: string;
  volatility_window_bars: number;
  volatility_window_days: number;
  days_per_year: number;
  series: MarketSeries[];
}

export interface HistogramBin {
  x: number;
  observed: number;
  normal: number;
}

export interface SigmaEvent {
  sigma: number;
  observed: number;
  expected_normal: number;
  n: number;
}

export interface DistributionItem {
  symbol: string;
  timeframe: string;
  partition: Partition;
  stats: {
    n: number;
    mean: number;
    std: number;
    skew: number;
    excess_kurtosis: number;
    min: number;
    max: number;
    jarque_bera_pvalue: number;
    [key: string]: number | null;
  };
  tail_risk: { level: number; n: number; k: number; var: number; es: number }[];
  sigma_events: SigmaEvent[];
  histogram: {
    mean: number;
    std: number;
    bin_width: number;
    clipped: number;
    bins: HistogramBin[];
  };
}

export interface DistributionsFile {
  return_kind: string;
  items: DistributionItem[];
}

export interface SummaryItem {
  symbol: string;
  timeframe: string;
  partition: Partition;
  bars: number;
  start: string;
  end: string;
  coverage_pct: number;
  missing_bars: number;
  duplicates: number;
  invalid_ohlc: number;
  max_gap_bars: number;
  annualised_volatility: number;
  skew: number;
  excess_kurtosis: number;
  worst_bar: number;
  best_bar: number;
  max_drawdown: number;
  jarque_bera_pvalue: number;
}

export interface SummaryFile {
  items: SummaryItem[];
}

export interface ProvenanceDataset {
  dataset_id: string;
  sha256: string | null;
  partition: Partition;
  rows: number;
  start: string;
  end: string;
}

export interface ProvenanceFile {
  generated_at: string;
  code_commit: string | null;
  contract_version: string;
  exchange: string;
  market_type: string;
  cutoff: string;
  holdout_start: string;
  partitions_exported: Partition[];
  holdout_exported: boolean;
  symbols: string[];
  datasets: ProvenanceDataset[];
}

async function loadJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(
      `No se pudo cargar ${path} (${response.status}). ` +
        "Ejecuta: uv run python scripts/export_web_data.py --include-holdout"
    );
  }
  return (await response.json()) as T;
}

const OPTIONS = { revalidateOnFocus: false, shouldRetryOnError: false };

export function useMarketSeries() {
  return useSWR<MarketSeriesFile>("/data/market_series.json", loadJson, OPTIONS);
}

export function useDistributions() {
  return useSWR<DistributionsFile>("/data/distributions.json", loadJson, OPTIONS);
}

export function useSummary() {
  return useSWR<SummaryFile>("/data/summary.json", loadJson, OPTIONS);
}

export function useProvenance() {
  return useSWR<ProvenanceFile>("/data/provenance.json", loadJson, OPTIONS);
}

/** Short label for a symbol: BTCUSDT -> BTC. */
export function baseAsset(symbol: string): string {
  return symbol.replace(/USDT$/, "");
}

/** The first day of the holdout in a series, used to shade the frozen region. */
export function holdoutBoundary(points: { t: string; p: Partition }[]): string | null {
  const first = points.find((point) => point.p === "holdout");
  return first ? first.t : null;
}
