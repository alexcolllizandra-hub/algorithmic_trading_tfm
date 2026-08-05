"use client";

import { useTheme } from "@/components/layout/ThemeProvider";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
      className="rounded-md border border-border bg-surface px-2.5 py-1.5 text-sm text-muted transition hover:text-fg"
    >
      {theme === "dark" ? "\u2600 Light" : "\u263D Dark"}
    </button>
  );
}
