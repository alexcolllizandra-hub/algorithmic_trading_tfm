"use client";

// Session attempts counter: every backtest the visitor runs in the lab —
// single runs and every walk-forward evaluation — increments a persistent
// counter, and the UI shows the expected best Sharpe that many no-skill
// tries would produce. Selection bias, applied to the person selecting.

import { useCallback, useSyncExternalStore } from "react";

const KEY = "perp-lab.lab-attempts";
const EVENT = "perp-lab:attempts";

function read(): number {
  if (typeof window === "undefined") return 0;
  const raw = window.localStorage.getItem(KEY);
  const n = raw ? Number(raw) : 0;
  return Number.isFinite(n) && n >= 0 ? n : 0;
}

export function addAttempts(n: number): void {
  if (typeof window === "undefined" || n <= 0) return;
  window.localStorage.setItem(KEY, String(read() + n));
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

export function useAttempts(): { attempts: number; add: (n: number) => void } {
  const attempts = useSyncExternalStore(subscribe, read, () => 0);
  const add = useCallback((n: number) => addAttempts(n), []);
  return { attempts, add };
}
