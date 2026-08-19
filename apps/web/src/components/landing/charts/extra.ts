"use client";

// Loader for the landing's additional real-data charts.
//
// One 24 KB file written by `scripts/export_landing_extra.py` from the same
// study artifacts the thesis cites. Nothing here is simulated: the family
// curves are exact decimated equity values, the null distribution reproduces
// notebook 07 (seed 42), and the funded-account numbers come from its table.

import useSWR from "swr";

export interface FamilyCurve {
  family: string;
  round: string;
  median_return: number | null;
  buy_and_hold: number | null;
  curve: number[];
}

export interface NullBin {
  x: number;
  d: number;
}

export interface LandingExtra {
  generated_at: string;
  note: string;
  families: FamilyCurve[];
  null_distribution: {
    family: string;
    symbol: string;
    n_rotations: number;
    bins: NullBin[];
    real_seeds: number[];
    band: [number, number];
  };
  funded: {
    n_paths: number;
    firms: {
      id: string;
      source: string;
      retrieved: string;
      rules: {
        profit_target: number;
        max_total_drawdown: number;
        max_daily_loss: number;
        max_days: number;
      };
      strategy_phase1: number;
      strategy_both: number;
      coin_flip_phase1: number;
      coin_flip_both: number;
    }[];
  };
}

const loadJson = async (path: string): Promise<LandingExtra> => {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${response.status} ${path}`);
  return response.json();
};

export function useLandingExtra() {
  return useSWR<LandingExtra>("/data/landing_extra.json", loadJson, {
    revalidateOnFocus: false,
  });
}
