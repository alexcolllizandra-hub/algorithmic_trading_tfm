"use client";

import { useTheme } from "@/components/layout/ThemeProvider";

/** Convert a Tailwind-style CSS var (`R G B`) to comma-separated rgb for canvas libs. */
function cssVarRgb(name: string): string {
  if (typeof window === "undefined") return "#647080";
  const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  if (!raw) return "#647080";
  if (raw.startsWith("#")) return raw;
  const parts = raw.split(/\s+/).filter(Boolean);
  if (parts.length >= 3) {
    return `rgb(${parts.slice(0, 3).join(", ")})`;
  }
  return raw;
}

/** Resolve chart colors from the active theme (reads CSS variables at runtime). */
export function useChartColors() {
  useTheme(); // re-render on theme change
  if (typeof window === "undefined") {
    return {
      grid: "#263240",
      axis: "#94a3b8",
      accent: "#60a5fa",
      alt: "#f59e0b",
      positive: "#34d399",
      negative: "#f87171",
    };
  }
  return {
    grid: cssVarRgb("--border"),
    axis: cssVarRgb("--muted"),
    accent: cssVarRgb("--accent"),
    alt: "#f59e0b",
    positive: cssVarRgb("--positive"),
    negative: cssVarRgb("--negative"),
  };
}
