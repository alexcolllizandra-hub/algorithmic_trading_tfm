"use client";

// Loader for the lab's real candle data, exported by
// scripts/export_lab_data.py from the validated datasets (development
// partition only — the holdout window is excluded at export time).

import useSWR from "swr";

import type { Bars } from "./strategies";
import type { FundingSeries } from "./engine";

export interface LabFile {
  symbol: string;
  timeframe: string;
  start: string;
  end: string;
  n: number;
  holdout_excluded_from: string;
  t: number[];
  o: number[];
  h: number[];
  l: number[];
  c: number[];
  ft: number[];
  fr: number[];
  source: {
    bars: { dataset_id?: string; sha256?: string };
    funding: { dataset_id?: string; sha256?: string };
  };
  generated_at: string;
}

export interface LabDataset {
  meta: Pick<
    LabFile,
    "symbol" | "timeframe" | "start" | "end" | "n" | "source" | "holdout_excluded_from"
  >;
  bars: Bars;
  funding: FundingSeries;
}

const load = async (path: string): Promise<LabDataset> => {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${response.status} ${path}`);
  const file: LabFile = await response.json();
  return {
    meta: {
      symbol: file.symbol,
      timeframe: file.timeframe,
      start: file.start,
      end: file.end,
      n: file.n,
      source: file.source,
      holdout_excluded_from: file.holdout_excluded_from,
    },
    bars: {
      t: Float64Array.from(file.t),
      o: Float64Array.from(file.o),
      h: Float64Array.from(file.h),
      l: Float64Array.from(file.l),
      c: Float64Array.from(file.c),
    },
    funding: {
      t: Float64Array.from(file.ft),
      rate: Float64Array.from(file.fr),
    },
  };
};

export function useLabData(symbol: string) {
  return useSWR<LabDataset>(`/data/lab/${symbol}.json`, load, {
    revalidateOnFocus: false,
    revalidateIfStale: false,
  });
}
