"use client";

// Session run history (phase 8e, block C1): every single backtest the
// visitor executes is recorded locally, so the comparison table can show
// what the attempts counter only counts — and make the selection-bias
// lesson concrete: your best row is the right tail of your own attempts.

import { useCallback, useSyncExternalStore } from "react";

export interface HistoryEntry {
  ts: number;
  strategyId: string;
  symbol: string;
  params: Record<string, number | string>;
  oosReturn: number;
  oosSharpe: number;
  maxDd: number;
  pValue: number;
  passed: number;
  totalTests: number;
}

const KEY = "perp-lab.lab-history";
const EVENT = "perp-lab:history";
const MAX_ENTRIES = 50;

let cache: HistoryEntry[] | null = null;
let cacheRaw: string | null = null;

function read(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  const raw = window.localStorage.getItem(KEY);
  if (raw === cacheRaw && cache) return cache;
  try {
    cache = raw ? (JSON.parse(raw) as HistoryEntry[]) : [];
  } catch {
    cache = [];
  }
  cacheRaw = raw;
  return cache;
}

export function addHistoryEntry(entry: HistoryEntry): void {
  if (typeof window === "undefined") return;
  const next = [entry, ...read()].slice(0, MAX_ENTRIES);
  window.localStorage.setItem(KEY, JSON.stringify(next));
  cacheRaw = null;
  window.dispatchEvent(new Event(EVENT));
}

export function clearHistory(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(KEY);
  cacheRaw = null;
  window.dispatchEvent(new Event(EVENT));
}

function subscribe(callback: () => void): () => void {
  window.addEventListener(EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

const EMPTY: HistoryEntry[] = [];

export function useHistory(): {
  entries: HistoryEntry[];
  add: (entry: HistoryEntry) => void;
  clear: () => void;
} {
  const entries = useSyncExternalStore(subscribe, read, () => EMPTY);
  const add = useCallback((entry: HistoryEntry) => addHistoryEntry(entry), []);
  const clear = useCallback(() => clearHistory(), []);
  return { entries, add, clear };
}

/** Compact one-line parameter summary for the history table. */
export function paramSummary(params: Record<string, number | string>): string {
  return Object.entries(params)
    .filter(([key]) => key !== "direction")
    .map(([key, value]) => `${key}=${value}`)
    .join(" ");
}
