import type { RunKind } from "@/lib/api-types";

/**
 * Prominent, persistent warning that development/synthetic results are
 * exploratory and NOT final-holdout performance. Hidden only for true holdout
 * runs (which do not exist in this phase).
 */
export function ExploratoryBanner({ kind, message }: { kind?: RunKind; message?: string | null }) {
  if (kind === "final-holdout") return null;
  const text =
    message ??
    "Exploratory results: development walk-forward validation/test metrics only. These are NOT final-holdout performance and must not be reported as the thesis's out-of-sample result.";
  return (
    <div
      role="note"
      className="flex items-start gap-3 rounded-card border border-warn/50 bg-warn/10 px-4 py-3 text-sm text-warn"
    >
      <span aria-hidden className="mt-0.5 text-base">
        {"\u26A0"}
      </span>
      <p className="font-medium">{text}</p>
    </div>
  );
}
