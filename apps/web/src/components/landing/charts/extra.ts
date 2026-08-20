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

export interface MountainBlock {
  family: string;
  symbol: string;
  n_evaluations: number;
  n_total: number;
  share_failed: number;
  share_positive: number;
  best: number;
  median: number;
  bins: NullBin[];
}

export interface FoldsBlock {
  family: string;
  symbol: string;
  n_seeds: number;
  folds: { fold: number; test_start: string; mean: number; min: number; max: number }[];
  n_positive: number;
  top2_share_of_gains: number | null;
}

export interface RsGaBlock {
  metric: string;
  families: { family: string; n_seeds: number; rs: number; ga: number }[];
}

export interface MetaBlock {
  family: string;
  symbol: string;
  n_events: number;
  primary_total_return: number;
  meta_total_return: number;
  median_roc_auc: number;
  abstention_rate: number;
  folds_improved: number;
  folds_profitable: number;
  n_folds: number;
  selected_models: string[];
}

export interface MarketStructureBlock {
  symbol: string;
  underwater: { t: number; dd: number }[];
  underwater_stats: {
    share_below_peak: number;
    max_drawdown: number;
    longest_underwater_days: number;
  };
  seasonality: { w: number; h: number; v: number }[];
  funding: { t: number; r: number }[];
  funding_stats: {
    n_events: number;
    mean_rate: number;
    annualised_mean: number;
    share_positive: number;
  };
}

export interface LandingExtraFull extends LandingExtra {
  mountain: MountainBlock;
  folds: FoldsBlock;
  rs_ga: RsGaBlock;
  meta: MetaBlock;
  market_structure: MarketStructureBlock;
}

const loadJson = async (path: string): Promise<LandingExtraFull> => {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${response.status} ${path}`);
  return response.json();
};

export function useLandingExtra() {
  return useSWR<LandingExtraFull>("/data/landing_extra.json", loadJson, {
    revalidateOnFocus: false,
  });
}

/** The strategy-explorer export of the best family, reused for the seed fan. */
export interface SeedFanFile {
  family: string;
  per_asset: Record<
    string,
    {
      oos_start: string;
      oos_end: string;
      n_bars: number;
      buy_and_hold: { total_return: number | null };
      seeds: { seed: number; curve: number[] }[];
      average_curve: number[];
    }
  >;
}

const loadFan = async (path: string): Promise<SeedFanFile> => {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${response.status} ${path}`);
  return response.json();
};

export function useSeedFan() {
  return useSWR<SeedFanFile>("/data/strategies/volatility_breakout.json", loadFan, {
    revalidateOnFocus: false,
  });
}
